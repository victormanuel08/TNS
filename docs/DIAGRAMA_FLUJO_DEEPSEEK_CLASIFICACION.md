# 📊 Diagrama de Flujo: Clasificación Contable con Deepseek

## 🎯 Resumen Ejecutivo

**¿Se envía el prompt exacto de BCE a Deepseek?**  
✅ **SÍ**, el prompt está basado en BCE (línea 16: `# ==================== PROMPTS (Basados en BCE) ====================`), pero adaptado y mejorado para MANU.

---

## 🔄 Flujo Completo de Clasificación

```
┌─────────────────────────────────────────────────────────────────┐
│                   1. PREPARACIÓN DE DATOS                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  Leer documento desde raw_data (BD)  │
        │  - Extraer TODOS los artículos       │
        │  - Cada artículo con:                │
        │    • nombre, cantidad, valores       │
        │    • impuestos (IVA, etc.)           │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  Buscar CIUU de Empresa y Proveedor  │
        │  - RUT → Cámara Comercio → Cache    │
        │  - Obtener "incluye" y "excluye"     │
        └─────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   2. CONSTRUCCIÓN DEL PROMPT                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │      SYSTEM PROMPT (Instrucciones)   │
        │  ─────────────────────────────────   │
        │  • Eres contador público experto     │
        │  • Reglas de clasificación contable  │
        │  • Formato de respuesta JSON         │
        │  • Instrucciones estrictas           │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │       USER PROMPT (Contexto)        │
        │  ─────────────────────────────────   │
        │  CONTEXTO EMPRESA:                   │
        │  • NIT: {empresa_nit}                │
        │  • GIRO PRINCIPAL: {ciuu} - {desc}   │
        │  • INCLUYE: {incluye}                │
        │  • EXCLUYE: {excluye}                 │
        │  • GIROS SECUNDARIOS: {secundarios}  │
        │                                      │
        │  CONTEXTO PROVEEDOR:                 │
        │  • NIT: {proveedor_nit}              │
        │  • GIRO: {ciuu} - {desc}             │
        │  • INCLUYE: {incluye}                │
        │  • EXCLUYE: {excluye}                 │
        │  • Aplica Retención: {sí/no}         │
        │  • % Retención: {porcentaje}         │
        │  • Modalidad Pago: {credito/contado} │
        │  • Forma Pago: {efectivo/transferencia}│
        │                                      │
        │  FACTURAS Y ARTÍCULOS:               │
        │  {JSON con TODOS los artículos}      │
        │                                      │
        │  REQUERIMIENTO:                      │
        │  • Analizar giros                    │
        │  • Clasificar artículos              │
        │  • Aplicar retenciones               │
        │  • Generar asientos contables        │
        └─────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   3. ENVÍO A DEEPSEEK API                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  POST https://api.deepseek.com/     │
        │  ─────────────────────────────────   │
        │  Headers:                            │
        │  • Authorization: Bearer {API_KEY}   │
        │  • Content-Type: application/json    │
        │                                      │
        │  Body:                               │
        │  {                                   │
        │    "model": "deepseek-chat",         │
        │    "messages": [                      │
        │      {                                │
        │        "role": "system",             │
        │        "content": "{SYSTEM_PROMPT}"  │
        │      },                               │
        │      {                                │
        │        "role": "user",                │
        │        "content": "{USER_PROMPT}"     │
        │      }                                │
        │    ],                                 │
        │    "max_tokens": 8000,                │
        │    "temperature": 0.1,               │
        │    "response_format": {               │
        │      "type": "json_object"            │
        │    }                                  │
        │  }                                   │
        └─────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   4. PROCESAMIENTO EN DEEPSEEK                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  Deepseek analiza:                   │
        │  ─────────────────────────────────   │
        │  1. Compara giro empresa vs proveedor│
        │  2. Evalúa cada artículo:            │
        │     • ¿Es para reventa? → INVENTARIO│
        │     • ¿Es para consumo? → GASTO      │
        │     • ¿Es durable? → ACTIVO          │
        │  3. Aplica impuestos proporcionados │
        │  4. Calcula retenciones              │
        │  5. Genera cuentas contables         │
        │  6. Crea asientos balanceados        │
        │  7. Evalúa confianza (ALTA/MEDIA/BAJA)│
        └─────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   5. RESPUESTA DE DEEPSEEK                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  JSON Response:                      │
        │  ─────────────────────────────────   │
        │  {                                   │
        │    "id": "chat-xxx",                 │
        │    "model": "deepseek-chat",         │
        │    "choices": [{                      │
        │      "message": {                    │
        │        "content": "{JSON_RESULTADO}" │
        │      }                                │
        │    }],                                │
        │    "usage": {                        │
        │      "prompt_tokens": 1471,          │
        │      "completion_tokens": 499,       │
        │      "total_tokens": 1970            │
        │    }                                  │
        │  }                                   │
        │                                      │
        │  JSON_RESULTADO contiene:             │
        │  {                                   │
        │    "proveedores": {                   │
        │      "{nit}": {                       │
        │        "aplica_retencion": true,      │
        │        "porcentaje_retencion": 11,    │
        │        "clasificaciones": {           │
        │          "{factura_num}": [            │
        │            {                          │
        │              "nombre": "Artículo",   │
        │              "ref": "F001-123",       │
        │              "cantidad": 5,           │
        │              "valor_unitario": 25000, │
        │              "valor_total": 125000,   │
        │              "modalidad_pago": "credito",│
        │              "grupo_contable": "HERRAMIENTAS",│
        │              "destino": "INVENTARIO",│
        │              "cuentas": {            │
        │                "1435": {              │
        │                  "valor": 125000,     │
        │                  "naturaleza": "D",   │
        │                  "auxiliar": "01",    │
        │                  "nomauxiliar": "Herramientas"│
        │                },                    │
        │                "240801": {            │
        │                  "valor": 23750,      │
        │                  "naturaleza": "D",   │
        │                  "auxiliar": "02",    │
        │                  "nomauxiliar": "IVA compras"│
        │                },                     │
        │                "110505": {            │
        │                  "valor": 148750,     │
        │                  "naturaleza": "C",   │
        │                  "auxiliar": "01",    │
        │                  "nomauxiliar": "Proveedores"│
        │                }                      │
        │              },                      │
        │              "impuestos_aplicados": [],│
        │              "confianza": "ALTA"      │
        │            }                         │
        │          ]                           │
        │        },                            │
        │        "asientos_contables": [       │
        │          {                           │
        │            "factura": "F001-123",     │
        │            "proveedor": "{nit}",      │
        │            "fecha": "2024-03-15",     │
        │            "descripcion": "Compra...",│
        │            "debitos": [...],         │
        │            "creditos": [...],         │
        │            "total_debitos": 148750,   │
        │            "total_creditos": 148750,  │
        │            "balanceado": true         │
        │          }                           │
        │        ]                             │
        │      }                               │
        │    },                                │
        │    "recomendaciones": []             │
        │  }                                   │
        └─────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   6. PROCESAMIENTO DE RESPUESTA                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  Parsear JSON de respuesta          │
        │  ─────────────────────────────────   │
        │  • Extraer clasificaciones          │
        │  • Extraer asientos contables        │
        │  • Calcular costos (USD y COP)       │
        │  • Calcular tiempo de procesamiento  │
        │  • Contar tokens (input/output)      │
        └─────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   7. ALMACENAMIENTO EN BD                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  Guardar en ClasificacionContable    │
        │  ─────────────────────────────────   │
        │  • factura_json_enviada:             │
        │    - Solo factura (sin prompt)       │
        │    - Todos los artículos reales      │
        │                                      │
        │  • respuesta_json_completa:           │
        │    - Respuesta completa de Deepseek  │
        │    - Con metadata (tokens, etc.)     │
        │                                      │
        │  • respuesta_json_factura:           │
        │    - Solo clasificaciones            │
        │    - Sin metadata                    │
        │                                      │
        │  • Costos y tiempos:                 │
        │    - costo_total_factura (USD)       │
        │    - costo_total_cop                 │
        │    - tiempo_procesamiento_segundos   │
        │    - tokens_input/output             │
        └─────────────────────────────────────┘
```

