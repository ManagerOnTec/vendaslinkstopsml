"""
Django settings for vendaslinkstopsml project.
Configurado para deploy no GCP Cloud Run com variáveis de ambiente.
"""

import os
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Inicializar django-environ
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    GOOGLE_ADSENSE_ID=(str, ''),
    SITE_NAME=(str, 'Vendas Links Tops ML'),
    SITE_DESCRIPTION=(str, 'As melhores ofertas do Mercado Livre'),
    GS_BUCKET_NAME=(str, ''),
    GS_PROJECT_ID=(str, ''),
)

# Ler ficheiro .env se existir (desenvolvimento local)
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(str(env_file), overwrite=True)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
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

# Database
DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')
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

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise para servir static files em produção
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Variáveis customizadas do site
SITE_NAME = env('SITE_NAME')
SITE_DESCRIPTION = env('SITE_DESCRIPTION')
GOOGLE_ADSENSE_ID = env('GOOGLE_ADSENSE_ID')

# Paginação
PRODUTOS_POR_PAGINA = 12
ANUNCIO_A_CADA_N_PRODUTOS = 6

# Segurança para endpoint de atualização automática (Cloud Scheduler)
# Se vazio, o endpoint aceita qualquer requisição (não recomendado em produção)
CRON_SECRET = env('CRON_SECRET', default='')

# CSRF Trusted Origins (necessário para proxies)
CSRF_TRUSTED_ORIGINS = [
    'https://*.manus.computer',
    'https://*.us2.manus.computer',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Segurança para produção
if not DEBUG:
    SECURE_SSL_REDIRECT = False  # Cloud Run já faz SSL termination
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_TRUSTED_ORIGINS = [f'https://{host}' for host in ALLOWED_HOSTS if host not in ('localhost', '127.0.0.1', '0.0.0.0')]
