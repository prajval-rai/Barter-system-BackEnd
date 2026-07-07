from django.contrib.auth.models import User
from django.db import models
from django.contrib.auth import get_user_model
from encrypted_model_fields.fields import EncryptedCharField
from .utils import make_hash
from django.contrib.auth.models import AbstractUser
from django.conf import settings



class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("Admin", "Admin"),
        ("User", "User")
    )
    first_name = EncryptedCharField(max_length=150, blank=True)
    last_name  = EncryptedCharField(max_length=150, blank=True)
    email      = EncryptedCharField(max_length=255, blank=True)
    contact_number = EncryptedCharField(max_length=11, null=True, blank=True)
    contact_hash   = models.CharField(max_length=64, null=True, db_index=True)
    email_hash     = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    is_verified      = models.BooleanField(default=False)
    token_created_at = models.DateTimeField(null=True, blank=True)
    latitude = models.FloatField(null=True,blank=True)
    longitude = models.FloatField(null=True,blank=True)
    address = models.TextField(blank=True,null=True)
    description = models.TextField(blank=True,null=True)
    rating = models.FloatField(blank=True,null=True)
    role = models.CharField(max_length=30,default="User", choices=ROLE_CHOICES)
    city = models.CharField(max_length=50,blank=True,null=True)
    pincode = models.CharField(max_length=50,blank=True,null=True)

    USERNAME_FIELD  = "username"
    REQUIRED_FIELDS = ["email"]

    groups = models.ManyToManyField(
        "auth.Group", blank=True,
        related_name="customuser_set", related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission", blank=True,
        related_name="customuser_set", related_query_name="customuser",
    )

    class Meta:
        db_table = "custom_user"

    def save(self, *args, **kwargs):
        if self.contact_number:
            self.contact_hash = make_hash(self.contact_number)
        if self.email:
            self.email_hash = make_hash(self.email)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email



class UserNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    description = models.TextField()
    redirect = models.CharField(max_length=30)
    status = models.BooleanField(default=False)  # fixed typo: staus → status


class FCMToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fcm_tokens")
    token = models.TextField(unique=True)
    device_type = models.CharField(
        max_length=20,
        choices=[("android", "Android"), ("ios", "iOS"), ("web", "Web")]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.device_type}"
