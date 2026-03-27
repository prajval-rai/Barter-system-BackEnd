from django.urls import path
from .views import *


urlpatterns = [
    path("login/",google_login),
    path("me/",me),
    path("logout/",logout),
    path("upsertProfile/",profile),
    path("update_profile/",update_profile),
]