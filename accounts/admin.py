from django.contrib import admin
from .models import CustomUser, Review,UserNotification



@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    # Columns shown in the list view
    list_display = (
        "username", "decrypted_email", "decrypted_first_name",
        "decrypted_last_name", "role", "is_active", "is_staff", "date_joined",
    )
    search_fields = ("username", "email_hash", "contact_hash")  # search by hash, not ciphertext
    readonly_fields = (
        "decrypted_first_name", "decrypted_last_name", "decrypted_email",
        "decrypted_contact_number", "contact_hash", "email_hash",
        "token_created_at", "date_joined", "last_login",
    )
    fields = (
        "username", "password",
        "decrypted_first_name", "decrypted_last_name",
        "decrypted_email", "decrypted_contact_number",
        "contact_hash", "email_hash",
        "is_active", "is_staff", "is_superuser", "role",
        "is_verified", "token_created_at",
        "latitude", "longitude", "address", "description",
        "city", "pincode",
        "groups", "user_permissions",
        "date_joined", "last_login",
    )

    def decrypted_email(self, obj):
        return obj.email
    decrypted_email.short_description = "Email"

    def decrypted_first_name(self, obj):
        return obj.first_name
    decrypted_first_name.short_description = "First name"

    def decrypted_last_name(self, obj):
        return obj.last_name
    decrypted_last_name.short_description = "Last name"

    def decrypted_contact_number(self, obj):
        return obj.contact_number
    decrypted_contact_number.short_description = "Contact number"

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    # Every column shown, all at once — simple list view
    list_display = (
        "id", "rated_user", "rated_by", "rating", "comment",
        "created_at", "updated_at",
    )
    list_filter = ("rating", "created_at")
    search_fields = (
        "rated_user__username", "rated_by__username",
        "rated_user__email_hash", "rated_by__email_hash",
    )
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("rated_user", "rated_by")

    def changelist_view(self, request, extra_context=None):
        # ✅ Shows total review count above the table
        extra_context = extra_context or {}
        extra_context["total_reviews"] = self.get_queryset(request).count()
        return super().changelist_view(request, extra_context=extra_context)
