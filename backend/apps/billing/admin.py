from django.contrib import admin

from .models import ConversionEvent, Invoice, InvoiceLine, DisputeRecord


@admin.register(ConversionEvent)
class ConversionEventAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'merchant', 'source', 'order_amount', 'commission_amount', 'is_valid', 'converted_at')
    list_filter = ('source', 'is_valid', 'is_disputed')
    search_fields = ('order_id',)


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'merchant', 'total', 'status', 'due_date', 'created_at')
    list_filter = ('status',)
    search_fields = ('invoice_number',)
    inlines = [InvoiceLineInline]


@admin.register(DisputeRecord)
class DisputeRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'merchant', 'status', 'credit_amount', 'filed_at', 'resolved_at')
    list_filter = ('status',)
