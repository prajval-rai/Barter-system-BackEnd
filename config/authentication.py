from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions


from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions

class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that reads the access token from cookies instead of headers
    """
    def authenticate(self, request):
        print("---------------------------",request.COOKIES)
        token = request.COOKIES.get("access")
        if not token:
            return None  # ✅ No token → anonymous user

        try:
            validated_token = self.get_validated_token(token)
            return self.get_user(validated_token), validated_token
        # except exceptions.AuthenticationFailed:
        #     # Already a JWT exception → propagate
        #     raise
        except Exception as e:
            # Any other error → treat as invalid token
            raise exceptions.AuthenticationFailed(f"Invalid token: {str(e)}")
