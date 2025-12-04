# Resumen: Endpoints Simplificados con API Key

## 🎯 Funcionamiento Automático

**Con solo enviar tu API Key, el sistema automáticamente:**
- Identifica todas tus empresas asociadas
- Retorna datos solo de esas empresas
- No necesitas especificar NITs ni empresas manualmente

---

## 📅 Calendario Tributario - Eventos

### GET `/api/calendario-tributario/eventos/`

**Solo API Key (retorna todo automáticamente):**
```bash
GET /api/calendario-tributario/eventos/
Headers:
  Api-Key: <tu_api_key>
```

**Respuesta:** Eventos de TODAS tus empresas asociadas

**Con filtros opcionales:**
```bash
GET /api/calendario-tributario/eventos/?nit=900869750&fecha_desde=2024-01-01
Headers:
  Api-Key: <tu_api_key>
```

**Respuesta:** Eventos solo de esa empresa (si está autorizada)

---

### POST `/api/calendario-tributario/eventos-multiples/`

**Solo API Key (retorna todo automáticamente):**
```bash
POST /api/calendario-tributario/eventos-multiples/
Headers:
  Api-Key: <tu_api_key>
Body:
{}  # Vacío o sin "nits"
```

**Respuesta:** Eventos de TODAS tus empresas asociadas

**Con NITs específicos (opcional):**
```bash
POST /api/calendario-tributario/eventos-multiples/
Headers:
  Api-Key: <tu_api_key>
Body:
{
  "nits": ["900869750", "132791157"],
  "fecha_desde": "2024-01-01"
}
```

**Respuesta:** Eventos solo de esos NITs (si están autorizados)

---

## 🔐 Passwords de Entidades

### GET `/api/contrasenas-entidades/`

**Solo API Key (retorna todo automáticamente):**
```bash
GET /api/contrasenas-entidades/
Headers:
  Api-Key: <tu_api_key>
```

**Respuesta:** Passwords de TODAS tus empresas asociadas

**Con filtros opcionales:**
```bash
GET /api/contrasenas-entidades/?nit=900869750&entidad_id=1
Headers:
  Api-Key: <tu_api_key>
```

**Respuesta:** Passwords solo de esa empresa/entidad (si está autorizada)

---

## ✅ Ventajas

1. **Simple:** Solo envías API Key, el sistema hace el resto
2. **Automático:** Identifica tus empresas sin configuración
3. **Seguro:** Solo ves datos de tus empresas autorizadas
4. **Flexible:** Puedes agregar filtros opcionales si necesitas

---

## 📝 Ejemplos Completos

### Python
```python
import requests

headers = {'Api-Key': 'tu_api_key_aqui'}

# Eventos de todas tus empresas
response = requests.get(
    'https://api.eddeso.com/api/calendario-tributario/eventos/',
    headers=headers
)
print(response.json())

# Passwords de todas tus empresas
response = requests.get(
    'https://api.eddeso.com/api/contrasenas-entidades/',
    headers=headers
)
print(response.json())
```

### JavaScript/Fetch
```javascript
const apiKey = 'tu_api_key_aqui';

// Eventos de todas tus empresas
fetch('https://api.eddeso.com/api/calendario-tributario/eventos/', {
  headers: { 'Api-Key': apiKey }
})
  .then(res => res.json())
  .then(data => console.log(data));

// Passwords de todas tus empresas
fetch('https://api.eddeso.com/api/contrasenas-entidades/', {
  headers: { 'Api-Key': apiKey }
})
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## 🔒 Seguridad

- ✅ Solo ves datos de empresas asociadas a tu API Key
- ✅ No puedes acceder a datos de otras empresas
- ✅ Los filtros se validan automáticamente
- ✅ Si intentas acceder a empresa no autorizada, recibes error 403

