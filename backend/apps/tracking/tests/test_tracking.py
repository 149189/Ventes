"""Tests for click tracking, redirect system, and fraud detection."""
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, Client
from django.utils import timezone

from apps.accounts.models import User
from apps.merchants.models import MerchantProfile, SKU
from apps.campaigns.models import Campaign
from apps.conversations.models import Conversation
from apps.tracking.models import RedirectToken, ClickEvent, FraudFlag
from apps.tracking.fraud import FraudDetector


class RedirectTokenModelTest(TestCase):
    """Tests for RedirectToken model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant_track', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.user,
            company_name='Track Store',
            contact_email='track@store.com',
            status=MerchantProfile.Status.APPROVED,
        )
        self.sku = SKU.objects.create(
            merchant=self.merchant,
            name='Test Product',
            sku_code='TEST-001',
            description='A test product',
            category='Electronics',
            original_price=29.99,
            landing_url='https://example.com/product',
        )
        self.conversation = Conversation.objects.create(
            phone_number='whatsapp:+1111111111',
            merchant=self.merchant,
        )

    def test_create_redirect_token(self):
        token = RedirectToken.objects.create(
            conversation=self.conversation,
            sku=self.sku,
            merchant=self.merchant,
            destination_url='https://example.com/product?utm_source=salescount',
            expires_at=timezone.now() + timedelta(hours=72),
        )
        self.assertIsNotNone(token.token)
        self.assertTrue(token.is_active)
        self.assertEqual(str(token), f"Token {token.token} -> {self.sku.name}")

    def test_token_uuid_is_unique(self):
        t1 = RedirectToken.objects.create(
            conversation=self.conversation,
            sku=self.sku,
            merchant=self.merchant,
            destination_url='https://example.com/1',
            expires_at=timezone.now() + timedelta(hours=72),
        )
        t2 = RedirectToken.objects.create(
            conversation=self.conversation,
            sku=self.sku,
            merchant=self.merchant,
            destination_url='https://example.com/2',
            expires_at=timezone.now() + timedelta(hours=72),
        )
        self.assertNotEqual(t1.token, t2.token)


class RedirectViewTest(TestCase):
    """Tests for the /t/{uuid}/ redirect endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant_redir', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.user,
            company_name='Redirect Store',
            contact_email='redir@store.com',
            status=MerchantProfile.Status.APPROVED,
        )
        self.sku = SKU.objects.create(
            merchant=self.merchant,
            name='Redirect Product',
            sku_code='REDIR-001',
            description='A redirect product',
            category='Electronics',
            original_price=49.99,
            landing_url='https://merchant.com/product',
        )
        self.conversation = Conversation.objects.create(
            phone_number='whatsapp:+2222222222',
            merchant=self.merchant,
        )
        self.token = RedirectToken.objects.create(
            conversation=self.conversation,
            sku=self.sku,
            merchant=self.merchant,
            destination_url='https://merchant.com/product?utm_source=salescount',
            expires_at=timezone.now() + timedelta(hours=72),
        )
        self.client = Client()

    @patch('apps.tracking.tasks.calculate_fraud_score.delay')
    def test_redirect_302(self, mock_fraud):
        response = self.client.get(f'/t/{self.token.token}/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.token.destination_url)

    @patch('apps.tracking.tasks.calculate_fraud_score.delay')
    def test_redirect_creates_click_event(self, mock_fraud):
        self.client.get(
            f'/t/{self.token.token}/',
            HTTP_USER_AGENT='Mozilla/5.0',
            REMOTE_ADDR='203.0.113.1',
        )
        click = ClickEvent.objects.get(redirect_token=self.token)
        self.assertEqual(click.ip_address, '203.0.113.1')
        self.assertEqual(click.user_agent, 'Mozilla/5.0')

    @patch('apps.tracking.tasks.calculate_fraud_score.delay')
    def test_redirect_triggers_fraud_check(self, mock_fraud):
        self.client.get(f'/t/{self.token.token}/')
        click = ClickEvent.objects.get(redirect_token=self.token)
        mock_fraud.assert_called_once_with(click.id)

    def test_invalid_token_404(self):
        fake_token = uuid.uuid4()
        response = self.client.get(f'/t/{fake_token}/')
        self.assertEqual(response.status_code, 404)

    def test_inactive_token_410(self):
        self.token.is_active = False
        self.token.save()
        response = self.client.get(f'/t/{self.token.token}/')
        self.assertEqual(response.status_code, 410)

    def test_expired_token_410(self):
        self.token.expires_at = timezone.now() - timedelta(hours=1)
        self.token.save()
        response = self.client.get(f'/t/{self.token.token}/')
        self.assertEqual(response.status_code, 410)
        # Token should be deactivated
        self.token.refresh_from_db()
        self.assertFalse(self.token.is_active)

    @patch('apps.tracking.tasks.calculate_fraud_score.delay')
    def test_x_forwarded_for_ip(self, mock_fraud):
        self.client.get(
            f'/t/{self.token.token}/',
            HTTP_X_FORWARDED_FOR='198.51.100.1, 10.0.0.1',
        )
        click = ClickEvent.objects.get(redirect_token=self.token)
        self.assertEqual(click.ip_address, '198.51.100.1')


class FraudDetectorTest(TestCase):
    """Tests for the 5-layer fraud detection system."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant_fraud', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.user,
            company_name='Fraud Test Store',
            contact_email='fraud@store.com',
            status=MerchantProfile.Status.APPROVED,
        )
        self.sku = SKU.objects.create(
            merchant=self.merchant,
            name='Fraud Test Product',
            sku_code='FRAUD-001',
            description='A fraud test product',
            category='Electronics',
            original_price=19.99,
            landing_url='https://example.com/fraud-test',
        )
        self.conversation = Conversation.objects.create(
            phone_number='whatsapp:+3333333333',
            merchant=self.merchant,
        )
        self.token = RedirectToken.objects.create(
            conversation=self.conversation,
            sku=self.sku,
            merchant=self.merchant,
            destination_url='https://example.com/fraud-test',
            expires_at=timezone.now() + timedelta(hours=72),
        )

    def _create_click(self, ip='203.0.113.1', ua='Mozilla/5.0', token=None):
        return ClickEvent.objects.create(
            redirect_token=token or self.token,
            ip_address=ip,
            user_agent=ua,
        )

    def test_clean_click_no_flags(self):
        click = self._create_click()
        detector = FraudDetector(click)
        score, flags = detector.run_all_checks()
        self.assertEqual(score, 0.0)
        self.assertEqual(flags, [])

    def test_rate_limit_detection(self):
        """Layer 1: > 10 clicks per hour from same conversation triggers flag."""
        for _ in range(11):
            self._create_click()

        click = self._create_click()
        detector = FraudDetector(click)
        result = detector.check_rate_limit()
        self.assertTrue(result)
        self.assertEqual(detector.flags[0][0], 'rate_limit')

    def test_token_reuse_detection(self):
        """Layer 2: Same token clicked multiple times triggers flag."""
        self._create_click()  # First click on this token

        click = self._create_click()  # Second click — should flag
        detector = FraudDetector(click)
        result = detector.check_token_reuse()
        self.assertTrue(result)
        self.assertEqual(detector.flags[0][0], 'token_reuse')

    def test_ip_cluster_detection(self):
        """Layer 3: > 20 clicks from same IP in 24h triggers flag."""
        for i in range(21):
            token = RedirectToken.objects.create(
                conversation=self.conversation,
                sku=self.sku,
                merchant=self.merchant,
                destination_url=f'https://example.com/page{i}',
                expires_at=timezone.now() + timedelta(hours=72),
            )
            self._create_click(ip='198.51.100.5', token=token)

        click = self._create_click(ip='198.51.100.5')
        detector = FraudDetector(click)
        result = detector.check_ip_cluster()
        self.assertTrue(result)
        self.assertEqual(detector.flags[0][0], 'ip_cluster')

    def test_bot_user_agent_detection(self):
        """Layer 4: Known bot patterns in UA trigger flag."""
        bot_uas = [
            'Googlebot/2.1',
            'Mozilla/5.0 (compatible; Scrapy)',
            'python-requests/2.31',
            'HeadlessChrome/121',
            '',  # Empty UA
        ]
        for ua in bot_uas:
            click = self._create_click(ua=ua)
            detector = FraudDetector(click)
            result = detector.check_bot_user_agent()
            self.assertTrue(result, f"Should flag UA: {ua!r}")

    def test_legitimate_user_agent_passes(self):
        """Layer 4: Normal browser UAs should not flag."""
        click = self._create_click(ua='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)')
        detector = FraudDetector(click)
        result = detector.check_bot_user_agent()
        self.assertFalse(result)

    def test_low_dwell_time_detection(self):
        """Layer 5: Clicks < 2 seconds apart trigger flag."""
        # Create a previous click with explicit timestamp
        prev_click = self._create_click()
        now = timezone.now()
        ClickEvent.objects.filter(pk=prev_click.pk).update(clicked_at=now - timedelta(seconds=1))

        # Create click 1 second later
        click = self._create_click()
        ClickEvent.objects.filter(pk=click.pk).update(clicked_at=now)
        click.refresh_from_db()

        detector = FraudDetector(click)
        result = detector.check_low_dwell_time()
        self.assertTrue(result)
        self.assertEqual(detector.flags[0][0], 'low_dwell')

    def test_fraud_score_calculation(self):
        """Weighted score: bot_ua=0.5, rate_limit=0.3, token_reuse=0.25."""
        click = self._create_click(ua='Googlebot/2.1')
        # Add another click for token reuse
        self._create_click()

        detector = FraudDetector(click)
        detector.check_bot_user_agent()  # 0.5
        detector.check_token_reuse()     # 0.25
        score = detector.calculate_score()
        self.assertAlmostEqual(score, 0.75)

    def test_score_capped_at_1(self):
        """Score should not exceed 1.0 even with many flags."""
        click = self._create_click(ua='Googlebot/2.1')
        detector = FraudDetector(click)
        # Manually add many flags
        detector.flags = [
            ('bot_ua', {}), ('rate_limit', {}), ('token_reuse', {}),
            ('ip_cluster', {}), ('low_dwell', {}),
        ]
        score = detector.calculate_score()
        self.assertEqual(score, 1.0)

    def test_save_results_persists(self):
        """save_results() should update ClickEvent and create FraudFlag records."""
        self._create_click()  # Existing click for token reuse
        click = self._create_click(ua='Scrapy/2.0')

        detector = FraudDetector(click)
        detector.save_results()

        click.refresh_from_db()
        self.assertGreater(click.fraud_score, 0)
        self.assertTrue(len(click.fraud_reasons) > 0)

        # FraudFlags should be created
        flags = FraudFlag.objects.filter(click_event=click)
        self.assertTrue(flags.exists())
        flag_types = set(flags.values_list('flag_type', flat=True))
        self.assertIn('bot_ua', flag_types)
        self.assertIn('token_reuse', flag_types)

    def test_fraudulent_threshold(self):
        """Click is marked fraudulent when score >= 0.5."""
        click = self._create_click(ua='Googlebot/2.1')  # bot_ua = 0.5
        detector = FraudDetector(click)
        detector.save_results()
        click.refresh_from_db()
        self.assertTrue(click.is_fraudulent)

    def test_clean_click_not_fraudulent(self):
        """Click with no flags is not marked fraudulent."""
        click = self._create_click(ua='Mozilla/5.0 (Macintosh)')
        detector = FraudDetector(click)
        detector.save_results()
        click.refresh_from_db()
        self.assertFalse(click.is_fraudulent)
        self.assertEqual(click.fraud_score, 0.0)


class TrackingURLInjectionTest(TestCase):
    """Tests for inject_tracking_urls in techniques.py."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant_inject', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.user,
            company_name='Inject Store',
            contact_email='inject@store.com',
            status=MerchantProfile.Status.APPROVED,
        )
        self.sku = SKU.objects.create(
            merchant=self.merchant,
            name='Injectable Product',
            sku_code='INJ-001',
            description='An injectable product',
            category='Fashion',
            original_price=59.99,
            landing_url='https://merchant.com/product/1',
        )
        self.campaign = Campaign.objects.create(
            merchant=self.merchant,
            name='Inject Campaign',
            status=Campaign.Status.ACTIVE,
            daily_message_limit=1000,
            start_date=timezone.now(),
        )
        self.conversation = Conversation.objects.create(
            phone_number='whatsapp:+4444444444',
            merchant=self.merchant,
            campaign=self.campaign,
        )

    def test_replaces_placeholder_with_tracked_url(self):
        from apps.conversations.bot.techniques import inject_tracking_urls

        response = f"Check out this product: [product_link:{self.sku.id}]"
        result = inject_tracking_urls(response, self.conversation)

        self.assertNotIn('[product_link:', result)
        self.assertIn('/t/', result)

        # Verify token was created
        token = RedirectToken.objects.get(conversation=self.conversation, sku=self.sku)
        self.assertTrue(token.is_active)
        self.assertIn('utm_source=salescount', token.destination_url)

    def test_multiple_placeholders(self):
        from apps.conversations.bot.techniques import inject_tracking_urls

        sku2 = SKU.objects.create(
            merchant=self.merchant,
            name='Second Product',
            sku_code='INJ-002',
            description='Second injectable product',
            category='Fashion',
            original_price=39.99,
            landing_url='https://merchant.com/product/2',
        )
        response = f"Option A: [product_link:{self.sku.id}] or Option B: [product_link:{sku2.id}]"
        result = inject_tracking_urls(response, self.conversation)

        self.assertEqual(result.count('/t/'), 2)
        self.assertEqual(RedirectToken.objects.filter(conversation=self.conversation).count(), 2)

    def test_invalid_sku_id_replaced_with_hash(self):
        from apps.conversations.bot.techniques import inject_tracking_urls

        response = "Check out this product: [product_link:99999]"
        result = inject_tracking_urls(response, self.conversation)

        self.assertNotIn('[product_link:', result)
        self.assertIn('#', result)

    def test_no_placeholders_unchanged(self):
        from apps.conversations.bot.techniques import inject_tracking_urls

        response = "Just a regular message with no links."
        result = inject_tracking_urls(response, self.conversation)
        self.assertEqual(result, response)


