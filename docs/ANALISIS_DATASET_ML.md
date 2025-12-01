# Análisis del Dataset para Modelos Predictivos

## ✅ Estado Actual: La Mayoría de Campos Están Disponibles

**Actualización:** La consulta SQL ha sido actualizada y la mayoría de campos están funcionando correctamente. Solo faltan 4 campos específicos.

## 📊 Estructura Actual de Datos

### ✅ Campos que SÍ están disponibles y funcionando:

#### 📦 Información Básica del Artículo:
- ✅ `articulo_codigo`, `articulo_nombre` - Identificación del artículo
- ✅ `cantidad` - Cantidad de la transacción
- ✅ `precio_unitario` - Precio unitario
- ✅ `valor_total` - Valor total calculado

#### 📅 Información Temporal:
- ✅ `fecha` - Fecha completa de la transacción (disponible para análisis granular)
- ✅ `periodo` (fecha truncada a mes) - Usado en agregaciones mensuales

#### 🏥 Información Médica/Clínica:
- ✅ `paciente`, `cedula_paciente` - Patrones de pacientes recurrentes
- ✅ `medico`, `cedula_medico`, `medico2`, `cedula_medico2` - Patrones por médico
- ✅ `clinica`, `nit_clinica` - Patrones por clínica
- ✅ `pagador`, `nit_pagador` - Patrones por pagador
- ✅ `procedimientos` - Información de procedimientos

#### 🌍 Información Geográfica/Operacional:
- ✅ `ciudad`, `codigo_ciudad` - Patrones geográficos de demanda
- ✅ `tipo_bodega`, `codigo_bodega`, `sistema_bodega` - Patrones por tipo de bodega
- ✅ `bodega_contenedor` - Información de contenedores

#### 📋 Información de Documentos:
- ✅ `tipo_documento` - Tipo de documento (FACTURA_VENTA, REMISION_ENTRADA, etc.)

#### 🏷️ Clasificaciones:
- ✅ `es_implante`, `es_instrumental`, `es_equipo_poder` - Clasificación médica

### ❌ Campos que FALTAN (4 campos críticos):

#### 1. **`lote`** - Código de lote del artículo
#### 2. **`fecha_orden_pedido`** - Fecha de orden de pedido (especialmente para remisiones de entrada)
#### 3. **`stock_previo`** - Nivel de inventario antes de la transacción
#### 4. **`stock_nuevo`** - Nivel de inventario después de la transacción

---

## ⚠️ Limitaciones por Campos Faltantes

### 1. **Sin Información de Lotes (`lote`)**

**Impacto en Modelos Predictivos:**
- ❌ **No puedes predecir rotación por lote específico**
  - Los modelos solo pueden predecir demanda general del artículo
  - No pueden distinguir entre diferentes lotes del mismo artículo
  
- ❌ **No puedes alertar sobre lotes próximos a vencer**
  - Sin `lote` + `fecha_vencimiento`, no hay forma de identificar qué lote específico está próximo a vencer
  - No puedes priorizar ventas de lotes más antiguos (FIFO)
  
- ❌ **No puedes optimizar compras considerando vencimientos**
  - No puedes calcular cuánto stock de cada lote queda disponible
  - No puedes determinar cuándo necesitas comprar nuevo lote antes de que se venza el actual

**Ejemplo Práctico:**
```
Artículo: "Medicamento X"
- Lote A: Vence en 30 días, Stock: 50 unidades
- Lote B: Vence en 90 días, Stock: 100 unidades

Sin `lote`: El modelo solo ve "150 unidades totales"
Con `lote`: El modelo puede predecir "priorizar venta de Lote A" y "comprar nuevo lote en 20 días"
```

### 2. **Sin Fecha de Orden de Pedido (`fecha_orden_pedido`)**

**Impacto en Modelos Predictivos:**
- ❌ **No puedes calcular lead times reales**
  - `lead_time_dias` se calcula como: `fecha_recepcion - fecha_orden_pedido`
  - Sin `fecha_orden_pedido`, no puedes calcular cuánto tiempo realmente tarda un proveedor
  
