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


# -----------------------
# ReplaceOption Serializer
# -----------------------
class ReplaceOptionSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    category = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = ReplaceOption
        fields = ['id', 'title', 'description', 'category', 'category_id']


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
class ProductSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'description', 'category', 'category_id',
             'status', 'created_at', 'thumbnail'
        ]
        read_only_fields = ['status', 'created_at']

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

# -----------------------
# ProductImage Serializer (optional)
# -----------------------
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'created_at', 'product']
        read_only_fields = ['created_at', 'product']
