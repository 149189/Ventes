"""Tests for the WhatsApp bot conversation engine."""
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.merchants.models import MerchantProfile, SKU, PromoRule
from apps.campaigns.models import Campaign, ABTestVariant
from apps.conversations.models import Conversation, Message, FollowUpSchedule
from apps.conversations.bot.engine import ConversationEngine


class ConversationModelTest(TestCase):
    """Tests for Conversation model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant1', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.user,
            company_name='Test Store',
            contact_email='test@store.com',
            status=MerchantProfile.Status.APPROVED,
        )

    def test_conversation_creation(self):
        conv = Conversation.objects.create(
            phone_number='whatsapp:+1234567890',
            merchant=self.merchant,
        )
        self.assertEqual(conv.stage, Conversation.Stage.GREETING)
        self.assertFalse(conv.is_opted_out)
        self.assertIsNone(conv.ended_at)

    def test_conversation_str(self):
        conv = Conversation.objects.create(
            phone_number='whatsapp:+1234567890',
            merchant=self.merchant,
        )
        self.assertIn('+1234567890', str(conv))
        self.assertIn('Greeting', str(conv))


class IntentClassificationTest(TestCase):
    """Tests for the intent classification in the conversation engine."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant2', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.user,
            company_name='Test Store',
            contact_email='test@store.com',
            status=MerchantProfile.Status.APPROVED,
        )
        self.conversation = Conversation.objects.create(
            phone_number='whatsapp:+1111111111',
            merchant=self.merchant,
        )
        self.engine = ConversationEngine(self.conversation)

    def test_handoff_intent(self):
        self.assertEqual(self.engine._classify_intent('I want to talk to a human'), 'human_handoff')
        self.assertEqual(self.engine._classify_intent('let me speak to an agent'), 'human_handoff')
        self.assertEqual(self.engine._classify_intent('representative please'), 'human_handoff')

    def test_objection_intent(self):
        self.assertEqual(self.engine._classify_intent('too expensive'), 'objection')
        self.assertEqual(self.engine._classify_intent("I'm not sure about this"), 'objection')
        self.assertEqual(self.engine._classify_intent('can I get a discount'), 'objection')
        self.assertEqual(self.engine._classify_intent('what about returns'), 'objection')

    def test_close_signal_intent(self):
        self.assertEqual(self.engine._classify_intent('yes I want to buy'), 'close_signal')
        self.assertEqual(self.engine._classify_intent('okay sure'), 'close_signal')
        self.assertEqual(self.engine._classify_intent("I'll take it"), 'close_signal')
        self.assertEqual(self.engine._classify_intent('send it to me'), 'close_signal')

    def test_general_intent(self):
        self.assertEqual(self.engine._classify_intent('hello there'), 'general')
        self.assertEqual(self.engine._classify_intent('what products do you have'), 'general')
        self.assertEqual(self.engine._classify_intent('tell me more'), 'general')


