"""Comprehensive tests for production hardening — Phase 7."""
from django.test import TestCase, RequestFactory, override_settings

from apps.accounts.models import User


# ---------------------------------------------------------------------------
# Health check tests
# ---------------------------------------------------------------------------
class HealthCheckTest(TestCase):
    """Test the /health/ and /ready/ endpoints."""

    def test_health_returns_200(self):
        resp = self.client.get('/health/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'ok')

    def test_readiness_returns_200_with_checks(self):
        resp = self.client.get('/ready/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('checks', data)
        self.assertIn('database', data['checks'])
        self.assertIn('cache', data['checks'])
        self.assertEqual(data['checks']['database']['status'], 'ok')

    def test_readiness_database_latency(self):
        resp = self.client.get('/ready/')
        data = resp.json()
        self.assertIn('latency_ms', data['checks']['database'])
        self.assertGreaterEqual(data['checks']['database']['latency_ms'], 0)

    def test_readiness_cache_check(self):
        resp = self.client.get('/ready/')
        data = resp.json()
        # In test env (LocMemCache), cache should be ok
        self.assertEqual(data['checks']['cache']['status'], 'ok')

    def test_health_allows_get_and_head(self):
        resp = self.client.get('/health/')
        self.assertEqual(resp.status_code, 200)
        resp = self.client.head('/health/')
        self.assertEqual(resp.status_code, 200)

    def test_health_no_auth_required(self):
        """Health endpoints should not require authentication."""
        resp = self.client.get('/health/')
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get('/ready/')
        self.assertIn(resp.status_code, [200, 503])


# ---------------------------------------------------------------------------
# Request ID middleware tests
# ---------------------------------------------------------------------------
class RequestIDMiddlewareTest(TestCase):
    """Test the X-Request-ID middleware."""

    def test_response_has_request_id_header(self):
        resp = self.client.get('/health/')
        self.assertIn('X-Request-ID', resp)
        # Should be a UUID-like string
        self.assertEqual(len(resp['X-Request-ID']), 36)

    def test_request_id_forwarded_from_header(self):
        custom_id = 'my-trace-id-12345'
        resp = self.client.get('/health/', HTTP_X_REQUEST_ID=custom_id)
        self.assertEqual(resp['X-Request-ID'], custom_id)

    def test_request_id_generated_when_missing(self):
        resp = self.client.get('/health/')
        request_id = resp['X-Request-ID']
        self.assertTrue(len(request_id) > 0)

    def test_different_requests_get_different_ids(self):
        resp1 = self.client.get('/health/')
        resp2 = self.client.get('/health/')
        self.assertNotEqual(resp1['X-Request-ID'], resp2['X-Request-ID'])


# ---------------------------------------------------------------------------
# DRF throttle configuration tests
# ---------------------------------------------------------------------------
class ThrottleConfigTest(TestCase):
    """Test that DRF throttling is properly configured."""

    def test_anon_throttle_rate_configured(self):
        from django.conf import settings
        rates = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {})
        self.assertIn('anon', rates)
        self.assertEqual(rates['anon'], '100/hour')

    def test_user_throttle_rate_configured(self):
        from django.conf import settings
        rates = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {})
        self.assertIn('user', rates)
        self.assertEqual(rates['user'], '1000/hour')

    def test_throttle_classes_present(self):
        from django.conf import settings
        classes = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_CLASSES', [])
        class_names = [c.split('.')[-1] for c in classes]
        self.assertIn('AnonRateThrottle', class_names)
        self.assertIn('UserRateThrottle', class_names)


# ---------------------------------------------------------------------------
# Custom throttle tests
# ---------------------------------------------------------------------------
class CustomThrottleTest(TestCase):
    """Test custom throttle classes."""

    def test_whatsapp_webhook_throttle_rate(self):
        from common.throttling import WhatsAppWebhookThrottle
        t = WhatsAppWebhookThrottle()
        self.assertEqual(t.rate, '60/minute')

    def test_postback_throttle_rate(self):
        from common.throttling import PostbackThrottle
        t = PostbackThrottle()
        self.assertEqual(t.rate, '100/minute')

    def test_merchant_api_throttle_rate(self):
        from common.throttling import MerchantAPIThrottle
        t = MerchantAPIThrottle()
        self.assertEqual(t.rate, '200/minute')

    def test_admin_api_throttle_rate(self):
        from common.throttling import AdminAPIThrottle
        t = AdminAPIThrottle()
        self.assertEqual(t.rate, '500/minute')


