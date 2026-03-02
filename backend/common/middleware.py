import uuid
import logging
import time

logger = logging.getLogger('salescount.request')


class RequestIDMiddleware:
    """Attach a unique request ID to every request for distributed tracing."""

    HEADER = 'X-Request-ID'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get(
            f'HTTP_{self.HEADER.upper().replace("-", "_")}',
            str(uuid.uuid4()),
        )
        request.request_id = request_id

        response = self.get_response(request)
        response[self.HEADER] = request_id
        return response


class RequestLoggingMiddleware:
    """Log every request with method, path, status, and duration."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        # Skip health check noise
        if request.path in ('/health/', '/ready/'):
            return response

        logger.info(
            '%s %s %s %sms uid=%s',
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            getattr(request, 'request_id', '-'),
        )
        return response
