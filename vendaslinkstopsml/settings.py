from datetime import timedelta
import os
from decouple import config, Csv
from pathlib import Path

# --- CONFIGURAÇÃO PARA GCP E PROXY --- 
CSRF_TRUSTED_ORIGINS = [ 
    f"https://{host}" for host in config("ALLOWED_HOSTS", default="", cast=Csv()) 
]


SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

BASE_DIR = Path(__file__).resolve().parent.parent

# --- SEGURANÇA --- 
SECRET_KEY = config('SECRET_KEY') 
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config( "ALLOWED_HOSTS", default="", cast=lambda v: [s.strip() for s in v.split(",") if s] )


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
USE_SQLITE = config("USE_SQLITE", default=False, cast=bool)

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
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': '3306',
            'OPTIONS': {
                "unix_socket": config("DB_SOCKET"), 
                "charset": "utf8mb4",
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
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')] 
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') 
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- VARIÁVEIS DE SITE CUSTOMIZADAS ---
SITE_NAME = config('SITE_NAME')
SITE_DESCRIPTION = config('SITE_DESCRIPTION')
GOOGLE_ADSENSE_ID = config('GOOGLE_ADSENSE_ID')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='webmaster@localhost')

# Paginação
PRODUTOS_POR_PAGINA = 12
ANUNCIO_A_CADA_N_PRODUTOS = 6

# Segurança para endpoint de atualização automática (Cloud Scheduler)
CRON_SECRET = config('CRON_SECRET', default='')

# --- CONFIGURAÇÃO GCP STORAGE BUCKET E MEDIA ---
if not DEBUG:
    # Produção: usar GCP Storage
    GS_PROJECT_ID = config('GS_PROJECT_ID')
    GS_BUCKET_NAME = config('GS_BUCKET_NAME')
    GS_EXPIRATION = timedelta(minutes=30)
    GS_QUERYSTRING_AUTH = True
    GS_DEFAULT_ACL = None
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') 
    SECURE_SSL_REDIRECT = True 
    # Isso força o Django a tratar as URLs como HTTPS 
    DEFAULT_FILE_STORAGE = 'vendaslinkstopsml.storage_backends.PrivateMediaStorage' 
    MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/media/' 
else: 
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

