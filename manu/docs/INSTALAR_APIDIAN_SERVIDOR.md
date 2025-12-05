# Instalación de APIDIAN en el Servidor

## Pasos para instalar y configurar APIDIAN

### 1. Instalar dependencia pymysql

```bash
cd /home/victus/projects/CORE/manu
source env/bin/activate
pip install pymysql>=1.1.0
```

### 2. Crear migraciones

```bash
python manage.py makemigrations apidian
```

### 3. Aplicar migraciones

```bash
python manage.py migrate
```

### 4. Configurar variables de entorno

Editar el archivo `.env`:

```bash
nano .env
```

Agregar:

```env
# Configuración Base de Datos APIDIAN (MariaDB)
APIDIAN_DB_HOST=45.149.204.184
APIDIAN_DB_PORT=3307
APIDIAN_DB_USER=apidian
APIDIAN_DB_PASSWORD=tu_password_aqui
APIDIAN_DB_NAME=apidian
```

### 5. Reiniciar servicios

```bash
# Reiniciar Django (si está con PM2)
pm2 restart manu
# o el nombre de tu proceso Django
```

## Verificación

Probar el endpoint:

```bash
curl -X GET http://localhost:8001/api/apidian/events/ \
  -H "Authorization: Bearer tu_token"
```

## Notas

- Los modelos de APIDIAN tienen `managed=False`, por lo que no se crearán tablas en la BD de MANU
- La conexión a MariaDB de APIDIAN se hace directamente usando `pymysql`
- Los endpoints requieren autenticación (IsAuthenticated por defecto)

