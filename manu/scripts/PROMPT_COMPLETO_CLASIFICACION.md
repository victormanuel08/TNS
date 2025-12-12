# 📋 PROMPT COMPLETO DE CLASIFICACIÓN CONTABLE

Este documento contiene el prompt completo usado para la clasificación contable. Se muestra aquí para análisis y validación.

---

## SYSTEM PROMPT

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
{{
  "proveedores": {{
    "nit": {{
      "clasificaciones": {{
        "ref_factura": [{{
            "nombre": "Artículo",
          "ref": "ref_factura",
            "valor_total": 125000,
            "modalidad_pago": "credito",
          "cuentas": {{
            "143501": {{"valor": 125000, "naturaleza": "D", "auxiliar": "01", "nomauxiliar": "Descripción específica"}},
            "240801": {{"valor": 23750, "naturaleza": "D", "auxiliar": "02", "nomauxiliar": "IVA compras"}},
            "220501": {{"valor": 148750, "naturaleza": "C", "auxiliar": "01", "nomauxiliar": "Proveedores"}}
          }},
            "confianza": "ALTA"
        }}]
      }},
      "asientos_contables": [{{
        "factura": "ref_factura",
        "debitos": [{{"cuenta": "143501", "valor": 125000, "auxiliar": "01", "nomauxiliar": "Descripción"}}],
        "creditos": [{{"cuenta": "220501", "valor": 148750, "auxiliar": "01", "nomauxiliar": "Proveedores"}}],
          "total_debitos": 148750,
          "total_creditos": 148750,
        "balanceado": true
      }}]
    }}
  }}
}}

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

---

## USER PROMPT

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

## 📝 ANÁLISIS DEL PROMPT

### ✅ Uso correcto de códigos CIUU:

El prompt usa códigos CIUU (4100, 4651, 5611, 6201, 5630, 4711, 4771, 1071) para:
1. **Entender el contexto/giro de la empresa** (ej: "Empresa CIUU 5611 (Restaurantes)")
2. **Comparar artículos con el "INCLUYE" del CIUU** para decidir si es inventario o gasto
3. **Proporcionar ejemplos contextuales** al LLM

**Estos códigos CIUU NO son cuentas PUC y NO deben ser validados como tal.**

### ❌ Errores reales detectados:

1. **Cuentas PUC que NO EXISTEN:** 5420, 5425, 5475, 5480, 5505
2. **Cuentas PUC con descripciones incorrectas:** 5205, 530505-530525, 6135, 110510, 110515
3. **Error tipográfico:** 2001 debería ser 1520

---

## 📋 ANÁLISIS DETALLADO DE ERRORES

### 1. ❌ **5205** - Servicios públicos (ERROR CRÍTICO)

**Estado actual en el prompt:**
```
- **Servicios públicos** → 5205 (Energía, agua, gas, internet, telefonía)
```

**Estado real en el modelo PUC:**
- **5205**: "GASTOS DE PERSONAL" (nivel 4)
- **Problema**: El prompt asigna servicios públicos a una cuenta de gastos de personal, lo cual es completamente incorrecto.

**Cuentas correctas encontradas en el PUC:**
- **5235**: "SERVICIOS" (nivel 4) - Cuenta principal para servicios
- **523525**: "ACUEDUCTO Y ALCANTARILLADO" (nivel 6)
- **523530**: "ENERGIA ELECTRICA" (nivel 6)
- **523535**: "TELEFONO" (nivel 6)
- **523540**: "CORREO, PORTES Y TELEGRAMAS" (nivel 6)

**Cómo debe quedar:**
```
- **Servicios públicos** → 5235 (Servicios - cuenta principal) o específicamente:
  - **Acueducto y alcantarillado** → 523525
  - **Energía eléctrica** → 523530
  - **Teléfono** → 523535
  - **Correo, portes y telegramas** → 523540
```