---

## 📤 ¿QUÉ SE ENVÍA A DEEPSEEK?

### 1. **System Prompt** (Instrucciones Generales)
```python
"Eres contador público colombiano experto en NIIF, PUC y normatividad tributaria..."
```
- Define el rol del AI
- Establece reglas de clasificación contable
- Especifica formato de respuesta JSON
- Define reglas de oro contables (INVENTARIO, GASTO, ACTIVO)

### 2. **User Prompt** (Contexto Específico)
```python
## CONTEXTO EMPRESA COMPRADORA:
- Razón Social: {empresa_nit}
- GIRO PRINCIPAL: {ciuu} - {descripción con INCLUYE/EXCLUYE}
- GIROS SECUNDARIOS: {lista de secundarios}

## CONTEXTO PROVEEDOR:
- NIT: {proveedor_nit}
- GIRO: {ciuu} - {descripción con INCLUYE/EXCLUYE}
- Tipo Operación: {compra/venta}
- Aplica Retención: {true/false}
- % Retención: {porcentaje}
- Modalidad Pago: {credito/contado}
- Forma Pago: {efectivo/transferencia/etc}

## FACTURAS Y ARTÍCULOS:
{JSON con TODOS los artículos, cada uno con:
  - nombre
  - ref (número de factura)
  - cantidad
  - valor_unitario
  - valor_total
  - impuestos: [
      {
        code: "01",
        nombre: "IVA",
        porcentaje: 19,
        base: 125000,
        valor: 23750
      }
    ]
}
```

