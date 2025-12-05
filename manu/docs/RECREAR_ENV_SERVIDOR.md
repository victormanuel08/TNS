# Comandos para Recrear .env en UTF-8 en el Servidor

## Opción 1: Comandos Manuales (Recomendado)

```bash
# 1. Ir al directorio del proyecto
cd /ruta/a/manu

# 2. Hacer backup del .env actual
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 3. Borrar el .env actual
rm .env

# 4. Crear nuevo .env en UTF-8
touch .env
echo "# Archivo de configuración de entorno" > .env
echo "# Codificación: UTF-8" >> .env
echo "" >> .env

# 5. Verificar codificación
file -bi .env
```

## Opción 2: Usar el Script

```bash
# Dar permisos de ejecución
chmod +x scripts/recrear_env.sh

# Ejecutar el script
./scripts/recrear_env.sh
```

## Opción 3: Comando Único

```bash
cd /ruta/a/manu && \
cp .env .env.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true && \
rm -f .env && \
echo "# Archivo de configuración de entorno" > .env && \
echo "# Codificación: UTF-8" >> .env && \
echo "" >> .env && \
file -bi .env
```

## Después de Recrear

1. **Editar el .env** con tus variables:
```bash
nano .env
# o
vi .env
```

2. **Agregar las variables necesarias**, por ejemplo:
```env
# Django
DJANGO_SECRET_KEY=tu_secret_key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=api.eddeso.com,localhost

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=manu
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=127.0.0.1
DB_PORT=5432

# API DIAN
API_DIAN_ROUTE=http://45.149.204.184:81
TOKEN_API_DIAN_BASIC=tu_token

# APIDIAN Database
APIDIAN_DB_HOST=45.149.204.184
APIDIAN_DB_PORT=3307
APIDIAN_DB_USER=apidian
APIDIAN_DB_PASSWORD=tu_password_apidian
APIDIAN_DB_NAME=apidian

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_email
EMAIL_HOST_PASSWORD=tu_password_email
DEFAULT_FROM_EMAIL=noreply@eddeso.com

# Redis
REDIS_URL=redis://localhost:6379/0

# S3
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_STORAGE_BUCKET_NAME=tu_bucket
AWS_S3_ENDPOINT_URL=https://usc1.contabostorage.com
```

3. **Verificar que el archivo está en UTF-8**:
```bash
file -bi .env
# Debe mostrar: text/plain; charset=utf-8
```

4. **Verificar que no tiene BOM** (opcional):
```bash
hexdump -C .env | head -1
# No debe empezar con: ef bb bf
```

## Notas

- El backup se guarda con timestamp para no perder datos
- El nuevo .env se crea en UTF-8 sin BOM
- Recuerda agregar todas las variables necesarias
- Verifica los permisos del archivo (debe ser legible por el usuario de Django)

