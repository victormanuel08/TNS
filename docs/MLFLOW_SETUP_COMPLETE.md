# Configuración Completa de MLflow en mlflow.eddeso.com

## Paso 1: Agregar DNS en Cloudflare

1. Ve a tu panel de Cloudflare
2. Selecciona el dominio `eddeso.com`
3. Ve a **DNS** → **Records**
4. Haz clic en **Add record**
5. Configura:
   - **Type**: `A` (o `CNAME` si prefieres)
   - **Name**: `mlflow`
   - **IPv4 address**: `TU_IP_SERVIDOR` (o `@` si usas CNAME)
   - **Proxy status**: ✅ **Proxied** (nube naranja)
6. Guarda

**Nota**: Si usas CNAME, el contenido sería `eddeso.com` o el registro A principal.

## Paso 2: Crear configuración de Nginx en el servidor

Ejecuta estos comandos en el VPS:

```bash
# Crear archivo de configuración de Nginx
sudo nano /etc/nginx/sites-available/mlflow
```

Pega este contenido:

```nginx
server {
    listen 80;
    server_name mlflow.eddeso.com;

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

Guarda y cierra (Ctrl+X, Y, Enter)

## Paso 3: Habilitar la configuración

```bash
# Crear enlace simbólico
sudo ln -s /etc/nginx/sites-available/mlflow /etc/nginx/sites-enabled/mlflow

# Verificar que la configuración es correcta
sudo nginx -t

# Si todo está bien, recargar Nginx
sudo systemctl reload nginx
```

## Paso 4: Configurar SSL con Certbot

```bash
# Obtener certificado SSL
sudo certbot --nginx -d mlflow.eddeso.com
```

Certbot automáticamente:
- Obtendrá el certificado SSL
- Modificará la configuración de Nginx para usar HTTPS
- Configurará redirección HTTP → HTTPS

## Paso 5: Crear servicio Systemd para MLflow

```bash
# Crear archivo de servicio
sudo nano /etc/systemd/system/mlflowcore.service
```

Pega este contenido:

```ini
[Unit]
Description=MLflow Tracking Server (CORE)
After=network.target

[Service]
Type=simple
User=victus
Group=victus
WorkingDirectory=/home/victus/projects/CORE/manu
Environment="PATH=/home/victus/projects/CORE/manu/venv/bin"
ExecStart=/home/victus/projects/CORE/manu/venv/bin/mlflow ui --port 5050 --host 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Guarda y cierra.

## Paso 6: Habilitar e iniciar el servicio MLflow

```bash
# Recargar systemd
sudo systemctl daemon-reload

# Habilitar para que inicie automáticamente
sudo systemctl enable mlflowcore.service

# Iniciar el servicio
sudo systemctl start mlflowcore.service

# Verificar que está corriendo
sudo systemctl status mlflowcore.service
```

## Paso 7: Verificar que todo funciona

```bash
# Verificar que MLflow está escuchando en el puerto 5050
sudo ss -tlnp | grep 5050

# Verificar que Nginx está configurado correctamente
sudo nginx -t

# Ver logs de MLflow
sudo journalctl -u mlflowcore.service -f
```

## Paso 8: Actualizar variable de entorno (si es necesario)

Asegúrate de que en `~/projects/CORE/manu/.env` tengas:

```env
MLFLOW_TRACKING_URI=http://localhost:5050
```

**Nota**: El backend usa `localhost:5050` internamente, pero desde el navegador accedes por `https://mlflow.eddeso.com`.

## Verificación Final

1. **Desde el navegador**: Abre `https://mlflow.eddeso.com`
2. **Deberías ver**: La interfaz de MLflow con los experimentos

## Troubleshooting

### Si MLflow no carga:

```bash
# Verificar que el servicio está corriendo
sudo systemctl status mlflowcore.service

# Ver logs
sudo journalctl -u mlflowcore.service -n 50

# Verificar el puerto
sudo ss -tlnp | grep 5050
```

### Si hay error de SSL:

```bash
# Verificar certificado
sudo certbot certificates

# Renovar si es necesario
sudo certbot renew
```

### Si Nginx da error:

```bash
# Verificar configuración
sudo nginx -t

# Ver logs de Nginx
sudo tail -f /var/log/nginx/error.log
```

## Comandos Útiles

```bash
# Reiniciar MLflow
sudo systemctl restart mlflowcore.service

# Ver logs en tiempo real
sudo journalctl -u mlflowcore.service -f

# Detener MLflow
sudo systemctl stop mlflowcore.service

# Iniciar MLflow
sudo systemctl start mlflowcore.service
```

## Listo! 🎉

Ahora puedes acceder a MLflow en:
- **URL**: `https://mlflow.eddeso.com`
- **Sin necesidad de abrir puertos** (Nginx maneja todo)
- **Con SSL automático** (Certbot)
- **Inicia automáticamente** al reiniciar el servidor (systemd)

