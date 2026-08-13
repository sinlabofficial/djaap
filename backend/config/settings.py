from datetime import timedelta
from importlib.util import find_spec
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from config.config import (
    DEV_SECRET_KEY,
    EXAMPLE_SECRET_KEY,
    config,
    csv,
    database_from_url,
)

BASE_DIR = Path(__file__).resolve().parent.parent

config.load()

SECRET_KEY = config.SECRET_KEY
DEBUG = config.DEBUG
DJANGO_ENV = config.DJANGO_ENV
REALTIME_ENABLED = config.REALTIME_ENABLED
CHANNEL_LAYER_BACKEND = config.CHANNEL_LAYER_BACKEND
CHANNEL_LAYER_REDIS_URL = config.CHANNEL_LAYER_REDIS_URL
PLATFORM_RUNTIME_RETENTION_DAYS = config.PLATFORM_RUNTIME_RETENTION_DAYS
TASKS_BACKEND = config.TASKS_BACKEND
TASKS_WEBHOOK_BACKEND = config.TASKS_WEBHOOK_BACKEND or TASKS_BACKEND
PERIODIC_SCHEDULER_ENABLED = config.PERIODIC_SCHEDULER_ENABLED
ALLOWED_HOSTS = csv(config.ALLOWED_HOSTS)

if not DEBUG and (
    not SECRET_KEY or SECRET_KEY in (DEV_SECRET_KEY, EXAMPLE_SECRET_KEY)
):
    raise ImproperlyConfigured("SECRET_KEY must be set to a secure value in production.")

if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be set when DEBUG=False.")

if not DEBUG and not config.DATABASE_URL:
    raise ImproperlyConfigured("DATABASE_URL must be set when DEBUG=False.")

if not DEBUG:
    production_database = database_from_url(
        config.DATABASE_URL,
        base_dir=BASE_DIR,
        conn_max_age=config.DATABASE_CONN_MAX_AGE,
        ssl_require=config.DATABASE_SSL_REQUIRE,
    )
    if production_database.get("ENGINE") != "django.db.backends.postgresql":
        raise ImproperlyConfigured(
            "DATABASE_URL must point to PostgreSQL when DEBUG=False."
        )

if not DEBUG and any(
    backend.endswith("ImmediateBackend")
    for backend in (TASKS_BACKEND, TASKS_WEBHOOK_BACKEND)
):
    raise ImproperlyConfigured(
        "TASKS_BACKEND must name a production worker backend when DEBUG=False. "
        "ImmediateBackend is only supported for development and test."
    )

if REALTIME_ENABLED and find_spec("channels") is None:
    raise ImproperlyConfigured(
        "REALTIME_ENABLED=True requires the optional Channels dependency."
    )
if (
    not DEBUG
    and REALTIME_ENABLED
    and CHANNEL_LAYER_BACKEND.endswith("InMemoryChannelLayer")
):
    raise ImproperlyConfigured(
        "CHANNEL_LAYER_BACKEND must be a shared production backend when "
        "REALTIME_ENABLED=True and DEBUG=False."
    )

# Custom User Model
# IMPORTANT: This MUST be set before the first migration.
# Django uses this to determine which model to use for authentication.
AUTH_USER_MODEL = "core.User"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_alive",
    "safedelete",
    "auditlog",
    "impersonate",
    "apps.core",
    "apps.platform_runtime",
    "apps.example",
    "apps.dashboard",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    "impersonate.middleware.ImpersonateMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates", BASE_DIR.parent / "frontend"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.organization",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

TASKS = {
    "default": {
        "BACKEND": TASKS_BACKEND,
    },
    "webhook": {
        "BACKEND": TASKS_WEBHOOK_BACKEND,
    },
}

if REALTIME_ENABLED:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": CHANNEL_LAYER_BACKEND,
            **(
                {"CONFIG": {"hosts": [CHANNEL_LAYER_REDIS_URL]}}
                if CHANNEL_LAYER_REDIS_URL
                else {}
            ),
        }
    }

DATABASES = {
    "default": database_from_url(
        config.DATABASE_URL,
        base_dir=BASE_DIR,
        conn_max_age=config.DATABASE_CONN_MAX_AGE,
        ssl_require=config.DATABASE_SSL_REQUIRE,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STATICFILES_DIRS = [
    BASE_DIR.parent / "dist",
    BASE_DIR.parent / "frontend" / "static",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Security Settings
if not DEBUG:
    SECURE_SSL_REDIRECT = config.SECURE_SSL_REDIRECT
    SECURE_HSTS_SECONDS = config.SECURE_HSTS_SECONDS
    SECURE_HSTS_PRELOAD = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_HTTPONLY = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CORS Settings
CORS_ALLOWED_ORIGINS = csv(config.CORS_ALLOWED_ORIGINS)
CSRF_TRUSTED_ORIGINS = csv(config.CSRF_TRUSTED_ORIGINS)

# REST Framework Settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
}

# Spectacular Settings for API Docs
SPECTACULAR_SETTINGS = {
    "TITLE": "djaapp API",
    "DESCRIPTION": "Optional integration API for the djaapp webapp",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# The integration API is optional. The server-rendered webapp must boot without
# the API extra installed.
API_ENABLED = all(
    find_spec(module)
    for module in ("rest_framework", "rest_framework_simplejwt", "drf_spectacular")
)
if API_ENABLED:
    INSTALLED_APPS.extend(
        [
            "rest_framework",
            "rest_framework_simplejwt",
            "rest_framework_simplejwt.token_blacklist",
            "drf_spectacular",
            "apps.api",
        ]
    )

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    "apps.core.backends.MultiIdentifierAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Impersonate Settings
IMPERSONATE = {
    "REDIRECT_URL": "/admin/",
    "PAGINATE_COUNT": 20,
    "REQUIRE_SUPERUSER": False,
    "REQUIRE_STAFF": True,
    "MAX_DURATION": 3600,
    "DISABLE_LOGGING": False,
}
