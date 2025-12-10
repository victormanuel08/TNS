# 🔍 ANÁLISIS: Sistema de Pregunta Inteligente Actual (MANU)

## 📋 RESUMEN EJECUTIVO

**Sistema actual**: Ya tienes un sistema de "pregunta inteligente" funcional que:
- ✅ Importa datos de Firebird → PostgreSQL
- ✅ Usa DeepSeek para interpretar consultas en lenguaje natural
- ✅ Hace predicciones con ML (XGBoost, Prophet)
- ✅ Consulta datos históricos desde PostgreSQL
- ✅ Genera respuestas en lenguaje natural

**Pregunta clave**: ¿Es descartable, mejorable, o hacer algo nuevo?

---

## 🏗️ ARQUITECTURA ACTUAL

### **1. Flujo de Datos: Firebird → PostgreSQL**

```
Firebird (Base de datos operativa)
    ↓
DataManager.importar_datos_empresa()
    ↓
DatabaseConnector (conecta a Firebird)
    ↓
Extrae datos con consultas SQL
    ↓
Guarda en PostgreSQL: MovimientoInventario
    ↓
Datos disponibles para consultas rápidas
```

**Archivos clave:**
- `manu/apps/sistema_analitico/services/data_manager.py`
- `manu/apps/sistema_analitico/services/database_connectors.py`
- `manu/apps/sistema_analitico/models.py` → `MovimientoInventario`

**Ventajas:**
- ✅ Datos estructurados en PostgreSQL (rápido)
- ✅ No depende de Firebird en tiempo real
- ✅ Puede hacer agregaciones complejas

**Desventajas:**
- ⚠️ Requiere importación periódica (no tiempo real)
- ⚠️ Ocupa espacio en PostgreSQL

---

### **2. Sistema de Pregunta Inteligente**

**Endpoint:** `POST /assistant/api/consulta-natural/pregunta_inteligente/`

**Flujo:**
```
Usuario: "¿Qué artículos debo comprar el próximo mes?"
    ↓
ConsultaNaturalViewSet.pregunta_inteligente()
    ↓
_interpretar_consulta_natural() → Detecta tipo de consulta
    ↓
┌─────────────────────────────────────┐
│ ¿Es predictiva o histórica?         │
└─────────────────────────────────────┘
    ↓
┌──────────────┬──────────────────────┐
│ PREDICTIVA   │ HISTÓRICA            │
│ (ML)         │ (SQL directo)        │
├──────────────┼──────────────────────┤
│ - XGBoost    │ - Consulta a        │
│ - Prophet    │   MovimientoInventario│
│ - Modelos    │ - Agregaciones SQL   │
│   .joblib    │ - Filtros por fecha  │
└──────────────┴──────────────────────┘
    ↓
NaturalResponseOrchestrator
    ↓
DeepSeekIntegrator.generar_respuesta_niño_inteligente()
    ↓
Respuesta en lenguaje natural
```

**Archivos clave:**
- `manu/apps/sistema_analitico/views.py` → `ConsultaNaturalViewSet`
- `manu/apps/sistema_analitico/services/deepseek_integrator.py`
- `manu/apps/sistema_analitico/services/natural_response_orchestrator.py`

---

### **3. Predicciones ML**

**Modelos:**
- **XGBoost**: Predicción de demanda con características avanzadas
- **Prophet**: Predicción de tendencias y estacionalidad
- **Guardado**: `.joblib` (similar a jsonline, pero binario)

**Flujo:**
```
1. Entrenar modelos:
   POST /assistant/api/ml/entrenar_modelos/
   → MLEngine.entrenar_modelos_empresa()
   → Lee MovimientoInventario
   → Entrena XGBoost + Prophet
   → Guarda en modelos_ml/empresa_{nit}.joblib

2. Predecir:
   → MLEngine.predecir_demanda_articulos()
   → Carga modelo desde disco
   → Genera predicciones
   → Retorna resultados
```

**Archivos clave:**
- `manu/apps/sistema_analitico/services/ml_engine.py`
- `manu/apps/sistema_analitico/services/xgboost_predictor.py`
- `manu/apps/sistema_analitico/services/prophet_forecaster.py`

**Integración MLflow (opcional):**
- Registra métricas de entrenamiento
- Tracking de experimentos
- UI en `http://localhost:5000`

---

### **4. Consultas Históricas**

**Datos precargados:**
- ✅ Sí, están en PostgreSQL (`MovimientoInventario`)
- ✅ No hay caché específico (se consulta directamente)
- ✅ Consultas SQL optimizadas con índices

**Tipos de consultas históricas:**
- `ventas_por_mes`: Ventas de un mes específico
- `ventas_por_meses`: Ventas de múltiples meses
- `compras_por_mes`: Compras de un mes
- `ventas_por_anio`: Ventas de un año
- `ventas_por_rango_fechas`: Ventas en rango
- `ventas_recientes`: Ventas recientes
- `comparar_anios`: Comparación entre años
- `articulos_mas_vendidos`: Top artículos

