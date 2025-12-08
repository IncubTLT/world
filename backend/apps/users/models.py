from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import FileExtensionValidator
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        extra_fields.setdefault("display_name", email.split("@")[0])
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class ProfileVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    REGISTERED = "registered", "Only registered"


class Interest(models.Model):
    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=64, unique=True)

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return self.name


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)  # email is the login identifier (OTP/link per spec)
    display_name = models.CharField(max_length=150)
    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
        help_text="Stored in S3-compatible storage",
    )
    bio = models.TextField(blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    interests = models.ManyToManyField(Interest, related_name="users", blank=True)
    profile_visibility = models.CharField(
        max_length=20,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PUBLIC,
        help_text="Controls who can see profile and routes",
    )
    email_confirmed = models.BooleanField(default=False)  # toggled after OTP/link confirmation

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = [\"display_name\"]

    objects = UserManager()

    def __str__(self) -> str:  # pragma: no cover - readable admin label
        return self.display_name or self.email
