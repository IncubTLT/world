from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe

from .models import (GptModels, Proxy, TextTransactions, UploadedScanImage,
                     UserGptModels, UserPrompt)

User = get_user_model()


@admin.register(TextTransactions)
class TextTransactionsAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'consumer', 'model', 'question_tokens', 'answer_tokens')
    search_fields = ('user__username',)
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
    pass


@admin.register(GptModels)
class GptModelsAdmin(admin.ModelAdmin):
    pass


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


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    pass


@admin.register(UploadedScanImage)
class UploadedScanImageAdmin(admin.ModelAdmin):
    pass
