"""
Script rápido para analizar consumo de clasificaciones procesadas HOY
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.sistema_analitico.models import ClasificacionContable, AIAnalyticsAPIKey
from apps.dian_scraper.models import ScrapingSession
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import date, timedelta
from apps.sistema_analitico.services.clasificador_contable_service import calcular_costo_tokens

hoy = date.today()
print(f"\n📊 ANÁLISIS DE CONSUMO HOY ({hoy})")
print("=" * 80)

# Clasificaciones procesadas HOY
clasif_hoy = ClasificacionContable.objects.filter(procesado_at__date=hoy)
total_hoy = clasif_hoy.count()

print(f"\n📋 Clasificaciones procesadas HOY: {total_hoy}")

if total_hoy > 0:
    # Costo acumulado
    costo_hoy = clasif_hoy.aggregate(total=Sum('costo_total_factura'))['total'] or 0
    print(f"💰 Costo acumulado HOY: ${float(costo_hoy):.6f} USD")
    print(f"💰 Costo acumulado HOY: ${float(costo_hoy) * 4000:,.2f} COP")
    
    # Tokens totales
    tokens_input = sum(c.tokens_input for c in clasif_hoy)
    tokens_output = sum(c.tokens_output for c in clasif_hoy)
    print(f"\n📊 Tokens totales HOY:")
    print(f"   - Input: {tokens_input:,}")
    print(f"   - Output: {tokens_output:,}")
    
    # Cache hit/miss
    total_cache_hit = 0
    total_cache_miss = 0
    for c in clasif_hoy:
        if c.respuesta_json_completa:
            usage = c.respuesta_json_completa.get('usage', {})
            cache_hit = usage.get('prompt_cache_hit_tokens', 0)
            cache_miss = usage.get('prompt_cache_miss_tokens', 0)
            if cache_hit > 0 or cache_miss > 0:
                total_cache_hit += cache_hit
                total_cache_miss += cache_miss
    
    if total_cache_hit > 0 or total_cache_miss > 0:
        print(f"   - Cache HIT: {total_cache_hit:,}")
        print(f"   - Cache MISS: {total_cache_miss:,}")
    
    # Recalcular costo
    if tokens_input > 0 or tokens_output > 0:
        costo_recalc = calcular_costo_tokens(
            input_tokens=tokens_input,
            output_tokens=tokens_output,
            cache_hit_tokens=total_cache_hit if total_cache_hit > 0 else None,
            cache_miss_tokens=total_cache_miss if total_cache_miss > 0 else None
        )
        print(f"\n💰 Costo recalculado HOY: ${costo_recalc['costo_usd']:.6f} USD")
    
    # Sesiones procesadas HOY
    sesiones_hoy = ScrapingSession.objects.filter(
        clasificaciones_contables__procesado_at__date=hoy
    ).distinct()
    
    print(f"\n📦 Sesiones procesadas HOY: {sesiones_hoy.count()}")
    for sesion in sesiones_hoy:
        clasif_sesion = clasif_hoy.filter(session_dian_id=sesion.id)
        costo_sesion = clasif_sesion.aggregate(total=Sum('costo_total_factura'))['total'] or 0
        print(f"   - Sesión #{sesion.id}: {clasif_sesion.count()} facturas, ${float(costo_sesion):.6f} USD")
    
    # API Keys usadas HOY
    api_keys = AIAnalyticsAPIKey.objects.filter(activa=True)
    print(f"\n🔑 API Keys activas: {api_keys.count()}")
    for key in api_keys:
        print(f"   - {key.nombre}: {key.total_peticiones} peticiones, ${float(key.costo_total_usd):.6f} USD total")

print("\n" + "=" * 80)

