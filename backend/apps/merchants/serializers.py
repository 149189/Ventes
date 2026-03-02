from rest_framework import serializers

from .models import MerchantProfile, SKU, PromoRule


class MerchantProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantProfile
        fields = (
            'id', 'company_name', 'company_website', 'contact_email',
            'contact_phone', 'billing_address', 'tax_id', 'status', 'tier',
            'commission_rate', 'auto_optimize_commission', 'daily_budget_cap',
            'billing_model', 'dispute_window_days', 'whatsapp_number',
            'approved_at', 'created_at',
        )
        read_only_fields = ('id', 'status', 'tier', 'approved_at', 'created_at')


class MerchantOnboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantProfile
        fields = (
            'company_name', 'company_website', 'contact_email',
            'contact_phone', 'billing_address', 'tax_id', 'whatsapp_number',
        )


class BillingSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantProfile
        fields = ('commission_rate', 'auto_optimize_commission', 'daily_budget_cap', 'billing_model')

    def validate_commission_rate(self, value):
        if value < 4 or value > 10:
            raise serializers.ValidationError('Commission rate must be between 4% and 10%.')
        return value


class SKUSerializer(serializers.ModelSerializer):
    class Meta:
        model = SKU
        fields = (
            'id', 'sku_code', 'name', 'description', 'category',
            'original_price', 'discounted_price', 'landing_url',
            'image_url', 'stock_quantity', 'is_active', 'created_at',
        )
        read_only_fields = ('id', 'created_at')


class PromoRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoRule
        fields = (
            'id', 'name', 'promo_type', 'value', 'coupon_prefix',
            'max_uses', 'uses_count', 'valid_from', 'valid_until',
            'applicable_skus', 'is_active', 'created_at',
        )
        read_only_fields = ('id', 'uses_count', 'created_at')
