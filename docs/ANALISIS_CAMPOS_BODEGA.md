# Análisis: Campos de Bodega y Manejo de Columnas Faltantes

## 📊 Situación Actual

### SQL que Propones:
```sql
CASE 
    WHEN B.NOMBRE LIKE '%IMP%' THEN 'IMPLANTE'
    WHEN B.NOMBRE LIKE '%EQ%' OR B.NOMBRE LIKE '%PODER%' THEN 'EQUIPO DE PODER'
    ELSE 'INSTRUMENTAL'
END AS TIPO_BODEGA,

CASE 
    WHEN B.NOMBRE LIKE '%IMP%' THEN 'IMPLANTE'
    WHEN B.NOMBRE LIKE '%EQ%' OR B.NOMBRE LIKE '%PODER%' THEN 'EQUIPO DE PODER'
    ELSE 'INSTRUMENTAL'
END AS SISTEMA_BODEGA
```

### Código Python Actual (data_manager.py líneas 329-332):
```python
tipo_bodega = str(movimiento.tipo_bodega).upper()
movimiento.es_implante = 'IMPLANTE' in tipo_bodega
movimiento.es_instrumental = 'INSTRUMENTAL' in tipo_bodega
movimiento.es_equipo_poder = 'EQUIPO' in tipo_bodega and 'PODER' in tipo_bodega
```

---

## ✅ Análisis: ¿Está Bien o Falta Algo?

### **Respuesta: ESTÁ BIEN, pero hay una INCONSISTENCIA**

#### ✅ Lo que SÍ funciona:
1. Tu SQL calcula correctamente `TIPO_BODEGA` con valores: `'IMPLANTE'`, `'EQUIPO DE PODER'`, `'INSTRUMENTAL'`
2. El código Python lee `tipo_bodega` y verifica si contiene esas palabras
3. Los booleanos se asignan correctamente

#### ⚠️ Problema Potencial:
**El código Python busca `'EQUIPO'` y `'PODER'` por separado:**
```python
movimiento.es_equipo_poder = 'EQUIPO' in tipo_bodega and 'PODER' in tipo_bodega
```

Si tu SQL retorna `'EQUIPO DE PODER'`, esto funcionará ✅ porque:
- `'EQUIPO' in 'EQUIPO DE PODER'` = `True`
- `'PODER' in 'EQUIPO DE PODER'` = `True`
- Resultado: `True and True` = `True` ✅

**PERO** hay un caso edge: si el nombre de la bodega contiene `'EQ'` pero no `'PODER'`, tu SQL retornará `'EQUIPO DE PODER'` (por el `LIKE '%EQ%'`), pero esto es correcto según tu lógica.

---

## 🔧 Recomendación: Mejorar el Código Python

### Opción 1: **Simplificar usando el valor exacto** (RECOMENDADO)

Ya que tu SQL ya calcula los valores exactos, puedes simplificar el código Python:

```python
# En lugar de buscar substrings, verificar el valor exacto
tipo_bodega = str(movimiento.tipo_bodega).upper().strip()

movimiento.es_implante = tipo_bodega == 'IMPLANTE'
movimiento.es_instrumental = tipo_bodega == 'INSTRUMENTAL'
movimiento.es_equipo_poder = tipo_bodega == 'EQUIPO DE PODER'
```

**Ventajas:**
- ✅ Más preciso (no depende de substrings)
- ✅ Más rápido
- ✅ Más claro

### Opción 2: **Mantener lógica actual pero mejorada**

Si quieres mantener la lógica de búsqueda por substring (por si hay variaciones):

```python
tipo_bodega = str(movimiento.tipo_bodega).upper().strip()

movimiento.es_implante = 'IMPLANTE' in tipo_bodega
movimiento.es_instrumental = tipo_bodega == 'INSTRUMENTAL' or ('INSTRUMENTAL' in tipo_bodega and not movimiento.es_implante and not movimiento.es_equipo_poder)
movimiento.es_equipo_poder = ('EQUIPO' in tipo_bodega and 'PODER' in tipo_bodega) or tipo_bodega == 'EQUIPO DE PODER'
```

**Ventajas:**
- ✅ Más flexible (acepta variaciones)
- ⚠️ Más complejo

---

## 📋 ¿Qué Campo Usar en el SQL?

### **Respuesta: Usa `TIPO_BODEGA`**

El código Python lee `tipo_bodega` (línea 308):
```python
tipo_bodega=fila.get('TIPO_BODEGA'),
```

Entonces en tu SQL debes usar:
```sql
CASE 
    WHEN B.NOMBRE LIKE '%IMP%' THEN 'IMPLANTE'
    WHEN B.NOMBRE LIKE '%EQ%' OR B.NOMBRE LIKE '%PODER%' THEN 'EQUIPO DE PODER'
    ELSE 'INSTRUMENTAL'
END AS TIPO_BODEGA
```

**Nota:** `SISTEMA_BODEGA` también se lee (línea 310), pero no se usa para calcular los booleanos. Se guarda directamente en el modelo.

---

## 🚨 ¿Qué Pasa si el SQL NO Incluye Algunas Columnas?

