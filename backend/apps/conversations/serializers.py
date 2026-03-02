from rest_framework import serializers

from .models import Conversation, Message, FollowUpSchedule


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = (
            'id', 'conversation', 'direction', 'body', 'twilio_sid',
            'media_url', 'stage_at_send', 'openai_tokens_used', 'created_at',
        )
        read_only_fields = ('id', 'created_at')


class ConversationListSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    merchant_name = serializers.CharField(source='merchant.company_name', read_only=True)

    class Meta:
        model = Conversation
        fields = (
            'id', 'phone_number', 'merchant', 'merchant_name', 'campaign',
            'stage', 'is_opted_out', 'started_at', 'last_message_at', 'message_count',
        )

    def get_message_count(self, obj):
        return obj.messages.count()


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    merchant_name = serializers.CharField(source='merchant.company_name', read_only=True)

    class Meta:
        model = Conversation
        fields = (
            'id', 'phone_number', 'merchant', 'merchant_name', 'campaign',
            'ab_variant', 'stage', 'context_json', 'coupon_code',
            'is_opted_out', 'handed_off_to', 'started_at', 'last_message_at',
            'ended_at', 'messages',
        )


class FollowUpScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUpSchedule
        fields = ('id', 'conversation', 'scheduled_at', 'message_template', 'is_sent', 'sent_at')
        read_only_fields = ('id', 'is_sent', 'sent_at')
