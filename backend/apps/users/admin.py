from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Interest, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    list_display = (
        "email",
        "display_name",
        "role",
        "is_staff",
        "is_active",
        "email_confirmed",
        "profile_visibility",
        "date_joined",
    )
    list_filter = (
        "role",
        "profile_visibility",
        "email_confirmed",
        "is_staff",
        "is_superuser",
        "is_active",
    )
    ordering = ("-date_joined",)
    search_fields = ("email", "display_name", "country", "city", "id")
    autocomplete_fields = ("interests",)

    fieldsets = (
        (None, {"fields": ("email", "password", "display_name", "avatar", "bio")}),
        ("Location", {"fields": ("country", "city")}),
        ("Visibility", {"fields": ("profile_visibility", "interests", "email_confirmed")}),
        (
            "Permissions",
            {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "display_name"),
            },
        ),
    )


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    search_fields = ("name", "slug")
    list_display = ("name", "slug")
