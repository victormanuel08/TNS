# Scraping DIAN en BCE - Documentación Técnica

## 📋 Resumen

BCE tiene **dos sistemas** para obtener datos de la DIAN:

1. **Sistema Antiguo (API Externa)**: Usa un servicio externo vía API REST
2. **Sistema Nuevo (Scraping Directo)**: Hace scraping directo a la DIAN usando sesiones

---

## 🔧 Sistema 1: API Externa (DianRequestsViewSet)

### Endpoint que Llama

**URL Base**: Se obtiene de la tabla `varios` con código `ROUTEAPI`

**Endpoint Completo**:
```
GET {ROUTEAPI}/information/{nit}/{start}/{end}
```

### Ejemplo de URL Construida

```python
# Código en bce/backend/utils/views.py línea 2110
route = varios.objects.filter(code='ROUTEAPI').first()
url = f"{route.value}/information/{nit}/{start}/{end}"
# Ejemplo: "https://api-scraping-dian.com/information/900123456/2025-01-01/2025-01-31"
```

### Headers Enviados

```python
headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': f'Bearer {token}'
}
```

### Token (Authorization)

- **Origen**: Campo `token` del modelo `Third` (tercero)
- **Búsqueda**: Se busca el `Third` por `id_number` (NIT)
- **Código**:
  ```python
  third = Third.objects.filter(id_number=nit).first()
  token = third.token
  ```

### Parámetros en la URL

- `{nit}`: NIT de la empresa (sin puntos ni guiones)
- `{start}`: Fecha inicio (formato: `YYYY-MM-DD`)
- `{end}`: Fecha fin (formato: `YYYY-MM-DD`)

### Payload

**NO hay payload en el body** (es un GET request). Los parámetros van en la URL.

### Respuesta Esperada

```json
{
  "success": true,
  "data": [
    {
      "type_document_id": 1,
      "documents": [...],
      "document_type": {...},
      "company": {...}
    }
  ]
}
```

### Ubicación del Código

- **Archivo**: `bce/backend/utils/views.py`
- **Clase**: `DianRequestsViewSet`
- **Método**: `_fetch_dian_month_data()` (línea 2073)
- **Endpoint BCE**: `POST /api/dian-requests/get-invoices/`

### Flujo Completo

1. Frontend llama: `POST /api/dian-requests/get-invoices/`
2. Payload del frontend:
   ```json
   {
     "nit": "900123456",
     "desde": "2025-01-01",
     "hasta": "2025-01-31",
     "document_type_id": 1,
     "prefixes": ["FV", "NC"]
   }
   ```
3. Backend busca `Third` por NIT
4. Backend obtiene `token` de `Third.token`
5. Backend busca `ROUTEAPI` en tabla `varios`
6. Backend construye URL: `{ROUTEAPI}/information/{nit}/{start}/{end}`
7. Backend hace GET request con header `Authorization: Bearer {token}`
8. Backend procesa respuesta y retorna documentos

---

## 🔧 Sistema 2: Scraping Directo (Sesiones DIAN)

### Endpoint que Llama

**Endpoint BCE**: `POST /api/dian/api/sessions/`

### Payload Enviado

```json
{
  "nit": "900123456",
  "url": "https://catalogo-vpfe.dian.gov.co/User/AuthToken?pk=...",
  "tipo": "Sent",
  "fecha_desde": "2025-01-01",
  "fecha_hasta": "2025-01-31"
}
```

### Campos del Payload

- **`nit`**: NIT de la empresa (normalizado, solo números)
- **`url`**: URL completa del token de autenticación de la DIAN (obtenida después de autenticarse en MUISCA)
- **`tipo`**: Tipo de documentos a obtener
  - `"Sent"`: Documentos emitidos
  - `"Received"`: Documentos recibidos
- **`fecha_desde`**: Fecha inicio (formato: `YYYY-MM-DD`)
- **`fecha_hasta`**: Fecha fin (formato: `YYYY-MM-DD`)

### Headers Enviados

```javascript
{
  'x-api-key': apiKey.value,  // API Key del cliente
  'Content-Type': 'application/json'
}
```

### Flujo Completo

