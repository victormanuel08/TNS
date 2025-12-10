# 🔍 Flujo Completo de Búsqueda de CIUU (Incluye/Excluye)

## 📋 Escenario: El PDF del RUT ya tiene el código CIUU

Cuando el sistema extrae un código CIUU del PDF del RUT (ej: `5611`), necesita obtener la información detallada:
- **Descripción**: ¿Qué es esta actividad?
- **Incluye**: ¿Qué actividades incluye?
- **Excluye**: ¿Qué actividades excluye?

---

## 🔄 Secuencia de Búsqueda Completa

### **Paso 1: `obtener_contexto_ciuu_inteligente(ciuu_code)`**

Esta función es llamada cuando se necesita información detallada del CIUU. Sigue este flujo:

```
1. Buscar en Base de Datos (tabla ActividadEconomica)
   ↓ (si encuentra)
   ✅ RETORNA: descripción, incluye, excluye desde BD
   
   ↓ (si NO encuentra)
2. Llamar a obtener_o_crear_actividad_economica()
   ↓
3. obtener_o_crear_actividad_economica() hace:
   a) Buscar en BD (tabla ActividadEconomica)
      ↓ (si encuentra y es reciente < 7 días)
      ✅ RETORNA: actividad desde BD
      
      ↓ (si NO encuentra o es antigua > 7 días)
   b) Llamar a obtener_info_ciiu_completa()
      ↓
4. obtener_info_ciiu_completa() hace:
   a) Buscar en Cache Redis (clave: ciiu_info_{codigo})
      ↓ (si encuentra)
      ✅ RETORNA: info desde Redis
      
      ↓ (si NO encuentra)
   b) Consultar API del Gobierno (enlinea.ccc.org.co)
      - POST a: https://enlinea.ccc.org.co/busquedasciiu/bqciiu/busqueda
      - GET a: https://enlinea.ccc.org.co/busquedasciiu/bqciiu/actividades/{cseId}
      ↓ (si tiene éxito)
   c) Guardar en Cache Redis (7 días)
   d) Guardar en Base de Datos (tabla ActividadEconomica)
   e) ✅ RETORNA: info completa desde API
```

---

## 📊 Diagrama de Flujo Detallado

```
PDF RUT → CIUU: 5611
    ↓
obtener_contexto_ciuu_inteligente("5611")
    ↓
┌─────────────────────────────────────┐
│ 1. Buscar en BD (ActividadEconomica)│
│    WHERE codigo = '5611'             │
└─────────────────────────────────────┘
    ↓ (NO encuentra)
    ↓
┌─────────────────────────────────────┐
│ 2. obtener_o_crear_actividad_economica()│
│    a) Buscar en BD                   │
│    b) Si no existe o > 7 días:      │
│       → obtener_info_ciiu_completa() │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 3. obtener_info_ciiu_completa()     │
│    a) Cache Redis: ciiu_info_5611   │
│       ✅ Si existe → RETORNA        │
│    b) Si NO existe:                 │
│       → Consultar API Gobierno      │
│       → Guardar en Redis (7 días)   │
│       → Guardar en BD               │
│       ✅ RETORNA info completa      │
└─────────────────────────────────────┘
```

---

## 🔍 Detalles de Cada Paso

### **Paso 1: Buscar en Base de Datos**

**Código**: `obtener_contexto_ciuu_inteligente()` (línea 335-410)

```python
# Buscar en BD
actividad = ActividadEconomica.objects.filter(codigo=ciuu_code).first()

if actividad:
    # ✅ Encontrado en BD
    return {
        "codigo": ciuu_code,
        "descripcion": actividad.descripcion,
        "incluye": actividad.incluye,
        "excluye": actividad.excluye,
        "fuente": "base_datos"
    }
```

**Si encuentra**: Retorna inmediatamente con la información de BD.

**Si NO encuentra**: Continúa al paso 2.

---

### **Paso 2: `obtener_o_crear_actividad_economica()`**

**Código**: `ciiu_service.py` (línea 322-424)

**Flujo interno**:

1. **Buscar en BD**:
   ```python
   actividad = ActividadEconomica.objects.get(codigo=codigo_ciiu)
   ```

2. **Si existe y es reciente (< 7 días)**:
   - Retorna directamente desde BD
   - No consulta API

3. **Si NO existe o es antigua (> 7 días)**:
   - Llama a `obtener_info_ciiu_completa()`

---

### **Paso 3: `obtener_info_ciiu_completa()`**

**Código**: `ciiu_service.py` (línea 217-319)

