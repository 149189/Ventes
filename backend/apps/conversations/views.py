import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdminOrMerchant
from .models import Conversation, Message
from .serializers import ConversationListSerializer, ConversationDetailSerializer

logger = logging.getLogger(__name__)


def _validate_twilio_signature(request) -> bool:
    """Validate that the request genuinely comes from Twilio."""
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        signature = request.META.get('HTTP_X_TWILIO_SIGNATURE', '')
        url = request.build_absolute_uri()
        return validator.validate(url, request.POST, signature)
    except ImportError:
        logger.warning("twilio package not installed — skipping signature validation")
        return True
    except Exception as e:
        logger.error(f"Twilio signature validation error: {e}")
        return False


@method_decorator(csrf_exempt, name='dispatch')
class TwilioWebhookView(APIView):
    """Receive inbound WhatsApp messages from Twilio."""
    permission_classes = (permissions.AllowAny,)
    authentication_classes = []

    def post(self, request):
        # Validate Twilio signature
        if not settings.DEBUG and not _validate_twilio_signature(request):
            logger.warning("Invalid Twilio signature — rejecting webhook")
            return HttpResponse(status=403)

        phone_number = request.POST.get('From', '')
        body = request.POST.get('Body', '')
        twilio_sid = request.POST.get('MessageSid', '')
        media_url = request.POST.get('MediaUrl0', '')

        if not phone_number or not body:
            return HttpResponse(status=400)

        # Deduplicate by MessageSid
        if twilio_sid and Message.objects.filter(twilio_sid=twilio_sid).exists():
            logger.info(f"Duplicate MessageSid {twilio_sid} — skipping")
            return HttpResponse(
                '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                content_type='text/xml',
            )

        # Process the message synchronously so we can return the reply in TwiML.
        # This avoids Twilio error 63015 (session window expired) by piggybacking
        # the response on the inbound webhook instead of a separate API call.
        from .tasks import process_inbound_message_sync
        reply = ''
        try:
            reply = process_inbound_message_sync(
                phone_number=phone_number,
                body=body,
                twilio_sid=twilio_sid,
                media_url=media_url,
            )
        except Exception as e:
            logger.error(f"Message processing failed: {e}")

        # Return reply in TwiML — Twilio delivers this within the active session
        if reply:
            from xml.sax.saxutils import escape
            twiml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                f'<Response><Message>{escape(reply)}</Message></Response>'
            )
        else:
            twiml = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'

        return HttpResponse(twiml, content_type='text/xml')


@method_decorator(csrf_exempt, name='dispatch')
class TwilioStatusCallbackView(APIView):
    """Receive message delivery status from Twilio."""
    permission_classes = (permissions.AllowAny,)
    authentication_classes = []

    def post(self, request):
        message_sid = request.POST.get('MessageSid', '')
        message_status = request.POST.get('MessageStatus', '')
        logger.info(f"Twilio status: {message_sid} -> {message_status}")
        return HttpResponse(status=200)


class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationListSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrMerchant)
    filterset_fields = ('stage', 'is_opted_out', 'merchant')
    search_fields = ('phone_number',)
    ordering_fields = ('started_at', 'last_message_at')
    ordering = ('-last_message_at',)

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Conversation.objects.all()
        return Conversation.objects.filter(merchant=user.merchant_profile)


class ConversationDetailView(generics.RetrieveAPIView):
    serializer_class = ConversationDetailSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdminOrMerchant)

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Conversation.objects.all()
        return Conversation.objects.filter(merchant=user.merchant_profile)


class HandoffView(APIView):
    """Route conversation to a human agent."""
    permission_classes = (permissions.IsAuthenticated, IsAdminOrMerchant)

    def post(self, request, pk):
        try:
            conversation = Conversation.objects.get(pk=pk)
        except Conversation.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        conversation.stage = Conversation.Stage.HANDED_OFF
        conversation.handed_off_to = request.user
        conversation.save()
        return Response({'status': 'handed_off'})


