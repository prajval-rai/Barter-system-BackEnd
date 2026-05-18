from django.urls import path
from .views import *

urlpatterns = [
    # Categories
    path('categories/', category_list_create, name='category-list-create'),
    path('categories/<int:pk>/', category_detail, name='category-detail'),

    # Products
    

    path('create_product/', create_product, name='create_product'),
    path('add_replace_options/<int:product_id>/', add_replace_options, name='add_replace_options'),
    path('product_dropdown/', product_dropdown, name='product_dropdown'),
    path('', product_list_create, name='product-list-create'),
    path('<int:pk>/', product_detail, name='product-detail'),
    path('<int:product_id>/replace-options/bulk/', add_replace_options_bulk, name='replace-options'),
    path('grouped/', products_grouped_by_category, name='replace-options'),
    path('delete/<int:pk>/', delete_product, name='delete-product'),


    # Optional: individual image delete
    path('images_delete/<int:pk>/', product_image_delete, name='product-image-delete'),
    path('images/<int:pk>/', upload_product_images, name='upload_product_images'),
    path('get_product_images/<int:product_id>/', get_product_images, name='upload_product_images'),


    path('updated/<int:pk>/', product_update, name='product-update'),  # PUT only
    path('paginated/', product_list_paginated, name='product-list-paginated'),
    path('category/<int:category_id>/', product_list_by_category, name='product-list-by-category'),
    path('user/', product_list_by_user, name='product-list-by-user'),
    path('products_by_status/', products_by_status, name='products_by_status'),
    path('admin_products_by_status/', admin_products_by_status, name='products_by_status'),
    path('change_product_status/',change_product_status),
    path("marketplace/", marketplace, name="marketplace"),
    path("my_product/",my_product,name="my_product"),
    path('bookmark/<int:product_id>/',add_bookmark, name='add-bookmark'),
    path('bookmarks/',get_bookmarks, name='get-bookmarks'),
    path('bookmark/<int:product_id>/remove/',remove_bookmark,   name='remove-bookmark'),


]
