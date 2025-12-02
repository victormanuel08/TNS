# Verificación Final de MLflow

## Verificar configuración completa

```bash
# Ver toda la configuración de MLflow (debe tener bloque HTTP y HTTPS)
sudo cat /etc/nginx/sites-available/mlflow
```

Debe tener DOS bloques `server`:
1. Bloque HTTP (listen 80) - Redirige a HTTPS
2. Bloque HTTPS (listen 443 ssl) - Sirve MLflow

## Verificar que Nginx reconoce la configuración

```bash
# Ver qué configuración está activa para mlflow.eddeso.com
sudo nginx -T | grep -B 5 -A 25 "server_name mlflow.eddeso.com"
```

## Probar correctamente

```bash
# Probar sin el punto extra
curl -k -H "Host: mlflow.eddeso.com" https://localhost | head -20

# O ver solo las primeras líneas del HTML
curl -k -H "Host: mlflow.eddeso.com" https://localhost 2>/dev/null | head -20
```

## Si aún muestra el frontend

Verificar qué configuración está capturando la petición:

```bash
# Ver todas las configuraciones que mencionan mlflow
sudo nginx -T | grep -B 10 -A 10 "mlflow"

# Ver orden de procesamiento
ls -1 /etc/nginx/sites-enabled/ | sort | head -5
```

## Verificar que el bloque SSL está en el archivo correcto

```bash
# Ver si el bloque SSL está en mlflow
sudo grep -A 5 "listen 443" /etc/nginx/sites-available/mlflow

# Ver si está en livecore (incorrecto)
sudo grep -A 5 "listen 443.*mlflow" /etc/nginx/sites-available/livecore
```

