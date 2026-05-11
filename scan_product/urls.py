# Add this to your products/urls.py

from django.urls import path
from .views import *   # or wherever you put the view

urlpatterns = [
    # ... your existing urls ...
    path("<int:product_id>/", scan_product, name="scan-product"),
    path("nearby_products/", nearby_products, name="nearby-products"),
    path("scan_all_my_products/", scan_all_my_products, name="scan_all_my_products"),
]

# Full URL will be:  GET /products/scan/<product_id>/?radius=25&min_score=20