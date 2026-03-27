from django.contrib.auth.models import User
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    STATUS_CHOICES = (
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("closed", "Closed"),
        ("rejected", "Rejected"),
        ("banned", "Banned"),
    )

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Submitted")

    created_at = models.DateTimeField(auto_now_add=True)

    purchase_bill = models.FileField(upload_to="product_bill/", null=True, blank=True)

    purchase_year = models.IntegerField(null=True,blank=True)


    def __str__(self):
        return self.title




class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    created_at = models.DateTimeField(auto_now_add=True)


