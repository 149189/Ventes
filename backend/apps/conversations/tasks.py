import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def process_inbound_message(phone_number, body, twilio_sid='', media_url=''):
    """Process an inbound WhatsApp message through the bot engine."""
    from .models import Conversation, Message
    from apps.merchants.models import MerchantProfile

    # Find or create conversation
    conversation = Conversation.objects.filter(
        phone_number=phone_number,
        ended_at__isnull=True,
    ).first()

    if not conversation:
        # Route to merchant by matching the WhatsApp number the message was sent TO
        # Fall back to first approved merchant if no match
        merchant = (
            MerchantProfile.objects.filter(
                status=MerchantProfile.Status.APPROVED,
                whatsapp_number__isnull=False,
            ).exclude(whatsapp_number='').first()
            or MerchantProfile.objects.filter(status=MerchantProfile.Status.APPROVED).first()
        )
        if not merchant:
            logger.error(f"No approved merchant found for {phone_number}")
            return

        # Find active campaign for this merchant
        from apps.campaigns.models import Campaign
        campaign = Campaign.objects.filter(
            merchant=merchant,
            status=Campaign.Status.ACTIVE,
        ).first()

        conversation = Conversation.objects.create(
            phone_number=phone_number,
            merchant=merchant,
            campaign=campaign,
        )

        # Assign A/B test variant for new conversations
        from .bot.ab_testing import assign_variant
        assign_variant(conversation)

    # Deduplicate by twilio_sid
    if twilio_sid and Message.objects.filter(twilio_sid=twilio_sid).exists():
        logger.info(f"Duplicate message {twilio_sid} — skipping")
        return

    # Save inbound message
    Message.objects.create(
        conversation=conversation,
        direction=Message.Direction.INBOUND,
        body=body,
        twilio_sid=twilio_sid,
        media_url=media_url,
        stage_at_send=conversation.stage,
    )

    # Check if conversation is handed off
    if conversation.stage == Conversation.Stage.HANDED_OFF:
        logger.info(f"Conversation {conversation.id} is handed off, skipping bot")
        return

    # Check opt-out
    if body.strip().upper() in ('STOP', 'UNSUBSCRIBE', 'QUIT'):
        conversation.is_opted_out = True
        conversation.stage = Conversation.Stage.ENDED
        conversation.save()
        send_whatsapp_message.delay(
            phone_number=phone_number,
            body="You've been opted out. Reply START to re-subscribe. Have a great day!",
        )
        return

    # Check re-subscribe
    if body.strip().upper() == 'START' and conversation.is_opted_out:
        conversation.is_opted_out = False
        conversation.stage = Conversation.Stage.GREETING
        conversation.save()
        send_whatsapp_message.delay(
            phone_number=phone_number,
            body="Welcome back! How can I help you today?",
        )
        return

    # Process through bot engine
    from .bot.engine import ConversationEngine
    engine = ConversationEngine(conversation)
    response, tokens_used = engine.process_message(body)

    # Save outbound message with token tracking
    Message.objects.create(
        conversation=conversation,
        direction=Message.Direction.OUTBOUND,
        body=response,
        stage_at_send=conversation.stage,
        openai_tokens_used=tokens_used,
    )

    # Record conversion if conversation reached ENDED after closing
    if conversation.stage == Conversation.Stage.ENDED:
        from .bot.ab_testing import record_conversion
        record_conversion(conversation)

    # Send via Twilio
    send_whatsapp_message.delay(
        phone_number=phone_number,
        body=response,
    )


def process_inbound_message_sync(phone_number, body, twilio_sid='', media_url=''):
    """Process an inbound message and return the reply text (no Twilio send).

    Used by the webhook view to return the reply in TwiML, avoiding
    the 63015 session-window error that occurs with separate API sends.
    """
    from .models import Conversation, Message
    from apps.merchants.models import MerchantProfile

    # Find or create conversation
    conversation = Conversation.objects.filter(
        phone_number=phone_number,
        ended_at__isnull=True,
    ).first()

    if not conversation:
        merchant = (
            MerchantProfile.objects.filter(
                status=MerchantProfile.Status.APPROVED,
                whatsapp_number__isnull=False,
            ).exclude(whatsapp_number='').first()
            or MerchantProfile.objects.filter(status=MerchantProfile.Status.APPROVED).first()
        )
        if not merchant:
            logger.error(f"No approved merchant found for {phone_number}")
            return ''

        from apps.campaigns.models import Campaign
        campaign = Campaign.objects.filter(
            merchant=merchant,
            status=Campaign.Status.ACTIVE,
        ).first()

        conversation = Conversation.objects.create(
            phone_number=phone_number,
            merchant=merchant,
            campaign=campaign,
        )

        from .bot.ab_testing import assign_variant
        assign_variant(conversation)

    # Deduplicate by twilio_sid
    if twilio_sid and Message.objects.filter(twilio_sid=twilio_sid).exists():
        logger.info(f"Duplicate message {twilio_sid} — skipping")
        return ''

    # Save inbound message
    Message.objects.create(
        conversation=conversation,
        direction=Message.Direction.INBOUND,
        body=body,
        twilio_sid=twilio_sid,
        media_url=media_url,
        stage_at_send=conversation.stage,
    )

    # Handed off — no bot reply
    if conversation.stage == Conversation.Stage.HANDED_OFF:
        logger.info(f"Conversation {conversation.id} is handed off, skipping bot")
        return ''

    # Opt-out
    if body.strip().upper() in ('STOP', 'UNSUBSCRIBE', 'QUIT'):
        conversation.is_opted_out = True
        conversation.stage = Conversation.Stage.ENDED
        conversation.save()
        return "You've been opted out. Reply START to re-subscribe. Have a great day!"

    # Re-subscribe
    if body.strip().upper() == 'START' and conversation.is_opted_out:
        conversation.is_opted_out = False
        conversation.stage = Conversation.Stage.GREETING
        conversation.save()
        return "Welcome back! How can I help you today?"

    # Process through bot engine
    from .bot.engine import ConversationEngine
    engine = ConversationEngine(conversation)
    response, tokens_used = engine.process_message(body)

    # Save outbound message
    Message.objects.create(
        conversation=conversation,
        direction=Message.Direction.OUTBOUND,
        body=response,
        stage_at_send=conversation.stage,
        openai_tokens_used=tokens_used,
    )

    if conversation.stage == Conversation.Stage.ENDED:
        from .bot.ab_testing import record_conversion
        record_conversion(conversation)

    return response


@shared_task
def send_whatsapp_message(phone_number, body):
    """Send a WhatsApp message via Twilio."""
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            from_=settings.TWILIO_WHATSAPP_FROM,
            to=phone_number,
            body=body,
        )
        logger.info(f"Sent WhatsApp message {message.sid} to {phone_number}")
        return message.sid
    except Exception as e:
        logger.error(f"Failed to send WhatsApp to {phone_number}: {e}")
        raise


@shared_task
def send_followup_reminder(conversation_id, followup_id):
    """Send a follow-up reminder message."""
    from .models import Conversation, FollowUpSchedule
    from django.utils import timezone

    try:
        followup = FollowUpSchedule.objects.get(id=followup_id, is_sent=False)
        conversation = followup.conversation
    except FollowUpSchedule.DoesNotExist:
        return

    if conversation.is_opted_out or conversation.stage == Conversation.Stage.ENDED:
        return

    send_whatsapp_message.delay(
        phone_number=conversation.phone_number,
        body=followup.message_template,
    )

    followup.is_sent = True
    followup.sent_at = timezone.now()
    followup.save()