**Por qué:** La cuenta 5205 es para "GASTOS DE PERSONAL", no para servicios públicos. Los servicios públicos están en la cuenta 5235 y sus subcuentas específicas (523525, 523530, 523535, 523540).

---

### 2. ❌ **530505-530525** - Honorarios profesionales (ERROR CRÍTICO)

**Estado actual en el prompt:**
```
- **Honorarios directores** → 530505 | **Auditores** → 530510 | **Abogados** → 530515 | **Contadores** → 530520 | **Otros** → 530525
```

**Estado real en el modelo PUC:**
- **530505**: "GASTOS BANCARIOS" (nivel 6)
- **530510**: "REAJUSTE MONETARIO - UPAC" (nivel 6)
- **530515**: "COMISIONES" (nivel 6)
- **530520**: "INTERESES" (nivel 6)
- **530525**: "DIFERENCIA EN CAMBIO" (nivel 6)
- **Problema**: Todas estas cuentas tienen descripciones completamente diferentes a honorarios profesionales.

**Cuentas correctas encontradas en el PUC:**
- **5210**: "HONORARIOS" (nivel 4) - Cuenta principal para honorarios
- **521005**: "JUNTA DIRECTIVA" (nivel 6)
- **521010**: "REVISORIA FISCAL" (nivel 6)
- **521015**: "AUDITORIA EXTERNA" (nivel 6)
- **521020**: "AVALUOS" (nivel 6)
- **521025**: "ASESORIA JURIDICA" (nivel 6) - Para abogados
- **521035**: "ASESORIA TECNICA" (nivel 6)
- **521095**: "OTROS" (nivel 6)

**También existe:**
- **5110**: "HONORARIOS" (nivel 4) - Otra cuenta de honorarios
- **511005**: "JUNTA DIRECTIVA" (nivel 6)
- **511015**: "AUDITORIA EXTERNA" (nivel 6)
- **511020**: "AVALUOS" (nivel 6)
- **511025**: "ASESORIA JURIDICA" (nivel 6)
- **511030**: "ASESORIA FINANCIERA" (nivel 6)
- **511035**: "ASESORIA TECNICA" (nivel 6)
- **511095**: "OTROS" (nivel 6)

**Cómo debe quedar:**
```
- **Honorarios profesionales** → 5210 (Honorarios - cuenta principal) o específicamente:
  - **Junta directiva** → 521005
  - **Revisoría fiscal** → 521010
  - **Auditoría externa** → 521015 (para auditores)
  - **Avalúos** → 521020
  - **Asesoría jurídica** → 521025 (para abogados)
  - **Asesoría técnica** → 521035
  - **Asesoría financiera** → 511030 (si existe en 5110xx)
  - **Otros honorarios** → 521095
```

**Por qué:** Las cuentas 530505-530525 son para gastos financieros (bancarios, intereses, comisiones, diferencias de cambio), NO para honorarios profesionales. Los honorarios están en las cuentas 5210xx o 5110xx.

---

### 3. ❌ **6135** - Costo de ventas (ERROR CRÍTICO)

**Estado actual en el prompt:**
```
- Si el artículo está en el "INCLUYE" pero se CONSUME inmediatamente (no se almacena) → 6135 (Costo de ventas)
- **Cuenta**: 6135 (4 dígitos - sin subcuentas específicas)
```

**Estado real en el modelo PUC:**
- **6135**: "COMERCIO AL POR MAYOR Y AL POR MENOR" (nivel 4)
- **Problema**: El prompt asigna "Costo de ventas" a una cuenta de actividad económica (comercio).

**Cuenta correcta encontrada en el PUC:**
- **61**: "COSTO DE VENTAS Y DE PRESTACION DE SERVICIOS" (nivel 2) - Cuenta principal
- **6105**: "AGRICULTURA, GANADERIA, CAZA Y SILVICULTURA" (nivel 4)
- **6110**: "PESCA" (nivel 4)
- **6115**: "EXPLOTACION DE MINAS Y CANTERAS" (nivel 4)
- **6120**: "INDUSTRIAS MANUFACTURERAS" (nivel 4)
- **6135**: "COMERCIO AL POR MAYOR Y AL POR MENOR" (nivel 4) - Esta es una subcuenta específica, NO el costo general

