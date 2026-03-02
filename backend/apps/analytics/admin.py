from django.contrib import admin

from .models import DailyMerchantStats, DailyCampaignStats, HourlyClickStats


@admin.register(DailyMerchantStats)
class DailyMerchantStatsAdmin(admin.ModelAdmin):
    list_display = ('merchant', 'date', 'clicks_total', 'conversions', 'spend', 'conversion_rate')
    list_filter = ('date',)


@admin.register(DailyCampaignStats)
class DailyCampaignStatsAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'date', 'impressions', 'clicks', 'conversions', 'spend')
    list_filter = ('date',)


@admin.register(HourlyClickStats)
class HourlyClickStatsAdmin(admin.ModelAdmin):
    list_display = ('merchant', 'hour', 'clicks', 'valid_clicks')
