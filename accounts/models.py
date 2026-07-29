from django.contrib.auth.models import User
from django.db import models
from django.contrib.auth import get_user_model
from encrypted_model_fields.fields import EncryptedCharField
from .utils import make_hash
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator



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

 
class Review(models.Model):
    """
    One user rating/reviewing another — e.g. after completing a trade.
    """
 
    # ✅ The user being rated
    rated_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_received",
    )
 
    # ✅ The user who wrote the review
    rated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_given",
    )
 
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True, null=True)
 
    # If reviews are tied to a specific trade/deal, point this at that
    # model instead — swap in your Trade FK here, e.g.:
    # trade = models.ForeignKey("trades.Trade", on_delete=models.CASCADE, related_name="reviews")
 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        db_table = "review"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["rated_user"]),
        ]
        constraints = [
            # A user can't rate themselves
            models.CheckConstraint(
                check=~models.Q(rated_user=models.F("rated_by")),
                name="review_no_self_rating",
            ),
        ]
 
    def __str__(self):
        return f"{self.rated_by} → {self.rated_user}: {self.rating}★"


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
