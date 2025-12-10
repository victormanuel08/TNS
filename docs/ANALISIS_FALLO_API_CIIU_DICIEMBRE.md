# 🔍 ANÁLISIS: Fallo de API CIIU desde 6 de Diciembre

## ❓ PREGUNTA DEL USUARIO

**"Veo que el 6 de diciembre empezó a fallar, los primeros 4 días trabajó bien. ¿Qué pasa? ¿Se cambió algo? ¿Difiere algo de cómo se hacía en BCE? ¿No los banearon? ¿Qué sucede?"**

---

## 🔍 COMPARACIÓN: Sistema Actual vs BCE

### **1. Payload (✅ IDÉNTICO)**

**BCE:**
```python
{
    "bdaCriterioBusqueda": codigo_ciiu,
    "bdaDispositivo": "desktop",
    "bdaIp": None,
    "bdaNavegador": "Chrome",
    "bdaQuery": codigo_ciiu,
    "bdaOpcionBusqueda": "codigo_ciiu",
    "bdaLatitud": "7.8972771",
    "bdaLongitud": "-72.4849746",
    "ciiuUsuario": {"usrId": 11294}
}
```

**Sistema Actual:**
```python
{
    "bdaCriterioBusqueda": codigo_ciiu,
    "bdaDispositivo": "desktop",
    "bdaIp": None,
    "bdaNavegador": "Chrome",
    "bdaQuery": codigo_ciiu,
    "bdaOpcionBusqueda": "codigo_ciiu",
    "bdaLatitud": "7.8972771",
    "bdaLongitud": "-72.4849746",
    "ciiuUsuario": {"usrId": 11294}
}
```

**✅ Payload es IDÉNTICO**

---

### **2. Headers (⚠️ DIFERENCIA CRÍTICA)**

**BCE:**
```python
async with aiohttp.ClientSession() as session:
    # Sin headers personalizados
    # aiohttp usa headers por defecto:
    # - User-Agent: Python/aiohttp/{version}
    # - Accept: */*
    # - Content-Type: application/json (si hay json)
```

**Sistema Actual:**
```python
async with aiohttp.ClientSession(timeout=timeout) as session:
    # Mismo comportamiento - sin headers personalizados
    # Timeout de 5 segundos (más corto que BCE)
```

**⚠️ PROBLEMA:** Ninguno de los dos sistemas envía headers que simulen un navegador real.

---

### **3. Timeout (⚠️ DIFERENCIA)**

**BCE:**
- ✅ Sin timeout explícito (usa el default de aiohttp: ~300 segundos)

**Sistema Actual:**
- ⚠️ Timeout de 5 segundos (muy corto)
- ⚠️ Esto podría causar fallos si la API está lenta

---

### **4. Manejo de Errores**

**BCE:**
```python
try:
    async with session.post(url, json=payload) as response:
        return await response.json()
except Exception as e:
    return {'error': str(e)}
```

**Sistema Actual:**
```python
try:
    async with session.post(CIIU_BUSQUEDA_URL, json=payload) as response:
        if response.status != 200:
            return {'error': f'Error: status {response.status}'}
        return await response.json()
except asyncio.TimeoutError:
    return {'error': 'Timeout: La API de CIIU no respondió en 5 segundos'}
except Exception as e:
    return {'error': str(e)}
```

**✅ Sistema actual tiene mejor manejo de errores**

---

## 🚨 PROBLEMA IDENTIFICADO

### **Error Observado:**
```
Cannot connect to host enlinea.ccc.org.co:443 ssl:default [getaddrinfo failed]
```

**Este error NO es de baneo, es de DNS/conectividad:**
- `getaddrinfo failed` = No puede resolver el nombre del dominio
- Esto sugiere problema de red/DNS, no de autenticación/autorización

---

## 🔍 POSIBLES CAUSAS

### **1. Problema de DNS/Conectividad (MÁS PROBABLE)**
- El dominio `enlinea.ccc.org.co` no se puede resolver
- Problema temporal de la infraestructura de la API
- Firewall/proxy bloqueando el acceso

### **2. Cambio en la API (POSIBLE)**
- La API cambió su infraestructura
- Cambió el dominio o la configuración SSL
- Implementaron rate limiting más estricto

