"""
Django settings for vendaslinkstopsml project.
Configurado para deploy no GCP Cloud Run com suporte a:
- SQLite (desenvolvimento local)
- MySQL (produção com Cloud SQL)
- Google Cloud Storage para media files
- Cloud Scheduler para automação
"""

import os
from pathlib import Path
from datetime import timedelta
import environ

# --- CONFIGURAÇÃO PARA GCP E PROXY ---
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    USE_SQLITE=(bool, True),
    GOOGLE_ADSENSE_ID=(str, ''),
    SITE_NAME=(str, 'Vendas Links Tops ML'),
    SITE_DESCRIPTION=(str, 'As melhores ofertas do Mercado Livre'),
    GS_BUCKET_NAME=(str, ''),
    GS_PROJECT_ID=(str, ''),
    GS_QUERYSTRING_AUTH=(bool, True),
)

# Ler ficheiro .env se existir (desenvolvimento local)
BASE_DIR = Path(__file__).resolve().parent.parent
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(str(env_file), overwrite=True)

# Build CSRF_TRUSTED_ORIGINS dinamicamente
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in env.list('ALLOWED_HOSTS', default=[])]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# --- SEGURANÇA ---
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'storages',  # Google Cloud Storage
    'produtos',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'vendaslinkstopsml.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'produtos.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'vendaslinkstopsml.wsgi.application'

# --- BANCO DE DADOS ---
USE_SQLITE = env('USE_SQLITE')

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST'),
            'PORT': '3306',
            'OPTIONS': {
                'charset': 'utf8mb4',
                'sql_mode': 'STRICT_TRANS_TABLES',
            }
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# --- ARQUIVOS ESTÁTICOS E MÍDIA ---
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- VARIÁVEIS DE SITE CUSTOMIZADAS ---
SITE_NAME = env('SITE_NAME')
SITE_DESCRIPTION = env('SITE_DESCRIPTION')
GOOGLE_ADSENSE_ID = env('GOOGLE_ADSENSE_ID')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='webmaster@localhost')

# Paginação
PRODUTOS_POR_PAGINA = 12
ANUNCIO_A_CADA_N_PRODUTOS = 6

# Segurança para endpoint de atualização automática (Cloud Scheduler)
CRON_SECRET = env('CRON_SECRET', default='')

# --- CONFIGURAÇÃO GCP STORAGE BUCKET E MEDIA ---
if not DEBUG:
    # Produção: usar GCP Storage
    GS_PROJECT_ID = env('GS_PROJECT_ID')
    GS_BUCKET_NAME = env('GS_BUCKET_NAME')
    GS_EXPIRATION = timedelta(minutes=30)
    GS_QUERYSTRING_AUTH = env('GS_QUERYSTRING_AUTH', cast=bool, default=True)
    GS_DEFAULT_ACL = None

    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Usar GCS para arquivos de mídia
    DEFAULT_FILE_STORAGE = 'vendaslinkstopsml.storage_backends.PrivateMediaStorage'
    MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/media/'
else:
    # Desenvolvimento: usar filesystem local
    MEDIA_URL = '/media/'

# --- LOGGING ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'storages': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'produtos': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