class ClickEventAPITest(TestCase):
    """Tests for the click event and fraud flag API endpoints."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_click', password='test1234', role='admin',
        )
        self.merchant_user = User.objects.create_user(
            username='merchant_click_api', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.merchant_user,
            company_name='API Store',
            contact_email='api@store.com',
            status=MerchantProfile.Status.APPROVED,
        )
        self.sku = SKU.objects.create(
            merchant=self.merchant,
            name='API Product',
            sku_code='API-001',
            description='An API product',
            category='Electronics',
            original_price=99.99,
            landing_url='https://merchant.com/api-product',
        )
        self.conversation = Conversation.objects.create(
            phone_number='whatsapp:+5555555555',
            merchant=self.merchant,
        )
        self.token = RedirectToken.objects.create(
            conversation=self.conversation,
            sku=self.sku,
            merchant=self.merchant,
            destination_url='https://merchant.com/api-product',
            expires_at=timezone.now() + timedelta(hours=72),
        )
        self.click = ClickEvent.objects.create(
            redirect_token=self.token,
            ip_address='203.0.113.10',
            user_agent='Mozilla/5.0 (Test)',
            fraud_score=0.3,
        )
        self.client = Client()

    def _login_admin(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.admin)
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {refresh.access_token}'

    def test_click_list_requires_admin(self):
        response = self.client.get('/api/v1/tracking/clicks/')
        self.assertEqual(response.status_code, 401)

    def test_click_list_admin_access(self):
        self._login_admin()
        response = self.client.get('/api/v1/tracking/clicks/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data.get('results', data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['ip_address'], '203.0.113.10')
        self.assertEqual(results[0]['merchant_name'], 'API Store')

    def test_click_list_fraud_only_filter(self):
        self._login_admin()
        # Create a fraudulent click
        fraudulent_click = ClickEvent.objects.create(
            redirect_token=self.token,
            ip_address='198.51.100.1',
            user_agent='Googlebot',
            is_fraudulent=True,
            fraud_score=0.8,
        )

        response = self.client.get('/api/v1/tracking/clicks/?fraud_only=true')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data.get('results', data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], fraudulent_click.id)

    def test_click_detail(self):
        self._login_admin()
        response = self.client.get(f'/api/v1/tracking/clicks/{self.click.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['ip_address'], '203.0.113.10')

    def test_fraud_flag_list(self):
        self._login_admin()
        FraudFlag.objects.create(
            click_event=self.click,
            flag_type='bot_ua',
            details={'user_agent': 'Googlebot'},
        )
        response = self.client.get('/api/v1/tracking/fraud-flags/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data.get('results', data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['flag_type'], 'bot_ua')

    def test_fraud_flag_review(self):
        self._login_admin()
        flag = FraudFlag.objects.create(
            click_event=self.click,
            flag_type='bot_ua',
            details={'user_agent': 'Googlebot'},
        )
        response = self.client.post(
            f'/api/v1/tracking/fraud-flags/{flag.id}/review/',
            data={'verdict': 'fraudulent'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        flag.refresh_from_db()
        self.assertTrue(flag.reviewed)
        self.assertEqual(flag.reviewed_by, self.admin)
        self.assertIsNotNone(flag.reviewed_at)

        # Click should be marked fraudulent
        self.click.refresh_from_db()
        self.assertTrue(self.click.is_fraudulent)

    def test_fraud_flag_review_legitimate(self):
        self._login_admin()
        flag = FraudFlag.objects.create(
            click_event=self.click,
            flag_type='token_reuse',
            details={'previous_clicks': 1},
        )
        response = self.client.post(
            f'/api/v1/tracking/fraud-flags/{flag.id}/review/',
            data={'verdict': 'legitimate'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        flag.refresh_from_db()
        self.assertTrue(flag.reviewed)

        # Click should not be marked fraudulent
        self.click.refresh_from_db()
        self.assertFalse(self.click.is_fraudulent)


class CeleryTaskTest(TestCase):
    """Tests for Celery tasks (sync execution)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant_task', password='test1234', role='merchant',
        )
        self.merchant = MerchantProfile.objects.create(
            user=self.user,
            company_name='Task Store',
            contact_email='task@store.com',
            status=MerchantProfile.Status.APPROVED,
        )
        self.sku = SKU.objects.create(
            merchant=self.merchant,
            name='Task Product',
            sku_code='TASK-001',
            description='A task product',
            category='Electronics',
            original_price=15.99,
            landing_url='https://example.com/task',
        )
        self.conversation = Conversation.objects.create(
            phone_number='whatsapp:+6666666666',
            merchant=self.merchant,
        )

    def test_expire_redirect_tokens(self):
        from apps.tracking.tasks import expire_redirect_tokens

        # Create expired token
        expired = RedirectToken.objects.create(
            conversation=self.conversation,
            sku=self.sku,
            merchant=self.merchant,
            destination_url='https://example.com/expired',
            expires_at=timezone.now() - timedelta(hours=1),
            is_active=True,
        )
        # Create active token
        active = RedirectToken.objects.create(
            conversation=self.conversation,
            sku=self.sku,
            merchant=self.merchant,
            destination_url='https://example.com/active',
            expires_at=timezone.now() + timedelta(hours=72),
            is_active=True,
        )

        expire_redirect_tokens()

        expired.refresh_from_db()
        active.refresh_from_db()
        self.assertFalse(expired.is_active)
        self.assertTrue(active.is_active)

    def test_calculate_fraud_score_task(self):
        from apps.tracking.tasks import calculate_fraud_score

        token = RedirectToken.objects.create(
            conversation=self.conversation,
            sku=self.sku,
            merchant=self.merchant,
            destination_url='https://example.com/task',
            expires_at=timezone.now() + timedelta(hours=72),
        )
        click = ClickEvent.objects.create(
            redirect_token=token,
            ip_address='203.0.113.1',
            user_agent='Googlebot/2.1',
        )

        calculate_fraud_score(click.id)

        click.refresh_from_db()
        self.assertGreater(click.fraud_score, 0)
        self.assertTrue(click.is_fraudulent)  # bot_ua = 0.5

    def test_calculate_fraud_score_nonexistent_click(self):
        from apps.tracking.tasks import calculate_fraud_score
        # Should not raise
        calculate_fraud_score(999999)
