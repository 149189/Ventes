from django.contrib import admin

from .models import Conversation, Message, FollowUpSchedule


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('direction', 'body', 'twilio_sid', 'created_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'phone_number', 'merchant', 'stage', 'is_opted_out', 'started_at')
    list_filter = ('stage', 'is_opted_out')
    search_fields = ('phone_number',)
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'direction', 'body_preview', 'created_at')
    list_filter = ('direction',)

    def body_preview(self, obj):
        return obj.body[:80]


@admin.register(FollowUpSchedule)
class FollowUpScheduleAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'scheduled_at', 'is_sent', 'sent_at')
    list_filter = ('is_sent',)
