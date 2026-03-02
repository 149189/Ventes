import json
import logging

from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdmin, IsMerchant, IsAdminOrMerchant
from common.exceptions import DisputeWindowExpired
from .models import ConversionEvent, Invoice, DisputeRecord
from .serializers import (
    ConversionEventSerializer,
    InvoiceSerializer,
    DisputeRecordSerializer,
    PostbackSerializer,
    CouponRedeemSerializer,
)
from .postbacks import process_postback

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class PostbackView(APIView):
    """HMAC-signed conversion postback from merchants."""
    permission_classes = (permissions.AllowAny,)
    authentication_classes = []

    def post(self, request):
        serializer = PostbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversion = process_postback(serializer.validated_data)
        return Response(
            {'status': 'ok', 'conversion_id': conversion.id},
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name='dispatch')
class CouponRedeemView(APIView):
    """Coupon redemption confirmation from merchants."""
    permission_classes = (permissions.AllowAny,)
    authentication_classes = []

    def post(self, request):
        serializer = CouponRedeemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.merchants.models import MerchantProfile
        from apps.conversations.models import Conversation
        from common.hmac_utils import verify_hmac_signature, verify_timestamp_freshness
        from common.exceptions import InvalidHMACSignature, StaleTimestamp

        try:
            merchant = MerchantProfile.objects.get(id=data['merchant_id'])
        except MerchantProfile.DoesNotExist:
            return Response({'error': 'Merchant not found'}, status=status.HTTP_404_NOT_FOUND)

        if not verify_timestamp_freshness(data['timestamp']):
            raise StaleTimestamp()

        payload = {k: str(v) for k, v in data.items() if k != 'hmac_signature'}
        if not verify_hmac_signature(merchant.hmac_secret, payload, data['hmac_signature']):
            raise InvalidHMACSignature()

        # Find conversation by coupon code
        conversation = Conversation.objects.filter(
            coupon_code=data['coupon_code'],
            merchant=merchant,
        ).first()

        commission = data['order_amount'] * (merchant.commission_rate / 100)

        conversion = ConversionEvent.objects.create(
            conversation=conversation,
            merchant=merchant,
            source=ConversionEvent.Source.COUPON,
            order_id=data['order_id'],
            order_amount=data['order_amount'],
            coupon_code=data['coupon_code'],
            commission_amount=commission,
            converted_at=timezone.now(),
        )

        return Response(
            {'status': 'ok', 'conversion_id': conversion.id},
            status=status.HTTP_201_CREATED,
        )


class ConversionListView(generics.ListAPIView):
    serializer_class = ConversionEventSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrMerchant)
    ordering = ('-converted_at',)

    def get_queryset(self):
        qs = ConversionEvent.objects.select_related('merchant')
        user = self.request.user
        if user.role == 'admin':
            return qs
        return qs.filter(merchant=user.merchant_profile)


class InvoiceListView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrMerchant)
    ordering = ('-created_at',)

    def get_queryset(self):
        qs = Invoice.objects.select_related('merchant').prefetch_related('lines')
        user = self.request.user
        if user.role == 'admin':
            return qs
        return qs.filter(merchant=user.merchant_profile)


class InvoiceDetailView(generics.RetrieveAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrMerchant)

    def get_queryset(self):
        qs = Invoice.objects.select_related('merchant').prefetch_related('lines')
        user = self.request.user
        if user.role == 'admin':
            return qs
        return qs.filter(merchant=user.merchant_profile)


class DisputeCreateView(generics.CreateAPIView):
    serializer_class = DisputeRecordSerializer
    permission_classes = (permissions.IsAuthenticated, IsMerchant)

    def perform_create(self, serializer):
        conversion = serializer.validated_data['conversion_event']
        merchant = self.request.user.merchant_profile

        # Check dispute window
        if (timezone.now() - conversion.converted_at).days > merchant.dispute_window_days:
            raise DisputeWindowExpired()

        conversion.is_disputed = True
        conversion.save(update_fields=['is_disputed'])

        serializer.save(merchant=merchant)


