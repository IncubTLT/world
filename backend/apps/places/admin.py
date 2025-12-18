from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.translation import gettext_lazy as _

from apps.filehub.models import MediaAttachment
from apps.geohub.models import GeoCoverageBinding
from .models import Place


class GeoCoverageBindingInline(GenericTabularInline):
    model = GeoCoverageBinding
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 0
    fields = ("coverage", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("coverage",)
    verbose_name = _("Точка покрытия")
    verbose_name_plural = _("Точки покрытия")


class PlaceMediaInline(GenericTabularInline):
    model = MediaAttachment
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 0
    fields = ("media_file", "role", "priority", "is_primary", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("media_file",)
    verbose_name = _("Медиа")
    verbose_name_plural = _("Медиа")


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "place_type",
        "country",
        "region",
        "city",
        "created_by",
        "is_active",
        "created_at",
    )
    list_filter = (
        "place_type",
        "country",
        "region",
        "city",
        "is_active",
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = ("id", "name", "description", "country", "region", "city", "created_by__email")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("place_type", "created_by")
    list_select_related = ("place_type", "created_by")
    inlines = (GeoCoverageBindingInline, PlaceMediaInline)
    fieldsets = (
        (None, {"fields": ("name", "description", "place_type", "is_active")}),
        (_("Расположение"), {"fields": ("country", "region", "city")}),
        (_("Служебное"), {"fields": ("created_by", "created_at", "updated_at")}),
    )
