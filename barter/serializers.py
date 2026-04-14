from rest_framework import serializers
from .models import BarterRequest,SaveProducts
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

    request_product     = ProductBasicSerializer(read_only=True)
    request_for_product = ProductBasicSerializer(read_only=True)
    from_user = serializers.CharField(source="from_user.email", read_only=True)
    to_user   = serializers.CharField(source="to_user.email",   read_only=True)

    # ── New fields from annotations ───────────────────────────────────────────
    unread_count         = serializers.IntegerField(read_only=True, default=0)
    last_message         = serializers.CharField(read_only=True, default="", allow_null=True)
    last_message_time    = serializers.DateTimeField(read_only=True, default=None, allow_null=True)
    last_message_sender  = serializers.CharField(read_only=True, default="", allow_null=True)

    class Meta:
        model  = BarterRequest
        fields = [
            "id",
            "from_user",
            "to_user",
            "request_product",
            "request_for_product",
            "status",
            "created_at",
            # new
            "unread_count",
            "last_message",
            "last_message_time",
            "last_message_sender",
        ]



class SaveProductsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaveProducts
        fields = '__all__'
        read_only_fields = ['user', 'created_at']