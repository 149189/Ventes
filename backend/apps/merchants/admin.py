from django.contrib import admin

from .models import MerchantProfile, SKU, PromoRule


@admin.register(MerchantProfile)
class MerchantProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user', 'industry', 'status', 'tier', 'commission_rate', 'created_at')
    list_filter = ('status', 'tier', 'industry', 'billing_model')
    search_fields = ('company_name', 'contact_email')


@admin.register(SKU)
class SKUAdmin(admin.ModelAdmin):
    list_display = ('sku_code', 'name', 'merchant', 'original_price', 'is_active')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'sku_code')


@admin.register(PromoRule)
class PromoRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'merchant', 'promo_type', 'value', 'is_active')
    list_filter = ('promo_type', 'is_active')
