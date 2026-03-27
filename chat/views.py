from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import ChatMessage
from .serializers import ChatMessageSerializer

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