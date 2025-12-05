# Integración APIDIAN

Esta app proporciona una integración completa con APIDIAN, incluyendo:
- Conexión directa a la base de datos MariaDB de APIDIAN
- Endpoints para enviar eventos a la API de APIDIAN
- Servicios para consultar datos de APIDIAN

## Configuración

### Variables de Entorno

Agregar al archivo `.env`:

```env
# Configuración Base de Datos APIDIAN (MariaDB)
APIDIAN_DB_HOST=45.149.204.184
APIDIAN_DB_PORT=3307
APIDIAN_DB_USER=apidian
APIDIAN_DB_PASSWORD=tu_password_aqui
APIDIAN_DB_NAME=apidian

# Configuración API APIDIAN (ya existente)
API_DIAN_ROUTE=http://45.149.204.184:81
TOKEN_API_DIAN_BASIC=tu_token_aqui
```

## Endpoints Disponibles

### 1. Enviar Evento (Send Event)

**POST** `/api/apidian/send-event/`

Envía un evento directamente a APIDIAN con el XML en base64.

**Body:**
```json
{
    "event_id": 1,
    "allow_cash_documents": false,
    "sendmail": false,
    "base64_attacheddocument_name": "ad09001495660102400018741.xml",
    "base64_attacheddocument": "PD94bWw....",
    "type_rejection_id": null,
    "resend_consecutive": false
}
```

**Respuesta:**
```json
{
    "success": true,
    "message": "Evento enviado exitosamente",
    "data": { ... }
}
```

### 2. Enviar Evento desde Archivo

**POST** `/api/apidian/send-event-from-file/`

Envía un evento desde un archivo XML local.

**Body:**
```json
{
    "event_id": 1,
    "xml_file_path": "/ruta/al/archivo.xml",
    "allow_cash_documents": false,
    "sendmail": false,
    "type_rejection_id": null,
    "resend_consecutive": false
}
```

### 3. Enviar Evento desde Documento en BD

**POST** `/api/apidian/send-event-from-document/`

Envía un evento desde un documento existente en la BD de APIDIAN.

**Body:**
```json
{
    "event_id": 1,
    "document_id": 123,
    "allow_cash_documents": false,
    "sendmail": false,
    "type_rejection_id": null,
    "resend_consecutive": false
}
```

### 4. Listar Eventos Disponibles

**GET** `/api/apidian/events/`

Obtiene la lista de eventos disponibles en APIDIAN.

### 5. Listar Tipos de Rechazo

**GET** `/api/apidian/type-rejections/`

Obtiene la lista de tipos de rechazo disponibles.

### 6. Listar Documentos

**GET** `/api/apidian/documents/`

Lista documentos de APIDIAN con filtros opcionales.

**Query Parameters:**
- `nit`: Filtrar por NIT
- `fecha_desde`: Fecha desde (formato: YYYY-MM-DD)
- `fecha_hasta`: Fecha hasta (formato: YYYY-MM-DD)

**Ejemplo:**
```
GET /api/apidian/documents/?nit=900123456&fecha_desde=2025-01-01
```

### 7. Obtener Documento por ID

**GET** `/api/apidian/documents/{document_id}/`

Obtiene un documento específico por ID.

## Uso de los Servicios

### Conexión a Base de Datos

```python
from apidian.services.db_connection import ApidianDBConnection

# Usar como context manager
with ApidianDBConnection() as db:
    results = db.execute_query("SELECT * FROM events")
```

### Cliente API

```python
from apidian.services.apidian_client import ApidianAPIClient

client = ApidianAPIClient()
result = client.send_event(
    event_id=1,
    attached_document_name="documento.xml",
    attached_document_base64="PD94bWw...",
    sendmail=True
)
```

### Consultas de Datos

```python
from apidian.services.data_queries import ApidianDataQueries

queries = ApidianDataQueries()
events = queries.get_events()
documents = queries.get_documents_by_nit("900123456")
```

## Estructura de Archivos

```
apidian/
├── __init__.py
├── models.py              # Modelos para serialización
├── serializers.py         # Serializers para validación
├── views.py               # ViewSets con endpoints
├── urls.py                # Configuración de URLs
├── services/
│   ├── __init__.py
│   ├── db_connection.py   # Conexión a MariaDB
│   ├── apidian_client.py  # Cliente para API REST
│   └── data_queries.py    # Consultas a la BD
└── README.md              # Esta documentación
```

## Notas

- La conexión a la BD de APIDIAN se establece bajo demanda
- Los servicios manejan automáticamente la conexión/desconexión
- Todos los endpoints requieren autenticación (IsAuthenticated)
- Los errores se registran en los logs de Django

