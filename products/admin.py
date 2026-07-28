from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductImage, BookMarkProduct


# ─────────────────────────────────────────────────────────────
# Category
# ─────────────────────────────────────────────────────────────
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "product_count")
    search_fields = ("name",)
    ordering = ("name",)

    def product_count(self, obj):
        return obj.product_set.count()
    product_count.short_description = "Products"


# ─────────────────────────────────────────────────────────────
# Product images shown inline inside the Product admin page
# ─────────────────────────────────────────────────────────────
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("image", "image_preview", "created_at")
    readonly_fields = ("image_preview", "created_at")

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:6px;object-fit:cover;" />',
                obj.image.url,
            )
        return "-"
    image_preview.short_description = "Preview"


# ─────────────────────────────────────────────────────────────
# Product
# ─────────────────────────────────────────────────────────────
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "owner",
        "category",
        "condition",
        "purchase_year",
        "status",
        "image_count",
        "has_bill",
        "created_at",
    )
    list_display_links = ("id", "title")
    list_editable = ("status",)
    list_filter = ("status", "condition", "category", "created_at")
    search_fields = ("title", "description", "owner__username", "owner__email")
    autocomplete_fields = ("owner", "category")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    inlines = [ProductImageInline]
    list_per_page = 25

    fieldsets = (
        ("Basic Info", {
            "fields": ("owner", "title", "description", "category")
        }),
        ("Condition & Purchase", {
            "fields": ("condition", "purchase_year", "purchase_bill")
        }),
        ("Status", {
            "fields": ("status", "created_at")
        }),
    )

    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = "Images"

    def has_bill(self, obj):
        return bool(obj.purchase_bill)
    has_bill.boolean = True
    has_bill.short_description = "Bill Uploaded"


# ─────────────────────────────────────────────────────────────
# ProductImage (also viewable/manageable on its own)
# ─────────────────────────────────────────────────────────────
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "image_preview", "created_at")
    list_filter = ("created_at",)
    search_fields = ("product__title",)
    readonly_fields = ("image_preview",)
    ordering = ("-created_at",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:50px;border-radius:6px;object-fit:cover;" />',
                obj.image.url,
            )
        return "-"
    image_preview.short_description = "Preview"


# ─────────────────────────────────────────────────────────────
# BookMarkProduct
# ─────────────────────────────────────────────────────────────
@admin.register(BookMarkProduct)
class BookMarkProductAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "product__title")
    autocomplete_fields = ("user", "product")
    ordering = ("-created_at",)
