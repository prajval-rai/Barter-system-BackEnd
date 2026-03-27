# urls.py

from django.urls import path
from .views import *

urlpatterns = [

    path("request/", create_barter_request),

    path("requests/", get_barter_requests),

    path("requests/received/", received_barter_requests),

    path("request/<int:request_id>/", update_barter_status),
    path("get_accepted_request/", get_accepted_request),

]