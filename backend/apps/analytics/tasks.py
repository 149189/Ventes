import logging
from datetime import timedelta

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def aggregate_hourly_stats():
    """Compute hourly click stats for near-real-time dashboards."""
    from django.utils import timezone
    from apps.tracking.models import ClickEvent
    from apps.merchants.models import MerchantProfile
    from .models import HourlyClickStats

    now = timezone.now()
    current_hour = now.replace(minute=0, second=0, microsecond=0)

    for merchant in MerchantProfile.objects.filter(status=MerchantProfile.Status.APPROVED):
        clicks = ClickEvent.objects.filter(
            redirect_token__merchant=merchant,
            clicked_at__gte=current_hour,
            clicked_at__lt=current_hour + timedelta(hours=1),
        )

        total = clicks.count()
        valid = clicks.filter(is_fraudulent=False).count()

        HourlyClickStats.objects.update_or_create(
            merchant=merchant,
            hour=current_hour,
            defaults={'clicks': total, 'valid_clicks': valid},
        )


@shared_task
def aggregate_daily_stats():
    """Compute daily merchant and campaign stats."""
    from django.utils import timezone
    from django.db.models import Sum
    from apps.merchants.models import MerchantProfile
    from apps.campaigns.models import Campaign
    from apps.conversations.models import Conversation, Message
    from apps.tracking.models import ClickEvent
    from apps.billing.models import ConversionEvent
    from .models import DailyMerchantStats, DailyCampaignStats

    yesterday = (timezone.now() - timedelta(days=1)).date()

    for merchant in MerchantProfile.objects.filter(status=MerchantProfile.Status.APPROVED):
        convos = Conversation.objects.filter(merchant=merchant, started_at__date=yesterday)
        clicks = ClickEvent.objects.filter(
            redirect_token__merchant=merchant, clicked_at__date=yesterday,
        )
        conversions = ConversionEvent.objects.filter(
            merchant=merchant, converted_at__date=yesterday, is_valid=True,
        )

        total_clicks = clicks.count()
        valid_clicks = clicks.filter(is_fraudulent=False).count()
        total_conversions = conversions.count()
        revenue = conversions.aggregate(t=Sum('order_amount'))['t'] or 0
        spend = conversions.aggregate(t=Sum('commission_amount'))['t'] or 0
        messages = Message.objects.filter(
            conversation__merchant=merchant,
            created_at__date=yesterday,
            direction='outbound',
        ).count()

        DailyMerchantStats.objects.update_or_create(
            merchant=merchant,
            date=yesterday,
            defaults={
                'conversations_started': convos.count(),
                'conversations_converted': convos.filter(
                    stage=Conversation.Stage.ENDED,
                ).count(),
                'messages_sent': messages,
                'clicks_total': total_clicks,
                'clicks_valid': valid_clicks,
                'clicks_fraudulent': total_clicks - valid_clicks,
                'conversions': total_conversions,
                'revenue_gross': revenue,
                'spend': spend,
                'ctr': (valid_clicks / messages * 100) if messages > 0 else 0,
                'conversion_rate': (total_conversions / valid_clicks * 100) if valid_clicks > 0 else 0,
            },
        )

    # Campaign stats
    for campaign in Campaign.objects.filter(status__in=['active', 'paused', 'ended']):
        clicks = ClickEvent.objects.filter(
            redirect_token__campaign=campaign, clicked_at__date=yesterday,
        )
        conversions = ConversionEvent.objects.filter(
            click_event__redirect_token__campaign=campaign,
            converted_at__date=yesterday,
            is_valid=True,
        )
        messages = Message.objects.filter(
            conversation__campaign=campaign,
            created_at__date=yesterday,
            direction='outbound',
        ).count()

        total_clicks = clicks.count()
        total_conversions = conversions.count()
        spend = conversions.aggregate(t=Sum('commission_amount'))['t'] or 0

        DailyCampaignStats.objects.update_or_create(
            campaign=campaign,
            date=yesterday,
            defaults={
                'impressions': messages,
                'clicks': total_clicks,
                'conversions': total_conversions,
                'spend': spend,
                'ctr': (total_clicks / messages * 100) if messages > 0 else 0,
                'conversion_rate': (total_conversions / total_clicks * 100) if total_clicks > 0 else 0,
            },
        )

    logger.info(f"Daily stats aggregated for {yesterday}")


@shared_task
def update_merchant_tiers():
    """Monthly: recalculate merchant tiers based on volume."""
    from django.utils import timezone
    from django.db.models import Sum
    from apps.merchants.models import MerchantProfile
    from apps.billing.models import ConversionEvent

    last_month_start = (timezone.now().replace(day=1) - timedelta(days=1)).replace(day=1).date()
    last_month_end = (timezone.now().replace(day=1) - timedelta(days=1)).date()

    for merchant in MerchantProfile.objects.filter(status=MerchantProfile.Status.APPROVED):
        revenue = ConversionEvent.objects.filter(
            merchant=merchant,
            converted_at__date__gte=last_month_start,
            converted_at__date__lte=last_month_end,
            is_valid=True,
        ).aggregate(total=Sum('order_amount'))['total'] or 0

        # Tier thresholds
        if revenue >= 50000:
            new_tier = MerchantProfile.Tier.PLATINUM
        elif revenue >= 20000:
            new_tier = MerchantProfile.Tier.GOLD
        elif revenue >= 5000:
            new_tier = MerchantProfile.Tier.SILVER
        else:
            new_tier = MerchantProfile.Tier.BRONZE

        if merchant.tier != new_tier:
            merchant.tier = new_tier
            merchant.save(update_fields=['tier'])
            logger.info(f"Merchant {merchant.id} tier updated to {new_tier}")