- ❌ **No puedes optimizar tiempos de reposición**
  - No puedes predecir "pedir X días antes" basado en lead times históricos
  - No puedes ajustar puntos de reorden considerando variabilidad de lead times
  
- ❌ **No puedes predecir cuándo llegará un pedido**
  - Especialmente crítico para remisiones de entrada
  - No puedes anticipar cuándo tendrás stock disponible después de hacer un pedido

**Ejemplo Práctico:**
```
Remisión de Entrada:
- Fecha recepción: 2025-01-15
- Sin fecha_orden_pedido: No sabes si el lead time fue 5, 10 o 30 días
- Con fecha_orden_pedido: Sabes que el lead time fue 10 días, puedes predecir mejor
```

### 3. **Sin Stock Previo y Nuevo (`stock_previo`, `stock_nuevo`)**

**Impacto en Modelos Predictivos:**
- ❌ **No puedes calcular rotación de inventario**
  - Rotación = `ventas_anuales / stock_promedio`
  - Sin `stock_previo`/`stock_nuevo`, no puedes calcular stock promedio real
  
- ❌ **No puedes determinar días de inventario disponible**
  - Días de inventario = `stock_actual / demanda_diaria_promedio`
  - Sin stock actual, no puedes saber cuántos días de inventario tienes
  
- ❌ **No puedes optimizar niveles de stock**
  - No puedes calcular punto de reorden: `(lead_time * demanda_diaria) + stock_seguridad`
  - No puedes determinar si tienes exceso o falta de inventario
  
- ❌ **No puedes predecir con contexto de inventario actual**
  - Los modelos solo ven "cuánto se vendió", no "cuánto había disponible"
  - No pueden ajustar predicciones considerando si había stock disponible o no

**Ejemplo Práctico:**
```
Transacción:
- Cantidad vendida: 10 unidades
- Sin stock_previo/stock_nuevo: No sabes si había 10, 100 o 1000 unidades disponibles
- Con stock_previo/stock_nuevo: 
  - Stock previo: 50 unidades
  - Stock nuevo: 40 unidades
  - Puedes calcular: rotación, días de inventario, punto de reorden
```

---

## 🎯 Qué se Puede Mejorar

### A. **Análisis de Rotación y Stock**

Si incluyes `stock_previo` y `stock_nuevo`:

```python
# Métricas que puedes calcular:
- dias_inventario = (stock_nuevo / demanda_diaria_promedio)
- rotacion_inventario = (ventas_anuales / stock_promedio)
- punto_reorden = (lead_time_dias * demanda_diaria_promedio) + stock_seguridad
- cobertura_inventario = stock_nuevo / demanda_mensual_proyectada
```

**Beneficios:**
- ✅ Predicciones más precisas considerando inventario actual
- ✅ Alertas automáticas de reposición
- ✅ Optimización de niveles de stock

### B. **Análisis por Lotes**

Si incluyes `lote`:

```python
# Métricas que puedes calcular:
- rotacion_por_lote = ventas_lote / cantidad_lote
- dias_restantes_lote = (stock_lote / demanda_diaria_promedio)
- alerta_vencimiento = fecha_vencimiento - fecha_actual < dias_umbral
```

**Beneficios:**
- ✅ Alertas de productos próximos a vencer
- ✅ Optimización FIFO/FEFO automática
- ✅ Reducción de mermas

### C. **Lead Time y Optimización de Pedidos**

Si usas `fecha_orden_pedido` y `lead_time_dias`:

```python
# Métricas que puedes calcular:
- lead_time_real = fecha_recepcion - fecha_orden_pedido
- variabilidad_lead_time = std(lead_time_real)
- stock_seguridad_ajustado = variabilidad_lead_time * demanda_promedio
```

**Beneficios:**
- ✅ Predicciones más precisas considerando tiempos reales
- ✅ Optimización de puntos de reorden
- ✅ Mejor planificación de compras

### D. **Análisis Temporal Granular**

Si usas `fecha` completa en lugar de solo mes:

