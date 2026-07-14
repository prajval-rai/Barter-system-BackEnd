import os
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account
import dj_database_url
from datetime import timedelta
import json
import firebase_admin
from firebase_admin import credentials


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-dev-key")
DEBUG = os.getenv("DEBUG", "False") == "True"

# ✅ Firebase init with guard
firebase_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

if not firebase_admin._apps and firebase_json:
    firebase_credentials = json.loads(firebase_json)
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred)

# --------------------
# SECURITY
# --------------------
CLOUD_FILE_NAME = os.getenv("cloud_file_name") 
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
ALLOWED_HOSTS = ["*"]

# --------------------
# GOOGLE CLOUD STORAGE
# --------------------
GS_BUCKET_NAME = os.getenv("NEW_BUCKET_NAME")
GS_PROJECT_ID = os.getenv("NEW_PROJECT_ID")

CLOUD_FILE_NAME = os.getenv("NEW_CLOUD_FILE_NAME")
GS_CREDENTIALS = None

if GOOGLE_SERVICE_ACCOUNT_JSON:
    GS_CREDENTIALS = service_account.Credentials.from_service_account_info(
        json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    )
elif CLOUD_FILE_NAME:
    GS_CREDENTIALS = service_account.Credentials.from_service_account_file(
        os.path.join(BASE_DIR, CLOUD_FILE_NAME)
    )

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": GS_BUCKET_NAME,
            "project_id": GS_PROJECT_ID,
            "credentials": GS_CREDENTIALS,
            "location": "uploads",
            "querystring_auth": False,        # keep — plain public URLs, not signed
            "default_acl": None,              # UBLA bucket: no per-object ACL allowed
            "object_parameters": {
                "cache_control": "public, max-age=31536000, immutable",
            },
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# --------------------
# APPS
# --------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "channels",
    "daphne",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "storages",
    "accounts",
    "products",
    "barter",
    "chat",
    "core",
    "scan_product",
    "rest_framework_simplejwt.token_blacklist"
]



ASGI_APPLICATION = 'config.asgi.application'


REDIS_URL = os.getenv(
    "REDIS_URL","redis-15305.crce285.us-east-1-4.ec2.cloud.redislabs.com:15305"
)


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}
FIELD_ENCRYPTION_KEY = os.getenv("FIELD_ENCRYPTION_KEY")
AUTH_USER_MODEL = "accounts.CustomUser"


# ---------------JWT Config---------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

HASH_SALT = os.getenv('HASH_SALT')


CSRF_TRUSTED_ORIGINS = list(filter(None, [
    os.getenv("CSRF_TRUSTED_ORIGINS"),
]))

CORS_ALLOWED_ORIGINS = list(filter(None, [
    os.getenv("CORS_ALLOWED_ORIGINS"),
]))

import os

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL")
DEFAULT_ADMIN = os.getenv("DEFAULT_ADMIN")

CORS_ALLOW_HEADERS = [
    "authorization",
    "content-type",
    "Access-Control-Allow-Origin",
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'config.authentication.CookieJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

CORS_ALLOW_CREDENTIALS = True
CSRF_COOKIE_HTTPONLY = False  # add this
CSRF_USE_SESSIONS = False 


# --------------------
# MIDDLEWARE
# --------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ✅ Serves /static/ files via Whitenoise
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


CSRF_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True

# --------------------
# URLS / TEMPLATES
# --------------------
ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"

# --------------------
# DATABASE
# --------------------

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True
    )
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# --------------------
# STATIC FILES
# --------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = []

# --------------------
# CORS
# --------------------
CORS_ALLOW_ALL_ORIGINS = False
