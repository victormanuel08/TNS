# 🔍 Análisis: Problemas con RUT PDF y API de Cámara de Comercio

## 📋 Problemas Reportados

### 1. **PDF no existe en la URL**
- **URL reportada**: `https://api.eddeso.com/media/ruts/RUT_UT_PROTECCION_RIO_PERALONSO_ZULIA_2025_1.pdf`
- **Error**: El archivo no existe en esa ruta

### 2. **No consulta API de Cámara de Comercio**
- **Problema**: El sistema no está buscando en la API de CCC o del gobierno cuando no encuentra el RUT

---

## 🔍 Análisis del Problema 1: PDF no existe

### Configuración Actual

**Settings (`manu/config/settings.py`):**
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

**Modelo RUT (`manu/apps/sistema_analitico/models.py`):**
```python
archivo_pdf = models.FileField(
    upload_to='ruts/',
    null=True,
    blank=True,
    help_text='Archivo PDF del RUT original'
)
```

**URLs (`manu/config/urls.py`):**
```python
urlpatterns = [
    # ...
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### Posibles Causas

1. **El archivo no se guardó correctamente**
   - El PDF se subió pero hubo un error al guardarlo
   - El archivo se guardó pero con otro nombre

2. **La URL no está correctamente configurada**
   - El servidor web (nginx/apache) no está sirviendo `/media/`
   - La URL absoluta se construye incorrectamente

3. **El archivo se guardó en otra ubicación**
   - El `MEDIA_ROOT` está configurado diferente en producción
   - El archivo está en el servidor pero la URL es incorrecta

### Comandos para Diagnosticar

```bash
# 1. Verificar si el archivo existe en el servidor
ls -la /ruta/al/proyecto/media/ruts/ | grep "RUT_UT_PROTECCION"

# 2. Verificar configuración de MEDIA_ROOT
python manage.py shell -c "from django.conf import settings; print('MEDIA_ROOT:', settings.MEDIA_ROOT); print('MEDIA_URL:', settings.MEDIA_URL)"

# 3. Verificar el RUT en la BD
python manage.py shell -c "from apps.sistema_analitico.models import RUT; rut = RUT.objects.filter(razon_social__icontains='RIO_PERALONSO').first(); print('RUT encontrado:', rut); print('archivo_pdf:', rut.archivo_pdf if rut else None); print('URL:', rut.archivo_pdf.url if rut and rut.archivo_pdf else None)"

# 4. Verificar permisos del directorio media
ls -la /ruta/al/proyecto/media/
ls -la /ruta/al/proyecto/media/ruts/
```

---

## 🔍 Análisis del Problema 2: No consulta API de Cámara de Comercio

### Flujo Actual de Búsqueda

El código en `buscar_rut_por_nit` (líneas 585-710) tiene este flujo:

```python
1. Buscar en RUT (tabla RUT) por nit_normalizado
   ↓ (si encuentra, RETORNA aquí)
2. Buscar en Proveedor (tabla Proveedor - cache)
   ↓ (si encuentra, RETORNA aquí)
3. Consultar Cámara de Comercio (API)
   ↓ (si encuentra, guarda en Proveedor y RETORNA)
4. Retornar None
```

### Posibles Causas

1. **El RUT existe en la BD pero sin CIUU**
   - El RUT se encuentra en el paso 1
   - Pero `rut.actividad_principal_ciiu` está NULL
   - Retorna antes de llegar a la consulta de API

2. **El Proveedor existe en cache pero sin CIUU**
   - El Proveedor se encuentra en el paso 2
   - Pero `proveedor.actividad_principal_ciiu` está NULL
   - Retorna antes de llegar a la consulta de API

3. **La consulta a la API falla silenciosamente**
   - La API de Cámara de Comercio no responde
   - Hay un error pero se captura y retorna None
   - No se loguea el error correctamente

4. **El NIT no se encuentra en la API**
   - La API de datos.gov.co no tiene ese NIT
   - Retorna None pero no se intenta otra fuente

### Código Actual de Consulta

**`camara_comercio_service.py` (línea 15):**
```python
CAMARA_COMERCIO_API_URL = 'https://www.datos.gov.co/resource/c82u-588k.json'
```

**Problema potencial**: Esta API solo tiene empresas de **Bogotá**. Si la empresa es de otra ciudad, no la encontrará.

### Solución Propuesta

1. **Mejorar el logging** para ver qué está pasando
2. **Consultar múltiples APIs**:
   - API de datos.gov.co (Bogotá)
   - API de enlinea.ccc.org.co (si está disponible)
   - Otras APIs gubernamentales

3. **Forzar consulta de API** si el RUT existe pero no tiene CIUU

---

## 🛠️ Comandos para Diagnosticar

```bash
# 1. Verificar si el RUT existe en la BD
python manage.py shell -c "
from apps.sistema_analitico.models import RUT
nit = 'NIT_AQUI'  # Reemplazar con el NIT del problema
rut = RUT.objects.filter(nit_normalizado=nit).first()
if rut:
    print(f'RUT encontrado: {rut.razon_social}')
    print(f'CIUU Principal: {rut.actividad_principal_ciiu}')
    print(f'Archivo PDF: {rut.archivo_pdf}')
else:
    print('RUT no encontrado en BD')
"

# 2. Verificar si el Proveedor existe en cache
python manage.py shell -c "
from apps.sistema_analitico.models import Proveedor
nit = 'NIT_AQUI'  # Reemplazar con el NIT del problema
prov = Proveedor.objects.filter(nit_normalizado=nit).first()
if prov:
    print(f'Proveedor encontrado: {prov.razon_social}')
    print(f'CIUU Principal: {prov.actividad_principal_ciiu}')
    print(f'Fuente: {prov.fuente}')
else:
    print('Proveedor no encontrado en cache')
"

# 3. Probar consulta directa a API de Cámara de Comercio
python manage.py shell -c "
from apps.sistema_analitico.services.camara_comercio_service import consultar_camara_comercio_por_nit
nit = 'NIT_AQUI'  # Reemplazar con el NIT del problema
resultado = consultar_camara_comercio_por_nit(nit)
print('Resultado:', resultado)
"

# 4. Verificar logs de la consulta
# Buscar en los logs del servidor mensajes como:
# - 'Consultando Cámara de Comercio para NIT:'
# - 'No se encontró información en Cámara de Comercio para NIT:'
# - 'Error consultando Cámara de Comercio'
```

---

## ✅ Soluciones Propuestas

### Para el Problema 1 (PDF no existe)

1. **Verificar que el archivo se guardó**:
   - Revisar logs de la subida del PDF
   - Verificar en el servidor si el archivo existe
   - Verificar permisos del directorio `media/ruts/`

2. **Corregir la URL**:
   - Verificar que nginx/apache está sirviendo `/media/`
   - Verificar que `MEDIA_URL` y `MEDIA_ROOT` están correctos
   - Verificar que `request.build_absolute_uri()` está construyendo la URL correcta

### Para el Problema 2 (No consulta API)

1. **Mejorar el logging**:
   - Agregar más logs en `buscar_rut_por_nit`
   - Loggear cuando se encuentra RUT pero sin CIUU
   - Loggear cuando se intenta consultar la API

2. **Forzar consulta si RUT existe pero sin CIUU**:
   - Si el RUT existe pero `actividad_principal_ciiu` es NULL, consultar API
   - Guardar el CIUU encontrado en el RUT

3. **Consultar múltiples APIs**:
   - API de datos.gov.co (Bogotá)
   - API de enlinea.ccc.org.co (nacional)
   - Otras fuentes gubernamentales

