from django.conf import settings
from django.db import models


class Campaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        ENDED = 'ended', 'Ended'

    merchant = models.ForeignKey(
        'merchants.MerchantProfile', on_delete=models.CASCADE, related_name='campaigns',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    target_skus = models.ManyToManyField('merchants.SKU', blank=True, related_name='campaigns')
    promo_rule = models.ForeignKey(
        'merchants.PromoRule', on_delete=models.SET_NULL, null=True, blank=True,
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    daily_message_limit = models.IntegerField(default=1000)
    messages_sent_today = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'campaigns'

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class CampaignCreative(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='creatives')
    name = models.CharField(max_length=100)
    greeting_template = models.TextField()
    pitch_template = models.TextField()
    close_template = models.TextField()
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'campaign_creatives'

    def __str__(self):
        return f"{self.name} ({self.campaign.name})"


class ABTestVariant(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='ab_variants')
    name = models.CharField(max_length=100)
    variant_type = models.CharField(max_length=50)
    config_json = models.JSONField(default=dict)
    traffic_weight = models.FloatField(default=0.5)
    impressions = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ab_test_variants'

    def __str__(self):
        return f"{self.name} ({self.campaign.name})"
