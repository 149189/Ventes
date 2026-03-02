from django.urls import path

from . import views

app_name = 'billing'

urlpatterns = [
    path('postback/', views.PostbackView.as_view(), name='postback'),
    path('coupon-redeem/', views.CouponRedeemView.as_view(), name='coupon-redeem'),
    path('conversions/', views.ConversionListView.as_view(), name='conversions'),
    path('invoices/', views.InvoiceListView.as_view(), name='invoices'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('disputes/', views.DisputeListView.as_view(), name='disputes'),
    path('disputes/create/', views.DisputeCreateView.as_view(), name='dispute-create'),
    path('disputes/<int:pk>/', views.DisputeResolveView.as_view(), name='dispute-resolve'),
    path('disputes/<int:pk>/resolve/', views.DisputeResolveView.as_view(), name='dispute-resolve-action'),
    path('revenue-stats/', views.RevenueStatsView.as_view(), name='revenue-stats'),
    path('razorpay/webhook/', views.RazorpayWebhookView.as_view(), name='razorpay-webhook'),
]
