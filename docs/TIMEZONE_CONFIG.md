# Configuración de Zona Horaria - Bogotá, Colombia

## Configuración del Servidor (Ubuntu/Debian)

### 1. Verificar la zona horaria actual

```bash
timedatectl
```

### 2. Listar zonas horarias disponibles (buscar Bogotá)

```bash
timedatectl list-timezones | grep -i bogota
```

Debería mostrar: `America/Bogota`

### 3. Configurar la zona horaria del sistema

```bash
sudo timedatectl set-timezone America/Bogota
```

### 4. Verificar que se aplicó correctamente

```bash
timedatectl
```

Debería mostrar:
```
               Local time: [hora actual en Bogotá]
           Universal time: [hora UTC]
                 RTC time: [hora del reloj]
                Time zone: America/Bogota (COT, -0500)
```

### 5. Verificar que la hora es correcta

```bash
date
```

## Configuración de Django

Ya está configurado en `manu/config/settings.py`:

```python
TIME_ZONE = 'America/Bogota'
USE_TZ = True
CELERY_TIMEZONE = 'America/Bogota'
LANGUAGE_CODE = 'es-co'
```

### Aplicar cambios

Después de cambiar la configuración, reinicia los servicios:

```bash
# Reiniciar el servicio de Django
sudo systemctl restart backcore.service

# Reiniciar Celery
sudo systemctl restart celerycore.service

# Verificar que están corriendo
sudo systemctl status backcore.service
sudo systemctl status celerycore.service
```

## Configuración de PostgreSQL

PostgreSQL hereda la zona horaria del sistema operativo, pero puedes verificar:

```bash
# Conectarse a PostgreSQL
sudo -u postgres psql

# Dentro de PostgreSQL, verificar la zona horaria
SHOW timezone;

# Si no está en America/Bogota, configurarla (opcional)
ALTER DATABASE tns_core SET timezone = 'America/Bogota';
```

## Verificación Final

### 1. Verificar desde Python/Django

```bash
cd ~/projects/CORE/manu
source venv/bin/activate
python manage.py shell
```

Dentro del shell de Django:

```python
from django.utils import timezone
import pytz

# Ver la zona horaria configurada
print(timezone.get_current_timezone())
# Debería mostrar: <DstTzInfo 'America/Bogota' COT-1 day, 19:00:00 STD>

# Ver la hora actual
print(timezone.now())
# Debería mostrar la hora actual en Bogotá
```

### 2. Verificar desde el sistema

```bash
# Hora del sistema
date

# Hora UTC
date -u

# Diferencia esperada: 5 horas (Bogotá está UTC-5)
```

## Notas Importantes

1. **Todos los proyectos en el servidor** heredarán la zona horaria del sistema una vez configurada con `timedatectl`.

2. **Django con `USE_TZ = True`** almacena todas las fechas en UTC en la base de datos, pero las muestra en la zona horaria configurada (`TIME_ZONE`).

3. **Celery** también usará la zona horaria configurada para programar tareas.

4. **No es necesario reiniciar el servidor**, solo los servicios de Django y Celery.

5. **Si tienes otros proyectos** (BCE, CAES, etc.) que también usan Django, también heredarán esta configuración si usan `USE_TZ = True` y tienen `TIME_ZONE` configurado.

