# Configurar API Key para Scraping Total Sin Restricciones

## 📋 Descripción

Una API Key con `permite_scraping_total = True` permite hacer scraping de DIAN **sin validar empresas ni autorizaciones**. Esto es útil para API Keys administrativas que necesitan acceso total.

## 🔧 Configuración

### Opción 1: Usando el comando Django (Recomendado)

```bash
# Por ID
python manage.py configurar_api_key_scraping_total <api_key_id>

# Por API Key string
python manage.py configurar_api_key_scraping_total --api-key "sk_xxxxx"

# Por NIT
python manage.py configurar_api_key_scraping_total --nit "900123456"

# Desactivar scraping total
python manage.py configurar_api_key_scraping_total <api_key_id> --desactivar
```

### Opción 2: Directamente en la base de datos

```sql
-- Activar scraping total para una API Key específica
UPDATE api_keys_clientes 
SET permite_scraping_total = TRUE 
WHERE id = <api_key_id>;

-- O por NIT
UPDATE api_keys_clientes 
SET permite_scraping_total = TRUE 
WHERE nit = '900123456';

-- O por API Key string
UPDATE api_keys_clientes 
SET permite_scraping_total = TRUE 
WHERE api_key = 'sk_xxxxx';
```

### Opción 3: Desde el shell de Django

```python
from apps.sistema_analitico.models import APIKeyCliente

# Buscar la API Key
api_key = APIKeyCliente.objects.get(id=1)  # O por nit, api_key, etc.

# Activar scraping total
api_key.permite_scraping_total = True
api_key.save()

# Verificar
print(f"Scraping total: {api_key.permite_scraping_total}")
```

## ⚠️ Seguridad

**IMPORTANTE**: 
- Solo usar para API Keys administrativas o de confianza
- No exponer estas API Keys públicamente
- Revisar regularmente qué API Keys tienen este flag activo
- Considerar usar fechas de caducidad más cortas para estas API Keys

## 🔍 Verificar API Keys con Scraping Total

```sql
-- Ver todas las API Keys con scraping total activo
SELECT 
    id,
    nit,
    nombre_cliente,
    api_key,
    permite_scraping_total,
    activa,
    fecha_caducidad
FROM api_keys_clientes
WHERE permite_scraping_total = TRUE
AND activa = TRUE;
```

## 📝 Tabla: `api_keys_clientes`

Campo agregado:
- **`permite_scraping_total`**: `BooleanField` (default: `False`)
  - Si es `True`: No valida empresas, permite scraping sin restricciones
  - Si es `False`: Valida empresas asociadas (comportamiento normal)

## 🎯 Comportamiento

### Con `permite_scraping_total = True`:
- ✅ No valida empresas asociadas
- ✅ Permite scraping de cualquier NIT
- ✅ No requiere que existan empresas en `EmpresaServidor`
- ✅ Acceso total a todas las funciones de scraping

### Con `permite_scraping_total = False` (default):
- ✅ Valida empresas asociadas
- ✅ Solo permite scraping de NITs con empresas asociadas
- ✅ Comportamiento normal y seguro

## 🔄 Migración

La migración `0041_agregar_permite_scraping_total.py` agrega el campo a la tabla.

Para aplicarla:
```bash
python manage.py migrate sistema_analitico
```

