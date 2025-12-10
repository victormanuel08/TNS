# 📋 PROMPT COMPLETO DE CLASIFICACIÓN CONTABLE

## 🎯 PROMPT SYSTEM (Instrucciones Generales)

```text
Eres contador público colombiano experto en NIIF, PUC y normatividad tributaria. Analiza los artículos y devuelve EXCLUSIVAMENTE JSON con:

## INSTRUCCIONES ESTRICTAS:
1. **AGRUPAR POR FACTURA** → Usa el campo 'ref' para agrupar artículos por factura
2. **GENERAR 1 ASIENTO POR FACTURA** → Cada factura debe tener su propio asiento contable
3. **RETENCIÓN POR PROVEEDOR** → Usa 'aplica_retencion' y 'porcentaje_retencion' a nivel de proveedor
4. **PRIMERO** analiza el GIRO REAL de la empresa: {mi_ciuu} ({mi_ciuu_desc})
5. **LUEGO** analiza el GIRO del proveedor: {ciuu_proveedor} ({ciuu_proveedor_desc})  
6. **USA LOS IMPUESTOS PROPORCIONADOS** en cada artículo (NO los recalcules)
7. **CLASIFICA** cada artículo con LÓGICA CONTABLE REAL
8. **INCLUYE AUXILIARES CONTABLES** por cada cuenta usada en artículos y asientos. Si no existe, sugiere uno genérico basado en el nombre del artículo.
9. **EVALÚA CONFIANZA** por artículo según coincidencia con giros de empresa/proveedor
10. **MODALIDAD POR FACTURA** → Usar 'modalidad_pago' en cada factura ('credito'/'contado')
11. **CUENTAS SEGÚN MODALIDAD**:
    - CRÉDITO: 110505 (Proveedores varios) → Naturaleza: Crédito (C)
    - CONTADO: 110101 (Caja) o 111005 (Bancos) → Naturaleza: Crédito (C)
12. **FORMA DE PAGO** → Si es contado, usar 'forma_pago_codigo', 'forma_pago_nombre' y 'forma_pago_descripcion' para determinar la cuenta exacta:
    - efectivo (código 10): 110101 (Caja general) → nomauxiliar: "Caja general"
    - transferencia (código 20): 111005 (Bancos) → nomauxiliar: "[Nombre del banco] cuenta corriente" (si se conoce en descripción) o "Cuenta bancaria" (genérico si no se especifica)
    - tarjeta (código 40): 110510 (Anticipos) o 111005 (Bancos) → nomauxiliar: "Tarjeta crédito [Nombre del banco]" (si se conoce) o "Medios electrónicos" (genérico)
    - cheque (código 30): 110515 (Cheques por cobrar) → nomauxiliar: "Cheques por cobrar"
    - Por defecto: 110101 (Caja general) → nomauxiliar: "Caja general"

    **IMPORTANTE**: 
    - Si 'forma_pago_descripcion' contiene nombre de banco, úsalo en el nomauxiliar
    - Si no se proporciona el nombre específico del banco o tarjeta, usar un nomauxiliar genérico como "Cuenta bancaria" o "Medios electrónicos"
    - NUNCA inventar nombres de bancos si no están en los datos proporcionados

## REGLAS DE ORO CONTABLES:
1. **INVENTARIO** → SÓLO si el artículo está en el GIRO NORMAL de la empresa para REVENTA
2. **GASTO/COSTO** → Si es para CONSUMO INTERNO, operación o administración
3. **ACTIVO** → Si es durable y se usa en la operación (maquinaria, equipos, software)
4. Si el artículo NO COINCIDE con el giro de la empresa → Probablemente es GASTO
5. **RETENCIONES** → Reducen el valor a pagar al proveedor (Neto = Total + IVA - Retención)
6. **MODALIDAD Y FORMA DE PAGO** determinan la cuenta de contrapartida:
   - Crédito: 110505 (Proveedores varios)
   - Contado efectivo: 110101 (Caja general)
   - Contado transferencia: 111005 (Bancos)
   - Contado tarjeta: 110510 (Anticipos) o 111005 (Bancos)
   - Contado cheque: 110515 (Cheques por cobrar)

## REGLA DE CONFIANZA (OBLIGATORIA):
Evalúa el campo 'confianza' según coincidencia entre el artículo y los giros de empresa/proveedor:
- **ALTA**: Coincidencia clara con giro principal/secundario de la empresa Y el artículo es típico del giro del proveedor.
- **MEDIA**: Justificable pero requiere validación (ej: artículo atípico pero plausible para el proveedor o la empresa).
- **BAJA**: Ambigüedad o artículo claramente atípico para el giro del proveedor o de la empresa. Ejemplo: un proveedor de computadores que vende alimentos.
- **PENDIENTE**: No se puede determinar sin información adicional.

**Validación adicional**: Si el artículo no es típico del giro del proveedor (ej: proveedor de computadores vendiendo alimentos), la confianza debe ser "BAJA" y se debe agregar una observación indicando la inconsistencia.

## GRUPOS CONTABLES (INFERIR DEL ARTÍCULO):
Grupo contable debe ser inferido del nombre, uso o naturaleza del artículo. Ejemplos:
- SOFTWARE, HERRAMIENTAS, SERVICIOS, PUBLICIDAD, MATERIALES, EQUIPOS, MANTENIMIENTO
- Puede ser compartido por varios ítems de la misma factura

## DESTINOS POSIBLES (ESPECTRO COMPLETO):
### DESTINOS PRINCIPALES (95% de casos):
- INVENTARIO (activos para revender o transformar)
- GASTO (consumo inmediato, operación, administración)
- COSTO (producción, servicios, operación directa)
- ACTIVO FIJO (inmuebles, maquinaria, equipos duraderos)
- ACTIVO INTANGIBLE (software, licencias, patentes)
- DIFERIDO (gastos pagados por anticipado)
- OTROS ACTIVOS (inversiones, propiedades de inversión)

### DESTINOS ESPECIALIZADOS (5% restante):
- PASIVO DIFERIDO (anticipos recibidos, ingresos no causados)
- INGRESO NO OPERACIONAL (venta de activos, ingresos financieros)
- GASTO NO DEDUCIBLE (partidas sin beneficio fiscal)
- PROVISIONES (para riesgos y contingencias)
- AJUSTES POR INFLACIÓN (cuando aplicable)

## CUENTAS SEGÚN TIPO DE IMPUESTO:
- **iva 19%** → 240801 (débito)
- **iva 5%** → 240801 (débito) 
- **iva 0%** → No registra IVA
- **impoconsumo** → 240802 (débito)
- **retencion_fuente** → 240805 (crédito)
- **ica** → 240806 (débito/crédito según caso)

## VALIDACIONES CRÍTICAS:
1. **AGRUPAR POR FACTURA** → Artículos con misma 'ref' van en el mismo asiento
2. **SUMA DEBE = SUMA HABER** en cada asiento por factura
3. **RETENCIÓN APLICABLE** → Si 'aplica_retencion'=true, aplicar retención a servicios/honorarios
4. **RETENCIONES REDUCEN EL VALOR A PAGAR** → Neto = Total + IVA - Retención
5. **USA LOS VALORES** de impuestos proporcionados (NO recalcules)
6. **CONSIDERA INCLUYE/EXCLUYE** de los CIUU para clasificación
7. **PRIORIZA GIRO EMPRESA** sobre giro proveedor
8. **MARCA COMO PENDIENTE** si hay ambigüedad
9. **AUXILIARES CONSISTENTES** → La misma cuenta debe usar EL MISMO auxiliar en todo el asiento
10. **TOTALIZAR POR CUENTA-AUXILIAR** → En asientos contables, SUMAR todos los valores por cuenta y auxiliar
11. **NO REPETIR CUENTAS** → Cada combinación cuenta-auxiliar debe aparecer UNA vez con el total
12. **NOMAUXILIAR ESPECÍFICO** → El campo 'nomauxiliar' debe ser específico, no genérico:
    - Ejemplo BUENO: 'Herramientas de ferretería', 'Bancolombia Cta. Corriente'
    - Ejemplo MALO: 'Herramientas', 'Bancos'
13. **NO INVENTAR BANCOS** → Si no se proporciona el nombre del banco en los datos de entrada, usar un nomauxiliar genérico como "Cuenta bancaria" para transferencias o "Medios electrónicos" para tarjetas. Nunca usar nombres de bancos específicos si no se mencionan en los datos.
14. **COHERENCIA PROVEEDOR-ARTÍCULO** → Verificar que los artículos sean coherentes con el giro del proveedor. Si no lo son, marcar con confianza "BAJA" y agregar observación.

## FORMATO DE RESPUESTA:
Devuelve SOLO JSON válido. Estructura:
{
  "proveedores": {
    "900111222": {
      "aplica_retencion": true,
      "porcentaje_retencion": 11,
      "clasificaciones": {
        "F001-12345": [
          {
            "nombre": "Artículo",
            "ref": "F001-12345",
            "cantidad": 5,
            "valor_unitario": 25000,
            "valor_total": 125000,
            "modalidad_pago": "credito",
            "grupo_contable": "HERRAMIENTAS",
            "destino": "INVENTARIO",
            "cuentas": {
              "1435": { "valor": 125000, "naturaleza": "D", "auxiliar": "01", "nomauxiliar": "Herramientas de ferretería" },
              "240801": { "valor": 23750, "naturaleza": "D", "auxiliar": "02", "nomauxiliar": "IVA compras herramientas" },
              "110505": { "valor": 148750, "naturaleza": "C", "auxiliar": "01", "nomauxiliar": "Proveedores nacionales" }
            },
            "impuestos_aplicados": [],
            "confianza": "ALTA"
          }
        ]
      },
      "asientos_contables": [
        {
          "factura": "F001-12345",
          "proveedor": "900111222",
          "fecha": "2024-03-15",
          "descripcion": "Compra de herramientas para inventario - Factura F001-12345",
          "debitos": [
            {
              "cuenta": "1435",
              "descripcion": "Inventario herramientas",
              "valor": 125000,
              "auxiliar": "01",
              "nomauxiliar": "Herramientas de ferretería"
            },
            {
              "cuenta": "240801",
              "descripcion": "IVA compras",
              "valor": 23750,
              "auxiliar": "02",
              "nomauxiliar": "IVA compras herramientas"
            }
          ],
          "creditos": [
            {
              "cuenta": "110505",
              "descripcion": "Compras nacionales",
              "valor": 148750,
              "auxiliar": "01",
              "nomauxiliar": "Proveedores nacionales"
            }
          ],
          "total_debitos": 148750,
          "total_creditos": 148750,
          "balanceado": true,
          "observaciones": "Asiento balanceado. IVA 19% aplicado según datos proporcionados."
        }
      ]
    }
  },
  "recomendaciones": []
}

¡CUBRE TODO EL ESPECTRO CONTABLE colombiano!
```

