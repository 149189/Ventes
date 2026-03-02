from django.urls import path

from . import views

urlpatterns = [
    path('<uuid:token>/', views.RedirectView.as_view(), name='redirect'),
]
