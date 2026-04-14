# views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Product, BarterRequest
from .serializers import *
from django.db.models import Q,Subquery, OuterRef, IntegerField,Count
from django.db.models.functions import Coalesce
from utils.twilio_service import send_whatsapp_message
from chat.models import ChatMessage


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

        receiver_phone = to_user.userprofile.contact_number
        if receiver_phone:
            receiver_phone = f"+91{receiver_phone}"
            receiver_msg = (
                f"🔔 *New Barter Request Received!*\n\n"
                f"Hey *{to_user.username}* 👋\n\n"
                f"Someone is interested in bartering with you!\n\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"👤 *Request From:* {request.user.username}\n"
                f"📦 *They're Offering:* {request_product.title}\n"
                f"🎯 *They Want:* {request_for_product.title}\n"
                f"━━━━━━━━━━━━━━━━\n\n"
                f"⚡ *Action Required!*\n"
                f"  • Open the app to review the offer\n"
                f"  • Accept if you're interested in the trade\n"
                f"  • Decline if it's not a good fit for you\n\n"
                f"⏰ *Don't keep them waiting —* "
                f"respond to the request at your earliest!\n\n"
                f"🤝 Happy Trading!\n\n"
                f"_– BarterApp Team_ 🛍️"
            )
            try:
                send_whatsapp_message(receiver_phone, receiver_msg)
            except Exception as e:
                print("WhatsApp Error (receiver):", str(e))

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
    user = request.user

    # Subquery: unread count for this user in each chat
    unread_subquery = ChatMessage.objects.filter(
        barter_request_id=OuterRef('pk'),
        seen=False,
    ).exclude(
        sender=user
    ).values('barter_request_id').annotate(
        c=Count('id')
    ).values('c')

    # Subquery: last message text
    last_msg_subquery = ChatMessage.objects.filter(
        barter_request_id=OuterRef('pk')
    ).order_by('-created_at').values('text')[:1]

    # Subquery: last message timestamp
    last_time_subquery = ChatMessage.objects.filter(
        barter_request_id=OuterRef('pk')
    ).order_by('-created_at').values('created_at')[:1]

    # Subquery: last message sender email
    last_sender_subquery = ChatMessage.objects.filter(
        barter_request_id=OuterRef('pk')
    ).order_by('-created_at').values('sender__email')[:1]

    requests = BarterRequest.objects.filter(
        Q(from_user=user) | Q(to_user=user),
        Q(status="accepted") | Q(status="completed"),
    ).select_related(
        "request_product",
        "request_for_product",
        "from_user",
        "to_user",
    ).annotate(
        unread_count=Coalesce(
            Subquery(unread_subquery, output_field=IntegerField()),
            0
        ),
        last_message=Subquery(last_msg_subquery),
        last_message_time=Subquery(last_time_subquery),
        last_message_sender=Subquery(last_sender_subquery),
    ).order_by('-created_at')

    serializer = BarterRequestSerializer(
        requests, many=True, context={"request": request}
    )
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