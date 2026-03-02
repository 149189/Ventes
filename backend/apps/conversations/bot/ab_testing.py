"""A/B testing variant selection for conversations."""
import random
import logging

logger = logging.getLogger(__name__)


def assign_variant(conversation) -> None:
    """Assign an A/B test variant to a conversation based on traffic weights."""
    if not conversation.campaign:
        return

    variants = list(
        conversation.campaign.ab_variants.filter(is_active=True)
    )

    if not variants:
        return

    # Weighted random selection
    total_weight = sum(v.traffic_weight for v in variants)
    if total_weight == 0:
        return

    rand = random.uniform(0, total_weight)
    cumulative = 0

    for variant in variants:
        cumulative += variant.traffic_weight
        if rand <= cumulative:
            conversation.ab_variant = variant
            variant.impressions += 1
            variant.save(update_fields=['impressions'])
            conversation.save(update_fields=['ab_variant'])
            logger.info(f"Assigned variant '{variant.name}' to conversation {conversation.id}")
            return


def record_conversion(conversation) -> None:
    """Record a conversion for the assigned A/B variant."""
    if conversation.ab_variant:
        variant = conversation.ab_variant
        variant.conversions += 1
        variant.save(update_fields=['conversions'])
        logger.info(f"Recorded conversion for variant '{variant.name}'")
