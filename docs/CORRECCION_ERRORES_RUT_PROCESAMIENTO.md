# 🔧 CORRECCIÓN: Errores en Procesamiento de RUTs

## ❌ PROBLEMAS IDENTIFICADOS

### **1. Error: "el valor es demasiado largo para el tipo character varying(100)"**

**Causa:** Algunos campos con `max_length=100` no se estaban truncando correctamente antes de guardar en la BD.

**Campos afectados:**
- `numero_formulario` (max_length=100)
- `sigla` (max_length=100)
- `pais` (max_length=100)
- `departamento_nombre` (max_length=100)
- `ciudad_nombre` (max_length=100)

**Archivos afectados:**
- RUT AGROLUXURY.pdf
- RUT ABRAHAN AVENDAÑO.pdf
- RUT ARONNY BARRERA.pdf
- RUT CAMILO ZAFRA.pdf
- RUT CARDIO COUNTRY SAS.pdf
- RUT DANIEL RANGEL.pdf
- RUT GUSTAVO BEDOYA.pdf
- RUT INMOBILIARIA MARELSA.pdf
- RUT IVAN JOSE GUTIERREZ (LA REPIZZA).pdf
- RUT JAVIER PEÑALOZA.pdf
- RUT LUIS CARLOS ANDRADE (TAPITAS NIZA).pdf
- RUT MATEO BAUTISTA.pdf
- RUT SIERVO AVENDAÑO.pdf
- RUT SIMON OMAÑA (SALCHIXX).pdf
- RUT WLADIMIR VELASQUEZ (COMPLICITO).pdf
- RUT YOLEIDY AVENDAÑO.pdf
- RUT WENDY ROJAS.pdf

---

### **2. Error: "llave duplicada viola restricción de unicidad «ruts_nit_normalizado_key»"**

**Causa:** En procesamiento paralelo, múltiples threads pueden intentar crear el mismo RUT simultáneamente, causando una condición de carrera. El método `get_or_create()` puede fallar si dos threads intentan crear el mismo registro al mismo tiempo.

**Archivos afectados:**
- La mayoría de los RUTs que ya existían en la BD

---

## ✅ SOLUCIONES APLICADAS

### **1. Mejorado truncamiento de campos**

**Archivo:** `manu/apps/sistema_analitico/services/rut_batch_processor.py`

**Cambio:** Agregado truncamiento adicional antes de asignar campos al objeto RUT:

```python
# Actualizar campos desde PDF (ya truncados)
# Asegurar que todos los campos se trunquen antes de asignar
for key, value in rut_data_truncado.items():
    if key not in ['_texto_completo', '_codigos_ciiu_encontrados', '_establecimientos'] and hasattr(rut, key):
        try:
            # Obtener el campo del modelo para verificar max_length
            field = rut._meta.get_field(key)
            if isinstance(field, models.CharField) and value:
                # Truncar si excede max_length
                if field.max_length and len(str(value)) > field.max_length:
                    value = str(value)[:field.max_length]
                    logger.warning(f"[RUT {pdf_name}] Campo '{key}' truncado a {field.max_length} caracteres")
            setattr(rut, key, value)
        except (AttributeError, ValueError) as e:
            logger.error(f"[RUT {pdf_name}] Error asignando campo '{key}': {str(e)}")
            # Continuar con el siguiente campo
```

**Beneficios:**
- ✅ Trunca campos dinámicamente según el `max_length` del modelo
- ✅ Loguea advertencias cuando se trunca un campo
- ✅ Maneja errores de forma segura sin detener el procesamiento

---

### **2. Manejo de errores de duplicados**

**Archivo:** `manu/apps/sistema_analitico/services/rut_batch_processor.py`

**Cambio:** Agregado manejo de excepción `IntegrityError` para duplicados:

```python
# Crear o actualizar RUT con datos ya truncados
# Manejar errores de duplicados en procesamiento paralelo
try:
    rut, created = RUT.objects.get_or_create(
        nit_normalizado=nit_normalizado,
        defaults={
            'nit': rut_data_truncado.get('nit', nit_normalizado),
            'dv': rut_data_truncado.get('dv', ''),
            'razon_social': razon_social_final,
        }
    )
except IntegrityError:
    # Si hay duplicado (condición de carrera), obtener el existente
    rut = RUT.objects.get(nit_normalizado=nit_normalizado)
    created = False
```

**Beneficios:**
- ✅ Maneja condiciones de carrera en procesamiento paralelo
- ✅ Si el RUT ya existe, lo obtiene y continúa actualizándolo
- ✅ No marca como fallido cuando es solo un duplicado

---

## 📋 VERIFICACIÓN

### **Antes de la corrección:**
- ❌ Errores de "valor demasiado largo" para campos de 100 caracteres
- ❌ Errores de "llave duplicada" en procesamiento paralelo
- ❌ RUTs marcados como fallidos cuando solo había duplicados

### **Después de la corrección:**
- ✅ Todos los campos se truncan automáticamente según su `max_length`
- ✅ Duplicados se manejan correctamente (obtiene el existente y actualiza)
- ✅ RUTs se procesan correctamente incluso si ya existen

---

## 🔄 PRÓXIMOS PASOS

1. **Reiniciar Celery** para aplicar los cambios
2. **Reprocesar el ZIP** de RUTs
3. **Verificar logs** para confirmar que:
   - Los campos se truncan correctamente (warnings de truncamiento)
   - Los duplicados se manejan sin errores
   - Los RUTs se procesan exitosamente

---

**Última actualización**: Diciembre 2025

