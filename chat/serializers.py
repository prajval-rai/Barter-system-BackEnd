from rest_framework import serializers
from .models import ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source="sender.email", read_only=True)
 
    class Meta:
        model  = ChatMessage
        fields = ["id", "text", "sender_email", "seen", "created_at"]