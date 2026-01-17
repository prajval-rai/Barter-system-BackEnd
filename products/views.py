from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .models import Product, ProductImage, Category
from .serializers import ProductSerializer, CategorySerializer,ProductImageSerializer,ReplaceOptionSerializer,ProductListSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django.db.models import Prefetch

# --------------------
# CATEGORY CRUD
# --------------------
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def category_list_create(request):
    if request.method == 'GET':
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def category_detail(request, pk):
    try:
        category = Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = CategorySerializer(category)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = CategorySerializer(category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------
# PRODUCT
# --------------------
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def product_list_create(request):
    if request.method == 'GET':
        products = Product.objects.all()
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        print("000000000000000000000000000",request.data)
        serializer = ProductSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            product = serializer.save()
            return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




# --------------------
# REPLACE OPTIONS
# --------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_replace_options(request, product_id):
    try:
        product = Product.objects.get(id=product_id, owner=request.user)
    except Product.DoesNotExist:
        return Response({"error": "Product not found or not yours"}, status=status.HTTP_404_NOT_FOUND)

    data = request.data
    if not isinstance(data, list):
        return Response({"error": "Expected a list of replace options"}, status=status.HTTP_400_BAD_REQUEST)

    created_options = []
    for item in data:
        serializer = ReplaceOptionSerializer(data=item)
        if serializer.is_valid():
            serializer.save(product=product)
            created_options.append(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return Response(created_options, status=status.HTTP_201_CREATED)



# --------------------
# PRODUCT IMAGES
# --------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_product_images(request, pk):
    try:
        product = Product.objects.get(id=pk, owner=request.user)
        print("1111111111111111111111111111111111",product)
    except Product.DoesNotExist:
        return Response({"error": "Product not found or not yours"}, status=status.HTTP_404_NOT_FOUND)

    files = request.FILES.getlist('images')
    if not files:
        return Response({"error": "No images uploaded"}, status=status.HTTP_400_BAD_REQUEST)

    created_images = []
    for f in files:
        img = ProductImage.objects.create(product=product, image=f)
        created_images.append(ProductImageSerializer(img).data)

    return Response(created_images, status=status.HTTP_201_CREATED)




@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def product_update(request, pk):
    """
    Update a product and optionally add new images
    """
    try:
        product = Product.objects.get(pk=pk, owner=request.user)
    except Product.DoesNotExist:
        return Response({"error": "Product not found or not owned by you"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProductSerializer(product, data=request.data, partial=True, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --------------------
# List Products with Pagination
# --------------------
@api_view(['GET'])
@permission_classes([AllowAny])
def product_list_paginated(request):
    """
    List all open products with pagination
    """
    products = Product.objects.filter(status="open").order_by('-created_at')
    paginator = PageNumberPagination()
    paginator.page_size = 10  # default 10 per page
    result_page = paginator.paginate_queryset(products, request)
    serializer = ProductSerializer(result_page, many=True)
    return paginator.get_paginated_response(serializer.data)


# --------------------
# List Products by Category
# --------------------
@api_view(['GET'])
@permission_classes([AllowAny])
def product_list_by_category(request, category_id):
    """
    List all products in a given category
    """
    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)

    products = Product.objects.filter(category=category, status="open").order_by('-created_at')
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

# --------------------
# List Products created by logged-in user
# --------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_list_by_user(request):
    """
    List all products created by the logged-in user
    """
    products = Product.objects.filter(owner=request.user).order_by('-created_at')
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)




@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def product_detail(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ProductSerializer(product)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = ProductSerializer(product, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------
# PRODUCT IMAGE CRUD (Optional: individual image delete)
# --------------------
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def product_image_delete(request, pk):
    try:
        print("---------------------",pk)
        image = ProductImage.objects.get(pk=pk)
    except ProductImage.DoesNotExist:
        return Response({"error": "Image not found"}, status=status.HTTP_404_NOT_FOUND)
    image.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def products_grouped_by_category(request):
    """
    List all products grouped by category (optimized)
    """
    # Prefetch images and replace options in a single query
    categories = Category.objects.all().prefetch_related(
        Prefetch(
            'product_set',
            queryset=Product.objects.filter(status="open")
            .prefetch_related('images', 'replace_options')
        )
    )

    data = []
    for category in categories:
        products = category.product_set.all()
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        data.append({
            "category": category.name,
            "products": serializer.data
        })

    return Response(data)
