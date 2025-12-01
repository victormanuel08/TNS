# Variables de Entorno a Añadir al .env

Añade estas variables a tu archivo `.env` existente. **IMPORTANTE:** Mantén todos los valores que ya tienes.

## Variables para FUDO SCRAPER

Añade estas secciones al final de tu `.env`:

```env
# ============================================
# FUDO SCRAPER - API FUDO
# ============================================
FUDO_API_URL=https://api.fu.do
FUDO_AUTH_URL=https://auth.fu.do/authenticate
FUDO_CLUSTER_ID=2
FUDO_LOGIN=your-fudo-username
FUDO_PASSWORD=your-fudo-password
FORCE_CACHE=0

# ============================================
# FUDO SCRAPER - FIREBIRD
# ============================================
FIREBIRD_HOST=localhost
FIREBIRD_USER=SYSDBA
FIREBIRD_PASSWORD=masterkey
FIREBIRD_CHARSET=ISO8859_1
# FIREBIRD_DB se configura por empresa en EmpresaServidor.ruta_base

# ============================================
# FUDO SCRAPER - CONFIGURACIÓN FACTURAS
# ============================================
# PREFIX: Prefijo de facturación para FUDO (ej: FE, FC, etc.)
# Este prefijo se usa al crear facturas desde FUDO en Firebird
PREFIX=FE
# REVERSE_PREFIX: Si es True, invierte el prefijo cuando el pago es en efectivo
REVERSE_PREFIX=False
```

## Variables adicionales para Celery (si no las tienes)

```env
CELERY_BROKER_URL=redis://localhost:6380/0
CELERY_RESULT_BACKEND=redis://localhost:6380/0
```

## Nota sobre PREFIX

**PREFIX** es el prefijo de facturación que se usa cuando se crean facturas desde FUDO en Firebird. 
- Ejemplos comunes: `FE` (Factura Electrónica), `FC` (Factura Contado), etc.
- Este valor se usa en el scraper de FUDO para generar los números de factura en Firebird.

