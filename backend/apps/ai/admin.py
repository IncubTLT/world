from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import (GptModels, Proxy, TextTransactions, UploadedScanImage,
                     UserGptModels, UserPrompt)

User = get_user_model()


@admin.register(TextTransactions)
class TextTransactionsAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'consumer', 'model', 'question_tokens', 'answer_tokens')
    search_fields = ('user__email', 'consumer', 'model')
    list_filter = (
        'model',
        'consumer',
        ('created_at', admin.DateFieldListFilter),
        'user',
    )
    readonly_fields = ('preview',)

    def preview(self, obj):
        return mark_safe(f'<img src="{obj.image.url}" style="max-height: 400px;">')


@admin.register(UserPrompt)
class UserPromptAdmin(admin.ModelAdmin):
    list_display = ("title", "consumer", "is_default")
    list_filter = ("consumer", "is_default")
    search_fields = ("title", "prompt_text")
    ordering = ("title",)


@admin.register(GptModels)
class GptModelsAdmin(admin.ModelAdmin):
    list_display = ("public_name", "provider_cdk", "consumer", "is_default", "is_free", "proxy")
    list_filter = ("provider_cdk", "consumer", "is_default", "is_free")
    search_fields = ("public_name", "title", "proxy__title")
    autocomplete_fields = ("proxy",)
    ordering = ("public_name",)


class GptModelsInline(admin.StackedInline):
    model = GptModels.approved_users.through
    extra = 0


@admin.register(UserGptModels)
class UserGptModelsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Основные данные', {'fields': ('user',)}),
        ('ИИ', {'fields': ('active_model', 'active_prompt')}),
        ('Время начала окна', {'fields': ('time_start',)}),
    )
    inlines = (GptModelsInline,)
    list_display = ("user", "active_model", "active_prompt", "time_start")
    search_fields = ("user__email",)
    autocomplete_fields = ("user", "active_model", "active_prompt")
    ordering = ("-time_start",)


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = ("title", "proxy_url")
    search_fields = ("title", "proxy_url", "proxy_http", "proxy_socks")
    ordering = ("title",)


@admin.register(UploadedScanImage)
class UploadedScanImageAdmin(admin.ModelAdmin):
    list_display = ("user", "chat_id", "image")
    search_fields = ("user__email", "chat_id")
    autocomplete_fields = ("user",)
