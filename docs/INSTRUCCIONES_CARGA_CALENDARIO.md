# Instrucciones para Carga Masiva de Calendario Tributario

## 📋 Archivos Disponibles

1. **`ejemplo_calendario_tributario.xlsx`** - Excel de ejemplo con formato correcto (solo muestra)
2. **`calendario_tributario_editable_*.xlsx`** - **⭐ RECOMENDADO**: Calendario completo exportado desde BCE, listo para editar fechas
3. **`export_bce_para_manu_*.xlsx`** - Datos base exportados desde BCE (Third_Types, Regiments_Types, Tax, etc.)

---

## 📊 Formato del Excel para Carga Masiva

### Columnas Requeridas:

| Columna | Tipo | Descripción | Ejemplos |
|---------|------|-------------|----------|
| `tax_code` | Texto | Código del impuesto | RGC, RPJ, RPN, IVB, IVC, AEE, RSA, RET |
| `expirations_digits` | Texto | Últimos dígitos del NIT | "1", "2", "01", "99", "00", "" (vacío) |
| `third_type_code` | Texto | Tipo de tercero | "PN", "PJ", "" (vacío) |
| `regiment_type_code` | Texto | Régimen tributario | "GC", "SIM", "ORD", "" (vacío) |
| `date` | Fecha | Fecha límite | "11/02/2025" o "2025-02-11" |
| `description` | Texto | Descripción de la obligación | "Pago primera cuota", "Declaración IVA" |

### Reglas de Validación:

1. **tax_code**: Debe existir previamente en la tabla `Impuesto`
2. **expirations_digits**: 
   - 1 dígito: "0" a "9"
   - 2 dígitos: "01" a "99", "00"
   - Vacío ("") = aplica a TODOS los NITs
3. **third_type_code**: 
   - "PN" = Persona Natural
   - "PJ" = Persona Jurídica
   - Vacío ("") = aplica a todos los tipos
4. **regiment_type_code**: 
   - Debe existir en `TipoRegimen` o estar vacío
   - Vacío ("") = aplica a todos los regímenes
5. **date**: Formato DD/MM/YYYY o YYYY-MM-DD

---

## 📝 Ejemplos de Datos

### Ejemplo 1: Gran Contribuyente, último dígito 1
```
tax_code: RGC
expirations_digits: 1
third_type_code: PN
regiment_type_code: GC
date: 11/02/2025
description: Pago primera cuota
```

### Ejemplo 2: Persona Natural, últimos dos dígitos 01
```
tax_code: RPN
expirations_digits: 01
third_type_code: PN
regiment_type_code: 
date: 12/08/2025
description: Declaracion y Pago
```

### Ejemplo 3: Aplica a todos los NITs
```
tax_code: AEE
expirations_digits: 
third_type_code: PN
regiment_type_code: 
date: 31/12/2025
description: Obligación general para todos
```

### Ejemplo 4: IVA Bimestral, Persona Jurídica
```
tax_code: IVB
expirations_digits: 0
third_type_code: PJ
regiment_type_code: 
date: 20/03/2025
description: Declaración IVA Bimestral
```

---

## 🚀 Proceso de Carga

1. **Preparar el Excel** siguiendo el formato del ejemplo
2. **Validar datos** antes de cargar:
   - Verificar que todos los `tax_code` existan
   - Verificar que los `regiment_type_code` existan (si no están vacíos)
   - Verificar formato de fechas
3. **Subir el Excel** desde el frontend admin o endpoint API
4. **Revisar resultados** de la carga (éxitos y errores)

---

## ⚠️ Notas Importantes

- **Un mismo impuesto puede tener múltiples fechas** según los dígitos
- **Las fechas pueden repetirse** para diferentes combinaciones
- **El sistema buscará coincidencias** en este orden:
  1. Dígitos vacíos (aplica a todos)
  2. Último dígito
  3. Últimos dos dígitos
- **Si un registro ya existe** (mismo tax, digits, third_type, regiment), se actualizará la fecha y descripción

---

## 📥 Exportar Datos desde BCE

### ⭐ Opción 1: Exportar Calendario Completo Editable (RECOMENDADO)

Este comando exporta **TODOS** los registros del calendario actual. Solo necesitas cambiar las fechas:

```bash
cd bce/backend
python manage.py exportar_calendario_editable --output-dir ../../docs
```

O para un año específico:

```bash
python manage.py exportar_calendario_editable --year 2025 --output-dir ../../docs
```

**Ventajas:**
- ✅ Contiene TODOS los registros actuales
- ✅ Solo necesitas modificar las fechas en la columna `date`
- ✅ Mantiene todas las combinaciones (tax_code, digits, third_type, regiment)
- ✅ Incluye hoja de instrucciones en el Excel

### Opción 2: Exportar Datos Base

Para exportar los datos base (tipos, regímenes, impuestos):

```bash
cd bce/backend
python manage.py exportar_datos_para_manu --format excel --output-dir ../../docs
```

Esto generará un Excel con:
- **Third_Types**: Tipos de tercero (PN, PJ)
- **Regiments_Types**: Regímenes tributarios (GC, SIM, ORD, etc.)
- **Tax**: Impuestos disponibles (RGC, RPJ, IVB, etc.)
- **Responsabilities_Types**: Responsabilidades con sus impuestos asociados
- **Expirations_Sample**: Muestra de vigencias existentes

