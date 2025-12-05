# Generación Automática de Configuraciones de Nginx

## 📋 Descripción

El comando `generar_configs_nginx` genera y actualiza automáticamente las configuraciones de Nginx para los dominios registrados en `EmpresaDominio`. Este script lee las configuraciones existentes de Nginx para evitar duplicados y conflictos.

## ⚡ Resumen Ejecutivo

### Preguntas Frecuentes

**¿Cómo se llama el servicio del frontend?**
- Nombre real: **`Eddeso`** (proceso PM2) ✅ VERIFICADO 2025-12-04
- Verificar: `pm2 list` para ver todos los procesos

**¿Qué puerto corre?**
- Puerto real: **`3006`** ✅ VERIFICADO 2025-12-04
- Verificar: `pm2 show Eddeso` muestra `--port 3006`

**¿Se ejecuta automáticamente al crear un `EmpresaDominio`?**
- ❌ **NO**, actualmente es **manual**
- El administrador debe ejecutar: `sudo python manage.py generar_configs_nginx`

**¿Se reinicia PM2 cuando se agrega un dominio?**
- ❌ **NO es necesario**
- PM2 no necesita reiniciarse porque el frontend ya está corriendo
- Nginx solo cambia a qué dominio redirige, no afecta el proceso del frontend

**¿Se reinicia Nginx cuando se agrega un dominio?**
- ⚠️ **NO automáticamente**, pero **SÍ es necesario** hacerlo manualmente
- Después de ejecutar el script: `sudo systemctl reload nginx`

**¿Cuándo se ejecuta?**
- Actualmente: **Manual** después de crear/actualizar un dominio
- Futuro: Se puede automatizar con Django signals o Celery tasks

**¿Cuánto tiempo tarda?**
- Generar configuraciones: **~15-20 segundos** (10 dominios nuevos)
- Recargar Nginx: **< 1 segundo**
- **Total: ~20 segundos** (manual)

## 🚀 Cómo Ejecutar

### Comando Básico (Con Valores Fijos)

```bash
cd /home/victus/projects/CORE/manu
source env/bin/activate
python manage.py generar_configs_nginx_fixed
```

**O usar el script automatizado:**

```bash
# Dar permisos
chmod +x docs/script_generar_configs_nginx.sh

# Ejecutar (requiere sudo)
sudo docs/script_generar_configs_nginx.sh
```

### Comando Original (Con Parámetros)

```bash
cd /home/victus/projects/CORE/manu
source env/bin/activate
python manage.py generar_configs_nginx --frontend-port 3006
```

### Opciones Disponibles

```bash
# Modo dry-run (solo muestra lo que haría, sin crear archivos)
python manage.py generar_configs_nginx --dry-run

# Especificar directorio de Nginx (default: /etc/nginx)
python manage.py generar_configs_nginx --nginx-dir /etc/nginx

# Especificar directorio de salida (default: /etc/nginx/sites-available)
python manage.py generar_configs_nginx --output-dir /etc/nginx/sites-available

# Especificar puerto del frontend (default: 3006 para Eddeso)
python manage.py generar_configs_nginx_fixed --frontend-port 3006

# Combinar opciones
python manage.py generar_configs_nginx_fixed --dry-run --frontend-port 3006
```

### Con Permisos de Root (Recomendado)

El script necesita permisos de escritura en `/etc/nginx/sites-available` y `/etc/nginx/sites-enabled`:

```bash
sudo python manage.py generar_configs_nginx_fixed
```

**O usar el script bash automatizado (recomendado):**

```bash
sudo docs/script_generar_configs_nginx.sh
```

Este script:
- ✅ Verifica que el servicio PM2 "Eddeso" esté corriendo
- ✅ Verifica que el puerto 3006 esté en uso
- ✅ Ejecuta el comando Django con valores fijos
- ✅ Verifica la configuración de Nginx
- ✅ Recarga Nginx automáticamente si todo está correcto

## 🔍 Identificación del Servicio Livecore

### ¿Qué es "livecore"?

"Livecore" es el nombre del proceso PM2 que ejecuta el frontend Nuxt de eddeso.com. Este servicio maneja todas las peticiones del frontend.

### Verificar el Servicio PM2

```bash
# Listar todos los procesos PM2
pm2 list

# Ver información detallada del proceso "livecore"
pm2 describe livecore

# Ver logs en tiempo real
pm2 logs livecore

# Ver estado y puerto
pm2 show livecore

# Ver todos los procesos con sus nombres
pm2 jlist | jq '.[] | {name: .name, pid: .pid, status: .pm2_env.status}'
```

