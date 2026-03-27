from rest_framework import serializers
from .models import BarterRequest
from products.models import Product

class BarterRequestCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = BarterRequest
        fields = [
            "request_product",
            "request_for_product",
        ]

class ProductBasicSerializer(serializers.ModelSerializer):

    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "title", "thumbnail"]

    def get_thumbnail(self, obj):
        image = obj.images.first()
        if not image:
            return None
        request = self.context.get("request")
        if request is None:
            # GCS URLs are already absolute — return directly
            return image.image.url
        return request.build_absolute_uri(image.image.url)
        
    

class BarterRequestSerializer(serializers.ModelSerializer):

    request_product = ProductBasicSerializer(read_only=True)
    request_for_product = ProductBasicSerializer(read_only=True)

    from_user = serializers.CharField(source="from_user.username", read_only=True)
    to_user = serializers.CharField(source="to_user.username", read_only=True)

    class Meta:
        model = BarterRequest
        fields = [
            "id",
            "from_user",
            "to_user",
            "request_product",
            "request_for_product",
            "status",
            "created_at",
        ]