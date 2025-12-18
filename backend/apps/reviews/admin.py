from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from apps.filehub.models import MediaAttachment
from .models import Review


class ReviewMediaInline(GenericTabularInline):
    model = MediaAttachment
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 0
    fields = ("media_file", "role", "priority", "is_primary", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("media_file",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("place", "author", "rating", "is_hidden", "created_at")
    list_filter = ("rating", "is_hidden", ("created_at", admin.DateFieldListFilter))
    search_fields = ("id", "place__name", "author__email", "text")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("place", "author")
    autocomplete_fields = ("place", "author")
    inlines = (ReviewMediaInline,)
