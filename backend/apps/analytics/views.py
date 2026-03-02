from datetime import timedelta

from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdmin, IsAdminOrMerchant, IsMerchant
from apps.conversations.models import Conversation
from apps.tracking.models import ClickEvent
from apps.billing.models import ConversionEvent
from apps.merchants.models import MerchantProfile


class AdminDashboardView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        period = request.query_params.get('period', '7d')
        days = {'today': 0, '7d': 7, '30d': 30}.get(period, 7)

        from datetime import timedelta
        since = timezone.now() - timedelta(days=days) if days > 0 else timezone.now().replace(hour=0, minute=0)

        conversations = Conversation.objects.filter(started_at__gte=since).count()
        clicks = ClickEvent.objects.filter(clicked_at__gte=since)
        total_clicks = clicks.count()
        flagged = clicks.filter(is_fraudulent=True).count()
        conversions = ConversionEvent.objects.filter(converted_at__gte=since, is_valid=True)
        total_conversions = conversions.count()
        revenue = conversions.aggregate(total=Sum('commission_amount'))['total'] or 0
        conv_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
        active_merchants = MerchantProfile.objects.filter(status=MerchantProfile.Status.APPROVED).count()

        return Response({
            'total_conversations': conversations,
            'total_clicks': total_clicks,
            'flagged_clicks': flagged,
            'total_conversions': total_conversions,
            'total_revenue': revenue,
            'conversion_rate': round(conv_rate, 2),
            'active_merchants': active_merchants,
        })


class MerchantDashboardView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsMerchant)

    def get(self, request):
        try:
            merchant = request.user.merchant_profile
        except MerchantProfile.DoesNotExist:
            return Response({
                'conversations_today': 0, 'clicks_today': 0, 'conversions_today': 0,
                'ctr': 0, 'spend_today': 0, 'daily_budget_cap': 0, 'budget_remaining': 0,
            })
        today = timezone.now().date()

        conversations = Conversation.objects.filter(
            merchant=merchant, started_at__date=today,
        ).count()

        clicks = ClickEvent.objects.filter(
            redirect_token__merchant=merchant,
            clicked_at__date=today,
            is_fraudulent=False,
        ).count()

        conversions_qs = ConversionEvent.objects.filter(
            merchant=merchant,
            converted_at__date=today,
            is_valid=True,
        )
        conversions = conversions_qs.count()
        spend = conversions_qs.aggregate(total=Sum('commission_amount'))['total'] or 0

        messages_sent = Conversation.objects.filter(
            merchant=merchant, started_at__date=today,
        ).aggregate(count=Count('messages'))['count'] or 1

        ctr = (clicks / messages_sent * 100) if messages_sent > 0 else 0

        return Response({
            'conversations_today': conversations,
            'clicks_today': clicks,
            'conversions_today': conversions,
            'ctr': round(ctr, 2),
            'spend_today': spend,
            'daily_budget_cap': merchant.daily_budget_cap,
            'budget_remaining': max(merchant.daily_budget_cap - spend, 0),
        })


class MerchantSpendingView(APIView):
    permission_classes = (permissions.IsAuthenticated, IsMerchant)

    def get(self, request):
        try:
            merchant = request.user.merchant_profile
        except MerchantProfile.DoesNotExist:
            return Response([])
        today = timezone.now().date()

        from .models import DailyMerchantStats

        stats = DailyMerchantStats.objects.filter(
            merchant=merchant,
            date__gte=today - timedelta(days=30),
        ).order_by('date').values(
            'date', 'spend', 'clicks_valid', 'conversions', 'conversion_rate',
        )

        return Response(list(stats))


def _get_date_range(period: str):
    """Return (start_date, end_date) for a period string."""
    today = timezone.now().date()
    days = {'7d': 7, '14d': 14, '30d': 30}.get(period, 7)
    return today - timedelta(days=days - 1), today


def _fill_dates(data_dict: dict, start_date, end_date, defaults: dict):
    """Ensure every date in range has an entry."""
    result = []
    current = start_date
    while current <= end_date:
        row = data_dict.get(current, {**defaults})
        row['date'] = current.isoformat()
        result.append(row)
        current += timedelta(days=1)
    return result


