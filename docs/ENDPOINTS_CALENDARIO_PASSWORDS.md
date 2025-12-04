# Documentación de Endpoints: Calendario Tributario y Passwords de Entidades

## 📅 Calendario Tributario

### 1. Obtener Eventos para un NIT (GET)

**Endpoint:** `GET /api/calendario-tributario/eventos/`

**Autenticación:** 
- ✅ Requiere API Key válida (puede consultar eventos de sus empresas asociadas)
- ✅ O ser superusuario autenticado (puede consultar cualquier empresa)
- ❌ NO es público - requiere autenticación

**Query Parameters (TODOS OPCIONALES):**
- `nit` (opcional): NIT de la empresa específica (sin dígito de verificación). Si no se envía, retorna eventos de TODAS las empresas asociadas a tu API Key.
- `empresa_id` (opcional): ID de la empresa en MANU. Si no se envía, retorna eventos de TODAS las empresas asociadas a tu API Key.
- `fecha_desde` (opcional): Fecha desde (formato: `YYYY-MM-DD`)
- `fecha_hasta` (opcional): Fecha hasta (formato: `YYYY-MM-DD`)
- `tipo_regimen` (opcional): Código del régimen tributario (ej: `GC`, `SIM`, `ORD`)

**Comportamiento:**
- Si solo envías API Key (sin `nit` ni `empresa_id`): Retorna eventos de TODAS tus empresas asociadas
- Si envías `nit` o `empresa_id`: Retorna eventos solo de esa empresa (debe estar autorizada)

**Ejemplo de Request:**
```bash
GET /api/calendario-tributario/eventos/?nit=900869750&fecha_desde=2024-01-01&fecha_hasta=2024-12-31
Headers:
  Authorization: Bearer <token>
  # O
  Api-Key: <api_key>
```

**Ejemplo de Response:**
```json
{
  "eventos": [
    {
      "id": 1,
      "impuesto": {
        "codigo": "IVA",
        "nombre": "Impuesto al Valor Agregado",
        "descripcion": "IVA mensual"
      },
      "fecha_limite": "2024-12-31",
      "descripcion": "Declaración y pago IVA",
      "tipo_tercero": "PJ",
      "tipo_regimen": "GC",
      "digitos_nit": "0",
      "dias_restantes": 30
    }
  ],
  "total": 1,
  "filtros": {
    "nit": "900869750",
    "empresa_id": null,
    "fecha_desde": "2024-01-01",
    "fecha_hasta": "2024-12-31",
    "tipo_regimen": null
  }
}
```

---

### 2. Obtener Eventos para Múltiples NITs (POST) ⭐ NUEVO

**Endpoint:** `POST /api/calendario-tributario/eventos-multiples/`

**Autenticación:** 
- ✅ Requiere API Key válida (puede consultar eventos de sus empresas asociadas)
- ✅ O ser superusuario autenticado (puede consultar cualquier empresa)
- ❌ NO es público - requiere autenticación

**Body (JSON):**
```json
{
  "nits": ["900869750", "132791157"],  // OPCIONAL: Si no se envía, usa TODAS tus empresas
  "fecha_desde": "2024-01-01",  // Opcional
  "fecha_hasta": "2024-12-31",  // Opcional
  "tipo_regimen": "GC"  // Opcional
}
```

**Campos:**
- `nits` (opcional): Lista de NITs (sin dígito de verificación). Si no se envía o está vacía, usa automáticamente TODAS las empresas asociadas a tu API Key.
- `fecha_desde` (opcional): Fecha desde (formato: `YYYY-MM-DD`)
- `fecha_hasta` (opcional): Fecha hasta (formato: `YYYY-MM-DD`)
- `tipo_regimen` (opcional): Código del régimen tributario

**Comportamiento:**
- Si no envías `nits` o está vacío: Retorna eventos de TODAS tus empresas asociadas automáticamente
- Si envías `nits`: Solo retorna eventos de esos NITs (deben estar autorizados)

**Ejemplo de Request:**
```bash
POST /api/calendario-tributario/eventos-multiples/
Headers:
  Authorization: Bearer <token>
  Content-Type: application/json
Body:
{
  "nits": ["900869750", "132791157"],
  "fecha_desde": "2024-01-01",
  "fecha_hasta": "2024-12-31"
}
```

