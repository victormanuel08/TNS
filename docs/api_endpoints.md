# API Reference - TNSFULL

Esta guia concentra todos los endpoints expuestos por el backend (autenticacion, Scraping DIAN, documentos, asistencia/ML y puente TNS). Todos los ejemplos usan `{{base_url}} = http://localhost:8000` a menos que se indique lo contrario.

## Tabla de contenido
1. [Autenticacion (JWT y API keys)](#1-autenticacion)
2. [Headers y convenciones](#2-headers-y-convenciones)
3. [Scraping DIAN](#3-scraping-dian)
4. [Documentos procesados](#4-documentos-procesados)
5. [Sistema (descubrimiento / extraccion)](#5-sistema-descubrimiento--extraccion)
6. [Motor de Machine Learning](#6-motor-de-machine-learning)
7. [Consulta natural (IA)](#7-consulta-natural-ia)
8. [Puente TNS](#8-puente-tns)
9. [Coleccion Postman y buenas practicas](#9-coleccion-postman-y-buenas-practicas)

---

## 1. Autenticacion

### Login JWT
- **POST** `/api/auth/login/`
- **Body**
  ```json
  {
    "username": "admin",
    "password": "********"
  }
  ```
- **Respuesta**
  ```json
  {
    "access": "<jwt>",
    "refresh": "<jwt>",
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "is_superuser": true,
      "puede_gestionar_api_keys": true,
      "default_template": "app",
      "default_empresa_id": 12,
      "subdomain": "app",
      "preferred_template": "app",
      "empresas": [
        {
          "empresa_servidor_id": 12,
          "nombre": "Contoso SAS",
          "nit": "900123456",
          "anio_fiscal": 2025,
          "codigo": "01",
          "preferred_template": "restaurant"
        }
      ]
    }
  }
  ```
- Todos los requests deben incluir el subdominio activo: `X-Subdomain: <subdominio>`. El login solo es válido cuando el usuario pertenece a ese subdominio.

### Refresh token
- **POST** `/api/auth/refresh/`
- **Body** `{"refresh": "<jwt_refresh>"}`
- **Respuesta** `{"access": "<jwt>"}`

### Logout
- **POST** `/api/auth/logout/`
- **Headers** `Authorization: Bearer <jwt>`
- **Body** `{"refresh_token": "<jwt_refresh>"}`

Las API keys tambien se aceptan en la mayoria de endpoints enviando `Api-Key: <token>` o `api_key` en los headers.

---

## 2. Headers y convenciones
- `Authorization: Bearer <access_token>` para usuarios internos.
- `Api-Key: <token>` para clientes externos (limita el acceso a las empresas asociadas al NIT).
- Todas las fechas usan ISO-8601 (`YYYY-MM-DD`).
- En respuestas paginadas DRF envia `{ "count": N, "results": [...] }`.

---

## 3. Scraping DIAN

### Crear sesion
- **POST** `/dian/api/sessions/`
- **Body**
  ```json
  {
    "url": "https://catalogo-vpfe.dian.gov.co/User/AuthToken?pk=...",
    "tipo": "Sent",
    "nit": "900123456",
    "fecha_desde": "2025-01-01",
    "fecha_hasta": "2025-01-31"
  }
  ```
- El serializer ajusta `fecha_ejecutado` para evitar traslapes.

### Quick Scrape
- **POST** `/dian/api/sessions/quick_scrape/`
- Mismo payload que crear sesion; crea + inicia en un llamado (ideal para API keys o pruebas rapidas).

### Iniciar scraping
- **POST** `/dian/api/sessions/{id}/start_scraping/`
- Cambia estado a `running` y dispara la tarea Celery `run_dian_scraping_task`.

### Test connection
- **POST** `/dian/api/sessions/test_connection/`
- **Body** `{ "url": "<AuthToken DIAN>" }`
- Permite pruebas anonimas (no persiste la sesion).

### Descargas
- **GET** `/dian/api/sessions/{id}/download_json/`
- **GET** `/dian/api/sessions/{id}/download_excel/`
- Requieren que la sesion este `completed`; devuelven los archivos generados por `FileProcessor`.

---

## 4. Documentos procesados

### Listar documentos
- **GET** `/dian/api/documents/`
- Query params: `session_id`, `nit`, `tipo`, `fecha_desde`, `fecha_hasta`.

### Exportar
- **GET** `/dian/api/documents/export/?format=excel`
- Usa los mismos filtros que el listado. `format=excel` genera XLSX, cualquier otro valor devuelve JSON.

---

## 5. Sistema (descubrimiento / extraccion)
Base: `/assistant/api/sistema/`

### 5.1 Inicializar Sistema
- **POST** `/inicializar_sistema/`
- Resetea/valida configuración general del sistema
- Crea o carga el archivo maestro (`data/maestro.pkl`)
- **Response:**
  ```json
  {
    "estado": "sistema_inicializado",
    "version": "2.0"
  }
  ```

### 5.2 Descubrir Empresas
- **POST** `/descubrir_empresas/`
- **Body:**
  ```json
  {
    "servidor_id": 1
  }
  ```
- **Qué hace:**
  1. Conecta al servidor usando `ruta_maestra` (ADMIN.gdb)
  2. Ejecuta: `SELECT CODIGO, NOMBRE, NIT, ANOFIS, ARCHIVO FROM EMPRESAS WHERE NIT IS NOT NULL`
  3. Para cada empresa: crea o actualiza `EmpresaServidor`
  4. Valida unicidad global por NIT + año fiscal (evita duplicados entre servidores)
- **Response:**
  ```json
  {
    "estado": "empresas_descubiertas",
    "total_empresas": 5
  }
  ```
- **Nota**: Ver [`FLUJO_SISTEMA.md`](./FLUJO_SISTEMA.md) para detalles completos del proceso.

### 5.3 Extraer Datos
- **POST** `/extraer_datos/`
- **Body:**
  ```json
  {
    "empresa_servidor_id": 1,
    "fecha_inicio": "2025-01-01",
    "fecha_fin": "2025-01-31",
    "forzar_reextraccion": false
  }
  ```
- **Qué hace:**
  1. Conecta a la base de datos de la empresa (usando `ruta_base`)
  2. Ejecuta la consulta SQL configurada (`consulta_sql`) con parámetros de fecha
  3. Procesa resultados en chunks de 1000 registros
  4. Crea registros `MovimientoInventario` en PostgreSQL
  5. Calcula campos derivados (valor_total, lead_time_dias, tipo_bodega)
  6. Actualiza `ultima_extraccion` de la empresa
- **Response:**
  ```json
  {
    "estado": "exito",
    "registros_guardados": 15234,
    "total_encontrados": 15234,
    "chunks_procesados": 16
  }
  ```
- **Nota**: Si `forzar_reextraccion=false` y ya existen datos para ese rango, retorna `{"estado": "ya_extraido"}`.

### 5.4 Gestión de Servidores
- **GET** `/assistant/api/servidores/` - Lista todos los servidores
- **POST** `/assistant/api/servidores/` - Crea un nuevo servidor
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
- **PATCH** `/assistant/api/servidores/{id}/` - Actualiza un servidor
- **DELETE** `/assistant/api/servidores/{id}/` - Elimina un servidor

### 5.5 Gestión de Empresas
- **GET** `/assistant/api/empresas-servidor/` - Lista todas las empresas
- **GET** `/assistant/api/empresas-servidor/{id}/` - Obtiene una empresa específica
- **PATCH** `/assistant/api/empresas-servidor/{id}/` - Actualiza empresa (útil para configurar `consulta_sql`)
  ```json
  {
    "consulta_sql": "SELECT TIPO_DOCUMENTO, FECHA, ARTICULO_CODIGO, ... FROM MOVIMIENTOS WHERE FECHA BETWEEN ? AND ?"
  }
  ```

---

## 6. Motor de Machine Learning
Base: `/assistant/api/ml/`

1. **Entrenar modelos** – `POST /entrenar_modelos/`
   ```json
   {
     "empresa_servidor_id": 1,
     "fecha_inicio": "2023-01-01",
     "fecha_fin": "2023-12-31"
   }
   ```
2. **Predecir demanda** – `POST /predecir_demanda/`
   ```json
   {
     "modelo_id": "empresa_900123456",
     "meses": 6
   }
   ```
3. **Recomendaciones de compra** – `POST /recomendaciones_compras/`
   ```json
   {
     "modelo_id": "empresa_900123456",
     "meses": 6,
     "nivel_servicio": 0.95
   }
   ```

Las respuestas incluyen los datos calculados (forecast, MAE, recomendaciones, etc.).

---

## 7. Consulta natural (IA)
- **POST** `/assistant/api/consulta-natural/pregunta_inteligente/`
- **Headers**: JWT o API key (si se usa API key `empresa_servidor_id` es opcional).
- **Body**
  ```json
  {
    "consulta": "Que articulos debo comprar el proximo mes?",
    "empresa_servidor_id": 1
  }
  ```
- **Respuesta**
  ```json
  {
    "consulta_original": "...",
    "explicacion_nino_inteligente": "...",
    "datos_tecnicos_completos": { 
      "series": [], 
      "insights": [],
      "mlflow_run_id": "abc123...",  // Si MLflow está disponible
      "mlflow_ui_url": "http://localhost:5000/#/experiments/0/runs/abc123..."  // Si MLflow está disponible
    }
  }
  ```
  
  **Nota**: Para predicciones (demanda, recomendaciones), las respuestas incluyen enlaces a MLflow UI si está configurado. Ver [MLFLOW_INTEGRATION.md](./MLFLOW_INTEGRATION.md).

---

## 8. Puente TNS
Base: `/assistant/api/tns/`. Todos los llamados requieren JWT o API key.

### 8.1 Query SQL
- **POST** `/query/`
  ```json
  {
    "empresa_servidor_id": 1,
    "sql": "SELECT FIRST 10 * FROM CLIENTES WHERE NIT = ?",
    "params": ["900123456"]
  }
  ```

### 8.2 Stored Procedure
- **POST** `/procedure/`
  ```json
  {
    "empresa_servidor_id": 1,
    "procedure": "TNS_SP_CLIENTE",
    "params": { "NIT": "900123456" }
  }
  ```

### 8.3 Emitir factura
- **POST** `/emit_invoice/`
  ```json
  {
    "empresa_servidor_id": 1,
    "codcomp": "FV",
    "codprefijo": "FE",
    "formapago": "CO",
    "nittri": "13279115"
  }
  ```
- Retorna `{ "numero": "<consecutivo>" }` si la insercion fue exitosa.

### 8.4 Listar tablas
- **GET** `/tables/?empresa_servidor_id=1`
- Devuelve `{ "tables": ["CLIENTES", "FACTURAS", ...] }`.

### 8.5 Consultar empresas via ADMIN.gdb
- **GET** `/admin_empresas/?empresa_servidor_id=1&search_nit=900123456`
- **Respuesta**
  ```json
  {
    "count": 2,
    "nit_buscado": "900123456",
    "empresas": [
      { "CODIGO": "01", "NOMBRE": "EMPRESA DEMO", "ANOFIS": 2025, "ARCHIVO": "C:/Visual TNS/EMPRESA.GDB" }
    ]
  }
  ```

### 8.6 Validar usuario TNS
- **POST** `/validate_user/`
  ```json
  {
    "empresa_servidor_id": 1,
    "username": "ADMIN",
    "password": "secreto"
  }
  ```
- **Respuesta** incluye los campos de `VALIDATE` y un objeto `MODULOS` con los permisos permitidos.

---

## 9. Coleccion Postman y buenas practicas
- La coleccion `postman_collection.json` (en la raiz del repo) contiene ejemplos para todos los endpoints mencionados arriba. Usa las variables `{{base_url}}`, `{{jwt_token}}`, `{{api_key}}`, `{{session_id}}` y `{{subdomain}}`.
- Siempre que se agregue o cambie un endpoint:
  1. Actualiza esta documentacion.
  2. Exporta/actualiza la coleccion Postman con el flujo correspondiente.
  3. Si aplica, agrega ejemplos de request/response en la seccion adecuada.
- Recomendacion: documentar tambien la version del backend en la coleccion (variable `{{api_version}}`).

---
