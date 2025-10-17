# settings.py
from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}

# --- Security ---
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is missing. Define it in .env")

DEBUG = env_bool("DEBUG", False)

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "159.198.76.102",           # server IP
    "server1.unwindafrica.com", # VPS hostname
    "unwindafrica.com",         # <-- add this
    "www.unwindafrica.com",
]

# Required for HTTPS + CSRF protection
CSRF_TRUSTED_ORIGINS = [
    "https://unwindafrica.com",     # <-- add this
    "https://server1.unwindafrica.com",
    "https://www.unwindafrica.com",
]




# If you're behind Nginx/Certbot, tell Django to trust X-Forwarded-Proto=https
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Auth redirects ---
LOGIN_URL = 'dashboard_login'
LOGIN_REDIRECT_URL = 'dashboard_home'
LOGOUT_REDIRECT_URL = 'dashboard_login'

# --- Apps ---
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'Web', 'dashboard', 'widget_tweaks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ok as fallback; Nginx will serve static
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'Web' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- Database ---
# Prefer DATABASE_URL in production; falls back to explicit PG vars; DEBUG->sqlite3 for convenience
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=False  # local Postgres on same VPS, no SSL needed
        )
    }
elif DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv("DB_NAME", "unwind_prod"),
            'USER': os.getenv("DB_USER", "unwind_user"),
            'PASSWORD': os.getenv("DB_PASS", ""),
            'HOST': os.getenv("DB_HOST", "127.0.0.1"),
            'PORT': os.getenv("DB_PORT", "5432"),
            'CONN_MAX_AGE': 600,
        }
    }

# --- Password validators ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Internationalization ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# --- Static & Media ---
# Match Nginx (we'll serve /static and /media from /srv/unwindafrica/*)
STATIC_URL = '/static/'
STATIC_ROOT = os.getenv('STATIC_ROOT')  # Nginx location /static/ -> /srv/unwindafrica/static

local_static = BASE_DIR / "static"
STATICFILES_DIRS = [local_static] if local_static.exists() else []

MEDIA_URL = '/media/'
MEDIA_ROOT = os.getenv('MEDIA_ROOT')    # Nginx location /media/ -> /srv/unwindafrica/media

# WhiteNoise (kept as fallback; safe with Nginx in front)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Extra Security (enable once HTTPS is ready) ---
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
    SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", True)