**Ejemplo de Response:**
```json
{
  "resultados": {
    "900869750": {
      "nit_original": "900869750",
      "nit_normalizado": "900869750",
      "total_eventos": 5,
      "eventos": [
        {
          "id": 1,
          "impuesto": {
            "codigo": "IVA",
            "nombre": "Impuesto al Valor Agregado",
            "descripcion": "IVA mensual"
          },
          "fecha_limite": "2024-12-31",
          "descripcion": "Declaración y pago IVA",
          "tipo_tercero": "PJ",
          "tipo_regimen": "GC",
          "digitos_nit": "0",
          "dias_restantes": 30
        }
      ]
    },
    "132791157": {
      "nit_original": "132791157",
      "nit_normalizado": "132791157",
      "total_eventos": 3,
      "eventos": [...]
    }
  },
  "total_nits": 2,
  "total_eventos": 8,
  "filtros": {
    "fecha_desde": "2024-01-01",
    "fecha_hasta": "2024-12-31",
    "tipo_regimen": null
  }
}
```

**Notas Importantes:**
- Los NITs se normalizan automáticamente (se eliminan puntos, guiones y espacios)
- **NO se requiere dígito de verificación** - el sistema usa los últimos dígitos del NIT para filtrar eventos
- El sistema busca eventos que coincidan con:
  - Último dígito del NIT (ej: NIT `900869750` → busca dígitos `"0"`)
  - Últimos dos dígitos del NIT (ej: NIT `900869750` → busca dígitos `"50"`)
  - Dígitos vacíos (`""`) que aplican a todos los NITs

**Seguridad:**
- Si usas API Key, solo puedes consultar eventos de empresas asociadas a tu API Key
- Si eres superusuario, puedes consultar eventos de cualquier empresa
- Si intentas consultar una empresa no autorizada, recibirás error 403

---

## 🔐 Passwords de Entidades

### Listar Contraseñas (GET) ⭐ MODIFICADO

**Endpoint:** `GET /api/contrasenas-entidades/`

**Autenticación:** Requiere API Key o autenticación de usuario + **Validación TNS**

**IMPORTANTE:** Ahora requiere validación TNS de la empresa antes de mostrar las contraseñas.

**Autenticación:**
- ✅ Requiere API Key válida (retorna passwords de sus empresas asociadas automáticamente)
- ✅ O ser superusuario autenticado (puede ver todas)
- ❌ NO es público - requiere autenticación

**Query Parameters (TODOS OPCIONALES):**
- `nit` (opcional): Filtrar por NIT específico. Si no se envía, retorna passwords de TODAS tus empresas asociadas.
- `entidad_id` (opcional): Filtrar por ID de entidad
- `empresa_id` (opcional): Filtrar por ID de empresa (debe estar autorizada)

**Comportamiento:**
- Si solo envías API Key (sin filtros): Retorna passwords de TODAS tus empresas asociadas
- Si envías `nit` o `empresa_id`: Retorna passwords solo de esa empresa (debe estar autorizada)

**Ejemplo de Request (solo API Key - retorna todo automáticamente):**
```bash
GET /api/contrasenas-entidades/
Headers:
  Api-Key: <tu_api_key>
```

**Ejemplo de Request (con filtros opcionales):**
```bash
GET /api/contrasenas-entidades/?nit=900869750&entidad_id=1
Headers:
  Api-Key: <tu_api_key>
```

**Ejemplo de Response:**
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "nit_normalizado": "900869750",
      "entidad": {
        "id": 1,
        "nombre": "DIAN",
        "sigla": "DIAN"
      },
      "empresa_servidor": {
        "id": 1,
        "nombre": "Mi Empresa S.A.S.",
        "codigo": "001"
      },
      "usuario": "admin@dian.gov.co",
      "contrasena": "encrypted_password",
      "descripcion": "Usuario principal DIAN",
      "fecha_creacion": "2024-01-01T00:00:00Z",
      "fecha_actualizacion": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**Errores posibles:**
- `403 Forbidden`: Sin API Key o API Key inválida
  ```json
  {
    "error": "Se requiere API Key válida o autenticación de superusuario para consultar passwords de entidades",
    "info": "Si tienes una API Key, envíala en el header: Api-Key: <tu_api_key>"
  }
  ```

- `403 Forbidden`: Intentando acceder a empresa no autorizada
  ```json
  {
    "error": "No tienes permiso para consultar passwords de este NIT"
  }
  ```

**Notas Importantes:**
- Solo necesitas enviar tu API Key - el sistema automáticamente filtra por tus empresas asociadas
- Si no especificas filtros, retorna passwords de TODAS tus empresas
- Las contraseñas están encriptadas en la base de datos
- Solo puedes ver passwords de empresas asociadas a tu API Key

