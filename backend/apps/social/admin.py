from django.contrib import admin

from .models import Activity, Follow


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "target", "created_at")
    search_fields = ("follower__email", "target__email")


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("actor", "verb", "created_at", "target")
    list_filter = ("verb", "created_at")
    search_fields = ("actor__email",)
