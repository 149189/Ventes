"""Sales techniques — URL injection, coupon generation."""
import re
import uuid
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def inject_tracking_urls(response: str, conversation) -> str:
    """Replace [product_link:sku_id] placeholders with tracked redirect URLs."""
    from apps.tracking.models import RedirectToken
    from apps.merchants.models import SKU
    from django.utils import timezone
    from datetime import timedelta

    pattern = r'\[product_link:(\d+)\]'
    matches = re.findall(pattern, response)

    for sku_id in matches:
        try:
            sku = SKU.objects.get(id=int(sku_id))
            # Create redirect token
            token = RedirectToken.objects.create(
                conversation=conversation,
                sku=sku,
                merchant=conversation.merchant,
                campaign=conversation.campaign,
                destination_url=_build_destination_url(sku, conversation),
                expires_at=timezone.now() + timedelta(hours=settings.REDIRECT_TOKEN_EXPIRY_HOURS),
            )
            # Build tracked URL
            domain = getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000')
            tracked_url = f"{domain}/t/{token.token}/"
            response = response.replace(f"[product_link:{sku_id}]", tracked_url)

        except SKU.DoesNotExist:
            logger.warning(f"SKU {sku_id} not found for tracking URL")
            response = response.replace(f"[product_link:{sku_id}]", "#")

    return response


def _build_destination_url(sku, conversation) -> str:
    """Build destination URL with UTM parameters."""
    base_url = sku.landing_url
    separator = '&' if '?' in base_url else '?'
    utms = (
        f"utm_source=salescount"
        f"&utm_medium=whatsapp"
        f"&utm_campaign={conversation.campaign_id or 'direct'}"
        f"&utm_content={sku.sku_code}"
    )
    return f"{base_url}{separator}{utms}"


def generate_coupon_code(conversation) -> str:
    """Generate a unique coupon code for the conversation."""
    promo_rule = None
    if conversation.campaign and conversation.campaign.promo_rule:
        promo_rule = conversation.campaign.promo_rule

    if not promo_rule or not promo_rule.is_active:
        # Check if merchant has any active promo rules
        from apps.merchants.models import PromoRule
        from django.utils import timezone
        promo_rule = PromoRule.objects.filter(
            merchant=conversation.merchant,
            is_active=True,
            valid_from__lte=timezone.now(),
            valid_until__gte=timezone.now(),
        ).first()

    if not promo_rule:
        return ''

    # Check usage limits
    if promo_rule.max_uses > 0 and promo_rule.uses_count >= promo_rule.max_uses:
        return ''

    # Generate unique code
    short_id = uuid.uuid4().hex[:6].upper()
    code = f"{promo_rule.coupon_prefix}-{short_id}"

    promo_rule.uses_count += 1
    promo_rule.save(update_fields=['uses_count'])

    return code
