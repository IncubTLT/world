from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

User = get_user_model()


class RequestCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(
        help_text=_("Email, на который нужно отправить код входа."),
    )


class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text=_("Email, который использовался при запросе кода."))
    code = serializers.CharField(
        max_length=6,
        help_text=_("Одноразовый код, отправленный на email."),
    )


class UserSerializer(serializers.ModelSerializer):
    """
    Публичное представление пользователя для API.
    Без чувствительных полей, только то, что можно показывать наружу.
    """

    class Meta:
        model = User
        fields = ("id", "email", "display_name")
        read_only_fields = fields
