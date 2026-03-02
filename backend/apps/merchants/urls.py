from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'merchants'

router = DefaultRouter()
router.register('skus', views.SKUViewSet, basename='sku')
router.register('promo-rules', views.PromoRuleViewSet, basename='promo-rule')

urlpatterns = [
    path('profile/', views.MerchantProfileView.as_view(), name='profile'),
    path('onboard/', views.MerchantOnboardView.as_view(), name='onboard'),
    path('billing-settings/', views.BillingSettingsView.as_view(), name='billing-settings'),
    path('', include(router.urls)),
    # Admin endpoints
    path('admin/list/', views.AdminMerchantListView.as_view(), name='admin-list'),
    path('admin/<int:pk>/<str:action_type>/', views.AdminMerchantActionView.as_view(), name='admin-action'),
]
