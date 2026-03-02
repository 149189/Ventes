from rest_framework import serializers

from .models import DailyMerchantStats, DailyCampaignStats


class DailyMerchantStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyMerchantStats
        fields = '__all__'


class DailyCampaignStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyCampaignStats
        fields = '__all__'


class AdminDashboardSerializer(serializers.Serializer):
    total_conversations = serializers.IntegerField()
    total_clicks = serializers.IntegerField()
    flagged_clicks = serializers.IntegerField()
    total_conversions = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    conversion_rate = serializers.FloatField()
    active_merchants = serializers.IntegerField()


class MerchantDashboardSerializer(serializers.Serializer):
    conversations_today = serializers.IntegerField()
    clicks_today = serializers.IntegerField()
    conversions_today = serializers.IntegerField()
    ctr = serializers.FloatField()
    spend_today = serializers.DecimalField(max_digits=12, decimal_places=2)
    daily_budget_cap = serializers.DecimalField(max_digits=10, decimal_places=2)
    budget_remaining = serializers.DecimalField(max_digits=10, decimal_places=2)
