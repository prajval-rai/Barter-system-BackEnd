from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from helper_function.config import Config
from django.utils import timezone
from .models import UserProfile
from .serializer import ProfileSerializer


GOOGLE_CLIENT_ID = Config.google_key


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

        # ✅ Get or create user
        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            }
        )

        # ✅ Ensure UserProfile exists
        profile, _ = UserProfile.objects.get_or_create(user=user)

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
                "role": profile.role,
                "address":profile.address,
                "lat":profile.latitude,
                "long":profile.longitude
            }
        })

        # ✅ Set Cookies
        response.set_cookie(
            key="access",
            value=tokens["access"],
            httponly=True,
            secure=False,  # change to True in production
            samesite="Lax",
            domain="localhost"
        )

        response.set_cookie(
            key="refresh",
            value=tokens["refresh"],
            httponly=True,
            secure=False,  # change to True in production
            samesite="Lax",
            domain="localhost"
        )

        return response

    except ValueError:
        return Response(
            {"error": "Invalid Google token"},
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

    # Delete cookies
    response.delete_cookie("access")
    response.delete_cookie("refresh")

    return response


@api_view(["GET"])
def profile(request):
    try:
        profile_object = UserProfile.objects.get(user=request.user.id)
        profile_serialize = ProfileSerializer(profile_object).data
        return Response({"data":profile_serialize})
    except Exception as e:
        return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
    

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    try:
        profile_object = UserProfile.objects.get(user=request.user)

        serializer = ProfileSerializer(
            profile_object,
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

    except UserProfile.DoesNotExist:
        return Response(
            {"message": "Profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )