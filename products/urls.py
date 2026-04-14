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
    upload_product_images,
    products_grouped_by_category,
    delete_product,
    add_replace_options_bulk,
    create_product,
    products_by_status,
    get_product_images,
    admin_products_by_status,
    change_product_status,
    marketplace,
    my_product
)

urlpatterns = [
    # Categories
    path('categories/', category_list_create, name='category-list-create'),
    path('categories/<int:pk>/', category_detail, name='category-detail'),

    # Products
    

    path('create_product/', create_product, name='create_product'),
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
    path("my_product/",my_product,name="my_product")


]
