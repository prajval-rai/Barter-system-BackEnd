from django.db import models
from products.models import Product,Category
from django.contrib.auth.models import User

class ReplaceOption(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="replace_options")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.product.title} → {self.title}"


class BarterRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
    )

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_requests")
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_requests")

    requested_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="offers_received")

    extra_offer = models.TextField(blank=True)  # cash / service / add-on
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_user} → {self.to_user}"

