from django.contrib import admin
from .models import CustomUser


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
        "latitude", "longitude", "address", "description", "rating",
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