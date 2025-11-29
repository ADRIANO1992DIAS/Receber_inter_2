
import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / "config" / "inter" / ".env")


def env(name: str, default=None, required: bool = False):
    value = os.getenv(name, default)
    if required and (value is None or str(value).strip() == ""):
        raise ImproperlyConfigured(f"Required environment variable missing: {name}")
    return value


SECRET_KEY = env("SECRET_KEY", required=True)
DEBUG = str(env("DEBUG", "0")).lower() in {"1", "true", "yes"}

_raw_hosts = env("ALLOWED_HOSTS", "")
if not _raw_hosts:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be configured via environment variable.")
ALLOWED_HOSTS = [host.strip() for host in _raw_hosts.split(",") if host.strip()]

CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in env("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]
FERNET_KEYS = [k.strip() for k in env("FERNET_KEYS", required=True).split(",") if k.strip()]
if not FERNET_KEYS:
    raise ImproperlyConfigured("FERNET_KEYS must be configured (comma-separated) for encryption.")

PRIVATE_STORAGE_ROOT = BASE_DIR / "private"
PRIVATE_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "billing.apps.BillingConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
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
            "builtins": ["billing.templatetags.formatters"],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

BANCO = str(env("BANCO", "1")).strip()
USE_POSTGRES = BANCO not in {"0", "false", "False"}

if USE_POSTGRES:
    DB_NAME = env("DB_NAME", "receber_inter")
    DB_USER = env("DB_USER", "receber_user")
    DB_PASSWORD = env("DB_PASSWORD", "receber_pass")
    DB_HOST = env("DB_HOST", "db")
    DB_PORT = env("DB_PORT", "5432")

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Fortaleza"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/protected-media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "/clientes/"
LOGIN_URL = "login"

# Security hardening (overridable via env for dev)
SECURE_SSL_REDIRECT = str(env("SECURE_SSL_REDIRECT", "1")).lower() in {"1", "true", "yes"}
SESSION_COOKIE_SECURE = str(env("SESSION_COOKIE_SECURE", "1")).lower() in {"1", "true", "yes"}
CSRF_COOKIE_SECURE = str(env("CSRF_COOKIE_SECURE", "1")).lower() in {"1", "true", "yes"}
SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_PRELOAD = str(env("SECURE_HSTS_PRELOAD", "1")).lower() in {"1", "true", "yes"}
SECURE_HSTS_INCLUDE_SUBDOMAINS = str(env("SECURE_HSTS_INCLUDE_SUBDOMAINS", "1")).lower() in {"1", "true", "yes"}
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin"
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_PRELOAD = False
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_PROXY_SSL_HEADER = None

FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