### Identificar el Nombre Real del Servicio

Si no se llama "livecore", busca el proceso que corre el frontend:

```bash
# Ver todos los procesos PM2
pm2 list

# Buscar procesos que contengan "nuxt", "front", "eddeso"
pm2 list | grep -i "nuxt\|front\|eddeso"

# Ver el archivo de configuración PM2 (si existe)
cat ~/.pm2/ecosystem.config.js
# o
cat ~/ecosystem.config.js
```

### Verificar el Puerto del Frontend

El puerto por defecto es **3001**, pero puede variar. Verifica de estas formas:

### Identificar el Puerto

El puerto por defecto es **3001**, pero puede verificarse de varias formas:

#### Opción 1: Desde PM2

```bash
pm2 show livecore | grep "script path"
# Luego ver el archivo de configuración PM2 o el package.json
```

#### Opción 2: Desde Nginx

```bash
# Ver la configuración de livecore en Nginx
sudo cat /etc/nginx/sites-available/livecore | grep proxy_pass

# Debería mostrar algo como:
# proxy_pass http://localhost:3001;
```

#### Opción 3: Desde el Proceso

```bash
# Ver qué puerto está usando el proceso
sudo netstat -tlnp | grep node
# o
sudo ss -tlnp | grep node

# Buscar el PID del proceso livecore
pm2 pid livecore
# Luego ver los puertos abiertos por ese PID
sudo lsof -p $(pm2 pid livecore) | grep LISTEN
```

#### Opción 4: Desde el Código

```bash
# Verificar en el código del frontend
cd /home/victus/projects/CORE/front
cat nuxt.config.ts | grep -i port
# o
cat package.json | grep -i "start\|dev"

# Ver el archivo .env del frontend (si existe)
cat .env | grep -i port
```

#### Opción 5: Desde el Proceso PM2 Directamente

```bash
# Obtener el PID del proceso
PID=$(pm2 pid livecore)  # o el nombre real del proceso

# Ver variables de entorno del proceso (puede contener PORT)
pm2 env $PID

# Ver el comando completo que ejecuta PM2
pm2 describe livecore | grep "script path\|exec cwd"
```

### Script de Verificación Completa

Crea un script para verificar todo:

```bash
#!/bin/bash
# verify_livecore.sh

echo "🔍 Verificando servicio Livecore"
echo "================================"
echo ""

# 1. Verificar PM2
echo "1️⃣ Procesos PM2:"
pm2 list
echo ""

# 2. Buscar proceso del frontend
echo "2️⃣ Buscando proceso del frontend:"
pm2 list | grep -i "nuxt\|front\|eddeso\|livecore" || echo "   No encontrado con esos nombres"
echo ""

# 3. Ver puertos abiertos por Node
echo "3️⃣ Puertos abiertos por procesos Node:"
sudo netstat -tlnp | grep node || sudo ss -tlnp | grep node
echo ""

# 4. Ver configuración de Nginx
echo "4️⃣ Configuración de Nginx (proxy_pass):"
sudo grep -r "proxy_pass.*localhost" /etc/nginx/sites-enabled/ | grep -v "#"
echo ""

# 5. Verificar puerto en código
echo "5️⃣ Puerto en código del frontend:"
if [ -f "/home/victus/projects/CORE/front/nuxt.config.ts" ]; then
    grep -i "port\|300" /home/victus/projects/CORE/front/nuxt.config.ts | head -5
else
    echo "   Archivo nuxt.config.ts no encontrado"
fi
```

Guarda como `verify_livecore.sh`, dale permisos y ejecuta:

```bash
chmod +x verify_livecore.sh
./verify_livecore.sh
```

## 📝 Qué Hace el Script

### Paso 1: Leer Configuraciones Existentes

El script lee todos los archivos en:
- `/etc/nginx/sites-available/`
- `/etc/nginx/sites-enabled/`

Extrae todos los `server_name` de cada archivo para construir una lista de dominios ya configurados.

### Paso 2: Leer Dominios de Base de Datos

Lee todos los dominios activos de `EmpresaDominio` donde `activo=True`.

### Paso 3: Identificar Dominios a Configurar

