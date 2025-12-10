#!/bin/bash
# Script para diagnosticar el flujo de búsqueda del CIUU 4290
# Muestra en qué paso del flujo está: Redis, BD, o API

CIUU_CODE="4290"
echo "=========================================="
echo "🔍 DIAGNÓSTICO CIUU $CIUU_CODE"
echo "=========================================="
echo ""

# 1. Verificar en Redis
echo "1️⃣ Verificando en Redis Cache..."
echo "-----------------------------------"
python manage.py shell << EOF
from django.core.cache import cache
cache_key = f"ciiu_info_${CIUU_CODE}"
info = cache.get(cache_key)
if info:
    print("✅ ENCONTRADO en Redis Cache")
    print(f"   Descripción: {info.get('cseDescripcion', 'N/A')}")
    print(f"   Título: {info.get('cseTitulo', 'N/A')}")
    print(f"   Incluye: {len(info.get('incluye', []))} items")
    print(f"   Excluye: {len(info.get('excluye', []))} items")
else:
    print("❌ NO encontrado en Redis Cache")
EOF
echo ""

# 2. Verificar en Base de Datos
echo "2️⃣ Verificando en Base de Datos..."
echo "-----------------------------------"
python manage.py shell << EOF
from apps.sistema_analitico.models import ActividadEconomica
from django.utils import timezone
from datetime import timedelta

try:
    actividad = ActividadEconomica.objects.get(codigo="${CIUU_CODE}")
    print("✅ ENCONTRADO en Base de Datos")
    print(f"   Descripción: {actividad.descripcion}")
    print(f"   Título: {actividad.titulo}")
    print(f"   Incluye: {len(actividad.incluye) if actividad.incluye else 0} items")
    print(f"   Excluye: {len(actividad.excluye) if actividad.excluye else 0} items")
    
    if actividad.fecha_ultima_consulta_api:
        dias_desde_consulta = (timezone.now() - actividad.fecha_ultima_consulta_api).days
        print(f"   Última consulta API: hace {dias_desde_consulta} días")
        if dias_desde_consulta < 7:
            print("   ✅ Info es reciente (< 7 días)")
        else:
            print("   ⚠️ Info es antigua (> 7 días), se actualizará desde API")
    else:
        print("   ⚠️ No tiene fecha de última consulta API")
except ActividadEconomica.DoesNotExist:
    print("❌ NO encontrado en Base de Datos")
EOF
echo ""

# 3. Forzar consulta completa (simular lo que hace el sistema)
echo "3️⃣ Forzando consulta completa (simula flujo real)..."
echo "-----------------------------------"
python manage.py shell << EOF
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from apps.sistema_analitico.services.clasificador_contable_service import obtener_contexto_ciuu_inteligente

print("🔍 Ejecutando obtener_contexto_ciuu_inteligente('${CIUU_CODE}')...")
print("")

resultado = obtener_contexto_ciuu_inteligente("${CIUU_CODE}")

if resultado:
    print("✅ RESULTADO OBTENIDO:")
    print(f"   Código: {resultado.get('codigo')}")
    print(f"   Descripción: {resultado.get('descripcion')}")
    print(f"   Fuente: {resultado.get('fuente')}")
    print(f"   Incluye: {len(resultado.get('incluye_raw', []))} items")
    print(f"   Excluye: {len(resultado.get('excluye_raw', []))} items")
    
    if resultado.get('fuente') == 'base_datos':
        print("")
        print("📊 ANÁLISIS: La info vino desde Base de Datos")
        print("   → No se consultó la API (ya estaba en BD)")
    elif resultado.get('fuente') == 'api_externa':
        print("")
        print("📊 ANÁLISIS: La info vino desde API Externa")
        print("   → Se consultó la API porque no estaba en BD")
        print("   → Ahora está guardada en BD y Redis para próximas consultas")
else:
    print("❌ No se pudo obtener información del CIUU")
EOF
echo ""

# 4. Verificar nuevamente en Redis (por si se guardó)
echo "4️⃣ Verificando nuevamente en Redis (por si se guardó)..."
echo "-----------------------------------"
python manage.py shell << EOF
from django.core.cache import cache
cache_key = f"ciiu_info_${CIUU_CODE}"
info = cache.get(cache_key)
if info:
    print("✅ AHORA SÍ está en Redis Cache (se guardó después de la consulta)")
else:
    print("❌ Aún no está en Redis Cache")
EOF
echo ""

echo "=========================================="
echo "✅ Diagnóstico completado"
echo "=========================================="

