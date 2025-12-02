# Solución: Falta configuración SSL para MLflow

## Problema

La configuración de MLflow solo tiene `listen 80` (HTTP) pero NO tiene `listen 443 ssl` (HTTPS). Cuando accedes por HTTPS, Nginx no encuentra la configuración y redirige al frontend.

## Solución: Configurar SSL con Certbot

Ejecuta estos comandos en el servidor:

```bash
# 1. Verificar si ya hay certificado SSL para mlflow.eddeso.com
sudo certbot certificates | grep mlflow

# 2. Si NO hay certificado, obtenerlo
sudo certbot --nginx -d mlflow.eddeso.com

# 3. Verificar que se agregó el bloque SSL
sudo cat /etc/nginx/sites-available/mlflow | grep -A 20 "listen 443"
```

## Verificación

Después de ejecutar Certbot, la configuración debe tener DOS bloques:

1. **Bloque HTTP** (listen 80) - Redirige a HTTPS
2. **Bloque HTTPS** (listen 443 ssl) - Sirve MLflow

### Verificar configuración completa:

```bash
sudo cat /etc/nginx/sites-available/mlflow
```

Debe mostrar algo como:

```nginx
# Bloque HTTP - Redirige a HTTPS
server {
    if ($host = mlflow.eddeso.com) {
        return 301 https://$host$request_uri;
    }
    listen 80;
    server_name mlflow.eddeso.com;
    return 404;
}

# Bloque HTTPS - Sirve MLflow
server {
    listen 443 ssl http2;
    server_name mlflow.eddeso.com;
    
    ssl_certificate /etc/letsencrypt/live/mlflow.eddeso.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mlflow.eddeso.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:5050;
        # ... resto de configuración
    }
}
```

## Si Certbot no funciona

Si Certbot da error, verifica:

```bash
# Ver si el DNS está resuelviendo correctamente
dig mlflow.eddeso.com

# Verificar que Cloudflare tiene el registro
# (debe estar en Cloudflare con proxy activado)
```

## Después de configurar SSL

```bash
# Recargar Nginx
sudo nginx -t
sudo systemctl reload nginx

# Probar con HTTPS
curl -k -H "Host: mlflow.eddeso.com" https://localhost | head -20
```

Debe mostrar HTML de MLflow, no del frontend.

