from django.contrib import admin

from .models import Place, PlaceMedia


class PlaceMediaInline(admin.TabularInline):
    model = PlaceMedia
    extra = 1


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "place_type", "country", "region", "is_active", "created_at")
    list_filter = ("place_type", "country", "region", "is_active")
    search_fields = ("name", "description", "country", "region", "city")
    inlines = [PlaceMediaInline]


@admin.register(PlaceMedia)
class PlaceMediaAdmin(admin.ModelAdmin):
    list_display = ("place", "media_type", "order", "uploaded_at")
    list_filter = ("media_type",)
