from django.conf import settings
from django.db import models


class ConversionEvent(models.Model):
    class Source(models.TextChoices):
        POSTBACK = 'postback', 'Postback'
        COUPON = 'coupon', 'Coupon Redemption'

    click_event = models.ForeignKey(
        'tracking.ClickEvent', on_delete=models.SET_NULL, null=True, related_name='conversions',
    )
    conversation = models.ForeignKey(
        'conversations.Conversation', on_delete=models.SET_NULL, null=True,
    )
    merchant = models.ForeignKey(
        'merchants.MerchantProfile', on_delete=models.CASCADE, related_name='conversions',
    )
    source = models.CharField(max_length=20, choices=Source.choices)
    order_id = models.CharField(max_length=255)
    order_amount = models.DecimalField(max_digits=10, decimal_places=2)
    coupon_code = models.CharField(max_length=50, blank=True)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_valid = models.BooleanField(default=True)
    is_disputed = models.BooleanField(default=False)
    converted_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'conversion_events'
        indexes = [
            models.Index(fields=['merchant', 'converted_at']),
        ]

    def __str__(self):
        return f"Conversion {self.order_id} (${self.order_amount})"


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SENT = 'sent', 'Sent'
        PAID = 'paid', 'Paid'
        OVERDUE = 'overdue', 'Overdue'
        DISPUTED = 'disputed', 'Disputed'

    merchant = models.ForeignKey(
        'merchants.MerchantProfile', on_delete=models.CASCADE, related_name='invoices',
    )
    razorpay_invoice_id = models.CharField(max_length=255, blank=True)
    invoice_number = models.CharField(max_length=50, unique=True)
    period_start = models.DateField()
    period_end = models.DateField()
    total_clicks = models.IntegerField(default=0)
    total_conversions = models.IntegerField(default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    pdf_url = models.URLField(blank=True)
    due_date = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'invoices'

    def __str__(self):
        return f"Invoice {self.invoice_number} - ${self.total}"


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    conversion_event = models.ForeignKey(
        ConversionEvent, on_delete=models.SET_NULL, null=True, blank=True,
    )
    click_event = models.ForeignKey(
        'tracking.ClickEvent', on_delete=models.SET_NULL, null=True, blank=True,
    )
    description = models.CharField(max_length=255)
    billing_type = models.CharField(max_length=10, choices=[('cpa', 'CPA'), ('cpc', 'CPC')])
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'invoice_lines'


class DisputeRecord(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        UNDER_REVIEW = 'under_review', 'Under Review'
        UPHELD = 'upheld', 'Upheld'
        REJECTED = 'rejected', 'Rejected'

    conversion_event = models.ForeignKey(
        ConversionEvent, on_delete=models.CASCADE, related_name='disputes',
    )
    merchant = models.ForeignKey(
        'merchants.MerchantProfile', on_delete=models.CASCADE, related_name='disputes',
    )
    reason = models.TextField()
    evidence = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    credit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    filed_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'dispute_records'

    def __str__(self):
        return f"Dispute {self.id} - {self.get_status_display()}"
