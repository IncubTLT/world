from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.translation import gettext_lazy as _
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from apps.geohub.models import GeoCoverageBinding
from .models import Trip, TripPoint


class TripPointCoverageInline(GenericTabularInline):
    model = GeoCoverageBinding
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 0
    fields = ("coverage", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("coverage",)
    verbose_name = _("Точка покрытия")
    verbose_name_plural = _("Точки покрытия")


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "is_public", "is_hidden", "source_trip", "created_at")
    list_filter = (
        "is_public",
        "is_hidden",
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = ("id", "title", "short_description", "description", "owner__email")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("owner", "source_trip")
    list_select_related = ("owner", "source_trip")
    fieldsets = (
        (None, {"fields": ("title", "owner")}),
        (_("Описание"), {"fields": ("short_description", "description")}),
        (_("Публикация"), {"fields": ("is_public", "is_hidden", "source_trip")}),
        (_("Служебное"), {"fields": ("created_at", "updated_at")}),
    )


@admin.register(TripPoint)
class TripPointAdmin(TreeAdmin):
    form = movenodeform_factory(TripPoint)
    list_display = ("trip", "place", "note", "path", "depth")
    list_filter = ("trip", "place")
    search_fields = ("trip__title", "note", "place__name")
    list_select_related = ("trip", "place")
    inlines = (TripPointCoverageInline,)
    ordering = ("path",)
