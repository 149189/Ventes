from rest_framework import serializers

from .models import Campaign, CampaignCreative, ABTestVariant


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = (
            'id', 'name', 'description', 'status', 'target_skus', 'promo_rule',
            'start_date', 'end_date', 'daily_message_limit', 'messages_sent_today',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'messages_sent_today', 'created_at', 'updated_at')


class CampaignCreativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignCreative
        fields = (
            'id', 'campaign', 'name', 'greeting_template', 'pitch_template',
            'close_template', 'is_approved', 'approved_by', 'created_at',
        )
        read_only_fields = ('id', 'is_approved', 'approved_by', 'created_at')


class ABTestVariantSerializer(serializers.ModelSerializer):
    conversion_rate = serializers.SerializerMethodField()

    class Meta:
        model = ABTestVariant
        fields = (
            'id', 'campaign', 'name', 'variant_type', 'config_json',
            'traffic_weight', 'impressions', 'conversions', 'conversion_rate',
            'is_active', 'created_at',
        )
        read_only_fields = ('id', 'impressions', 'conversions', 'created_at')

    def get_conversion_rate(self, obj):
        if obj.impressions == 0:
            return 0.0
        return round(obj.conversions / obj.impressions * 100, 2)
