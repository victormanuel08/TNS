"""
Script para verificar consumo considerando zona horaria
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.sistema_analitico.models import ClasificacionContable
from apps.dian_scraper.models import ScrapingSession
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta, date
from apps.sistema_analitico.services.clasificador_contable_service import calcular_costo_tokens
import pytz

print(f"\n📊 ANÁLISIS DE CONSUMO POR ZONA HORARIA")
print("=" * 80)

# Fechas importantes
ahora_utc = timezone.now()
hoy_local = date.today()
hoy_utc = ahora_utc.date()

print(f"\n🕐 ZONA HORARIA:")
print(f"   - UTC ahora: {ahora_utc}")
print(f"   - Fecha local: {hoy_local}")
print(f"   - Fecha UTC: {hoy_utc}")

# Clasificaciones de las últimas 48 horas (para cubrir desfases)
hace_48h = ahora_utc - timedelta(hours=48)
clasif_48h = ClasificacionContable.objects.filter(procesado_at__gte=hace_48h).order_by('procesado_at')

print(f"\n📋 Clasificaciones últimas 48 horas: {clasif_48h.count()}")

# Agrupar por fecha UTC
clasif_por_fecha_utc = {}
for c in clasif_48h:
    if c.procesado_at:
        fecha_utc = c.procesado_at.date()
        if fecha_utc not in clasif_por_fecha_utc:
            clasif_por_fecha_utc[fecha_utc] = []
        clasif_por_fecha_utc[fecha_utc].append(c)

print(f"\n📅 CLASIFICACIONES POR FECHA UTC:")
for fecha_utc in sorted(clasif_por_fecha_utc.keys()):
    clasif_fecha = clasif_por_fecha_utc[fecha_utc]
    costo_fecha = sum(float(c.costo_total_factura) for c in clasif_fecha)
    tokens_output = sum(c.tokens_output for c in clasif_fecha)
    tokens_input = sum(c.tokens_input for c in clasif_fecha)
    
    print(f"\n   {fecha_utc} (UTC):")
    print(f"      - Clasificaciones: {len(clasif_fecha)}")
    print(f"      - Costo: ${costo_fecha:.6f} USD")
    print(f"      - Output tokens: {tokens_output:,}")
    print(f"      - Input tokens: {tokens_input:,}")
    
    # Sesiones involucradas
    sesiones = set(c.session_dian_id for c in clasif_fecha if c.session_dian_id)
    if sesiones:
        print(f"      - Sesiones: {', '.join(f'#{s}' for s in sesiones)}")

# Específicamente para 2025-12-09 UTC
fecha_09_dic_utc = date(2025, 12, 9)
if fecha_09_dic_utc in clasif_por_fecha_utc:
    clasif_09_dic = clasif_por_fecha_utc[fecha_09_dic_utc]
    costo_09_dic = sum(float(c.costo_total_factura) for c in clasif_09_dic)
    
    print(f"\n💰 RESUMEN PARA 2025-12-09 (UTC):")
    print(f"   - Total clasificaciones: {len(clasif_09_dic)}")
    print(f"   - Costo total: ${costo_09_dic:.6f} USD")
    
    # Comparar con DeepSeek
    costo_deepseek_chat = 0.260092  # Del CSV
    print(f"\n🔍 COMPARACIÓN CON DEEPSEEK:")
    print(f"   - Sistema (2025-12-09 UTC): ${costo_09_dic:.6f} USD")
    print(f"   - DeepSeek deepseek-chat: ${costo_deepseek_chat:.6f} USD")
    print(f"   - Diferencia: ${costo_deepseek_chat - costo_09_dic:.6f} USD")
    
    if abs(costo_deepseek_chat - costo_09_dic) > 0.01:
        print(f"   ⚠️ Hay una diferencia significativa")
    else:
        print(f"   ✅ Los costos coinciden")

print("\n" + "=" * 80)

