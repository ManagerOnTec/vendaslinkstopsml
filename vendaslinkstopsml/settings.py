from datetime import timedelta
import os
from decouple import config, Csv
from pathlib import Path

# --- SEGURANÇA --- 
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production-abc123xyz789') 
DEBUG = config('DEBUG', default=True, cast=bool)

# --- CONFIGURAÇÃO PARA GCP E PROXY --- 
def _parse_hosts(hosts_str):
    """Remove portas de hostnames, deixa apenas domínio/IP"""
    return [s.split(':')[0].strip() for s in hosts_str.split(',') if s.strip()]

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", 
    default="", 
    cast=lambda v: [s.strip() for s in v.split(",") if s]
)

CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in config("ALLOWED_HOSTS", default="", cast=Csv())
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

BASE_DIR = Path(__file__).resolve().parent.parent




# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
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
# Usa SQLite por padrão (dev), MySQL apenas em produção com USE_SQLITE=False
USE_SQLITE = config("USE_SQLITE", default=True, cast=bool)

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 20,  # 20 segundos de timeout para operações
            }
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='vendaslinkstopsml'),
            'USER': config('DB_USER', default='root'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': '3306',
            'OPTIONS': {
                "unix_socket": config("DB_SOCKET", default=""), 
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
SITE_NAME = config('SITE_NAME', default='Vendas Links Top SML')
SITE_DESCRIPTION = config('SITE_DESCRIPTION', default='Encontre os melhores links de vendas para seus produtos favoritos.')
GOOGLE_ADSENSE_ID = config('GOOGLE_ADSENSE_ID', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='webmaster@localhost')

# Paginação
PRODUTOS_POR_PAGINA = 12
ANUNCIO_A_CADA_N_PRODUTOS = 6

# Segurança para endpoint de atualização automática (Cloud Scheduler)
CRON_SECRET = config('CRON_SECRET', default='')

# --- CONFIGURAÇÃO GCP STORAGE BUCKET E MEDIA ---
if not DEBUG: 
    INSTALLED_APPS.append('storages')
    # Produção: usar GCP Storage
    GS_PROJECT_ID = config('GS_PROJECT_ID', default='')
    GS_BUCKET_NAME = config('GS_BUCKET_NAME', default='')
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

