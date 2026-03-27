from django.urls import path
from . import views

urlpatterns = [
    path('history/<int:request_id>/', views.message_history, name='chat-history'),
]