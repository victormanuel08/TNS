#!/usr/bin/env python
"""
Script para probar el cálculo de costos REAL con una clasificación de factura.
Hace una petición real a DeepSeek y muestra cómo se calculan los costos.
Ejecutar: python probar_calculo_costos_real.py
"""

import sys
import os
import json

# Configurar Django
manu_dir = os.path.join(os.path.dirname(__file__), 'manu')
if os.path.exists(manu_dir):
    sys.path.insert(0, manu_dir)

try:
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    from django.conf import settings
    from apps.sistema_analitico.services.clasificador_contable_service import calcular_costo_tokens
    import requests
    
    print("=" * 60)
    print("🧪 PRUEBA DE CÁLCULO DE COSTOS REAL")
    print("=" * 60)
    print()
    
    # Obtener API key
    api_key = getattr(settings, 'DEEPSEEK_API_KEY', '')
    api_url = getattr(settings, 'DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
    
    if not api_key:
        print("❌ ERROR: DEEPSEEK_API_KEY no configurada")
        exit(1)
    
    print("📤 Enviando petición REAL a DeepSeek...")
    print(f"📍 URL: {api_url}")
    print()
    
    # Payload de prueba (similar a una clasificación real pero más simple)
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": "Clasifica este artículo contablemente: 'Papel para impresora, 500 hojas'. Responde solo con JSON: {\"clasificacion\": \"GASTO\" o \"COSTO\" o \"ACTIVO\"}"
            }
        ],
        "max_tokens": 100,
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        usage = data.get('usage', {})
        
        print("✅ Respuesta recibida de DeepSeek!")
        print()
        print("=" * 60)
        print("📊 DATOS DE USAGE (de la respuesta real):")
        print("=" * 60)
        
        input_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0)
        cache_hit_tokens = usage.get('prompt_cache_hit_tokens', None)
        cache_miss_tokens = usage.get('prompt_cache_miss_tokens', None)
        
        print(f"  - prompt_tokens (total input):     {input_tokens}")
        print(f"  - completion_tokens (output):     {output_tokens}")
        print(f"  - prompt_cache_hit_tokens:        {cache_hit_tokens if cache_hit_tokens is not None else 'No disponible'}")
        print(f"  - prompt_cache_miss_tokens:        {cache_miss_tokens if cache_miss_tokens is not None else 'No disponible'}")
        
        print()
        print("=" * 60)
        print("💰 CÁLCULO DE COSTOS:")
        print("=" * 60)
        
        # Calcular costo usando la función actualizada
        costo_info = calcular_costo_tokens(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_hit_tokens=cache_hit_tokens,
            cache_miss_tokens=cache_miss_tokens
        )
        
        print(f"  💵 Costo Total USD:     ${costo_info['costo_usd']:.8f}")
        print(f"  💵 Costo Total COP:     ${costo_info['costo_cop']:,.2f}")
        print()
        print(f"  📥 Tokens Input:        {costo_info['tokens_input']}")
        print(f"  📤 Tokens Output:       {costo_info['tokens_output']}")
        print(f"  ✅ Cache HIT tokens:    {costo_info['tokens_cache_hit']}")
        print(f"  ❌ Cache MISS tokens:   {costo_info['tokens_cache_miss']}")
        print()
        print(f"  💰 Costo Input USD:     ${costo_info['costo_input_usd']:.8f}")
        print(f"  💰 Costo Output USD:    ${costo_info['costo_output_usd']:.8f}")
        print()
        print("=" * 60)
        print("📋 DETALLE DE PRECIOS USADOS:")
        print("=" * 60)
        detalle = costo_info.get('detalle', {})
        print(f"  - Precio Cache HIT:     ${detalle.get('precio_cache_hit', 0):.10f} USD/token")
        print(f"  - Precio Cache MISS:     ${detalle.get('precio_cache_miss', 0):.10f} USD/token")
        print(f"  - Precio Output:         ${detalle.get('precio_output', 0):.10f} USD/token")
        
        print()
        print("=" * 60)
        print("🧮 DESGLOSE DEL CÁLCULO:")
        print("=" * 60)
        
        if cache_hit_tokens is not None and cache_miss_tokens is not None:
            print(f"  Costo Input = (Cache HIT × Precio HIT) + (Cache MISS × Precio MISS)")
            print(f"             = ({costo_info['tokens_cache_hit']} × ${detalle.get('precio_cache_hit', 0):.10f}) + ({costo_info['tokens_cache_miss']} × ${detalle.get('precio_cache_miss', 0):.10f})")
            print(f"             = ${(costo_info['tokens_cache_hit'] * detalle.get('precio_cache_hit', 0)):.10f} + ${(costo_info['tokens_cache_miss'] * detalle.get('precio_cache_miss', 0)):.10f}")
            print(f"             = ${costo_info['costo_input_usd']:.10f}")
        else:
            print(f"  ⚠️  Cache no disponible, usando estimación (70% hit, 30% miss)")
            print(f"  Costo Input estimado = ${costo_info['costo_input_usd']:.10f}")
        
        print(f"  Costo Output = Output tokens × Precio Output")
        print(f"               = {costo_info['tokens_output']} × ${detalle.get('precio_output', 0):.10f}")
        print(f"               = ${costo_info['costo_output_usd']:.10f}")
        print()
        print(f"  Costo Total = Costo Input + Costo Output")
        print(f"              = ${costo_info['costo_input_usd']:.10f} + ${costo_info['costo_output_usd']:.10f}")
        print(f"              = ${costo_info['costo_usd']:.10f} USD")
        print(f"              = ${costo_info['costo_cop']:,.2f} COP")
        
        print()
        print("=" * 60)
        print("✅ Prueba completada exitosamente!")
        print("=" * 60)
        print()
        print("💡 NOTA: Este es un cálculo REAL usando:")
        print("   - Valores de cache reales de la API (si disponibles)")
        print("   - Precios configurados desde settings.py")
        print("   - Tasa de cambio configurada")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error HTTP: {e}")
        if e.response:
            print(f"   Status Code: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    import traceback
    traceback.print_exc()