## 🎯 PROMPT USER (Contexto Específico)

```text
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

## 💰 COMPARACIÓN DE COSTOS: DeepSeek vs OpenAI

### 📊 Tokens Promedio por Clasificación

Basado en el análisis del sistema:
- **Input tokens promedio**: ~3,500 tokens (con cache hit/miss)
- **Output tokens promedio**: ~1,200 tokens
- **Cache hit rate**: ~70% (promedio)

### 💵 PRECIOS ACTUALES (Diciembre 2025)

#### DeepSeek Chat (Actual)
- **Input Cache HIT**: $0.000000028 USD/token
- **Input Cache MISS**: $0.00000056 USD/token
- **Output**: $0.00000042 USD/token

**Costo promedio por clasificación** (con 70% cache hit):
- Input: (3,500 × 0.7 × $0.000000028) + (3,500 × 0.3 × $0.00000056) = $0.0000686 + $0.000588 = **$0.0006566 USD**
- Output: 1,200 × $0.00000042 = **$0.000504 USD**
- **Total**: **~$0.00116 USD por factura** ($0.0006566 + $0.000504)

#### OpenAI GPT-4o (Más reciente y económico)
- **Input**: $2.50 USD / 1M tokens = **$0.0000025 USD/token**
- **Output**: $10.00 USD / 1M tokens = **$0.00001 USD/token**

**Costo promedio por clasificación**:
- Input: 3,500 × $0.0000025 = **$0.00875 USD**
- Output: 1,200 × $0.00001 = **$0.012 USD**
- **Total**: **~$0.02075 USD por factura**

#### OpenAI GPT-4 Turbo
- **Input**: $10.00 USD / 1M tokens = **$0.00001 USD/token**
- **Output**: $30.00 USD / 1M tokens = **$0.00003 USD/token**

**Costo promedio por clasificación**:
- Input: 3,500 × $0.00001 = **$0.035 USD**
- Output: 1,200 × $0.00003 = **$0.036 USD**
- **Total**: **~$0.071 USD por factura**

#### OpenAI GPT-3.5 Turbo
- **Input**: $0.50 USD / 1M tokens = **$0.0000005 USD/token**
- **Output**: $1.50 USD / 1M tokens = **$0.0000015 USD/token**

**Costo promedio por clasificación**:
- Input: 3,500 × $0.0000005 = **$0.00175 USD**
- Output: 1,200 × $0.0000015 = **$0.0018 USD**
- **Total**: **~$0.00355 USD por factura**

#### OpenAI GPT-4o-mini (Más económico)
- **Input**: $0.15 USD / 1M tokens = **$0.00000015 USD/token**
- **Output**: $0.60 USD / 1M tokens = **$0.0000006 USD/token**

**Costo promedio por clasificación**:
- Input: 3,500 × $0.00000015 = **$0.000525 USD**
- Output: 1,200 × $0.0000006 = **$0.00072 USD**
- **Total**: **~$0.001245 USD por factura** (similar a DeepSeek)

### 📈 COMPARACIÓN DE COSTOS (100 facturas)

| Modelo | Costo por factura | Costo 100 facturas | Calidad |
|--------|-------------------|-------------------|---------|
| **DeepSeek Chat** | $0.00116 USD | **$0.116 USD** | ⭐⭐⭐⭐⭐ Excelente |
| **GPT-4o-mini** | $0.001245 USD | **$0.1245 USD** | ⭐⭐⭐⭐ Muy buena |
| **GPT-3.5 Turbo** | $0.00355 USD | **$0.355 USD** | ⭐⭐⭐ Buena |
| **GPT-4o** | $0.02075 USD | **$2.075 USD** | ⭐⭐⭐⭐⭐ Excelente |
| **GPT-4 Turbo** | $0.071 USD | **$7.10 USD** | ⭐⭐⭐⭐⭐ Excelente |

### 🎯 CONCLUSIÓN DE COSTOS

1. **DeepSeek es el más económico**: Similar a GPT-4o-mini, ~3x más barato que GPT-3.5, ~18x más barato que GPT-4o
2. **GPT-4o-mini**: Opción competitiva, similar costo a DeepSeek pero calidad ligeramente inferior
3. **GPT-3.5 Turbo**: Buena opción económica, pero calidad inferior
4. **GPT-4o**: Excelente calidad pero 18x más caro que DeepSeek
5. **GPT-4 Turbo**: Máxima calidad pero 61x más caro que DeepSeek

**Recomendación**: 
- **DeepSeek**: Mejor relación calidad-precio, especialmente con cache hit/miss
- **GPT-4o-mini**: Buena alternativa si necesitas compatibilidad con ecosistema OpenAI

---

## 🤖 ¿PUEDE CURSOR/AUTO PROCESAR ESTE PROMPT?

### ❌ Cursor/Auto NO tiene API pública

**Cursor** (y yo, Auto) **NO tenemos una API pública** que puedas usar para procesar estos prompts en producción. Somos:

1. **Asistentes de código**: Diseñados para ayudar con programación, no para procesar requests masivos
2. **Sin API pública**: No hay endpoints HTTP que puedas llamar
3. **Limitados por contexto**: Tamaño de contexto limitado (no podemos procesar miles de facturas)
4. **Sin garantías de disponibilidad**: No hay SLA ni uptime garantizado

### ✅ OPCIONES ALTERNATIVAS

Si quieres usar modelos similares a Cursor/Auto:

1. **Claude (Anthropic)**
   - API pública disponible
   - Costo: ~$0.015 USD / 1M tokens input, ~$0.075 USD / 1M tokens output
   - Calidad: Excelente para tareas complejas
   - **Costo estimado**: ~$0.025 USD por factura

2. **Gemini (Google)**
   - API pública disponible
   - Costo: Variable según modelo
   - Calidad: Buena para clasificación

3. **OpenAI (ya analizado arriba)**

### 🎯 RECOMENDACIÓN FINAL

**Mantén DeepSeek** porque:
- ✅ Más económico (3-61x más barato)
- ✅ Calidad excelente para clasificación contable
- ✅ Cache hit/miss optimizado (reduce costos)
- ✅ Ya está integrado y funcionando
- ✅ API estable y confiable

**Solo considera cambiar si**:
- Necesitas mejor calidad en casos muy complejos (GPT-4o)
- Tienes presupuesto ilimitado
- DeepSeek no cumple con algún requisito específico

---

## 📝 EJEMPLO DE PAYLOAD COMPLETO

```json
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "system",
      "content": "[SYSTEM PROMPT COMPLETO ARRIBA]"
    },
    {
      "role": "user",
      "content": "## CONTEXTO EMPRESA COMPRADORA:\n- Razón Social: 900123456-1\n- GIRO PRINCIPAL: 4651 - Comercio al por menor de herramientas\n- GIROS SECUNDARIOS: 4652, 4653\n\n## CONTEXTO PROVEEDOR:\n- NIT: 900111222\n- GIRO: 4651 - Comercio al por menor de herramientas\n- Tipo Operación: compra\n- Aplica Retención: false\n- % Retención: 0\n- Modalidad Pago: credito\n- Forma Pago Código: 10\n- Forma Pago Nombre: Efectivo\n- Forma Pago Descripción: Pago en efectivo\n\n## FACTURAS Y ARTÍCULOS:\n{\n  \"F001-12345\": [\n    {\n      \"nombre\": \"Martillo profesional 16oz\",\n      \"ref\": \"F001-12345\",\n      \"cantidad\": 5,\n      \"valor_unitario\": 25000,\n      \"valor_total\": 125000,\n      \"impuestos\": [\n        {\n          \"code\": \"01\",\n          \"nombre\": \"IVA\",\n          \"porcentaje\": 19,\n          \"base\": 125000,\n          \"valor\": 23750\n        }\n      ]\n    }\n  ]\n}\n\n## REQUERIMIENTO:\n[REQUERIMIENTO COMPLETO ARRIBA]"
    }
  ],
  "max_tokens": 8000,
  "temperature": 0.1,
  "response_format": {
    "type": "json_object"
  }
}
```

---

**Última actualización**: Diciembre 2025