**Cómo debe quedar:**
```
- Si el artículo está en el "INCLUYE" pero se CONSUME inmediatamente (no se almacena) → 61 (Costo de ventas y de prestación de servicios) o específicamente según actividad:
  - **Comercio** → 6135 (Comercio al por mayor y al por menor)
  - **Agricultura** → 6105
  - **Pesca** → 6110
  - **Minería** → 6115
  - **Manufactura** → 6120
- **Cuenta**: 61 (nivel 2) o subcuentas específicas según actividad económica
```

**Por qué:** La cuenta 6135 es específica para "COMERCIO AL POR MAYOR Y AL POR MENOR", no es el costo de ventas general. El costo de ventas general es la cuenta 61 (nivel 2), y luego hay subcuentas específicas según la actividad económica.

---

### 4. ⚠️ **110510** y **110515** - Modalidades de pago (ERROR MEDIO)

**Estado actual en el prompt:**
```
- **CONTADO TARJETA** → 110510 (Anticipos) o 111005 (Bancos)
- **CONTADO CHEQUE** → 110515 (Cheques por cobrar)
```

**Estado real en el modelo PUC:**
- **110510**: "CAJAS MENORES" (nivel 6)
- **110515**: "MONEDA EXTRANJERA" (nivel 6)
- **Problema**: Las descripciones no coinciden con lo que el prompt dice.

**Cuentas correctas encontradas en el PUC (1105xx):**
- **110505**: "CAJA GENERAL" (nivel 6)
- **110510**: "CAJAS MENORES" (nivel 6)
- **110515**: "MONEDA EXTRANJERA" (nivel 6)

**Cómo debe quedar:**
```
- **CONTADO TARJETA** → 111005 (Bancos - moneda nacional) o 110510 (Cajas menores) si es efectivo en caja menor
- **CONTADO CHEQUE** → 111005 (Bancos - moneda nacional) - Los cheques se depositan en bancos, no en "cheques por cobrar"
```

**Por qué:** 
- **110510** es "CAJAS MENORES", no "Anticipos". Los anticipos podrían estar en otra cuenta (ej: 1705xx).
- **110515** es "MONEDA EXTRANJERA", no "Cheques por cobrar". Los cheques se depositan en bancos (111005), no hay una cuenta específica de "cheques por cobrar" en 1105xx.

---

### 5. ❌ **5420, 5425, 5475, 5480, 5505** - Cuentas que NO EXISTEN

#### 5.1. **5420** - Arrendamientos

**Estado actual en el prompt:**
```
- **Arrendamientos** → 5420 (Oficinas, locales, vehículos)
```

**Estado real en el modelo PUC:**
- **5420**: ❌ NO EXISTE

**Cuenta correcta encontrada en el PUC:**
- **5220**: "ARRENDAMIENTOS" (nivel 4) - Cuenta principal
- **415505**: "ARRENDAMIENTOS DE BIENES INMUEBLES" (nivel 6)
- **615505**: "ARRENDAMIENTOS DE BIENES INMUEBLES" (nivel 6)

**Cómo debe quedar:**
```
- **Arrendamientos** → 5220 (Arrendamientos - cuenta principal) o específicamente:
  - **Arrendamientos de bienes inmuebles** → 415505 o 615505 según contexto
```

**Por qué:** La cuenta 5420 no existe en el PUC. Los arrendamientos están en la cuenta 5220 (nivel 4).

---

#### 5.2. **5425** - Seguros

**Estado actual en el prompt:**
```
- **Seguros** → 5425 (Vida, salud, vehículos, inmuebles)
```

**Estado real en el modelo PUC:**
- **5425**: ❌ NO EXISTE

