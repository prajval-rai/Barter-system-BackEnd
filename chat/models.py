from django.db import models
from barter.models import BarterRequest
from django.contrib.auth.models import User

# Create your models here.
class ChatMessage(models.Model):
    barter_request_id = models.IntegerField(db_index=True)
    sender            = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    text       = models.TextField()
    seen       = models.BooleanField(default=False)   # ✅ NEW
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ["created_at"]
 
    def __str__(self):
        return f"[{self.barter_request_id}] {self.sender.email}: {self.text[:40]}"
 