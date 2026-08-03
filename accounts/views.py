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

import os



from .utils import send_email

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "").rstrip("/")


def build_welcome_email_html(first_name: str) -> str:
    marketplace_url = f"{FRONTEND_BASE_URL}/marketplace"

    return f"""
    <!DOCTYPE html>
    <html>
      <body style="margin:0; padding:0; background-color:#eaf1ff; font-family: 'Helvetica Neue', Arial, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(180deg,#dce9ff 0%,#eaf1ff 40%,#ffffff 100%); padding:48px 0;">
          <tr>
            <td align="center">
              <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:24px; overflow:hidden; box-shadow:0 20px 50px rgba(23,43,99,0.12);">

                <!-- Header / brand -->
                <tr>
                  <td align="center" style="padding:36px 32px 20px;">
                    <table cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="padding-right:8px; vertical-align:middle;">
                          <div style="width:36px; height:36px; border-radius:10px; background:#2563eb; display:inline-block; line-height:36px; text-align:center;">
                            <span style="color:#ffffff; font-size:18px; font-weight:bold;">⇄</span>
                          </div>
                        </td>
                        <td style="vertical-align:middle;">
                          <span style="font-size:22px; font-weight:800; color:#0f172a;">Len<span style="color:#2563eb;">Den</span></span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <!-- Headline -->
                <tr>
                  <td align="center" style="padding:0 40px 8px;">
                    <p style="margin:0; font-size:12px; letter-spacing:1.5px; font-weight:700; color:#2563eb; text-transform:uppercase;">
                      Welcome to LenDen
                    </p>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding:0 40px 16px;">
                    <h1 style="margin:0; font-size:24px; line-height:1.3; color:#0f172a; font-weight:800;">
                      Hey {first_name or "there"}, your<br/>account is ready 🎉
                    </h1>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding:0 40px 28px;">
                    <p style="margin:0; font-size:14.5px; color:#64748b; line-height:1.7;">
                      You're signed in with Google — no password needed.
                      Start browsing what people are exchanging near you,
                      and give your unused items a second life.
                    </p>
                  </td>
                </tr>

                <!-- CTA button -->
                <tr>
                  <td align="center" style="padding:0 40px 32px;">
                    <a href="{marketplace_url}"
                       style="display:inline-block; padding:14px 32px; background:#2563eb; color:#ffffff; text-decoration:none; font-size:14.5px; font-weight:700; border-radius:999px; box-shadow:0 8px 20px rgba(37,99,235,0.35);">
                      Find what you need →
                    </a>
                  </td>
                </tr>

                <!-- Divider -->
                <tr>
                  <td style="padding:0 40px;">
                    <div style="height:1px; background:#e5e9f2;"></div>
                  </td>
                </tr>

                <!-- Tagline -->
                <tr>
                  <td align="center" style="padding:24px 40px 8px;">
                    <p style="margin:0; font-size:13px; color:#94a3b8; font-style:italic;">
                      "Jo aapke liye useless hai, kisi aur ke liye valuable ho sakta hai."
                    </p>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding:0 40px 28px;">
                    <p style="margin:0; font-size:12.5px; font-weight:700; color:#2563eb;">
                      #ExchangeForBetter
                    </p>
                  </td>
                </tr>

                <!-- Footer -->
                <tr>
                  <td align="center" style="background:#f8fafc; padding:20px 32px;">
                    <p style="margin:0; font-size:11.5px; color:#9ca3af;">
                      © {timezone.now().year} LenDen. All rights reserved.
                    </p>
                  </td>
                </tr>

              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """



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

        # 🔧 FIX: refresh from DB so encrypted fields are re-loaded through the
        # normal decrypt-on-read path instead of staying as ciphertext left
        # behind by the encrypted field's pre_save() mutation on this instance.
        user.refresh_from_db()

        # ✅ Send welcome email only for newly created users
        if created:
            try:
                send_email(
                    to=user.email,
                    subject="Welcome! Your account is ready 🎉",
                    html=build_welcome_email_html(user.first_name),
                )
            except Exception:
                pass  # don't let an email failure break login

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
            secure=True,
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
            secure=True,
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Frontend just calls this with credentials included (cookies sent
    automatically) — no body required.
    """
    try:
        refresh_token = request.COOKIES.get("refresh")

        # ✅ Blacklist the refresh token so it can't be reused
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass  # already invalid/expired — nothing to blacklist

        response = Response({"message": "Logout successful"})

        # ✅ Clear cookies (must match path/domain/samesite used when setting them)
        response.delete_cookie(
            key="access",
            samesite="None",
        )
        response.delete_cookie(
            key="refresh",
            samesite="None",
        )

        return response

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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