**Cuenta correcta encontrada en el PUC:**
- **5230**: "SEGUROS" (nivel 4) - Cuenta principal
- **5130**: "SEGUROS" (nivel 4) - Otra cuenta de seguros
- **520554**: "SEGUROS" (nivel 6)

**Cómo debe quedar:**
```
- **Seguros** → 5230 (Seguros - cuenta principal) o 5130 según contexto
```

**Por qué:** La cuenta 5425 no existe en el PUC. Los seguros están en la cuenta 5230 (nivel 4).

---

#### 5.3. **5475** - Vigilancia/seguridad

**Estado actual en el prompt:**
```
- **Vigilancia/seguridad** → 5475
```

**Estado real en el modelo PUC:**
- **5475**: ❌ NO EXISTE

**Cuenta correcta encontrada en el PUC:**
- **513505**: "ASEO Y VIGILANCIA" (nivel 6)
- **523505**: "ASEO Y VIGILANCIA" (nivel 6)

**Cómo debe quedar:**
```
- **Vigilancia/seguridad** → 513505 o 523505 (Aseo y vigilancia)
```

**Por qué:** La cuenta 5475 no existe en el PUC. La vigilancia está combinada con aseo en las cuentas 513505 o 523505.

---

#### 5.4. **5480** - Aseo/limpieza

**Estado actual en el prompt:**
```
- **Aseo/limpieza** → 5480
```

**Estado real en el modelo PUC:**
- **5480**: ❌ NO EXISTE

**Cuenta correcta encontrada en el PUC:**
- **513505**: "ASEO Y VIGILANCIA" (nivel 6)
- **523505**: "ASEO Y VIGILANCIA" (nivel 6)

**Cómo debe quedar:**
```
- **Aseo/limpieza** → 513505 o 523505 (Aseo y vigilancia)
```

**Por qué:** La cuenta 5480 no existe en el PUC. El aseo está combinado con vigilancia en las cuentas 513505 o 523505.

---

#### 5.5. **5505** - Publicidad

**Estado actual en el prompt:**
```
- **Publicidad** → 5505
```

**Estado real en el modelo PUC:**
- **5505**: ❌ NO EXISTE

**Cuenta correcta encontrada en el PUC:**
- **523560**: "PUBLICIDAD, PROPAGANDA Y PROMOCION" (nivel 6)
- **415555**: "PUBLICIDAD" (nivel 6)
- **615555**: "PUBLICIDAD" (nivel 6)

**Cómo debe quedar:**
```
- **Publicidad** → 523560 (Publicidad, propaganda y promoción) o 415555/615555 según contexto
```

**Por qué:** La cuenta 5505 no existe en el PUC. La publicidad está en la cuenta 523560 (nivel 6).

---

### 6. ⚠️ **2001** - Error tipográfico

**Estado actual en el prompt:**
```
- **Maquinaria** → 152001 (rango 152001-152098)
```

**Problema detectado:** En el análisis se encontró referencia a "2001" como cuenta base, pero debería ser "1520".

**Cómo debe quedar:**
```
- **Maquinaria** → 152001 (rango 152001-152098) - Cuenta base: 1520 (no 2001)
```

**Por qué:** Error tipográfico. La cuenta base es 1520, no 2001.

---

## 📝 PROMPT ORIGINAL CON SUGERENCIAS DE CORRECCIÓN

A continuación se muestra el prompt original con las correcciones sugeridas entre paréntesis en cada línea problemática:

