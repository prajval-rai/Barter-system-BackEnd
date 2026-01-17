from django.urls import path
from .views import (
    category_list_create, category_detail,
    product_list_create, product_detail,
    product_image_delete,
    product_list_create,
    product_update,
    product_list_paginated,
    product_list_by_category,
    product_list_by_user,
    add_replace_options,
    upload_product_images,
    products_grouped_by_category
)

urlpatterns = [
    # Categories
    path('categories/', category_list_create, name='category-list-create'),
    path('categories/<int:pk>/', category_detail, name='category-detail'),

    # Products
    path('', product_list_create, name='product-list-create'),
    path('<int:pk>/', product_detail, name='product-detail'),
    path('<int:product_id>/replace-options/', add_replace_options, name='replace-options'),
    path('grouped/', products_grouped_by_category, name='replace-options'),

    # Optional: individual image delete
    path('images_delete/<int:pk>/', product_image_delete, name='product-image-delete'),
    path('images/<int:pk>/', upload_product_images, name='upload_product_images'),


    path('updated/<int:pk>/', product_update, name='product-update'),  # PUT only
    path('paginated/', product_list_paginated, name='product-list-paginated'),
    path('category/<int:category_id>/', product_list_by_category, name='product-list-by-category'),
    path('user/', product_list_by_user, name='product-list-by-user'),
]
