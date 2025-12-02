# Seguridad de MLflow

## Problema

MLflow por defecto **NO tiene autenticación**. Cualquiera que acceda a `https://mlflow.eddeso.com` puede ver y modificar todos los experimentos y modelos.

## Soluciones de Seguridad

### Opción 1: Autenticación Básica HTTP (Nginx) - Recomendado

Agregar autenticación básica HTTP en Nginx antes de llegar a MLflow:

```bash
# Instalar herramienta para generar contraseña
sudo apt-get install apache2-utils

# Crear usuario y contraseña
sudo htpasswd -c /etc/nginx/.htpasswd_mlflow admin
# Te pedirá una contraseña, ingrésala

# Agregar más usuarios (sin -c)
sudo htpasswd /etc/nginx/.htpasswd_mlflow usuario2
```

Luego modificar la configuración de Nginx:

```bash
sudo nano /etc/nginx/sites-available/mlflow
```

Agregar en el bloque `location /` del servidor HTTPS (443):

```nginx
location / {
    # Autenticación básica
    auth_basic "MLflow - Acceso Restringido";
    auth_basic_user_file /etc/nginx/.htpasswd_mlflow;
    
    proxy_pass http://localhost:5050;
    # ... resto de configuración
}
```

### Opción 2: Restringir por IP (Solo acceso desde tu IP)

Si solo quieres acceder desde tu IP específica:

```bash
sudo nano /etc/nginx/sites-available/mlflow
```

Agregar en el bloque HTTPS:

```nginx
location / {
    # Solo permitir acceso desde tu IP (reemplaza con tu IP pública)
    allow TU_IP_PUBLICA;
    deny all;
    
    proxy_pass http://localhost:5050;
    # ... resto de configuración
}
```

### Opción 3: Autenticación Nativa de MLflow (Más Complejo)

MLflow soporta autenticación nativa, pero requiere configuración adicional. Ver documentación oficial.

### Opción 4: Túnel SSH (Para acceso temporal)

Si solo necesitas acceso ocasional, usar túnel SSH en lugar de exponer públicamente:

```bash
# Desde tu máquina local
ssh -L 5050:localhost:5050 victus@TU_IP_SERVIDOR
```

Luego acceder a `http://localhost:5050` localmente.

## Recomendación

**Opción 1 (Autenticación Básica HTTP)** es la más simple y efectiva para producción. Es rápida de configurar y proporciona una capa de seguridad básica.

## Configuración Completa con Autenticación Básica

```bash
# 1. Instalar herramienta
sudo apt-get install apache2-utils

# 2. Crear archivo de contraseñas
sudo htpasswd -c /etc/nginx/.htpasswd_mlflow admin
# Ingresa la contraseña cuando te la pida

# 3. Dar permisos correctos
sudo chmod 644 /etc/nginx/.htpasswd_mlflow
sudo chown root:www-data /etc/nginx/.htpasswd_mlflow

# 4. Editar configuración de Nginx
sudo nano /etc/nginx/sites-available/mlflow
```

Agregar estas líneas en el bloque `location /` del servidor HTTPS:

```nginx
auth_basic "MLflow - Acceso Restringido";
auth_basic_user_file /etc/nginx/.htpasswd_mlflow;
```

```bash
# 5. Verificar y recargar
sudo nginx -t
sudo systemctl reload nginx
```

Ahora cuando accedas a `https://mlflow.eddeso.com`, te pedirá usuario y contraseña.

