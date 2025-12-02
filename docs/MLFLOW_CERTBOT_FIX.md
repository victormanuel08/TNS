# Solución: Certbot desplegó SSL en el archivo incorrecto

## Problema

Certbot desplegó el certificado SSL en `/etc/nginx/sites-enabled/0-livecore` en lugar de `/etc/nginx/sites-enabled/0-mlflow`. Esto significa que `0-livecore` está capturando `mlflow.eddeso.com`.

## Solución: Agregar bloque SSL manualmente a MLflow

### 1. Ver configuración de livecore para entender el problema:

```bash
sudo cat /etc/nginx/sites-available/livecore | grep -A 10 "server_name"
```

### 2. Agregar bloque SSL manualmente a MLflow:

```bash
sudo nano /etc/nginx/sites-available/mlflow
```

Agrega este bloque DESPUÉS del bloque HTTP existente:

```nginx
server {
    listen 443 ssl http2;
    server_name mlflow.eddeso.com;

    ssl_certificate /etc/letsencrypt/live/mlflow.eddeso.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mlflow.eddeso.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://localhost:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts para operaciones largas
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

### 3. Verificar y recargar:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Probar:

```bash
curl -k -H "Host: mlflow.eddeso.com" https://localhost | head -20
```

## Alternativa: Excluir mlflow de livecore

Si `livecore` tiene un wildcard `*.eddeso.com`, debemos excluir `mlflow`:

```bash
# Ver configuración de livecore
sudo cat /etc/nginx/sites-available/livecore
```

Si tiene `server_name *.eddeso.com`, cambiarlo a excluir mlflow (pero esto es más complejo).

La solución más simple es agregar el bloque SSL manualmente a MLflow como se muestra arriba.

