# Acceso a MLflow desde el Navegador

MLflow corre en el puerto **5050** y puedes acceder de varias formas:

## Opción 1: Acceso Directo (Simple)

### Desde el servidor:
```bash
# En el servidor, abrir en navegador local
http://localhost:5050
```

### Desde fuera del servidor:
```bash
# Usar la IP pública del servidor
http://TU_IP_SERVIDOR:5050
```

**⚠️ Requisito**: El puerto 5050 debe estar abierto en el firewall:
```bash
sudo ufw allow 5050/tcp
```

## Opción 2: Proxy Reverso con Nginx (Recomendado - Más Seguro)

### 1. Crear configuración de Nginx

Crea el archivo `/etc/nginx/sites-available/mlflow`:

```nginx
server {
    listen 80;
    server_name mlflow.eddeso.com;  # O el subdominio que prefieras

    location / {
        proxy_pass http://localhost:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (si MLflow lo necesita)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 2. Habilitar la configuración

```bash
sudo ln -s /etc/nginx/sites-available/mlflow /etc/nginx/sites-enabled/mlflow
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Configurar SSL (Opcional pero recomendado)

```bash
sudo certbot --nginx -d mlflow.eddeso.com
```

### 4. Acceder

Ahora puedes acceder a MLflow en:
- `https://mlflow.eddeso.com` (con SSL)
- O `http://mlflow.eddeso.com` (sin SSL)

## Opción 3: Túnel SSH (Para desarrollo/testing)

Si no quieres exponer el puerto públicamente, puedes usar un túnel SSH:

```bash
# Desde tu máquina local
ssh -L 5050:localhost:5050 usuario@TU_IP_SERVIDOR
```

Luego accede desde tu navegador local:
```
http://localhost:5050
```

## Configuración del Servicio Systemd

Para que MLflow se inicie automáticamente, crea un servicio systemd:

### 1. Crear archivo de servicio

Crea `/etc/systemd/system/mlflowcore.service`:

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

### 2. Habilitar y iniciar el servicio

```bash
sudo systemctl daemon-reload
sudo systemctl enable mlflowcore.service
sudo systemctl start mlflowcore.service
sudo systemctl status mlflowcore.service
```

### 3. Ver logs

```bash
sudo journalctl -u mlflowcore.service -f
```

## Verificación

### Verificar que MLflow está corriendo

```bash
# Verificar el puerto
sudo ss -tlnp | grep 5050

# Debería mostrar algo como:
# LISTEN 0 128 0.0.0.0:5050 *:* users:(("python",pid=XXXX,fd=XX))
```

### Probar desde el servidor

```bash
curl http://localhost:5050
```

Debería devolver HTML de la interfaz de MLflow.

## Notas Importantes

1. **No necesitas crear subdominio**: Puedes acceder directamente por IP:puerto o usar túnel SSH.

2. **Seguridad**: Si expones MLflow públicamente, considera:
   - Usar autenticación (MLflow no tiene auth por defecto)
   - Restringir acceso por IP en Nginx
   - Usar túnel SSH para acceso temporal

3. **Variable de entorno**: Asegúrate de que en `manu/.env` tengas:
   ```env
   MLFLOW_TRACKING_URI=http://localhost:5050
   ```

4. **Firewall**: Si usas acceso directo, abre el puerto:
   ```bash
   sudo ufw allow 5050/tcp
   ```

