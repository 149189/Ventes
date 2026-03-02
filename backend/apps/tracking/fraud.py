"""Fraud detection pipeline for click events."""
from datetime import timedelta

from django.utils import timezone

from .models import ClickEvent, FraudFlag


class FraudDetector:
    def __init__(self, click_event: ClickEvent):
        self.click = click_event
        self.flags: list[tuple[str, dict]] = []

    def check_rate_limit(self, max_clicks_per_hour: int = 10) -> bool:
        recent_count = ClickEvent.objects.filter(
            redirect_token__conversation__phone_number=(
                self.click.redirect_token.conversation.phone_number
            ),
            clicked_at__gte=timezone.now() - timedelta(hours=1),
        ).count()
        if recent_count > max_clicks_per_hour:
            self.flags.append((
                'rate_limit',
                {'count': recent_count, 'threshold': max_clicks_per_hour},
            ))
            return True
        return False

    def check_token_reuse(self) -> bool:
        previous_clicks = self.click.redirect_token.clicks.exclude(id=self.click.id).count()
        if previous_clicks > 0:
            self.flags.append((
                'token_reuse',
                {'previous_clicks': previous_clicks},
            ))
            return True
        return False

    def check_ip_cluster(self, max_clicks_per_ip: int = 20) -> bool:
        ip_count = ClickEvent.objects.filter(
            ip_address=self.click.ip_address,
            clicked_at__gte=timezone.now() - timedelta(hours=24),
        ).count()
        if ip_count > max_clicks_per_ip:
            self.flags.append((
                'ip_cluster',
                {'count': ip_count, 'threshold': max_clicks_per_ip},
            ))
            return True
        return False

    def check_bot_user_agent(self) -> bool:
        bot_patterns = [
            'bot', 'crawler', 'spider', 'headless', 'phantom',
            'selenium', 'puppeteer', 'scrapy', 'wget', 'curl',
            'httpclient', 'python-requests', 'go-http-client',
        ]
        ua_lower = self.click.user_agent.lower()
        if not ua_lower or any(pattern in ua_lower for pattern in bot_patterns):
            self.flags.append((
                'bot_ua',
                {'user_agent': self.click.user_agent or '(empty)'},
            ))
            return True
        return False

    def check_low_dwell_time(self, min_seconds: int = 2) -> bool:
        """Layer 5: Flag if click happened too fast after the previous one.

        Low dwell time suggests automated clicking — a real user needs
        at least a few seconds to read a message and click.
        """
        conversation = self.click.redirect_token.conversation
        previous_click = (
            ClickEvent.objects.filter(
                redirect_token__conversation=conversation,
                clicked_at__lt=self.click.clicked_at,
            )
            .order_by('-clicked_at')
            .first()
        )
        if previous_click:
            delta = (self.click.clicked_at - previous_click.clicked_at).total_seconds()
            if delta < min_seconds:
                self.flags.append((
                    'low_dwell',
                    {'seconds_since_previous': round(delta, 2), 'threshold': min_seconds},
                ))
                return True
        return False

    def calculate_score(self) -> float:
        weights = {
            'rate_limit': 0.3,
            'token_reuse': 0.25,
            'ip_cluster': 0.25,
            'bot_ua': 0.5,
            'low_dwell': 0.2,
        }
        score = sum(weights.get(flag_type, 0.1) for flag_type, _ in self.flags)
        return min(score, 1.0)

    def run_all_checks(self) -> tuple[float, list]:
        """Run all 5 fraud detection layers."""
        self.check_rate_limit()
        self.check_token_reuse()
        self.check_ip_cluster()
        self.check_bot_user_agent()
        self.check_low_dwell_time()
        score = self.calculate_score()
        return score, self.flags

    def save_results(self) -> None:
        score, flags = self.run_all_checks()
        self.click.fraud_score = score
        self.click.is_fraudulent = score >= 0.5
        self.click.fraud_reasons = [{'type': t, 'details': d} for t, d in flags]
        self.click.save()

        for flag_type, details in flags:
            FraudFlag.objects.create(
                click_event=self.click,
                flag_type=flag_type,
                details=details,
            )
