# Backups Automáticos a S3

## 📋 Resumen

El sistema de backups automáticos está configurado para ejecutarse automáticamente según la hora programada de cada empresa (por defecto 1:00 AM).

## ⚙️ Configuración

### 1. Programación de Tareas (Celery Beat)

La tarea `procesar_backups_programados` se ejecuta **cada hora** y verifica qué empresas tienen backups programados para esa hora.

**Configuración en `settings.py`:**
```python
CELERY_BEAT_SCHEDULE = {
    'procesar-backups-programados': {
        'task': 'sistema_analitico.procesar_backups_programados',
        'schedule': crontab(minute=0),  # Cada hora en el minuto 0
    },
}
```

### 2. Iniciar Celery Beat

**En Windows (desarrollo):**
```powershell
celery -A config beat -l info
```

**En Ubuntu/VPS (producción):**
```bash
# Crear servicio systemd para Celery Beat
sudo nano /etc/systemd/system/celerybeat.service
```

Contenido del servicio:
```ini
[Unit]
Description=Celery Beat Scheduler
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=victus
Group=victus
WorkingDirectory=/home/victus/projects/CORE/manu
Environment="PATH=/home/victus/projects/CORE/manu/env/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/victus/projects/CORE/manu/.env
ExecStart=/home/victus/projects/CORE/manu/env/bin/celery -A config beat -l info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Activar el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable celerybeat.service
sudo systemctl start celerybeat.service
sudo systemctl status celerybeat.service
```

## 📅 Política de Retención

### Año Fiscal Actual (ej: 2025)
- **Máximo 3 backups** (últimos 3 días)
- Se eliminan los backups más antiguos automáticamente
- Cada backup se crea según la hora programada de la empresa (1:00 AM por defecto)

### Años Fiscales Anteriores
- **1 backup por año fiscal**
- Si el backup tiene **más de 30 días**, se elimina automáticamente para mantenerlo fresco
- El sistema verifica y crea backups automáticamente cuando es necesario

### Ejemplo

Para una empresa con año fiscal 2025:
- **2025**: Máximo 3 backups (ej: 01/12, 02/12, 03/12)
- **2024**: 1 backup (se reemplaza si tiene más de 30 días)
- **2023**: 1 backup (se reemplaza si tiene más de 30 días)

## 🔧 Configuración por Empresa

Cada empresa puede configurar:
- **`hora_backup`**: Hora programada (default: 01:00)
- **`backups_habilitados`**: Activar/desactivar backups automáticos (default: True)
- **`limite_espacio_gb`**: Límite de espacio en GB (default: 1 GB)

## ⚡ Estrategia de Procesamiento (Evitar Sobrecarga)

Para evitar sobrecargar el servidor con ~1000 empresas:

### A las 1:00 AM (Hora Programada)
- **Prioridad Alta**: Procesa empresas del año fiscal actual
- Procesa en **lotes de 20 empresas** para evitar sobrecarga
- Todas las empresas del año actual se procesan en esta hora

### Durante el Día (Cada Hora)
- **Prioridad Baja**: Procesa empresas de años anteriores que necesitan backup
- Verifica máximo **50 empresas por hora**
- Procesa máximo **10 empresas por hora** que necesitan backup (>30 días)
- Rate limiting: **10 tareas por minuto** máximo

### Ejemplo con 1000 Empresas
- **~80 empresas año actual**: Se procesan a la 1:00 AM en lotes de 20 (4 lotes)
- **~920 empresas años anteriores**: Se procesan gradualmente durante el día
  - Si cada empresa necesita backup cada 30 días, se procesan ~30 empresas/día
  - Con 10 empresas/hora, se cubren todas en ~92 horas (~4 días)

## 📊 Verificación

Para verificar que los backups automáticos están funcionando:

```bash
# Ver logs de Celery Beat
sudo journalctl -u celerybeat.service -f

# Ver logs de Celery Worker
sudo journalctl -u celerycore.service -f

# Verificar tareas programadas
celery -A config inspect scheduled
```

## ⚠️ Notas Importantes

1. **Celery Beat debe estar corriendo** para que los backups automáticos funcionen
2. La tarea se ejecuta cada hora y verifica empresas con margen de ±5 minutos
3. Si una empresa tiene `backups_habilitados=False`, no se ejecutarán backups automáticos
4. Los backups manuales desde el frontend no están sujetos a la hora programada

