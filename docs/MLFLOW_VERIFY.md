# Verificación Final de MLflow

## El 301 es Normal

El `301 Moved Permanently` que ves es porque Certbot configuró SSL y redirige HTTP → HTTPS. Esto es correcto.

## Verificaciones Necesarias

### 1. Verificar que MLflow está corriendo:

```bash
# Ver estado del servicio
sudo systemctl status mlflowcore.service

# Verificar puerto 5050
sudo ss -tlnp | grep 5050

# Ver logs
sudo journalctl -u mlflowcore.service -n 20 --no-pager
```

### 2. Probar con HTTPS (no HTTP):

```bash
# Probar con HTTPS (el 301 redirige a HTTPS)
curl -k -H "Host: mlflow.eddeso.com" https://localhost | head -30

# O seguir la redirección
curl -L -H "Host: mlflow.eddeso.com" http://localhost | head -30
```

### 3. Verificar configuración SSL de MLflow:

```bash
# Ver configuración completa de MLflow (debe tener bloque SSL)
sudo cat /etc/nginx/sites-available/mlflow
```

### 4. Probar directamente el puerto 5050:

```bash
# Verificar que MLflow responde directamente
curl http://localhost:5050 | head -20
```

Si esto funciona, MLflow está corriendo. El problema es solo la configuración de Nginx.

### 5. Ver configuración SSL completa:

```bash
# Ver qué configuración tiene MLflow (debe tener listen 443)
sudo nginx -T | grep -A 30 "server_name mlflow.eddeso.com"
```

## Solución si MLflow no está corriendo

Si el servicio no está activo:

```bash
# Verificar que MLflow está instalado
/home/victus/projects/CORE/manu/env/bin/python -m mlflow --version

# Si no está instalado
cd /home/victus/projects/CORE/manu
source env/bin/activate
pip install mlflow>=2.8.0
deactivate

# Reiniciar servicio
sudo systemctl restart mlflowcore.service
sudo systemctl status mlflowcore.service
```

