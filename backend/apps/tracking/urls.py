from django.urls import path

from . import views

app_name = 'tracking'

urlpatterns = [
    path('clicks/', views.ClickEventListView.as_view(), name='click-list'),
    path('clicks/<int:pk>/', views.ClickEventDetailView.as_view(), name='click-detail'),
    path('merchant/clicks/', views.MerchantClicksView.as_view(), name='merchant-click-list'),
    path('merchant/clicks/summary/', views.MerchantClickSummaryView.as_view(), name='merchant-click-summary'),
    path('fraud-flags/', views.FraudFlagListView.as_view(), name='fraud-flag-list'),
    path('fraud-flags/<int:pk>/', views.FraudFlagReviewView.as_view(), name='fraud-flag-review'),
    path('fraud-flags/<int:pk>/review/', views.FraudFlagReviewView.as_view(), name='fraud-flag-review-action'),
]