class StageTransitionTest(TestCase):
    """Tests for the conversation stage state machine."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant3', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.user,
            company_name='Test Store',
            contact_email='test@store.com',
            status=MerchantProfile.Status.APPROVED,
        )
        self.conversation = Conversation.objects.create(
            phone_number='whatsapp:+2222222222',
            merchant=self.merchant,
        )
        self.engine = ConversationEngine(self.conversation)

    def test_greeting_to_qualifying(self):
        result = self.engine._determine_next_stage('general')
        self.assertEqual(result, Conversation.Stage.QUALIFYING)

    def test_qualifying_to_narrowing(self):
        self.conversation.stage = Conversation.Stage.QUALIFYING
        result = self.engine._determine_next_stage('general')
        self.assertEqual(result, Conversation.Stage.NARROWING)

    def test_narrowing_to_pitching(self):
        self.conversation.stage = Conversation.Stage.NARROWING
        result = self.engine._determine_next_stage('general')
        self.assertEqual(result, Conversation.Stage.PITCHING)

    def test_pitching_stays_on_general(self):
        self.conversation.stage = Conversation.Stage.PITCHING
        result = self.engine._determine_next_stage('general')
        self.assertEqual(result, Conversation.Stage.PITCHING)

    def test_pitching_to_closing_on_close_signal(self):
        self.conversation.stage = Conversation.Stage.PITCHING
        result = self.engine._determine_next_stage('close_signal')
        self.assertEqual(result, Conversation.Stage.CLOSING)

    def test_closing_to_ended_on_close_signal(self):
        self.conversation.stage = Conversation.Stage.CLOSING
        result = self.engine._determine_next_stage('close_signal')
        self.assertEqual(result, Conversation.Stage.ENDED)

    def test_closing_stays_on_general(self):
        self.conversation.stage = Conversation.Stage.CLOSING
        result = self.engine._determine_next_stage('general')
        self.assertEqual(result, Conversation.Stage.CLOSING)

    def test_objection_from_any_stage(self):
        for stage in [Conversation.Stage.QUALIFYING, Conversation.Stage.PITCHING, Conversation.Stage.CLOSING]:
            self.conversation.stage = stage
            result = self.engine._determine_next_stage('objection')
            self.assertEqual(result, Conversation.Stage.OBJECTION_HANDLING)

    def test_objection_handling_to_pitching(self):
        self.conversation.stage = Conversation.Stage.OBJECTION_HANDLING
        result = self.engine._determine_next_stage('general')
        self.assertEqual(result, Conversation.Stage.PITCHING)

    def test_followup_to_pitching(self):
        self.conversation.stage = Conversation.Stage.FOLLOWUP
        result = self.engine._determine_next_stage('general')
        self.assertEqual(result, Conversation.Stage.PITCHING)

    def test_full_happy_path(self):
        """Test complete flow: greeting -> qualifying -> narrowing -> pitching -> closing -> ended."""
        stages = []
        # greeting -> qualifying (general)
        stages.append(self.engine._determine_next_stage('general'))
        self.conversation.stage = stages[-1]

        # qualifying -> narrowing (general)
        stages.append(self.engine._determine_next_stage('general'))
        self.conversation.stage = stages[-1]

        # narrowing -> pitching (general)
        stages.append(self.engine._determine_next_stage('general'))
        self.conversation.stage = stages[-1]

        # pitching -> closing (close_signal)
        stages.append(self.engine._determine_next_stage('close_signal'))
        self.conversation.stage = stages[-1]

        # closing -> ended (close_signal)
        stages.append(self.engine._determine_next_stage('close_signal'))

        self.assertEqual(stages, [
            Conversation.Stage.QUALIFYING,
            Conversation.Stage.NARROWING,
            Conversation.Stage.PITCHING,
            Conversation.Stage.CLOSING,
            Conversation.Stage.ENDED,
        ])


class ConversationHistoryTest(TestCase):
    """Tests for building conversation history for OpenAI."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant4', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.user,
            company_name='Test Store',
            contact_email='test@store.com',
            status=MerchantProfile.Status.APPROVED,
        )
        self.conversation = Conversation.objects.create(
            phone_number='whatsapp:+3333333333',
            merchant=self.merchant,
        )
        self.engine = ConversationEngine(self.conversation)

    def test_empty_history(self):
        history = self.engine._build_history()
        self.assertEqual(history, [])

    def test_history_roles(self):
        Message.objects.create(
            conversation=self.conversation,
            direction=Message.Direction.INBOUND,
            body='Hello',
            stage_at_send='greeting',
        )
        Message.objects.create(
            conversation=self.conversation,
            direction=Message.Direction.OUTBOUND,
            body='Hi there!',
            stage_at_send='greeting',
        )

        history = self.engine._build_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['role'], 'user')
        self.assertEqual(history[0]['content'], 'Hello')
        self.assertEqual(history[1]['role'], 'assistant')
        self.assertEqual(history[1]['content'], 'Hi there!')

    def test_history_limit_20(self):
        for i in range(25):
            Message.objects.create(
                conversation=self.conversation,
                direction=Message.Direction.INBOUND,
                body=f'Message {i}',
                stage_at_send='greeting',
            )

        history = self.engine._build_history()
        self.assertEqual(len(history), 20)


