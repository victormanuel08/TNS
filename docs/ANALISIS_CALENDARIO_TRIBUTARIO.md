# Análisis del Calendario Tributario en BCE

## 📋 Resumen Ejecutivo

El calendario tributario en BCE determina las fechas de vencimiento de obligaciones tributarias basándose en:
1. **Últimos dígitos del NIT** (1 o 2 dígitos)
2. **Tipo de tercero** (Persona Natural - PN, Persona Jurídica - PJ)
3. **Régimen tributario** (Gran Contribuyente - GC, etc.)
4. **Responsabilidades tributarias** (códigos como RGC, RPJ, RPN, IVB, IVC, AEE, etc.)

---

## 🗂️ Modelos Utilizados

### 1. **Expirations** (Vigencias)
```python
class Expirations(models.Model):
    digits = models.CharField(max_length=2)  # Últimos 1 o 2 dígitos del NIT
    date = models.DateField()  # Fecha límite de la obligación
    third_types = models.ForeignKey('Third_Types', ...)  # PN o PJ
    regiments_types = models.ForeignKey('Regiments_Types', ...)  # GC, etc.
    description = models.TextField()  # Descripción de la obligación
```

**Campos clave:**
- `digits`: Puede ser "1", "2", "01", "02", "99", "00", o "" (vacío = aplica a todos)
- `date`: Fecha límite específica
- `third_types`: Filtro por tipo de tercero (opcional, null = aplica a todos)
- `regiments_types`: Filtro por régimen (opcional, null = aplica a todos)

### 2. **Tax** (Impuestos)
```python
class Tax(models.Model):
    expirations = models.ManyToManyField('Expirations', ...)  # Múltiples vigencias
    code = models.CharField(max_length=3, unique=True)  # Código único (RGC, RPJ, RPN, IVB, IVC, AEE, etc.)
    name = models.CharField(max_length=100)
    description = models.TextField()
```

**Códigos de impuestos comunes:**
- `RGC`: Retención Gran Contribuyente
- `RPJ`: Retención Persona Jurídica
- `RPN`: Retención Persona Natural
- `IVB`: IVA Bimestral
- `IVC`: IVA Cuatrimestral
- `AEE`: Otros impuestos

### 3. **Responsabilitys_Types** (Responsabilidades Tributarias)
```python
# Relación: Responsabilitys_Types -> Tax -> Expirations
# Un tercero tiene responsabilidades, cada responsabilidad tiene impuestos,
# cada impuesto tiene múltiples vigencias (expirations)
```

### 4. **Third_Types** (Tipos de Tercero)
- `PN`: Persona Natural
- `PJ`: Persona Jurídica

### 5. **Regiments_Types** (Régimen Tributario)
- `GC`: Gran Contribuyente
- `SIM`: Régimen Simple
- `ORD`: Régimen Ordinario
- `""`: Sin régimen específico (aplica a todos)

---

## 🔍 Lógica de Cálculo de Fechas

### Código en `MenuElementsCalendarView` (líneas 1402-1411):

```python
id_str = str(tercero.id_number)  # NIT como string
expirations = tax.expirations.filter(
    Q(third_types=tercero.type) | Q(third_types__isnull=True),
    Q(regiments_types=tercero.regiment) | 
    Q(regiments_types__code='GC') | 
    Q(regiments_types__isnull=True),
    Q(digits='') | Q(digits=id_str[-1:]) | Q(digits=id_str[-2:])
)
```

### Explicación de la lógica:

1. **Extrae el NIT** del tercero como string
2. **Filtra expirations** que cumplan TODAS estas condiciones:
   - **Tipo de tercero**: Coincide con el tipo del tercero O es null (aplica a todos)
   - **Régimen**: Coincide con el régimen del tercero O es 'GC' O es null (aplica a todos)
   - **Dígitos**: 
     - `digits=''` → Aplica a todos los NITs
     - `digits=id_str[-1:]` → Último dígito del NIT (ej: NIT 9008697500 → "0")
     - `digits=id_str[-2:]` → Últimos dos dígitos (ej: NIT 9008697500 → "00")

### Ejemplos:

**NIT: 9008697500**
- Último dígito: `"0"`
- Últimos dos dígitos: `"00"`
- Buscará expirations con `digits=''`, `digits='0'`, o `digits='00'`

**NIT: 132791157**
- Último dígito: `"7"`
- Últimos dos dígitos: `"57"`
- Buscará expirations con `digits=''`, `digits='7'`, o `digits='57'`

---

## 📊 Estructura de Datos en `create_expirations.py`

Cada registro tiene:
```python
{
    "tax_code": "RGC",              # Código del impuesto
    "expirations_digits": "1",      # Últimos dígitos (1 o 2 caracteres)
    "third_type_code": "PN",       # Tipo de tercero (PN o PJ)
    "regiment_type_code": "GC",    # Régimen (GC, SIM, ORD, o "" para todos)
    "date": "11/02/2025",          # Fecha límite
    "description": "Pago primera cuota"  # Descripción
}
```

### Ejemplos de datos:

```python
# Para Gran Contribuyente, Persona Natural, último dígito 1
{"tax_code": "RGC", "expirations_digits": "1", "third_type_code": "PN", 
 "regiment_type_code": "GC", "date": "11/02/2025", "description": "Pago primera cuota"}

# Para Persona Natural, últimos dos dígitos 01
{"tax_code": "RPN", "expirations_digits": "01", "third_type_code": "PN", 
 "regiment_type_code": "", "date": "12/08/2025", "description": "Declaracion y Pago"}

# Para todos los tipos (sin restricción de dígitos)
{"tax_code": "AEE", "expirations_digits": "", "third_type_code": "PN", 
 "regiment_type_code": "GC", "date": "09/04/2025", "description": ""}
```

---

## 🎯 Cómo Determinar Fechas para un NIT

### Proceso paso a paso:

1. **Obtener el NIT** del tercero (ej: `9008697500`)
2. **Obtener las responsabilidades** del RUT del tercero
3. **Para cada responsabilidad:**
   - Obtener los impuestos (Tax) asociados
   - Para cada impuesto:
     - Extraer último dígito: `"0"`
     - Extraer últimos dos dígitos: `"00"`
     - Buscar expirations que coincidan:
       - Tipo de tercero: PN o PJ (o null)
       - Régimen: GC, SIM, ORD, etc. (o null)
       - Dígitos: `""`, `"0"`, o `"00"` (o los últimos 2 dígitos si aplica)
4. **Retornar todas las fechas encontradas** con su descripción

---

## 📅 Necesidad Futura: Carga desde Excel

### Formato del Excel propuesto:

| tax_code | expirations_digits | third_type_code | regiment_type_code | date | description |
|----------|-------------------|-----------------|-------------------|------|-------------|
| RGC | 1 | PN | GC | 11/02/2025 | Pago primera cuota |
| RGC | 2 | PN | GC | 12/02/2025 | Pago primera cuota |
| RPN | 01 | PN | | 12/08/2025 | Declaracion y Pago |
| IVB | 0 | PJ | | 15/03/2025 | Declaración IVA Bimestral |

### Proceso de carga:

1. **Leer Excel** con pandas o openpyxl
2. **Validar datos:**
   - `tax_code` debe existir en Tax
   - `third_type_code` debe ser PN o PJ (o vacío)
   - `regiment_type_code` debe existir en Regiments_Types (o vacío)
   - `date` debe ser fecha válida
   - `expirations_digits` debe ser 1 o 2 caracteres (o vacío)
3. **Crear o actualizar Expirations:**
   - Si existe (mismo tax, digits, third_types, regiments_types), actualizar fecha y descripción
   - Si no existe, crear nuevo registro
4. **Asociar Expirations a Tax** (ManyToMany)

---

## 🔗 Relaciones entre Modelos

```
Third (Tercero)
  └─> RUT
       └─> Responsabilitys_Types (Responsabilidades)
            └─> Tax (Impuestos)
                 └─> Expirations (Vigencias) [ManyToMany]
                      ├─> digits (últimos dígitos NIT)
                      ├─> date (fecha límite)
                      ├─> third_types (PN/PJ)
                      └─> regiments_types (GC/SIM/ORD)
```

---

## 💡 Puntos Clave

1. **Un impuesto puede tener múltiples vigencias** (diferentes fechas según dígitos)
2. **Los dígitos pueden ser 1 o 2 caracteres** ("1" a "9", "0", "01" a "99", "00")
3. **Un dígito vacío ("") significa que aplica a todos los NITs**
4. **Las vigencias se filtran por:**
   - Tipo de tercero (PN/PJ)
   - Régimen tributario (GC/SIM/ORD)
   - Últimos dígitos del NIT
5. **El sistema busca coincidencias en este orden:**
   - Primero: dígitos vacíos (aplica a todos)
   - Segundo: último dígito
   - Tercero: últimos dos dígitos

---

## 🚀 Implementación Futura en MANU

### Modelos necesarios:

1. **Tax** (Impuesto)
   - `code` (CharField, unique) - Código del impuesto
   - `name`, `description`

2. **Expiration** (Vigencia)
   - `digits` (CharField, max_length=2) - Últimos dígitos
   - `date` (DateField) - Fecha límite
   - `third_type_code` (CharField) - PN o PJ (opcional)
   - `regiment_type_code` (CharField) - GC, SIM, etc. (opcional)
   - `description` (TextField)
   - `tax` (ForeignKey a Tax)

3. **Relación:**
   - Tax.expirations = ManyToManyField(Expiration)

### Endpoint para cargar Excel:

- POST `/api/calendario-tributario/cargar-excel/`
- Recibe archivo Excel
- Valida y procesa datos
- Crea/actualiza Expirations
- Asocia a Tax correspondiente

---

## ✅ Conclusión

El calendario tributario funciona como un sistema de reglas que:
- **Distribuye las fechas** de vencimiento según los últimos dígitos del NIT
- **Permite personalización** por tipo de tercero y régimen
- **Requiere actualización periódica** mediante Excel con las nuevas fechas del año fiscal

La carga desde Excel es esencial porque:
- Las fechas cambian cada año
- Hay muchos impuestos y combinaciones
- Es más eficiente que cargar manualmente cientos de registros

