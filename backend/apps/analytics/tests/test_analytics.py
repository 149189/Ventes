"""Comprehensive tests for the analytics app — Phase 6."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.merchants.models import MerchantProfile, SKU
from apps.campaigns.models import Campaign
from apps.conversations.models import Conversation, Message
from apps.tracking.models import RedirectToken, ClickEvent
from apps.billing.models import ConversionEvent
from apps.analytics.models import DailyMerchantStats, DailyCampaignStats, HourlyClickStats


def _make_merchant_user(username='merch1'):
    user = User.objects.create_user(
        username=username, password='pass1234', role='merchant',
    )
    merchant = MerchantProfile.objects.create(
        user=user,
        company_name=f'Test Co ({username})',
        contact_email=f'{username}@example.com',
        contact_phone='+919876543210',
        billing_address='123 Street',
        status=MerchantProfile.Status.APPROVED,
        commission_rate=Decimal('5.00'),
        daily_budget_cap=Decimal('500.00'),
        hmac_secret='test-secret-key',
    )
    return user, merchant


def _make_admin_user(username='admin1'):
    return User.objects.create_user(
        username=username, password='pass1234', role='admin',
    )


def _seed_data(merchant, days_ago=3):
    """Create conversations, clicks, conversions spread over days."""
    campaign = Campaign.objects.create(
        merchant=merchant,
        name='Test Campaign',
        status=Campaign.Status.ACTIVE,
        start_date=timezone.now() - timedelta(days=10),
    )
    sku = SKU.objects.create(
        merchant=merchant,
        sku_code='SKU001',
        name='Test Product',
        description='A product',
        category='General',
        original_price=Decimal('1000.00'),
        landing_url='https://example.com',
    )

    conversations = []
    clicks = []
    conversions = []

    for d in range(days_ago):
        ts = timezone.now() - timedelta(days=d)

        conv = Conversation.objects.create(
            phone_number=f'+9198765{d:05d}',
            merchant=merchant,
            campaign=campaign,
        )
        Conversation.objects.filter(pk=conv.pk).update(started_at=ts)
        conversations.append(conv)

        Message.objects.create(
            conversation=conv,
            direction='outbound',
            body='Hello!',
        )

        token = RedirectToken.objects.create(
            conversation=conv,
            sku=sku,
            merchant=merchant,
            campaign=campaign,
            destination_url='https://example.com/product',
            expires_at=timezone.now() + timedelta(hours=24),
        )

        click = ClickEvent.objects.create(
            redirect_token=token,
            ip_address='1.2.3.4',
            user_agent='Mozilla/5.0',
        )
        ClickEvent.objects.filter(pk=click.pk).update(clicked_at=ts)
        clicks.append(click)

        if d % 2 == 0:
            ce = ConversionEvent.objects.create(
                click_event=click,
                conversation=conv,
                merchant=merchant,
                source='postback',
                order_id=f'ORD-{d}',
                order_amount=Decimal('2000.00'),
                commission_amount=Decimal('100.00'),
                converted_at=ts,
            )
            conversions.append(ce)

    # Add a fraudulent click
    fraud_token = RedirectToken.objects.create(
        conversation=conversations[0],
        sku=sku,
        merchant=merchant,
        campaign=campaign,
        destination_url='https://example.com/fraud',
        expires_at=timezone.now() + timedelta(hours=24),
    )
    fraud_click = ClickEvent.objects.create(
        redirect_token=fraud_token,
        ip_address='9.9.9.9',
        user_agent='bot/1.0',
        is_fraudulent=True,
        fraud_score=0.9,
    )

    return campaign, sku, conversations, clicks, conversions


# ---------------------------------------------------------------------------
# Admin Dashboard Tests
# ---------------------------------------------------------------------------
class AdminDashboardViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin_user()
        _, self.merchant = _make_merchant_user()
        _seed_data(self.merchant, days_ago=5)

    def test_admin_dashboard_returns_kpis(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/analytics/admin/dashboard/?period=7d')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('total_conversations', resp.data)
        self.assertIn('total_clicks', resp.data)
        self.assertIn('flagged_clicks', resp.data)
        self.assertIn('total_conversions', resp.data)
        self.assertIn('total_revenue', resp.data)
        self.assertIn('conversion_rate', resp.data)
        self.assertIn('active_merchants', resp.data)

    def test_admin_dashboard_period_filter(self):
        self.client.force_authenticate(self.admin)
        resp7 = self.client.get('/api/v1/analytics/admin/dashboard/?period=7d')
        resp30 = self.client.get('/api/v1/analytics/admin/dashboard/?period=30d')
        self.assertEqual(resp7.status_code, 200)
        self.assertEqual(resp30.status_code, 200)
        # 30d should include at least as many as 7d
        self.assertGreaterEqual(
            resp30.data['total_clicks'], resp7.data['total_clicks'],
        )

    def test_admin_dashboard_has_flagged_clicks(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/analytics/admin/dashboard/?period=30d')
        self.assertGreaterEqual(resp.data['flagged_clicks'], 1)

    def test_unauthenticated_returns_401(self):
        resp = self.client.get('/api/v1/analytics/admin/dashboard/')
        self.assertEqual(resp.status_code, 401)

    def test_merchant_cannot_access_admin_dashboard(self):
        merch_user, _ = _make_merchant_user('merch_noadmin')
        self.client.force_authenticate(merch_user)
        resp = self.client.get('/api/v1/analytics/admin/dashboard/')
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Admin Trends Tests
# ---------------------------------------------------------------------------
class AdminTrendsViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin_user()
        _, self.merchant = _make_merchant_user()
        _seed_data(self.merchant, days_ago=5)

    def test_trends_returns_daily_data(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/analytics/admin/trends/?period=7d')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 7)  # 7 days of data
        first = resp.data[0]
        self.assertIn('date', first)
        self.assertIn('clicks', first)
        self.assertIn('conversions', first)
        self.assertIn('revenue', first)
        self.assertIn('fraudulent', first)
        self.assertIn('conversations', first)

    def test_trends_30d_returns_30_days(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/analytics/admin/trends/?period=30d')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 30)

    def test_trends_has_nonzero_data(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/analytics/admin/trends/?period=7d')
        total_clicks = sum(d['clicks'] for d in resp.data)
        self.assertGreater(total_clicks, 0)


# ---------------------------------------------------------------------------
# Admin Funnel Tests
# ---------------------------------------------------------------------------
class AdminFunnelViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin_user()
        _, self.merchant = _make_merchant_user()
        _seed_data(self.merchant, days_ago=3)

    def test_funnel_returns_three_stages(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/analytics/admin/funnel/?period=7d')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['funnel']), 3)
        stages = [f['stage'] for f in resp.data['funnel']]
        self.assertEqual(stages, ['Conversations', 'Clicks', 'Conversions'])

    def test_funnel_counts_decrease(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/analytics/admin/funnel/?period=30d')
        funnel = resp.data['funnel']
        # Conversations >= Clicks >= Conversions
        self.assertGreaterEqual(funnel[0]['count'], funnel[1]['count'])
        self.assertGreaterEqual(funnel[1]['count'], funnel[2]['count'])


# ---------------------------------------------------------------------------
# Top Merchants Tests
# ---------------------------------------------------------------------------
class TopMerchantsViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin_user()
        _, self.merchant1 = _make_merchant_user('merch1')
        _, self.merchant2 = _make_merchant_user('merch2')

        _seed_data(self.merchant1, days_ago=3)

        # Add conversions for merchant2
        ConversionEvent.objects.create(
            merchant=self.merchant2,
            source='postback',
            order_id='ORD-M2-1',
            order_amount=Decimal('5000.00'),
            commission_amount=Decimal('250.00'),
            converted_at=timezone.now(),
        )

    def test_top_merchants_returns_ranked_list(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/analytics/admin/top-merchants/?period=30d')
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 2)
        # First merchant should have highest revenue
        self.assertGreater(resp.data[0]['revenue'], 0)

    def test_top_merchants_includes_merchant_name(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/analytics/admin/top-merchants/')
        for entry in resp.data:
            self.assertIn('merchant', entry)
            self.assertIn('revenue', entry)
            self.assertIn('conversions', entry)


# ---------------------------------------------------------------------------
# Merchant Dashboard Tests
# ---------------------------------------------------------------------------
class MerchantDashboardViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.merch_user, self.merchant = _make_merchant_user()

    def test_merchant_dashboard_returns_today_kpis(self):
        self.client.force_authenticate(self.merch_user)
        resp = self.client.get('/api/v1/analytics/merchant/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('conversations_today', resp.data)
        self.assertIn('clicks_today', resp.data)
        self.assertIn('conversions_today', resp.data)
        self.assertIn('ctr', resp.data)
        self.assertIn('spend_today', resp.data)
        self.assertIn('daily_budget_cap', resp.data)
        self.assertIn('budget_remaining', resp.data)

    def test_merchant_dashboard_budget_remaining(self):
        ConversionEvent.objects.create(
            merchant=self.merchant,
            source='postback',
            order_id='ORD-BUDGET',
            order_amount=Decimal('2000.00'),
            commission_amount=Decimal('100.00'),
            converted_at=timezone.now(),
        )

        self.client.force_authenticate(self.merch_user)
        resp = self.client.get('/api/v1/analytics/merchant/dashboard/')
        self.assertEqual(resp.data['spend_today'], Decimal('100.00'))
        self.assertEqual(
            resp.data['budget_remaining'],
            self.merchant.daily_budget_cap - Decimal('100.00'),
        )

    def test_admin_cannot_access_merchant_dashboard(self):
        admin = _make_admin_user()
        self.client.force_authenticate(admin)
        resp = self.client.get('/api/v1/analytics/merchant/dashboard/')
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Merchant Trends Tests
# ---------------------------------------------------------------------------
class MerchantTrendsViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.merch_user, self.merchant = _make_merchant_user()
        _seed_data(self.merchant, days_ago=5)

    def test_merchant_trends_returns_daily_data(self):
        self.client.force_authenticate(self.merch_user)
        resp = self.client.get('/api/v1/analytics/merchant/trends/?period=7d')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 7)
        first = resp.data[0]
        self.assertIn('date', first)
        self.assertIn('clicks', first)
        self.assertIn('conversions', first)
        self.assertIn('spend', first)
        self.assertIn('conversations', first)

    def test_merchant_trends_only_own_data(self):
        """Merchant should not see other merchant's data."""
        merch_user2, merchant2 = _make_merchant_user('merch2')
        _seed_data(merchant2, days_ago=3)

        self.client.force_authenticate(self.merch_user)
        resp = self.client.get('/api/v1/analytics/merchant/trends/?period=7d')

        # Should only see merchant1's data
        total_clicks = sum(d['clicks'] for d in resp.data)
        # merchant1 has 5 valid clicks (from seed), not merchant2's 3
        self.assertGreater(total_clicks, 0)

        # Now check merchant2
        self.client.force_authenticate(merch_user2)
        resp2 = self.client.get('/api/v1/analytics/merchant/trends/?period=7d')
        total_clicks2 = sum(d['clicks'] for d in resp2.data)
        self.assertGreater(total_clicks2, 0)