class AgentReplyView(APIView):
    """Human agent sends a message in a handed-off conversation."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        try:
            conversation = Conversation.objects.get(pk=pk, stage=Conversation.Stage.HANDED_OFF)
        except Conversation.DoesNotExist:
            return Response({'error': 'Not found or not in handoff'}, status=status.HTTP_404_NOT_FOUND)

        body = request.data.get('body', '')
        if not body:
            return Response({'error': 'Message body required'}, status=status.HTTP_400_BAD_REQUEST)

        # Save agent message
        message = Message.objects.create(
            conversation=conversation,
            direction=Message.Direction.AGENT,
            body=body,
            stage_at_send=conversation.stage,
        )

        # Send via Twilio
        from .tasks import send_whatsapp_message
        send_whatsapp_message.delay(
            phone_number=conversation.phone_number,
            body=body,
        )

        return Response({'status': 'sent', 'message_id': message.id})


class SimulateChatView(APIView):
    """Test the bot engine without Twilio/Celery. DEBUG mode only.

    POST /api/v1/conversations/simulate/
    {
        "phone_number": "+1234567890",   (optional, defaults to test number)
        "message": "Hi there!",
        "use_openai": false              (optional, defaults to false — uses mock AI)
    }

    Returns the bot response synchronously.
    """
    permission_classes = (permissions.AllowAny,)
    authentication_classes = []

    def post(self, request):
        if not settings.DEBUG:
            return Response(
                {'error': 'Simulation endpoint is only available in DEBUG mode'},
                status=status.HTTP_403_FORBIDDEN,
            )

        phone_number = request.data.get('phone_number', 'whatsapp:+0000000000')
        message_body = request.data.get('message', '')
        use_openai = request.data.get('use_openai', False)

        if not message_body:
            return Response({'error': 'message is required'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.merchants.models import MerchantProfile
        from apps.campaigns.models import Campaign

        # Find or create conversation
        conversation = Conversation.objects.filter(
            phone_number=phone_number,
            ended_at__isnull=True,
        ).first()

        if not conversation:
            merchant = MerchantProfile.objects.filter(
                status=MerchantProfile.Status.APPROVED,
            ).first()

            if not merchant:
                return Response(
                    {'error': 'No approved merchant. Run the seed script or create one in admin.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            campaign = Campaign.objects.filter(
                merchant=merchant,
                status=Campaign.Status.ACTIVE,
            ).first()

            conversation = Conversation.objects.create(
                phone_number=phone_number,
                merchant=merchant,
                campaign=campaign,
            )

            # Assign A/B variant
            from .bot.ab_testing import assign_variant
            assign_variant(conversation)

        # Save inbound message
        Message.objects.create(
            conversation=conversation,
            direction=Message.Direction.INBOUND,
            body=message_body,
            stage_at_send=conversation.stage,
        )

        # Check opt-out
        if message_body.strip().upper() in ('STOP', 'UNSUBSCRIBE', 'QUIT'):
            conversation.is_opted_out = True
            conversation.stage = Conversation.Stage.ENDED
            conversation.save()
            return Response({
                'response': "You've been opted out. Reply START to re-subscribe.",
                'conversation_id': conversation.id,
                'stage': conversation.stage,
            })

        # Process through engine
        if use_openai:
            from .bot.engine import ConversationEngine
            engine = ConversationEngine(conversation)
            bot_response, tokens_used = engine.process_message(message_body)
        else:
            # Mock AI response for testing without API keys
            bot_response, tokens_used = self._mock_response(conversation, message_body)

        # Save outbound message
        Message.objects.create(
            conversation=conversation,
            direction=Message.Direction.OUTBOUND,
            body=bot_response,
            stage_at_send=conversation.stage,
            openai_tokens_used=tokens_used,
        )

        # Get all messages for context
        messages = list(
            conversation.messages.order_by('created_at').values(
                'direction', 'body', 'stage_at_send', 'created_at',
            )
        )

        return Response({
            'response': bot_response,
            'conversation_id': conversation.id,
            'stage': conversation.stage,
            'stage_display': conversation.get_stage_display(),
            'coupon_code': conversation.coupon_code,
            'tokens_used': tokens_used,
            'message_count': len(messages),
            'messages': messages,
        })

    def _mock_response(self, conversation, user_message):
        """Generate a mock bot response for testing without OpenAI."""
        from .bot.engine import ConversationEngine

        engine = ConversationEngine(conversation)
        intent = engine._classify_intent(user_message)
        next_stage = engine._determine_next_stage(intent)

        # Handle handoff
        if intent == 'human_handoff':
            conversation.stage = Conversation.Stage.HANDED_OFF
            conversation.save()
            return "Let me connect you with a team member. Someone will be with you shortly!", 0

        conversation.stage = next_stage
        engine._update_context(user_message, intent)
        conversation.save()

        # Generate stage-appropriate mock responses
        stage_responses = {
            Conversation.Stage.QUALIFYING: (
                "Great to hear from you! What kind of products are you looking for today? "
                "We have some amazing options."
            ),
            Conversation.Stage.NARROWING: (
                "I have a few options that might be perfect for you. "
                "Are you looking for something specific in terms of price range or features?"
            ),
            Conversation.Stage.PITCHING: (
                "Check out this product — it's one of our best sellers! "
                "[product_link:1] Great quality and currently on sale."
            ),
            Conversation.Stage.CLOSING: (
                "Excellent choice! Here's a special discount code just for you. "
                "Ready to place your order?"
            ),
            Conversation.Stage.OBJECTION_HANDLING: (
                "I completely understand your concern. Let me address that — "
                "we offer free returns within 30 days, so there's no risk."
            ),
            Conversation.Stage.ENDED: "Thank you for your purchase! Enjoy your products.",
        }

        response = stage_responses.get(
            next_stage,
            "Welcome! I'm here to help you find the perfect product. What are you interested in?",
        )

        # Inject tracking URLs if applicable
        if next_stage in (Conversation.Stage.PITCHING, Conversation.Stage.CLOSING):
            from .bot.techniques import inject_tracking_urls, generate_coupon_code
            response = inject_tracking_urls(response, conversation)
            if next_stage == Conversation.Stage.CLOSING and not conversation.coupon_code:
                coupon = generate_coupon_code(conversation)
                if coupon:
                    conversation.coupon_code = coupon
                    conversation.save()
                    response += f"\n\nUse code: {coupon}"

        if next_stage == Conversation.Stage.ENDED:
            from django.utils import timezone
            conversation.ended_at = timezone.now()
            conversation.save()
            from .bot.ab_testing import record_conversion
            record_conversion(conversation)

        return response, 0
