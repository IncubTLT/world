from django.contrib import admin

from .models import Trip, TripPoint


class TripPointInline(admin.TabularInline):
    model = TripPoint
    extra = 1
    fields = ("order", "latitude", "longitude", "place", "note")


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "is_public", "is_hidden", "created_at")
    list_filter = ("is_public", "is_hidden", "created_at")
    search_fields = ("title", "short_description", "description", "owner__email")
    inlines = [TripPointInline]


@admin.register(TripPoint)
class TripPointAdmin(admin.ModelAdmin):
    list_display = ("trip", "order", "place", "latitude", "longitude")
    list_filter = ("trip",)
    search_fields = ("trip__title", "note")
