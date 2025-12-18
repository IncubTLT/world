from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.translation import gettext_lazy as _

from .models import MediaAttachment, MediaFile, MediaFileVariant


class MediaVariantInline(admin.TabularInline):
    model = MediaFileVariant
    extra = 0
    fields = ("kind", "key", "width", "height", "size_bytes", "content_type", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("kind",)


class MediaAttachmentInline(admin.TabularInline):
    model = MediaAttachment
    extra = 0
    fields = ("content_type", "object_id", "role", "priority", "is_primary", "created_at")
    readonly_fields = ("created_at",)
    raw_id_fields = ("content_type",)
    autocomplete_fields = ("media_file",)
    show_change_link = True


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "file_type",
        "owner",
        "visibility",
        "status",
        "size_bytes",
        "created_at",
    )
    list_filter = (
        "file_type",
        "visibility",
        "status",
        ("created_at", admin.DateFieldListFilter),
        "owner",
    )
    search_fields = ("id", "key", "original_name", "owner__email")
    readonly_fields = ("created_at", "updated_at", "checksum")
    autocomplete_fields = ("owner",)
    inlines = (MediaVariantInline, MediaAttachmentInline)
    ordering = ("-created_at",)


@admin.register(MediaFileVariant)
class MediaFileVariantAdmin(admin.ModelAdmin):
    list_display = ("media_file", "kind", "key", "width", "height", "size_bytes", "created_at")
    list_filter = ("kind",)
    search_fields = ("key", "media_file__id")
    autocomplete_fields = ("media_file",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


class MediaAttachmentGenericInline(GenericTabularInline):
    model = MediaAttachment
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 0
    fields = ("media_file", "role", "priority", "is_primary", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("media_file",)
    verbose_name = _("Медиа")
    verbose_name_plural = _("Медиа")


@admin.register(MediaAttachment)
class MediaAttachmentAdmin(admin.ModelAdmin):
    list_display = ("media_file", "content_type", "object_id", "role", "is_primary", "priority", "created_at")
    list_filter = ("role", "is_primary", "content_type")
    search_fields = ("object_id", "media_file__id", "content_type__model")
    autocomplete_fields = ("media_file",)
    raw_id_fields = ("content_type",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
