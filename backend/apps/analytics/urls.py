from django.urls import path

from . import views

app_name = 'analytics'

urlpatterns = [
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/trends/', views.AdminTrendsView.as_view(), name='admin-trends'),
    path('admin/funnel/', views.AdminFunnelView.as_view(), name='admin-funnel'),
    path('admin/top-merchants/', views.TopMerchantsView.as_view(), name='top-merchants'),
    path('merchant/dashboard/', views.MerchantDashboardView.as_view(), name='merchant-dashboard'),
    path('merchant/trends/', views.MerchantTrendsView.as_view(), name='merchant-trends'),
    path('merchant/spending/', views.MerchantSpendingView.as_view(), name='merchant-spending'),
]
