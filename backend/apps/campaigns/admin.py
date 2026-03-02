from django.contrib import admin

from .models import Campaign, CampaignCreative, ABTestVariant


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'merchant', 'status', 'start_date', 'end_date', 'created_at')
    list_filter = ('status',)
    search_fields = ('name',)


@admin.register(CampaignCreative)
class CampaignCreativeAdmin(admin.ModelAdmin):
    list_display = ('name', 'campaign', 'is_approved', 'created_at')
    list_filter = ('is_approved',)


@admin.register(ABTestVariant)
class ABTestVariantAdmin(admin.ModelAdmin):
    list_display = ('name', 'campaign', 'variant_type', 'traffic_weight', 'impressions', 'conversions')
    list_filter = ('variant_type', 'is_active')