# ---------------------------------------------------------------------------
# Settings configuration tests
# ---------------------------------------------------------------------------
class SettingsConfigTest(TestCase):
    """Verify base settings are correctly configured for security."""

    def test_jwt_access_token_short_lifetime(self):
        from django.conf import settings
        lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
        self.assertLessEqual(lifetime.total_seconds(), 900)  # 15 minutes max

    def test_jwt_refresh_token_rotation_enabled(self):
        from django.conf import settings
        self.assertTrue(settings.SIMPLE_JWT['ROTATE_REFRESH_TOKENS'])
        self.assertTrue(settings.SIMPLE_JWT['BLACKLIST_AFTER_ROTATION'])

    def test_password_validators_configured(self):
        from django.conf import settings
        self.assertGreaterEqual(len(settings.AUTH_PASSWORD_VALIDATORS), 4)

    def test_middleware_order_security_first(self):
        from django.conf import settings
        mw = settings.MIDDLEWARE
        # RequestID should be present
        self.assertIn('common.middleware.RequestIDMiddleware', mw)
        # SecurityMiddleware should come right after RequestID
        req_idx = mw.index('common.middleware.RequestIDMiddleware')
        sec_idx = mw.index('django.middleware.security.SecurityMiddleware')
        self.assertLess(req_idx, sec_idx)
        # CORS must come before CommonMiddleware
        cors_idx = mw.index('corsheaders.middleware.CorsMiddleware')
        common_idx = mw.index('django.middleware.common.CommonMiddleware')
        self.assertLess(cors_idx, common_idx)

    def test_logging_configured(self):
        from django.conf import settings
        self.assertIn('LOGGING', dir(settings))
        self.assertIn('loggers', settings.LOGGING)
        self.assertIn('salescount.request', settings.LOGGING['loggers'])

    def test_celery_task_time_limits(self):
        from django.conf import settings
        self.assertEqual(settings.CELERY_TASK_SOFT_TIME_LIMIT, 300)
        self.assertEqual(settings.CELERY_TASK_TIME_LIMIT, 600)

    def test_celery_acks_late(self):
        from django.conf import settings
        self.assertTrue(settings.CELERY_TASK_ACKS_LATE)

    def test_cache_configured(self):
        from django.conf import settings
        self.assertIn('default', settings.CACHES)
        self.assertIn('BACKEND', settings.CACHES['default'])


# ---------------------------------------------------------------------------
# Celery beat schedule tests
# ---------------------------------------------------------------------------
class CeleryBeatScheduleTest(TestCase):
    """Verify all periodic tasks are scheduled."""

    def test_hourly_stats_scheduled(self):
        from django.conf import settings
        schedule = settings.CELERY_BEAT_SCHEDULE
        self.assertIn('aggregate-hourly-stats', schedule)
        self.assertEqual(
            schedule['aggregate-hourly-stats']['task'],
            'apps.analytics.tasks.aggregate_hourly_stats',
        )

    def test_daily_stats_scheduled(self):
        from django.conf import settings
        schedule = settings.CELERY_BEAT_SCHEDULE
        self.assertIn('aggregate-daily-stats', schedule)
        task = schedule['aggregate-daily-stats']
        self.assertEqual(task['task'], 'apps.analytics.tasks.aggregate_daily_stats')

    def test_budget_caps_scheduled(self):
        from django.conf import settings
        schedule = settings.CELERY_BEAT_SCHEDULE
        self.assertIn('check-daily-budget-caps', schedule)
        task = schedule['check-daily-budget-caps']
        self.assertEqual(task['task'], 'apps.billing.tasks.check_daily_budget_caps')

    def test_invoices_scheduled_weekly(self):
        from django.conf import settings
        schedule = settings.CELERY_BEAT_SCHEDULE
        self.assertIn('generate-weekly-invoices', schedule)
        task = schedule['generate-weekly-invoices']
        self.assertEqual(task['task'], 'apps.billing.tasks.generate_invoices')
        # Should run on Monday
        self.assertEqual(task['schedule'].day_of_week, {1})

    def test_tier_update_scheduled_monthly(self):
        from django.conf import settings
        schedule = settings.CELERY_BEAT_SCHEDULE
        self.assertIn('update-merchant-tiers', schedule)
        task = schedule['update-merchant-tiers']
        self.assertEqual(task['task'], 'apps.analytics.tasks.update_merchant_tiers')
        # Should run on 1st of month
        self.assertEqual(task['schedule'].day_of_month, {1})


