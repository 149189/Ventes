from .base import *  # noqa: F401,F403

DEBUG = True

try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ['debug_toolbar']  # noqa: F405
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa: F405
except ImportError:
    pass

INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Use SQLite for local dev (override Docker-based DATABASE_URL from .env)
DATABASES = {  # noqa: F405
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
    }
}

# Override Redis URLs to use REDIS_URL env var instead of hardcoded localhost
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')  # noqa: F405
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')  # noqa: F405

# Disable Redis cache in dev if Redis is not available
CACHES = {  # noqa: F405
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Allow all origins in dev
CORS_ALLOW_ALL_ORIGINS = True

# Email backend for dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
