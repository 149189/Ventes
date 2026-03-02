"""Comprehensive tests for the billing app — Phase 5."""
import time
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.merchants.models import MerchantProfile, SKU
from apps.campaigns.models import Campaign
from apps.conversations.models import Conversation
from apps.tracking.models import RedirectToken, ClickEvent
from apps.billing.models import ConversionEvent, Invoice, InvoiceLine, DisputeRecord
from common.hmac_utils import generate_hmac_signature


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
        daily_budget_cap=Decimal('100.00'),
        hmac_secret='test-secret-key-12345',
    )
    return user, merchant


def _make_admin_user(username='admin1'):
    return User.objects.create_user(
        username=username, password='pass1234', role='admin',
    )


def _make_conversation(merchant, campaign=None):
    return Conversation.objects.create(
        phone_number='+919876543210',
        merchant=merchant,
        campaign=campaign,
        coupon_code='SALE20',
    )


def _make_click_chain(merchant, conversation, campaign=None):
    """Create redirect token + click event chain."""
    sku = SKU.objects.create(
        merchant=merchant,
        sku_code='SKU001',
        name='Test Product',
        description='A great product',
        category='Electronics',
        original_price=Decimal('1000.00'),
        landing_url='https://merchant.com/product',
    )
    token = RedirectToken.objects.create(
        conversation=conversation,
        sku=sku,
        merchant=merchant,
        campaign=campaign,
        destination_url='https://merchant.com/product?utm_source=salescount',
        expires_at=timezone.now() + timedelta(hours=24),
    )
    click = ClickEvent.objects.create(
        redirect_token=token,
        ip_address='1.2.3.4',
        user_agent='Mozilla/5.0',
    )
    return sku, token, click


