from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import GeoCoverage, GeoCoverageBinding, PlaceType


@admin.register(PlaceType)
class PlaceTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "radius_meters_default", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "description")
    ordering = ("name",)
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("name", "code", "description")}),
        (_("Параметры"), {"fields": ("radius_meters_default", "is_active")}),
        (_("Служебное"), {"fields": ("created_at",)}),
    )


class GeoCoverageBindingInline(admin.TabularInline):
    model = GeoCoverageBinding
    extra = 0
    raw_id_fields = ("content_type", "coverage")
    fields = ("coverage", "content_type", "object_id", "created_at")
    readonly_fields = ("created_at",)
    verbose_name = _("Привязка")
    verbose_name_plural = _("Привязки")


@admin.register(GeoCoverage)
class GeoCoverageAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "place_type",
        "latitude",
        "longitude",
        "radius_meters",
        "bindings_count",
        "created_at",
    )
    list_filter = ("place_type", ("created_at", admin.DateFieldListFilter))
    search_fields = ("name", "latitude", "longitude")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [GeoCoverageBindingInline]
    fieldsets = (
        (None, {"fields": ("name", "place_type")}),
        (_("Координаты"), {"fields": ("latitude", "longitude", "radius_meters")}),
        (_("Служебное"), {"fields": ("created_at", "updated_at")}),
    )
    list_select_related = ("place_type",)

    @admin.display(description=_("Кол-во привязок"))
    def bindings_count(self, obj):
        return obj.links.count()


@admin.register(GeoCoverageBinding)
class GeoCoverageBindingAdmin(admin.ModelAdmin):
    list_display = ("coverage", "content_type", "object_id", "created_at")
    list_filter = ("content_type", ("created_at", admin.DateFieldListFilter))
    search_fields = ("object_id", "coverage__name", "content_type__model")
    raw_id_fields = ("coverage", "content_type")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