**Ejemplo de consulta:**
```python
# En _consultar_ventas_por_mes()
query = MovimientoInventario.objects.filter(
    empresa_servidor_id=empresa_servidor_id,
    fecha__year=anio,
    fecha__month=mes,
    tipo_movimiento='VENTA'
).aggregate(
    total_ventas=Sum('valor_total'),
    cantidad_articulos=Count('articulo_id', distinct=True)
)
```

---

## 🔄 COMPARACIÓN: Sistema Actual vs RAGFlow/Casibase

| Aspecto | Sistema Actual (MANU) | RAGFlow/Casibase |
|---------|----------------------|------------------|
| **Datos** | Firebird → PostgreSQL (estructurado) | PDFs → Base vectorial (texto) |
| **Búsqueda** | SQL directo (rápido) | Búsqueda vectorial (embeddings) |
| **Predicciones** | ✅ ML (XGBoost, Prophet) | ❌ No tiene |
| **Interpretación** | DeepSeek (lenguaje natural) | DeepSeek (lenguaje natural) |
| **Actualización** | ⚠️ Importación manual | ✅ Agregar PDF inmediato |
| **Tipo de datos** | Datos transaccionales (ventas, compras) | Documentos (PDFs, textos) |
| **Costo** | ~$0.001 por consulta (DeepSeek) | ~$0.001 por consulta (DeepSeek) |
| **Memoria conversacional** | ⚠️ No implementada | ✅ Sí (dentro de sesión) |
| **Transparencia** | ✅ Muestra datos SQL | ✅ Muestra documentos fuente |

---

## ✅ FORTALEZAS DEL SISTEMA ACTUAL

### **1. Datos Estructurados**
- ✅ PostgreSQL es rápido para consultas SQL
- ✅ Puede hacer agregaciones complejas
- ✅ Índices optimizados para búsquedas

### **2. Predicciones ML**
- ✅ Modelos entrenados específicos por empresa
- ✅ XGBoost + Prophet (dos enfoques complementarios)
- ✅ MLflow para tracking (opcional)

### **3. Integración Firebird**
- ✅ Ya tienes la infraestructura
- ✅ Importación automatizable
- ✅ No depende de Firebird en tiempo real

### **4. DeepSeek Integrado**
- ✅ Ya usas DeepSeek para interpretar consultas
- ✅ Genera respuestas en lenguaje natural
- ✅ Tono personalizado ("niño inteligente")

---

## ⚠️ DEBILIDADES / ÁREAS DE MEJORA

### **1. Memoria Conversacional**
- ❌ **No tiene**: No recuerda contexto entre preguntas
- ✅ **Mejorable**: Agregar historial de conversación

**Ejemplo actual:**
```
Usuario: "¿Cuánto vendí en enero?"
Bot: "Vendiste $5,000,000 en enero"

Usuario: "¿Y en febrero?"
Bot: "Vendiste $6,000,000 en febrero"
     ↑ No recuerda que hablábamos de ventas
```

**Mejora posible:**
```python
# Agregar historial de conversación
conversacion = [
    {"role": "user", "content": "¿Cuánto vendí en enero?"},
    {"role": "assistant", "content": "Vendiste $5,000,000 en enero"},
    {"role": "user", "content": "¿Y en febrero?"}
]
# DeepSeek puede usar el contexto
```

### **2. Actualización de Datos**
- ⚠️ **Manual**: Requiere importación periódica
- ✅ **Mejorable**: Automatizar importación (Celery task)

### **3. Consultas Históricas Precargadas**
- ⚠️ **No hay caché**: Cada consulta ejecuta SQL
- ✅ **Mejorable**: Agregar caché Redis para consultas frecuentes

**Ejemplo:**
```python
# Caché para consultas comunes
cache_key = f"ventas_mes_{empresa_id}_{anio}_{mes}"
resultado = cache.get(cache_key)
if not resultado:
    resultado = ejecutar_consulta_sql()
    cache.set(cache_key, resultado, timeout=3600)  # 1 hora
```

### **4. Text2SQL Avanzado**
- ⚠️ **Limitado**: Solo consultas predefinidas
- ✅ **Mejorable**: DeepSeek genera SQL dinámico

**Actual:**
```python
# Consultas hardcodeadas
if tipo_consulta == 'ventas_por_mes':
    return self._consultar_ventas_por_mes(...)
```

**Mejora posible:**
```python
# DeepSeek genera SQL dinámico
sql = deepseek.generar_sql(consulta_natural, schema_postgresql)
resultado = ejecutar_sql(sql)
```

---

## 🎯 RECOMENDACIÓN: ¿DESCARTAR, MEJORAR O NUEVO?

### ❌ **NO DESCARTAR**

**Razones:**
1. ✅ Ya funciona y está integrado
2. ✅ Tiene predicciones ML (RAGFlow no tiene)
3. ✅ Datos estructurados (más rápido que RAG)
4. ✅ Específico para tu dominio (inventario, ventas)

### ✅ **MEJORAR (Recomendado)**

**Mejoras prioritarias:**

#### **1. Memoria Conversacional** (Alta prioridad)
```python
# Agregar a DeepSeekIntegrator
def generar_respuesta_con_contexto(self, contexto_tecnico, historial_conversacion):
    messages = [
        {"role": "system", "content": self.tono_niño},
        *historial_conversacion,  # ← Agregar historial
        {"role": "user", "content": contexto_tecnico}
    ]
```

