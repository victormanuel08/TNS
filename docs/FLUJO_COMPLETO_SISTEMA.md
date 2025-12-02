# 🔄 Flujo Completo del Sistema TNS Core

## 📋 Tabla de Contenidos
1. [Secuencia Correcta de Configuración](#secuencia-correcta)
2. [Modelos de Base de Datos](#modelos-base-datos)
3. [Flujo Detallado Paso a Paso](#flujo-detallado)
4. [Tareas Asíncronas (Celery)](#tareas-celery)
5. [Integración MLflow](#integracion-mlflow)
6. [Endpoints Disponibles](#endpoints-disponibles)
7. [Asociación de NITs y Empresas](#asociacion-nits)
8. [Extracción de Datos](#extraccion-datos)
9. [Entrenamiento de Modelos](#entrenamiento-modelos)

---

## 🎯 Secuencia Correcta de Configuración {#secuencia-correcta}

### **Paso 1: Crear Servidor**
- **Endpoint**: `POST /api/servidores/`
- **Modelo**: `Servidor`
- **Campos requeridos**:
  - `nombre`: Nombre del servidor (ej: "BCE", "Producción")
  - `host`: IP o hostname del servidor Firebird
  - `usuario`: Usuario de Firebird
  - `password`: Contraseña de Firebird
  - `tipo_servidor`: "FIREBIRD" o "SQL_SERVER"
  - `puerto`: Puerto (default: 3050 para Firebird)
  - `ruta_maestra`: Ruta a la base de datos ADMIN.gdb (ej: `C:\datos\ADMIN.gdb`)

**¿Qué pasa?**
- Se crea un registro en la tabla `servidores`
- El servidor queda listo para descubrir empresas

---

### **Paso 2: Crear VPN (Opcional pero Recomendado)**
- **Endpoint**: `POST /api/vpn/configs/`
- **Modelo**: `VpnConfig`
- **¿Para qué?**
  - Conectar de forma segura al servidor Firebird si está en una red privada
  - El backend usa SSH para configurar WireGuard en el servidor remoto

**¿Qué pasa?**
- Se generan claves públicas/privadas
- Se asigna una IP en la red WireGuard (ej: `10.8.3.10`)
- Se crea el archivo `.conf` para el cliente
- Se agrega el peer al servidor WireGuard vía SSH

**Nota**: Si el servidor Firebird es accesible directamente, puedes saltar este paso.

---

### **Paso 3: Descubrir Empresas (Sincronizar)**
- **Endpoint**: `POST /api/sistema/descubrir_empresas/`
- **Body**: `{"servidor_id": 1}`
- **Tarea Celery**: `descubrir_empresas_task` ✅

**¿Qué pasa?**
1. Se conecta al servidor Firebird usando las credenciales del `Servidor`
2. Ejecuta SQL: `SELECT CODIGO, NOMBRE, NIT, ANOFIS, ARCHIVO FROM EMPRESAS WHERE NIT IS NOT NULL`
3. Para cada empresa encontrada:
   - Verifica si ya existe una empresa con el mismo `NIT` y `anio_fiscal` (en cualquier servidor)
   - Si existe en otro servidor: la omite (no duplica)
   - Si no existe: crea/actualiza `EmpresaServidor` en la base de datos
4. Retorna lista de empresas creadas/actualizadas

**Modelo creado**: `EmpresaServidor`
- `servidor`: FK a `Servidor`
- `codigo`: Código de la empresa en TNS
- `nombre`: Nombre de la empresa
- `nit`: NIT (normalizado, sin puntos/guiones)
- `anio_fiscal`: Año fiscal (ej: 2024, 2025)
- `ruta_base`: Ruta al archivo `.gdb` de la empresa
- `estado`: "ACTIVO" por defecto

**⚠️ Importante**:
- El `NIT` + `anio_fiscal` es único globalmente (no puede haber duplicados)
- Si una empresa existe en múltiples servidores con el mismo NIT y año, solo se guarda una vez

**Progreso**: Usa `GET /api/sistema/estado-descubrimiento/?task_id=XXX` para ver el progreso

---

### **Paso 4: Extraer Datos de la Empresa**
- **Endpoint**: `POST /api/sistema/extraer_datos/`
- **Body**: 
  ```json
  {
    "empresa_servidor_id": 1,
    "fecha_inicio": "2024-01-01",
    "fecha_fin": "2024-12-31"
  }
  ```
- **Tarea**: Síncrona (no usa Celery actualmente, pero podría migrarse)

**¿Qué pasa?**
1. Se conecta a la base de datos de la empresa (usando `ruta_base` del `EmpresaServidor`)
2. Ejecuta una consulta SQL compleja que extrae:
   - Movimientos de inventario (ventas, compras, traslados)
   - Artículos, precios, cantidades
   - Fechas, bodegas, tipos de documento
3. **Procesa en chunks de 1000 registros** para evitar sobrecarga
4. Guarda cada registro en la tabla `MovimientoInventario` (PostgreSQL)
5. Actualiza `ultima_extraccion` en `EmpresaServidor`

**Modelo creado**: `MovimientoInventario`
- `empresa_servidor_id`: FK a `EmpresaServidor`
- `articulo_codigo`, `articulo_nombre`
- `cantidad`, `precio_unitario`
- `fecha`, `tipo_documento` (FACTURA_VENTA, FACTURA_COMPRA, etc.)
- `tipo_bodega`, `es_implante`, `es_instrumental`, `es_equipo_poder`

**⚠️ Importante**:
- La extracción puede tardar varios minutos dependiendo del volumen de datos
- Se puede forzar re-extracción con `forzar_reextraccion=True`
- Los datos se guardan en PostgreSQL (no en Firebird)

---

### **Paso 5: Crear Usuario (Opcional)**
- **Endpoint**: `POST /api/auth/register/` (si existe) o crear directamente en Django Admin
- **Modelo**: `User` (Django)
- **¿Para qué?**
  - Acceso al panel de administración
  - Generar API Keys
  - Gestionar permisos

**Nota**: Si solo usas API Keys, no necesitas crear usuarios.

---

### **Paso 6: Generar API Key**
- **Endpoint**: `POST /api/api-keys/generar_api_key/`
- **Body**:
  ```json
  {
    "nit": "900123456",
    "nombre_cliente": "Cliente Ejemplo",
    "dias_validez": 365
  }
  ```
- **Modelo**: `APIKeyCliente`

**¿Qué pasa?**
1. Se genera una API Key única: `sk_XXXXXXXX...`
2. Se busca todas las empresas con el `NIT` proporcionado (normalizado)
3. Se asocian automáticamente todas las empresas del mismo NIT a la API Key
4. Se guarda la fecha de caducidad

**Modelo creado**: `APIKeyCliente`
- `nit`: NIT del cliente (normalizado)
- `nombre_cliente`: Nombre descriptivo
- `api_key`: Clave única (ej: `sk_abc123...`)
- `fecha_caducidad`: Fecha de expiración
- `activa`: Boolean
- `empresas_asociadas`: ManyToMany a `EmpresaServidor` (se llena automáticamente)

**⚠️ Importante**:
- La API Key se asocia automáticamente a **TODAS** las empresas con el mismo NIT
- Si creas una nueva empresa con el mismo NIT después, puedes llamar `actualizar_empresas_asociadas()` para actualizar la relación

---

### **Paso 7: Entrenar Modelos ML (Opcional)**
- **Endpoint**: `POST /api/ml/entrenar_modelos/`
- **Body**:
  ```json
  {
    "empresa_servidor_id": 1
  }
  ```
- **Tarea**: Síncrona (pero podría migrarse a Celery)

**¿Qué pasa?**
1. Obtiene **TODAS** las empresas con el mismo NIT que la empresa proporcionada
2. Extrae datos de `MovimientoInventario` de todas esas empresas
3. Agrupa por `articulo_codigo` y `periodo` (mes)
4. Entrena dos modelos:
   - **Prophet**: Para predicción de series temporales
   - **XGBoost**: Para predicción de demanda con features adicionales
5. Guarda los modelos en `manu/modelos_ml/` como archivos `.joblib`
6. **Registra en MLflow** (si está configurado):
   - Crea un experimento si no existe
   - Registra parámetros, métricas, y el modelo
   - Genera un `run_id` y URL para ver en MLflow UI

**Modelo ID**: `empresa_{NIT}` (ej: `empresa_900123456`)

**Archivos generados**:
- `manu/modelos_ml/empresa_{NIT}_prophet.joblib`
- `manu/modelos_ml/empresa_{NIT}_xgboost.joblib`
- `manu/modelos_ml/empresa_{NIT}_metadata.json`

**MLflow**:
- Si `MLFLOW_TRACKING_URI` está configurado, se registra automáticamente
- Puedes ver el entrenamiento en: `http://mlflow.eddeso.com/#/experiments/0/runs/{run_id}`
- Si MLflow no está disponible, el entrenamiento funciona igual (solo no se registra)

---

## 🗄️ Modelos de Base de Datos {#modelos-base-datos}

### **Jerarquía de Modelos**

```
Servidor (1) ──┐
               ├──> EmpresaServidor (N)
               │     ├──> MovimientoInventario (N)
               │     ├──> APIKeyCliente.empresas_asociadas (M:N)
               │     ├──> EmpresaPersonalizacion (1:1)
               │     ├──> EmpresaEcommerceConfig (1:1)
               │     └──> EmpresaDominio (N)
               │
VpnConfig (N) ──┘
```

### **Tablas Principales**

1. **`servidores`**: Servidores Firebird/SQL Server
2. **`empresas_servidor`**: Empresas descubiertas (único por NIT + año fiscal)
3. **`movimientos_inventario`**: Datos extraídos de TNS (PostgreSQL)
4. **`api_keys_clientes`**: API Keys para acceso al frontend
5. **`empresas_personalizacion`**: Configuración de autopago (modo vertical/horizontal)
6. **`empresas_ecommerce_config`**: Configuración de e-commerce
7. **`empresas_dominio`**: Mapeo de dominios a empresas
8. **`vpn_configs`**: Configuraciones de VPN/WireGuard

---

## 🔄 Flujo Detallado Paso a Paso {#flujo-detallado}

### **Escenario Completo: Configurar una Nueva Empresa**

```
1. Admin crea Servidor
   └─> POST /api/servidores/
   └─> Se guarda en BD: servidores

2. Admin crea VPN (opcional)
   └─> POST /api/vpn/configs/
   └─> Se genera .conf y se agrega peer al servidor WireGuard

3. Admin sincroniza empresas
   └─> POST /api/sistema/descubrir_empresas/ {"servidor_id": 1}
   └─> Celery: descubrir_empresas_task
   └─> Se conecta a Firebird, ejecuta SQL, crea EmpresaServidor
   └─> Progreso: GET /api/sistema/estado-descubrimiento/?task_id=XXX

4. Admin extrae datos
   └─> POST /api/sistema/extraer_datos/
   └─> Se conecta a empresa.gdb, extrae movimientos
   └─> Guarda en MovimientoInventario (PostgreSQL)

5. Admin genera API Key
   └─> POST /api/api-keys/generar_api_key/ {"nit": "900123456"}
   └─> Se asocian automáticamente todas las empresas del NIT

6. Admin entrena modelos (opcional)
   └─> POST /api/ml/entrenar_modelos/ {"empresa_servidor_id": 1}
   └─> Usa datos de TODAS las empresas del mismo NIT
   └─> Guarda modelos en manu/modelos_ml/
   └─> Registra en MLflow (si está configurado)
```

---

## ⚙️ Tareas Asíncronas (Celery) {#tareas-celery}

### **Tareas que Usan Celery**

1. **`descubrir_empresas_task`**
   - **Trigger**: `POST /api/sistema/descubrir_empresas/`
   - **Proceso**: Conecta a Firebird, ejecuta SQL, crea/actualiza empresas
   - **Razón**: Puede tardar varios minutos, evita timeout
   - **Progreso**: `GET /api/sistema/estado-descubrimiento/?task_id=XXX`

2. **`procesar_factura_dian_task`**
   - **Trigger**: `POST /api/dian-processor/procesar-factura/`
   - **Proceso**: Procesa factura electrónica DIAN
   - **Razón**: Operación que puede tardar

### **Tareas que NO Usan Celery (pero podrían)**

- `extraer_datos_empresa`: Actualmente síncrona, pero podría migrarse
- `entrenar_modelos_empresa`: Actualmente síncrona, pero podría migrarse

---

## 📊 Integración MLflow {#integracion-mlflow}

### **¿Cuándo se Crea en MLflow?**

**Solo cuando se entrena un modelo**:
- `POST /api/ml/entrenar_modelos/` → `MLEngine.entrenar_modelos_empresa()`
- Si `MLFLOW_TRACKING_URI` está configurado, se registra automáticamente

### **¿Qué se Registra en MLflow?**

1. **Experimento**: `"TNS_Demanda_Prediccion"` (o el nombre configurado)
2. **Run**: Un run por cada entrenamiento
3. **Parámetros**:
   - `modelo_id`: `empresa_{NIT}`
   - `nit_empresa`: NIT
   - `fecha_entrenamiento`: Timestamp
   - `filas_entrenamiento`: Cantidad de registros
4. **Métricas**:
   - Prophet: `prophet_datos_entrenamiento`
   - XGBoost: `xgboost_mae`, `xgboost_r2`, `xgboost_rmse`
5. **Modelos**:
   - XGBoost se guarda como artefacto MLflow
   - Prophet se guarda como metadata (no es directamente compatible)
6. **Artefactos**:
   - `training_data_sample.csv`: Muestra de datos de entrenamiento

### **URL de MLflow**

- **Producción**: `https://mlflow.eddeso.com`
- **Local**: `http://localhost:5050`
- **Run específico**: `https://mlflow.eddeso.com/#/experiments/0/runs/{run_id}`

### **Configuración**

En `.env`:
```bash
MLFLOW_TRACKING_URI=https://mlflow.eddeso.com
```

Si no está configurado, el entrenamiento funciona igual, solo no se registra en MLflow.

---

## 🔌 Endpoints Disponibles {#endpoints-disponibles}

### **Servidores**
- `GET /api/servidores/` - Listar servidores
- `POST /api/servidores/` - Crear servidor
- `PUT /api/servidores/{id}/` - Actualizar servidor
- `DELETE /api/servidores/{id}/` - Eliminar servidor

### **Empresas**
- `GET /api/empresas-servidor/` - Listar empresas
- `POST /api/empresas-servidor/` - Crear empresa manualmente
- `PUT /api/empresas-servidor/{id}/` - Actualizar empresa
- `DELETE /api/empresas-servidor/{id}/` - Eliminar empresa

### **Sistema**
- `POST /api/sistema/descubrir_empresas/` - Sincronizar empresas (Celery)
- `GET /api/sistema/estado-descubrimiento/?task_id=XXX` - Ver progreso
- `POST /api/sistema/extraer_datos/` - Extraer datos de empresa

### **ML**
- `POST /api/ml/entrenar_modelos/` - Entrenar modelos
- `POST /api/ml/predecir_demanda/` - Predecir demanda

### **API Keys**
- `POST /api/api-keys/generar_api_key/` - Generar API Key
- `GET /api/api-keys/listar_api_keys/` - Listar API Keys
- `POST /api/api-keys/revocar_api_key/` - Revocar API Key
- `POST /api/api-keys/validar_api_key/` - Validar API Key (público)

### **VPN**
- `GET /api/vpn/configs/` - Listar configuraciones VPN
- `POST /api/vpn/configs/` - Crear configuración VPN
- `GET /api/vpn/configs/{id}/download_config/` - Descargar .conf

---

## 🔗 Asociación de NITs y Empresas {#asociacion-nits}

### **¿Cómo se Asocian?**

1. **Al crear API Key**:
   - Se proporciona un `nit` (ej: `"900123456"`)
   - El sistema busca todas las empresas con ese NIT (normalizado)
   - Se asocian automáticamente a la API Key

2. **Normalización de NIT**:
   - Se eliminan puntos, guiones, espacios
   - Ej: `"900.123.456-7"` → `"9001234567"`

3. **Método `actualizar_empresas_asociadas()`**:
   - Se llama automáticamente al crear/actualizar API Key
   - También se puede llamar manualmente si se agregan nuevas empresas

### **Ejemplo**

```
EmpresaServidor 1: NIT="900123456", año=2024
EmpresaServidor 2: NIT="900123456", año=2025
APIKeyCliente: nit="900123456"
  └─> empresas_asociadas = [EmpresaServidor 1, EmpresaServidor 2]
```

**Frontend**:
- Al validar API Key: `POST /api/api-keys/validar_api_key/`
- Retorna todas las empresas asociadas al NIT
- El usuario puede elegir qué empresa usar

---

## 📥 Extracción de Datos {#extraccion-datos}

### **¿Qué SQL se Ejecuta?**

El `DataManager.extraer_datos_empresa()` ejecuta una consulta SQL compleja que extrae:

```sql
SELECT 
  M.CODIGO as articulo_codigo,
  M.NOMBRE as articulo_nombre,
  M.CANTIDAD,
  M.PRECIO_UNITARIO,
  M.FECHA,
  M.TIPO_DOCUMENTO,
  M.TIPO_BODEGA,
  -- ... más campos
FROM MOVIMIENTOS M
WHERE M.FECHA BETWEEN ? AND ?
```

### **¿Dónde se Guarda?**

- **Tabla**: `movimientos_inventario` (PostgreSQL)
- **Modelo**: `MovimientoInventario`
- **Relación**: `empresa_servidor_id` → `EmpresaServidor`

### **Procesamiento en Chunks**

- **Chunk size**: 1000 registros
- **Razón**: Evitar sobrecarga de memoria y timeout
- **Progreso**: Se puede agregar logging para ver el progreso

### **Re-extracción**

- Si `forzar_reextraccion=True`: Elimina datos existentes y re-extrae
- Si `forzar_reextraccion=False`: Verifica si ya se extrajo en ese rango de fechas

---

## 🤖 Entrenamiento de Modelos {#entrenamiento-modelos}

### **¿Qué Datos se Usan?**

**TODAS las empresas con el mismo NIT**:
- Si entrenas con `empresa_servidor_id=1` (NIT: 900123456)
- El sistema busca todas las empresas con NIT="900123456"
- Usa datos de `MovimientoInventario` de todas esas empresas

### **¿Qué Modelos se Entrenan?**

1. **Prophet**:
   - Predicción de series temporales
   - Usa datos históricos de demanda mensual
   - Guarda: `empresa_{NIT}_prophet.joblib`

2. **XGBoost**:
   - Predicción de demanda con features adicionales
   - Usa: cantidad, precio, tipo de artículo, bodega, etc.
   - Guarda: `empresa_{NIT}_xgboost.joblib`

### **¿Dónde se Guardan?**

- **Directorio**: `manu/modelos_ml/`
- **Formato**: `.joblib` (pickle de scikit-learn)
- **Metadata**: `empresa_{NIT}_metadata.json`

### **MLflow**

- Si `MLFLOW_TRACKING_URI` está configurado:
  - Se crea un experimento: `"TNS_Demanda_Prediccion"`
  - Se registra cada entrenamiento como un "run"
  - Se guardan parámetros, métricas, y el modelo XGBoost
  - Se genera una URL para ver en MLflow UI

---

## 🎨 Pestañas de Configuración para el Frontend

### **Propuesta de Estructura**

#### **1. Pestaña "Servidores"**
- Listar servidores
- Crear/editar servidor
- Campos: nombre, host, usuario, password, puerto, ruta_maestra

#### **2. Pestaña "VPN"**
- Listar configuraciones VPN
- Crear nueva VPN
- Descargar .conf
- Ver estado de conexión

#### **3. Pestaña "Empresas"**
- Listar empresas descubiertas
- Botón "Sincronizar" → `POST /api/sistema/descubrir_empresas/`
- Modal de progreso (SweetAlert2) → `GET /api/sistema/estado-descubrimiento/`
- Botón "Extraer Datos" → `POST /api/sistema/extraer_datos/`
- Mostrar: nombre, NIT, año fiscal, última extracción, estado

#### **4. Pestaña "API Keys"**
- Listar API Keys
- Generar nueva API Key → `POST /api/api-keys/generar_api_key/`
- Campos: NIT, nombre_cliente, días_validez
- Mostrar: API Key (solo una vez), empresas asociadas, fecha caducidad
- Revocar API Key

#### **5. Pestaña "ML / Modelos"**
- Listar modelos entrenados (leer de `manu/modelos_ml/`)
- Botón "Entrenar Modelo" → `POST /api/ml/entrenar_modelos/`
- Mostrar: NIT, fecha entrenamiento, métricas, link a MLflow
- Predecir demanda → `POST /api/ml/predecir_demanda/`

#### **6. Pestaña "Configuración"**
- Configuración general del sistema
- Variables de entorno (solo lectura)
- Estado de servicios (Celery, MLflow, etc.)

---

## ✅ Checklist de Configuración Completa

- [ ] 1. Crear Servidor
- [ ] 2. Crear VPN (si es necesario)
- [ ] 3. Sincronizar empresas (descubrir)
- [ ] 4. Extraer datos de empresas
- [ ] 5. Generar API Key
- [ ] 6. Entrenar modelos (opcional)
- [ ] 7. Configurar e-commerce (si aplica)
- [ ] 8. Configurar autopago (si aplica)

---

## 📝 Notas Importantes

1. **NIT + Año Fiscal es Único**: No puede haber dos empresas con el mismo NIT y año fiscal, incluso en diferentes servidores.

2. **Asociación Automática**: Las API Keys se asocian automáticamente a todas las empresas del mismo NIT.

3. **MLflow es Opcional**: El sistema funciona sin MLflow, solo no se registran los entrenamientos.

4. **Celery es Necesario**: Para tareas largas como "descubrir empresas", Celery es esencial para evitar timeouts.

5. **Extracción de Datos**: Se guarda en PostgreSQL, no en Firebird. Esto permite análisis rápido sin conectar a Firebird cada vez.

6. **Modelos por NIT**: Los modelos se entrenan usando datos de TODAS las empresas del mismo NIT, no solo una.

---

## 🔍 Próximos Pasos

1. **Migrar `extraer_datos` a Celery**: Para manejar empresas con muchos datos
2. **Migrar `entrenar_modelos` a Celery**: Para entrenamientos largos
3. **Agregar progreso a `extraer_datos`**: Similar a `descubrir_empresas`
4. **Dashboard de métricas**: Mostrar estadísticas de empresas, extracciones, modelos
5. **Programación automática**: Cron jobs para re-extraer datos y re-entrenar modelos

