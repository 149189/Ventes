from django.urls import path

from . import views

app_name = 'whatsapp'

urlpatterns = [
    path('webhook/', views.TwilioWebhookView.as_view(), name='webhook'),
    path('status/', views.TwilioStatusCallbackView.as_view(), name='status'),
]
