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
    'django_redis',  # Para cache con Redis
    'apps.sistema_analitico',
    'apps.dian_scraper',
    'apps.fudo_scraper',
    'apidian',  # App para integración con APIDIAN
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

LANGUAGE_CODE = 'es-co'  # Español Colombia

TIME_ZONE = 'America/Bogota'  # Zona horaria de Bogotá, Colombia

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
DEEPSEEK_API_URL = env('DEEPSEEK_API_URL', default='https://api.deepseek.com/v1/chat/completions')

# ==================== Precios DeepSeek API (por token, en USD) ====================
# Valores reales basados en facturación de DeepSeek (diciembre 2025)
# Estos valores se cargan desde variables de entorno para fácil ajuste
DEEPSEEK_PRICE_OUTPUT_TOKEN = env.float('DEEPSEEK_PRICE_OUTPUT_TOKEN', default=0.00000042)  # $0.42 por 1M tokens output
DEEPSEEK_PRICE_INPUT_CACHE_HIT = env.float('DEEPSEEK_PRICE_INPUT_CACHE_HIT', default=0.000000028)  # $0.028 por 1M tokens input (cache hit)
DEEPSEEK_PRICE_INPUT_CACHE_MISS = env.float('DEEPSEEK_PRICE_INPUT_CACHE_MISS', default=0.00000056)  # $0.56 por 1M tokens input (cache miss)

# Tasa de cambio COP/USD (ajustable según mercado)
TASA_CAMBIO_COP_USD = env.float('TASA_CAMBIO_COP_USD', default=4000)

# Configuración de clasificación contable con procesamiento paralelo
CLASIFICACION_MAX_FACTURAS = env.int('CLASIFICACION_MAX_FACTURAS', default=0)  # 0 = ilimitado
CLASIFICACION_MAX_ARTICULOS = env.int('CLASIFICACION_MAX_ARTICULOS', default=0)  # 0 = ilimitado
CLASIFICACION_MAX_ARTICULOS_POR_FACTURA = env.int('CLASIFICACION_MAX_ARTICULOS_POR_FACTURA', default=50)
CLASIFICACION_TIMEOUT_SEGUNDOS = env.int('CLASIFICACION_TIMEOUT_SEGUNDOS', default=90)
CLASIFICACION_MAX_TOKENS = env.int('CLASIFICACION_MAX_TOKENS', default=8000)
CLASIFICACION_TEMPERATURE = env.float('CLASIFICACION_TEMPERATURE', default=0.1)
CLASIFICACION_DEBUG = env.bool('CLASIFICACION_DEBUG', default=False)

# Procesamiento paralelo con rate limiting (configuración antigua, ver más abajo)
# NOTA: Esta configuración está duplicada más abajo con valores actualizados

# ==================== Configuración Clasificación Contable ====================
# Límites configurables (0 = ilimitado)
# Valores originales de BCE: sin límites explícitos, procesa factura por factura
CLASIFICACION_MAX_FACTURAS = env.int('CLASIFICACION_MAX_FACTURAS', default=0)  # 0 = ilimitado (BCE original: sin límite)
CLASIFICACION_MAX_ARTICULOS = env.int('CLASIFICACION_MAX_ARTICULOS', default=0)  # 0 = ilimitado (BCE original: sin límite)
CLASIFICACION_MAX_ARTICULOS_POR_FACTURA = env.int('CLASIFICACION_MAX_ARTICULOS_POR_FACTURA', default=0)  # 0 = ilimitado (BCE original: sin límite)
CLASIFICACION_TIMEOUT_SEGUNDOS = env.int('CLASIFICACION_TIMEOUT_SEGUNDOS', default=90)  # BCE original: 90 segundos
CLASIFICACION_MAX_TOKENS = env.int('CLASIFICACION_MAX_TOKENS', default=8000)  # BCE original: 8000
CLASIFICACION_TEMPERATURE = env.float('CLASIFICACION_TEMPERATURE', default=0.1)  # BCE original: 0.1
CLASIFICACION_DEBUG = env.bool('CLASIFICACION_DEBUG', default=False)  # Activar prints de debug

# ==================== Rate Limiting para DeepSeek ====================
# DeepSeek acepta hasta 60 llamadas por minuto (rate limit estándar)
# 
# Estrategia recomendada para 100 facturas:
#   - Grupo 1: Enviar 50 facturas primero (en lotes de 10) = 5 lotes
#   - Esperar 60 segundos (para resetear el contador del minuto)
#   - Grupo 2: Enviar las 50 restantes (en lotes de 10)
#   - Tiempo total estimado: ~2-3 minutos para 100 facturas
#
# Consideraciones:
#   - Cada factura toma ~20 segundos en procesarse
#   - En paralelo (lotes de 10), podemos procesar más rápido
#   - Pero debemos respetar el límite de 60 RPM para evitar errores 429
#
# Tamaño de lote: cuántas facturas se procesan en paralelo a la vez
# Recomendado: 10 (según recomendaciones de DeepSeek)
CLASIFICACION_LOTE_PARALELO = env.int('CLASIFICACION_LOTE_PARALELO', default=10)