1. **Crear Sesión**:
   ```javascript
   POST /api/dian/api/sessions/
   Body: { nit, url, tipo, fecha_desde, fecha_hasta }
   ```
   - Retorna: `{ id, status, documents_downloaded }`

2. **Iniciar Scraping**:
   ```javascript
   POST /api/dian/api/sessions/{id}/start_scraping/
   ```
   - Cambia estado a `running`
   - Dispara tarea Celery `run_dian_scraping_task`

3. **Monitorear Sesión**:
   ```javascript
   GET /api/dian/api/sessions/{id}/
   ```
   - Estado: `pending`, `running`, `completed`, `failed`
   - `documents_downloaded`: Cantidad de documentos descargados

4. **Descargar Resultados**:
   ```javascript
   GET /api/dian/api/sessions/{id}/download_json/
   GET /api/dian/api/sessions/{id}/download_excel/
   ```

### Ubicación del Código

- **Frontend**: `bce/frontend/pages/ScrapingDian.vue`
- **Método**: `executeScraping()` (línea 1186)
- **Backend**: Probablemente en `bce/backend/dian/` o similar

### Quick Scrape (Alternativa)

También existe un endpoint que crea e inicia en un solo llamado:

```javascript
POST /api/dian/api/sessions/quick_scrape/
Body: { nit, url, tipo, fecha_desde, fecha_hasta }
```

---

## 🔍 Configuración Necesaria

### Para Sistema 1 (API Externa)

1. **ROUTEAPI en tabla `varios`**:
   ```sql
   INSERT INTO varios (code, value) 
   VALUES ('ROUTEAPI', 'https://api-scraping-dian.com');
   ```

2. **Token en modelo `Third`**:
   ```python
   third = Third.objects.get(id_number='900123456')
   third.token = 'token-del-servicio-externo'
   third.save()
   ```

### Para Sistema 2 (Scraping Directo)

1. **API Key del cliente** (para autenticación)
2. **URL de autenticación DIAN** (obtenida manualmente de MUISCA)

---

## 📊 Comparación de Sistemas

| Característica | Sistema 1 (API Externa) | Sistema 2 (Scraping Directo) |
|----------------|-------------------------|-------------------------------|
| **Método** | GET request a API externa | Scraping directo a DIAN |
| **Autenticación** | Bearer token (de `Third.token`) | URL de autenticación DIAN |
| **Configuración** | ROUTEAPI + token en Third | API Key + URL DIAN |
| **Procesamiento** | Síncrono | Asíncrono (Celery) |
| **Estado** | Respuesta inmediata | Sesiones con estados |
| **Endpoint BCE** | `/api/dian-requests/get-invoices/` | `/api/dian/api/sessions/` |

---

## 🎯 Endpoints BCE Disponibles

### Sistema 1 (API Externa)

- **POST** `/api/dian-requests/get-invoices/`
  - Body: `{ nit, desde, hasta, document_type_id, prefixes }`
  - Retorna: Documentos directamente

### Sistema 2 (Scraping Directo)

- **POST** `/api/dian/api/sessions/` - Crear sesión
- **POST** `/api/dian/api/sessions/quick_scrape/` - Crear e iniciar
- **POST** `/api/dian/api/sessions/{id}/start_scraping/` - Iniciar scraping
- **POST** `/api/dian/api/sessions/test_connection/` - Probar conexión
- **GET** `/api/dian/api/sessions/{id}/` - Obtener sesión
- **GET** `/api/dian/api/sessions/{id}/download_json/` - Descargar JSON
- **GET** `/api/dian/api/sessions/{id}/download_excel/` - Descargar Excel
- **GET** `/api/dian/api/documents/` - Listar documentos
- **GET** `/api/dian/api/documents/export/` - Exportar documentos

---

## 📦 Qué Descarga el Sistema de Scraping Directo

### Proceso de Descarga y Procesamiento

1. **Descarga desde DIAN**:
   - El scraper descarga archivos **ZIP** desde la DIAN
   - Los ZIPs contienen archivos **XML** (facturas electrónicas en formato UBL)

2. **Procesamiento de Archivos**:
   - Extrae los XMLs de los ZIPs
   - Parsea cada XML usando `UBLXMLParser`
   - Extrae información estructurada de cada factura

