# Flujo de Cache CIIU y Limpieza

## 📋 Resumen

Este documento explica cómo funciona el sistema de cache de códigos CIIU y cómo limpiarlo cuando sea necesario.

## 🔄 Flujo de Consulta CIIU

Cuando el sistema necesita información de un código CIIU, sigue este orden:

```
1. Cache Redis (ciiu_info_{codigo} y ciiu_modelo_{codigo})
   ↓ (si no existe)
2. Base de Datos (tabla ActividadEconomica)
   ↓ (si no existe)
3. API Externa (enlinea.ccc.org.co)
   ↓ (si tiene éxito)
4. Guardar en Base de Datos
5. Guardar en Cache Redis
```

### Detalles del Flujo

1. **Cache Redis**: 
   - Claves: `ciiu_info_{codigo}` (info de API) y `ciiu_modelo_{codigo}` (modelo Django)
   - Timeout: 7 días (604800 segundos)
   - Se verifica primero porque es lo más rápido

2. **Base de Datos**:
   - Tabla: `ActividadEconomica`
   - Si existe y fue consultada hace menos de 7 días, se retorna directamente
   - Si existe pero tiene más de 7 días, se actualiza desde la API

3. **API Externa**:
   - URL: `https://enlinea.ccc.org.co/busquedasciiu/bqciiu/busqueda`
   - Solo se consulta si no existe en BD o si se fuerza la actualización
   - Si la API falla, se usa la información existente en BD (si existe)

## ❓ Preguntas Frecuentes

### ¿Qué pasa si borro un CIUU de la base de datos?

Si borras un CIUU de la tabla `ActividadEconomica`:

1. **Si está en cache Redis**: El sistema seguirá usando el cache hasta que expire (7 días)
2. **Si no está en cache**: El sistema intentará consultar la API externa
3. **Si la API falla**: El sistema creará un registro básico con el código CIIU

**Recomendación**: Si borras un CIUU de BD, también limpia su cache de Redis para forzar la consulta a la API.

### ¿Si vuelvo a correr todos los RUTs, los CIUUs se agregan?

**Sí**, si vuelves a procesar todos los RUTs:

1. El sistema extraerá los códigos CIIU de cada RUT
2. Para cada código CIIU:
   - Buscará en cache Redis
   - Si no está, buscará en BD
   - Si no está en BD, consultará la API externa
   - Guardará el resultado en BD y cache

**Nota**: Si un CIUU ya existe en BD, no se volverá a crear, pero se actualizará si tiene más de 7 días sin consultar.

### ¿Cómo quitar el cache para que busque en BD y luego en API?

Tienes **3 opciones**:

#### Opción 1: Usar el comando de Django (Recomendado)

**Comando simplificado (recomendado si hay problemas de conexión)**:
```bash
# Limpiar cache de un código CIIU específico
python manage.py limpiar_cache_ciiu_simple --codigo 5611

# Limpiar TODOS los caches de CIUU
python manage.py limpiar_cache_ciiu_simple --todos
```

**Comando completo (con más opciones)**:
```bash
# Limpiar cache de un código CIIU específico
python manage.py limpiar_cache_ciiu --codigo 5611

# Limpiar TODOS los caches de CIUU (con confirmación)
python manage.py limpiar_cache_ciiu --todos

# Ver qué se eliminaría sin hacer cambios (dry-run)
python manage.py limpiar_cache_ciiu --codigo 5611 --dry-run
```

**Nota**: Si el comando `limpiar_cache_ciiu` falla con error de conexión, usa `limpiar_cache_ciiu_simple` que se conecta directamente a Redis.

#### Opción 2: Cerrar y reiniciar Redis

```bash
# En Windows (PowerShell)
Stop-Service redis
Start-Service redis

# O si usas Redis directamente
redis-cli FLUSHALL  # ⚠️ Esto elimina TODO el cache, no solo CIUU
```

**⚠️ ADVERTENCIA**: `FLUSHALL` elimina **TODO** el cache de Redis, no solo los CIUUs.

#### Opción 3: Limpiar manualmente desde Python/Django Shell

```python
from django.core.cache import cache

# Limpiar un código específico
codigo = "5611"
cache.delete(f"ciiu_info_{codigo}")
cache.delete(f"ciiu_modelo_{codigo}")

# Limpiar todos los caches de CIUU (requiere acceso a Redis)
from django.core.cache import caches
cache_backend = caches['default']
if hasattr(cache_backend, '_cache') and hasattr(cache_backend._cache, 'client'):
    redis_client = cache_backend._cache.client
    keys = redis_client.keys("ciiu_*")
    for key in keys:
        key_str = key.decode('utf-8') if isinstance(key, bytes) else key
        cache.delete(key_str)
```

## 🛠️ Comandos Útiles

### Limpiar cache de un CIUU específico

```bash
python manage.py limpiar_cache_ciiu --codigo 5611
```

### Limpiar todos los caches de CIUU

```bash
python manage.py limpiar_cache_ciiu --todos --force
```

### Ver qué se eliminaría (sin hacer cambios)

```bash
python manage.py limpiar_cache_ciiu --codigo 5611 --dry-run
```

### Procesar todos los RUTs nuevamente

```bash
# Esto procesará todos los RUTs y creará/actualizará los CIUUs necesarios
# (se hace desde la interfaz web o mediante la tarea Celery)
```

## 📝 Ejemplo: Caso de Uso

**Escenario**: Borraste el CIUU `5611` de la base de datos y quieres que el sistema lo vuelva a consultar desde la API.

**Pasos**:

1. **Limpiar el cache de Redis**:
   ```bash
   python manage.py limpiar_cache_ciiu --codigo 5611
   ```

2. **Procesar un RUT que use ese CIUU** (o esperar a que se procese automáticamente)

3. **El sistema automáticamente**:
   - No encontrará el CIUU en cache (lo limpiamos)
   - No lo encontrará en BD (lo borraste)
   - Consultará la API externa
   - Guardará el resultado en BD
   - Guardará el resultado en cache

## 🔍 Verificar Estado del Cache

Para verificar si un CIUU está en cache:

```python
from django.core.cache import cache

codigo = "5611"
info_cache = cache.get(f"ciiu_info_{codigo}")
modelo_cache = cache.get(f"ciiu_modelo_{codigo}")

if info_cache:
    print(f"✅ CIUU {codigo} está en cache (info)")
if modelo_cache:
    print(f"✅ CIUU {codigo} está en cache (modelo)")
```

## ⚠️ Advertencias

1. **No borres CIUUs de BD sin necesidad**: Si solo quieres actualizar la información, usa `forzar_actualizacion=True` en lugar de borrar.

2. **Cerrar Redis elimina TODO el cache**: No solo los CIUUs, sino también otros caches del sistema (DIAN, etc.).

3. **La API externa puede fallar**: Si la API está caída, el sistema usará la información existente en BD (si existe) o creará un registro básico.

4. **El cache expira automáticamente**: Después de 7 días, el cache se limpia automáticamente y se consulta la API nuevamente.

## 📚 Referencias

- Archivo de servicio: `manu/apps/sistema_analitico/services/ciiu_service.py`
- Función principal: `obtener_o_crear_actividad_economica()`
- Modelo: `manu/apps/sistema_analitico/models.py` → `ActividadEconomica`