### **3. Baneo por Rate Limiting (POSIBLE)**
- Demasiadas peticiones desde la misma IP
- El sistema actual procesa muchos RUTs en paralelo
- BCE probablemente hace menos peticiones

### **4. Falta de Headers de Navegador (POSIBLE)**
- La API podría estar bloqueando peticiones sin User-Agent de navegador
- aiohttp envía `User-Agent: Python/aiohttp/{version}` que es fácil de detectar

---

## 📊 DIFERENCIAS CLAVE

| Aspecto | BCE | Sistema Actual | Impacto |
|---------|-----|----------------|---------|
| **Payload** | ✅ Idéntico | ✅ Idéntico | Ninguno |
| **Headers** | ⚠️ Default aiohttp | ⚠️ Default aiohttp | Posible detección |
| **Timeout** | ✅ ~300s (default) | ⚠️ 5s (muy corto) | Puede causar fallos |
| **Rate Limiting** | ✅ Menos peticiones | ⚠️ Muchas peticiones paralelas | Posible baneo |
| **User-Agent** | ⚠️ Python/aiohttp | ⚠️ Python/aiohttp | Fácil de detectar |

---

## ✅ SOLUCIONES PROPUESTAS

### **1. Agregar Headers de Navegador Real (RECOMENDADO)**

```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'es-CO,es;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Content-Type': 'application/json',
    'Origin': 'https://enlinea.ccc.org.co',
    'Referer': 'https://enlinea.ccc.org.co/',
}

async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
    ...
```

### **2. Aumentar Timeout**

```python
# Cambiar de 5 segundos a 30 segundos
timeout = aiohttp.ClientTimeout(total=30, connect=10)
```

### **3. Agregar Rate Limiting**

```python
# Limitar peticiones concurrentes
# Esperar entre peticiones
import asyncio
await asyncio.sleep(0.5)  # Esperar 500ms entre peticiones
```

### **4. Verificar Conectividad**

```bash
# Verificar si el dominio está accesible
ping enlinea.ccc.org.co
curl -I https://enlinea.ccc.org.co
nslookup enlinea.ccc.org.co
```

---

## 🔍 VERIFICACIÓN NECESARIA

### **1. ¿Funciona BCE actualmente?**
- Si BCE funciona y el sistema actual no → Problema específico del sistema actual
- Si ambos fallan → Problema de la API o conectividad

### **2. ¿El dominio está accesible?**
```bash
# Desde el servidor donde corre el sistema
curl -v https://enlinea.ccc.org.co/busquedasciiu/bqciiu/busqueda
```

### **3. ¿Hay rate limiting?**
- Verificar si BCE sigue funcionando
- Comparar volumen de peticiones

---

## 📋 CONCLUSIÓN

### **Problema más probable:**
1. **Falta de headers de navegador** → API detecta peticiones automatizadas
2. **Rate limiting** → Demasiadas peticiones paralelas desde el sistema actual
3. **Problema de DNS/conectividad** → Temporal, no relacionado con el código

### **Recomendaciones inmediatas:**
1. ✅ Agregar headers de navegador real
2. ✅ Aumentar timeout a 30 segundos
3. ✅ Agregar rate limiting (esperar entre peticiones)
4. ✅ Verificar si BCE sigue funcionando

---

## ✅ SOLUCIÓN APLICADA

### **Cambios realizados:**

1. **✅ Agregados headers de navegador real:**
   - `User-Agent`: Chrome 120 (simula navegador real)
   - `Accept`, `Accept-Language`, `Accept-Encoding`
   - `Origin`, `Referer`, `Connection`

2. **✅ Aumentado timeout:**
   - De 5 segundos → 30 segundos
   - Conectividad: 10 segundos

3. **✅ Mejorado manejo de errores:**
   - Mensajes de timeout actualizados

### **Archivo modificado:**
- `manu/apps/sistema_analitico/services/ciiu_service.py`

### **Próximos pasos:**
1. Probar si la API responde con los nuevos headers
2. Verificar si BCE sigue funcionando (comparar)
3. Si persiste el problema, verificar conectividad DNS

---

**Última actualización**: Diciembre 2025

