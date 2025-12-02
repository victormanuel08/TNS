# Solución: Celery Worker Timeout en Systemd

## Problema

El servicio `celerycore.service` está fallando con timeout:
```
celerycore.service: start operation timed out. Terminating.
celerycore.service: Failed with result 'timeout'.
```

## Causas Identificadas

1. **Pool incorrecto**: Está usando `-P solo` que es para Windows, no para Linux
2. **Task events deshabilitados**: `task events: OFF` impide el monitoreo
3. **Timeout muy corto**: Systemd mata el proceso antes de que termine de iniciar
4. **Type incorrecto**: Debe ser `Type=notify` o `Type=simple`, no `Type=forking`

## Solución

### 1. Crear/Actualizar el archivo de servicio systemd

```bash
sudo nano /etc/systemd/system/celerycore.service
```

Copiar el contenido del archivo `docs/systemd/celerycore.service`:

```ini
[Unit]
Description=Celery Worker for TNS Core
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=notify
User=victus
Group=victus
WorkingDirectory=/home/victus/projects/CORE/manu
Environment="PATH=/home/victus/projects/CORE/manu/env/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/victus/projects/CORE/manu/.env

# Comando para iniciar Celery
# -P prefork: Pool de procesos para Linux (NO usar -P solo que es para Windows)
# -E: Habilitar eventos de tareas para monitoreo
# -l info: Nivel de logging
ExecStart=/home/victus/projects/CORE/manu/env/bin/celery -A config worker -l info -P prefork --concurrency=4 -E --time-limit=3600

# Notificar a systemd cuando esté listo
NotifyAccess=all

# Timeouts aumentados para dar tiempo a Celery de iniciar
TimeoutStartSec=300
TimeoutStopSec=60

# Reiniciar automáticamente si falla
Restart=always
RestartSec=10

# Límites de recursos
LimitNOFILE=65536

# Logs
StandardOutput=journal
StandardError=journal
SyslogIdentifier=celerycore

[Install]
WantedBy=multi-user.target
```

### 2. Recargar systemd y reiniciar

```bash
# Recargar configuración de systemd
sudo systemctl daemon-reload

# Detener el servicio actual (si está corriendo)
sudo systemctl stop celerycore.service

# Iniciar el servicio
sudo systemctl start celerycore.service

# Habilitar para que inicie automáticamente
sudo systemctl enable celerycore.service

# Verificar estado
sudo systemctl status celerycore.service
```

### 3. Verificar que funciona

```bash
# Ver logs en tiempo real
sudo journalctl -u celerycore.service -f

# Deberías ver:
# - ✅ celery@hostname v5.5.3 (immunity)
# - ✅ .> task events: ON (habilitado)
# - ✅ .> concurrency: 4 (prefork)  <-- NO debe decir "solo"
# - ✅ [tasks] listando todas las tareas
```

### 4. Probar una tarea

```bash
# Desde Django shell
cd /home/victus/projects/CORE/manu
source env/bin/activate
python manage.py shell
```

```python
from apps.sistema_analitico.tasks import descubrir_empresas_task

# Probar tarea (reemplazar 1 con un servidor_id válido)
result = descubrir_empresas_task.delay(1)
print(f"Task ID: {result.id}")
print(f"Status: {result.state}")

# Verificar que no esté en PENDING
import time
time.sleep(2)
print(f"Status después de 2s: {result.state}")
```

## Cambios Clave

### Antes (Incorrecto)
```bash
celery -A config worker -l info -P solo
```
- ❌ `-P solo` es para Windows
- ❌ Sin `-E` (eventos deshabilitados)
- ❌ Timeout muy corto en systemd

### Después (Correcto)
```bash
celery -A config worker -l info -P prefork --concurrency=4 -E --time-limit=3600
```
- ✅ `-P prefork` para Linux
- ✅ `-E` habilita eventos de tareas
- ✅ `TimeoutStartSec=300` en systemd (5 minutos)
- ✅ `Type=notify` para mejor integración con systemd

## Verificación Final

1. **Estado del servicio**:
   ```bash
   sudo systemctl status celerycore.service
   # Debe mostrar: active (running)
   ```

2. **Logs sin errores**:
   ```bash
   sudo journalctl -u celerycore.service -n 50 --no-pager
   # No debe haber "timeout" o "Failed"
   ```

3. **Tareas funcionando**:
   - Las tareas no deben quedarse en estado `PENDING`
   - Deben ejecutarse y completarse

4. **Monitoreo en tiempo real**:
   - En el admin frontend, pestaña "Logs" → "Tareas en Tiempo Real"
   - Debe mostrar workers activos y tareas ejecutándose

## Troubleshooting

Si sigue fallando:

1. **Verificar Redis**:
   ```bash
   redis-cli ping
   # Debe responder: PONG
   ```

2. **Verificar permisos**:
   ```bash
   ls -la /home/victus/projects/CORE/manu
   # El usuario victus debe tener permisos de lectura/escritura
   ```

3. **Verificar entorno virtual**:
   ```bash
   /home/victus/projects/CORE/manu/env/bin/celery --version
   # Debe mostrar la versión de Celery
   ```

4. **Probar manualmente**:
   ```bash
   cd /home/victus/projects/CORE/manu
   source env/bin/activate
   celery -A config worker -l info -P prefork --concurrency=4 -E
   # Si funciona manualmente, el problema es la configuración de systemd
   ```