Compara los dominios de BD con los ya configurados en Nginx:
- **Nuevos dominios**: No están en Nginx → Se crearán archivos nuevos
- **Dominios existentes**: Ya están en Nginx → Se actualizarán si es necesario

### Paso 4: Crear Backups

Antes de modificar archivos existentes, crea backups en:
```
/etc/nginx/sites-available/.backups/
```

Formato: `{nombre_archivo}_{timestamp}.backup`

### Paso 5: Generar/Actualizar Configuraciones

#### Para Dominios Nuevos

Crea un archivo nuevo en `/etc/nginx/sites-available/`:
```
ecommerce-{dominio_sanitizado}
```

Ejemplo: `ecommerce-empresanueva_com_co`

Y crea un enlace simbólico en `/etc/nginx/sites-enabled/`.

#### Para Dominios Existentes

Actualiza el archivo existente agregando el dominio al `server_name` si no está presente.

### Paso 6: Verificar y Sugerir Recarga

El script verifica la configuración de Nginx con `nginx -t` y sugiere recargar Nginx si todo está correcto.

## ⚙️ Flujo Actual (Manual)

### Cuando se Crea un `EmpresaDominio`

**Actualmente NO se ejecuta automáticamente**. El flujo es:

1. **Usuario crea `EmpresaDominio`** en el frontend/admin
2. **Se guarda en BD** (sin cambios en Nginx)
3. **Administrador ejecuta manualmente**:
   ```bash
   sudo python manage.py generar_configs_nginx
   ```
4. **El script genera/actualiza** las configuraciones de Nginx
5. **Administrador recarga Nginx**:
   ```bash
   sudo nginx -t  # Verificar
   sudo systemctl reload nginx  # Recargar
   ```

### ¿Se Reinicia PM2?

**NO**, el script NO reinicia PM2 automáticamente. PM2 no necesita reiniciarse porque:
- El frontend Nuxt ya está corriendo en el puerto 3001
- Nginx solo cambia a qué dominio redirige, no afecta el proceso del frontend
- El frontend detecta el dominio desde el header `Host` en cada request

### ¿Se Reinicia Nginx?

**NO automáticamente**, pero **SÍ es necesario** hacerlo manualmente después de ejecutar el script:

```bash
# 1. Verificar que la configuración es válida
sudo nginx -t

# 2. Si es válida, recargar (sin downtime)
sudo systemctl reload nginx

# O reiniciar (con breve downtime)
sudo systemctl restart nginx
```

## ⏱️ Tiempos Estimados

| Operación | Tiempo Estimado |
|-----------|----------------|
| Leer configuraciones Nginx | 1-3 segundos |
| Leer dominios de BD | < 1 segundo |
| Crear backup | < 1 segundo por archivo |
| Generar archivo nuevo | < 1 segundo por dominio |
| Actualizar archivo existente | < 1 segundo por dominio |
| Verificar Nginx (`nginx -t`) | 1-2 segundos |
| Recargar Nginx (`reload`) | < 1 segundo |
| **Total (10 dominios nuevos)** | **~15-20 segundos** |

## 🔄 Automatización Futura

### Opción 1: Signal de Django (Recomendado)

Agregar un signal `post_save` en el modelo `EmpresaDominio`:

```python
# manu/apps/sistema_analitico/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import EmpresaDominio
from django.core.management import call_command
import subprocess

@receiver(post_save, sender=EmpresaDominio)
def generar_config_nginx_automatico(sender, instance, created, **kwargs):
    """Genera configuración de Nginx automáticamente cuando se crea/actualiza un dominio"""
    if instance.activo:
        try:
            # Ejecutar el comando
            call_command('generar_configs_nginx', verbosity=0)
            
            # Verificar y recargar Nginx
            result = subprocess.run(
                ['sudo', 'nginx', '-t'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Recargar Nginx
                subprocess.run(
                    ['sudo', 'systemctl', 'reload', 'nginx'],
                    timeout=10
                )
                logger.info(f"✅ Configuración de Nginx actualizada para {instance.dominio}")
            else:
                logger.error(f"❌ Error en configuración de Nginx: {result.stderr}")
        except Exception as e:
            logger.error(f"❌ Error generando configuración de Nginx: {e}")
```

**Registrar el signal en `apps.py`:**

```python
# manu/apps/sistema_analitico/apps.py
from django.apps import AppConfig

class SistemaAnaliticoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sistema_analitico'

    def ready(self):
        import apps.sistema_analitico.signals  # Registrar signals
```