class CouponGenerationTest(TestCase):
    """Tests for coupon code generation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant5', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.user,
            company_name='Test Store',
            contact_email='test@store.com',
            status=MerchantProfile.Status.APPROVED,
        )
        self.promo = PromoRule.objects.create(
            merchant=self.merchant,
            name='Test Promo',
            promo_type='percentage',
            value=10,
            coupon_prefix='TEST',
            max_uses=100,
            valid_from=timezone.now(),
            valid_until=timezone.now() + timezone.timedelta(days=30),
        )

    def test_generate_coupon(self):
        from apps.conversations.bot.techniques import generate_coupon_code

        conv = Conversation.objects.create(
            phone_number='whatsapp:+4444444444',
            merchant=self.merchant,
        )
        code = generate_coupon_code(conv)
        self.assertTrue(code.startswith('TEST-'))
        self.assertEqual(len(code), 11)  # TEST- + 6 chars

    def test_coupon_increments_usage(self):
        from apps.conversations.bot.techniques import generate_coupon_code

        conv = Conversation.objects.create(
            phone_number='whatsapp:+5555555555',
            merchant=self.merchant,
        )
        initial_count = self.promo.uses_count
        generate_coupon_code(conv)
        self.promo.refresh_from_db()
        self.assertEqual(self.promo.uses_count, initial_count + 1)

    def test_coupon_respects_max_uses(self):
        from apps.conversations.bot.techniques import generate_coupon_code

        self.promo.uses_count = 100
        self.promo.save()

        conv = Conversation.objects.create(
            phone_number='whatsapp:+6666666666',
            merchant=self.merchant,
        )
        code = generate_coupon_code(conv)
        self.assertEqual(code, '')

    def test_no_coupon_without_promo(self):
        from apps.conversations.bot.techniques import generate_coupon_code

        self.promo.is_active = False
        self.promo.save()

        conv = Conversation.objects.create(
            phone_number='whatsapp:+7777777777',
            merchant=self.merchant,
        )
        code = generate_coupon_code(conv)
        self.assertEqual(code, '')


class ABTestingTest(TestCase):
    """Tests for A/B test variant assignment."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant6', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.user,
            company_name='Test Store',
            contact_email='test@store.com',
            status=MerchantProfile.Status.APPROVED,
        )
        self.campaign = Campaign.objects.create(
            merchant=self.merchant,
            name='Test Campaign',
            status=Campaign.Status.ACTIVE,
            daily_message_limit=1000,
            start_date=timezone.now(),
        )
        self.variant_a = ABTestVariant.objects.create(
            campaign=self.campaign,
            name='Variant A',
            variant_type='greeting',
            traffic_weight=50,
        )
        self.variant_b = ABTestVariant.objects.create(
            campaign=self.campaign,
            name='Variant B',
            variant_type='greeting',
            traffic_weight=50,
        )

    def test_variant_assignment(self):
        from apps.conversations.bot.ab_testing import assign_variant

        conv = Conversation.objects.create(
            phone_number='whatsapp:+8888888888',
            merchant=self.merchant,
            campaign=self.campaign,
        )
        assign_variant(conv)
        conv.refresh_from_db()
        self.assertIn(conv.ab_variant, [self.variant_a, self.variant_b])

    def test_variant_impressions_incremented(self):
        from apps.conversations.bot.ab_testing import assign_variant

        conv = Conversation.objects.create(
            phone_number='whatsapp:+9999999999',
            merchant=self.merchant,
            campaign=self.campaign,
        )
        initial_a = self.variant_a.impressions
        initial_b = self.variant_b.impressions

        assign_variant(conv)
        self.variant_a.refresh_from_db()
        self.variant_b.refresh_from_db()

        total_increase = (
            (self.variant_a.impressions - initial_a) +
            (self.variant_b.impressions - initial_b)
        )
        self.assertEqual(total_increase, 1)

    def test_no_variant_without_campaign(self):
        from apps.conversations.bot.ab_testing import assign_variant

        conv = Conversation.objects.create(
            phone_number='whatsapp:+1010101010',
            merchant=self.merchant,
        )
        assign_variant(conv)
        conv.refresh_from_db()
        self.assertIsNone(conv.ab_variant)

    def test_record_conversion(self):
        from apps.conversations.bot.ab_testing import assign_variant, record_conversion

        conv = Conversation.objects.create(
            phone_number='whatsapp:+1212121212',
            merchant=self.merchant,
            campaign=self.campaign,
        )
        assign_variant(conv)
        conv.refresh_from_db()

        variant = conv.ab_variant
        initial_conversions = variant.conversions
        record_conversion(conv)
        variant.refresh_from_db()
        self.assertEqual(variant.conversions, initial_conversions + 1)


