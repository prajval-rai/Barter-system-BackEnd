from django.db import models
from products.models import Product,Category
from django.contrib.auth.models import User

class ReplaceOption(models.Model):
    

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="replace_options")
    replace_type = models.CharField(max_length=10, default="product",null=True,blank=True)

    # Only for product type
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    # Only for point type
    point_value = models.PositiveIntegerField(null=True, blank=True)
    meta = models.JSONField(blank=True, null=True)  # Store MRP, usage, condition, purchase_year

    icon = models.CharField(max_length=100, default="noto:package")


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

    from_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_requests"
    )

    to_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_requests"
    )

    request_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="products_offered"
    )

    request_for_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="products_requested"
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    msg = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_user} offering {self.request_product} for {self.request_for_product}"


class SaveProducts(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    created_at= models.DateTimeField(auto_now_add=True)


