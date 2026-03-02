from rest_framework.exceptions import APIException


class InvalidHMACSignature(APIException):
    status_code = 403
    default_detail = 'Invalid HMAC signature.'
    default_code = 'invalid_hmac'


class StaleTimestamp(APIException):
    status_code = 403
    default_detail = 'Request timestamp is too old.'
    default_code = 'stale_timestamp'


class DailyBudgetExceeded(APIException):
    status_code = 429
    default_detail = 'Daily budget cap has been reached.'
    default_code = 'budget_exceeded'


class DisputeWindowExpired(APIException):
    status_code = 400
    default_detail = 'Dispute window has expired.'
    default_code = 'dispute_window_expired'
