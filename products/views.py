from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .models import Product, ProductImage, Category
from .serializers import ProductSerializer, CategorySerializer,ProductImageSerializer,ReplaceOptionSerializer,ProductListSerializer,GetProductSerializer,MarketplaceProductSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from google.cloud import storage
from django.conf import settings
from barter.models import ReplaceOption
from django.db import transaction
import json
from django.db.models import Q
from accounts.models import UserProfile
from barter.serializers import ProductBasicSerializer
from utils.twilio_service import send_whatsapp_message
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





@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
@transaction.atomic
def create_product(request):
    try:
        # -------------------------
        # 1️⃣ CREATE PRODUCT
        # -------------------------

        product_serializer = ProductSerializer(
            data=request.data, 
            context={'request': request}  # ✅ Pass request to fix KeyError
        )
        product_serializer.is_valid(raise_exception=True)
        product = product_serializer.save(owner=request.user)

        # -------------------------
        # 2️⃣ ADD REPLACE OPTIONS
        # -------------------------

        replace_options_raw = request.data.get("replace_options")
        if replace_options_raw:
            try:
                replace_options = json.loads(replace_options_raw)
            except json.JSONDecodeError:
                return Response(
                    {"error": "Invalid replace_options JSON"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not isinstance(replace_options, list):
                return Response(
                    {"error": "replace_options must be a list"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            objects_to_create = []
            for item in replace_options:
                serializer = ReplaceOptionSerializer(
                    data=item,
                    context={'request': request}  # ✅ Pass request context here too
                )
                serializer.is_valid(raise_exception=True)
                v = serializer.validated_data

                objects_to_create.append(
                    ReplaceOption(
                        product=product,
                        replace_type=v.get("replace_type"),
                        title=v.get("title", ""),
                        description=v.get("description", ""),
                        category=v.get("category"),
                        point_value=v.get("point_value"),
                        meta=v.get("meta", {})
                    )
                )

            ReplaceOption.objects.bulk_create(objects_to_create)

        # -------------------------
        # 3️⃣ ADD THUMBNAIL
        # -------------------------

        
        product.save()

        # -------------------------
        # 4️⃣ ADD IMAGES
        # -------------------------

        images = request.FILES.getlist('images')
        for f in images:
            ProductImage.objects.create(product=product, image=f)

        phone = request.user.userprofile.contact_number
        if phone:
            phone = f"+91{phone}"  # important for Twilio

            message = (
    f"🎉 *Product Listed Successfully!*\n\n"
    f"Hey *{request.user.username}* 👋\n\n"
    f"Your product is now *live* and under review by our team.\n\n"
    f"━━━━━━━━━━━━━━━━\n"
    f"📦 *Product:* {product.title}\n"
    f"📌 *Status:* Under Review 🔍\n"
    f"━━━━━━━━━━━━━━━━\n\n"
    f"⏳ *What happens next?*\n"
    f"  • Our team will review your listing\n"
    f"  • Once approved, it becomes visible to all users\n"
    f"  • You'll get notified the moment someone matches your exchange!\n\n"
    f"💡 *Pro Tip:* Make sure your product images are clear and "
    f"your exchange options are accurate for faster approval.\n\n"
    f"🤝 Happy Trading & Best of Luck!\n\n"
    f"_– BarterApp Team_ 🛍️"
)

            send_whatsapp_message(phone, message)


        return Response(
            {
                "success": True,
                "product_id": product.id,
                "message": "Product created successfully"
            },
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )





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
def add_replace_options_bulk(request, product_id):
    try:
        product = Product.objects.get(id=product_id, owner=request.user)
    except Product.DoesNotExist:
        return Response(
            {"error": "Product not found or not yours"},
            status=status.HTTP_404_NOT_FOUND
        )

    data = request.data
    if not isinstance(data, list):
        return Response(
            {"error": "Expected a list of replace options"},
            status=status.HTTP_400_BAD_REQUEST
        )

    objects_to_create = []

    for item in data:
        serializer = ReplaceOptionSerializer(data=item)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data

        objects_to_create.append(
            ReplaceOption(
                product=product,
                replace_type=v.get("replace_type"),
                title=v.get("title", ""),
                description=v.get("description", ""),
                category=v.get("category"),
                point_value=v.get("point_value"),
                meta=v.get("meta", {})
            )
        )

    # 🔥 KEY LINE: reset replace options
    product.replace_options.all().delete()

    # 🔥 single DB hit
    ReplaceOption.objects.bulk_create(objects_to_create)

    return Response({"success": True}, status=status.HTTP_200_OK)

# --------------------
# PRODUCT IMAGES
# --------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_product_images(request, pk):
    try:
        product = Product.objects.get(id=pk, owner=request.user)
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


@api_view(['GET'])
def get_product_images(request, product_id):
    images = ProductImage.objects.filter(product_id=product_id)

    if not images.exists():
        return Response(
            {"message": "No images found for this product"},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = ProductImageSerializer(
        images,
        many=True,
        context={"request": request}
    )
    return Response(serializer.data, status=status.HTTP_200_OK)




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
    serializer = GetProductSerializer(products, many=True)
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
            queryset=Product.objects.filter(status="Submitted")
            .prefetch_related('images', 'replace_options')
        )
    )

    print("---------------------",categories)

    data = []
    for category in categories:
        products = category.product_set.all()
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        data.append({
            "category": category.name,
            "products": serializer.data
        })

    return Response(data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product(request, pk):
    """
    Delete a product, its images, thumbnail, and replace options from DB and GCS
    """
    product = get_object_or_404(Product, pk=pk)

    try:
        # ---------------- Delete replace options ----------------
        product.replace_options.all().delete()

        # ---------------- Setup GCS client ----------------
        if not settings.GS_CREDENTIALS:
            return Response(
                {"detail": "GCS credentials not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        client = storage.Client(
            credentials=settings.GS_CREDENTIALS,
            project=settings.GS_PROJECT_ID
        )
        bucket = client.bucket(settings.GS_BUCKET_NAME)
        location = "uploads"  # matches your settings.STORAGES default location

        # ---------------- Delete product images ----------------
        for img in product.images.all():
            if img.image:
                blob_name = f"{location}/{img.image.name}"  # e.g. uploads/products/image.jpg
                try:
                    blob = bucket.blob(blob_name)
                    blob.delete()
                    print(f"Deleted image from GCS: {blob_name}")
                except Exception as e:
                    print(f"Failed to delete image {blob_name}: {e}")
            img.delete()  # delete from DB

        # ---------------- Delete thumbnail ----------------
        if product.thumbnail:
            blob_name = f"{location}/{product.thumbnail.name}"  # e.g. uploads/thumbnails/image.jpg
            try:
                blob = bucket.blob(blob_name)
                blob.delete()
                print(f"Deleted thumbnail from GCS: {blob_name}")
            except Exception as e:
                print(f"Failed to delete thumbnail {blob_name}: {e}")

        # ---------------- Delete the product ----------------
        product.delete()

        return Response(
            {"detail": "Product and related data deleted successfully."},
            status=200
        )

    except Exception as e:
        return Response(
            {"detail": f"Failed to delete product: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def products_by_status(request):
    """
    List products filtered by status (recent first)
    ?status=submitted | approved | closed
    """

    status_param = request.GET.get("status", "approved")

    valid_status = ["submitted", "approved", "closed","banned","rejected"]

    if status_param not in valid_status:
        return Response(
            {"error": f"Invalid status. Choose from {valid_status}"},
            status=400
        )

    products = Product.objects.filter(owner=request.user,status=status_param).order_by('-created_at')
    serializer = GetProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_products_by_status(request):
    """
    List products filtered by status (recent first)
    ?status=submitted | approved | closed
    """

    status_param = request.GET.get("status", "approved")

    valid_status = ["submitted", "approved", "closed","banned","rejected"]

    if status_param not in valid_status:
        return Response(
            {"error": f"Invalid status. Choose from {valid_status}"},
            status=400
        )

    products = Product.objects.filter(status=status_param).order_by('-created_at')
    serializer = GetProductSerializer(products, many=True)
    return Response(serializer.data)

    



@permission_classes([IsAuthenticated])
@api_view(["POST"])
def change_product_status(request):
    try:
        status_value = request.GET.get('status')
        status_choice = ["submitted","approved","closed","rejected","banned"]

        if status_value not in status_choice:
            return Response({"message":"Select Proper Status"}, status=status.HTTP_400_BAD_REQUEST)

        product_id = request.GET.get('product_id')

        user_profile = UserProfile.objects.get(user=request.user.id)

        if user_profile.role == "Admin":

            product_obj = Product.objects.get(id=product_id)
            product_obj.status = status_value
            product_obj.save()

            # -------------------------
            # 🔔 WhatsApp Notification
            # -------------------------
            owner_profile = UserProfile.objects.get(user=product_obj.owner)

            phone = owner_profile.contact_number

            if phone:
                phone = f"+91{phone}"

                # Friendly message based on status
                if status_value == "approved":
                    msg = (
                        f"✅ *Product Approved!*\n\n"
                        f"Hey *{product_obj.owner.username}* 👋\n\n"
                        f"🎉 Great news! Your product has been *approved* and is now *live* on the platform!\n\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📦 *Product:* {product_obj.title}\n"
                        f"📌 *Status:* Approved ✅\n"
                        f"━━━━━━━━━━━━━━━━\n\n"
                        f"🤝 Other users can now discover and barter with your product.\n\n"
                        f"💡 *Tip:* Keep your product details updated to attract more offers!\n\n"
                        f"_– BarterApp Team_ 🛍️"
                    )

                elif status_value == "rejected":
                    msg = (
                        f"❌ *Product Rejected*\n\n"
                        f"Hi *{product_obj.owner.username}* 👋\n\n"
                        f"Unfortunately, your product has been *rejected* after review.\n\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📦 *Product:* {product_obj.title}\n"
                        f"📌 *Status:* Rejected ❌\n"
                        f"━━━━━━━━━━━━━━━━\n\n"
                        f"🔍 *What to do next?*\n"
                        f"  • Review your product title & description\n"
                        f"  • Ensure images are clear & relevant\n"
                        f"  • Re-submit after making improvements\n\n"
                        f"📩 Need help? contact our support team.\n\n"
                        f"_– BarterApp Team_ 🛍️"
                    )

                elif status_value == "closed":
                    msg = (
                        f"🔒 *Product Closed*\n\n"
                        f"Hi *{product_obj.owner.username}* 👋\n\n"
                        f"Your product has been *closed* and is no longer available for barter.\n\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📦 *Product:* {product_obj.title}\n"
                        f"📌 *Status:* Closed 🔒\n"
                        f"━━━━━━━━━━━━━━━━\n\n"
                        f"📌 *Why might this happen?*\n"
                        f"  • The barter was successfully completed\n"
                        f"  • The listing was manually closed by admin\n\n"
                        f"➕ Want to list something new? Head over to the app!\n\n"
                        f"_– BarterApp Team_ 🛍️"
                    )

                elif status_value == "banned":
                    msg = (
                        f"🚫 *Product Banned*\n\n"
                        f"Hi *{product_obj.owner.username}* 👋\n\n"
                        f"Your product has been *banned* due to a policy violation.\n\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📦 *Product:* {product_obj.title}\n"
                        f"📌 *Status:* Banned 🚫\n"
                        f"━━━━━━━━━━━━━━━━\n\n"
                        f"⚠️ *This may have happened because:*\n"
                        f"  • The product violates our community guidelines\n"
                        f"  • Inappropriate content was detected\n"
                        f"  • Repeated policy breaches\n\n"
                        f"📩 *Think this is a mistake?*\n"
                        f"Contact our support team and we'll look into it.\n\n"
                        f"_– BarterApp Team_ 🛍️"
                    )

                else:
                    msg = (
                        f"🔔 *Product Status Updated*\n\n"
                        f"Hi *{product_obj.owner.username}* 👋\n\n"
                        f"There's an update on one of your listed products.\n\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📦 *Product:* {product_obj.title}\n"
                        f"📌 *New Status:* {status_value.capitalize()}\n"
                        f"━━━━━━━━━━━━━━━━\n\n"
                        f"Open the app for more details.\n\n"
                        f"_– BarterApp Team_ 🛍️"
                    )
                try:
                    send_whatsapp_message(phone, msg)
                except Exception as e:
                    print("WhatsApp Error:", str(e))

            return Response({
                "message": "Status Changed"
            })

        else:
            return Response({
                "message": "You are not allowed to change status!"
            })

    except Exception as e:
        return Response(
            {"detail": f"Failed to update status: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST
        )


# GET /products/marketplace/
#
# Public endpoint — any authenticated user can browse.
#
# Query params:
#   page        (int, default 1)
#   page_size   (int, default 12, max 40)
#   search      (str) — searches title + description
#   category    (int) — category id
#   sort        (str) — "newest" | "oldest"  (default newest)
#
# Response:
#   {
#     "results":   [...],
#     "page":      1,
#     "page_size": 12,
#     "total":     84,
#     "has_next":  true
#   }
# ════════════════════════════════════════════════════════════════════════════
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def marketplace(request):
    # ── 1. Parse params ──────────────────────────────────────────────────────
    try:
        page      = max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    try:
        page_size = min(int(request.query_params.get("page_size", 12)), 40)
    except (TypeError, ValueError):
        page_size = 12

    search   = request.query_params.get("search", "").strip()
    category = request.query_params.get("category", "").strip()
    sort     = request.query_params.get("sort", "newest")

    # ── 2. Base queryset — approved only, exclude own products ───────────────
    qs = (
        Product.objects
        .filter(status="approved")
        .exclude(owner=request.user)
        .select_related("owner", "category")
        .prefetch_related("replace_options", "images")
    )

    # ── 3. Search ─────────────────────────────────────────────────────────────
    if search:
        qs = qs.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )

    # ── 4. Category filter ────────────────────────────────────────────────────
    if category:
        qs = qs.filter(category_id=category)

    # ── 5. Sort ───────────────────────────────────────────────────────────────
    qs = qs.order_by("created_at" if sort == "oldest" else "-created_at")

    # ── 6. Paginate ───────────────────────────────────────────────────────────
    total    = qs.count()
    offset   = (page - 1) * page_size
    products = qs[offset : offset + page_size]
    has_next = (offset + page_size) < total

    # ── 7. Serialize & return ─────────────────────────────────────────────────
    serializer = MarketplaceProductSerializer(
        products, many=True, context={"request": request}
    )

    return Response({
        "results":   serializer.data,
        "page":      page,
        "page_size": page_size,
        "total":     total,
        "has_next":  has_next,
    }, status=status.HTTP_200_OK)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_product(request):
    try:
        product_obj = Product.objects.filter(owner=request.user.id,status="approved")
        product_basic = ProductBasicSerializer(product_obj,many=True,context={"request": request}).data
        return Response(product_basic)

    except Exception as e:
        return Response({'message':str(e)})