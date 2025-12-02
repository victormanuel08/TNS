# Exportar Datos de BCE para Migración a MANU

## 📋 Datos Necesarios

Para implementar correctamente el calendario tributario en MANU, necesitamos exportar los siguientes datos desde BCE:

### 1. **Third_Types** (Tipos de Tercero)
- `code` (ej: "PN", "PJ")
- `name` (ej: "Persona Natural", "Persona Jurídica")

### 2. **Regiments_Types** (Tipos de Régimen)
- `code` (ej: "GC", "SIM", "ORD", etc.)
- `name` (ej: "Gran Contribuyente", "Régimen Simple", etc.)
- `description` (opcional)

### 3. **Tax** (Impuestos)
- `code` (ej: "RGC", "RPJ", "RPN", "IVB", "IVC", "AEE", "RSA", "RET", etc.)
- `name` (ej: "Retención Gran Contribuyente", "IVA Bimestral", etc.)
- `description`

### 4. **Responsabilitys_Types** (Responsabilidades Tributarias)
- `code` (ej: "7", "9", "14", "42", "47", "48", "52", "55")
- `name` (ej: "Retención en la fuente", "IVA", etc.)
- `description`
- Relaciones con `Tax` (qué impuestos tiene cada responsabilidad)

---

## 🔧 Script para Exportar desde BCE

Ejecuta este comando en BCE para exportar los datos:

```python
# En Django shell de BCE: python manage.py shell
from core.models import Third_Types, Regiments_Types, Tax, Responsabilitys_Types
import json
from django.core import serializers

# 1. Exportar Third_Types
third_types = Third_Types.objects.all()
third_types_data = [{'code': t.code, 'name': t.name} for t in third_types]
print("THIRD_TYPES:", json.dumps(third_types_data, indent=2, ensure_ascii=False))

# 2. Exportar Regiments_Types
regiments = Regiments_Types.objects.all()
regiments_data = [{'code': r.code, 'name': r.name, 'description': r.description or ''} for r in regiments]
print("\nREGIMENTS_TYPES:", json.dumps(regiments_data, indent=2, ensure_ascii=False))

# 3. Exportar Tax
taxes = Tax.objects.all()
taxes_data = []
for tax in taxes:
    taxes_data.append({
        'code': tax.code,
        'name': tax.name,
        'description': tax.description or ''
    })
print("\nTAX:", json.dumps(taxes_data, indent=2, ensure_ascii=False))

# 4. Exportar Responsabilitys_Types con sus Tax
responsabilities = Responsabilitys_Types.objects.prefetch_related('tax').all()
responsabilities_data = []
for resp in responsabilities:
    taxes_codes = [t.code for t in resp.tax.all()]
    responsabilities_data.append({
        'code': resp.code,
        'name': resp.name,
        'description': resp.description or '',
        'tax_codes': taxes_codes
    })
print("\nRESPONSABILITIES_TYPES:", json.dumps(responsabilities_data, indent=2, ensure_ascii=False))
```

---

## 📊 Formato del Excel para Calendario Tributario

El Excel debe tener estas columnas:

| tax_code | expirations_digits | third_type_code | regiment_type_code | date | description |
|----------|-------------------|-----------------|-------------------|------|-------------|
| RGC | 1 | PN | GC | 11/02/2025 | Pago primera cuota |
| RGC | 2 | PN | GC | 12/02/2025 | Pago primera cuota |
| RPN | 01 | PN | | 12/08/2025 | Declaracion y Pago |
| IVB | 0 | PJ | | 15/03/2025 | Declaración IVA Bimestral |

**Notas:**
- `expirations_digits`: Puede ser "1"-"9", "0", "01"-"99", "00", o "" (vacío = todos)
- `third_type_code`: "PN" o "PJ" (o vacío = todos)
- `regiment_type_code`: "GC", "SIM", "ORD", etc. (o vacío = todos)
- `date`: Formato DD/MM/YYYY o YYYY-MM-DD

---

## ✅ Validaciones Necesarias

Al cargar el Excel, el sistema debe validar:

1. **tax_code** debe existir en la tabla `Tax`
2. **third_type_code** debe ser "PN", "PJ", o vacío
3. **regiment_type_code** debe existir en `Regiments_Types` o estar vacío
4. **date** debe ser una fecha válida
5. **expirations_digits** debe ser 1 o 2 caracteres (o vacío)

---

## 🚀 Proceso de Migración

1. **Exportar datos de BCE** usando el script
2. **Crear modelos en MANU** (Third_Types, Regiments_Types, Tax, Expiration)
3. **Cargar datos base** desde el export de BCE
4. **Cargar calendario** desde Excel
5. **Validar** que todo funcione correctamente