**Ventajas:**
- ✅ Automático al crear/actualizar dominio
- ✅ Sin intervención manual
- ✅ Tiempo: ~15-20 segundos después de crear el dominio

**Desventajas:**
- ⚠️ Requiere permisos sudo (puede fallar si Django no tiene permisos)
- ⚠️ Puede fallar si Nginx tiene errores de configuración

### Opción 2: Tarea Celery (Más Robusto)

Crear una tarea Celery que se ejecute después de crear el dominio:

```python
# manu/apps/sistema_analitico/tasks.py
@shared_task
def generar_config_nginx_task():
    """Genera configuración de Nginx y recarga el servicio"""
    from django.core.management import call_command
    import subprocess
    
    try:
        call_command('generar_configs_nginx', verbosity=0)
        
        # Verificar Nginx
        result = subprocess.run(
            ['sudo', 'nginx', '-t'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], timeout=10)
            return {'success': True, 'message': 'Nginx recargado exitosamente'}
        else:
            return {'success': False, 'error': result.stderr}
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

**Llamar desde el ViewSet:**

```python
# manu/apps/sistema_analitico/views.py
from .tasks import generar_config_nginx_task

class EmpresaDominioViewSet(...):
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == 201:
            # Ejecutar tarea asíncrona
            generar_config_nginx_task.delay()
        return response
```

**Ventajas:**
- ✅ No bloquea la respuesta HTTP
- ✅ Puede reintentar si falla
- ✅ Mejor manejo de errores
- ✅ Tiempo: ~15-20 segundos (asíncrono)

### Opción 3: Webhook/API Endpoint

Crear un endpoint que el frontend llame después de crear el dominio:

```python
# manu/apps/sistema_analitico/views.py
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerar_configs_nginx_view(request):
    """Endpoint para regenerar configuraciones de Nginx manualmente"""
    from django.core.management import call_command
    import subprocess
    
    try:
        call_command('generar_configs_nginx', verbosity=0)
        
        result = subprocess.run(
            ['sudo', 'nginx', '-t'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], timeout=10)
            return Response({'success': True, 'message': 'Nginx recargado exitosamente'})
        else:
            return Response({'success': False, 'error': result.stderr}, status=500)
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=500)
```

**Ventajas:**
- ✅ Control manual desde el frontend
- ✅ Puede mostrar progreso/errores al usuario
- ✅ No requiere permisos sudo en Django

## 📊 Resumen de Requisitos

| Componente | ¿Se Reinicia? | ¿Cuándo? | Tiempo |
|------------|---------------|----------|--------|
| **PM2 (livecore)** | ❌ NO | Nunca necesario | - |
| **Nginx** | ✅ SÍ | Después de generar configs | < 1 segundo |
| **Django** | ❌ NO | Nunca necesario | - |

## 🧪 Pruebas

### 1. Verificar que el Script Funciona

```bash
# Modo dry-run primero
sudo python manage.py generar_configs_nginx --dry-run

# Si todo se ve bien, ejecutar realmente
sudo python manage.py generar_configs_nginx
```

### 2. Verificar Configuración de Nginx

```bash
sudo nginx -t
```

### 3. Recargar Nginx

```bash
sudo systemctl reload nginx
```

### 4. Probar el Dominio

```bash
# Desde el servidor
curl -H "Host: empresanueva.com.co" http://localhost

# O desde el navegador
# http://empresanueva.com.co
```

### 5. Ver Logs

```bash
# Logs de Nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Logs de PM2 (livecore)
pm2 logs livecore
```

## ⚠️ Consideraciones Importantes

1. **Permisos**: El script necesita permisos de escritura en `/etc/nginx/`
2. **Backups**: Siempre crea backups antes de modificar archivos existentes
3. **Validación**: Siempre verifica con `nginx -t` antes de recargar
4. **Orden de Archivos**: Nginx procesa `server_name` en orden alfabético de archivos en `sites-enabled`
5. **Wildcards**: Si `livecore` tiene `server_name *.eddeso.com`, puede capturar todos los dominios
6. **Puerto**: Asegúrate de que el puerto del frontend (3001) sea correcto

## 📚 Referencias

- [Documentación de Nginx](https://nginx.org/en/docs/)
- [PM2 Documentation](https://pm2.keymetrics.io/docs/usage/quick-start/)
- [Django Management Commands](https://docs.djangoproject.com/en/stable/howto/custom-management-commands/)

