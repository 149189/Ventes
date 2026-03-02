import time

from django.db import connection
from django.core.cache import cache
from django.http import JsonResponse


def health_check(request):
    """Liveness probe — always returns 200 if the process is up."""
    return JsonResponse({'status': 'ok'})


def readiness_check(request):
    """Readiness probe — verifies database and cache connectivity."""
    checks = {}

    # Database
    try:
        start = time.monotonic()
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        checks['database'] = {
            'status': 'ok',
            'latency_ms': round((time.monotonic() - start) * 1000, 2),
        }
    except Exception as e:
        checks['database'] = {'status': 'error', 'detail': str(e)}

    # Cache
    try:
        start = time.monotonic()
        cache.set('_health_check', '1', timeout=5)
        val = cache.get('_health_check')
        checks['cache'] = {
            'status': 'ok' if val == '1' else 'degraded',
            'latency_ms': round((time.monotonic() - start) * 1000, 2),
        }
    except Exception as e:
        checks['cache'] = {'status': 'error', 'detail': str(e)}

    all_ok = all(c['status'] == 'ok' for c in checks.values())
    return JsonResponse(
        {'status': 'ok' if all_ok else 'degraded', 'checks': checks},
        status=200 if all_ok else 503,
    )
