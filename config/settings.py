"""
Django settings for the Sigma Social project.

This file is intentionally kept simple and explicit for Phase 1
(project foundation only — no social features yet).

Configuration is driven by environment variables so that the exact
same codebase can run locally (SQLite) and in production (PostgreSQL)
without any code changes — only environment differs.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths & environment loading
# ---------------------------------------------------------------------------

# BASE_DIR points to the project root (the folder containing manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from a local .env file if one exists.
# In production (Render/Railway), env vars are provided by the platform
# itself, so .env is not required there — this call is simply a no-op
# if no .env file is found.
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    """Read an environment variable as a boolean (e.g. 'True'/'False'/'1'/'0')."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_list(name: str, default: str = "") -> list[str]:
    """Read a comma-separated environment variable into a list of strings."""
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core security settings
# ---------------------------------------------------------------------------

# SECURITY WARNING: the SECRET_KEY must never be hard-coded or committed.
# It is read from the environment; there is no insecure fallback value,
# so the project will refuse to start without one being set.
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

# DEBUG must be explicitly controlled via the environment.
# Defaults to False so that a missing/misconfigured .env never
# accidentally leaves debug mode on in a real deployment.
DEBUG = env_bool("DJANGO_DEBUG", default=False)

# Comma-separated list of allowed hosts, e.g. "localhost,127.0.0.1,example.com"
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1")

# Comma-separated list of origins trusted for CSRF (must include scheme),
# e.g. "https://sigma-social.onrender.com,https://sigma-social.up.railway.app"
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", default="")

# Cloudinary (production media storage -- see MEDIA FILES section below).
# All three must be present for Cloudinary to be used; otherwise the app
# falls back to local disk storage, so local development never requires
# a Cloudinary account.
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
USE_CLOUDINARY = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)


# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local apps
    "pages",  # simple homepage app for Phase 1
    "users",  # authentication: register/login/logout for Phase 2
    "profiles",  # user profiles for Phase 3
    "posts",  # posts & feed for Phase 4
    "notifications",  # notifications for Phase 6
    "connections",  # followers/following for Phase 7
    "search",  # search & discovery for Phase 8
]

if USE_CLOUDINARY:
    # Only installed when Cloudinary credentials are actually configured,
    # so a plain local checkout never needs a Cloudinary account just to
    # run `manage.py runserver`.
    INSTALLED_APPS += ["cloudinary_storage", "cloudinary"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves static files efficiently in production and sits
    # directly after SecurityMiddleware, as recommended by its docs.
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
        # Project-level templates directory (in addition to each app's
        # own templates/ directory, which APP_DIRS below still picks up).
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "notifications.context_processors.unread_notifications_count",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Straightforward, explicit fallback logic (no clever abstractions):
#
#   - If POSTGRES_* environment variables are all present, use PostgreSQL.
#   - Otherwise, fall back to a local SQLite database file so that a new
#     developer can clone the repo and start working immediately without
#     installing/configuring PostgreSQL.

POSTGRES_VARS = (
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
)

if all(os.getenv(var) for var in POSTGRES_VARS):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ["POSTGRES_USER"],
            "PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "HOST": os.environ["POSTGRES_HOST"],
            "PORT": os.environ["POSTGRES_PORT"],
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Optional: some hosting platforms (Render, Railway) instead provide a
# single DATABASE_URL. If present, it takes priority over the individual
# POSTGRES_* variables above. This keeps the project compatible with
# either style of platform configuration without extra setup.
#
# In production this points at Supabase PostgreSQL, which requires SSL --
# ssl_require=True adds sslmode=require if the URL didn't already specify
# it. conn_max_age keeps connections alive across requests rather than
# reconnecting every time, appropriate for a persistent web service
# (as opposed to a serverless function).
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASES["default"] = dj_database_url.parse(
        DATABASE_URL, conn_max_age=600, ssl_require=not DEBUG
    )


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"

_project_static_dir = BASE_DIR / "static"
STATICFILES_DIRS = [_project_static_dir] if _project_static_dir.exists() else []

STATIC_ROOT = BASE_DIR / "staticfiles"


# ---------------------------------------------------------------------------
# Media files
# ---------------------------------------------------------------------------

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"


# ---------------------------------------------------------------------------
# Storage backends
# ---------------------------------------------------------------------------

if USE_CLOUDINARY:
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
        "API_KEY": CLOUDINARY_API_KEY,
        "API_SECRET": CLOUDINARY_API_SECRET,
    }

    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }


# ---------------------------------------------------------------------------
# Authentication, sessions & messages
# ---------------------------------------------------------------------------
# Only the framework is configured here — no login/registration views yet.
# These are Django's sensible defaults, made explicit for clarity.

AUTH_USER_MODEL = "auth.User"  # default User model for now; can be swapped later if needed

# Named URL patterns (defined in users/urls.py) rather than hard-coded paths.
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 2 weeks

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"


# ---------------------------------------------------------------------------
# Security headers & cookies (safe in both development and production)
# ---------------------------------------------------------------------------
# These don't depend on HTTPS being active, so they're set unconditionally
# rather than only inside the DEBUG-gated block below.

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
# The CSRF cookie doesn't need to be readable by JavaScript here --
# every form on the site is server-rendered with {% csrf_token %},
# there's no JS reading document.cookie to attach it to fetch/AJAX calls.
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"


# ---------------------------------------------------------------------------
# Production security hardening (only applied when DEBUG is False)
# ---------------------------------------------------------------------------
# These are safe defaults recommended by Django's deployment checklist.
# They only activate in production so local development isn't affected
# (e.g. no HTTPS redirect while running `runserver` on http://localhost).

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7  # 1 week; can be raised once confirmed working
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
