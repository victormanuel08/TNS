# Solución: Tareas Celery en Estado PENDING

## Problema

Las tareas de Celery se quedan en estado `PENDING` y nunca se procesan. Esto significa que el worker de Celery no está ejecutando las tareas.

## Diagnóstico

### 1. Verificar que Celery Worker esté corriendo

```bash
# Verificar el servicio de Celery
sudo systemctl status celerycore.service

# Ver logs del servicio
sudo journalctl -u celerycore.service -n 50 --no-pager

# Verificar si hay procesos de Celery corriendo
ps aux | grep celery
```

### 2. Verificar conexión a Redis

```bash
# Verificar que Redis esté corriendo
sudo systemctl status redis-server
# o
sudo systemctl status redis

# Probar conexión a Redis
redis-cli -h localhost -p 6379 ping
# Debe responder: PONG

# Verificar el puerto en el .env
grep REDIS_URL /home/victus/projects/CORE/manu/.env
```

**IMPORTANTE**: El `.env` debe tener `REDIS_URL=redis://localhost:6379/0` (no 6380)

### 3. Verificar configuración de Celery

```bash
# Verificar que el archivo celery.py existe
ls -la /home/victus/projects/CORE/manu/config/celery.py

# Verificar que __init__.py importa Celery
cat /home/victus/projects/CORE/manu/config/__init__.py
```

El archivo `config/__init__.py` debe contener:
```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

### 4. Probar tarea manualmente

```bash
cd /home/victus/projects/CORE/manu
source env/bin/activate

# Iniciar worker manualmente para ver errores
celery -A config worker -l info
```

## Soluciones

### Solución 1: Verificar y corregir REDIS_URL

```bash
# Editar .env
nano /home/victus/projects/CORE/manu/.env

# Asegurar que tenga:
REDIS_URL=redis://localhost:6379/0
```

### Solución 2: Reiniciar servicios

```bash
# Reiniciar Redis
sudo systemctl restart redis-server
# o
sudo systemctl restart redis

# Reiniciar Celery
sudo systemctl restart celerycore.service

# Verificar que ambos estén corriendo
sudo systemctl status redis-server
sudo systemctl status celerycore.service
```

### Solución 3: Verificar que __init__.py importa Celery

```bash
# Verificar contenido
cat /home/victus/projects/CORE/manu/config/__init__.py

# Si no existe o está vacío, crearlo:
cat > /home/victus/projects/CORE/manu/config/__init__.py << 'EOF'
from .celery import app as celery_app

__all__ = ('celery_app',)
EOF
```

### Solución 4: Verificar servicio systemd de Celery

```bash
# Ver contenido del servicio
sudo cat /etc/systemd/system/celerycore.service

# Debe tener algo como:
# [Unit]
# Description=Celery Worker (CORE)
# After=network.target redis-server.service
#
# [Service]
# Type=forking
# User=victus
# Group=victus
# WorkingDirectory=/home/victus/projects/CORE/manu
# Environment="PATH=/home/victus/projects/CORE/manu/env/bin"
# ExecStart=/home/victus/projects/CORE/manu/env/bin/celery -A config worker -l info --detach
# ExecStop=/bin/kill -s TERM $MAINPID
# Restart=always
# RestartSec=10
#
# [Install]
# WantedBy=multi-user.target

# Recargar systemd y reiniciar
sudo systemctl daemon-reload
sudo systemctl restart celerycore.service
```

### Solución 5: Probar tarea directamente

```bash
cd /home/victus/projects/CORE/manu
source env/bin/activate

# Iniciar worker en modo interactivo
celery -A config worker -l info --concurrency=1

# En otra terminal, probar una tarea
python manage.py shell
```

En el shell de Django:
```python
from apps.sistema_analitico.tasks import descubrir_empresas_task

# Probar tarea
result = descubrir_empresas_task.delay(1)  # Reemplazar 1 con un servidor_id válido
print(f"Task ID: {result.id}")
print(f"Status: {result.state}")
```

## Verificación Final

Después de aplicar las soluciones:

1. **Verificar que Redis esté corriendo**:
   ```bash
   redis-cli ping
   # Debe responder: PONG
   ```

2. **Verificar que Celery Worker esté corriendo**:
   ```bash
   sudo systemctl status celerycore.service
   # Debe mostrar: active (running)
   ```

3. **Ver logs de Celery**:
   ```bash
   sudo journalctl -u celerycore.service -f
   # Debe mostrar mensajes como:
   # [INFO/MainProcess] Connected to redis://localhost:6379/0
   # [INFO/MainProcess] celery@hostname ready.
   ```

4. **Probar desde el frontend**:
   - Ir a la pestaña "Empresas" en el admin panel
   - Hacer clic en "Escanear Empresas"
   - Verificar que el estado cambie de PENDING a PROCESSING y luego a SUCCESS

## Comandos Útiles

```bash
# Ver todas las tareas en Redis
redis-cli
> KEYS celery*
> GET celery-task-meta-<task_id>

# Limpiar tareas viejas de Redis (cuidado)
redis-cli FLUSHDB

# Ver workers activos
celery -A config inspect active

# Ver tareas registradas
celery -A config inspect registered
```

## Problemas Comunes

### Error: "No module named 'celery'"
```bash
# Instalar Celery en el venv
cd /home/victus/projects/CORE/manu
source env/bin/activate
pip install celery redis
```

### Error: "Connection refused" a Redis
- Verificar que Redis esté corriendo: `sudo systemctl status redis-server`
- Verificar el puerto en `.env`: debe ser `6379`, no `6380`
- Verificar firewall: `sudo ufw status`

### Error: "No tasks found"
- Verificar que `config/__init__.py` importa `celery_app`
- Verificar que las tareas estén decoradas con `@shared_task`
- Reiniciar el worker después de cambios en el código


