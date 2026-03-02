from rest_framework import serializers

from .models import ClickEvent, FraudFlag, RedirectToken


class RedirectTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = RedirectToken
        fields = ('id', 'token', 'sku', 'merchant', 'destination_url', 'is_active', 'created_at', 'expires_at')


class ClickEventSerializer(serializers.ModelSerializer):
    sku_name = serializers.CharField(source='redirect_token.sku.name', read_only=True)
    merchant_name = serializers.CharField(source='redirect_token.merchant.company_name', read_only=True)
    campaign_name = serializers.SerializerMethodField()
    token = serializers.UUIDField(source='redirect_token.token', read_only=True)
    destination_url = serializers.URLField(source='redirect_token.destination_url', read_only=True)
    fraud_flags = serializers.SerializerMethodField()

    class Meta:
        model = ClickEvent
        fields = (
            'id', 'token', 'sku_name', 'merchant_name', 'campaign_name',
            'ip_address', 'user_agent', 'referer', 'country_code',
            'destination_url', 'is_fraudulent', 'fraud_score', 'fraud_reasons',
            'fraud_flags', 'clicked_at',
        )

    def get_campaign_name(self, obj):
        campaign = obj.redirect_token.campaign
        return campaign.name if campaign else None

    def get_fraud_flags(self, obj):
        return list(obj.fraud_flags.values_list('flag_type', flat=True))


class ClickEventSummarySerializer(serializers.ModelSerializer):
    """Lighter serializer for merchant view — hides IP and user agent."""
    sku_name = serializers.CharField(source='redirect_token.sku.name', read_only=True)
    campaign_name = serializers.SerializerMethodField()
    token = serializers.UUIDField(source='redirect_token.token', read_only=True)
    destination_url = serializers.URLField(source='redirect_token.destination_url', read_only=True)

    class Meta:
        model = ClickEvent
        fields = (
            'id', 'token', 'sku_name', 'campaign_name',
            'destination_url', 'is_fraudulent', 'fraud_score', 'clicked_at',
        )

    def get_campaign_name(self, obj):
        campaign = obj.redirect_token.campaign
        return campaign.name if campaign else None


class FraudFlagSerializer(serializers.ModelSerializer):
    click_event_id = serializers.IntegerField(source='click_event.id', read_only=True)

    class Meta:
        model = FraudFlag
        fields = (
            'id', 'click_event', 'click_event_id', 'flag_type', 'details',
            'reviewed', 'reviewed_by', 'reviewed_at', 'created_at',
        )
        read_only_fields = ('id', 'click_event', 'click_event_id', 'flag_type', 'details', 'created_at')