---

## 🔍 Lógica de Filtrado de Eventos (Calendario Tributario)

El sistema filtra eventos basándose en:

1. **Últimos dígitos del NIT:**
   - Busca eventos con `digitos_nit` igual a:
     - `""` (vacío) → Aplica a todos los NITs
     - Último dígito del NIT (ej: NIT `900869750` → `"0"`)
     - Últimos dos dígitos del NIT (ej: NIT `900869750` → `"50"`)

2. **Tipo de Tercero:**
   - Se obtiene del RUT (Persona Natural `PN` o Persona Jurídica `PJ`)
   - Si no hay RUT, busca eventos que apliquen a todos (`tipo_tercero = null`)

3. **Régimen Tributario:**
   - Si se proporciona `tipo_regimen`, filtra por ese régimen
   - También busca eventos que apliquen a todos (`tipo_regimen = null`)

4. **Fechas:**
   - `fecha_desde`: Solo eventos con `fecha_limite >= fecha_desde`
   - `fecha_hasta`: Solo eventos con `fecha_limite <= fecha_hasta`

---

## 📝 Ejemplos de Uso

### Python (requests)
```python
import requests

# Obtener eventos de TODAS tus empresas (solo API Key)
response = requests.get(
    'https://api.eddeso.com/api/calendario-tributario/eventos/',
    headers={'Api-Key': '<tu_api_key>'}
)
print(response.json())

# Obtener eventos de un NIT específico (opcional)
response = requests.get(
    'https://api.eddeso.com/api/calendario-tributario/eventos/',
    params={'nit': '900869750', 'fecha_desde': '2024-01-01'},
    headers={'Api-Key': '<tu_api_key>'}
)
print(response.json())

# Obtener eventos de TODAS tus empresas automáticamente (sin especificar NITs)
response = requests.post(
    'https://api.eddeso.com/api/calendario-tributario/eventos-multiples/',
    json={'fecha_desde': '2024-01-01', 'fecha_hasta': '2024-12-31'},
    headers={'Api-Key': '<tu_api_key>'}
)
print(response.json())

# Obtener eventos de NITs específicos (opcional)
response = requests.post(
    'https://api.eddeso.com/api/calendario-tributario/eventos-multiples/',
    json={
        'nits': ['900869750', '132791157'],
        'fecha_desde': '2024-01-01'
    },
    headers={'Api-Key': '<tu_api_key>'}
)
print(response.json())

# Listar passwords de TODAS tus empresas (solo API Key)
response = requests.get(
    'https://api.eddeso.com/api/contrasenas-entidades/',
    headers={'Api-Key': '<tu_api_key>'}
)
print(response.json())

# Listar passwords de un NIT específico (opcional)
response = requests.get(
    'https://api.eddeso.com/api/contrasenas-entidades/',
    params={'nit': '900869750'},
    headers={'Api-Key': '<tu_api_key>'}
)
print(response.json())
```

### cURL
```bash
# Eventos de TODAS tus empresas (solo API Key)
curl -X GET "https://api.eddeso.com/api/calendario-tributario/eventos/" \
  -H "Api-Key: <tu_api_key>"

# Eventos de un NIT específico (opcional)
curl -X GET "https://api.eddeso.com/api/calendario-tributario/eventos/?nit=900869750&fecha_desde=2024-01-01" \
  -H "Api-Key: <tu_api_key>"

# Eventos de TODAS tus empresas automáticamente (sin especificar NITs)
curl -X POST "https://api.eddeso.com/api/calendario-tributario/eventos-multiples/" \
  -H "Api-Key: <tu_api_key>" \
  -H "Content-Type: application/json" \
  -d '{"fecha_desde": "2024-01-01", "fecha_hasta": "2024-12-31"}'

# Eventos de NITs específicos (opcional)
curl -X POST "https://api.eddeso.com/api/calendario-tributario/eventos-multiples/" \
  -H "Api-Key: <tu_api_key>" \
  -H "Content-Type: application/json" \
  -d '{"nits": ["900869750", "132791157"], "fecha_desde": "2024-01-01"}'

# Passwords de TODAS tus empresas (solo API Key)
curl -X GET "https://api.eddeso.com/api/contrasenas-entidades/" \
  -H "Api-Key: <tu_api_key>"

# Passwords de un NIT específico (opcional)
curl -X GET "https://api.eddeso.com/api/contrasenas-entidades/?nit=900869750" \
  -H "Api-Key: <tu_api_key>"
```

