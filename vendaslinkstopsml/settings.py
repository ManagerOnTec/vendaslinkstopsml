from datetime import timedelta
import os
import logging
from decouple import config, Csv
from pathlib import Path

# Configurar logging básico para debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SEGURANÇA --- 
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production-abc123xyz789') 
DEBUG = config('DEBUG', default=True, cast=bool)

# --- CONFIGURAÇÃO PARA GCP E PROXY --- 
def _parse_hosts(hosts_str):
    """Remove portas de hostnames, deixa apenas domínio/IP"""
    return [s.split(':')[0].strip() for s in hosts_str.split(',') if s.strip()]

# Se ALLOWED_HOSTS não estiver definido, aceita wildcard em DEBUG, mas tira erro em produção
_allowed_hosts_env = config("ALLOWED_HOSTS", default="")

# ============ DEBUG LOGGING ============
logger.info("=" * 80)
logger.info("📋 ALLOWED_HOSTS CONFIGURATION DEBUG")
logger.info("=" * 80)
logger.info(f"Raw environment variable: ALLOWED_HOSTS='{_allowed_hosts_env}'")
logger.info(f"Comprimento: {len(_allowed_hosts_env)} caracteres")
if _allowed_hosts_env:
    for i, host in enumerate([s.strip() for s in _allowed_hosts_env.split(",") if s], 1):
        logger.info(f"   [{i}] '{host}'")
logger.info(f"DEBUG mode: {DEBUG}")
logger.info("=" * 80)
# ======================================

if _allowed_hosts_env:
    # Se estiver definido, usar conforme configurado
    ALLOWED_HOSTS = [s.strip() for s in _allowed_hosts_env.split(",") if s]
else:
    # Fallback: aceitar wildcard em DEBUG para desenvolvimento
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '*'] if DEBUG else []
    if not DEBUG:
        logger.error("🚨 ERRO: ALLOWED_HOSTS não definido em produção!")

CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in config("ALLOWED_HOSTS", default="", cast=Csv())
]

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

# ============================================================
# CONFIGURAÇÕES DE SESSÃO E LOGOUT TIMEOUT
# ============================================================
# Carrega timeout de logout do banco de dados (via EscalonamentoConfig)
# Fallback: 30 minutos se não conseguir carregar do BD

try:
    from produtos.config_escalonamento import SESSION_COOKIE_AGE
    # SESSION_COOKIE_AGE já está em segundos
except ImportError:
    # Se não conseguir importar, usa default de 30 minutos
    SESSION_COOKIE_AGE = 30 * 60  # 30 minutos em segundos

# Outras configurações de session
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS em produção
SESSION_COOKIE_HTTPONLY = True  # Proteger contra XSS
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Logout ao fechar navegador