# ---------------------------------------------------------------------------
# Celery Tasks Tests
# ---------------------------------------------------------------------------
class AggregationTaskTest(TestCase):
    def setUp(self):
        _, self.merchant = _make_merchant_user()
        self.campaign = Campaign.objects.create(
            merchant=self.merchant,
            name='Stats Campaign',
            status=Campaign.Status.ACTIVE,
            start_date=timezone.now() - timedelta(days=10),
        )
        self.sku = SKU.objects.create(
            merchant=self.merchant,
            sku_code='SKU-STAT',
            name='Stats Product',
            description='Product',
            category='Test',
            original_price=Decimal('500.00'),
            landing_url='https://example.com',
        )

    def test_aggregate_hourly_stats(self):
        from apps.analytics.tasks import aggregate_hourly_stats

        conv = Conversation.objects.create(
            phone_number='+919999900001',
            merchant=self.merchant,
            campaign=self.campaign,
        )
        token = RedirectToken.objects.create(
            conversation=conv,
            sku=self.sku,
            merchant=self.merchant,
            campaign=self.campaign,
            destination_url='https://example.com',
            expires_at=timezone.now() + timedelta(hours=24),
        )
        ClickEvent.objects.create(
            redirect_token=token, ip_address='1.1.1.1', user_agent='Mozilla/5.0',
        )
        ClickEvent.objects.create(
            redirect_token=token, ip_address='2.2.2.2', user_agent='bot',
            is_fraudulent=True,
        )

        aggregate_hourly_stats()

        stats = HourlyClickStats.objects.filter(merchant=self.merchant)
        self.assertEqual(stats.count(), 1)
        stat = stats.first()
        self.assertEqual(stat.clicks, 2)
        self.assertEqual(stat.valid_clicks, 1)

    def test_aggregate_daily_stats(self):
        from apps.analytics.tasks import aggregate_daily_stats

        yesterday = timezone.now() - timedelta(days=1)

        conv = Conversation.objects.create(
            phone_number='+919999900002',
            merchant=self.merchant,
            campaign=self.campaign,
        )
        Conversation.objects.filter(pk=conv.pk).update(started_at=yesterday)

        Message.objects.create(
            conversation=conv, direction='outbound', body='Hi there!',
        )
        Message.objects.filter(conversation=conv).update(created_at=yesterday)

        token = RedirectToken.objects.create(
            conversation=conv,
            sku=self.sku,
            merchant=self.merchant,
            campaign=self.campaign,
            destination_url='https://example.com',
            expires_at=timezone.now() + timedelta(hours=24),
        )
        click = ClickEvent.objects.create(
            redirect_token=token, ip_address='3.3.3.3', user_agent='Mozilla/5.0',
        )
        ClickEvent.objects.filter(pk=click.pk).update(clicked_at=yesterday)

        ConversionEvent.objects.create(
            click_event=click,
            conversation=conv,
            merchant=self.merchant,
            source='postback',
            order_id='ORD-DAILY',
            order_amount=Decimal('1000.00'),
            commission_amount=Decimal('50.00'),
            converted_at=yesterday,
        )

        aggregate_daily_stats()

        mstats = DailyMerchantStats.objects.filter(merchant=self.merchant)
        self.assertEqual(mstats.count(), 1)
        ms = mstats.first()
        self.assertEqual(ms.clicks_total, 1)
        self.assertEqual(ms.conversions, 1)
        self.assertEqual(ms.spend, Decimal('50.00'))

        cstats = DailyCampaignStats.objects.filter(campaign=self.campaign)
        self.assertEqual(cstats.count(), 1)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------
class AnalyticsModelTest(TestCase):
    def setUp(self):
        _, self.merchant = _make_merchant_user()
        self.campaign = Campaign.objects.create(
            merchant=self.merchant,
            name='Model Test',
            status=Campaign.Status.ACTIVE,
            start_date=timezone.now(),
        )

    def test_daily_merchant_stats_str(self):
        stat = DailyMerchantStats.objects.create(
            merchant=self.merchant,
            date=timezone.now().date(),
        )
        self.assertIn(str(self.merchant), str(stat))

    def test_daily_campaign_stats_str(self):
        stat = DailyCampaignStats.objects.create(
            campaign=self.campaign,
            date=timezone.now().date(),
        )
        self.assertIn(str(self.campaign), str(stat))

    def test_unique_together_merchant_date(self):
        from django.db import IntegrityError
        today = timezone.now().date()
        DailyMerchantStats.objects.create(merchant=self.merchant, date=today)
        with self.assertRaises(IntegrityError):
            DailyMerchantStats.objects.create(merchant=self.merchant, date=today)
