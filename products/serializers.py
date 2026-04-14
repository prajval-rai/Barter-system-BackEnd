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
        fields = ['id', 'title', 'description', 'category', 'category_id', 'replace_type', 'point_value', 'meta','icon']

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
             'replace_options', 'product_replace_options','purchase_year','purchase_bill'
        ]
        read_only_fields = ['status', 'created_at', 'product_replace_options',"title"]

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
             'status', 'created_at','replace_options','product_replace_options',
             'purchase_year','purchase_bill'
        ]
        read_only_fields = ['status', 'created_at']
    
    def get_product_replace_options(self, obj):
        return ReplaceOptionSerializer(obj.replace_options.all(), many=True).data

    def create(self, validated_data):
        category = validated_data.pop('category', None)

        product_kwargs = {
            'owner': self.context['request'].user,
            'category': category,
        }
        

        product_kwargs.update(validated_data)
        return Product.objects.create(**product_kwargs)

    def update(self, instance, validated_data):
        category = validated_data.pop('category', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if category:
            instance.category = category
    

        instance.save()
        return instance







class GetProductSerializer(serializers.ModelSerializer):
    replace_options = ReplaceOptionSerializer(many=True, write_only=True, required=False)
    product_replace_options = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'description',
            'category',
            'category_id',
            'thumbnail',   # 👈 single image only
            'status',
            'created_at',
            'replace_options',
            'product_replace_options',
            'purchase_year',
            'purchase_bill',
        ]
        read_only_fields = ['status', 'created_at']

    def get_thumbnail(self, obj):
        first_image = obj.images.first()
        if first_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None

    def get_product_replace_options(self, obj):
        return ReplaceOptionSerializer(obj.replace_options.all(), many=True).data

    def create(self, validated_data):
        category = validated_data.pop('category', None)

        product_kwargs = {
            'owner': self.context['request'].user,
            'category': category,
        }

        product_kwargs.update(validated_data)
        return Product.objects.create(**product_kwargs)

    def update(self, instance, validated_data):
        category = validated_data.pop('category', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if category:
            instance.category = category

        instance.save()
        return instance



class MarketReplaceOptionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", default=None)

    class Meta:
        model  = ReplaceOption
        fields = ["id", "replace_type", "title", "description", "category_name", "point_value"]


class MarketplaceProductSerializer(serializers.ModelSerializer):
    category_name   = serializers.CharField(source="category.name", default=None)
    owner_name      = serializers.SerializerMethodField()
    thumbnail       = serializers.SerializerMethodField()
    replace_options = MarketReplaceOptionSerializer(many=True, read_only=True)

    class Meta:
        model  = Product
        fields = [
            "id",
            "title",
            "description",
            "category",          # id
            "category_name",
            "status",
            "created_at",
            "purchase_year",
            "owner_name",
            "thumbnail",
            "replace_options",
        ]

    def get_owner_name(self, obj):
        u = obj.owner
        full = f"{u.first_name} {u.last_name}".strip()
        return full or u.username

    def get_thumbnail(self, obj):
        request = self.context.get("request")
        # Assumes related_name="images" on your ProductImage model
        # and the image field is called `image` (FileField / ImageField)
        first = obj.images.first()
        if not first:
            return None
        try:
            url = first.image.url
            return request.build_absolute_uri(url) if request else url
        except Exception:
            return None
        

        