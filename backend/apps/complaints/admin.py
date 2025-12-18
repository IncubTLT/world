from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("author", "content_type", "object_id", "status", "created_at", "resolved_at")
    list_filter = ("status", "content_type", ("created_at", admin.DateFieldListFilter))
    search_fields = ("author__email", "reason", "object_id", "content_type__model")
    list_select_related = ("author", "content_type")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("author", "content_type", "object_id", "reason")}),
        (_("Статус"), {"fields": ("status", "moderator_comment", "resolved_at")}),
        (_("Служебное"), {"fields": ("snapshot", "created_at", "updated_at")}),
    )
