# urls.py

from django.urls import path
from .views import *

urlpatterns = [

    path("request/", create_barter_request),

    path("requests/", get_barter_requests),

    path("requests/received/", received_barter_requests),

    path("request/<int:request_id>/", update_barter_status),
    path("get_accepted_request/", get_accepted_request),
    path('saved-products/', saved_products),
    path('saved-products/add/', save_product),
    path('saved-products/<int:pk>/', remove_saved_product),
    path('saved-products/toggle/', toggle_save_product),
    path('saved-products/is-saved/', is_saved),

]