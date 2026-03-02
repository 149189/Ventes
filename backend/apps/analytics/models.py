from django.db import models


class DailyMerchantStats(models.Model):
    merchant = models.ForeignKey(
        'merchants.MerchantProfile', on_delete=models.CASCADE, related_name='daily_stats',
    )
    date = models.DateField()
    conversations_started = models.IntegerField(default=0)
    conversations_converted = models.IntegerField(default=0)
    messages_sent = models.IntegerField(default=0)
    clicks_total = models.IntegerField(default=0)
    clicks_valid = models.IntegerField(default=0)
    clicks_fraudulent = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    revenue_gross = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ctr = models.FloatField(default=0.0)
    conversion_rate = models.FloatField(default=0.0)

    class Meta:
        db_table = 'daily_merchant_stats'
        unique_together = ('merchant', 'date')

    def __str__(self):
        return f"{self.merchant} - {self.date}"


class DailyCampaignStats(models.Model):
    campaign = models.ForeignKey(
        'campaigns.Campaign', on_delete=models.CASCADE, related_name='daily_stats',
    )
    date = models.DateField()
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ctr = models.FloatField(default=0.0)
    conversion_rate = models.FloatField(default=0.0)

    class Meta:
        db_table = 'daily_campaign_stats'
        unique_together = ('campaign', 'date')

    def __str__(self):
        return f"{self.campaign} - {self.date}"


class HourlyClickStats(models.Model):
    merchant = models.ForeignKey(
        'merchants.MerchantProfile', on_delete=models.CASCADE,
    )
    hour = models.DateTimeField()
    clicks = models.IntegerField(default=0)
    valid_clicks = models.IntegerField(default=0)

    class Meta:
        db_table = 'hourly_click_stats'
        unique_together = ('merchant', 'hour')
