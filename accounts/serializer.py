from rest_framework import serializers
from .models import CustomUser,UserNotification


# -----------------------
# Category Serializer
# -----------------------
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'name']



class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = "__all__"


class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = '__all__'
        read_only_fields = ['user']