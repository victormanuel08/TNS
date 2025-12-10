# 🔍 Comandos para Diagnosticar CIUU 4290 en el VPS

## 📋 Comandos Rápidos

### 1. **Verificar en Redis**

```bash
python manage.py shell -c "
from django.core.cache import cache
cache_key = 'ciiu_info_4290'
info = cache.get(cache_key)
if info:
    print('✅ ENCONTRADO en Redis')
    print(f'Descripción: {info.get(\"cseDescripcion\", \"N/A\")}')
    print(f'Incluye: {len(info.get(\"incluye\", []))} items')
    print(f'Excluye: {len(info.get(\"excluye\", []))} items')
else:
    print('❌ NO está en Redis')
"
```

### 2. **Verificar en Base de Datos**

```bash
python manage.py shell -c "
from apps.sistema_analitico.models import ActividadEconomica
from django.utils import timezone
from datetime import timedelta

try:
    actividad = ActividadEconomica.objects.get(codigo='4290')
    print('✅ ENCONTRADO en BD')
    print(f'Descripción: {actividad.descripcion}')
    print(f'Incluye: {len(actividad.incluye) if actividad.incluye else 0} items')
    print(f'Excluye: {len(actividad.excluye) if actividad.excluye else 0} items')
    
    if actividad.fecha_ultima_consulta_api:
        dias = (timezone.now() - actividad.fecha_ultima_consulta_api).days
        print(f'Última consulta API: hace {dias} días')
        print('✅ Reciente' if dias < 7 else '⚠️ Antigua (> 7 días)')
except ActividadEconomica.DoesNotExist:
    print('❌ NO está en BD')
"
```

### 3. **Forzar Consulta Completa (Ver Flujo Real)**

```bash
python manage.py shell -c "
import logging
logging.basicConfig(level=logging.INFO)

from apps.sistema_analitico.services.clasificador_contable_service import obtener_contexto_ciuu_inteligente

print('🔍 Consultando CIUU 4290...')
print('')

resultado = obtener_contexto_ciuu_inteligente('4290')

if resultado:
    print('✅ RESULTADO:')
    print(f'Código: {resultado.get(\"codigo\")}')
    print(f'Descripción: {resultado.get(\"descripcion\")}')
    print(f'Fuente: {resultado.get(\"fuente\")}')
    print(f'Incluye: {len(resultado.get(\"incluye_raw\", []))} items')
    print(f'Excluye: {len(resultado.get(\"excluye_raw\", []))} items')
    
    fuente = resultado.get('fuente')
    if fuente == 'base_datos':
        print('')
        print('📊 Vino desde BD (no consultó API)')
    elif fuente == 'api_externa':
        print('')
        print('📊 Vino desde API (no estaba en BD)')
else:
    print('❌ No se pudo obtener')
"
```

### 4. **Script Completo de Diagnóstico**

```bash
# Subir el script al VPS y ejecutarlo
bash diagnostico_ciuu_4290.sh
```

O ejecutar todo en una línea:

```bash
python manage.py shell << 'EOF'
from django.core.cache import cache
from apps.sistema_analitico.models import ActividadEconomica
from apps.sistema_analitico.services.clasificador_contable_service import obtener_contexto_ciuu_inteligente
from django.utils import timezone

CIUU = "4290"

print("=" * 50)
print(f"🔍 DIAGNÓSTICO CIUU {CIUU}")
print("=" * 50)
print("")

# 1. Redis
print("1️⃣ Redis Cache:")
cache_key = f"ciiu_info_{CIUU}"
info_redis = cache.get(cache_key)
if info_redis:
    print(f"   ✅ ENCONTRADO en Redis")
    print(f"   Descripción: {info_redis.get('cseDescripcion', 'N/A')}")
else:
    print(f"   ❌ NO está en Redis")
print("")

# 2. BD
print("2️⃣ Base de Datos:")
try:
    actividad = ActividadEconomica.objects.get(codigo=CIUU)
    print(f"   ✅ ENCONTRADO en BD")
    print(f"   Descripción: {actividad.descripcion}")
    if actividad.fecha_ultima_consulta_api:
        dias = (timezone.now() - actividad.fecha_ultima_consulta_api).days
        print(f"   Última consulta: hace {dias} días")
        print(f"   {'✅ Reciente' if dias < 7 else '⚠️ Antigua'}")
except ActividadEconomica.DoesNotExist:
    print(f"   ❌ NO está en BD")
print("")

# 3. Consulta completa
print("3️⃣ Consulta Completa (flujo real):")
resultado = obtener_contexto_ciuu_inteligente(CIUU)
if resultado:
    print(f"   ✅ OBTENIDO")
    print(f"   Fuente: {resultado.get('fuente')}")
    print(f"   Descripción: {resultado.get('descripcion')}")
    print(f"   Incluye: {len(resultado.get('incluye_raw', []))} items")
    print(f"   Excluye: {len(resultado.get('excluye_raw', []))} items")
    
    fuente = resultado.get('fuente')
    if fuente == 'base_datos':
        print("")
        print("   📊 CONCLUSIÓN: Vino desde BD (no consultó API)")
    elif fuente == 'api_externa':
        print("")
        print("   📊 CONCLUSIÓN: Vino desde API (no estaba en BD)")
        print("   📊 Ahora está guardado en BD y Redis")
else:
    print(f"   ❌ No se pudo obtener")
print("")

# 4. Verificar Redis nuevamente
print("4️⃣ Redis después de consulta:")
info_redis_2 = cache.get(cache_key)
if info_redis_2:
    print(f"   ✅ AHORA SÍ está en Redis (se guardó)")
else:
    print(f"   ❌ Aún no está en Redis")
print("")

print("=" * 50)
print("✅ Diagnóstico completado")
print("=" * 50)
EOF
```

