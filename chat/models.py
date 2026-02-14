from django.db import models
from barter.models import BarterRequest
from django.contrib.auth.models import User

# Create your models here.
class ChatRoom(models.Model):
    barter_request = models.OneToOneField(BarterRequest, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
