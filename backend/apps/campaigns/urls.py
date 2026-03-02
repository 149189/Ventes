from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'campaigns'

router = DefaultRouter()
router.register('', views.CampaignViewSet, basename='campaign')

urlpatterns = [
    path('', include(router.urls)),
    path('<int:campaign_pk>/creatives/', views.CampaignCreativeViewSet.as_view({
        'get': 'list', 'post': 'create',
    }), name='creatives-list'),
    path('<int:campaign_pk>/creatives/<int:pk>/', views.CampaignCreativeViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 'delete': 'destroy',
    }), name='creatives-detail'),
    path('<int:campaign_pk>/ab-variants/', views.ABTestVariantViewSet.as_view({
        'get': 'list', 'post': 'create',
    }), name='ab-variants-list'),
    path('<int:campaign_pk>/ab-variants/<int:pk>/', views.ABTestVariantViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 'delete': 'destroy',
    }), name='ab-variants-detail'),
]
