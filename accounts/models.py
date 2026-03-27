from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ("Admin", "Admin"),
        ("User", "User")
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    latitude = models.FloatField(null=True,blank=True)
    longitude = models.FloatField(null=True)
    address = models.TextField(blank=True,null=True)
    description = models.TextField(blank=True,null=True)
    rating = models.FloatField(blank=True,null=True)
    role = models.CharField(max_length=30,default="User", choices=ROLE_CHOICES)
    contact_number = models.CharField(max_length=10,null=True,blank=True)

    def __str__(self):
        return self.user.username



class UserNotification(models.Model):

    user = models.ForeignKey(User,on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    description = models.TextField()
    redirect = models.CharField(max_length=30)
    staus = models.BooleanField(default=False)
