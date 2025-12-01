# Flujo de Trabajo del Sistema Analítico - EDDESO

Este documento describe la secuencia completa de pasos para configurar y utilizar el sistema analítico, explicando qué hace cada acción en el backend.

## Tabla de Contenido

1. [Flujo Principal de Configuración](#flujo-principal-de-configuración)
2. [Detalle de Cada Paso](#detalle-de-cada-paso)
3. [Flujos Adicionales](#flujos-adicionales)
4. [Diagrama de Secuencia](#diagrama-de-secuencia)

---

## Flujo Principal de Configuración

### Secuencia Recomendada

```
1. Crear Servidor
   ↓
2. Escanear Empresas (Descubrir Empresas)
   ↓
3. Configurar Consulta SQL (si es necesario)
   ↓
4. Extraer Datos de Inventario
   ↓
5. Entrenar Modelos de ML (opcional)
   ↓
6. Usar Consultas Naturales / Predicciones
```

---

## Detalle de Cada Paso

### Paso 1: Crear Servidor

**Endpoint:** `POST /assistant/api/servidores/`

**Qué hace:**
- Crea un registro de `Servidor` en la base de datos PostgreSQL
- Almacena credenciales encriptadas (usando `EncryptedTextField`)
- Guarda información de conexión: host, puerto, usuario, password, tipo de servidor
- Registra el servidor en el archivo maestro (`data/maestro.pkl`)

**Request:**
```json
{
  "nombre": "Servidor Principal",
  "host": "192.168.1.100",
  "usuario": "SYSDBA",
  "password": "masterkey",
  "tipo_servidor": "FIREBIRD",
  "puerto": 3050,
  "ruta_maestra": "C:/Visual TNS/ADMIN.gdb"
}
```

**Response:**
```json
{
  "id": 1,
  "nombre": "Servidor Principal",
  "host": "192.168.1.100",
  "tipo_servidor": "FIREBIRD",
  "puerto": 3050,
  "activo": true,
  "fecha_creacion": "2025-01-15T10:30:00Z"
}
```

**Backend (Django):**
- `ServidorViewSet.create()` → Crea el modelo `Servidor`
- El password se encripta automáticamente usando `EncryptedTextField`
- Se actualiza el archivo maestro con la información del servidor

---

### Paso 2: Escanear Empresas (Descubrir Empresas)

**Endpoint:** `POST /assistant/api/sistema/descubrir_empresas/`

**Qué hace:**
1. Conecta al servidor usando la `ruta_maestra` (ADMIN.gdb)
2. Ejecuta la consulta: `SELECT CODIGO, NOMBRE, NIT, ANOFIS, ARCHIVO FROM EMPRESAS WHERE NIT IS NOT NULL`
3. Para cada empresa encontrada:
   - Verifica si ya existe una empresa con el mismo NIT y año fiscal (en cualquier servidor)
   - Si existe en otro servidor: la omite (evita duplicados globales)
   - Si existe en el mismo servidor: la actualiza
   - Si no existe: la crea como nueva `EmpresaServidor`
4. Retorna el total de empresas procesadas

**Request:**
```json
{
  "servidor_id": 1
}
```

**Response:**
```json
{
  "estado": "empresas_descubiertas",
  "total_empresas": 5
}
```

**Backend (Django):**
- `SistemaViewSet.descubrir_empresas()` → Llama a `DataManager.descubrir_empresas()`
- `DataManager.descubrir_empresas()`:
  - Conecta al servidor base usando `DatabaseConnector`
  - Ejecuta la consulta SQL en la tabla `EMPRESAS`
  - Itera sobre los resultados y crea/actualiza `EmpresaServidor`
  - Usa `update_or_create()` para evitar duplicados
  - Valida unicidad global por NIT + año fiscal

**Modelo creado:**
- `EmpresaServidor` con campos: `servidor`, `codigo`, `nombre`, `nit`, `anio_fiscal`, `ruta_base`, `estado`

---

### Paso 3: Configurar Consulta SQL (Opcional pero Recomendado)

**Endpoint:** `PATCH /assistant/api/empresas-servidor/{id}/`

**Qué hace:**
- Permite configurar la consulta SQL personalizada que se usará para extraer datos
- Si no se configura, el sistema usa una consulta por defecto
- La consulta debe retornar campos específicos (ver documentación de campos requeridos)

**Request:**
```json
{
  "consulta_sql": "SELECT TIPO_DOCUMENTO, FECHA, ARTICULO_CODIGO, ARTICULO_NOMBRE, CANTIDAD, PRECIO_UNITARIO, ... FROM MOVIMIENTOS WHERE FECHA BETWEEN ? AND ?"
}
```

**Backend (Django):**
- `EmpresaServidorViewSet.partial_update()` → Actualiza el campo `consulta_sql`
- Esta consulta se usará en el paso 4 para extraer datos

---

### Paso 4: Extraer Datos de Inventario

**Endpoint:** `POST /assistant/api/sistema/extraer_datos/`

**Qué hace:**
1. Conecta a la base de datos de la empresa específica (usando `ruta_base`)
2. Ejecuta la consulta SQL configurada con los parámetros de fecha
3. Procesa los resultados en chunks de 1000 registros (para optimizar memoria)
4. Para cada registro:
   - Mapea los campos del SQL a `MovimientoInventario`
   - Calcula campos derivados (valor_total, lead_time_dias, etc.)
   - Determina tipo de bodega (implante, instrumental, equipo de poder)
   - Normaliza NITs (elimina dígito verificador)
5. Guarda los movimientos en la base de datos PostgreSQL usando `bulk_create()`
6. Actualiza `ultima_extraccion` de la empresa

**Request:**
```json
{
  "empresa_servidor_id": 1,
  "fecha_inicio": "2025-01-01",
  "fecha_fin": "2025-01-31",
  "forzar_reextraccion": false
}
```

**Response:**
```json
{
  "estado": "exito",
  "registros_guardados": 15234,
  "total_encontrados": 15234,
  "chunks_procesados": 16
}
```

**Backend (Django):**
- `SistemaViewSet.extraer_datos()` → Llama a `DataManager.extraer_datos_empresa()`
- `DataManager.extraer_datos_empresa()`:
  - Verifica si ya se extrajeron datos para ese rango (si `forzar_reextraccion=false`)
  - Cuenta total de registros con `_contar_registros()`
  - Divide en chunks de 1000 registros
  - Para cada chunk: `_extraer_chunk()` → `_guardar_movimientos()`
  - `_guardar_movimientos()`: Crea objetos `MovimientoInventario` y los guarda con `bulk_create()`

**Modelo creado:**
- Múltiples registros de `MovimientoInventario` con toda la información de movimientos de inventario

---

### Paso 5: Entrenar Modelos de Machine Learning (Opcional)

**Endpoint:** `POST /assistant/api/ml/entrenar_modelos/`

**Qué hace:**
1. Obtiene todos los movimientos de inventario de la empresa
2. Prepara los datos para entrenamiento (series temporales)
3. Entrena dos modelos:
   - **XGBoost**: Para predicción de demanda con características avanzadas
   - **Prophet**: Para predicción de tendencias y estacionalidad
4. Evalúa los modelos (calcula MAE, R², RMSE)
5. Guarda los modelos entrenados en `modelos_ml/empresa_{nit}.joblib`
6. Si MLflow está configurado, registra el entrenamiento

**Request:**
```json
{
  "empresa_servidor_id": 1,
  "fecha_inicio": "2023-01-01",
  "fecha_fin": "2023-12-31"
}
```

**Response:**
```json
{
  "estado": "modelos_entrenados",
  "modelo_id": "empresa_900123456",
  "xgboost_mae": 12.5,
  "xgboost_r2": 0.89,
  "prophet_mae": 15.2,
  "mlflow_run_id": "abc123...",
  "mlflow_ui_url": "http://localhost:5000/#/experiments/0/runs/abc123..."
}
```

**Backend (Django):**
- `MLViewSet.entrenar_modelos()` → Llama a `MLEngine.entrenar_modelos_empresa()`
- `MLEngine.entrenar_modelos_empresa()`:
  - Obtiene datos históricos de `MovimientoInventario`
  - Prepara features para XGBoost (demanda histórica, estacionalidad, etc.)
  - Entrena XGBoost con `XGBoostPredictor`
  - Entrena Prophet con `ProphetForecaster`
  - Guarda modelos en disco
  - Si MLflow disponible: registra métricas y modelo

---

### Paso 6: Usar Consultas Naturales / Predicciones

**Endpoint:** `POST /assistant/api/consulta-natural/pregunta_inteligente/`

**Qué hace:**
1. Analiza la consulta del usuario usando IA (DeepSeek)
2. Determina el tipo de consulta (análisis, predicción, recomendación)
3. Ejecuta la consulta correspondiente:
   - **Análisis**: Consulta directa a `MovimientoInventario`
   - **Predicción**: Usa modelos ML entrenados
   - **Recomendación**: Genera recomendaciones de compra
4. Genera explicación en lenguaje natural
5. Retorna respuesta estructurada

**Request:**
```json
{
  "consulta": "¿Qué artículos debo comprar el próximo mes?",
  "empresa_servidor_id": 1
}
```

**Response:**
```json
{
  "consulta_original": "¿Qué artículos debo comprar el próximo mes?",
  "explicacion_nino_inteligente": "Basado en el análisis de tu inventario...",
  "datos_tecnicos_completos": {
    "recomendaciones": [...],
    "mlflow_run_id": "...",
    "mlflow_ui_url": "..."
  }
}
```

**Backend (Django):**
- `ConsultaNaturalViewSet.pregunta_inteligente()` → Usa `NaturalResponseOrchestrator`
- `NaturalResponseOrchestrator`:
  - Analiza la consulta con `DeepSeekIntegrator`
  - Determina tipo de consulta
  - Ejecuta consulta usando `MLEngine` o consultas directas
  - Genera explicación con IA
  - Formatea respuesta

---

## Flujos Adicionales

### Flujo: Scraping DIAN

**Secuencia:**
```
1. Crear Sesión DIAN
   POST /dian/api/sessions/
   ↓
2. Iniciar Scraping
   POST /dian/api/sessions/{id}/start_scraping/
   ↓
3. Procesar Documentos
   (Automático - Celery Task)
   ↓
4. Descargar Resultados
   GET /dian/api/sessions/{id}/download_json/
```

**Qué hace cada paso:**
- **Crear Sesión**: Guarda URL de DIAN, NIT, fechas, tipo de scraping
- **Iniciar Scraping**: Dispara tarea Celery que:
  - Usa Playwright para automatizar navegador
  - Descarga facturas desde DIAN
  - Procesa XMLs y extrae datos
  - Guarda en `DianDocument`
- **Procesar**: Convierte XMLs a JSON estructurado
- **Descargar**: Genera archivos JSON/Excel con los documentos procesados

---

### Flujo: Scraping FUDO

**Secuencia:**
```
1. Configurar Empresa con credenciales FUDO
   ↓
2. Iniciar Scraping FUDO
   POST /fudo/api/scraping/start/
   ↓
3. Procesar y Sincronizar
   (Automático - Celery Task)
```

**Qué hace:**
- Conecta a API de FUDO usando credenciales
- Obtiene productos, categorías, ventas
- Sincroniza con base de datos Firebird de la empresa
- Actualiza inventario y movimientos

---

### Flujo: Puente TNS

**Secuencia:**
```
1. Validar Usuario TNS
   POST /assistant/api/tns/validate_user/
   ↓
2. Consultar Tablas
   GET /assistant/api/tns/tables/
   ↓
3. Ejecutar Queries
   POST /assistant/api/tns/query/
   ↓
4. Emitir Facturas
   POST /assistant/api/tns/emit_invoice/
```

**Qué hace cada paso:**
- **Validar Usuario**: Verifica credenciales TNS en la base de datos
- **Consultar Tablas**: Lista todas las tablas disponibles
- **Ejecutar Queries**: Ejecuta SQL directo en Firebird
- **Emitir Facturas**: Crea facturas usando stored procedures de TNS

---

## Diagrama de Secuencia

```
Usuario (Frontend)
    │
    ├─► POST /assistant/api/servidores/
    │   └─► ServidorViewSet.create()
    │       └─► Crea Servidor en BD
    │
    ├─► POST /assistant/api/sistema/descubrir_empresas/
    │   └─► SistemaViewSet.descubrir_empresas()
    │       └─► DataManager.descubrir_empresas()
    │           ├─► Conecta a ADMIN.gdb
    │           ├─► Ejecuta SELECT FROM EMPRESAS
    │           └─► Crea/Actualiza EmpresaServidor
    │
    ├─► PATCH /assistant/api/empresas-servidor/{id}/
    │   └─► EmpresaServidorViewSet.partial_update()
    │       └─► Actualiza consulta_sql
    │
    ├─► POST /assistant/api/sistema/extraer_datos/
    │   └─► SistemaViewSet.extraer_datos()
    │       └─► DataManager.extraer_datos_empresa()
    │           ├─► Conecta a base de empresa
    │           ├─► Ejecuta consulta SQL con fechas
    │           ├─► Procesa en chunks de 1000
    │           └─► Guarda MovimientoInventario (bulk_create)
    │
    ├─► POST /assistant/api/ml/entrenar_modelos/
    │   └─► MLViewSet.entrenar_modelos()
    │       └─► MLEngine.entrenar_modelos_empresa()
    │           ├─► Obtiene MovimientoInventario
    │           ├─► Entrena XGBoost
    │           ├─► Entrena Prophet
    │           └─► Guarda modelos en disco
    │
    └─► POST /assistant/api/consulta-natural/pregunta_inteligente/
        └─► ConsultaNaturalViewSet.pregunta_inteligente()
            └─► NaturalResponseOrchestrator
                ├─► Analiza consulta (DeepSeek)
                ├─► Ejecuta consulta/predicción
                └─► Genera respuesta
```

---

## Modelos de Datos Clave

### Servidor
- Almacena información de conexión a bases de datos externas
- Tipos soportados: Firebird, PostgreSQL, SQL Server, MySQL
- Credenciales encriptadas

### EmpresaServidor
- Representa una empresa en un servidor específico
- Unicidad global por NIT + año fiscal
- Contiene `ruta_base` (path a la base de datos de la empresa)
- Contiene `consulta_sql` (query personalizada para extracción)

### MovimientoInventario
- Almacena todos los movimientos extraídos
- Campos: tipo_documento, fecha, artículo, cantidad, precios, etc.
- Índices optimizados para consultas rápidas
- Usado para análisis y entrenamiento de ML

---

## Notas Importantes

1. **Unicidad de Empresas**: El sistema garantiza que no haya duplicados por NIT + año fiscal, incluso entre diferentes servidores.

2. **Extracción en Chunks**: Los datos se extraen en chunks de 1000 registros para optimizar memoria y rendimiento.

3. **Validación de Consulta SQL**: La consulta SQL debe retornar campos específicos. Ver documentación de campos requeridos.

4. **MLflow Opcional**: El sistema funciona sin MLflow, pero si está configurado, registra todos los entrenamientos y predicciones.

5. **Encriptación**: Las contraseñas de servidores se almacenan encriptadas usando `encrypted_model_fields`.

6. **Conexiones**: El sistema maneja conexiones a múltiples tipos de bases de datos usando `DatabaseConnector`.

---

## Troubleshooting

### Error al descubrir empresas
- Verifica que el servidor tenga `ruta_maestra` configurada (ADMIN.gdb)
- Verifica credenciales de conexión
- Verifica que la tabla `EMPRESAS` exista en ADMIN.gdb

### Error al extraer datos
- Verifica que `consulta_sql` esté configurada correctamente
- Verifica que la empresa tenga `ruta_base` configurada
- Verifica que los campos requeridos estén en la consulta SQL

### Modelos ML no entrenan
- Verifica que haya datos en `MovimientoInventario`
- Verifica que el rango de fechas tenga suficientes datos
- Revisa logs para errores específicos

---

## Referencias

- **API Endpoints**: [`docs/api_endpoints.md`](./api_endpoints.md)
- **MLflow Integration**: [`docs/MLFLOW_INTEGRATION.md`](./MLFLOW_INTEGRATION.md)
- **Código Backend**: `manu/apps/sistema_analitico/`

