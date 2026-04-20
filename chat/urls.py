from django.urls import path
from . import views

urlpatterns = [
    path('history/<int:request_id>/', views.message_history, name='chat-history'),
    path("request/<int:pk>/otp/generate/", views.generate_otp),
  path("request/<int:pk>/otp/verify/",   views.verify_otp),
  path("ws-token/",   views.get_ws_token),
#   path("barter/rate/<int:pk>/",                 views.rate_trade)
]