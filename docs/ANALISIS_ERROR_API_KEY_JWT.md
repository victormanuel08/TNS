# 🔍 ANÁLISIS: Error "API Key no encontrada" con JWT

## ❌ PROBLEMA

**Error en logs:**
```
❌ [API_KEY] API Key no encontrada en BD: eyJhbGciOiJIUzI1NiIs...
```

**Causa:** El frontend está enviando un **JWT (JSON Web Token)** como si fuera una **API Key**.

---

## 🔑 DIFERENCIA ENTRE JWT Y API KEY

### **JWT (JSON Web Token)**
- **Formato:** `eyJhbGciOiJIUzI1NiIs...` (base64)
- **Se genera:** Al hacer login con usuario/password
- **Se usa:** Para autenticación de usuarios en el frontend
- **Header:** `Authorization: Bearer eyJhbGciOiJIUzI1NiIs...`

### **API Key**
- **Formato:** `sk_XXXXXXXX...` (empieza con `sk_`)
- **Se genera:** Manualmente desde el panel de admin o endpoint
- **Se usa:** Para acceso programático sin usuario
- **Header:** `Api-Key: sk_XXXXXXXX...` o `Authorization: Api-Key sk_XXXXXXXX...`

---

## 🐛 CÓDIGO PROBLEMÁTICO

**Archivo:** `manu/apps/sistema_analitico/views.py` línea 330-332

```python
elif auth_header.startswith('Bearer '):
    # ❌ PROBLEMA: Está tomando el JWT como API Key
    api_key = auth_header.replace('Bearer ', '')
```

**Problema:** Si el header es `Authorization: Bearer eyJhbGciOiJIUzI1NiIs...`, el código intenta buscar esa cadena como API Key en la BD, pero las API Keys tienen formato `sk_...`, no `eyJ...`.

---

## ✅ SOLUCIÓN

### **1. Corregir el código para ignorar JWT**

El código debe verificar que la API Key tenga el formato correcto (`sk_...`) antes de intentar buscarla en la BD.

### **2. Generar una API Key correctamente**

**Opción A: Desde el panel de admin (frontend)**
1. Login con usuario/password (ej: `manu` / `manu`)
2. Ir a `/admin/dashboard`
3. Sección "API Keys"
4. Click en "Generar API Key"
5. Completar:
   - NIT: (ej: `1005038638`)
   - Nombre Cliente: (ej: `Mi Empresa`)
   - Días de validez: (ej: `365`)
6. **Copiar la API Key generada** (solo se muestra una vez)

**Opción B: Desde el endpoint (con JWT)**
```bash
POST /api/api-keys/generar_api_key/
Authorization: Bearer <tu_jwt_token>
Content-Type: application/json

{
  "nit": "1005038638",
  "nombre_cliente": "Mi Empresa",
  "dias_validez": 365
}
```

**Respuesta:**
```json
{
  "nit": "1005038638",
  "nombre_cliente": "Mi Empresa",
  "api_key": "sk_XXXXXXXX...",  // ← Esta es la API Key
  "empresas_asociadas": 1,
  "fecha_caducidad": "2026-12-09T..."
}
```

---

## 🔧 CORRECCIÓN DEL CÓDIGO

**Archivos corregidos:**
1. `manu/apps/sistema_analitico/views.py` (línea 330-332)
2. `manu/apps/sistema_analitico/views_firebird_admin.py` (línea 32)

**Cambio aplicado:**
- Verificar que la API Key tenga formato `sk_...` antes de buscarla
- Ignorar tokens `Bearer` que sean JWT (empiezan con `eyJ`)

**Código corregido:**
```python
elif auth_header.startswith('Bearer '):
    # Verificar que sea una API Key (formato sk_...) y no un JWT (formato eyJ...)
    bearer_token = auth_header.replace('Bearer ', '').strip()
    # Las API Keys empiezan con 'sk_', los JWT empiezan con 'eyJ'
    if bearer_token.startswith('sk_'):
        api_key = bearer_token
    # Si es JWT (eyJ...), ignorarlo - no es una API Key
```

---

## 📋 RESUMEN

1. ✅ **JWT** = Token de login (usuario/password) → Para frontend
2. ✅ **API Key** = Clave programática (`sk_...`) → Para APIs
3. ❌ **Problema actual:** El código intenta usar JWT como API Key
4. ✅ **Solución:** Generar una API Key desde el panel de admin o endpoint

---

**Última actualización**: Diciembre 2025