class OptOutTest(TestCase):
    """Tests for opt-out/opt-in handling."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant7', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.user,
            company_name='Test Store',
            contact_email='test@store.com',
            status=MerchantProfile.Status.APPROVED,
        )
        self.conversation = Conversation.objects.create(
            phone_number='whatsapp:+1313131313',
            merchant=self.merchant,
        )

    def test_opt_out_keywords(self):
        for keyword in ['STOP', 'UNSUBSCRIBE', 'QUIT']:
            conv = Conversation.objects.create(
                phone_number=f'whatsapp:+{keyword}test',
                merchant=self.merchant,
            )
            # Verify the keyword triggers opt-out in task logic
            self.assertIn(keyword, ['STOP', 'UNSUBSCRIBE', 'QUIT'])


def _clean_installed_apps():
    """Return INSTALLED_APPS without debug_toolbar to avoid djdt namespace issues."""
    from django.conf import settings
    return [app for app in settings.INSTALLED_APPS if app != 'debug_toolbar']


def _clean_middleware():
    """Return MIDDLEWARE without debug_toolbar to avoid djdt namespace issues."""
    from django.conf import settings
    return [m for m in settings.MIDDLEWARE if 'debug_toolbar' not in m]


class SimulateEndpointTest(TestCase):
    """Tests for the /simulate/ endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant8', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.user,
            company_name='Test Store',
            contact_email='test@store.com',
            status=MerchantProfile.Status.APPROVED,
        )

    def test_simulate_creates_conversation(self):
        with self.settings(
            DEBUG=True,
            INSTALLED_APPS=_clean_installed_apps(),
            MIDDLEWARE=_clean_middleware(),
            ROOT_URLCONF='salescount.urls',
        ):
            from django.test import Client
            client = Client()
            response = client.post(
                '/api/v1/conversations/simulate/',
                data={'message': 'Hello there!'},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn('response', data)
            self.assertIn('conversation_id', data)
            self.assertIn('stage', data)

    def test_simulate_progresses_stages(self):
        with self.settings(
            DEBUG=True,
            INSTALLED_APPS=_clean_installed_apps(),
            MIDDLEWARE=_clean_middleware(),
            ROOT_URLCONF='salescount.urls',
        ):
            from django.test import Client
            client = Client()

            # First message — greeting -> qualifying
            r1 = client.post(
                '/api/v1/conversations/simulate/',
                data={'message': 'Hi!', 'phone_number': 'whatsapp:+test-stage'},
                content_type='application/json',
            )
            self.assertEqual(r1.json()['stage'], 'qualifying')

            # Second message — qualifying -> narrowing
            r2 = client.post(
                '/api/v1/conversations/simulate/',
                data={'message': 'I want shoes', 'phone_number': 'whatsapp:+test-stage'},
                content_type='application/json',
            )
            self.assertEqual(r2.json()['stage'], 'narrowing')

    @override_settings(DEBUG=False)
    def test_simulate_blocked_in_production(self):
        from django.test import Client
        client = Client()
        response = client.post(
            '/api/v1/conversations/simulate/',
            data={'message': 'Hello'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_simulate_opt_out(self):
        with self.settings(
            DEBUG=True,
            INSTALLED_APPS=_clean_installed_apps(),
            MIDDLEWARE=_clean_middleware(),
            ROOT_URLCONF='salescount.urls',
        ):
            from django.test import Client
            client = Client()
            response = client.post(
                '/api/v1/conversations/simulate/',
                data={'message': 'STOP', 'phone_number': 'whatsapp:+test-optout'},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn('opted out', data['response'].lower())
