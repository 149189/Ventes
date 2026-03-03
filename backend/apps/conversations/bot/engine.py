import logging

from apps.conversations.models import Conversation, Message
from .rag import retrieve_relevant_products
from .openai_client import generate_response
from .prompts import get_prompt_for_stage
from .techniques import inject_tracking_urls, generate_coupon_code

logger = logging.getLogger(__name__)

# Intent keywords for classification
HANDOFF_KEYWORDS = {'human', 'agent', 'person', 'talk to someone', 'representative', 'help me'}
OBJECTION_KEYWORDS = {'expensive', 'too much', 'cheaper', 'discount', 'not sure', 'think about it', 'size', 'return'}
CLOSE_SIGNALS = {'yes', 'okay', 'sure', 'buy', 'order', 'checkout', 'link', 'send it', 'i want', "i'll take"}

# Stages that need product context (RAG + embedding API call).
# Greeting and qualifying should just chat — no products yet.
# Only these stages need product data (costs 1 embedding API call).
# Greeting, qualifying, narrowing just chat — no products, no API burn.
_PRODUCT_STAGES = {
    Conversation.Stage.PITCHING,
    Conversation.Stage.CLOSING,
    Conversation.Stage.OBJECTION_HANDLING,
}


class ConversationEngine:
    def __init__(self, conversation: Conversation):
        self.conversation = conversation

    def process_message(self, user_message: str) -> tuple[str, int]:
        """Process a user message and return (response, tokens_used)."""
        tokens_used = 0

        # 1. Classify intent
        intent = self._classify_intent(user_message)

        # 2. Handle special intents
        if intent == 'human_handoff':
            self.conversation.stage = Conversation.Stage.HANDED_OFF
            self.conversation.save()
            return ("Let me connect you with a team member. "
                    "Someone will be with you shortly!"), 0

        # 3. Determine next stage FIRST so we know whether to fetch products
        next_stage = self._determine_next_stage(intent)

        # 4. Only call RAG (embedding API) when the stage actually needs products.
        #    This saves the Gemini embedding quota for greeting/qualifying turns
        #    AND prevents the bot from pitching products prematurely.
        rag_context = ""
        matched_sku_ids = []
        if next_stage in _PRODUCT_STAGES:
            try:
                rag_context, matched_sku_ids = retrieve_relevant_products(
                    query=user_message,
                    merchant_id=self.conversation.merchant_id,
                )
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")

            # Store recommended SKUs
            if matched_sku_ids:
                self.conversation.recommended_skus.add(*matched_sku_ids)

        # 5. Get stage-appropriate system prompt
        system_prompt = get_prompt_for_stage(
            stage=self.conversation.stage,
            merchant_name=self.conversation.merchant.company_name,
            context=self.conversation.context_json,
        )

        # 6. Build conversation history
        history = self._build_history()

        # 7. Generate AI response
        try:
            response, tokens_used = generate_response(system_prompt, history, rag_context)
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            response = ("I'm having a moment! Let me connect you "
                        "with someone who can help.")
            self.conversation.stage = Conversation.Stage.HANDED_OFF
            self.conversation.save()
            return response, 0

        # 8. Apply the stage transition
        self.conversation.stage = next_stage

        # 9. Update conversation context
        self._update_context(user_message, intent)
        self.conversation.save()

        # 10. Inject tracking URLs if in pitching/closing
        if next_stage in (Conversation.Stage.PITCHING, Conversation.Stage.CLOSING):
            response = inject_tracking_urls(response, self.conversation)

            # Generate coupon if closing and no coupon yet
            if next_stage == Conversation.Stage.CLOSING and not self.conversation.coupon_code:
                coupon = generate_coupon_code(self.conversation)
                if coupon:
                    self.conversation.coupon_code = coupon
                    self.conversation.save()

        # 11. Schedule follow-ups if closing
        if next_stage == Conversation.Stage.CLOSING:
            self._schedule_followups()

        # 12. End conversation if ENDED
        if next_stage == Conversation.Stage.ENDED:
            from django.utils import timezone
            self.conversation.ended_at = timezone.now()
            self.conversation.save()

        return response, tokens_used

    def _classify_intent(self, message: str) -> str:
        msg_lower = message.lower().strip()

        if any(kw in msg_lower for kw in HANDOFF_KEYWORDS):
            return 'human_handoff'
        if any(kw in msg_lower for kw in OBJECTION_KEYWORDS):
            return 'objection'
        if any(kw in msg_lower for kw in CLOSE_SIGNALS):
            return 'close_signal'
        return 'general'

    def _determine_next_stage(self, intent: str) -> str:
        current = self.conversation.stage
        stage = Conversation.Stage

        if intent == 'objection':
            return stage.OBJECTION_HANDLING

        transitions = {
            stage.GREETING: stage.QUALIFYING,
            stage.QUALIFYING: stage.NARROWING,
            stage.NARROWING: stage.PITCHING,
            stage.PITCHING: stage.CLOSING if intent == 'close_signal' else stage.PITCHING,
            stage.CLOSING: stage.ENDED if intent == 'close_signal' else stage.CLOSING,
            stage.OBJECTION_HANDLING: stage.PITCHING,
            stage.FOLLOWUP: stage.PITCHING,
        }

        return transitions.get(current, current)

    def _build_history(self) -> list[dict]:
        messages = self.conversation.messages.order_by('-created_at', '-pk')[:20]
        history = []
        for msg in reversed(messages):
            role = 'user' if msg.direction == Message.Direction.INBOUND else 'assistant'
            history.append({'role': role, 'content': msg.body})
        return history

    def _update_context(self, user_message: str, intent: str):
        ctx = self.conversation.context_json or {}
        ctx['last_intent'] = intent
        ctx['message_count'] = ctx.get('message_count', 0) + 1
        self.conversation.context_json = ctx

    def _schedule_followups(self):
        from apps.conversations.models import FollowUpSchedule
        from apps.conversations.tasks import send_followup_reminder
        from django.utils import timezone
        from datetime import timedelta

        # Only schedule if none exist yet
        if self.conversation.followups.filter(is_sent=False).exists():
            return

        # 24-hour follow-up
        followup_24h = FollowUpSchedule.objects.create(
            conversation=self.conversation,
            scheduled_at=timezone.now() + timedelta(hours=24),
            message_template=(
                "Hi! Just checking in. Did you get a chance to check out the products "
                "we discussed? I'm here if you have any questions!"
            ),
        )
        send_followup_reminder.apply_async(
            args=[self.conversation.id, followup_24h.id],
            eta=followup_24h.scheduled_at,
        )

        # 3-day follow-up
        followup_3d = FollowUpSchedule.objects.create(
            conversation=self.conversation,
            scheduled_at=timezone.now() + timedelta(days=3),
            message_template=(
                "Hey there! We still have some great deals available. "
                "Would you like me to help you find the perfect product? "
                "Reply STOP to opt out."
            ),
        )
        send_followup_reminder.apply_async(
            args=[self.conversation.id, followup_3d.id],
            eta=followup_3d.scheduled_at,
        )
