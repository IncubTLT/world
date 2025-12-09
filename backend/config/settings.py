from datetime import timedelta
import os
from pathlib import Path

import boto3
import redis
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "change-me")
if not SECRET_KEY:
    raise ImproperlyConfigured("Missing SECRET_KEY environment variable")

SALT_KEY = os.environ.get("SALT_KEY")
if not SALT_KEY:
    raise ImproperlyConfigured("Missing SALT_KEY environment variable")

CERT_PASSPHRASE = os.environ.get("CERT_PASSPHRASE")
if not CERT_PASSPHRASE:
    raise ImproperlyConfigured("Missing CERT_PASSPHRASE environment variable")

DEFAULT_SIGNATURE_ALGORITHM = "RS256"


DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', default='localhost').split(' ')
DOMAIN = os.environ.get("DOMAIN")

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    f"https://{DOMAIN}"
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "apps.users",
    "apps.filehub",
    "apps.geohub",
    "apps.places",
    "apps.trips",
    "apps.reviews",
    "apps.messaging",
    "apps.social",
    "apps.complaints",
    "apps.utils",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


def _postgres_settings():
    return {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.environ.get("POSTGRES_DB", "world"),
        "USER": os.environ.get("POSTGRES_USER", "world"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "world"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }


def _sqlite_settings():
    return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}


DATABASES = {"default": _sqlite_settings() if os.environ.get("USE_SQLITE", "0") == "1" else _postgres_settings()}

# django-dbbackup
DBBACKUP_CONNECTORS = {
    'default': {
        'CONNECTOR': 'dbbackup.db.postgresql.PgDumpBinaryConnector',
    }
}
DBBACKUP_CLEANUP_KEEP = 10

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.mail.ru"
EMAIL_PORT = 465
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER
EMAIL_ADMIN = EMAIL_HOST_USER
TEMPLATED_EMAIL_BACKEND = 'templated_email.backends.vanilla_django.TemplateBackend'
TEMPLATED_EMAIL_TEMPLATE_DIR = 'templated_email/'
TEMPLATED_EMAIL_FILE_EXTENSION = 'email'
EMAIL_TIMEOUT = 20

LANGUAGE_CODE = "ru"
LANGUAGES = [
    ("ru", "Русский"),
    ("en", "English"),
]
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_S3_DOMAIN = os.getenv('AWS_S3_DOMAIN')
AWS_S3_ENDPOINT_URL = f'https://{AWS_S3_DOMAIN}'
AWS_S3_USE_SSL = bool(int(os.getenv('AWS_S3_USE_SSL', 0)))
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME')

AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

STATIC_BUCKET_NAME = 'hal-static'
MEDIA_BUCKET_NAME = 'hal-media'
DATABASE_BUCKET_NAME = 'hal-database'

USE_S3 = bool(int(os.getenv('USE_S3', 0)))

# === Пути к директориям ===
STATICFILES_DIRS = (BASE_DIR / 'static',)
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'
BACKUP_ROOT = BASE_DIR / 'backup'

if USE_S3:
    STATIC_URL = f'{AWS_S3_ENDPOINT_URL}/{STATIC_BUCKET_NAME}/'
    MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{MEDIA_BUCKET_NAME}/'
    STORAGES = {
        'default': {
            'BACKEND': 'config.storages.MediaStorage',
        },
        'staticfiles': {
            'BACKEND': 'config.storages.StaticStorage',
        },
        'dbbackup': {
            'BACKEND': 'config.storages.DataBaseStorage',
            'OPTIONS': {
                'access_key': AWS_ACCESS_KEY_ID,
                'secret_key': AWS_SECRET_ACCESS_KEY,
                'bucket_name': DATABASE_BUCKET_NAME,
                'default_acl': 'private',
            }
        },
    }
    DBBACKUP_STORAGE_OPTIONS = STORAGES['dbbackup']['OPTIONS']
else:
    STATIC_URL = '/static/'
    MEDIA_URL = '/media/'
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
        'dbbackup': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
            'OPTIONS': {
                'location': BACKUP_ROOT,
            },
        },
    }

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

S3_CLIENT = boto3.client(
    's3',
    region_name=AWS_S3_REGION_NAME,
    use_ssl=AWS_S3_USE_SSL,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    endpoint_url=AWS_S3_ENDPOINT_URL
)


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
    },
}

SIMPLE_JWT = {
    # access-токен: живёт недолго, только для авторизации запросов
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),

    # refresh-токен: «сессия» пользователя
    # можно увеличить до 540 дней (~18 месяцев)
    "REFRESH_TOKEN_LIFETIME": timedelta(days=365),

    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Мир Странствий API",
    "DESCRIPTION": "Backend Django/DRF для проекта «Мир Странствий».",
    "VERSION": "1.0.0",
}

# REDIS
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0'
REDIS_DB = 0
REDIS_CLIENT_DATA = {
    'host': REDIS_HOST,
    'port': REDIS_PORT,
    'db': REDIS_DB,
    'password': REDIS_PASSWORD
}
pool = redis.ConnectionPool(
    max_connections=120,
    socket_timeout=5,
    socket_connect_timeout=2,
    **REDIS_CLIENT_DATA
)
REDIS_CLIENT = redis.Redis(connection_pool=pool)

# CACHE BACKEND
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

DEFENDER_REDIS_URL = REDIS_URL
DEFENDER_COOLOFF_TIME = 600
DEFENDER_LOCKOUT_URL = "/block/"
