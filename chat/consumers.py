# chat/consumers.py

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def connect(self):
        self.request_id  = self.scope["url_route"]["kwargs"]["request_id"]
        self.room_group  = f"chat_{self.request_id}"
        user             = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close()
            return

        self.user       = user
        self.user_email = user.email

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

        # ✅ Tell every other member of this room this user is now online
        await self.channel_layer.group_send(self.room_group, {
            "type":   "presence",
            "status": "online",
            "email":  self.user_email,
        })

        # Send history
        messages = await self.get_history()
        await self.send(text_data=json.dumps({"type": "history", "messages": messages}))

        # ✅ Mark all unread messages (sent by the OTHER user) as seen
        await self.mark_all_seen()
        # Tell the sender their messages were seen
        await self.channel_layer.group_send(self.room_group, {
            "type":       "all_seen",
            "reader":     self.user_email,
            "request_id": self.request_id,
        })

    async def disconnect(self, code):
        if not hasattr(self, "room_group"):
            return
        # ✅ Tell every other member this user went offline
        await self.channel_layer.group_send(self.room_group, {
            "type":   "presence",
            "status": "offline",
            "email":  self.user_email,
        })
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    # ─── Receive from browser ─────────────────────────────────────────────────

    async def receive(self, text_data):
        data    = json.loads(text_data)
        msg_type = data.get("type", "message")

        if msg_type == "seen" and "message_id" in data:
            # Client explicitly marks a single message as seen
            await self.mark_seen(data["message_id"])
            await self.channel_layer.group_send(self.room_group, {
                "type":       "seen_ack",
                "message_id": str(data["message_id"]),
                "reader":     self.user_email,
            })
            return

        text = data.get("text", "").strip()
        if not text:
            return

        msg = await self.save_message(self.user, text)

        await self.channel_layer.group_send(self.room_group, {
            "type":         "chat_message",
            "id":           msg["id"],
            "text":         msg["text"],
            "sender_email": msg["sender_email"],
            "created_at":   msg["created_at"],
            "seen":         False,
        })

    # ─── Group event handlers (sent to this socket) ───────────────────────────

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type":         "message",
            "id":           event["id"],
            "text":         event["text"],
            "sender_email": event["sender_email"],
            "created_at":   event["created_at"],
            "seen":         event.get("seen", False),
        }))

    async def presence(self, event):
        # Don't echo presence back to the user who triggered it
        if event["email"] == self.user_email:
            return
        await self.send(text_data=json.dumps({
            "type":   "presence",
            "status": event["status"],   # "online" | "offline"
            "email":  event["email"],
        }))

    async def seen_ack(self, event):
        # Don't send seen_ack back to the reader themselves
        if event["reader"] == self.user_email:
            return
        await self.send(text_data=json.dumps({
            "type":       "seen_ack",
            "message_id": event["message_id"],
            "reader":     event["reader"],
        }))

    async def all_seen(self, event):
        # Notify the sender that all their messages were read on connect
        if event["reader"] == self.user_email:
            return
        await self.send(text_data=json.dumps({
            "type":   "all_seen",
            "reader": event["reader"],
        }))

    # ─── DB helpers ───────────────────────────────────────────────────────────

    @database_sync_to_async
    def save_message(self, user, text):
        from .serializers import ChatMessageSerializer
        from .models import ChatMessage
        msg = ChatMessage.objects.create(
            barter_request_id=self.request_id,
            sender=user,
            text=text,
        )
        return ChatMessageSerializer(msg).data

    @database_sync_to_async
    def get_history(self):
        from .serializers import ChatMessageSerializer
        from .models import ChatMessage
        msgs = (
            ChatMessage.objects
            .filter(barter_request_id=self.request_id)
            .select_related("sender")
            .order_by("created_at")[:50]
        )
        return ChatMessageSerializer(msgs, many=True).data

    @database_sync_to_async
    def mark_seen(self, message_id):
        from .models import ChatMessage
        ChatMessage.objects.filter(
            id=message_id,
            barter_request_id=self.request_id,
        ).exclude(sender=self.user).update(seen=True)

    @database_sync_to_async
    def mark_all_seen(self):
        """Mark every unread message in this room (not sent by self) as seen."""
        from .models import ChatMessage
        ChatMessage.objects.filter(
            barter_request_id=self.request_id,
            seen=False,
        ).exclude(sender=self.user).update(seen=True)