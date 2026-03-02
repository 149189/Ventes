"""Razorpay API integration for billing and invoicing."""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def get_razorpay_client():
    import razorpay
    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
    )
    return client


def create_customer(merchant) -> str:
    """Create a Razorpay customer for the merchant."""
    client = get_razorpay_client()
    customer = client.customer.create({
        'name': merchant.company_name,
        'email': merchant.contact_email,
        'contact': merchant.contact_phone,
        'notes': {'merchant_id': str(merchant.id)},
    })
    return customer['id']


def create_invoice(merchant, line_items: list[dict]):
    """Create a Razorpay invoice for the merchant."""
    client = get_razorpay_client()

    rzp_line_items = []
    for item in line_items:
        rzp_line_items.append({
            'name': item['description'],
            'amount': int(item['amount'] * 100),  # Razorpay uses paise
            'currency': 'INR',
            'quantity': 1,
        })

    invoice_data = {
        'type': 'invoice',
        'customer_id': merchant.razorpay_customer_id,
        'line_items': rzp_line_items,
        'currency': 'INR',
        'sms_notify': 1,
        'email_notify': 1,
        'expire_by': None,  # No expiry, they pay when ready
        'notes': {
            'merchant_id': str(merchant.id),
        },
    }

    invoice = client.invoice.create(invoice_data)
    return invoice


def verify_webhook_signature(payload_body: str, signature: str) -> bool:
    """Verify Razorpay webhook signature."""
    client = get_razorpay_client()
    try:
        client.utility.verify_webhook_signature(
            payload_body,
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET,
        )
        return True
    except Exception:
        return False


def fetch_payment(payment_id: str) -> dict:
    """Fetch payment details from Razorpay."""
    client = get_razorpay_client()
    return client.payment.fetch(payment_id)
