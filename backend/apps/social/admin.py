from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Activity, Follow


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "target", "created_at")
    list_filter = (("created_at", admin.DateFieldListFilter),)
    search_fields = ("follower__email", "target__email")
    autocomplete_fields = ("follower", "target")
    ordering = ("-created_at",)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("actor", "verb", "target_type", "object_id", "is_recommended", "created_at")
    list_filter = ("verb", "is_recommended", ("created_at", admin.DateFieldListFilter), "content_type")
    search_fields = ("actor__email", "object_id", "content_type__model")
    autocomplete_fields = ("actor",)
    raw_id_fields = ("content_type",)
    ordering = ("-created_at",)

    @admin.display(description=_("Тип объекта"))
    def target_type(self, obj: Activity):
        return obj.content_type.model if obj.content_type_id else "-"
