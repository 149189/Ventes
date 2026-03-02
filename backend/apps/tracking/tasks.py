from celery import shared_task


@shared_task
def calculate_fraud_score(click_event_id):
    """Run all fraud checks on a click event."""
    from .models import ClickEvent
    from .fraud import FraudDetector

    try:
        click = ClickEvent.objects.select_related(
            'redirect_token__conversation',
        ).get(id=click_event_id)
    except ClickEvent.DoesNotExist:
        return

    detector = FraudDetector(click)
    detector.save_results()


@shared_task
def expire_redirect_tokens():
    """Deactivate expired redirect tokens."""
    from django.utils import timezone
    from .models import RedirectToken

    count = RedirectToken.objects.filter(
        is_active=True,
        expires_at__lt=timezone.now(),
    ).update(is_active=False)

    return f"Expired {count} tokens"


@shared_task
def periodic_fraud_sweep():
    """Recalculate fraud scores for recent clicks."""
    from django.utils import timezone
    from datetime import timedelta
    from .models import ClickEvent

    recent_clicks = ClickEvent.objects.filter(
        clicked_at__gte=timezone.now() - timedelta(hours=1),
        fraud_score=0.0,
    ).values_list('id', flat=True)

    for click_id in recent_clicks:
        calculate_fraud_score.delay(click_id)