```python
# Patrones adicionales:
- dia_semana = fecha.dayofweek  # Lunes=0, Domingo=6
- semana_mes = fecha.isocalendar().week % 4
- fin_de_mes = fecha.day > 25
- estacion = fecha.month // 3  # Primavera, Verano, Otoño, Invierno
```

**Beneficios:**
- ✅ Detección de patrones diarios/semanales
- ✅ Predicciones más precisas a corto plazo
- ✅ Mejor ajuste estacional

### E. **Análisis Geográfico**

Si usas `ciudad` y `tipo_bodega`:

```python
# Métricas que puedes calcular:
- demanda_por_ciudad = df.groupby(['ciudad', 'articulo']).sum()
- variabilidad_geografica = std(demanda_por_ciudad)
- optimizacion_distribucion = min(demanda - stock_por_ciudad)
```

**Beneficios:**
- ✅ Predicciones por región
- ✅ Optimización de distribución
- ✅ Detección de oportunidades regionales

---

## 📋 Recomendaciones Prioritarias

### 🚨 **CRÍTICO - Agregar los 4 Campos Faltantes:**

#### 1. **`lote`** - Código de lote del artículo
**Prioridad:** ALTA (especialmente para productos con control de lotes)

**Qué hacer:**
- Verificar si existe en `KARDEX` o `DEKARDEX` en TNS
- Si existe, agregarlo al SELECT de la consulta SQL
- Si no existe, considerar agregarlo al modelo TNS o usar un campo alternativo

**Beneficio inmediato:**
- Alertas de lotes próximos a vencer
- Optimización FIFO/FEFO
- Reducción de mermas

#### 2. **`fecha_orden_pedido`** - Fecha de orden de pedido
**Prioridad:** ALTA (especialmente para remisiones de entrada)

**Qué hacer:**
- Verificar si existe en `DOCUMENTO` o `KARDEX` en TNS
- Si existe, agregarlo al SELECT de la consulta SQL
- Si no existe, considerar usar `FECHA_PEDIDO` o campo similar

**Beneficio inmediato:**
- Cálculo de lead times reales
- Optimización de tiempos de reposición
- Mejor planificación de compras

#### 3. **`stock_previo`** y **`stock_nuevo`** - Niveles de inventario
**Prioridad:** CRÍTICA (fundamental para optimización de inventario)

**Qué hacer:**
- Verificar si existen en `KARDEX` o `DEKARDEX` en TNS
- Posibles nombres: `STOCK_ANTERIOR`, `STOCK_ACTUAL`, `CANTIDAD_ANTERIOR`, `CANTIDAD_ACTUAL`
- Si existen, agregarlos al SELECT de la consulta SQL
- Si no existen, considerar calcularlos desde movimientos anteriores

**Beneficio inmediato:**
- Cálculo de rotación de inventario
- Determinación de días de inventario disponible
- Optimización de niveles de stock
- Cálculo de puntos de reorden

---

## 🔬 Modelos que Puedes Construir AHORA (con campos disponibles)

### 1. **Modelo de Demanda Temporal** ✅
```python
# Features (YA DISPONIBLES):
- fecha (completa), mes, año, dia_semana, semana_mes
- ciudad, tipo_bodega, sistema_bodega
- articulo_codigo, articulo_nombre
- tipo_documento, cantidad, precio_unitario
# Target: cantidad (demanda futura)
```

### 2. **Modelo de Demanda por Cliente/Clínica** ✅
```python
# Features (YA DISPONIBLES):
- paciente, cedula_paciente
- medico, clinica, pagador
- ciudad, codigo_ciudad
- articulo_codigo, cantidad
# Target: cantidad (demanda por cliente/clínica)
```

### 3. **Modelo Geoespacial** ✅
```python
# Features (YA DISPONIBLES):
- ciudad, codigo_ciudad
- tipo_bodega, sistema_bodega, codigo_bodega
- demanda_historica_region
- articulo_codigo, cantidad
# Target: demanda_por_region
```

