from rest_framework import serializers
from .models import Product, ProductImage, Category
from barter.models import ReplaceOption


# -----------------------
# Category Serializer
# -----------------------
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class ReplaceOptionSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False,  # <-- make optional
        allow_null=True  # <-- allow null for point type
    )
    category = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = ReplaceOption
        fields = ['id', 'title', 'description', 'category', 'category_id', 'replace_type', 'point_value', 'meta']

    def validate(self, attrs):
        replace_type = attrs.get('replace_type', getattr(self.instance, 'replace_type', None))

        # Product type must have category
        if replace_type == "product" and not attrs.get('category'):
            raise serializers.ValidationError({"category_id": "This field is required for product type."})

        # Point type can have category null
        return attrs


class ProductListSerializer(serializers.ModelSerializer):
    replace_options = ReplaceOptionSerializer(many=True,write_only=True,required=False)
    product_replace_options = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'description',
            'created_at',
            'thumbnail', 'replace_options', 'product_replace_options'
        ]
        read_only_fields = ['status', 'created_at', 'thumbnail', 'product_replace_options',"title"]

    def get_product_replace_options(self, obj):
        return ReplaceOptionSerializer(obj.replace_options.all(), many=True).data





# -----------------------
# Product Serializer
# -----------------------

# -----------------------
# ProductImage Serializer (optional)
# -----------------------
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'created_at', 'product']
        read_only_fields = ['created_at', 'product']
        
class ProductSerializer(serializers.ModelSerializer):
    replace_options = ReplaceOptionSerializer(many=True,write_only=True,required=False)
    product_replace_options = serializers.SerializerMethodField()
    images = ProductImageSerializer(
        many=True, read_only=True
    )  # 👈 THIS LINE
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'description', 'category', 'category_id',"images",
             'status', 'created_at', 'thumbnail','replace_options','product_replace_options'
        ]
        read_only_fields = ['status', 'created_at']
    
    def get_product_replace_options(self, obj):
        return ReplaceOptionSerializer(obj.replace_options.all(), many=True).data

    def create(self, validated_data):
        category = validated_data.pop('category', None)
        thumbnail = validated_data.pop('thumbnail', None)

        product_kwargs = {
            'owner': self.context['request'].user,
            'category': category,
        }
        if thumbnail:
            product_kwargs['thumbnail'] = thumbnail

        product_kwargs.update(validated_data)
        return Product.objects.create(**product_kwargs)

    def update(self, instance, validated_data):
        category = validated_data.pop('category', None)
        thumbnail = validated_data.pop('thumbnail', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if category:
            instance.category = category
        if thumbnail:
            instance.thumbnail = thumbnail

        instance.save()
        return instance


