# Monitoreo en Tiempo Real del Procesamiento de ZIP de RUTs

## 📋 Comandos para Monitorear

### 1. Ver Tareas Activas de Celery
```bash
# Ver todas las tareas activas
celery -A config inspect active

# Ver tareas activas con más detalle
celery -A config inspect active -d celery@$(hostname)
```

### 2. Ver Estado de una Tarea Específica
Si tienes el `task_id` que se retornó al subir el ZIP:
```bash
# Reemplaza TASK_ID con el ID real
celery -A config result TASK_ID
```

### 3. Monitoreo en Tiempo Real con Celery Events
```bash
# Monitoreo en tiempo real (muestra todas las tareas)
celery -A config events

# Monitoreo con formato más legible
celery -A config events --dump
```

### 4. Ver Logs del Worker de Celery
```bash
# Ver logs en tiempo real (si usas systemd)
sudo journalctl -u celery -f

# O si lo ejecutas manualmente, los logs aparecen en la consola
```

### 5. Ver Estado de la Tarea desde Python/Django Shell
```python
from celery.result import AsyncResult
from config.celery import app

# Reemplaza TASK_ID con el ID real
task_id = 'tu-task-id-aqui'
result = AsyncResult(task_id, app=app)

# Ver estado
print(f"Estado: {result.state}")
print(f"Info: {result.info}")

# Ver progreso (si está disponible)
if result.info:
    print(f"Procesados: {result.info.get('procesados', 0)}/{result.info.get('total', 0)}")
    print(f"Exitosos: {result.info.get('exitosos', 0)}")
    print(f"Fallidos: {result.info.get('fallidos', 0)}")
    print(f"Status: {result.info.get('status', 'N/A')}")
```

### 6. Ver Logs de Django
```bash
# Si tienes logs configurados en Django
tail -f /ruta/a/tus/logs/django.log | grep -i rut

# O ver todos los logs
tail -f /ruta/a/tus/logs/django.log
```

## 📊 Información que Verás

Cuando monitorees, verás información como:
- **Estado**: `PROCESSING`, `SUCCESS`, `ERROR`
- **Progreso**: `Procesando X/Y: nombre_archivo.pdf`
- **Contadores**:
  - `total`: Total de archivos PDF en el ZIP
  - `procesados`: Archivos procesados hasta ahora
  - `exitosos`: RUTs procesados exitosamente
  - `fallidos`: RUTs que fallaron

## 🔍 Ejemplo de Salida

```
Estado: PROCESSING
Info: {
    'status': 'Procesando 45/120: empresa_123.pdf',
    'total': 120,
    'procesados': 44,
    'exitosos': 38,
    'fallidos': 6
}
```

## ⚡ Comando Rápido Recomendado

Para monitoreo continuo, usa:
```bash
# En una terminal
watch -n 2 'celery -A config inspect active'

# O para ver logs en tiempo real
tail -f /var/log/celery/worker.log
```

## 📝 Nota

- Si el ZIP tiene **menos de 50 archivos**, se procesa directamente (síncrono)
- Si tiene **más de 50 archivos**, se procesa con Celery (asíncrono) y recibirás un `task_id`
- El `task_id` se muestra en la respuesta del API cuando subes el ZIP