---

## 🎯 Comando Todo-en-Uno (Copia y Pega)

```bash
python manage.py shell << 'EOF'
from django.core.cache import cache
from apps.sistema_analitico.models import ActividadEconomica
from apps.sistema_analitico.services.clasificador_contable_service import obtener_contexto_ciuu_inteligente
from django.utils import timezone

CIUU = "4290"
print("=" * 50)
print(f"🔍 DIAGNÓSTICO CIUU {CIUU}")
print("=" * 50)
print("")

# 1. Redis
print("1️⃣ Redis Cache:")
cache_key = f"ciiu_info_{CIUU}"
info_redis = cache.get(cache_key)
print(f"   {'✅ ENCONTRADO' if info_redis else '❌ NO está'}")
if info_redis:
    print(f"   Descripción: {info_redis.get('cseDescripcion', 'N/A')}")
print("")

# 2. BD
print("2️⃣ Base de Datos:")
try:
    actividad = ActividadEconomica.objects.get(codigo=CIUU)
    print(f"   ✅ ENCONTRADO")
    print(f"   Descripción: {actividad.descripcion}")
    if actividad.fecha_ultima_consulta_api:
        dias = (timezone.now() - actividad.fecha_ultima_consulta_api).days
        print(f"   Última consulta: hace {dias} días ({'✅ Reciente' if dias < 7 else '⚠️ Antigua'})")
except ActividadEconomica.DoesNotExist:
    print(f"   ❌ NO está en BD")
print("")

# 3. Consulta completa
print("3️⃣ Consulta Completa (flujo real):")
resultado = obtener_contexto_ciuu_inteligente(CIUU)
if resultado:
    print(f"   ✅ OBTENIDO desde: {resultado.get('fuente')}")
    print(f"   Descripción: {resultado.get('descripcion')}")
    print(f"   Incluye: {len(resultado.get('incluye_raw', []))} items")
    print(f"   Excluye: {len(resultado.get('excluye_raw', []))} items")
    
    fuente = resultado.get('fuente')
    if fuente == 'base_datos':
        print("   📊 CONCLUSIÓN: Vino desde BD (no consultó API)")
    elif fuente == 'api_externa':
        print("   📊 CONCLUSIÓN: Vino desde API (no estaba en BD)")
        print("   📊 Ahora está guardado en BD y Redis")
else:
    print(f"   ❌ No se pudo obtener")
print("")

# 4. Redis después
print("4️⃣ Redis después de consulta:")
info_redis_2 = cache.get(cache_key)
print(f"   {'✅ AHORA SÍ está' if info_redis_2 else '❌ Aún no está'}")
print("")
print("=" * 50)
EOF
```

---

## 📊 Interpretación de Resultados

### **Escenario 1: Está en Redis**
```
1️⃣ Redis Cache: ✅ ENCONTRADO
2️⃣ Base de Datos: ✅ ENCONTRADO
3️⃣ Consulta Completa: ✅ OBTENIDO desde: base_datos
   📊 CONCLUSIÓN: Vino desde BD (no consultó API)
```
**Significado**: El CIUU ya estaba cacheado, no se consultó la API.

### **Escenario 2: NO está en Redis pero SÍ en BD**
```
1️⃣ Redis Cache: ❌ NO está
2️⃣ Base de Datos: ✅ ENCONTRADO
3️⃣ Consulta Completa: ✅ OBTENIDO desde: base_datos
   📊 CONCLUSIÓN: Vino desde BD (no consultó API)
4️⃣ Redis después de consulta: ✅ AHORA SÍ está
```
**Significado**: Estaba en BD pero no en Redis. Se cargó desde BD y se guardó en Redis.

### **Escenario 3: NO está en Redis NI en BD**
```
1️⃣ Redis Cache: ❌ NO está
2️⃣ Base de Datos: ❌ NO está
3️⃣ Consulta Completa: ✅ OBTENIDO desde: api_externa
   📊 CONCLUSIÓN: Vino desde API (no estaba en BD)
   📊 Ahora está guardado en BD y Redis
4️⃣ Redis después de consulta: ✅ AHORA SÍ está
```
**Significado**: No estaba en ningún lado, se consultó la API, se guardó en BD y Redis.

---

## 🔧 Ver Logs en Tiempo Real

Si quieres ver los logs mientras se ejecuta:

```bash
# En una terminal, ver logs de Django
tail -f /ruta/a/logs/django.log | grep -i "ciiu\|4290"

# O si usas systemd
journalctl -u tu-servicio-django -f | grep -i "ciiu\|4290"
```

