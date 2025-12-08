from django.contrib import admin

from .models import Review, ReviewMedia


class ReviewMediaInline(admin.TabularInline):
    model = ReviewMedia
    extra = 1
    max_num = 3


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("place", "author", "rating", "is_hidden", "created_at")
    list_filter = ("rating", "is_hidden", "created_at")
    search_fields = ("place__name", "author__email", "text")
    inlines = [ReviewMediaInline]


@admin.register(ReviewMedia)
class ReviewMediaAdmin(admin.ModelAdmin):
    list_display = ("review", "uploaded_at")
