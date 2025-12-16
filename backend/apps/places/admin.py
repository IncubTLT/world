from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "place_type", "country", "region", "is_active", "created_at")
    list_filter = ("place_type", "country", "region", "is_active")
    search_fields = ("name", "description", "country", "region", "city")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("place_type",)
    fieldsets = (
        (None, {"fields": ("name", "description", "place_type", "is_active")}),
        (_("Расположение"), {"fields": ("country", "region", "city")}),
        (_("Служебное"), {"fields": ("created_at", "updated_at")}),
    )
