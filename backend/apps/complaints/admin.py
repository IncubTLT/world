from django.contrib import admin

from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("author", "content_object", "status", "created_at", "resolved_at")
    list_filter = ("status", "created_at")
    search_fields = ("author__email", "reason")
