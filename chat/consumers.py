# chat/consumers.py

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER — push a fresh unread count to a specific user's personal channel
#  group.  Call this from anywhere (save_message, mark_seen, etc.)
# ─────────────────────────────────────────────────────────────────────────────

@database_sync_to_async
def _get_unread_counts_per_chat(user_email: str) -> dict:
    from chat.models import ChatMessage
    from barter.models import BarterRequest
    from django.db.models import Count, Q

    active_request_ids = BarterRequest.objects.filter(
        status="accepted"
    ).filter(
        Q(from_user__email=user_email) | Q(to_user__email=user_email)
    ).values_list("id", flat=True)

    counts = (
        ChatMessage.objects
        .filter(
            barter_request_id__in=active_request_ids,  # ← use barter_request_id
            seen=False,
        )
        .exclude(sender__email=user_email)
        .values('barter_request_id')
        .annotate(count=Count('id'))
    )

    return {str(row['barter_request_id']): row['count'] for row in counts}

async def push_unread_count(channel_layer, user_email: str):
    counts = await _get_unread_counts_per_chat(user_email)  # dict {req_id: count}
    await channel_layer.group_send(
        _unread_group(user_email),
        {"type": "unread_count_update", "counts": counts},
    )


def _unread_group(email: str) -> str:
    """Stable personal group name — one per user."""
    # Replace @ and . so it's a valid channel-layer group name
    safe = email.replace("@", "_at_").replace(".", "_dot_")
    return f"unread_{safe}"


@database_sync_to_async
def _get_unread_count(user_email: str) -> int:
    from chat.models import ChatMessage
    from barter.models import BarterRequest          # adjust import to your app

    # All accepted/active barter requests this user is part of
    active_requests = BarterRequest.objects.filter(
        status="accepted"
    ).filter(
        # user is either side of the trade
        __import__('django.db.models', fromlist=['Q']).Q(from_user__email=user_email) |
        __import__('django.db.models', fromlist=['Q']).Q(to_user__email=user_email)
    ).values_list("id", flat=True)

    return ChatMessage.objects.filter(
        barter_request_id__in=active_requests,
        seen=False,
    ).exclude(
        sender__email=user_email,
    ).count()


# ─────────────────────────────────────────────────────────────────────────────
#  CHAT CONSUMER  (existing, extended with unread broadcasting)
# ─────────────────────────────────────────────────────────────────────────────

