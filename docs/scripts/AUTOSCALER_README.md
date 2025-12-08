# Autoescalador de Workers Gunicorn y Celery

## 📋 Descripción

Sistema de autoescalado que ajusta dinámicamente el número de workers de Gunicorn y Celery basándose en:
- **CPU**: Uso de CPU del sistema
- **Memoria**: Memoria disponible
- **Cola Celery**: Tamaño de la cola de tareas (solo para Celery)

## 🚀 Instalación

```bash
# 1. Copiar scripts al servidor
# (Desde tu máquina local, copiar docs/scripts/* al servidor)

# 2. En el servidor, ejecutar instalador
sudo bash /home/victus/scripts/install_autoscaler.sh
```

## ⚙️ Configuración

Editar `/home/victus/scripts/autoscaler_config.json`:

```json
{
  "projects": {
    "backregisters": {
      "enabled": false,  // Cambiar a true para habilitar
      "min_workers": 1,
      "max_workers": 3,
      "cpu_thresholds": {
        "scale_up_2": 70,
        "scale_up_3": 80,
        "scale_down_2": 40,
        "scale_down_1": 35
      }
    }
  }
}
```

### Parámetros importantes:

- **enabled**: `true` para habilitar autoescalado para este proyecto
- **min_workers**: Número mínimo de workers (siempre activos)
- **max_workers**: Número máximo de workers (límite superior)
- **cpu_thresholds**: Umbrales de CPU para escalar
  - `scale_up_N`: CPU > X% durante Y minutos → subir a N workers
  - `scale_down_N`: CPU < X% durante Y minutos → bajar a N workers
- **cpu_duration_minutes**: Duración mínima antes de escalar
- **memory_threshold_mb**: Memoria disponible mínima antes de escalar

## 📊 Uso

### Iniciar autoescalador

```bash
# Iniciar timer (ejecuta cada 2 minutos)
sudo systemctl start autoscaler.timer
sudo systemctl enable autoscaler.timer

# Ver estado
sudo systemctl status autoscaler.timer
```

### Ver logs

```bash
# Logs en tiempo real
sudo journalctl -u autoscaler -f

# Últimas 50 líneas
sudo journalctl -u autoscaler -n 50
```

### Verificar workers actuales

```bash
# Ver workers de un servicio
ps aux | grep "backregisters.*gunicorn" | grep -v grep | wc -l

# Ver todos los workers
ps aux | grep gunicorn | grep -v grep
```

## 🔄 Plan de Implementación Gradual

### Fase 1: Prueba con backregisters (menor riesgo)

1. Editar `autoscaler_config.json`:
   ```json
   "backregisters": {
     "enabled": true
   }
   ```

2. Modificar servicio systemd a 1 worker base:
   ```bash
   sudo nano /etc/systemd/system/backregisters.service
   # Cambiar: --workers 3 → --workers 1
   sudo systemctl daemon-reload
   sudo systemctl restart backregisters
   ```

3. Iniciar autoescalador:
   ```bash
   sudo systemctl start autoscaler.timer
   ```

4. Monitorear durante 1 hora:
   ```bash
   sudo journalctl -u autoscaler -f
   watch -n 5 'ps aux | grep "backregisters.*gunicorn" | grep -v grep | wc -l'
   ```

### Fase 2: Aplicar a otros proyectos

Repetir proceso para:
- backdipro
- backglobal
- backbce
- backcore (Gunicorn + Celery)

## 🛠️ Troubleshooting

### El autoescalador no escala

1. Verificar que está habilitado:
   ```bash
   jq '.projects.backregisters.enabled' /home/victus/scripts/autoscaler_config.json
   # Debe ser: true
   ```

2. Verificar logs:
   ```bash
   sudo journalctl -u autoscaler -n 100
   ```

3. Verificar métricas:
   ```bash
   bash /home/victus/scripts/autoscaler_metrics.sh all
   ```

### Error al modificar servicio systemd

El script necesita permisos de root. Verificar:
```bash
sudo systemctl status autoscaler
```

### Workers no cambian

1. Verificar que el servicio se reinició:
   ```bash
   sudo systemctl status backregisters
   ```

2. Verificar número de workers:
   ```bash
   ps aux | grep "backregisters.*gunicorn" | grep -v grep
   ```

## 📈 Monitoreo

### Métricas a observar

- **CPU promedio**: Debe estar entre 40-80% en uso normal
- **Memoria disponible**: Debe mantenerse > 1GB
- **Workers activos**: Debe variar según carga
- **Tiempo de respuesta**: No debe degradarse

### Alertas

El autoescalador registra todas las acciones en `/var/log/autoscaler.log`:
- Escalado hacia arriba: `scale_up`
- Escalado hacia abajo: `scale_down`
- Errores: `ERROR`

## 🔒 Seguridad

- El script se ejecuta como `root` (necesario para modificar systemd)
- Solo modifica archivos de servicio systemd
- No modifica código de aplicación
- Rollback fácil: restaurar archivos de servicio desde backup

## 📝 Rollback

Si necesitas desactivar el autoescalado:

```bash
# 1. Detener autoescalador
sudo systemctl stop autoscaler.timer
sudo systemctl disable autoscaler.timer

# 2. Restaurar servicios originales
sudo cp /home/victus/backups/systemd_services/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart backcore backbce backglobal backregisters backdipro celerycore
```

