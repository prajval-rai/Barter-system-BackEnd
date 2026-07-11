from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from helper_function.config import Config
from django.utils import timezone
from .models import CustomUser, UserNotification, FCMToken
from .serializer import ProfileSerializer, UserNotificationSerializer
from utils.twilio_service import send_whatsapp_message
from helper_function.utils import send_notification_to_token


GOOGLE_CLIENT_ID = Config.google_key

User = get_user_model()  # resolves to CustomUser — use this everywhere instead of importing User directly


# ✅ Generate JWT tokens
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


# ======================================================
# 🔥 GOOGLE LOGIN
# ======================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def google_login(request):
    """
    Frontend sends:
    {
        "token": "google-id-token"
    }
    """

    token = request.data.get("token")

    if not token:
        return Response(
            {"error": "Token is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # ✅ Verify Google token
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )

        email = idinfo.get("email")
        first_name = idinfo.get("given_name", "")
        last_name = idinfo.get("family_name", "")

        if not email:
            return Response(
                {"error": "Email not provided by Google"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Get or create user (CustomUser IS the user model — no separate profile object)
        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            }
        )

        # ✅ Update last login
        user.last_login = timezone.now()
        user.save()

        # ✅ Generate JWT
        tokens = get_tokens_for_user(user)

        response = Response({
            "message": "Login successful",
            "user": {
                "id": user.id,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "email": user.email,
                "role": getattr(user, "role", None),
                "address": getattr(user, "address", None),
                "lat": getattr(user, "latitude", None),
                "long": getattr(user, "longitude", None),
            }
        })

        # ✅ Set Cookies
        response.set_cookie(
            key="access",
            value=tokens["access"],
            httponly=True,
            secure=True,  # change to True in production
            samesite="None",
            max_age=86400,
        )

        # ✅ Send WhatsApp welcome message only if contact number exists
        phone = user.contact_number

        if phone:
            try:
                send_whatsapp_message(phone, f"Welcome {user.first_name}")
            except Exception:
                pass  # don't let a WhatsApp/Twilio failure break login

        response.set_cookie(
            key="refresh",
            value=tokens["refresh"],
            httponly=True,
            secure=True,  # change to True in production
            samesite="None",
            max_age=604800,
        )

        return response

    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
# ======================================================
# 🔥 GET CURRENT USER
# ======================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user

    return Response({
        "id": user.id,
        "name": f"{user.first_name} {user.last_name}",
        "email": user.email,
    })


# ======================================================
# 🔥 LOGOUT
# ======================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    response = Response({"message": "Logged out successfully"})
    response.delete_cookie("access")
    response.delete_cookie("refresh")
    return response


# ======================================================
# 🔥 PROFILE (GET) — CustomUser IS request.user, no separate lookup needed
# ======================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request):
    try:
        profile_serialize = ProfileSerializer(request.user).data
        return Response({"data": profile_serialize})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ======================================================
# 🔥 UPDATE PROFILE
# ======================================================

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    try:
        serializer = ProfileSerializer(
            request.user,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Profile updated successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "message": "Validation failed",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


# ======================================================
# 🔥 NOTIFICATIONS
# ======================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def notifications(request):
    if request.method == 'GET':
        data = UserNotification.objects.filter(user=request.user).order_by('-id')
        serializer = UserNotificationSerializer(data, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = UserNotificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def notification_detail(request, pk):
    try:
        obj = UserNotification.objects.get(pk=pk, user=request.user)
    except UserNotification.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    if request.method == 'GET':
        return Response(UserNotificationSerializer(obj).data)

    elif request.method in ['PUT', 'PATCH']:
        serializer = UserNotificationSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    elif request.method == 'DELETE':
        obj.delete()
        return Response({"message": "Deleted"}, status=204)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    try:
        obj = UserNotification.objects.get(pk=pk, user=request.user)
    except UserNotification.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    obj.staus = True
    obj.save()
    return Response({"message": "Marked as read"})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    UserNotification.objects.filter(user=request.user, staus=False).update(staus=True)
    return Response({"message": "All notifications marked as read"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_count(request):
    count = UserNotification.objects.filter(user=request.user, staus=False).count()
    return Response({"unread_count": count})


# ======================================================
# 🔥 FCM TOKEN
# ======================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_fcm_token(request):
    token = request.data.get("token")
    device_type = request.data.get("device_type", "web")

    if not token:
        return Response({"error": "Token is required"}, status=400)

    FCMToken.objects.get_or_create(
        user=request.user,
        token=token,
        defaults={"device_type": device_type}
    )
    return Response({"message": "Token registered successfully"})


@api_view(["POST"])
@permission_classes([AllowAny])
def send_test_notification(request):
    token = request.data.get("token")
    username = request.data.get("username", "Legend")

    if not token:
        return Response({"error": "Token is required"}, status=400)

    try:
        send_notification_to_token(
            token=token,
            title="🎉 The legend has arrived!",
            body=f"Welcome back, {username}! The app was getting lonely without you. 👀",
            data={"type": "login_alert"}
        )
        return Response({"success": True})

    except Exception as e:
        return Response({"error": str(e)}, status=500)


# ======================================================
# 🔥 PROFILE COMPLETION — CustomUser IS request.user, no reverse lookup needed
# ======================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_completion(request):
    all_field_keys = ["latitude", "longitude", "address", "contact_number", "description", "city", "pincode"]

    user = request.user

    fields = {
        "latitude":       getattr(user, "latitude", None),
        "longitude":      getattr(user, "longitude", None),
        "address":        getattr(user, "address", None),
        "contact_number": getattr(user, "contact_number", None),
        "description":    getattr(user, "description", None),
        "city":           getattr(user, "city", None),
        "pincode":        getattr(user, "pincode", None),
    }

    completed = {k: v for k, v in fields.items() if v not in [None, ""]}
    incomplete = {k: v for k, v in fields.items() if v in [None, ""]}
    percentage = (len(completed) / len(fields)) * 100

    return Response({
        "completion_percentage": round(percentage, 2),
        "completed_fields":      list(completed.keys()),
        "incomplete_fields":     list(incomplete.keys()),
        "total_fields":          len(fields),
        "filled_fields":         len(completed),
    })