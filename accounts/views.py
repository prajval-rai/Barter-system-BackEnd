from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from helper_function.config import Config
from django.utils import timezone

GOOGLE_CLIENT_ID = Config.google_key


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }




@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    """
    Google Login
    Frontend sends: { "token": "google-id-token" }
    """
    print("lllllllllllllllllll")
    token = request.data.get("token")
    print("===============================")
    if not token:
        return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Verify Google token
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)

        email = idinfo.get('email')
        first_name = idinfo.get('given_name', '')
        last_name = idinfo.get('family_name', '')

        # Get or create Django user
        user, created = User.objects.get_or_create(username=email, defaults={
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'last_login' : timezone.now()
        })

        # Generate JWT tokens
        tokens = get_tokens_for_user(user)
        print("-----------------------------",tokens)
        
        res = Response({
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "tokens": tokens
        })

        return res
    except ValueError as e:
        return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)


