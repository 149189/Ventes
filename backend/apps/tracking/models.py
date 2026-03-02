import uuid

from django.conf import settings
from django.db import models


class RedirectToken(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    conversation = models.ForeignKey(
        'conversations.Conversation', on_delete=models.CASCADE, related_name='redirect_tokens',
    )
    sku = models.ForeignKey('merchants.SKU', on_delete=models.CASCADE)
    merchant = models.ForeignKey('merchants.MerchantProfile', on_delete=models.CASCADE)
    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.SET_NULL, null=True)
    destination_url = models.URLField(max_length=2048)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'redirect_tokens'

    def __str__(self):
        return f"Token {self.token} -> {self.sku.name}"


class ClickEvent(models.Model):
    redirect_token = models.ForeignKey(RedirectToken, on_delete=models.CASCADE, related_name='clicks')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    referer = models.URLField(blank=True, max_length=2048)
    country_code = models.CharField(max_length=5, blank=True)
    is_fraudulent = models.BooleanField(default=False)
    fraud_score = models.FloatField(default=0.0)
    fraud_reasons = models.JSONField(default=list)
    clicked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'click_events'
        indexes = [
            models.Index(fields=['clicked_at']),
            models.Index(fields=['redirect_token', 'ip_address']),
        ]

    def __str__(self):
        return f"Click {self.id} on {self.redirect_token.token}"


class FraudFlag(models.Model):
    class FlagType(models.TextChoices):
        RATE_LIMIT = 'rate_limit', 'Rate Limit'
        TOKEN_REUSE = 'token_reuse', 'Token Reuse'
        LOW_DWELL = 'low_dwell', 'Low Dwell Time'
        IP_CLUSTER = 'ip_cluster', 'IP Cluster'
        BOT_UA = 'bot_ua', 'Bot User Agent'

    click_event = models.ForeignKey(ClickEvent, on_delete=models.CASCADE, related_name='fraud_flags')
    flag_type = models.CharField(max_length=30, choices=FlagType.choices)
    details = models.JSONField(default=dict)
    reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fraud_flags'

    def __str__(self):
        return f"{self.get_flag_type_display()} on Click {self.click_event_id}"
