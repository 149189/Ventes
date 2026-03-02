import logging
from datetime import timedelta

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def check_daily_budget_caps():
    """Pause campaigns that have exceeded their merchant's daily budget."""
    from django.db.models import Sum
    from django.utils import timezone
    from apps.merchants.models import MerchantProfile
    from apps.campaigns.models import Campaign
    from .models import ConversionEvent

    today = timezone.now().date()

    for merchant in MerchantProfile.objects.filter(status=MerchantProfile.Status.APPROVED):
        daily_spend = ConversionEvent.objects.filter(
            merchant=merchant,
            converted_at__date=today,
            is_valid=True,
        ).aggregate(total=Sum('commission_amount'))['total'] or 0

        if daily_spend >= merchant.daily_budget_cap:
            paused = Campaign.objects.filter(
                merchant=merchant,
                status=Campaign.Status.ACTIVE,
            ).update(status=Campaign.Status.PAUSED)
            if paused:
                logger.info(
                    f"Paused {paused} campaigns for merchant {merchant.id} "
                    f"(budget: {merchant.daily_budget_cap}, spent: {daily_spend})"
                )


@shared_task
def generate_invoices():
    """Generate weekly invoices for all active merchants."""
    from django.utils import timezone
    from django.db.models import Sum, Count
    from apps.merchants.models import MerchantProfile
    from apps.tracking.models import ClickEvent
    from .models import ConversionEvent, Invoice, InvoiceLine
    from .razorpay_client import create_invoice as razorpay_create_invoice

    today = timezone.now().date()
    period_start = today - timedelta(days=7)
    period_end = today - timedelta(days=1)

    for merchant in MerchantProfile.objects.filter(status=MerchantProfile.Status.APPROVED):
        # Aggregate conversions
        conversions = ConversionEvent.objects.filter(
            merchant=merchant,
            converted_at__date__gte=period_start,
            converted_at__date__lte=period_end,
            is_valid=True,
            is_disputed=False,
        )

        total_commission = conversions.aggregate(total=Sum('commission_amount'))['total'] or 0
        conv_count = conversions.count()

        if total_commission == 0:
            continue

        # Generate invoice number
        invoice_number = f"SC-{merchant.id}-{today.strftime('%Y%m%d')}"

        invoice = Invoice.objects.create(
            merchant=merchant,
            invoice_number=invoice_number,
            period_start=period_start,
            period_end=period_end,
            total_conversions=conv_count,
            subtotal=total_commission,
            total=total_commission,
            due_date=today + timedelta(days=30),
        )

        # Create line items
        for conv in conversions:
            InvoiceLine.objects.create(
                invoice=invoice,
                conversion_event=conv,
                description=f"Conversion {conv.order_id}",
                billing_type='cpa',
                quantity=1,
                unit_price=conv.commission_amount,
                line_total=conv.commission_amount,
            )

        # Create Razorpay invoice if merchant has Razorpay customer
        if merchant.razorpay_customer_id:
            try:
                rzp_invoice = razorpay_create_invoice(merchant, [{
                    'amount': float(total_commission),
                    'description': f"SalesCount - {period_start} to {period_end} ({conv_count} conversions)",
                }])
                invoice.razorpay_invoice_id = rzp_invoice['id']
                invoice.status = Invoice.Status.SENT
                invoice.save()
            except Exception as e:
                logger.error(f"Razorpay invoice creation failed for merchant {merchant.id}: {e}")

        logger.info(f"Generated invoice {invoice_number} for merchant {merchant.id}: {total_commission}")
