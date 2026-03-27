# Add this to your products/urls.py

from django.urls import path
from .views import *   # or wherever you put the view

urlpatterns = [
    # ... your existing urls ...
    path("<int:product_id>/", scan_product, name="scan-product"),
]

# Full URL will be:  GET /products/scan/<product_id>/?radius=25&min_score=20