class AdminTrendsView(APIView):
    """Daily time-series for admin charts: clicks, conversions, revenue, fraud."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        period = request.query_params.get('period', '7d')
        start_date, end_date = _get_date_range(period)
        since = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time()),
        )

        click_rows = {}
        for row in (
            ClickEvent.objects.filter(clicked_at__gte=since)
            .annotate(date=TruncDate('clicked_at'))
            .values('date')
            .annotate(
                total=Count('id'),
                fraudulent=Count('id', filter=Q(is_fraudulent=True)),
            )
            .order_by('date')
        ):
            click_rows[row['date']] = {
                'clicks': row['total'],
                'fraudulent': row['fraudulent'],
            }

        # Conversions + revenue per day
        conv_rows = {}
        for row in (
            ConversionEvent.objects.filter(converted_at__gte=since, is_valid=True)
            .annotate(date=TruncDate('converted_at'))
            .values('date')
            .annotate(
                count=Count('id'),
                revenue=Sum('commission_amount'),
            )
            .order_by('date')
        ):
            conv_rows[row['date']] = {
                'conversions': row['count'],
                'revenue': float(row['revenue'] or 0),
            }

        # Conversations per day
        convo_rows = {}
        for row in (
            Conversation.objects.filter(started_at__gte=since)
            .annotate(date=TruncDate('started_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        ):
            convo_rows[row['date']] = {'conversations': row['count']}

        # Merge into daily entries
        result = []
        current = start_date
        while current <= end_date:
            cr = click_rows.get(current, {})
            cv = conv_rows.get(current, {})
            co = convo_rows.get(current, {})
            result.append({
                'date': current.isoformat(),
                'clicks': cr.get('clicks', 0),
                'fraudulent': cr.get('fraudulent', 0),
                'conversions': cv.get('conversions', 0),
                'revenue': cv.get('revenue', 0),
                'conversations': co.get('conversations', 0),
            })
            current += timedelta(days=1)

        return Response(result)


class AdminFunnelView(APIView):
    """Conversion funnel: conversations → clicks → conversions."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        period = request.query_params.get('period', '7d')
        start_date, _ = _get_date_range(period)
        since = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time()),
        )

        conversations = Conversation.objects.filter(started_at__gte=since).count()
        clicks = ClickEvent.objects.filter(
            clicked_at__gte=since, is_fraudulent=False,
        ).count()
        conversions = ConversionEvent.objects.filter(
            converted_at__gte=since, is_valid=True,
        ).count()

        return Response({
            'funnel': [
                {'stage': 'Conversations', 'count': conversations},
                {'stage': 'Clicks', 'count': clicks},
                {'stage': 'Conversions', 'count': conversions},
            ],
        })


class MerchantTrendsView(APIView):
    """Daily time-series for merchant charts."""
    permission_classes = (permissions.IsAuthenticated, IsMerchant)

    def get(self, request):
        try:
            merchant = request.user.merchant_profile
        except MerchantProfile.DoesNotExist:
            return Response([])
        period = request.query_params.get('period', '7d')
        start_date, end_date = _get_date_range(period)
        since = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time()),
        )

        click_rows = {}
        for row in (
            ClickEvent.objects.filter(
                redirect_token__merchant=merchant,
                clicked_at__gte=since,
                is_fraudulent=False,
            )
            .annotate(date=TruncDate('clicked_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        ):
            click_rows[row['date']] = row['count']

        conv_rows = {}
        for row in (
            ConversionEvent.objects.filter(
                merchant=merchant,
                converted_at__gte=since,
                is_valid=True,
            )
            .annotate(date=TruncDate('converted_at'))
            .values('date')
            .annotate(
                count=Count('id'),
                spend=Sum('commission_amount'),
            )
            .order_by('date')
        ):
            conv_rows[row['date']] = {
                'conversions': row['count'],
                'spend': float(row['spend'] or 0),
            }

        convo_rows = {}
        for row in (
            Conversation.objects.filter(
                merchant=merchant, started_at__gte=since,
            )
            .annotate(date=TruncDate('started_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        ):
            convo_rows[row['date']] = row['count']

        result = []
        current = start_date
        while current <= end_date:
            cv = conv_rows.get(current, {})
            result.append({
                'date': current.isoformat(),
                'clicks': click_rows.get(current, 0),
                'conversions': cv.get('conversions', 0),
                'spend': cv.get('spend', 0),
                'conversations': convo_rows.get(current, 0),
            })
            current += timedelta(days=1)

        return Response(result)


class TopMerchantsView(APIView):
    """Top merchants by revenue in a period."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        period = request.query_params.get('period', '30d')
        start_date, _ = _get_date_range(period)
        since = timezone.make_aware(
            timezone.datetime.combine(start_date, timezone.datetime.min.time()),
        )

        merchants = (
            ConversionEvent.objects.filter(
                converted_at__gte=since, is_valid=True,
            )
            .values('merchant__company_name')
            .annotate(
                revenue=Sum('commission_amount'),
                conversions=Count('id'),
            )
            .order_by('-revenue')[:10]
        )

        return Response([
            {
                'merchant': m['merchant__company_name'],
                'revenue': float(m['revenue'] or 0),
                'conversions': m['conversions'],
            }
            for m in merchants
        ])
