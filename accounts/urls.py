from django.urls import path
from .views import *


urlpatterns = [
    path("login/",google_login),
    path("me/",me),
    path("logout/",logout),
    path("upsertProfile/",profile),
    path("update_profile/",update_profile),
    path('notifications/', notifications),
    path('notifications/<int:pk>/', notification_detail),
    path('notifications/<int:pk>/read/', mark_notification_read),
    path('notifications/read-all/', mark_all_read),
    path('notifications/unread-count/', unread_count),
]