class DisputeListView(generics.ListAPIView):
    serializer_class = DisputeRecordSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrMerchant)

    def get_queryset(self):
        qs = DisputeRecord.objects.select_related('merchant')
        user = self.request.user
        if user.role != 'admin':
            qs = qs.filter(merchant=user.merchant_profile)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class DisputeResolveView(APIView):
    """Resolve a dispute — uphold or reject."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def post(self, request, pk):
        try:
            dispute = DisputeRecord.objects.select_related(
                'conversion_event', 'merchant',
            ).get(pk=pk)
        except DisputeRecord.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status', '')
        if new_status not in ('upheld', 'rejected'):
            return Response(
                {'error': 'status must be upheld or rejected'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dispute.status = new_status
        dispute.resolved_by = request.user
        dispute.resolved_at = timezone.now()
        dispute.resolution_notes = request.data.get('resolution_notes', '')

        if new_status == 'upheld':
            dispute.credit_amount = dispute.conversion_event.commission_amount
        dispute.save()

        return Response(DisputeRecordSerializer(dispute).data)

    def patch(self, request, pk):
        return self.post(request, pk)


class RevenueStatsView(APIView):
    """Revenue summary stats for the admin dashboard."""
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get(self, request):
        invoices = Invoice.objects.all()
        disputes = DisputeRecord.objects.all()

        total_revenue = invoices.filter(
            status=Invoice.Status.PAID,
        ).aggregate(total=Sum('total'))['total'] or 0

        invoice_counts = invoices.aggregate(
            total=Count('id'),
            paid=Count('id', filter=Q(status=Invoice.Status.PAID)),
            overdue=Count('id', filter=Q(status=Invoice.Status.OVERDUE)),
        )

        dispute_counts = disputes.aggregate(
            total=Count('id'),
            open=Count('id', filter=Q(status__in=['open', 'under_review'])),
        )

        total_credits = disputes.filter(
            status='upheld',
        ).aggregate(total=Sum('credit_amount'))['total'] or 0

        return Response({
            'total_revenue': total_revenue,
            'total_invoices': invoice_counts['total'],
            'paid_invoices': invoice_counts['paid'],
            'overdue_invoices': invoice_counts['overdue'],
            'total_disputes': dispute_counts['total'],
            'open_disputes': dispute_counts['open'],
            'total_credits': total_credits,
        })


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(APIView):
    """Handle Razorpay webhook events."""
    permission_classes = (permissions.AllowAny,)
    authentication_classes = []

    def post(self, request):
        from .razorpay_client import verify_webhook_signature

        payload_body = request.body.decode('utf-8')
        signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')

        if not verify_webhook_signature(payload_body, signature):
            logger.error("Razorpay webhook signature verification failed")
            return HttpResponse(status=400)

        try:
            event = json.loads(payload_body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        event_type = event.get('event', '')

        if event_type == 'invoice.paid':
            self._handle_invoice_paid(event.get('payload', {}).get('invoice', {}).get('entity', {}))
        elif event_type == 'invoice.expired':
            self._handle_invoice_expired(event.get('payload', {}).get('invoice', {}).get('entity', {}))
        elif event_type == 'payment.captured':
            self._handle_payment_captured(event.get('payload', {}).get('payment', {}).get('entity', {}))

        return HttpResponse(status=200)

    def _handle_invoice_paid(self, rzp_invoice):
        rzp_id = rzp_invoice.get('id', '')
        try:
            invoice = Invoice.objects.get(razorpay_invoice_id=rzp_id)
            invoice.status = Invoice.Status.PAID
            invoice.paid_at = timezone.now()
            invoice.save()
            logger.info(f"Invoice {invoice.invoice_number} marked as paid via Razorpay")
        except Invoice.DoesNotExist:
            logger.warning(f"Invoice not found for Razorpay ID: {rzp_id}")

    def _handle_invoice_expired(self, rzp_invoice):
        rzp_id = rzp_invoice.get('id', '')
        try:
            invoice = Invoice.objects.get(razorpay_invoice_id=rzp_id)
            invoice.status = Invoice.Status.OVERDUE
            invoice.save()
            logger.info(f"Invoice {invoice.invoice_number} marked as overdue via Razorpay")
        except Invoice.DoesNotExist:
            logger.warning(f"Invoice not found for Razorpay ID: {rzp_id}")

    def _handle_payment_captured(self, payment):
        payment_id = payment.get('id', '')
        logger.info(f"Razorpay payment captured: {payment_id}")
