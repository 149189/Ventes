from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class WhatsAppWebhookThrottle(AnonRateThrottle):
    rate = '60/minute'


class PostbackThrottle(AnonRateThrottle):
    rate = '100/minute'


class MerchantAPIThrottle(UserRateThrottle):
    rate = '200/minute'


class AdminAPIThrottle(UserRateThrottle):
    rate = '500/minute'
