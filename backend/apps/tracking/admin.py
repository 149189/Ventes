from django.contrib import admin

from .models import RedirectToken, ClickEvent, FraudFlag


@admin.register(RedirectToken)
class RedirectTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'sku', 'merchant', 'is_active', 'created_at', 'expires_at')
    list_filter = ('is_active',)


@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'redirect_token', 'ip_address', 'is_fraudulent', 'fraud_score', 'clicked_at')
    list_filter = ('is_fraudulent',)


@admin.register(FraudFlag)
class FraudFlagAdmin(admin.ModelAdmin):
    list_display = ('click_event', 'flag_type', 'reviewed', 'created_at')
    list_filter = ('flag_type', 'reviewed')
