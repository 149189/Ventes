from celery import shared_task


@shared_task
def reset_daily_message_counts():
    """Reset messages_sent_today for all campaigns at midnight."""
    from .models import Campaign
    Campaign.objects.filter(status=Campaign.Status.ACTIVE).update(messages_sent_today=0)