# ---------------------------------------------------------------------------
# HMAC Postback Tests
# ---------------------------------------------------------------------------
class PostbackViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user, self.merchant = _make_merchant_user()
        self.campaign = Campaign.objects.create(
            merchant=self.merchant,
            name='Test Campaign',
            status=Campaign.Status.ACTIVE,
            start_date=timezone.now(),
        )
        self.conversation = _make_conversation(self.merchant, self.campaign)
        self.sku, self.token, self.click = _make_click_chain(
            self.merchant, self.conversation, self.campaign,
        )

    def _postback_payload(self, **overrides):
        ts = int(time.time())
        payload = {
            'token': str(self.token.token),
            'order_id': 'ORD-001',
            'order_amount': '5000.00',
            'timestamp': str(ts),
        }
        payload.update(overrides)
        sig = generate_hmac_signature(self.merchant.hmac_secret, payload)
        payload['hmac_signature'] = sig
        # Convert back for JSON
        payload['order_amount'] = Decimal(payload['order_amount'])
        payload['timestamp'] = int(payload['timestamp'])
        return payload

    def test_valid_postback_creates_conversion(self):
        data = self._postback_payload()
        resp = self.client.post('/api/v1/billing/postback/', data, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertIn('conversion_id', resp.data)

        conv = ConversionEvent.objects.get(id=resp.data['conversion_id'])
        self.assertEqual(conv.source, 'postback')
        self.assertEqual(conv.order_id, 'ORD-001')
        self.assertEqual(conv.merchant, self.merchant)
        # Commission = 5000 * 5% = 250
        self.assertEqual(conv.commission_amount, Decimal('250.00'))

    def test_postback_invalid_token_returns_403(self):
        data = self._postback_payload(token='00000000-0000-0000-0000-000000000000')
        resp = self.client.post('/api/v1/billing/postback/', data, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_postback_stale_timestamp_returns_403(self):
        stale_ts = int(time.time()) - 600  # 10 min ago
        payload = {
            'token': str(self.token.token),
            'order_id': 'ORD-002',
            'order_amount': '1000.00',
            'timestamp': str(stale_ts),
        }
        sig = generate_hmac_signature(self.merchant.hmac_secret, payload)
        payload['hmac_signature'] = sig
        payload['order_amount'] = Decimal(payload['order_amount'])
        payload['timestamp'] = int(payload['timestamp'])
        resp = self.client.post('/api/v1/billing/postback/', payload, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_postback_wrong_signature_returns_403(self):
        ts = int(time.time())
        data = {
            'token': str(self.token.token),
            'order_id': 'ORD-003',
            'order_amount': '2000.00',
            'timestamp': ts,
            'hmac_signature': 'invalid-signature-value',
        }
        resp = self.client.post('/api/v1/billing/postback/', data, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_postback_missing_fields_returns_400(self):
        resp = self.client.post('/api/v1/billing/postback/', {'token': str(self.token.token)}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_postback_records_ab_conversion(self):
        from apps.campaigns.models import ABTestVariant
        variant = ABTestVariant.objects.create(
            campaign=self.campaign,
            name='Variant A',
            variant_type='greeting',
            traffic_weight=1.0,
            impressions=10,
            conversions=0,
        )
        self.conversation.ab_variant = variant
        self.conversation.save()

        data = self._postback_payload()
        resp = self.client.post('/api/v1/billing/postback/', data, format='json')
        self.assertEqual(resp.status_code, 201)

        variant.refresh_from_db()
        self.assertEqual(variant.conversions, 1)


# ---------------------------------------------------------------------------
# Coupon Redemption Tests
# ---------------------------------------------------------------------------
class CouponRedeemViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user, self.merchant = _make_merchant_user()
        self.conversation = _make_conversation(self.merchant)

    def _coupon_payload(self, **overrides):
        ts = int(time.time())
        payload = {
            'coupon_code': 'SALE20',
            'order_id': 'ORD-C001',
            'order_amount': '3000.00',
            'merchant_id': str(self.merchant.id),
            'timestamp': str(ts),
        }
        payload.update(overrides)
        sig = generate_hmac_signature(self.merchant.hmac_secret, payload)
        payload['hmac_signature'] = sig
        payload['order_amount'] = Decimal(payload['order_amount'])
        payload['merchant_id'] = int(payload['merchant_id'])
        payload['timestamp'] = int(payload['timestamp'])
        return payload

    def test_valid_coupon_redeem(self):
        data = self._coupon_payload()
        resp = self.client.post('/api/v1/billing/coupon-redeem/', data, format='json')
        self.assertEqual(resp.status_code, 201)

        conv = ConversionEvent.objects.get(id=resp.data['conversion_id'])
        self.assertEqual(conv.source, 'coupon')
        self.assertEqual(conv.coupon_code, 'SALE20')
        self.assertEqual(conv.conversation, self.conversation)
        # Commission = 3000 * 5% = 150
        self.assertEqual(conv.commission_amount, Decimal('150.00'))

    def test_coupon_redeem_merchant_not_found(self):
        data = self._coupon_payload(merchant_id='99999')
        resp = self.client.post('/api/v1/billing/coupon-redeem/', data, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_coupon_redeem_stale_timestamp(self):
        stale_ts = int(time.time()) - 600
        payload = {
            'coupon_code': 'SALE20',
            'order_id': 'ORD-C002',
            'order_amount': '1000.00',
            'merchant_id': str(self.merchant.id),
            'timestamp': str(stale_ts),
        }
        sig = generate_hmac_signature(self.merchant.hmac_secret, payload)
        payload['hmac_signature'] = sig
        payload['order_amount'] = Decimal(payload['order_amount'])
        payload['merchant_id'] = int(payload['merchant_id'])
        payload['timestamp'] = int(payload['timestamp'])
        resp = self.client.post('/api/v1/billing/coupon-redeem/', payload, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_coupon_redeem_wrong_hmac(self):
        ts = int(time.time())
        data = {
            'coupon_code': 'SALE20',
            'order_id': 'ORD-C003',
            'order_amount': '1000.00',
            'merchant_id': self.merchant.id,
            'timestamp': ts,
            'hmac_signature': 'bad-sig',
        }
        resp = self.client.post('/api/v1/billing/coupon-redeem/', data, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_coupon_no_matching_conversation(self):
        """Conversion still created even if no conversation matches the coupon."""
        data = self._coupon_payload(coupon_code='NONEXISTENT')
        resp = self.client.post('/api/v1/billing/coupon-redeem/', data, format='json')
        self.assertEqual(resp.status_code, 201)
        conv = ConversionEvent.objects.get(id=resp.data['conversion_id'])
        self.assertIsNone(conv.conversation)


# ---------------------------------------------------------------------------
# Conversion List API Tests
# ---------------------------------------------------------------------------
class ConversionListViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin_user()
        self.merch_user, self.merchant = _make_merchant_user()
        self.merch_user2, self.merchant2 = _make_merchant_user('merch2')

        ConversionEvent.objects.create(
            merchant=self.merchant,
            source='postback',
            order_id='ORD-1',
            order_amount=Decimal('1000.00'),
            commission_amount=Decimal('50.00'),
            converted_at=timezone.now(),
        )
        ConversionEvent.objects.create(
            merchant=self.merchant2,
            source='coupon',
            order_id='ORD-2',
            order_amount=Decimal('2000.00'),
            commission_amount=Decimal('100.00'),
            converted_at=timezone.now(),
        )

    def test_unauthenticated_returns_401(self):
        resp = self.client.get('/api/v1/billing/conversions/')
        self.assertEqual(resp.status_code, 401)

    def test_admin_sees_all_conversions(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/billing/conversions/')
        self.assertEqual(resp.status_code, 200)
        data = resp.data.get('results', resp.data)
        self.assertEqual(len(data), 2)

    def test_merchant_sees_own_conversions(self):
        self.client.force_authenticate(self.merch_user)
        resp = self.client.get('/api/v1/billing/conversions/')
        self.assertEqual(resp.status_code, 200)
        data = resp.data.get('results', resp.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['order_id'], 'ORD-1')

    def test_conversion_includes_merchant_name(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/billing/conversions/')
        data = resp.data.get('results', resp.data)
        self.assertIn('merchant_name', data[0])


# ---------------------------------------------------------------------------
# Invoice API Tests
# ---------------------------------------------------------------------------
class InvoiceAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin_user()
        self.merch_user, self.merchant = _make_merchant_user()
        self.merch_user2, self.merchant2 = _make_merchant_user('merch2')

        today = timezone.now().date()
        self.invoice1 = Invoice.objects.create(
            merchant=self.merchant,
            invoice_number='SC-1-20260225',
            period_start=today - timedelta(days=7),
            period_end=today - timedelta(days=1),
            total_conversions=5,
            subtotal=Decimal('500.00'),
            total=Decimal('500.00'),
            status=Invoice.Status.SENT,
            due_date=today + timedelta(days=30),
        )
        self.invoice2 = Invoice.objects.create(
            merchant=self.merchant2,
            invoice_number='SC-2-20260225',
            period_start=today - timedelta(days=7),
            period_end=today - timedelta(days=1),
            total_conversions=3,
            subtotal=Decimal('300.00'),
            total=Decimal('300.00'),
            status=Invoice.Status.PAID,
            paid_at=timezone.now(),
            due_date=today + timedelta(days=30),
        )

    def test_admin_sees_all_invoices(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/billing/invoices/')
        self.assertEqual(resp.status_code, 200)
        data = resp.data.get('results', resp.data)
        self.assertEqual(len(data), 2)

    def test_merchant_sees_own_invoices(self):
        self.client.force_authenticate(self.merch_user)
        resp = self.client.get('/api/v1/billing/invoices/')
        self.assertEqual(resp.status_code, 200)
        data = resp.data.get('results', resp.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['invoice_number'], 'SC-1-20260225')

    def test_invoice_detail(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(f'/api/v1/billing/invoices/{self.invoice1.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['invoice_number'], 'SC-1-20260225')
        self.assertIn('lines', resp.data)

    def test_merchant_cannot_see_other_invoice(self):
        self.client.force_authenticate(self.merch_user)
        resp = self.client.get(f'/api/v1/billing/invoices/{self.invoice2.id}/')
        self.assertEqual(resp.status_code, 404)

    def test_invoice_includes_merchant_name(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(f'/api/v1/billing/invoices/{self.invoice1.id}/')
        self.assertIn('merchant_name', resp.data)
        self.assertEqual(resp.data['merchant_name'], 'Test Co (merch1)')


# ---------------------------------------------------------------------------
# Dispute Tests
# ---------------------------------------------------------------------------
class DisputeWorkflowTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin_user()
        self.merch_user, self.merchant = _make_merchant_user()

        self.conversion = ConversionEvent.objects.create(
            merchant=self.merchant,
            source='postback',
            order_id='ORD-D1',
            order_amount=Decimal('5000.00'),
            commission_amount=Decimal('250.00'),
            converted_at=timezone.now(),
        )

    def test_merchant_files_dispute(self):
        self.client.force_authenticate(self.merch_user)
        resp = self.client.post('/api/v1/billing/disputes/create/', {
            'conversion_event': self.conversion.id,
            'reason': 'Order was returned',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['status'], 'open')

        self.conversion.refresh_from_db()
        self.assertTrue(self.conversion.is_disputed)

    def test_dispute_window_expired(self):
        self.conversion.converted_at = timezone.now() - timedelta(days=30)
        self.conversion.save()

        self.client.force_authenticate(self.merch_user)
        resp = self.client.post('/api/v1/billing/disputes/create/', {
            'conversion_event': self.conversion.id,
            'reason': 'Too late',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_admin_resolves_dispute_upheld(self):
        dispute = DisputeRecord.objects.create(
            conversion_event=self.conversion,
            merchant=self.merchant,
            reason='Order returned',
        )

        self.client.force_authenticate(self.admin)
        resp = self.client.post(f'/api/v1/billing/disputes/{dispute.id}/resolve/', {
            'status': 'upheld',
        }, format='json')
        self.assertEqual(resp.status_code, 200)

        dispute.refresh_from_db()
        self.assertEqual(dispute.status, 'upheld')
        self.assertEqual(dispute.credit_amount, Decimal('250.00'))
        self.assertEqual(dispute.resolved_by, self.admin)
        self.assertIsNotNone(dispute.resolved_at)

    def test_admin_resolves_dispute_rejected(self):
        dispute = DisputeRecord.objects.create(
            conversion_event=self.conversion,
            merchant=self.merchant,
            reason='Fraudulent claim',
        )

        self.client.force_authenticate(self.admin)
        resp = self.client.post(f'/api/v1/billing/disputes/{dispute.id}/resolve/', {
            'status': 'rejected',
            'resolution_notes': 'Evidence insufficient',
        }, format='json')
        self.assertEqual(resp.status_code, 200)

        dispute.refresh_from_db()
        self.assertEqual(dispute.status, 'rejected')
        self.assertEqual(dispute.credit_amount, Decimal('0'))
        self.assertEqual(dispute.resolution_notes, 'Evidence insufficient')

    def test_dispute_resolve_invalid_status(self):
        dispute = DisputeRecord.objects.create(
            conversion_event=self.conversion,
            merchant=self.merchant,
            reason='Test',
        )
        self.client.force_authenticate(self.admin)
        resp = self.client.post(f'/api/v1/billing/disputes/{dispute.id}/resolve/', {
            'status': 'invalid',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_dispute_list_merchant_sees_own(self):
        DisputeRecord.objects.create(
            conversion_event=self.conversion,
            merchant=self.merchant,
            reason='My dispute',
        )

        _, merchant2 = _make_merchant_user('merch2')
        conv2 = ConversionEvent.objects.create(
            merchant=merchant2,
            source='postback',
            order_id='ORD-D2',
            order_amount=Decimal('1000.00'),
            commission_amount=Decimal('50.00'),
            converted_at=timezone.now(),
        )
        DisputeRecord.objects.create(
            conversion_event=conv2,
            merchant=merchant2,
            reason='Other dispute',
        )

        self.client.force_authenticate(self.merch_user)
        resp = self.client.get('/api/v1/billing/disputes/')
        data = resp.data.get('results', resp.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['reason'], 'My dispute')

    def test_dispute_list_admin_sees_all(self):
        DisputeRecord.objects.create(
            conversion_event=self.conversion,
            merchant=self.merchant,
            reason='Dispute 1',
        )
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/billing/disputes/')
        data = resp.data.get('results', resp.data)
        self.assertGreaterEqual(len(data), 1)

    def test_merchant_cannot_resolve_disputes(self):
        dispute = DisputeRecord.objects.create(
            conversion_event=self.conversion,
            merchant=self.merchant,
            reason='Cannot self-resolve',
        )
        self.client.force_authenticate(self.merch_user)
        resp = self.client.post(f'/api/v1/billing/disputes/{dispute.id}/resolve/', {
            'status': 'upheld',
        }, format='json')
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Revenue Stats Tests
# ---------------------------------------------------------------------------
class RevenueStatsViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin_user()
        _, self.merchant = _make_merchant_user()
        today = timezone.now().date()

        Invoice.objects.create(
            merchant=self.merchant,
            invoice_number='SC-R1',
            period_start=today - timedelta(days=7),
            period_end=today,
            subtotal=Decimal('1000.00'),
            total=Decimal('1000.00'),
            status=Invoice.Status.PAID,
            paid_at=timezone.now(),
            due_date=today + timedelta(days=30),
        )
        Invoice.objects.create(
            merchant=self.merchant,
            invoice_number='SC-R2',
            period_start=today - timedelta(days=14),
            period_end=today - timedelta(days=7),
            subtotal=Decimal('500.00'),
            total=Decimal('500.00'),
            status=Invoice.Status.OVERDUE,
            due_date=today - timedelta(days=5),
        )

        conv = ConversionEvent.objects.create(
            merchant=self.merchant,
            source='postback',
            order_id='ORD-R1',
            order_amount=Decimal('10000.00'),
            commission_amount=Decimal('500.00'),
            converted_at=timezone.now(),
        )
        DisputeRecord.objects.create(
            conversion_event=conv,
            merchant=self.merchant,
            reason='Returned',
            status='upheld',
            credit_amount=Decimal('500.00'),
        )

    def test_admin_gets_revenue_stats(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/billing/revenue-stats/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['total_revenue'], Decimal('1000.00'))
        self.assertEqual(resp.data['total_invoices'], 2)
        self.assertEqual(resp.data['paid_invoices'], 1)
        self.assertEqual(resp.data['overdue_invoices'], 1)
        self.assertEqual(resp.data['total_disputes'], 1)
        self.assertEqual(resp.data['total_credits'], Decimal('500.00'))

    def test_merchant_cannot_access_revenue_stats(self):
        merch_user, _ = _make_merchant_user('merch_stats')
        self.client.force_authenticate(merch_user)
        resp = self.client.get('/api/v1/billing/revenue-stats/')
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_cannot_access_revenue_stats(self):
        resp = self.client.get('/api/v1/billing/revenue-stats/')
        self.assertEqual(resp.status_code, 401)


# ---------------------------------------------------------------------------
# Celery Task Tests
# ---------------------------------------------------------------------------
class BillingTaskTest(TestCase):
    def setUp(self):
        self.merch_user, self.merchant = _make_merchant_user()
        self.merchant.daily_budget_cap = Decimal('100.00')
        self.merchant.save()

        self.campaign = Campaign.objects.create(
            merchant=self.merchant,
            name='Budget Test Campaign',
            status=Campaign.Status.ACTIVE,
            start_date=timezone.now(),
        )

    def test_check_daily_budget_caps_pauses_campaigns(self):
        from apps.billing.tasks import check_daily_budget_caps

        ConversionEvent.objects.create(
            merchant=self.merchant,
            source='postback',
            order_id='ORD-B1',
            order_amount=Decimal('2000.00'),
            commission_amount=Decimal('100.00'),
            converted_at=timezone.now(),
        )

        check_daily_budget_caps()

        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, Campaign.Status.PAUSED)

    def test_check_daily_budget_caps_skips_under_budget(self):
        from apps.billing.tasks import check_daily_budget_caps

        ConversionEvent.objects.create(
            merchant=self.merchant,
            source='postback',
            order_id='ORD-B2',
            order_amount=Decimal('500.00'),
            commission_amount=Decimal('25.00'),
            converted_at=timezone.now(),
        )

        check_daily_budget_caps()

        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, Campaign.Status.ACTIVE)

    def test_check_budget_ignores_invalid_conversions(self):
        from apps.billing.tasks import check_daily_budget_caps

        ConversionEvent.objects.create(
            merchant=self.merchant,
            source='postback',
            order_id='ORD-B3',
            order_amount=Decimal('5000.00'),
            commission_amount=Decimal('250.00'),
            is_valid=False,
            converted_at=timezone.now(),
        )

        check_daily_budget_caps()

        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, Campaign.Status.ACTIVE)

    def test_generate_invoices_creates_invoice(self):
        from apps.billing.tasks import generate_invoices

        # Create conversions in the past week
        ConversionEvent.objects.create(
            merchant=self.merchant,
            source='postback',
            order_id='ORD-INV1',
            order_amount=Decimal('10000.00'),
            commission_amount=Decimal('500.00'),
            converted_at=timezone.now() - timedelta(days=3),
        )
        ConversionEvent.objects.create(
            merchant=self.merchant,
            source='coupon',
            order_id='ORD-INV2',
            order_amount=Decimal('5000.00'),
            commission_amount=Decimal('250.00'),
            converted_at=timezone.now() - timedelta(days=2),
        )

        generate_invoices()

        invoices = Invoice.objects.filter(merchant=self.merchant)
        self.assertEqual(invoices.count(), 1)

        invoice = invoices.first()
        self.assertEqual(invoice.total_conversions, 2)
        self.assertEqual(invoice.subtotal, Decimal('750.00'))
        self.assertEqual(invoice.total, Decimal('750.00'))
        self.assertEqual(InvoiceLine.objects.filter(invoice=invoice).count(), 2)

    def test_generate_invoices_skips_disputed_conversions(self):
        from apps.billing.tasks import generate_invoices

        conv = ConversionEvent.objects.create(
            merchant=self.merchant,
            source='postback',
            order_id='ORD-INV3',
            order_amount=Decimal('10000.00'),
            commission_amount=Decimal('500.00'),
            is_disputed=True,
            converted_at=timezone.now() - timedelta(days=2),
        )

        generate_invoices()

        self.assertEqual(Invoice.objects.filter(merchant=self.merchant).count(), 0)

    def test_generate_invoices_skips_zero_commission(self):
        from apps.billing.tasks import generate_invoices
        # No conversions → no invoice
        generate_invoices()
        self.assertEqual(Invoice.objects.count(), 0)

    @patch('apps.billing.razorpay_client.create_invoice')
    def test_generate_invoices_calls_razorpay(self, mock_rzp):
        from apps.billing.tasks import generate_invoices

        self.merchant.razorpay_customer_id = 'cust_test123'
        self.merchant.save()

        mock_rzp.return_value = {'id': 'inv_rzp_123'}

        ConversionEvent.objects.create(
            merchant=self.merchant,
            source='postback',
            order_id='ORD-RZP1',
            order_amount=Decimal('10000.00'),
            commission_amount=Decimal('500.00'),
            converted_at=timezone.now() - timedelta(days=3),
        )

        generate_invoices()

        mock_rzp.assert_called_once()
        invoice = Invoice.objects.first()
        self.assertEqual(invoice.razorpay_invoice_id, 'inv_rzp_123')
        self.assertEqual(invoice.status, Invoice.Status.SENT)


# ---------------------------------------------------------------------------
# Razorpay Webhook Tests
# ---------------------------------------------------------------------------
class RazorpayWebhookTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        _, self.merchant = _make_merchant_user()
        today = timezone.now().date()

        self.invoice = Invoice.objects.create(
            merchant=self.merchant,
            invoice_number='SC-W1',
            razorpay_invoice_id='inv_rzp_test1',
            period_start=today - timedelta(days=7),
            period_end=today,
            subtotal=Decimal('1000.00'),
            total=Decimal('1000.00'),
            status=Invoice.Status.SENT,
            due_date=today + timedelta(days=30),
        )

    @patch('apps.billing.razorpay_client.verify_webhook_signature', return_value=True)
    def test_invoice_paid_webhook(self, mock_verify):
        payload = {
            'event': 'invoice.paid',
            'payload': {
                'invoice': {
                    'entity': {
                        'id': 'inv_rzp_test1',
                    }
                }
            }
        }
        resp = self.client.post(
            '/api/v1/billing/razorpay/webhook/',
            data=payload,
            format='json',
        )
        self.assertEqual(resp.status_code, 200)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)
        self.assertIsNotNone(self.invoice.paid_at)

    @patch('apps.billing.razorpay_client.verify_webhook_signature', return_value=True)
    def test_invoice_expired_webhook(self, mock_verify):
        payload = {
            'event': 'invoice.expired',
            'payload': {
                'invoice': {
                    'entity': {
                        'id': 'inv_rzp_test1',
                    }
                }
            }
        }
        resp = self.client.post(
            '/api/v1/billing/razorpay/webhook/',
            data=payload,
            format='json',
        )
        self.assertEqual(resp.status_code, 200)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.OVERDUE)

    @patch('apps.billing.razorpay_client.verify_webhook_signature', return_value=False)
    def test_invalid_signature_returns_400(self, mock_verify):
        payload = {'event': 'invoice.paid', 'payload': {}}
        resp = self.client.post(
            '/api/v1/billing/razorpay/webhook/',
            data=payload,
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    @patch('apps.billing.razorpay_client.verify_webhook_signature', return_value=True)
    def test_unknown_event_returns_200(self, mock_verify):
        payload = {'event': 'unknown.event', 'payload': {}}
        resp = self.client.post(
            '/api/v1/billing/razorpay/webhook/',
            data=payload,
            format='json',
        )
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# HMAC Utils Tests
# ---------------------------------------------------------------------------
class HMACUtilsTest(TestCase):
    def test_generate_and_verify_signature(self):
        payload = {'order_id': 'ORD-001', 'amount': '500', 'token': 'abc'}
        sig = generate_hmac_signature('my-secret', payload)
        from common.hmac_utils import verify_hmac_signature
        self.assertTrue(verify_hmac_signature('my-secret', payload, sig))

    def test_wrong_secret_fails(self):
        payload = {'key': 'value'}
        sig = generate_hmac_signature('correct-secret', payload)
        from common.hmac_utils import verify_hmac_signature
        self.assertFalse(verify_hmac_signature('wrong-secret', payload, sig))

    def test_timestamp_freshness(self):
        from common.hmac_utils import verify_timestamp_freshness
        self.assertTrue(verify_timestamp_freshness(int(time.time())))
        self.assertFalse(verify_timestamp_freshness(int(time.time()) - 600))

    def test_canonical_ordering(self):
        """Signature is deterministic regardless of key order."""
        payload1 = {'z': '1', 'a': '2', 'm': '3'}
        payload2 = {'a': '2', 'm': '3', 'z': '1'}
        sig1 = generate_hmac_signature('secret', payload1)
        sig2 = generate_hmac_signature('secret', payload2)
        self.assertEqual(sig1, sig2)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------
class BillingModelTest(TestCase):
    def setUp(self):
        _, self.merchant = _make_merchant_user()

    def test_conversion_event_str(self):
        conv = ConversionEvent.objects.create(
            merchant=self.merchant,
            source='postback',
            order_id='ORD-M1',
            order_amount=Decimal('1000.00'),
            commission_amount=Decimal('50.00'),
            converted_at=timezone.now(),
        )
        self.assertIn('ORD-M1', str(conv))

    def test_invoice_str(self):
        today = timezone.now().date()
        inv = Invoice.objects.create(
            merchant=self.merchant,
            invoice_number='SC-M1',
            period_start=today,
            period_end=today,
            total=Decimal('500.00'),
            due_date=today + timedelta(days=30),
        )
        self.assertIn('SC-M1', str(inv))

    def test_dispute_str(self):
        conv = ConversionEvent.objects.create(
            merchant=self.merchant,
            source='postback',
            order_id='ORD-M2',
            order_amount=Decimal('1000.00'),
            commission_amount=Decimal('50.00'),
            converted_at=timezone.now(),
        )
        dispute = DisputeRecord.objects.create(
            conversion_event=conv,
            merchant=self.merchant,
            reason='Test',
        )
        self.assertIn('Open', str(dispute))

    def test_invoice_line_creation(self):
        today = timezone.now().date()
        inv = Invoice.objects.create(
            merchant=self.merchant,
            invoice_number='SC-ML1',
            period_start=today,
            period_end=today,
            total=Decimal('100.00'),
            due_date=today + timedelta(days=30),
        )
        line = InvoiceLine.objects.create(
            invoice=inv,
            description='Conversion ORD-001',
            billing_type='cpa',
            quantity=1,
            unit_price=Decimal('100.00'),
            line_total=Decimal('100.00'),
        )
        self.assertEqual(inv.lines.count(), 1)
        self.assertEqual(line.billing_type, 'cpa')
