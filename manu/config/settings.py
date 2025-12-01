#config/settings.py

import os
from pathlib import Path
from datetime import timedelta
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_ROOT = BASE_DIR / 'staticfiles'


# Inicialización de entorno
env = environ.Env()
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(env_file)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('DJANGO_SECRET_KEY', default='unsafe-default-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DJANGO_DEBUG', default=False)

ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    "https://tudominio.com",
    "https://www.tudominio.com",
    "http://localhost:8000",
])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth', 
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'encrypted_model_fields',
    'apps.sistema_analitico',
    'apps.dian_scraper',
    'apps.fudo_scraper'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.sistema_analitico.middleware.ConsultaInteligenteCorsMiddleware'
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  
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


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': BASE_DIR / 'db.sqlite3',
#    }
#}

#DATABASES = {
#    "default": {
#        "ENGINE": "django.db.backends.postgresql",
#        "NAME": env('POSTGRES_DB'),
#        "USER": env('POSTGRES_USER'),
#        "PASSWORD": env('POSTGRES_PASSWORD'),
#        "HOST": env('POSTGRES_HOST'),
#        "PORT": env('POSTGRES_PORT'),
#    }
#}

DATABASES = {
    "default": {
        "ENGINE": env('DB_ENGINE', default='django.db.backends.postgresql'),
        "NAME": env('DB_NAME', default='manu'),
        "USER": env('DB_USER', default='postgres'),
        "PASSWORD": env('DB_PASSWORD', default='postgres'),
        "HOST": env('DB_HOST', default='127.0.0.1'),
        "PORT": env('DB_PORT', default='5432'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}



# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY', default='change-me')

DEEPSEEK_API_KEY = env('DEEPSEEK_API_KEY', default='')

DIAN_SCRAPER_HEADLESS = env.bool('DIAN_SCRAPER_HEADLESS', default=True)

REDIS_URL = env('REDIS_URL', default='redis://localhost:6380/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Configuración API DIAN
API_DIAN_ROUTE = env('API_DIAN_ROUTE', default='http://45.149.204.184:81')
TOKEN_API_DIAN_BASIC = env('TOKEN_API_DIAN_BASIC', default='78b8f740085ff4bb2cb704fe887638804125024f087259b5a81010ecb11e82e6')

# Configuración WireGuard VPN
WG_SERVER_HOST = env('WG_SERVER_HOST', default='')  # IP o hostname del servidor Linux con WireGuard
WG_SERVER_USER = env('WG_SERVER_USER', default='root')  # Usuario SSH (root o usuario con sudo)
WG_SERVER_PASSWORD = env('WG_SERVER_PASSWORD', default='')  # Password SSH (o usar clave privada)
WG_SERVER_SSH_PORT = env.int('WG_SERVER_SSH_PORT', default=22)  # Puerto SSH
WG_SSH_KEY_PATH = env('WG_SSH_KEY_PATH', default='')  # Ruta a clave SSH privada (alternativa a password)
WG_INTERFACE = env('WG_INTERFACE', default='wg0')  # Nombre de la interfaz WireGuard
WG_CONFIG_DIR = env('WG_CONFIG_DIR', default='/etc/wireguard')  # Directorio de configuración
WG_SERVER_IP = env('WG_SERVER_IP', default='10.8.0.1')  # IP del servidor en la red VPN
WG_SERVER_PORT = env.int('WG_SERVER_PORT', default=51820)  # Puerto del servidor WireGuard
WG_SERVER_PUBLIC_KEY_PATH = env('WG_SERVER_PUBLIC_KEY_PATH', default='/etc/wireguard/public.key')  # Ruta a clave pública del servidor
WG_SERVER_ENDPOINT = env('WG_SERVER_ENDPOINT', default='')  # Endpoint público (ej: servidor.com:51820)

# Configuración SSH para gestión de servicios del servidor (puede ser diferente al servidor WireGuard)
SERVER_SSH_HOST = env('SERVER_SSH_HOST', default='')  # IP o hostname del servidor VPS donde están los servicios
SERVER_SSH_USER = env('SERVER_SSH_USER', default='root')  # Usuario SSH (recomendado: usuario con sudo, también puede ser root)
SERVER_SSH_PASSWORD = env('SERVER_SSH_PASSWORD', default='')  # Password SSH (o usar clave privada)
SERVER_SSH_PORT = env.int('SERVER_SSH_PORT', default=22)  # Puerto SSH
SERVER_SSH_KEY_PATH = env('SERVER_SSH_KEY_PATH', default='')  # Ruta a clave SSH privada (alternativa a password)