### **Respuesta: Se OMITEN (no se revienta)**

El código usa `.get()` que retorna `None` si la columna no existe:

```python
# Línea 308-311
tipo_bodega=fila.get('TIPO_BODEGA'),        # Si no existe → None
codigo_bodega=fila.get('CODIGO_BODEGA'),    # Si no existe → None
sistema_bodega=fila.get('SISTEMA_BODEGA'),  # Si no existe → None
bodega_contenedor=fila.get('BODEGA_CONTENEDOR'), # Si no existe → None
```

**Comportamiento:**
- ✅ Si la columna **existe** → Se asigna el valor
- ✅ Si la columna **NO existe** → Se asigna `None`
- ✅ El modelo acepta `None` porque los campos tienen `null=True, blank=True` (excepto `tipo_bodega` y `sistema_bodega` que son requeridos)

### ⚠️ **EXCEPCIÓN: Columnas Requeridas**

Solo estas columnas son **REQUERIDAS** (línea 263):
```python
columnas_requeridas = ['TIPO_DOCUMENTO', 'FECHA', 'ARTICULO_CODIGO', 'ARTICULO_NOMBRE', 'CANTIDAD']
```

Si alguna de estas **falta**, el proceso se detiene:
```python
if columnas_faltantes:
    print(f"❌ COLUMNAS FALTANTES: {columnas_faltantes}")
    return 0  # Se detiene, no procesa nada
```

### 📊 **Campos que Pueden Faltar (se omiten sin error):**

Todos los demás campos usan `.get()` y pueden ser `None`:
- `FECHA_ORDEN_PEDIDO` → `None` si no existe
- `LOTE` → `None` si no existe
- `STOCK_PREVIO` → `None` si no existe
- `STOCK_NUEVO` → `None` si no existe
- `PACIENTE`, `MEDICO`, `CLINICA`, etc. → `None` si no existen

---

## 🔍 Problema Potencial con `tipo_bodega`

### ⚠️ **ATENCIÓN: `tipo_bodega` es REQUERIDO en el modelo**

En el modelo (línea 140):
```python
tipo_bodega = models.CharField(max_length=100)  # ❌ NO tiene null=True
```

**Si `TIPO_BODEGA` falta en el SQL:**
- `fila.get('TIPO_BODEGA')` retorna `None`
- Se intenta crear `MovimientoInventario` con `tipo_bodega=None`
- **ERROR:** Django lanzará una excepción porque el campo es requerido

### ✅ **Solución: Asegurar que `TIPO_BODEGA` siempre esté en el SQL**

Tu SQL CASE está bien, pero asegúrate de que:
1. ✅ Siempre retorne un valor (tu CASE tiene `ELSE 'INSTRUMENTAL'` → ✅ OK)
2. ✅ El alias sea exactamente `TIPO_BODEGA` (mayúsculas)

---

## 📝 Recomendación Final

### 1. **SQL (Ya está bien):**
```sql
CASE 
    WHEN B.NOMBRE LIKE '%IMP%' THEN 'IMPLANTE'
    WHEN B.NOMBRE LIKE '%EQ%' OR B.NOMBRE LIKE '%PODER%' THEN 'EQUIPO DE PODER'
    ELSE 'INSTRUMENTAL'
END AS TIPO_BODEGA
```

### 2. **Mejorar Código Python (Opción Recomendada):**

Modificar `data_manager.py` líneas 329-332:

```python
# ANTES (actual):
tipo_bodega = str(movimiento.tipo_bodega).upper()
movimiento.es_implante = 'IMPLANTE' in tipo_bodega
movimiento.es_instrumental = 'INSTRUMENTAL' in tipo_bodega
movimiento.es_equipo_poder = 'EQUIPO' in tipo_bodega and 'PODER' in tipo_bodega

# DESPUÉS (mejorado):
if movimiento.tipo_bodega:
    tipo_bodega = str(movimiento.tipo_bodega).upper().strip()
    movimiento.es_implante = tipo_bodega == 'IMPLANTE'
    movimiento.es_instrumental = tipo_bodega == 'INSTRUMENTAL'
    movimiento.es_equipo_poder = tipo_bodega == 'EQUIPO DE PODER'
else:
    # Si no hay tipo_bodega, usar valores por defecto
    movimiento.es_implante = False
    movimiento.es_instrumental = False
    movimiento.es_equipo_poder = False
```

**Ventajas:**
- ✅ Más preciso (usa valores exactos)
- ✅ Maneja el caso de `None`
- ✅ Más eficiente

---

## ✅ Resumen

1. **Tu SQL está BIEN** ✅ - Calcula correctamente `TIPO_BODEGA`
2. **El código Python funciona** ✅ - Pero se puede mejorar para ser más preciso
3. **Columnas faltantes se omiten** ✅ - No se revienta, solo se asigna `None`
4. **`TIPO_BODEGA` es requerido** ⚠️ - Asegúrate de que siempre esté en el SQL
5. **Recomendación** 💡 - Usar comparación exacta en lugar de búsqueda por substring

