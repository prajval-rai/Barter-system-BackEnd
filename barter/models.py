from django.db import models
from products.models import Product,Category
from django.contrib.auth.models import User

class ReplaceOption(models.Model):
    REPLACE_TYPE_CHOICES = (
        ("product", "Product"),
        ("point", "Point"),
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="replace_options")
    replace_type = models.CharField(max_length=10, choices=REPLACE_TYPE_CHOICES, default="product")

    # Only for product type
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    # Only for point type
    point_value = models.PositiveIntegerField(null=True, blank=True)
    meta = models.JSONField(blank=True, null=True)  # Store MRP, usage, condition, purchase_year

    def __str__(self):
        if self.replace_type == "product":
            return f"{self.product.title} → {self.title}"
        return f"{self.product.title} → {self.point_value} pts"



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

