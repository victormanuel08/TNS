# 📋 REPORTE DE INCONSISTENCIAS: PROMPT vs MODELO PUC

**Fecha:** 2024-12-12  
**Total cuentas en prompt:** 64  
**Total cuentas en modelo PUC:** 2,620  
**Cuentas existentes:** 54  
**Cuentas no existentes:** 10  
**Inconsistencias detectadas:** 46

---

## ❌ CUENTAS QUE NO EXISTEN EN EL PUC (10)

Estas cuentas están mencionadas en el prompt pero **NO EXISTEN** en el modelo PUC:

| Código | Descripción en Prompt | Observación |
|--------|----------------------|-------------|
| **2001** | Cuenta base (rango 152001-152098) | ❌ ERROR TIPOGRÁFICO: Debería ser **1520**, no 2001 |
| **4100** | Construcción | ✅ **CORRECTO** - Es código **CIUU** usado para contexto, NO es cuenta PUC |
| **4651** | Ferreterías | ✅ **CORRECTO** - Es código **CIUU** usado para contexto, NO es cuenta PUC |
| **5420** | Arrendamientos (Oficinas, locales, vehículos) | ❌ **NO EXISTE** en el PUC - Buscar cuenta correcta |
| **5425** | Seguros (Vida, salud, vehículos, inmuebles) | ❌ **NO EXISTE** en el PUC - Buscar cuenta correcta |
| **5475** | Vigilancia/seguridad | ❌ **NO EXISTE** en el PUC - Buscar cuenta correcta |
| **5480** | Aseo/limpieza | ❌ **NO EXISTE** en el PUC - Buscar cuenta correcta |
| **5505** | Publicidad | ❌ **NO EXISTE** en el PUC - Buscar cuenta correcta |
| **5611** | Restaurantes | ✅ **CORRECTO** - Es código **CIUU** usado para contexto, NO es cuenta PUC |
| **6201** | Servicios | ✅ **CORRECTO** - Es código **CIUU** usado para contexto, NO es cuenta PUC |

**✅ ACLARACIÓN:** Los códigos 4100, 4651, 5611, 6201 son códigos **CIUU** (Clasificación Industrial Internacional Uniforme) que el prompt usa para **entender el contexto/giro de la empresa**. NO son cuentas PUC y NO deben ser validadas como tal. El prompt los usa correctamente en ejemplos como:
- "Empresa CIUU 5611 (Restaurantes) compra..."
- "Empresa CIUU 4100 (Construcción) compra..."

Estos códigos CIUU ayudan al LLM a entender el giro de la empresa y clasificar correctamente según el contexto.

---

## ⚠️ INCONSISTENCIAS GRAVES DE DESCRIPCIÓN (Errores críticos)

Estas cuentas existen pero tienen descripciones **COMPLETAMENTE INCORRECTAS** en el prompt:

### 1. **5205** - ERROR CRÍTICO
- **Prompt dice:** "Energía, agua, gas, internet, telefonía" (Servicios públicos)
- **PUC dice:** "GASTOS DE PERSONAL"
- **Problema:** El prompt asigna servicios públicos a una cuenta de gastos de personal
- **Impacto:** ❌ **CRÍTICO** - Clasificaciones incorrectas

### 2. **530505-530525** - ERROR CRÍTICO
- **530505** - Prompt: "Honorarios directores" | PUC: "GASTOS BANCARIOS"
- **530510** - Prompt: "Auditores" | PUC: "REAJUSTE MONETARIO - UPAC"
- **530515** - Prompt: "Abogados" | PUC: "COMISIONES"
- **530520** - Prompt: "Honorarios contadores" | PUC: "INTERESES"
- **530525** - Prompt: "Otros" | PUC: "DIFERENCIA EN CAMBIO"
- **Problema:** El prompt asigna honorarios profesionales a cuentas completamente diferentes
- **Impacto:** ❌ **CRÍTICO** - Todas las clasificaciones de honorarios están mal

### 3. **6135** - ERROR CRÍTICO
- **Prompt dice:** "Costo de ventas"
- **PUC dice:** "COMERCIO AL POR MAYOR Y AL POR MENOR"
- **Problema:** El prompt asigna costo de ventas a una cuenta de actividad económica
- **Impacto:** ❌ **CRÍTICO** - Clasificaciones de costos incorrectas

### 4. **110510** y **110515** - ERROR
- **110510** - Prompt: "Anticipos" | PUC: "CAJAS MENORES"
- **110515** - Prompt: "Cheques por cobrar" | PUC: "MONEDA EXTRANJERA"
- **Problema:** Descripciones incorrectas para cuentas de caja
- **Impacto:** ⚠️ **MEDIO** - Puede causar confusión en modalidades de pago