class ChatConsumer(AsyncWebsocketConsumer):

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def connect(self):
        self.request_id         = self.scope["url_route"]["kwargs"]["request_id"]
        self.room_group         = f"chat_{self.request_id}"
        user                    = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close()
            return

        self.user               = user
        self.user_email         = user.email
        self.channel_name_saved = self.channel_name

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

        # 1. Announce online
        await self.channel_layer.group_send(self.room_group, {
            "type":   "presence",
            "status": "online",
            "email":  self.user_email,
        })

        # 2. Ask others for their status
        await self.channel_layer.group_send(self.room_group, {
            "type":            "presence_query",
            "requester_email": self.user_email,
            "reply_channel":   self.channel_name,
        })

        # 3. Send history
        messages = await self.get_history()
        await self.send(text_data=json.dumps({"type": "history", "messages": messages}))

        # 4. Mark all unread as seen & broadcast updated counts to BOTH users
        await self.mark_all_seen()

        # Tell the room the reader has seen everything
        await self.channel_layer.group_send(self.room_group, {
            "type":       "all_seen",
            "reader":     self.user_email,
            "request_id": self.request_id,
        })

        # Push fresh unread counts to both participants
        other_email = await self.get_other_participant_email()
        await push_unread_count(self.channel_layer, self.user_email)
        if other_email:
            await push_unread_count(self.channel_layer, other_email)

    async def disconnect(self, code):
        if not hasattr(self, "room_group"):
            return
        await self.channel_layer.group_send(self.room_group, {
            "type":   "presence",
            "status": "offline",
            "email":  self.user_email,
        })
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    # ─── Receive from browser ─────────────────────────────────────────────────

    async def receive(self, text_data):
        data     = json.loads(text_data)
        msg_type = data.get("type", "message")

        if msg_type == "seen" and "message_id" in data:
            await self.mark_seen(data["message_id"])
            await self.channel_layer.group_send(self.room_group, {
                "type":       "seen_ack",
                "message_id": str(data["message_id"]),
                "reader":     self.user_email,
            })
            # Refresh unread count for the reader (count went down)
            await push_unread_count(self.channel_layer, self.user_email)
            return

        # ── Save new message ──────────────────────────────────────────────────
        text = data.get("text", "").strip()
        media = data.get("media", [])

        if not text and not media:
            return

        pending_key = data.get("pending_key")
        msg = await self.save_message(self.user, text, media)

        await self.channel_layer.group_send(self.room_group, {
            "type":           "chat_message",
            "id":             msg["id"],
            "text":           msg["text"],
            "sender_email":   msg["sender_email"],
            "created_at":     msg["created_at"],
            "seen":           False,
            "pending_key":    pending_key,
            "sender_channel": self.channel_name,
            "media":          msg.get("media", []),
        })

        # Push fresh unread count to the OTHER participant
        other_email = await self.get_other_participant_email()
        if other_email:
            await push_unread_count(self.channel_layer, other_email)

    # ─── Group event handlers ─────────────────────────────────────────────────

    async def chat_message(self, event):
        is_sender   = event.get("sender_channel") == self.channel_name
        pending_key = event.get("pending_key") if is_sender else None

        payload = {
            "type":         "message",
            "id":           event["id"],
            "text":         event["text"],
            "sender_email": event["sender_email"],
            "created_at":   event["created_at"],
            "seen":         event.get("seen", False),
            "media":        event.get("media", []),
        }
        if pending_key is not None:
            payload["pending_key"] = pending_key

        await self.send(text_data=json.dumps(payload))

    async def presence(self, event):
        if event["email"] == self.user_email:
            return
        await self.send(text_data=json.dumps({
            "type":   "presence",
            "status": event["status"],
            "email":  event["email"],
        }))

    async def presence_query(self, event):
        if event["requester_email"] == self.user_email:
            return
        await self.channel_layer.send(event["reply_channel"], {
            "type":   "presence_reply",
            "status": "online",
            "email":  self.user_email,
        })

    async def presence_reply(self, event):
        await self.send(text_data=json.dumps({
            "type":   "presence",
            "status": event["status"],
            "email":  event["email"],
        }))

    async def seen_ack(self, event):
        if event["reader"] == self.user_email:
            return
        await self.send(text_data=json.dumps({
            "type":       "seen_ack",
            "message_id": event["message_id"],
            "reader":     event["reader"],
        }))

    async def all_seen(self, event):
        if event["reader"] == self.user_email:
            return
        await self.send(text_data=json.dumps({
            "type":   "all_seen",
            "reader": event["reader"],
        }))

    # ─── DB helpers ───────────────────────────────────────────────────────────

    @database_sync_to_async
    def save_message(self, user, text, media=None):
        from chat.serializers import ChatMessageSerializer
        from chat.models import ChatMessage
        msg = ChatMessage.objects.create(
            barter_request_id=self.request_id,
            sender=user,
            text=text,
        )
        # If your ChatMessage model supports media, attach here:
        # if media: msg.media.set(...)
        return ChatMessageSerializer(msg).data

    @database_sync_to_async
    def get_history(self):
        from chat.serializers import ChatMessageSerializer
        from chat.models import ChatMessage
        msgs = (
            ChatMessage.objects
            .filter(barter_request_id=self.request_id)
            .select_related("sender")
            .order_by("created_at")[:50]
        )
        return ChatMessageSerializer(msgs, many=True).data

    @database_sync_to_async
    def mark_seen(self, message_id):
        from chat.models import ChatMessage
        ChatMessage.objects.filter(
            id=message_id,
            barter_request_id=self.request_id,
        ).exclude(sender=self.user).update(seen=True)

    @database_sync_to_async
    def mark_all_seen(self):
        from chat.models import ChatMessage
        ChatMessage.objects.filter(
            barter_request_id=self.request_id,
            seen=False,
        ).exclude(sender=self.user).update(seen=True)

    @database_sync_to_async
    def get_other_participant_email(self) -> str | None:
        """Return the email of the OTHER user in this barter request."""
        try:
            from barter.models import BarterRequest          # adjust import
            req = BarterRequest.objects.select_related(
                "from_user", "to_user"
            ).get(id=self.request_id)
            if req.from_user.email == self.user_email:
                return req.to_user.email
            return req.from_user.email
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────────────────────
#  UNREAD COUNT CONSUMER
#  Frontend connects once on app load: ws://…/ws/unread/
#  It receives {"type": "unread_count", "count": N} whenever the count changes.
# ─────────────────────────────────────────────────────────────────────────────

class UnreadCountConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return

        self.user_email = user.email
        self.user_group = _unread_group(self.user_email)

        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

        # Send per-chat counts immediately on connect
        counts = await _get_unread_counts_per_chat(self.user_email)
        await self.send(text_data=json.dumps({
            "type":   "unread_counts",   # note: plural
            "counts": counts,
        }))

async def unread_count_update(self, event):
    await self.send(text_data=json.dumps({
        "type":   "unread_counts",
        "counts": event["counts"],
    }))
    async def disconnect(self, code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Client can send {"type": "ping"} to request a fresh count
        try:
            data = json.loads(text_data or "{}")
        except Exception:
            return

        if data.get("type") == "ping":
            count = await _get_unread_count(self.user_email)
            await self.send(text_data=json.dumps({
                "type":  "unread_count",
                "count": count,
            }))

    # Called by channel layer when push_unread_count fires
    async def unread_count_update(self, event):
        await self.send(text_data=json.dumps({
            "type":  "unread_count",
            "count": event["count"],
        }))