```
### 5. ¿ES SERVICIO? (GASTO)
**Si es SERVICIO según tipo:**
- **Reparación locativa** → 515015 (Reparaciones locativas)
- **Instalación eléctrica** → 515005 (Instalaciones eléctricas)
- **Honorarios directores** → 530505 | **Auditores** → 530510 | **Abogados** → 530515 | **Contadores** → 530520 | **Otros** → 530525
  [CORRECCIÓN: → 521005 (Junta directiva) | 521015 (Auditoría externa) | 521025 (Asesoría jurídica) | 521035 (Asesoría técnica) | 521095 (Otros) - Las cuentas 530505-530525 son para gastos financieros, NO honorarios]
- **Servicios públicos** → 5205 (Energía, agua, gas, internet, telefonía)
  [CORRECCIÓN: → 5235 (Servicios) o específicamente 523525 (Acueducto), 523530 (Energía), 523535 (Teléfono) - La cuenta 5205 es "GASTOS DE PERSONAL", no servicios públicos]
- **Arrendamientos** → 5420 (Oficinas, locales, vehículos)
  [CORRECCIÓN: → 5220 (Arrendamientos) - La cuenta 5420 NO EXISTE]
- **Seguros** → 5425 (Vida, salud, vehículos, inmuebles)
  [CORRECCIÓN: → 5230 (Seguros) - La cuenta 5425 NO EXISTE]
- **Vigilancia/seguridad** → 5475
  [CORRECCIÓN: → 513505 o 523505 (Aseo y vigilancia) - La cuenta 5475 NO EXISTE]
- **Aseo/limpieza** → 5480
  [CORRECCIÓN: → 513505 o 523505 (Aseo y vigilancia) - La cuenta 5480 NO EXISTE]
- **Publicidad** → 5505
  [CORRECCIÓN: → 523560 (Publicidad, propaganda y promoción) - La cuenta 5505 NO EXISTE]

### 3. ¿ES PARA CONSUMO INMEDIATO? (COSTO)
**ANALIZA el CIUU de la empresa:**
- Si el artículo está en el "INCLUYE" pero se CONSUME inmediatamente (no se almacena) → 6135 (Costo de ventas)
  [CORRECCIÓN: → 61 (Costo de ventas y de prestación de servicios) o específicamente según actividad (ej: 6135 para comercio) - La cuenta 6135 es específica para "COMERCIO AL POR MAYOR Y AL POR MENOR", no el costo general]
- Si el artículo NO está en el "INCLUYE" del CIUU → Probablemente 6135 (Costo) o 51xx/54xx/55xx (Gasto)
  [CORRECCIÓN: → Probablemente 61 (Costo) o 51xx/52xx/53xx (Gasto) - Corregir referencia a 54xx/55xx que no existen]
- **Cuenta**: 6135 (4 dígitos - sin subcuentas específicas)
  [CORRECCIÓN: → 61 (nivel 2) con subcuentas específicas según actividad económica]

## CUENTAS POR MODALIDAD PAGO:
- **CRÉDITO** → 220501 (Proveedores nacionales - rango 220501-220598)
- **CONTADO EFECTIVO** → 110505 (Caja general)
- **CONTADO TRANSFERENCIA** → 111005 (Bancos - moneda nacional)
- **CONTADO TARJETA** → 110510 (Anticipos) o 111005 (Bancos)
  [CORRECCIÓN: → 111005 (Bancos) o 110510 (Cajas menores) si es efectivo - La cuenta 110510 es "CAJAS MENORES", no "Anticipos"]
- **CONTADO CHEQUE** → 110515 (Cheques por cobrar)
  [CORRECCIÓN: → 111005 (Bancos - moneda nacional) - Los cheques se depositan en bancos. La cuenta 110515 es "MONEDA EXTRANJERA", no "Cheques por cobrar"]
```

---

## 🎯 CONCLUSIÓN

El prompt está **bien diseñado** en cuanto al uso de códigos CIUU para contexto. Los errores están en:
- Cuentas PUC inexistentes o con descripciones incorrectas
- NO en el uso de códigos CIUU (que es correcto)

**Impacto de los errores:**
- ❌ **CRÍTICO**: Errores en 5205, 530505-530525, 6135 causarían clasificaciones completamente incorrectas
- ⚠️ **MEDIO**: Errores en 110510, 110515 causarían confusión en modalidades de pago
- ⚠️ **MEDIO**: Cuentas inexistentes (5420, 5425, 5475, 5480, 5505) causarían errores al intentar clasificar estos conceptos

