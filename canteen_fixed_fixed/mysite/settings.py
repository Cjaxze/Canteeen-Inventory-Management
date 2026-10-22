import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Vercel sets the VERCEL environment variable, so we can tell where we are running.
ON_VERCEL = bool(os.environ.get('VERCEL'))

# On Vercel, set SECRET_KEY in Project Settings -> Environment Variables.
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Debug is ON on your computer and OFF on Vercel (unless you set DEBUG=True there).
DEBUG = os.environ.get('DEBUG', str(not ON_VERCEL)).lower() == 'true'

ALLOWED_HOSTS = ['.vercel.app', 'localhost', '127.0.0.1']
CSRF_TRUSTED_ORIGINS = ['https://*.vercel.app']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'mysite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ]},
    },
]

WSGI_APPLICATION = 'mysite.wsgi.application'

# Local: uses db.sqlite3. Vercel: set DATABASE_URL to a hosted Postgres
# (Neon, Supabase, Vercel Postgres). Vercel cannot save data to SQLite.
if os.environ.get('DATABASE_URL'):
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(os.environ['DATABASE_URL'], conn_max_age=60),
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Lets WhiteNoise serve your static folder directly, so no collectstatic step is needed.
WHITENOISE_USE_FINDERS = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = '/inventory/'
LOGOUT_REDIRECT_URL = '/staff/login/'