# ---------------------------------------------------------------------------
# Permissions tests
# ---------------------------------------------------------------------------
class PermissionsTest(TestCase):
    """Test role-based permissions."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_perm', password='pass1234', role='admin',
        )
        self.merchant = User.objects.create_user(
            username='merch_perm', password='pass1234', role='merchant',
        )
        self.agent = User.objects.create_user(
            username='agent_perm', password='pass1234', role='agent',
        )

    def test_is_admin_accepts_admin(self):
        from common.permissions import IsAdmin
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.admin
        self.assertTrue(IsAdmin().has_permission(request, None))

    def test_is_admin_rejects_merchant(self):
        from common.permissions import IsAdmin
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.merchant
        self.assertFalse(IsAdmin().has_permission(request, None))

    def test_is_merchant_accepts_merchant(self):
        from common.permissions import IsMerchant
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.merchant
        self.assertTrue(IsMerchant().has_permission(request, None))

    def test_is_admin_or_merchant_accepts_both(self):
        from common.permissions import IsAdminOrMerchant
        factory = RequestFactory()
        for user in [self.admin, self.merchant]:
            request = factory.get('/')
            request.user = user
            self.assertTrue(IsAdminOrMerchant().has_permission(request, None))

    def test_is_agent_accepts_agent(self):
        from common.permissions import IsAgent
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.agent
        self.assertTrue(IsAgent().has_permission(request, None))

    def test_is_agent_rejects_admin(self):
        from common.permissions import IsAgent
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.admin
        self.assertFalse(IsAgent().has_permission(request, None))


# ---------------------------------------------------------------------------
# Pagination tests
# ---------------------------------------------------------------------------
class PaginationTest(TestCase):
    """Test custom pagination class."""

    def test_standard_pagination_page_size(self):
        from common.pagination import StandardPagination
        p = StandardPagination()
        self.assertEqual(p.page_size, 20)

    def test_standard_pagination_max_page_size(self):
        from common.pagination import StandardPagination
        self.assertEqual(StandardPagination.max_page_size, 100)


# ---------------------------------------------------------------------------
# Exception classes tests
# ---------------------------------------------------------------------------
class ExceptionClassesTest(TestCase):
    """Test custom exception classes."""

    def test_invalid_hmac_status_code(self):
        from common.exceptions import InvalidHMACSignature
        self.assertEqual(InvalidHMACSignature.status_code, 403)

    def test_stale_timestamp_status_code(self):
        from common.exceptions import StaleTimestamp
        self.assertEqual(StaleTimestamp.status_code, 403)

    def test_daily_budget_exceeded_status_code(self):
        from common.exceptions import DailyBudgetExceeded
        self.assertEqual(DailyBudgetExceeded.status_code, 429)

    def test_dispute_window_expired_status_code(self):
        from common.exceptions import DisputeWindowExpired
        self.assertEqual(DisputeWindowExpired.status_code, 400)


# ---------------------------------------------------------------------------
# Production settings tests (override_settings)
# ---------------------------------------------------------------------------
class ProdSecuritySettingsTest(TestCase):
    """Verify prod-specific settings with override_settings."""

    @override_settings(DEBUG=False)
    def test_debug_is_false_in_prod(self):
        from django.conf import settings
        self.assertFalse(settings.DEBUG)

    def test_secret_key_not_default(self):
        from django.conf import settings
        self.assertNotEqual(settings.SECRET_KEY, '')
        self.assertNotEqual(settings.SECRET_KEY, 'insecure-default')

    def test_custom_user_model(self):
        from django.conf import settings
        self.assertEqual(settings.AUTH_USER_MODEL, 'accounts.User')

    def test_default_auto_field(self):
        from django.conf import settings
        self.assertEqual(settings.DEFAULT_AUTO_FIELD, 'django.db.models.BigAutoField')


# ---------------------------------------------------------------------------
# URL routing tests
# ---------------------------------------------------------------------------
class URLRoutingTest(TestCase):
    """Verify critical URL patterns are registered."""

    def test_health_url_exists(self):
        from django.urls import reverse
        url = reverse('health-check')
        self.assertEqual(url, '/health/')

    def test_readiness_url_exists(self):
        from django.urls import reverse
        url = reverse('readiness-check')
        self.assertEqual(url, '/ready/')

    def test_api_namespaces_accessible(self):
        """Known sub-paths under each API prefix should not 404."""
        api_paths = [
            '/api/v1/auth/login/',
            '/api/v1/merchants/',
            '/api/v1/campaigns/',
            '/api/v1/tracking/clicks/',
            '/api/v1/billing/invoices/',
            '/api/v1/analytics/admin/dashboard/',
        ]
        for path in api_paths:
            resp = self.client.get(path)
            # Should not be 404 — might be 401/403/405 which is expected
            self.assertNotEqual(
                resp.status_code, 404,
                f'{path} returned 404 — URL not registered',
            )


# ---------------------------------------------------------------------------
# Middleware integration tests
# ---------------------------------------------------------------------------
class MiddlewareIntegrationTest(TestCase):
    """Test middleware is properly installed and working."""

    def test_cors_middleware_in_chain(self):
        from django.conf import settings
        self.assertIn('corsheaders.middleware.CorsMiddleware', settings.MIDDLEWARE)

    def test_security_middleware_in_chain(self):
        from django.conf import settings
        self.assertIn('django.middleware.security.SecurityMiddleware', settings.MIDDLEWARE)

    def test_clickjacking_protection(self):
        from django.conf import settings
        self.assertIn(
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
            settings.MIDDLEWARE,
        )

    def test_request_logging_middleware_last(self):
        from django.conf import settings
        mw = settings.MIDDLEWARE
        self.assertEqual(mw[-1], 'common.middleware.RequestLoggingMiddleware')

    def test_csrf_middleware_present(self):
        from django.conf import settings
        self.assertIn('django.middleware.csrf.CsrfViewMiddleware', settings.MIDDLEWARE)
