from .base import *  # noqa: F401,F403

DEBUG = False

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)  # noqa: F405
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
X_FRAME_OPTIONS = 'DENY'

# WhiteNoise — serve static files without nginx
MIDDLEWARE.insert(  # noqa: F405
    MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1,  # noqa: F405
    'whitenoise.middleware.WhiteNoiseMiddleware',
)
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Database — persistent connections
DATABASES['default']['CONN_MAX_AGE'] = env.int('CONN_MAX_AGE', default=600)  # noqa: F405
DATABASES['default']['CONN_HEALTH_CHECKS'] = True  # noqa: F405

# CORS — only explicit origins in production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])  # noqa: F405

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')  # noqa: F405
EMAIL_PORT = env.int('EMAIL_PORT', default=587)  # noqa: F405
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')  # noqa: F405
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')  # noqa: F405
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@salescount.in')  # noqa: F405

# Celery production tuning
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000  # Recycle workers to prevent memory leaks
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Logging — JSON format for production log aggregators
LOGGING['formatters']['json'] = {  # noqa: F405
    '()': 'django.utils.log.ServerFormatter',
    'format': '{asctime} {levelname} {name} {message}',
    'style': '{',
}
LOGGING['root']['level'] = 'WARNING'  # noqa: F405
LOGGING['loggers']['apps']['level'] = 'INFO'  # noqa: F405

# Sentry
SENTRY_DSN = env('SENTRY_DSN', default='')  # noqa: F405
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=env.float('SENTRY_TRACES_RATE', default=0.1),  # noqa: F405
        send_default_pii=False,
        environment=env('SENTRY_ENVIRONMENT', default='production'),  # noqa: F405
    )
