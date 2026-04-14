# views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Product, BarterRequest
from .serializers import *
from django.db.models import Q


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_barter_request(request):

    serializer = BarterRequestCreateSerializer(data=request.data)

    if serializer.is_valid():

        request_product = serializer.validated_data["request_product"]
        request_for_product = serializer.validated_data["request_for_product"]

        # user must own the offered product
        if request_product.owner != request.user:
            return Response(
                {"error": "You can only offer your own product"},
                status=400
            )

        to_user = request_for_product.owner

        if to_user == request.user:
            return Response(
                {"error": "You cannot barter with yourself"},
                status=400
            )

        barter_request = BarterRequest.objects.create(
            from_user=request.user,
            to_user=to_user,
            request_product=request_product,
            request_for_product=request_for_product
        )

        return Response(
            {"message": "Barter request sent", "id": barter_request.id},
            status=201
        )

    return Response(serializer.errors, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_barter_requests(request):

    requests = BarterRequest.objects.filter(
        Q(from_user=request.user) | Q(to_user=request.user)
    ).select_related(
        "request_product",
        "request_for_product",
        "from_user",
        "to_user"
    ).order_by("-created_at")

    serializer = BarterRequestSerializer(requests, many=True,context={"request": request})

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_accepted_request(request):
    """
    ✅ FIX: Both the requester (from_user) AND the acceptor (to_user)
    should see the chat. The original code only returned chats where
    the current user was to_user, so the sender never saw their chat.
    """
    requests = BarterRequest.objects.filter(
        # ✅ Either side of the trade, as long as it's accepted
        Q(from_user=request.user) | Q(to_user=request.user),
        Q(status="accepted") | Q(status="completed"),
    ).select_related(
        "request_product",
        "request_for_product",
        "from_user",
        "to_user",
    ).order_by("-created_at")
 
    serializer = BarterRequestSerializer(requests, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def received_barter_requests(request):

    requests = BarterRequest.objects.filter(
        to_user=request.user
    ).select_related(
        "request_product",
        "request_for_product",
        "from_user"
    ).prefetch_related(
        "request_product__images",
        "request_for_product__images"
    ).order_by("-created_at")

    serializer = BarterRequestSerializer(
        requests,
        many=True,
        context={"request": request}
    )

    return Response(serializer.data)



@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_barter_status(request, request_id):

    status_value = request.data.get("status")

    if status_value not in ["accepted", "rejected", "completed"]:
        return Response({"error": "Invalid status"}, status=400)

    try:
        barter_request = BarterRequest.objects.select_related(
            "request_product",
            "request_for_product"
        ).get(id=request_id)

    except BarterRequest.DoesNotExist:
        return Response({"error": "Request not found"}, status=404)

    if barter_request.to_user != request.user:
        return Response({"error": "Permission denied"}, status=403)

    barter_request.status = status_value
    barter_request.save()

    serializer = BarterRequestSerializer(barter_request)

    return Response(serializer.data)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def saved_products(request):
    data = SaveProducts.objects.filter(user=request.user)
    serializer = SaveProductsSerializer(data, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_product(request):
    serializer = SaveProductsSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_saved_product(request, pk):
    try:
        obj = SaveProducts.objects.get(pk=pk, user=request.user)
    except SaveProducts.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    obj.delete()
    return Response({"message": "Removed"}, status=204)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_save_product(request):
    product_id = request.data.get('product')

    obj, created = SaveProducts.objects.get_or_create(
        user=request.user,
        product_id=product_id
    )

    if not created:
        obj.delete()
        return Response({"message": "Product unsaved"})

    return Response({"message": "Product saved"})





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def is_saved(request):
    product_id = request.query_params.get('product')

    exists = SaveProducts.objects.filter(
        user=request.user,
        product_id=product_id
    ).exists()

    return Response({"is_saved": exists})