**Beneficio**: Mejor experiencia de usuario

#### **2. Caché de Consultas Históricas** (Media prioridad)
```python
from django.core.cache import cache

def _consultar_ventas_por_mes(self, ...):
    cache_key = f"ventas_mes_{empresa_id}_{anio}_{mes}"
    resultado = cache.get(cache_key)
    if not resultado:
        resultado = ejecutar_consulta_sql()
        cache.set(cache_key, resultado, timeout=3600)
    return resultado
```

**Beneficio**: Consultas más rápidas

#### **3. Text2SQL Dinámico** (Baja prioridad)
```python
# Permitir que DeepSeek genere SQL
def _generar_sql_dinamico(self, consulta_natural, schema):
    prompt = f"""
    Schema PostgreSQL:
    {schema}
    
    Consulta del usuario: {consulta_natural}
    
    Genera SQL válido para PostgreSQL.
    """
    sql = deepseek.generar_respuesta(prompt)
    return sql
```

**Beneficio**: Consultas más flexibles

#### **4. Importación Automatizada** (Media prioridad)
```python
# Celery task para importar datos periódicamente
@shared_task
def importar_datos_empresa_periodico():
    empresas = EmpresaServidor.objects.filter(activo=True)
    for empresa in empresas:
        DataManager().importar_datos_empresa(empresa.id)
```

**Beneficio**: Datos siempre actualizados

---

### 🔄 **COMPLEMENTAR CON RAG (Opcional)**

**Para documentos contables PDF:**

Puedes agregar RAGFlow/Casibase **PARA DOCUMENTOS**, mientras mantienes el sistema actual **PARA DATOS TRANSACCIONALES**:

```
┌─────────────────────────────────────┐
│ Sistema Actual (MANU)                │
│ - Datos transaccionales              │
│ - Predicciones ML                    │
│ - Consultas SQL                      │
└─────────────────────────────────────┘
              +
┌─────────────────────────────────────┐
│ RAGFlow/Casibase (NUEVO)            │
│ - Documentos PDF (normas, guías)    │
│ - Búsqueda vectorial                │
│ - Chat sobre documentos             │
└─────────────────────────────────────┘
```

**Ejemplo de uso combinado:**
```
Usuario: "¿Cuánto vendí en enero?" 
→ Sistema Actual (SQL a PostgreSQL)

Usuario: "¿Qué dice la norma sobre IVA?"
→ RAGFlow (búsqueda en PDFs)

Usuario: "¿Qué artículos debo comprar?"
→ Sistema Actual (predicción ML)
```

---

## 📊 MATRIZ DE DECISIÓN

| Necesidad | Sistema Actual | RAGFlow/Casibase | Recomendación |
|-----------|---------------|------------------|---------------|
| **Datos transaccionales** | ✅ Perfecto | ❌ No aplica | **Mantener actual** |
| **Predicciones ML** | ✅ Tiene | ❌ No tiene | **Mantener actual** |
| **Documentos PDF** | ❌ No tiene | ✅ Perfecto | **Agregar RAG** |
| **Memoria conversacional** | ⚠️ Falta | ✅ Tiene | **Mejorar actual** |
| **Text2SQL dinámico** | ⚠️ Limitado | ❌ No aplica | **Mejorar actual** |

---

## 🎯 CONCLUSIÓN Y PLAN DE ACCIÓN

### **✅ DECISIÓN: MEJORAR EL SISTEMA ACTUAL**

**No descartar porque:**
1. ✅ Ya funciona y está integrado
2. ✅ Tiene predicciones ML (único)
3. ✅ Datos estructurados (más rápido)
4. ✅ Específico para tu dominio

**Mejoras prioritarias:**
1. **Memoria conversacional** (Alta)
2. **Caché de consultas** (Media)
3. **Importación automatizada** (Media)
4. **Text2SQL dinámico** (Baja)

**Complementar con RAG (opcional):**
- Agregar RAGFlow/Casibase **solo para documentos PDF**
- Mantener sistema actual **para datos transaccionales**

---

## 📝 PRÓXIMOS PASOS

### **Fase 1: Mejoras al Sistema Actual** (2-3 semanas)

1. **Memoria conversacional**
   - Agregar historial de conversación a `DeepSeekIntegrator`
   - Guardar conversaciones en base de datos (opcional)

2. **Caché de consultas**
   - Implementar caché Redis para consultas frecuentes
   - Invalidar caché cuando se importen nuevos datos

3. **Importación automatizada**
   - Crear Celery task para importación periódica
   - Configurar horarios por empresa

### **Fase 2: Complementar con RAG** (Opcional, 3-4 semanas)

1. **Integrar RAGFlow/Casibase**
   - Solo para documentos PDF (normas, guías)
   - Mantener sistema actual para datos transaccionales

2. **Unificar interfaz**
   - Mismo endpoint detecta tipo de consulta
   - Rutea a sistema actual o RAG según corresponda

---

**Última actualización**: Diciembre 2025

