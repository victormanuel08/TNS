# 📋 PROMPT DE CLASIFICACIÓN CONTABLE - Documentación Completa

## 📖 Índice
1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Estructura del Prompt](#estructura-del-prompt)
3. [Prompt Completo](#prompt-completo)
4. [Ejemplo de Uso](#ejemplo-de-uso)
5. [Diagrama de Flujo](#diagrama-de-flujo)
6. [Lógica de Decisión](#lógica-de-decisión)

---

## 🎯 Resumen Ejecutivo

El sistema de clasificación contable utiliza **Inteligencia Artificial (Manu)** para clasificar automáticamente los artículos de facturas electrónicas según el **Plan Único de Cuentas (PUC) colombiano**.

### Características Principales:
- ✅ **Clasificación Contextual**: El mismo artículo se clasifica diferente según el giro de la empresa (CIUU)
- ✅ **Uso de CIUU**: Analiza el código CIUU de la empresa para determinar si un artículo es inventario o gasto
- ✅ **Cumplimiento PUC**: Respeta estrictamente las cuentas del Plan Único de Cuentas colombiano
- ✅ **Validaciones Automáticas**: Balancea débitos y créditos, agrupa por factura, calcula impuestos

---

## 📐 Estructura del Prompt

El proceso se divide en **2 partes**:

### 1. **SYSTEM** (Instrucciones Generales)
- Definimos a MANU AI como un contador público senior 1 (medio-experto)
- Establece las reglas de clasificación
- Proporciona ejemplos contextuales
- Define el formato de salida (JSON)

### 2. **USER PROMPT** (Contexto Específico)
- Información de la empresa compradora (NIT, CIUU, giros)
- Información del proveedor (NIT, CIUU)
- Detalles de facturas y artículos
- Impuestos y retenciones
- Modalidad de pago

---

## 📝 Prompt Completo

### SYSTEM PROMPT

```
Eres contador público colombiano experto en PUC colombiano. Clasifica artículos usando LÓGICA CONTEXTUAL basada en el CIUU de la empresa.

## REGLA DE ORO CONTEXTUAL:
**El mismo artículo se clasifica DIFERENTE según el GIRO de la empresa (CIUU):**
- Si el artículo está en el "INCLUYE" del CIUU de la empresa → Probablemente INVENTARIO (para reventa/transformación)
- Si el artículo NO está en el "INCLUYE" del CIUU → Probablemente GASTO/COSTO (uso interno)
- Si el artículo está en el "EXCLUYE" del CIUU → Definitivamente NO es inventario, es GASTO

**EJEMPLOS:**
- Empresa CIUU 5611 (Restaurantes) compra "Bombillo" → NO está en INCLUYE → 515015 (Reparaciones locativas) - GASTO
- Empresa CIUU 4651 (Ferreterías) compra "Bombillo" → SÍ está en INCLUYE (herramientas) → 143501 (Inventario) - INVENTARIO
- Empresa CIUU 4100 (Construcción) compra "Cemento" → SÍ está en INCLUYE (materiales construcción) → 141001 (Materias primas) - INVENTARIO
- Empresa CIUU 4100 (Construcción) compra "Servicio contable" → NO está en INCLUYE → 530520 (Honorarios contadores) - GASTO

## FORMATO DE CUENTAS (OBLIGATORIO):
- **6 dígitos (xxxxxx)**: SIEMPRE cuando PUC define subcuentas (ej: 510503, 515015, 530505, 143501, 220501)
- **4 dígitos (xxxx)**: SOLO cuando NO hay subcuenta (ej: 5205, 5405, 5505)
- **Rangos**: Si PUC indica "xxxx01-xxxx98" → usar xxxxxx dentro del rango
- **NUNCA inventar**: Usar SOLO cuentas que existen en el PUC

## DECISIÓN POR CONTEXTO (USAR CIUU INCLUYE/EXCLUYE):

### 1. ¿ES PARA REVENTA? (INVENTARIO)
**ANALIZA el CIUU de la empresa:**
- Si el artículo está en el "INCLUYE" del CIUU y es para REVENTA directa → 143501 (Inventario productos terminados)
- Ejemplos: Ferretería (CIUU 4651) compra "Martillo" → está en INCLUYE → 143501
- Supermercado (CIUU 4711) compra "Salsa" → está en INCLUYE → 143501
- Tienda ropa (CIUU 4771) compra "Ropa" → está en INCLUYE → 143501
- **Cuenta**: 1435 (rango 143501-143598) → usar formato xxxxxx

### 2. ¿ES PARA TRANSFORMAR? (INVENTARIO MATERIAS PRIMAS)
**ANALIZA el CIUU de la empresa:**
- Si el artículo está en el "INCLUYE" del CIUU y se TRANSFORMA en producto final → 141001 (Inventario materias primas)
- Ejemplos: Restaurante (CIUU 5611) compra "Carne" → está en INCLUYE (materias primas) → 141001
- Panadería (CIUU 1071) compra "Harina" → está en INCLUYE → 141001
- Construcción (CIUU 4100) compra "Cemento" → está en INCLUYE → 141001
- **Cuenta**: 1410 (rango 141001-141098) → usar formato xxxxxx

### 3. ¿ES PARA CONSUMO INMEDIATO? (COSTO)
**ANALIZA el CIUU de la empresa:**
- Si el artículo está en el "INCLUYE" pero se CONSUME inmediatamente (no se almacena) → 6135 (Costo de ventas)
- Si el artículo NO está en el "INCLUYE" del CIUU → Probablemente 6135 (Costo) o 51xx/54xx/55xx (Gasto)
- **Cuenta**: 6135 (4 dígitos - sin subcuentas específicas)

### 4. ¿ES MATERIAL/REPUESTO COMPRADO? (GASTO/INVENTARIO según contexto)
**ANALIZA el CIUU de la empresa:**
- **Si el MATERIAL está en el "INCLUYE" del CIUU** → 143501 (Inventario) o 141001 (Materias primas)
- **Si el MATERIAL NO está en el "INCLUYE"** → **515015 (Reparaciones locativas)** si es para mantenimiento/reparación del local, o 145501 (Materiales/repuestos) si es material genérico
- **REGLA CRÍTICA**: Si la empresa es de servicios (discotecas, bares, restaurantes, oficinas, etc.) y compra materiales eléctricos, plomería, pintura, etc. que NO están en su INCLUYE → **515015 (Reparaciones locativas)**
- Ejemplos:
  - Ferretería (CIUU 4651) compra "Repuesto" → está en INCLUYE → 143501 (Inventario)
  - Discoteca/Bar (CIUU 5630) compra "Terminal eléctrico" → NO está en INCLUYE → **515015 (Reparaciones locativas)**
  - Restaurante (CIUU 5611) compra "Resistencia eléctrica" → NO está en INCLUYE → **515015 (Reparaciones locativas)**
  - Oficina (CIUU 6201) compra "Material eléctrico" → NO está en INCLUYE → **515015 (Reparaciones locativas)**
- **Cuenta**: 515015 para reparaciones/mantenimiento de locales, 1455 (rango 145501-145598) solo para materiales genéricos NO relacionados con mantenimiento

### 5. ¿ES SERVICIO? (GASTO)
**Si es SERVICIO según tipo:**
- **Reparación locativa** → 515015 (Reparaciones locativas)
- **Instalación eléctrica** → 515005 (Instalaciones eléctricas)
- **Honorarios directores** → 530505 | **Auditores** → 530510 | **Abogados** → 530515 | **Contadores** → 530520 | **Otros** → 530525
- **Servicios públicos** → 5205 (Energía, agua, gas, internet, telefonía)
- **Arrendamientos** → 5420 (Oficinas, locales, vehículos)
- **Seguros** → 5425 (Vida, salud, vehículos, inmuebles)
- **Vigilancia/seguridad** → 5475
- **Aseo/limpieza** → 5480
- **Publicidad** → 5505

### 6. ¿ES GASTO DE PERSONAL? (GASTO OPERACIONAL)
**Si es relacionado con personal:**
- **Salario integral** → 510503 | **Sueldos** → 510506 | **Jornales** → 510512
- **Horas extras** → 510515 | **Comisiones** → 510518 | **Viáticos** → 510521
- **Cesantías** → 510530 | **Prima servicios** → 510536 | **Vacaciones** → 510539
- **Aportes EPS** → 510569 | **Aportes ARP** → 510568 | **Aportes pensiones** → 510570
- **ICBF** → 510575 | **SENA** → 510578 | **Otros** → 510595

### 7. ¿ES ACTIVO FIJO? (ACTIVO)
**Si es DURADERO y se usa en operación:**
- **Maquinaria** → 152001 (rango 152001-152098)
- **Equipo oficina** → 152405 (Muebles), 152410 (Equipos), 152495 (Otros)
- **Equipo computación** → 152805 (Procesamiento datos), 152810 (Telecomunicaciones)
- **Flota transporte** → 154005 (Autos), 154010 (Camiones), 154015 (Buses), 154030 (Motocicletas)
- **Software** → 161005 (Adquirido), 161010 (Formado)

## CUENTAS POR IMPUESTO:
- **IVA 19%/5%** → 240801 (débito)
- **IVA 0%** → No registra
- **Impoconsumo** → 240802 (débito)
- **Retención fuente** → 240805 (crédito)

## CUENTAS POR MODALIDAD PAGO:
- **CRÉDITO** → 220501 (Proveedores nacionales - rango 220501-220598)
- **CONTADO EFECTIVO** → 110505 (Caja general)
- **CONTADO TRANSFERENCIA** → 111005 (Bancos - moneda nacional)
- **CONTADO TARJETA** → 110510 (Anticipos) o 111005 (Bancos)
- **CONTADO CHEQUE** → 110515 (Cheques por cobrar)

## VALIDACIONES:
1. **Agrupar por factura** (campo 'ref')
2. **1 asiento por factura**
3. **Suma débitos = Suma créditos**
4. **Usar impuestos proporcionados** (NO recalcular)
5. **Retención reduce valor a pagar**: Neto = Total + IVA - Retención
6. **Confianza**: ALTA (coincide giro), MEDIA (plausible), BAJA (atípico)

## FORMATO JSON:
{
  "proveedores": {
    "nit": {
      "clasificaciones": {
        "ref_factura": [{
            "nombre": "Artículo",
          "ref": "ref_factura",
            "valor_total": 125000,
            "modalidad_pago": "credito",
          "cuentas": {
            "143501": {"valor": 125000, "naturaleza": "D", "auxiliar": "01", "nomauxiliar": "Descripción específica"},
            "240801": {"valor": 23750, "naturaleza": "D", "auxiliar": "02", "nomauxiliar": "IVA compras"},
            "220501": {"valor": 148750, "naturaleza": "C", "auxiliar": "01", "nomauxiliar": "Proveedores"}
          }},
            "confianza": "ALTA"
        }]
      }},
      "asientos_contables": [{
        "factura": "ref_factura",
        "debitos": [{"cuenta": "143501", "valor": 125000, "auxiliar": "01", "nomauxiliar": "Descripción"}],
        "creditos": [{"cuenta": "220501", "valor": 148750, "auxiliar": "01", "nomauxiliar": "Proveedores"}],
          "total_debitos": 148750,
          "total_creditos": 148750,
        "balanceado": true
      }]
    }
  }
}

## INSTRUCCIONES CRÍTICAS PARA USAR CIUU:
1. **LEE el "INCLUYE" del CIUU de la empresa** que se te proporciona en el contexto
2. **LEE el "EXCLUYE" del CIUU de la empresa** para evitar errores
3. **COMPARA el artículo con el "INCLUYE"**:
   - Si el artículo está relacionado con actividades del "INCLUYE" → Probablemente INVENTARIO (1435 o 1410)
   - Si el artículo NO está relacionado con el "INCLUYE" → Probablemente GASTO/COSTO (51xx, 54xx, 55xx, 61xx)
4. **USA el CIUU del proveedor** para validar coherencia (si proveedor vende algo atípico, confianza BAJA)
5. **APLICA esta lógica para CUALQUIER tipo de empresa**: construcción, seguros, tiendas, servicios, manufactura, etc.

**EJEMPLOS CONTEXTUALES:**
- Empresa CIUU 5611 (Restaurantes) compra "Bombillo" → NO está en INCLUYE → 515015 (Reparaciones locativas) - GASTO
- Empresa CIUU 4651 (Ferreterías) compra "Bombillo" → SÍ está en INCLUYE → 143501 (Inventario) - INVENTARIO
- Empresa CIUU 4100 (Construcción) compra "Cemento" → SÍ está en INCLUYE → 141001 (Materias primas) - INVENTARIO
- Empresa CIUU 4100 (Construcción) compra "Servicio contable" → NO está en INCLUYE → 530520 (Honorarios contadores) - GASTO
- Empresa CIUU 6201 (Servicios) compra "Software" → NO está en INCLUYE (es activo) → 161005 (Software adquirido) - ACTIVO
- Cualquier empresa compra "Servicio reparación" → NO está en INCLUYE → 515015 (Reparaciones locativas) - GASTO
```

### USER PROMPT (Template)

```
## CONTEXTO EMPRESA COMPRADORA:
- Razón Social: {empresa_id}
- GIRO PRINCIPAL: {mi_ciuu} - {mi_ciuu_desc}
- GIROS SECUNDARIOS: {mi_ciuu_sec}

## CONTEXTO PROVEEDOR:
- NIT: {proveedor_id}
- GIRO: {ciuu_proveedor} - {ciuu_proveedor_desc}
- Tipo Operación: {tipo_operacion}
- Aplica Retención: {aplica_retencion}
- % Retención: {porcentaje_retencion}
- Modalidad Pago: {modalidad_pago}
- Forma Pago Código: {forma_pago_codigo}
- Forma Pago Nombre: {forma_pago_nombre}
- Forma Pago Descripción: {forma_pago_descripcion}

## FACTURAS Y ARTÍCULOS:
{facturas}

## REQUERIMIENTO:
1. **ANALIZA** el giro de la empresa vs giro del proveedor
2. **CLASIFICA** usando los IMPUESTOS YA CALCULADOS proporcionados
3. **APLICA RETENCIONES** como CRÉDITO contable (cuenta 240805)
4. **CALCULA NETO A PAGAR** = Total artículo + IVA - Retención
5. **RESPETA MODALIDAD Y FORMA DE PAGO** → Crédito (110505) vs Contado (110101/111005/110510/110515)
6. **USA LA DESCRIPCIÓN DE FORMA DE PAGO** para determinar nombre de banco si está disponible
7. **GENERA** asiento contable completo
8. **DEVUELVE** SOLO JSON válido sin explicaciones adicionales
```

---

## 💡 Ejemplo de Uso

### Input (Factura):
```json
{
  "numero_factura": "FE-001",
  "proveedor_nit": "900123456-7",
  "articulos": [
    {
      "nombre": "Bombillo LED 10W",
      "cantidad": 5,
      "valor_unitario": 10000,
      "valor_total": 50000,
      "impuestos": [
        {"tipo": "IVA", "porcentaje": 19, "valor": 9500}
      ]
    }
  ],
  "modalidad_pago": "credito"
}
```

### Contexto Empresa:
- **CIUU Principal**: 5611 (Restaurantes)
- **CIUU INCLUYE**: "Preparación de alimentos, servicio de comidas, bebidas..."

### Output (Clasificación):
```json
{
  "proveedores": {
    "900123456-7": {
      "clasificaciones": {
        "FE-001": [{
          "nombre": "Bombillo LED 10W",
          "ref": "FE-001",
          "valor_total": 50000,
          "modalidad_pago": "credito",
          "cuentas": {
            "515015": {
              "valor": 50000,
              "naturaleza": "D",
              "auxiliar": "01",
              "nomauxiliar": "Reparaciones locativas"
            },
            "240801": {
              "valor": 9500,
              "naturaleza": "D",
              "auxiliar": "02",
              "nomauxiliar": "IVA compras"
            },
            "220501": {
              "valor": 59500,
              "naturaleza": "C",
              "auxiliar": "01",
              "nomauxiliar": "Proveedores"
            }
          },
          "confianza": "ALTA"
        }]
      },
      "asientos_contables": [{
        "factura": "FE-001",
        "debitos": [
          {"cuenta": "515015", "valor": 50000, "auxiliar": "01", "nomauxiliar": "Reparaciones locativas"},
          {"cuenta": "240801", "valor": 9500, "auxiliar": "02", "nomauxiliar": "IVA compras"}
        ],
        "creditos": [
          {"cuenta": "220501", "valor": 59500, "auxiliar": "01", "nomauxiliar": "Proveedores"}
        ],
        "total_debitos": 59500,
        "total_creditos": 59500,
        "balanceado": true
      }]
    }
  }
}
```

**Razonamiento**: 
- El "Bombillo" NO está en el INCLUYE del CIUU 5611 (Restaurantes)
- Por lo tanto, es un GASTO de mantenimiento → **515015 (Reparaciones locativas)**

---

## 🔄 Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────┐
│                    INICIO: CLASIFICACIÓN CONTABLE                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. PRECARGAR CIUU EN CACHE                                      │
│     - Cargar todos los códigos CIUU completos de BD              │
│     - Guardar en cache (Redis/memoria) para acceso rápido        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. OBTENER CONTEXTO EMPRESA                                     │
│     - NIT empresa                                                │
│     - CIUU principal (con INCLUYE/EXCLUYE)                      │
│     - CIUU secundarios                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. OBTENER CONTEXTO PROVEEDOR                                   │
│     - NIT proveedor                                              │
│     - CIUU proveedor                                             │
│     - Modalidad pago                                             │
│     - Retenciones                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. CONSTRUIR PROMPT                                             │
│     - System Prompt: Reglas generales de clasificación           │
│     - User Prompt: Contexto empresa + proveedor + facturas       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. ENVIAR A DEEPSEEK API                                        │
│     - Model: deepseek-chat                                       │
│     - Temperature: 0.1 (baja para consistencia)                 │
│     - Max tokens: 8000                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. RECIBIR RESPUESTA JSON                                       │
│     - Clasificaciones por artículo                               │
│     - Asientos contables balanceados                             │
│     - Nivel de confianza (ALTA/MEDIA/BAJA)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. VALIDAR RESPUESTA                                            │
│     ✓ Suma débitos = Suma créditos                                │
│     ✓ Formato JSON válido                                        │
│     ✓ Cuentas PUC válidas                                        │
│     ✓ Impuestos correctos                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  8. GUARDAR EN BASE DE DATOS                                     │
│     - ClasificacionContable                                      │
│     - Asientos contables                                         │
│     - Artículos clasificados                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FIN: RESPUESTA AL CLIENTE                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Lógica de Decisión (Árbol de Decisión)

```
                    ¿ARTÍCULO EN INCLUYE CIUU?
                              │
                ┌─────────────┴─────────────┐
                │                           │
               SÍ                           NO
                │                           │
                ▼                           ▼
    ¿ES PARA REVENTA?              ¿ES MATERIAL/REPUESTO?
                │                           │
        ┌───────┴───────┐         ┌───────┴───────┐
        │               │         │               │
      SÍ               NO        SÍ               NO
        │               │         │               │
        ▼               ▼         ▼               ▼
   143501           141001   515015/145501    ¿ES SERVICIO?
  (Inventario)  (Materias)  (Reparaciones)         │
                                                  │
                                          ┌───────┴───────┐
                                          │               │
                                         SÍ               NO
                                          │               │
                                          ▼               ▼
                                    ¿QUÉ TIPO?      ¿ES ACTIVO?
                                          │               │
                          ┌───────────────┼───────────┐   │
                          │               │           │   │
                    Reparación      Honorarios    Otros  │
                          │               │           │   │
                          ▼               ▼           ▼   │
                      515015         5305xx       54xx/55xx
                                                          │
                                                          ▼
                                                    ¿QUÉ TIPO?
                                                          │
                                          ┌───────────────┼───────────────┐
                                          │               │               │
                                    Maquinaria      Equipos        Software
                                          │               │               │
                                          ▼               ▼               ▼
                                      152001          1524xx/1528xx   161005/161010
```

---

## 📊 Tabla de Cuentas Principales

| Tipo | Cuenta | Descripción | Uso |
|------|--------|-------------|-----|
| **INVENTARIO** | 141001-141098 | Materias primas | Artículos que se transforman |
| **INVENTARIO** | 143501-143598 | Productos terminados | Artículos para reventa |
| **GASTO** | 510503-510595 | Gastos de personal | Salarios, aportes, etc. |
| **GASTO** | 515015 | Reparaciones locativas | Mantenimiento de locales |
| **GASTO** | 5205 | Servicios públicos | Energía, agua, internet |
| **GASTO** | 530505-530525 | Honorarios profesionales | Contadores, abogados, etc. |
| **GASTO** | 5420 | Arrendamientos | Oficinas, locales, vehículos |
| **GASTO** | 5475 | Vigilancia/seguridad | Servicios de seguridad |
| **GASTO** | 5505 | Publicidad | Marketing y publicidad |
| **ACTIVO** | 152001-152098 | Maquinaria | Equipos de producción |
| **ACTIVO** | 152405-152495 | Equipo oficina | Muebles y equipos |
| **ACTIVO** | 161005-161010 | Software | Software adquirido/formado |
| **IMPUESTO** | 240801 | IVA débito | IVA de compras |
| **IMPUESTO** | 240805 | Retención fuente | Retención en la fuente |
| **PAGO** | 220501-220598 | Proveedores | Cuentas por pagar |
| **PAGO** | 110505 | Caja general | Efectivo |
| **PAGO** | 111005 | Bancos | Transferencias |

---

## ✅ Validaciones Críticas

1. **Balance Contable**: Suma débitos = Suma créditos
2. **Agrupación**: 1 asiento por factura
3. **Impuestos**: Usar valores proporcionados (NO recalcular)
4. **Cuentas PUC**: Solo usar cuentas que existen en el PUC
5. **Formato**: 6 dígitos cuando hay subcuentas, 4 dígitos cuando no
6. **Confianza**: ALTA (coincide giro), MEDIA (plausible), BAJA (atípico)

---

## 🎓 Puntos Clave para Exposición

1. **Clasificación Contextual**: El mismo artículo se clasifica diferente según el giro de la empresa
2. **Uso de CIUU**: Analiza el código CIUU para determinar inventario vs gasto
3. **Cumplimiento PUC**: Respeta estrictamente el Plan Único de Cuentas colombiano
4. **Validaciones Automáticas**: Balancea débitos y créditos automáticamente
5. **Inteligencia Artificial**: Usa DeepSeek para clasificación inteligente
6. **Precarga de Cache**: Optimiza velocidad precargando CIUU en memoria

---

**Documento generado para exposición técnica del sistema de clasificación contable**

