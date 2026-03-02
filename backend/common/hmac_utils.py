import hmac
import hashlib
import time


def generate_hmac_signature(merchant_secret: str, payload: dict) -> str:
    canonical = "&".join(
        f"{k}={v}" for k, v in sorted(payload.items()) if k != 'hmac_signature'
    )
    return hmac.new(
        merchant_secret.encode('utf-8'),
        canonical.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


def verify_hmac_signature(merchant_secret: str, payload: dict, provided_signature: str) -> bool:
    expected = generate_hmac_signature(merchant_secret, payload)
    return hmac.compare_digest(expected, provided_signature)


def verify_timestamp_freshness(timestamp: int, max_age_seconds: int = 300) -> bool:
    return abs(time.time() - timestamp) <= max_age_seconds