3. **Generación de Archivos de Salida**:
   - **JSON**: Contiene todos los documentos en formato JSON estructurado
   - **Excel**: Contiene dos hojas con información tabular

### Estructura del JSON

Cada documento en el JSON contiene:

```json
{
  "TipoDocumento": "Factura",
  "TipoBusqueda": "Sent",
  "Numero de Factura": "FV-001",
  "CUFE": "...",
  "Fecha de Creación": "2025-01-15",
  "Fecha de Vencimiento": "2025-01-30",
  "Moneda": "COP",
  "NIT del Emisor": "900123456",
  "Razon Social del Emisor": "EMPRESA SAS",
  "NIT del Receptor": "800654321",
  "Razon Social del Receptor": "CLIENTE LTDA",
  "Metodo de Pago": "Efectivo",
  "Sub Total": 1000000.00,
  "Impuestos Cabecera": 190000.00,
  "Retenciones": 0.00,
  "Total a Pagar": 1190000.00,
  "TaxBreakdown": [
    {
      "code": "01",
      "name": "IVA",
      "percent": 19.0,
      "taxable_amount": 1000000.00,
      "amount": 190000.00
    }
  ],
  "LineItems": [
    {
      "Nombre del Producto": "Producto 1",
      "Referencia": "REF001",
      "Unidad de Medida": "UN",
      "Cantidad": 10.0,
      "Precio Unitario": 100000.00,
      "Total": 1000000.00,
      "taxes": [...],
      "total_tax_line": 190000.00
    }
  ]
}
```

### Estructura del Excel

**Hoja 1: "Documentos"** (Resumen)
- TipoDocumento
- Numero
- CUFE
- Fecha
- Vencimiento
- Moneda
- NIT_Emisor, Nombre_Emisor
- NIT_Receptor, Nombre_Receptor
- MetodoPago
- Subtotal, ImpuestosCabecera, Retenciones, TotalPagar
- Lineas (cantidad de líneas)

**Hoja 2: "Lineas"** (Detalle de productos)
- TipoDocumento, Numero, CUFE, Fecha
- NIT_Emisor, NIT_Receptor
- Linea (número de línea)
- Nombre_Producto, Referencia, Medida
- Cantidad, PrecioUnitario, TotalLinea
- ImpCode, ImpName, ImpPercent, ImpBase, ImpValor

### Ubicación del Código

- **FileProcessor**: `manu/apps/dian_scraper/services/file_processor.py`
- **Views**: `manu/apps/dian_scraper/views.py` (líneas 77-112)
- **Modelo**: `manu/apps/dian_scraper/models.py` - `ScrapingSession`
  - Campos: `json_file`, `excel_file` (FileField)

### Flujo de Generación

1. **Scraping completa** → Descarga ZIPs de DIAN
2. **FileProcessor.process_downloaded_files()** → Procesa ZIPs
3. **Extrae XMLs** → Parsea con UBLXMLParser
4. **Genera JSON** → `_generate_output_files()` crea JSON
5. **Genera Excel** → Crea Excel con pandas (2 hojas)
6. **Guarda en BD** → Actualiza `session.json_file` y `session.excel_file`
7. **Usuario descarga** → Endpoints `download_json/` y `download_excel/`

---

## 📝 Notas Importantes

1. **Sistema 1** usa un servicio externo (probablemente un microservicio de scraping)
2. **Sistema 2** hace scraping directo a la DIAN usando la URL de autenticación
3. Ambos sistemas pueden coexistir
4. El **token** en Sistema 1 es diferente al **URL** en Sistema 2
5. Sistema 2 requiere que el usuario se autentique manualmente en MUISCA y copie la URL
6. **Sistema 2 genera automáticamente JSON y Excel** cuando el scraping se completa
7. Los archivos se guardan en `MEDIA_ROOT/dian_exports/` con timestamp
8. El Excel tiene **dos hojas**: resumen de documentos y detalle de líneas

---

## 🔗 Referencias

- **Código Sistema 1**: `bce/backend/utils/views.py` - `DianRequestsViewSet`
- **Código Sistema 2 Frontend**: `bce/frontend/pages/ScrapingDian.vue`
- **Documentación API**: `docs/api_endpoints.md`

