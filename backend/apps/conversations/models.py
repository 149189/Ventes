from django.conf import settings
from django.db import models


class Conversation(models.Model):
    class Stage(models.TextChoices):
        GREETING = 'greeting', 'Greeting'
        QUALIFYING = 'qualifying', 'Qualifying'
        NARROWING = 'narrowing', 'Narrowing'
        PITCHING = 'pitching', 'Pitching'
        CLOSING = 'closing', 'Closing'
        OBJECTION_HANDLING = 'objection_handling', 'Objection Handling'
        FOLLOWUP = 'followup', 'Follow Up'
        HANDED_OFF = 'handed_off', 'Handed Off'
        ENDED = 'ended', 'Ended'

    phone_number = models.CharField(max_length=20, db_index=True)
    campaign = models.ForeignKey(
        'campaigns.Campaign', on_delete=models.SET_NULL, null=True, related_name='conversations',
    )
    merchant = models.ForeignKey(
        'merchants.MerchantProfile', on_delete=models.CASCADE, related_name='conversations',
    )
    ab_variant = models.ForeignKey(
        'campaigns.ABTestVariant', on_delete=models.SET_NULL, null=True, blank=True,
    )
    stage = models.CharField(max_length=30, choices=Stage.choices, default=Stage.GREETING)
    context_json = models.JSONField(default=dict)
    recommended_skus = models.ManyToManyField('merchants.SKU', blank=True)
    coupon_code = models.CharField(max_length=50, blank=True)
    is_opted_out = models.BooleanField(default=False)
    handed_off_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'conversations'

    def __str__(self):
        return f"Conv {self.id} - {self.phone_number} ({self.get_stage_display()})"


class Message(models.Model):
    class Direction(models.TextChoices):
        INBOUND = 'inbound', 'Inbound'
        OUTBOUND = 'outbound', 'Outbound'
        AGENT = 'agent', 'Agent'

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    direction = models.CharField(max_length=10, choices=Direction.choices)
    body = models.TextField()
    twilio_sid = models.CharField(max_length=64, blank=True)
    media_url = models.URLField(blank=True)
    stage_at_send = models.CharField(max_length=30, blank=True)
    openai_tokens_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        ordering = ('created_at',)

    def __str__(self):
        return f"{self.get_direction_display()}: {self.body[:50]}"


class FollowUpSchedule(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='followups')
    scheduled_at = models.DateTimeField()
    message_template = models.TextField()
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'followup_schedules'

    def __str__(self):
        return f"Followup for Conv {self.conversation_id} at {self.scheduled_at}"