**Flujo interno**:

1. **Buscar en Cache Redis**:
   ```python
   cache_key = f"ciiu_info_{codigo_ciiu}"
   cached_info = cache.get(cache_key)
   if cached_info:
       return cached_info  # ✅ RETORNA desde Redis
   ```

2. **Si NO está en Redis, consultar API**:
   ```python
   # POST a: https://enlinea.ccc.org.co/busquedasciiu/bqciiu/busqueda
   response_data = await _make_async_request(payload)
   
   # GET a: https://enlinea.ccc.org.co/busquedasciiu/bqciiu/actividades/{cseId}
   activity_details = await _get_activity_details(cseId)
   ```

3. **Procesar respuesta**:
   - Extraer "incluye" y "excluye"
   - Construir objeto completo

4. **Guardar en Cache Redis** (7 días):
   ```python
   cache.set(cache_key, resultado, timeout=604800)  # 7 días
   ```

5. **Retornar información completa**

---

## 🎯 Resumen del Flujo Completo

### **Cuando el PDF tiene CIUU `5611`:**

1. ✅ **Redis Cache** (`ciiu_info_5611`) → Si existe, retorna inmediatamente
2. ✅ **Base de Datos** (`ActividadEconomica` donde `codigo='5611'`) → Si existe y es reciente, retorna
3. ✅ **API Gobierno** (`enlinea.ccc.org.co`) → Si no está en cache ni BD, consulta API
4. ✅ **Guardar en Redis** (7 días) → Para próximas consultas
5. ✅ **Guardar en BD** (`ActividadEconomica`) → Para persistencia

---

## 📝 Ejemplo Real

**Caso**: PDF RUT tiene CIUU `5611` (Restaurantes)

```
1. obtener_contexto_ciuu_inteligente("5611")
   ↓
2. Buscar en BD: ActividadEconomica WHERE codigo='5611'
   → NO existe
   ↓
3. obtener_o_crear_actividad_economica("5611")
   ↓
4. obtener_info_ciiu_completa("5611")
   ↓
5. Buscar en Redis: ciiu_info_5611
   → NO existe
   ↓
6. Consultar API: POST https://enlinea.ccc.org.co/busquedasciiu/bqciiu/busqueda
   → Respuesta: { cseId: "12345", cseCodigo: "5611", ... }
   ↓
7. Obtener detalles: GET https://enlinea.ccc.org.co/busquedasciiu/bqciiu/actividades/12345
   → Respuesta: [ { actIncluye: "S", ... }, { actIncluye: "N", ... } ]
   ↓
8. Procesar:
   - incluye: [ actividades con actIncluye="S" ]
   - excluye: [ actividades con actIncluye="N" ]
   ↓
9. Guardar en Redis: ciiu_info_5611 (7 días)
   ↓
10. Guardar en BD: ActividadEconomica(codigo='5611', ...)
   ↓
11. ✅ RETORNA: { codigo: "5611", descripcion: "...", incluye: [...], excluye: [...] }
```

**Próxima vez que se consulte el mismo CIUU `5611`:**

```
1. obtener_contexto_ciuu_inteligente("5611")
   ↓
2. Buscar en BD: ActividadEconomica WHERE codigo='5611'
   → ✅ EXISTE
   ↓
3. ✅ RETORNA inmediatamente desde BD (sin consultar API)
```

---

## 🔑 Puntos Clave

1. **Redis es lo más rápido**: Si está en cache, retorna en milisegundos
2. **BD es persistente**: Si está en BD y es reciente, no consulta API
3. **API es la última opción**: Solo se consulta si no está en cache ni BD
4. **Cache de 7 días**: Tanto Redis como BD tienen validación de 7 días
5. **Auto-actualización**: Si la info en BD tiene > 7 días, se actualiza desde API

---

## 🛠️ Comandos para Verificar

```bash
# Verificar si está en Redis
python manage.py shell -c "
from django.core.cache import cache
info = cache.get('ciiu_info_5611')
print('En Redis:', 'Sí' if info else 'No')
"

# Verificar si está en BD
python manage.py shell -c "
from apps.sistema_analitico.models import ActividadEconomica
act = ActividadEconomica.objects.filter(codigo='5611').first()
print('En BD:', 'Sí' if act else 'No')
if act:
    print('Descripción:', act.descripcion)
    print('Incluye:', len(act.incluye) if act.incluye else 0, 'items')
    print('Excluye:', len(act.excluye) if act.excluye else 0, 'items')
"
```