# Máximo de facturas por minuto antes de hacer pausa
# Recomendado: 50 (para estar seguro del límite de 60 RPM, dejar margen de seguridad)
CLASIFICACION_MAX_FACTURAS_POR_MINUTO = env.int('CLASIFICACION_MAX_FACTURAS_POR_MINUTO', default=50)

# Pausa entre grupos de facturas (en segundos)
# Recomendado: 60 segundos (para resetear el contador del minuto de DeepSeek)
CLASIFICACION_PAUSA_ENTRE_GRUPOS = env.int('CLASIFICACION_PAUSA_ENTRE_GRUPOS', default=60)

DIAN_SCRAPER_HEADLESS = env.bool('DIAN_SCRAPER_HEADLESS', default=True)
# Configuración de paralelismo para scraping DIAN
DIAN_SCRAPER_DOWNLOAD_BATCH_SIZE = env.int('DIAN_SCRAPER_DOWNLOAD_BATCH_SIZE', default=10)  # Descargas simultáneas
DIAN_SCRAPER_ZIP_WORKERS = env.int('DIAN_SCRAPER_ZIP_WORKERS', default=10)  # ZIPs procesados en paralelo

REDIS_URL = env('REDIS_URL', default='redis://localhost:6380/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Bogota'  # Zona horaria de Bogotá, Colombia

# Configuración de Celery Beat (tareas programadas)
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Ejecutar procesamiento de backups programados cada hora
    # Esto permite que las empresas con hora_backup configurada se ejecuten automáticamente
    'procesar-backups-programados': {
        'task': 'sistema_analitico.procesar_backups_programados',
        'schedule': crontab(minute=0),  # Cada hora en el minuto 0 (ej: 1:00, 2:00, 3:00...)
    },
    # Explorar empresas en todos los servidores automáticamente a la 1:00 AM
    # Detecta nuevas empresas creadas en los servidores
    'explorar-empresas-todos-servidores': {
        'task': 'sistema_analitico.explorar_empresas_todos_servidores',
        'schedule': crontab(hour=1, minute=0),  # Todos los días a la 1:00 AM
    },
    # Limpiar descargas temporales expiradas diariamente a las 2:00 AM
    'limpiar-descargas-expiradas': {
        'task': 'sistema_analitico.limpiar_descargas_expiradas',
        'schedule': crontab(hour=2, minute=0),  # Todos los días a las 2:00 AM
    },
}

# ==================== Configuración de Cache ====================
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'TIMEOUT': 604800,  # 7 días por defecto (igual que BCE)
    }
}

# Configuración de Email
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@eddeso.com')
FRONTEND_URL = env('FRONTEND_URL', default='https://api.eddeso.com')
API_PUBLIC_URL = env('API_PUBLIC_URL', default='https://api.eddeso.com')  # URL pública del API para links de descarga

# Configuración API DIAN
API_DIAN_ROUTE = env('API_DIAN_ROUTE', default='http://45.149.204.184:81')
TOKEN_API_DIAN_BASIC = env('TOKEN_API_DIAN_BASIC', default='78b8f740085ff4bb2cb704fe887638804125024f087259b5a81010ecb11e82e6')

# URL del backend BCE para obtener credenciales
BCE_API_URL = env('BCE_API_URL', default='http://localhost:8000')

# Configuración Base de Datos APIDIAN (MariaDB)
APIDIAN_DB_HOST = env('APIDIAN_DB_HOST', default='45.149.204.184')
APIDIAN_DB_PORT = env.int('APIDIAN_DB_PORT', default=3307)
APIDIAN_DB_USER = env('APIDIAN_DB_USER', default='apidian')
APIDIAN_DB_PASSWORD = env('APIDIAN_DB_PASSWORD', default='Bce.2024*/')
APIDIAN_DB_NAME = env('APIDIAN_DB_NAME', default='apidian')

# Configuración Hablame (SMS y Llamadas)
HABLAME_ACCOUNT = env('HABLAME_ACCOUNT', default='')
HABLAME_APIKEY = env('HABLAME_APIKEY', default='')
HABLAME_TOKEN = env('HABLAME_TOKEN', default='')
HABLAME_SMS_URL = env('HABLAME_SMS_URL', default='https://api103.hablame.co/api/sms/v3/send/priority')
HABLAME_SMS_REPORT_URL = env('HABLAME_SMS_REPORT_URL', default='https://api103.hablame.co/api/sms/v3/report/')
HABLAME_TTS_URL = env('HABLAME_TTS_URL', default='https://api103.hablame.co/api/callblasting/v1/callblasting/tts_text')
HABLAME_TTS_STATUS_URL = env('HABLAME_TTS_STATUS_URL', default='https://api103.hablame.co/api/callblasting/v1/callblasting/status/')
HABLAME_SMS_SERVICE_CODE = env('HABLAME_SMS_SERVICE_CODE', default='890202')
HABLAME_TTS_VOICE = env('HABLAME_TTS_VOICE', default='es-US-natural-3')
HABLAME_MAX_INTENTOS = env.int('HABLAME_MAX_INTENTOS', default=3)
HABLAME_TIEMPO_ESPERA = env.int('HABLAME_TIEMPO_ESPERA', default=5)

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