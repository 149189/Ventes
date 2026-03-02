from django.urls import path

from . import views

app_name = 'conversations'

urlpatterns = [
    path('', views.ConversationListView.as_view(), name='list'),
    path('simulate/', views.SimulateChatView.as_view(), name='simulate'),
    path('<int:pk>/', views.ConversationDetailView.as_view(), name='detail'),
    path('<int:pk>/handoff/', views.HandoffView.as_view(), name='handoff'),
    path('<int:pk>/agent-reply/', views.AgentReplyView.as_view(), name='agent-reply'),
]