### 3. **Payload HTTP**
```json
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "system",
      "content": "{SYSTEM_PROMPT}"
    },
    {
      "role": "user",
      "content": "{USER_PROMPT}"
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

## 📥 ¿QUÉ SE RECIBE DE DEEPSEEK?

### Estructura de Respuesta

```json
{
  "id": "chat-xxx",
  "model": "deepseek-chat",
  "choices": [{
    "message": {
      "content": "{JSON_RESULTADO}"
    }
  }],
  "usage": {
    "prompt_tokens": 1471,
    "completion_tokens": 499,
    "total_tokens": 1970
  }
}
```

### JSON_RESULTADO (contenido del mensaje)

```json
{
  "proveedores": {
    "{nit_proveedor}": {
      "aplica_retencion": true,
      "porcentaje_retencion": 11,
      "clasificaciones": {
        "{numero_factura}": [
          {
            "nombre": "Nombre del artículo",
            "ref": "F001-123",
            "cantidad": 5,
            "valor_unitario": 25000,
            "valor_total": 125000,
            "modalidad_pago": "credito",
            "grupo_contable": "HERRAMIENTAS",
            "destino": "INVENTARIO",
            "cuentas": {
              "1435": {
                "valor": 125000,
                "naturaleza": "D",
                "auxiliar": "01",
                "nomauxiliar": "Herramientas"
              },
              "240801": {
                "valor": 23750,
                "naturaleza": "D",
                "auxiliar": "02",
                "nomauxiliar": "IVA compras"
              },
              "110505": {
                "valor": 148750,
                "naturaleza": "C",
                "auxiliar": "01",
                "nomauxiliar": "Proveedores"
              }
            },
            "impuestos_aplicados": [],
            "confianza": "ALTA"
          }
        ]
      },
      "asientos_contables": [
        {
          "factura": "F001-123",
          "proveedor": "{nit}",
          "fecha": "2024-03-15",
          "descripcion": "Compra de herramientas",
          "debitos": [
            {
              "cuenta": "1435",
              "valor": 125000,
              "auxiliar": "01",
              "nomauxiliar": "Herramientas"
            },
            {
              "cuenta": "240801",
              "valor": 23750,
              "auxiliar": "02",
              "nomauxiliar": "IVA compras"
            }
          ],
          "creditos": [
            {
              "cuenta": "110505",
              "valor": 148750,
              "auxiliar": "01",
              "nomauxiliar": "Proveedores"
            }
          ],
          "total_debitos": 148750,
          "total_creditos": 148750,
          "balanceado": true
        }
      ]
    }
  },
  "recomendaciones": []
}
```

---

## 💾 ¿QUÉ SE GUARDA EN LA BASE DE DATOS?

### Modelo: `ClasificacionContable`

1. **`factura_json_enviada`** (JSONField)
   - ✅ **Solo la factura** (sin prompt)
   - ✅ **Todos los artículos reales** (no genérico)
   - ✅ Cada artículo con sus impuestos
   ```json
   {
     "numero_factura": "F001-123",
     "fecha": "2024-03-15",
     "modalidad_pago": "credito",
     "forma_pago": "efectivo",
     "proveedor_nit": "900111222",
     "articulos": [
       {
         "nombre": "Artículo 1",
         "cantidad": 5,
         "valor_unitario": 25000,
         "valor_total": 125000,
         "impuestos": [...]
       },
       ...
     ]
   }
   ```

2. **`respuesta_json_completa`** (JSONField)
   - ✅ Respuesta completa de Deepseek API
   - ✅ Incluye metadata (tokens, model, id, etc.)
   ```json
   {
     "id": "chat-xxx",
     "model": "deepseek-chat",
     "usage": {...},
     "choices": [...]
   }
   ```

3. **`respuesta_json_factura`** (JSONField)
   - ✅ Solo las clasificaciones (sin metadata)
   - ✅ Estructura limpia para uso en frontend
   ```json
   {
     "clasificaciones": {...},
     "asientos_contables": [...],
     "aplica_retencion": true,
     ...
   }
   ```

4. **Métricas**
   - `costo_total_factura` (USD)
   - `costo_total_cop`
   - `tiempo_procesamiento_segundos`
   - `tokens_input` / `tokens_output`
   - `confianza_promedio` (ALTA/MEDIA/BAJA)

---

## 🔍 Comparación: BCE vs MANU

| Aspecto | BCE | MANU |
|---------|-----|------|
| **Prompt Base** | ✅ Original | ✅ Basado en BCE (línea 16) |
| **Fuente de Artículos** | Excel | `raw_data.LineItems` (BD) |
| **CIUU Empresa** | RUT | RUT → Cámara Comercio → Cache |
| **CIUU Proveedor** | RUT | RUT → Proveedor (cache) → Cámara Comercio |
| **Retry Logic** | ❓ | ✅ Con backoff exponencial |
| **Rate Limiting** | ❓ | ✅ Manejo de 429 (Too Many Requests) |
| **Almacenamiento** | ❓ | ✅ 3 campos JSON separados |
| **Costos** | ❓ | ✅ Cálculo automático (USD/COP) |

---

## 🎯 ¿Por Qué Este Flujo?

### 1. **Contexto Completo para Deepseek**
- **CIUU de Empresa**: Para saber si el artículo es para reventa (INVENTARIO) o consumo (GASTO)
- **CIUU de Proveedor**: Para validar consistencia (¿el proveedor vende esto?)
- **INCLUYE/EXCLUYE**: Para decisiones más precisas

### 2. **Artículos Reales (No Genérico)**
- ✅ Cada artículo se envía individualmente
- ✅ Con sus impuestos ya calculados
- ✅ Deepseek NO recalcula impuestos, solo los usa

### 3. **Modalidad y Forma de Pago**
- **CRÉDITO**: Cuenta 110505 (Proveedores)
- **CONTADO**: Cuenta 110101 (Caja) o 111005 (Bancos)
- La forma de pago determina la cuenta exacta

### 4. **Asientos Balanceados**
- Deepseek genera asientos contables completos
- Debe cumplir: `total_debitos == total_creditos`
- Incluye auxiliares contables

### 5. **Confianza por Artículo**
- **ALTA**: Coincide con giro de empresa/proveedor
- **MEDIA**: Parcialmente relacionado
- **BAJA**: No relacionado o dudoso

---

## 📝 Notas Importantes

1. **El prompt es el mismo de BCE**, pero adaptado para MANU
2. **Se envían TODOS los artículos reales**, no un artículo genérico acumulado
3. **Los impuestos ya están calculados** en cada artículo (Deepseek NO los recalcula)
4. **Se guarda en 3 campos separados** para diferentes usos:
   - `factura_json_enviada`: Para auditoría (qué se envió)
   - `respuesta_json_completa`: Para debugging (respuesta completa)
   - `respuesta_json_factura`: Para frontend (solo clasificaciones)

---

## 🔗 Referencias en el Código

- **Prompts**: `manu/apps/sistema_analitico/services/clasificador_contable_service.py:16-116`
- **Método clasificar**: `manu/apps/sistema_analitico/services/clasificador_contable_service.py:443-644`
- **Modelo BD**: `manu/apps/sistema_analitico/models.py:2586-2713`
- **Endpoint**: `manu/apps/sistema_analitico/views.py:11647+`