### 4. **Modelo de Demanda por Día de Semana** ✅
```python
# Features (YA DISPONIBLES):
- dia_semana, semana_mes, fin_de_mes
- mes, año, estacion
- historico_dia_semana
- articulo_codigo, cantidad
# Target: demanda_diaria
```

---

## 🚀 Modelos que Podrías Construir CON los 4 Campos Faltantes

### 1. **Modelo de Rotación de Inventario** (requiere `stock_previo`, `stock_nuevo`)
```python
# Features:
- stock_previo, stock_nuevo, stock_promedio
- rotacion_historica, dias_inventario
- lead_time_promedio (si agregas fecha_orden_pedido)
- demanda_historica, variabilidad_demanda
# Target: cantidad_optimizada_compra, punto_reorden
```

### 2. **Modelo de Vencimiento** (requiere `lote` + `fecha_vencimiento`)
```python
# Features:
- lote, dias_restantes_vencimiento
- rotacion_lote, stock_lote
- precio_unitario, categoria_articulo
# Target: riesgo_vencimiento, prioridad_venta
```

### 3. **Modelo de Lead Time** (requiere `fecha_orden_pedido`)
```python
# Features:
- fecha_orden_pedido, fecha_recepcion
- proveedor (si está disponible), tipo_articulo
- temporada, volumen_pedido
# Target: lead_time_predicho, variabilidad_lead_time
```

### 4. **Modelo de Optimización de Stock** (requiere `stock_previo`, `stock_nuevo`)
```python
# Features:
- stock_previo, stock_nuevo
- demanda_historica, variabilidad_demanda
- lead_time_promedio (si agregas fecha_orden_pedido)
- rotacion_historica
# Target: stock_optimo, punto_reorden, stock_seguridad
```

---

## ✅ Estado Actual: Consulta SQL Actualizada

**Actualización:** La consulta SQL ha sido actualizada y la mayoría de campos están funcionando correctamente. Solo faltan 4 campos específicos que no están disponibles en la consulta actual.

---

## 🎯 Conclusiones

### ¿Es Suficiente el Dataset Actual?

**Respuesta:** **CASI**, pero faltan 4 campos críticos para optimización avanzada.

### ✅ Lo que SÍ tienes (y funciona bien):

1. **Información básica del artículo** - código, nombre, cantidad, precio
2. **Información temporal completa** - fecha completa (no solo mes)
3. **Información geográfica** - ciudad, bodega, sistema de bodega
4. **Información de clientes** - paciente, médico, clínica, pagador
5. **Información de documentos** - tipo de documento
6. **Clasificaciones** - implante, instrumental, equipo de poder

**Con esto puedes construir:**
- ✅ Modelos de demanda temporal (diaria, semanal, mensual)
- ✅ Modelos de demanda por región/cliente
- ✅ Modelos de demanda por día de semana
- ✅ Modelos geoespaciales
- ✅ Predicciones básicas de demanda

### ❌ Lo que FALTA (4 campos críticos):

1. **`lote`** - Para control de lotes y vencimientos
2. **`fecha_orden_pedido`** - Para calcular lead times reales
3. **`stock_previo`** - Para calcular rotación y días de inventario
4. **`stock_nuevo`** - Para calcular rotación y días de inventario

**Sin estos campos NO puedes:**
- ❌ Optimizar niveles de stock
- ❌ Calcular puntos de reorden
- ❌ Alertar sobre lotes próximos a vencer
- ❌ Calcular lead times reales
- ❌ Optimizar tiempos de reposición

---

## 📋 Recomendaciones Específicas

### A. **Actualizar Consulta SQL de Extracción**

La consulta SQL en `EmpresaServidor.consulta_sql` debe incluir:

```sql
SELECT 
    -- Campos existentes (ya funcionan)
    D.TIPO_DOCUMENTO,
    D.FECHA,
    A.ARTICULO_CODIGO AS ARTICULO_CODIGO,
    A.ARTICULO_NOMBRE AS ARTICULO_NOMBRE,
    -- ... otros campos ...
    
    -- ✅ CAMPOS FALTANTES (agregar si existen):
    K.LOTE,                           -- ¿Existe en KARDEX?
    K.STOCK_PREVIO,                   -- ¿Existe en KARDEX?
    K.STOCK_NUEVO,                    -- ¿Existe en KARDEX?
    DOC.FECHA_ORDEN_PEDIDO,           -- ¿Existe en DOCUMENTO?
    A.FECHA_VENCIMIENTO,              -- ¿Existe en ARTICULO/MATERIAL?
    
FROM DEKARDEX D
INNER JOIN KARDEX K ON D.KARDEXID = K.KARDEXID
INNER JOIN MATERIAL A ON D.MATID = A.MATID
LEFT JOIN DOCUMENTO DOC ON K.DOCID = DOC.DOCID
WHERE K.FECHA BETWEEN ? AND ?
```

### B. **Verificar Campos Disponibles en TNS**

Necesitas verificar qué campos están disponibles:

1. **En KARDEX:**
   - ¿Existe `LOTE`?
   - ¿Existe `STOCK_ANTERIOR` o similar?
   - ¿Existe `STOCK_ACTUAL` o similar?

2. **En DOCUMENTO:**
   - ¿Existe `FECHA_ORDEN_PEDIDO` o similar?
   - ¿Existe `FECHA_PEDIDO`?

3. **En ARTICULO/MATERIAL:**
   - ¿Existe `FECHA_VENCIMIENTO` o similar?
   - ¿Existe `FECHA_VENC`?

### 📊 Resumen de Limitaciones por Campo Faltante

| Campo Faltante | Limitación Principal | Impacto en Modelos |
|----------------|---------------------|-------------------|
| **`lote`** | No puedes controlar lotes ni alertar vencimientos | Predicciones generales, sin distinción por lote |
| **`fecha_orden_pedido`** | No puedes calcular lead times reales | Predicciones sin considerar tiempos de entrega |
| **`stock_previo`** | No puedes calcular rotación ni días de inventario | Predicciones sin contexto de inventario actual |
| **`stock_nuevo`** | No puedes calcular rotación ni días de inventario | Predicciones sin contexto de inventario actual |

---

## 📝 Siguiente Paso

### Para Completar el Dataset:

1. **🔍 Verificar campos disponibles en TNS:**
   - Consultar la estructura de `KARDEX`, `DEKARDEX`, `DOCUMENTO`
   - Identificar nombres exactos de los campos:
     - `LOTE` o similar en KARDEX/DEKARDEX
     - `FECHA_ORDEN_PEDIDO` o `FECHA_PEDIDO` en DOCUMENTO/KARDEX
     - `STOCK_PREVIO`, `STOCK_ANTERIOR`, `CANTIDAD_ANTERIOR` en KARDEX/DEKARDEX
     - `STOCK_NUEVO`, `STOCK_ACTUAL`, `CANTIDAD_ACTUAL` en KARDEX/DEKARDEX

2. **📝 Actualizar consulta SQL:**
   - Agregar estos 4 campos al SELECT de `EmpresaServidor.consulta_sql`
   - Agregar JOINs necesarios si los campos están en otras tablas

3. **🧪 Re-extraer datos:**
   - Ejecutar nueva extracción para poblar estos campos
   - Verificar que los campos se estén extrayendo correctamente

4. **🔧 Actualizar código de entrenamiento:**
   - Incluir estos campos en el dataset de entrenamiento
   - Crear características derivadas (rotación, días de inventario, etc.)

---

## ✅ Conclusión Final

**Estado Actual:** El dataset está **bien estructurado** y tiene **la mayoría de campos necesarios**. Con los campos actuales puedes construir modelos predictivos funcionales para:
- Predicción de demanda temporal
- Predicción de demanda por región/cliente
- Análisis de patrones de compra

**Para optimización avanzada de inventario**, necesitas agregar los 4 campos faltantes:
- `lote` - Control de lotes
- `fecha_orden_pedido` - Lead times
- `stock_previo` y `stock_nuevo` - Rotación y optimización

**Recomendación:** Prioriza agregar `stock_previo` y `stock_nuevo` primero, ya que son fundamentales para cualquier modelo de optimización de inventario.