---

## ⚠️ INCONSISTENCIAS MENORES (Cuentas en rangos)

Estas cuentas están dentro de **rangos válidos** en el PUC, pero no tienen descripción individual:

| Código | Descripción en Prompt | Estado en PUC |
|--------|----------------------|---------------|
| **141001** | Materias primas | ✅ Dentro del rango 141001-141098 |
| **141098** | Límite de rango | ✅ Dentro del rango 141001-141098 |
| **143501** | Inventario | ✅ Dentro del rango 143501-143598 |
| **143598** | Límite de rango | ✅ Dentro del rango 143501-143598 |
| **145501** | Materiales/repuestos | ✅ Dentro del rango 145501-145598 |
| **145598** | Límite de rango | ✅ Dentro del rango 145501-145598 |
| **152001** | Maquinaria | ✅ Dentro del rango 152001-152098 |
| **152098** | Límite de rango | ✅ Dentro del rango 152001-152098 |
| **220501** | Proveedores nacionales | ✅ Dentro del rango 220501-220598 |
| **240801** | IVA (débito) | ✅ Dentro del rango 240801-240898 |
| **240802** | Impoconsumo (débito) | ✅ Dentro del rango 240801-240898 |
| **240805** | Retención fuente (crédito) | ✅ Dentro del rango 240801-240898 |

**✅ NOTA:** Estas cuentas son **VÁLIDAS** porque están dentro de rangos definidos en el PUC. El prompt puede usarlas, pero debería aclarar que son parte de un rango.

---

## ⚠️ INCONSISTENCIAS DE NOMENCLATURA (Variaciones menores)

Estas cuentas existen y son correctas, solo tienen variaciones en la nomenclatura:

| Código | Prompt | PUC | Estado |
|--------|--------|-----|--------|
| **154005** | Autos | AUTOS, CAMIONETAS Y CAMPEROS | ✅ Correcto (más específico en PUC) |
| **154010** | Camiones | TRACTOMULAS Y REMOLQUES | ✅ Correcto (más específico en PUC) |
| **161005** | Adquirido | ADQUIRIDAS | ✅ Correcto (singular vs plural) |
| **161010** | Formado | FORMADAS | ✅ Correcto (singular vs plural) |
| **510521** | Viáticos | VIATICOS | ✅ Correcto (acento vs sin acento) |
| **510530** | Cesantías | CESANTIAS | ✅ Correcto (acento vs sin acento) |
| **510575** | ICBF | APORTES I.C.B.F. | ✅ Correcto (abreviado vs completo) |

**✅ NOTA:** Estas son variaciones menores y no afectan la funcionalidad.

---

## 📊 RESUMEN DE ACCIONES REQUERIDAS

### 🔴 CRÍTICO - Corregir inmediatamente:

1. ✅ **NO eliminar códigos CIUU** - Están correctamente usados para contexto (4100, 4651, 5611, 6201 son CIUU, no PUC)
2. **Corregir cuenta 5205** - Buscar la cuenta correcta para "Servicios públicos" (actualmente dice "GASTOS DE PERSONAL")
3. **Corregir cuentas 530505-530525** - Buscar las cuentas correctas para honorarios profesionales (actualmente tienen descripciones incorrectas)
4. **Corregir cuenta 6135** - Buscar la cuenta correcta para "Costo de ventas" (actualmente dice "COMERCIO AL POR MAYOR Y AL POR MENOR")
5. **Corregir cuentas 110510 y 110515** - Verificar descripciones correctas (actualmente dicen "CAJAS MENORES" y "MONEDA EXTRANJERA")

### ⚠️ MEDIO - Revisar y corregir:

6. **Eliminar cuentas inexistentes** (5420, 5425, 5475, 5480, 5505) o buscar sus equivalentes correctos
7. **Corregir error tipográfico** (2001 → 1520)

### ✅ BAJO - Aclarar en el prompt:

8. **Aclarar que cuentas en rangos** (141001, 143501, etc.) son válidas pero están dentro de rangos
9. **Mantener variaciones menores** de nomenclatura (son aceptables)

---

## 🎯 RECOMENDACIÓN

**ANTES DE USAR EL PROMPT EN PRODUCCIÓN:**

1. ✅ Corregir todas las inconsistencias críticas (5205, 530505-530525, 6135)
2. ✅ Eliminar códigos CIUU que se confundieron con cuentas PUC
3. ✅ Buscar las cuentas correctas para servicios públicos, honorarios y costos
4. ✅ Validar nuevamente después de las correcciones

**El prompt actual tiene errores que causarían clasificaciones contables incorrectas.**

