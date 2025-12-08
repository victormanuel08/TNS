#!/usr/bin/env python
"""
Script para verificar que los precios de DeepSeek se carguen correctamente desde settings.
Ejecutar: python verificar_precios.py
"""

import sys
import os

# Configurar Django
manu_dir = os.path.join(os.path.dirname(__file__), 'manu')
if os.path.exists(manu_dir):
    sys.path.insert(0, manu_dir)

try:
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    from django.conf import settings
    
    print("=" * 60)
    print("🔍 VERIFICACIÓN DE PRECIOS DEEPSEEK")
    print("=" * 60)
    print()
    
    # Verificar precios
    precio_output = getattr(settings, 'DEEPSEEK_PRICE_OUTPUT_TOKEN', None)
    precio_cache_hit = getattr(settings, 'DEEPSEEK_PRICE_INPUT_CACHE_HIT', None)
    precio_cache_miss = getattr(settings, 'DEEPSEEK_PRICE_INPUT_CACHE_MISS', None)
    tasa_cambio = getattr(settings, 'TASA_CAMBIO_COP_USD', None)
    
    print("📊 PRECIOS CONFIGURADOS:")
    print(f"  ✅ Output Token:        ${precio_output:.10f} USD/token" if precio_output else "  ❌ Output Token:        NO CONFIGURADO")
    print(f"  ✅ Input Cache HIT:     ${precio_cache_hit:.10f} USD/token" if precio_cache_hit else "  ❌ Input Cache HIT:     NO CONFIGURADO")
    print(f"  ✅ Input Cache MISS:    ${precio_cache_miss:.10f} USD/token" if precio_cache_miss else "  ❌ Input Cache MISS:    NO CONFIGURADO")
    print(f"  ✅ Tasa Cambio COP/USD: ${tasa_cambio:,.0f} COP" if tasa_cambio else "  ❌ Tasa Cambio:          NO CONFIGURADO")
    
    print()
    print("=" * 60)
    print("💰 PRECIOS POR MILLÓN DE TOKENS:")
    if precio_output:
        print(f"  Output:        ${precio_output * 1000000:.2f} USD por 1M tokens")
    if precio_cache_hit:
        print(f"  Input HIT:     ${precio_cache_hit * 1000000:.3f} USD por 1M tokens")
    if precio_cache_miss:
        print(f"  Input MISS:    ${precio_cache_miss * 1000000:.2f} USD por 1M tokens")
    
    print()
    print("=" * 60)
    print("✅ VALORES ESPERADOS (desde CSV):")
    print("  Output:        $0.42 USD por 1M tokens")
    print("  Input HIT:     $0.028 USD por 1M tokens")
    print("  Input MISS:    $0.56 USD por 1M tokens")
    
    print()
    print("=" * 60)
    
    # Verificar si coinciden
    if precio_output and abs(precio_output - 0.00000042) < 0.000000001:
        print("✅ Output Token: CORRECTO")
    elif precio_output:
        print(f"⚠️  Output Token: DIFERENTE (configurado: ${precio_output * 1000000:.2f}, esperado: $0.42)")
    
    if precio_cache_hit and abs(precio_cache_hit - 0.000000028) < 0.000000001:
        print("✅ Input Cache HIT: CORRECTO")
    elif precio_cache_hit:
        print(f"⚠️  Input Cache HIT: DIFERENTE (configurado: ${precio_cache_hit * 1000000:.3f}, esperado: $0.028)")
    
    if precio_cache_miss and abs(precio_cache_miss - 0.00000056) < 0.000000001:
        print("✅ Input Cache MISS: CORRECTO")
    elif precio_cache_miss:
        print(f"⚠️  Input Cache MISS: DIFERENTE (configurado: ${precio_cache_miss * 1000000:.2f}, esperado: $0.56)")
    
    print()
    print("=" * 60)
    print("✅ Verificación completada!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

