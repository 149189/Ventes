from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponseGone
from django.utils import timezone
from django.views import View
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdmin, IsAdminOrMerchant
from .models import RedirectToken, ClickEvent, FraudFlag
from .serializers import ClickEventSerializer, FraudFlagSerializer
from .tasks import calculate_fraud_score


class RedirectView(View):
    """Server-side redirect — logs click and 302s to merchant landing page."""

    def get(self, request, token):
        try:
            redirect_token = RedirectToken.objects.select_related(
                'sku', 'merchant', 'conversation',
            ).get(token=token)
        except RedirectToken.DoesNotExist:
            return HttpResponseNotFound("Invalid link")

        if not redirect_token.is_active:
            return HttpResponseGone("This link has expired")

        if redirect_token.expires_at < timezone.now():
            redirect_token.is_active = False
            redirect_token.save(update_fields=['is_active'])
            return HttpResponseGone("This link has expired")

        # Log click event
        click = ClickEvent.objects.create(
            redirect_token=redirect_token,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            referer=request.META.get('HTTP_REFERER', ''),
        )

        # Dispatch async fraud check
        calculate_fraud_score.delay(click.id)

        # 302 redirect to merchant landing page
        return HttpResponseRedirect(redirect_token.destination_url)

    def _get_client_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')


class ClickEventListView(generics.ListAPIView):
    serializer_class = ClickEventSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    ordering = ('-clicked_at',)

    def get_queryset(self):
        qs = ClickEvent.objects.select_related(
            'redirect_token__sku', 'redirect_token__merchant', 'redirect_token__campaign',
        ).prefetch_related('fraud_flags')

        # Support ?fraud_only=true filter
        if self.request.query_params.get('fraud_only') == 'true':
            qs = qs.filter(is_fraudulent=True)

        # Support ?is_fraudulent=true/false filter
        is_fraudulent = self.request.query_params.get('is_fraudulent')
        if is_fraudulent is not None:
            qs = qs.filter(is_fraudulent=is_fraudulent.lower() == 'true')

        # Filter by merchant
        merchant_id = self.request.query_params.get('merchant')
        if merchant_id:
            qs = qs.filter(redirect_token__merchant_id=merchant_id)

        return qs


class ClickEventDetailView(generics.RetrieveAPIView):
    serializer_class = ClickEventSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    queryset = ClickEvent.objects.select_related(
        'redirect_token__sku', 'redirect_token__merchant', 'redirect_token__campaign',
    ).prefetch_related('fraud_flags')


class FraudFlagListView(generics.ListAPIView):
    serializer_class = FraudFlagSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    ordering = ('-created_at',)

    def get_queryset(self):
        qs = FraudFlag.objects.select_related('click_event')
        # By default show unreviewed, allow ?all=true for all
        if self.request.query_params.get('all') != 'true':
            qs = qs.filter(reviewed=False)
        return qs


class FraudFlagReviewView(APIView):
    """Review a fraud flag — mark as legitimate or fraudulent."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def post(self, request, pk):
        try:
            flag = FraudFlag.objects.select_related('click_event').get(pk=pk)
        except FraudFlag.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        verdict = request.data.get('verdict', '')
        flag.reviewed = True
        flag.reviewed_by = request.user
        flag.reviewed_at = timezone.now()
        flag.save()

        # If verdict is 'fraudulent', also mark the click event
        if verdict == 'fraudulent':
            flag.click_event.is_fraudulent = True
            flag.click_event.save(update_fields=['is_fraudulent'])
        elif verdict == 'legitimate':
            # If all flags on this click are reviewed and none say fraudulent,
            # mark click as not fraudulent
            click = flag.click_event
            unreviewed = click.fraud_flags.filter(reviewed=False).exists()
            if not unreviewed:
                click.is_fraudulent = False
                click.save(update_fields=['is_fraudulent'])

        return Response(FraudFlagSerializer(flag).data)

    def patch(self, request, pk):
        """Also support PATCH for DRF compat."""
        return self.post(request, pk)


class MerchantClicksView(generics.ListAPIView):
    """Click events scoped to the authenticated merchant."""
    serializer_class = ClickEventSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrMerchant)
    ordering = ('-clicked_at',)

    def get_queryset(self):
        user = self.request.user
        qs = ClickEvent.objects.select_related(
            'redirect_token__sku', 'redirect_token__merchant', 'redirect_token__campaign',
        ).prefetch_related('fraud_flags')

        if user.role == 'merchant':
            qs = qs.filter(redirect_token__merchant=user.merchant_profile)
        elif user.role == 'admin':
            merchant_id = self.request.query_params.get('merchant')
            if merchant_id:
                qs = qs.filter(redirect_token__merchant_id=merchant_id)

        if self.request.query_params.get('fraud_only') == 'true':
            qs = qs.filter(is_fraudulent=True)

        return qs


class MerchantClickSummaryView(APIView):
    """Summary stats for merchant's clicks."""
    permission_classes = (permissions.IsAuthenticated, IsAdminOrMerchant)

    def get(self, request):
        from django.db.models import Count, Q
        from django.db.models.functions import TruncDate
        from datetime import timedelta

        user = request.user
        if user.role == 'merchant':
            try:
                merchant = user.merchant_profile
            except Exception:
                return Response({
                    'total_clicks': 0, 'today_clicks': 0, 'valid_clicks': 0,
                    'fraudulent_clicks': 0, 'fraud_rate': 0,
                    'weekly_breakdown': [], 'top_skus': [],
                })
        else:
            return Response({'error': 'Admin should use admin dashboard'}, status=400)

        today = timezone.now().date()
        qs = ClickEvent.objects.filter(redirect_token__merchant=merchant)

        total_clicks = qs.count()
        today_clicks = qs.filter(clicked_at__date=today).count()
        fraudulent = qs.filter(is_fraudulent=True).count()
        valid = total_clicks - fraudulent

        # Last 7 days breakdown using TruncDate
        week_ago = today - timedelta(days=7)
        weekly = (
            qs.filter(clicked_at__date__gte=week_ago)
            .annotate(day=TruncDate('clicked_at'))
            .values('day')
            .annotate(
                total=Count('id'),
                fraud=Count('id', filter=Q(is_fraudulent=True)),
            )
            .order_by('day')
        )

        # Top SKUs by clicks
        top_skus = (
            qs.values('redirect_token__sku__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        return Response({
            'total_clicks': total_clicks,
            'today_clicks': today_clicks,
            'valid_clicks': valid,
            'fraudulent_clicks': fraudulent,
            'fraud_rate': round((fraudulent / total_clicks * 100) if total_clicks > 0 else 0, 2),
            'weekly_breakdown': list(weekly),
            'top_skus': [
                {'name': s['redirect_token__sku__name'], 'clicks': s['count']}
                for s in top_skus
            ],
        })
