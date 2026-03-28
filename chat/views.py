from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import ChatMessage
from .serializers import ChatMessageSerializer
import random
import string
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache  



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_history(request, request_id):
    msgs = ChatMessage.objects.filter(
        barter_request_id=request_id
    ).select_related('sender').order_by('created_at')[:100]
    return Response(ChatMessageSerializer(msgs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_ws_token(request):
    """
    Returns the raw access token from the cookie so the frontend
    can pass it as ?token= when opening a WebSocket connection.
    The user must already be authenticated (cookie present) to call this.
    """
    raw_token = request.COOKIES.get("access")
    if not raw_token:
        return Response({"error": "No token"}, status=401)
    return Response({"token": raw_token})



# ── helpers ──────────────────────────────────────────────────────────────────
 
def _otp_key(request_id: int) -> str:
    return f"barter:otp:{request_id}"
 
 
def _make_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))
 
 
# ── generate ─────────────────────────────────────────────────────────────────
 
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_otp(request, pk: int):
    """
    Called by the deal *initiator* (from_user).
    Generates a 6-digit OTP, stores it in cache for 10 minutes,
    and returns it to the frontend so the initiator can share it verbally / in-app.
    """
    from barter.models import BarterRequest   # adjust import to your app
 
    try:
        barter = BarterRequest.objects.get(pk=pk)
    except BarterRequest.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
 
    # Only the initiator (from_user) can generate the OTP
    if barter.from_user != request.user:
        return Response({"error": "Only the deal initiator can generate an OTP."}, status=403)
 
    if barter.status != "accepted":
        return Response({"error": "Deal is not in an accepted state."}, status=400)
 
    otp = _make_otp()
    cache.set(_otp_key(pk), otp, timeout=600)   # 10 minutes
    return Response({"otp": otp})
 
 
# ── verify ───────────────────────────────────────────────────────────────────
 
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_otp(request, pk: int):
    """
    Called by the deal *receiver* (to_user) who enters the OTP.
    If valid, marks the barter request as completed.
    """
    from barter.models import BarterRequest   # adjust import to your app
 
    try:
        barter = BarterRequest.objects.get(pk=pk)
    except BarterRequest.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
 
    # Only the receiver should verify
    if barter.to_user != request.user:
        return Response({"error": "Only the trade recipient can verify the OTP."}, status=403)
 
    if barter.status != "accepted":
        return Response({"error": "Deal is not in an accepted state."}, status=400)
 
    submitted = request.data.get("otp", "").strip()
    stored    = cache.get(_otp_key(pk))
 
    if not stored:
        return Response({"error": "OTP has expired. Ask the other party to generate a new one."}, status=400)
 
    if submitted != stored:
        return Response({"error": "Invalid OTP. Please try again."}, status=400)
 
    # ✅ Valid — mark as completed
    barter.status = "completed"
    barter.save(update_fields=["status"])
    cache.delete(_otp_key(pk))   # one-time use
 
    return Response({"status": "completed"})
 
 
# # ── rate ─────────────────────────────────────────────────────────────────────
 
# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def rate_trade(request, pk: int):
#     """
#     POST { rating: 1-5, review: str, rated_user: email }
#     Creates or updates a TradeRating for this barter request.
 
#     You'll need a TradeRating model like:
#         class TradeRating(models.Model):
#             barter_request = models.ForeignKey(BarterRequest, on_delete=models.CASCADE, related_name="ratings")
#             rater    = models.ForeignKey(User, on_delete=models.CASCADE, related_name="given_ratings")
#             rated    = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_ratings")
#             rating   = models.PositiveSmallIntegerField()          # 1-5
#             review   = models.TextField(blank=True, default="")
#             created_at = models.DateTimeField(auto_now_add=True)
#             class Meta:
#                 unique_together = ("barter_request", "rater")
#     """
#     from barter.models import BarterRequest, TradeRating   # adjust imports
#     from django.contrib.auth import get_user_model
#     User = get_user_model()
 
#     try:
#         barter = BarterRequest.objects.get(pk=pk)
#     except BarterRequest.DoesNotExist:
#         return Response({"error": "Not found"}, status=404)
 
#     if barter.status != "completed":
#         return Response({"error": "Can only rate completed trades."}, status=400)
 
#     rating_value = int(request.data.get("rating", 0))
#     if not (1 <= rating_value <= 5):
#         return Response({"error": "Rating must be between 1 and 5."}, status=400)
 
#     rated_email = request.data.get("rated_user", "")
#     try:
#         rated_user = User.objects.get(email=rated_email)
#     except User.DoesNotExist:
#         return Response({"error": "Rated user not found."}, status=404)
 
#     review = request.data.get("review", "").strip()
 
#     TradeRating.objects.update_or_create(
#         barter_request=barter,
#         rater=request.user,
#         defaults={"rated": rated_user, "rating": rating_value, "review": review},
#     )
#     return Response({"status": "ok"})