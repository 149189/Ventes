from rest_framework import serializers

from .models import ConversionEvent, Invoice, InvoiceLine, DisputeRecord


class ConversionEventSerializer(serializers.ModelSerializer):
    merchant_name = serializers.CharField(source='merchant.company_name', read_only=True)

    class Meta:
        model = ConversionEvent
        fields = (
            'id', 'click_event', 'conversation', 'merchant', 'merchant_name',
            'source', 'order_id', 'order_amount', 'coupon_code',
            'commission_amount', 'is_valid', 'is_disputed', 'converted_at',
            'created_at',
        )
        read_only_fields = fields


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = ('id', 'description', 'billing_type', 'quantity', 'unit_price', 'line_total')


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)
    merchant_name = serializers.CharField(source='merchant.company_name', read_only=True)

    class Meta:
        model = Invoice
        fields = (
            'id', 'merchant', 'merchant_name', 'invoice_number',
            'period_start', 'period_end', 'total_clicks',
            'total_conversions', 'subtotal', 'credits', 'total', 'status',
            'pdf_url', 'due_date', 'paid_at', 'created_at', 'lines',
        )


class DisputeRecordSerializer(serializers.ModelSerializer):
    merchant_name = serializers.CharField(source='merchant.company_name', read_only=True)

    class Meta:
        model = DisputeRecord
        fields = (
            'id', 'conversion_event', 'merchant', 'merchant_name', 'reason',
            'evidence', 'status', 'resolution_notes', 'resolved_by',
            'credit_amount', 'filed_at', 'resolved_at',
        )
        read_only_fields = ('id', 'merchant', 'merchant_name', 'status', 'resolved_by', 'credit_amount', 'filed_at', 'resolved_at')


class PostbackSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    order_id = serializers.CharField(max_length=255)
    order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    timestamp = serializers.IntegerField()
    hmac_signature = serializers.CharField(max_length=64)


class CouponRedeemSerializer(serializers.Serializer):
    coupon_code = serializers.CharField(max_length=50)
    order_id = serializers.CharField(max_length=255)
    order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    merchant_id = serializers.IntegerField()
    timestamp = serializers.IntegerField()
    hmac_signature = serializers.CharField(max_length=64)
