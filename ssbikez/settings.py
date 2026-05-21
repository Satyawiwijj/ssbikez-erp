"""
Django settings for ssbikez project.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# SECURITY — move all secrets to environment variables in production
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-=4zkbi0kwlm+(+@y18-0)%#t(f^=_xtg5hl-45y$)$qyx4$pb@'
)

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

_hosts_env   = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in _hosts_env.split(',') if h.strip()]

# Security headers
X_FRAME_OPTIONS          = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
CSRF_COOKIE_SECURE       = not DEBUG   # True in production (HTTPS), False in dev
SESSION_COOKIE_SECURE    = not DEBUG   # same

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # local apps
    'accounts',
    'customers',
    'customer_vehicles',
    'sales',
    'billing',
    'rto',
    'service',
    'spares',
    'vas',
]

AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ssbikez.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'ssbikez.wsgi.application'


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N      = True
USE_TZ        = True


# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------

STATIC_URL  = 'static/'
MEDIA_URL   = '/media/'
MEDIA_ROOT  = BASE_DIR / 'media'


# ---------------------------------------------------------------------------
# Sessions & messages
# ---------------------------------------------------------------------------

SESSION_COOKIE_AGE           = 28800   # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'


# ---------------------------------------------------------------------------
# Email — console backend for development; swap in production
# ---------------------------------------------------------------------------

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# ---------------------------------------------------------------------------
# Auth redirects
# ---------------------------------------------------------------------------

LOGIN_URL          = '/accounts/login/'
LOGIN_REDIRECT_URL = '/accounts/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'
