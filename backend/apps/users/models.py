from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def _create_user(
        self,
        email: str,
        password: str | None,
        **extra_fields: Any,
    ) -> "User":
        if not email:
            raise ValueError(_("Требуется email."))

        email = self.normalize_email(email)
        # если display_name не передали — берём часть до @
        extra_fields.setdefault("display_name", email.split("@")[0])

        is_admin = bool(extra_fields.get("is_staff") or extra_fields.get("is_superuser"))
        user: User = self.model(email=email, **extra_fields)

        if is_admin:
            # для админов пароль обязателен
            if not password:
                raise ValueError(_("Администратор/суперпользователь должен иметь пароль."))
            user.set_password(password)
        else:
            # для обычных пользователей пароль запрещён
            if password:
                raise ValueError(_("Для обычных пользователей пароль запрещён."))
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        """
        Обычный пользователь:
        - is_staff=False, is_superuser=False
        - пароль не допускается, будет set_unusable_password().
        """
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        """
        Администратор / суперпользователь:
        - обязан иметь пароль.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Суперпользователь обязан иметь is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Суперпользователь обязан иметь is_superuser=True."))

        return self._create_user(email, password, **extra_fields)


class ProfileVisibility(models.TextChoices):
    PUBLIC = "public", _("Публичный профиль")
    REGISTERED = "registered", _("Только для зарегистрированных пользователей")


class Interest(models.Model):
    name = models.CharField(_("Название интереса"), max_length=64, unique=True)
    slug = models.SlugField(_("Слаг"), max_length=64, unique=True)

    class Meta:
        verbose_name = _("Интерес")
        verbose_name_plural = _("Интересы")

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class User(AbstractUser):
    username = None
    email = models.EmailField(_("Email"), unique=True)
    display_name = models.CharField(_("Отображаемое имя"), max_length=150)
    avatar = models.ImageField(
        _("Аватар"),
        upload_to="avatars/",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
        help_text=_("Хранится во внешнем S3-совместимом хранилище."),
    )
    bio = models.TextField(_("О себе"), blank=True)
    country = models.CharField(_("Страна"), max_length=100, blank=True)
    city = models.CharField(_("Город"), max_length=100, blank=True)
    interests = models.ManyToManyField(
        Interest,
        related_name="users",
        blank=True,
        verbose_name=_("Интересы"),
    )
    profile_visibility = models.CharField(
        _("Видимость профиля"),
        max_length=20,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PUBLIC,
        help_text=_("Определяет, кто может видеть профиль и маршруты пользователя."),
    )
    email_confirmed = models.BooleanField(
        _("Email подтверждён"),
        default=False,
        help_text=_("Отмечается после подтверждения email по коду или ссылке."),
    )

    objects: CustomUserManager = CustomUserManager()  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []  # type: ignore[assignment]

    class Meta:
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")

    def __str__(self) -> str:
        return self.display_name or self.email
