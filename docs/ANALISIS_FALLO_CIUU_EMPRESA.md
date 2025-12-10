# 🔍 ANÁLISIS: Por qué no se encontró CIUU de la Empresa

## 📋 DATOS DE LA FACTURA

**Empresa (Receptor):**
- NIT: `1005038638`
- ID: 152
- **Resultado:** ⚠️ No se encontró CIUU principal

**Proveedor (Emisor):**
- NIT: `900059238`
- Razón Social: MAKRO SUPERMAYORISTA S.A.S
- CIUU Principal: `4690` (Comercio al por mayor)
- **Resultado:** ✅ Encontrado correctamente

---

## 🔍 FLUJO DE BÚSQUEDA DE CIUU

El sistema busca CIUU en este orden:

```
1. Buscar en RUT (tabla RUT)
   ↓ (si no encuentra)
2. Buscar en Proveedor (tabla Proveedor - cache)
   ↓ (si no encuentra)
3. Consultar Cámara de Comercio (API)
   ↓ (si no encuentra)
4. Retornar None
```

**Código:** `manu/apps/sistema_analitico/services/clasificador_contable_service.py` línea 531-630

---

## ❌ ¿POR QUÉ FALLÓ?

### **Causa raíz: No existe RUT en la base de datos**

**Análisis del código:**

```python
# Línea 545: Busca RUT por NIT normalizado
rut = RUT.objects.filter(nit_normalizado=nit_normalizado).first()

if rut:
    # Extrae CIUU del RUT
    ciuu_principal = rut.actividad_principal_ciiu if hasattr(rut, 'actividad_principal_ciiu') else None
    # ...
else:
    # No encontró RUT, continúa buscando...
```

**Problema:**
1. ❌ No existe un registro en la tabla `RUT` para el NIT `1005038638`
2. ⚠️ El sistema intentó buscar en `Proveedor` (cache)
3. ⚠️ El sistema intentó consultar Cámara de Comercio (API)
4. ❌ Ninguna fuente devolvió CIUU

---

## 🔍 POSIBLES RAZONES

### **1. RUT no está registrado en la base de datos**

**Causa:**
- El RUT de la empresa nunca se subió/importó al sistema
- El RUT existe pero no se guardó en la tabla `RUT`

**Solución:**
- Subir el RUT PDF de la empresa
- O importar el RUT desde otra fuente

### **2. RUT existe pero sin CIUU**

**Causa:**
- El RUT está en la BD pero el campo `actividad_principal_ciiu` está NULL
- El RUT se importó incorrectamente

**Solución:**
- Verificar el RUT en la BD
- Re-importar el RUT si es necesario

### **3. Cámara de Comercio no devolvió datos**

**Causa:**
- La API de Cámara de Comercio falló
- El NIT no está registrado en Cámara de Comercio
- Problema de conectividad

**Solución:**
- Verificar logs de la API
- Intentar consulta manual

### **4. NIT normalizado incorrecto**

**Causa:**
- El NIT se normalizó incorrectamente
- El RUT está guardado con otro formato de NIT

**Verificación:**
```python
# NIT original: 1005038638
# NIT normalizado: 1005038638 (sin puntos ni guiones)
# Búsqueda: RUT.objects.filter(nit_normalizado='1005038638')
```

---

## 📊 IMPACTO EN LA CLASIFICACIÓN

### **¿Por qué clasificó mal?**

**Sin CIUU de empresa:**
- El sistema no sabe que eres un **restaurante**
- Asume que los alimentos son para **reventa** (inventario)
- Clasifica como `1435` (Inventario) en lugar de `6135` (Costo)

**Con CIUU de empresa (ej: 5610 - Restaurantes):**
- El sistema sabría que eres restaurante
- Clasificaría como `6135` (Costo de ventas)
- Los insumos irían a costo, no a inventario

---

## ✅ SOLUCIÓN

### **Paso 1: Verificar si existe RUT en la BD**

**Consulta SQL:**
```sql
SELECT * FROM rut WHERE nit_normalizado = '1005038638';
```

**O desde Django shell:**
```python
from apps.sistema_analitico.models import RUT
rut = RUT.objects.filter(nit_normalizado='1005038638').first()
if rut:
    print(f"RUT encontrado: {rut.razon_social}")
    print(f"CIUU Principal: {rut.actividad_principal_ciiu}")
else:
    print("RUT no encontrado")
```

### **Paso 2: Si no existe, subir/importar RUT**

**Opciones:**
1. **Subir RUT PDF** desde el frontend
2. **Importar desde API** de Cámara de Comercio
3. **Crear manualmente** en la BD

### **Paso 3: Verificar CIUU después de importar**

**Después de importar, verificar:**
```python
rut = RUT.objects.filter(nit_normalizado='1005038638').first()
if rut and rut.actividad_principal_ciiu:
    print(f"✅ CIUU encontrado: {rut.actividad_principal_ciiu}")
else:
    print("⚠️ RUT existe pero sin CIUU")
```

---

## 🔄 FLUJO CORRECTO (Después de corregir)

```
1. Factura llega con NIT empresa: 1005038638
   ↓
2. Sistema busca RUT: ✅ Encontrado
   ↓
3. Extrae CIUU: 5610 (Restaurantes)
   ↓
4. Clasifica artículos:
   - Salsa → 6135 (Costo) ✅
   - Chicharrón → 6135 (Costo) ✅
   - Impoconsumo → 240802 ✅
   ↓
5. Clasificación correcta ✅
```

---

## 📝 CONCLUSIÓN

### **Problema identificado:**

1. ❌ **No existe RUT en la BD** para el NIT `1005038638`
2. ⚠️ El sistema intentó buscar en otras fuentes pero no encontró CIUU
3. ❌ Sin CIUU, el sistema no sabe que eres restaurante
4. ❌ Clasificó incorrectamente como inventario (1435) en lugar de costo (6135)

### **Solución:**

1. ✅ **Subir/importar el RUT** de la empresa con NIT `1005038638`
2. ✅ **Verificar que el CIUU principal** esté guardado (ej: 5610 para restaurantes)
3. ✅ **Reclasificar la factura** después de tener el RUT

### **Prevención:**

- Asegurar que todas las empresas tengan RUT registrado
- Validar que el RUT tenga CIUU principal antes de clasificar
- Mostrar advertencia si falta CIUU al clasificar

---

**Última actualización**: Diciembre 2025

