"""HMAC-signed postback handling for conversion attribution."""
import logging

from django.utils import timezone

from common.hmac_utils import verify_hmac_signature, verify_timestamp_freshness
from common.exceptions import InvalidHMACSignature, StaleTimestamp
from apps.tracking.models import RedirectToken
from .models import ConversionEvent

logger = logging.getLogger(__name__)


def process_postback(validated_data: dict) -> ConversionEvent:
    """Process an HMAC-signed postback from a merchant."""
    token_uuid = validated_data['token']
    order_id = validated_data['order_id']
    order_amount = validated_data['order_amount']
    timestamp = validated_data['timestamp']
    signature = validated_data['hmac_signature']

    # Find redirect token
    try:
        redirect_token = RedirectToken.objects.select_related(
            'merchant', 'conversation', 'sku',
        ).get(token=token_uuid)
    except RedirectToken.DoesNotExist:
        raise InvalidHMACSignature("Token not found")

    merchant = redirect_token.merchant

    # Verify timestamp freshness (anti-replay)
    if not verify_timestamp_freshness(timestamp):
        raise StaleTimestamp()

    # Verify HMAC signature
    payload = {
        'token': str(token_uuid),
        'order_id': order_id,
        'order_amount': str(order_amount),
        'timestamp': str(timestamp),
    }
    if not verify_hmac_signature(merchant.hmac_secret, payload, signature):
        raise InvalidHMACSignature()

    # Get the click event
    click_event = redirect_token.clicks.order_by('-clicked_at').first()

    # Calculate commission
    commission = order_amount * (merchant.commission_rate / 100)

    # Create conversion event
    conversion = ConversionEvent.objects.create(
        click_event=click_event,
        conversation=redirect_token.conversation,
        merchant=merchant,
        source=ConversionEvent.Source.POSTBACK,
        order_id=order_id,
        order_amount=order_amount,
        commission_amount=commission,
        converted_at=timezone.now(),
    )

    # Update A/B test tracking
    from apps.conversations.bot.ab_testing import record_conversion
    if redirect_token.conversation:
        record_conversion(redirect_token.conversation)

    logger.info(f"Postback conversion: {order_id} for merchant {merchant.id}, commission ${commission}")
    return conversion
