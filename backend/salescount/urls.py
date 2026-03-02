from django.contrib import admin
from django.conf import settings
from django.urls import path, include

from common.health import health_check, readiness_check

urlpatterns = [
    # Health probes (outside /api/ — no auth required)
    path('health/', health_check, name='health-check'),
    path('ready/', readiness_check, name='readiness-check'),

    path('django-admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/merchants/', include('apps.merchants.urls')),
    path('api/v1/campaigns/', include('apps.campaigns.urls')),
    path('api/v1/whatsapp/', include('apps.conversations.urls')),
    path('api/v1/conversations/', include('apps.conversations.urls_api')),
    path('api/v1/tracking/', include('apps.tracking.urls')),
    path('api/v1/billing/', include('apps.billing.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    # Click tracking redirect (outside /api/)
    path('t/', include('apps.tracking.urls_redirect')),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
