# 🔍 ANÁLISIS: RUTs Fallidos sin Detalles en Logs

## ❓ PROBLEMA

**"Veo muchos fallidos pero no dice por qué"**

Los logs muestran muchos RUTs fallidos pero no muestran la razón específica del fallo.

---

## 🔍 CASOS DONDE SE MARCA COMO FALLIDO

### **1. Error al extraer datos del PDF (línea 183-186)**
```python
except Exception as e:
    logger.error(f"[RUT {pdf_name}] Error al extraer datos del PDF: {str(e)}", exc_info=True)
    return {
        'tipo': 'fallido',
        'archivo': pdf_name,
        'razon': f'Error al extraer datos del PDF: {str(e)}'
    }
```
**Causas comunes:**
- PDF corrupto o dañado
- PDF protegido con contraseña
- Formato de PDF no soportado
- Error en la librería de extracción (PyPDF2/pdfplumber)

---

### **2. NIT no detectado (línea 191-195)**
```python
if not nit_normalizado:
    return {
        'tipo': 'fallido',
        'archivo': pdf_name,
        'razon': 'No se pudo detectar el NIT del PDF. Por favor, proporciona el NIT manualmente.'
    }
```
**Causas comunes:**
- El PDF no contiene texto (solo imágenes)
- El NIT está en una imagen (requiere OCR)
- El formato del PDF es diferente al esperado
- El texto del PDF está corrupto

---

### **3. Error inesperado (línea 397-402)**
```python
except Exception as e:
    return {
        'tipo': 'fallido',
        'archivo': pdf_name,
        'razon': f'Error inesperado: {str(e)}'
    }
```
**Causas comunes:**
- Error al guardar en la BD
- Error al procesar establecimientos
- Error al procesar códigos CIIU
- Error de memoria
- Error de permisos de archivo

---

## ⚠️ PROBLEMA ACTUAL: LOGGING INSUFICIENTE

### **Problema:**
El código **SÍ loguea errores** (línea 181, 265), pero:
1. Los errores se loguean con `logger.error()` pero pueden no verse si el nivel de logging no está configurado
2. El error en la línea 397-402 **NO loguea** el error completo antes de retornar
3. Los errores pueden estar en diferentes niveles (ERROR, WARNING, DEBUG)

---

## ✅ SOLUCIÓN: MEJORAR LOGGING

### **Cambios necesarios:**

1. **Agregar logging antes de retornar error inesperado:**
```python
except Exception as e:
    logger.error(f"[RUT {pdf_name}] Error inesperado: {str(e)}", exc_info=True)
    return {
        'tipo': 'fallido',
        'archivo': pdf_name,
        'razon': f'Error inesperado: {str(e)}'
    }
```

2. **Agregar logging cuando NIT no se detecta:**
```python
if not nit_normalizado:
    logger.warning(f"[RUT {pdf_name}] No se pudo detectar el NIT del PDF")
    return {
        'tipo': 'fallido',
        'archivo': pdf_name,
        'razon': 'No se pudo detectar el NIT del PDF. Por favor, proporciona el NIT manualmente.'
    }
```

3. **Mejorar el resumen final para incluir razones:**
El resumen final debería mostrar las razones de los fallidos agrupadas.

---

## 📊 CÓMO IDENTIFICAR CAUSAS ACTUALMENTE

### **1. Buscar en logs de Celery:**
```bash
# Buscar errores de RUTs
grep "RUT.*Error" celery.log
grep "RUT.*fallido" celery.log
```

### **2. Buscar por tipo de error:**
```bash
# Errores de extracción
grep "Error al extraer datos del PDF" celery.log

# NIT no detectado
grep "No se pudo detectar el NIT" celery.log

# Errores inesperados
grep "Error inesperado" celery.log
```

### **3. Verificar nivel de logging:**
El nivel de logging debe estar en `INFO` o `DEBUG` para ver todos los errores.

---

## 🔧 RECOMENDACIONES

1. **Mejorar logging:** Agregar `logger.error()` antes de todos los `return {'tipo': 'fallido'}`

2. **Agrupar razones en resumen:** El resumen final debería mostrar:
   - Total fallidos
   - Fallidos por NIT no detectado
   - Fallidos por error de extracción
   - Fallidos por error inesperado

3. **Verificar nivel de logging:** Asegurar que Celery está configurado con nivel `INFO` o `DEBUG`

---

## ✅ SOLUCIÓN APLICADA

### **1. Mejorado logging de errores:**

**Archivo:** `manu/apps/sistema_analitico/services/rut_batch_processor.py`

**Cambios:**
- ✅ Agregado `logger.warning()` cuando NIT no se detecta (línea 191)
- ✅ Agregado `logger.error()` con `exc_info=True` para errores inesperados (línea 397)

**Antes:**
```python
if not nit_normalizado:
    return {'tipo': 'fallido', ...}  # Sin logging

except Exception as e:
    return {'tipo': 'fallido', ...}  # Sin logging
```

**Después:**
```python
if not nit_normalizado:
    logger.warning(f"[RUT {pdf_name}] No se pudo detectar el NIT del PDF")
    return {'tipo': 'fallido', ...}

except Exception as e:
    logger.error(f"[RUT {pdf_name}] Error inesperado al procesar RUT: {str(e)}", exc_info=True)
    return {'tipo': 'fallido', ...}
```

---

### **2. Mejorado reporte de fallidos:**

**Archivo:** `manu/apps/sistema_analitico/services/rut_batch_processor.py` (función `generar_reporte_txt`)

**Cambios:**
- ✅ Agrupa fallidos por tipo de error
- ✅ Muestra resumen estadístico por tipo
- ✅ Organiza el detalle por categorías

**Nuevo formato del reporte:**
```
RESUMEN DE FALLIDOS POR TIPO
  NIT no detectado: 15 archivos
  Error de extracción de PDF: 8 archivos
  Error inesperado: 3 archivos

DETALLE DE RUTs FALLIDOS

--- NIT NO DETECTADO (15 archivos) ---
1. Archivo: RUT XYZ.pdf
   Razón del fallo: No se pudo detectar el NIT del PDF...
...
```

---

## 📋 CÓMO VER LOS ERRORES AHORA

### **1. En los logs de Celery:**
Ahora todos los errores se loguean con detalles completos:
```bash
# Ver errores de NIT no detectado
grep "No se pudo detectar el NIT" celery.log

# Ver errores de extracción
grep "Error al extraer datos del PDF" celery.log

# Ver errores inesperados (con stack trace)
grep "Error inesperado al procesar RUT" celery.log
```

### **2. En el reporte TXT:**
El reporte ahora agrupa los fallidos por tipo y muestra estadísticas.

### **3. En el resultado de la tarea:**
El resultado de la tarea Celery incluye `resultados['fallidos']` con la razón de cada fallo.

---

**Última actualización**: Diciembre 2025

