# Validación de Configuración MLflow en el Servidor

## 1. Validar Configuración de Nginx

### Verificar que el archivo existe:
```bash
sudo ls -la /etc/nginx/sites-available/mlflow
```

### Ver el contenido completo:
```bash
sudo cat /etc/nginx/sites-available/mlflow
```

### Verificar que el enlace simbólico existe:
```bash
sudo ls -la /etc/nginx/sites-enabled/ | grep mlflow
```

### Verificar que la configuración es válida:
```bash
sudo nginx -t
```

**Salida esperada:**
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### Verificar que Nginx está usando la configuración:
```bash
sudo nginx -T | grep -A 20 "mlflow.eddeso.com"
```

## 2. Validar Servicio Systemd

### Verificar que el archivo existe:
```bash
sudo ls -la /etc/systemd/system/mlflowcore.service
```

### Ver el contenido completo:
```bash
sudo cat /etc/systemd/system/mlflowcore.service
```

### Verificar que systemd reconoce el servicio:
```bash
sudo systemctl list-unit-files | grep mlflow
```

**Salida esperada:**
```
mlflowcore.service                    enabled
```

### Verificar el estado del servicio:
```bash
sudo systemctl status mlflowcore.service
```

**Salida esperada (si está corriendo):**
```
● mlflowcore.service - MLflow Tracking Server (CORE)
     Loaded: loaded (/etc/systemd/system/mlflowcore.service; enabled; vendor preset: enabled)
     Active: active (running) since [fecha]
```

### Verificar que está escuchando en el puerto 5050:
```bash
sudo ss -tlnp | grep 5050
```

**Salida esperada:**
```
LISTEN 0 128 0.0.0.0:5050 *:* users:(("python",pid=XXXX,fd=XX))
```

## 3. Comparación Rápida (Verificar Contenido)

### Nginx - Debe contener:
```bash
sudo grep -E "server_name|proxy_pass|mlflow" /etc/nginx/sites-available/mlflow
```

**Debe mostrar:**
- `server_name mlflow.eddeso.com;`
- `proxy_pass http://localhost:5050;`

### Systemd - Debe contener:
```bash
sudo grep -E "Description|ExecStart|WorkingDirectory" /etc/systemd/system/mlflowcore.service
```

**Debe mostrar:**
- `Description=MLflow Tracking Server (CORE)`
- `ExecStart=/home/victus/projects/CORE/manu/venv/bin/mlflow ui --port 5050 --host 0.0.0.0`
- `WorkingDirectory=/home/victus/projects/CORE/manu`

## 4. Validación Completa (Script)

Ejecuta este comando para validar todo de una vez:

```bash
echo "=== Validación Nginx ===" && \
sudo test -f /etc/nginx/sites-available/mlflow && echo "✅ Archivo Nginx existe" || echo "❌ Archivo Nginx NO existe" && \
sudo test -L /etc/nginx/sites-enabled/mlflow && echo "✅ Enlace simbólico existe" || echo "❌ Enlace simbólico NO existe" && \
sudo nginx -t 2>&1 | grep -q "successful" && echo "✅ Configuración Nginx válida" || echo "❌ Configuración Nginx inválida" && \
echo "" && \
echo "=== Validación Systemd ===" && \
sudo test -f /etc/systemd/system/mlflowcore.service && echo "✅ Archivo systemd existe" || echo "❌ Archivo systemd NO existe" && \
sudo systemctl is-enabled mlflowcore.service >/dev/null 2>&1 && echo "✅ Servicio habilitado" || echo "❌ Servicio NO habilitado" && \
sudo systemctl is-active mlflowcore.service >/dev/null 2>&1 && echo "✅ Servicio activo" || echo "❌ Servicio NO activo" && \
echo "" && \
echo "=== Validación Puerto ===" && \
sudo ss -tlnp | grep -q ":5050" && echo "✅ Puerto 5050 en uso" || echo "❌ Puerto 5050 NO en uso"
```

## 5. Ver Logs (Si hay problemas)

### Logs del servicio MLflow:
```bash
sudo journalctl -u mlflowcore.service -n 50 --no-pager
```

### Logs de Nginx:
```bash
sudo tail -f /var/log/nginx/error.log
```

### Verificar errores recientes:
```bash
sudo journalctl -u mlflowcore.service --since "10 minutes ago" | grep -i error
```

## 6. Contenido Esperado

### `/etc/nginx/sites-available/mlflow` debe tener:
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
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

### `/etc/systemd/system/mlflowcore.service` debe tener:
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

## 7. Comandos de Reparación (Si algo falla)

### Si Nginx no encuentra el archivo:
```bash
sudo cp docs/nginx/mlflow.conf /etc/nginx/sites-available/mlflow
sudo ln -sf /etc/nginx/sites-available/mlflow /etc/nginx/sites-enabled/mlflow
sudo nginx -t
sudo systemctl reload nginx
```

### Si el servicio systemd no existe:
```bash
sudo cp docs/systemd/mlflowcore.service /etc/systemd/system/mlflowcore.service
sudo systemctl daemon-reload
sudo systemctl enable mlflowcore.service
sudo systemctl start mlflowcore.service
```

### Si el servicio no inicia:
```bash
# Ver qué está fallando
sudo journalctl -u mlflowcore.service -n 50

# Verificar que el venv existe
ls -la /home/victus/projects/CORE/manu/venv/bin/mlflow

# Verificar que MLflow está instalado
/home/victus/projects/CORE/manu/venv/bin/mlflow --version
```

