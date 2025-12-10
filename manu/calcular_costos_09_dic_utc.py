"""
Calcular costos exactos para 2025-12-09 UTC
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.sistema_analitico.models import ClasificacionContable
from apps.sistema_analitico.services.clasificador_contable_service import calcular_costo_tokens
from datetime import date

fecha_utc = date(2025, 12, 9)
clasif = ClasificacionContable.objects.filter(procesado_at__date=fecha_utc)

print(f"\n📊 ANÁLISIS COMPLETO 2025-12-09 (UTC)")
print("=" * 80)
print(f"\n📋 Total clasificaciones: {clasif.count()}")

# Tokens totales
total_output = 0
total_input = 0
total_cache_hit = 0
total_cache_miss = 0

for c in clasif:
    total_output += c.tokens_output
    total_input += c.tokens_input
    
    if c.respuesta_json_completa:
        usage = c.respuesta_json_completa.get('usage', {})
        cache_hit = usage.get('prompt_cache_hit_tokens', 0) or 0
        cache_miss = usage.get('prompt_cache_miss_tokens', 0) or 0
        
        if cache_hit > 0 or cache_miss > 0:
            total_cache_hit += cache_hit
            total_cache_miss += cache_miss
        else:
            # Estimación
            total_cache_hit += int(c.tokens_input * 0.7)
            total_cache_miss += int(c.tokens_input * 0.3)

print(f"\n📊 TOKENS TOTALES:")
print(f"   - Output: {total_output:,}")
print(f"   - Input: {total_input:,}")
print(f"   - Cache HIT: {total_cache_hit:,}")
print(f"   - Cache MISS: {total_cache_miss:,}")

# Calcular costo
costo_info = calcular_costo_tokens(
    input_tokens=total_input,
    output_tokens=total_output,
    cache_hit_tokens=total_cache_hit if total_cache_hit > 0 else None,
    cache_miss_tokens=total_cache_miss if total_cache_miss > 0 else None
)

print(f"\n💰 COSTO CALCULADO:")
print(f"   - Costo Input: ${costo_info['costo_input_usd']:.6f} USD")
print(f"   - Costo Output: ${costo_info['costo_output_usd']:.6f} USD")
print(f"   - Costo Total: ${costo_info['costo_usd']:.6f} USD")

# Costo acumulado en BD
costo_bd = sum(float(c.costo_total_factura) for c in clasif)
print(f"\n💰 COSTO EN BD: ${costo_bd:.6f} USD")

# Comparar con DeepSeek
costo_deepseek_chat = 0.260092
print(f"\n🔍 COMPARACIÓN CON DEEPSEEK:")
print(f"   - Sistema (2025-12-09 UTC): ${costo_info['costo_usd']:.6f} USD")
print(f"   - DeepSeek deepseek-chat: ${costo_deepseek_chat:.6f} USD")
print(f"   - Diferencia: ${costo_deepseek_chat - costo_info['costo_usd']:.6f} USD")
print(f"   - Porcentaje: {((costo_deepseek_chat - costo_info['costo_usd']) / costo_info['costo_usd'] * 100):.1f}% más en DeepSeek")

# Tokens de DeepSeek para comparar
tokens_deepseek_output = 253439
tokens_deepseek_cache_hit = 687168
tokens_deepseek_cache_miss = 480023

print(f"\n📊 COMPARACIÓN DE TOKENS:")
print(f"   - Output tokens:")
print(f"     * Sistema: {total_output:,}")
print(f"     * DeepSeek: {tokens_deepseek_output:,}")
print(f"     * Diferencia: {tokens_deepseek_output - total_output:,}")
print(f"   - Cache HIT tokens:")
print(f"     * Sistema: {total_cache_hit:,}")
print(f"     * DeepSeek: {tokens_deepseek_cache_hit:,}")
print(f"     * Diferencia: {tokens_deepseek_cache_hit - total_cache_hit:,}")
print(f"   - Cache MISS tokens:")
print(f"     * Sistema: {total_cache_miss:,}")
print(f"     * DeepSeek: {tokens_deepseek_cache_miss:,}")
print(f"     * Diferencia: {tokens_deepseek_cache_miss - total_cache_miss:,}")

print("\n" + "=" * 80)

