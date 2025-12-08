#!/usr/bin/env python
"""
Script simple para probar la API de DeepSeek y ver la respuesta completa.
Ejecutar: python test_deepseek_response.py
"""

import requests
import json
import os

# Configurar Django para leer settings
import sys
import os

# Agregar el directorio manu al path
manu_dir = os.path.join(os.path.dirname(__file__), 'manu')
if os.path.exists(manu_dir):
    sys.path.insert(0, manu_dir)

# Intentar obtener API key desde Django settings
api_key = ''
api_url = 'https://api.deepseek.com/v1/chat/completions'

try:
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    from django.conf import settings
    if settings.configured:
        api_key = getattr(settings, 'DEEPSEEK_API_KEY', '')
        api_url = getattr(settings, 'DEEPSEEK_API_URL', api_url)
        if api_key:
            print(f"✅ API Key cargada desde Django settings")
except Exception as e:
    # Si falla Django, continuar sin él
    pass

# Si no está en Django, intentar desde variable de entorno
if not api_key:
    api_key = os.getenv('DEEPSEEK_API_KEY', '')

# Si aún no hay API key, pedirla
if not api_key:
    print("⚠️  No se encontró DEEPSEEK_API_KEY")
    print("   Opciones:")
    print("   1. Configúrala en tu archivo .env como: DEEPSEEK_API_KEY=sk-...")
    print("   2. O ejecuta: export DEEPSEEK_API_KEY=sk-...")
    print("   3. O pégala aquí (se usará solo para esta prueba):")
    api_key = input("   API Key: ").strip()
    
    if not api_key:
        print("❌ ERROR: Se requiere API Key")
        exit(1)

print(f"🔍 Probando API de DeepSeek...")
print(f"📍 URL: {api_url}")
print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
print("-" * 60)

# Payload simple y barato (pregunta corta)
payload = {
    "model": "deepseek-chat",
    "messages": [
        {
            "role": "user",
            "content": "Di 'Hola' en una palabra"
        }
    ],
    "max_tokens": 10,
    "temperature": 0.1
}

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

try:
    print("📤 Enviando petición...")
    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    
    print("✅ Respuesta recibida!")
    print("=" * 60)
    
    data = response.json()
    
    # Mostrar respuesta completa formateada
    print("\n📋 RESPUESTA COMPLETA (JSON):")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    print("\n🔍 INFORMACIÓN DE USAGE (TOKENS):")
    
    if 'usage' in data:
        usage = data['usage']
        print(f"  - prompt_tokens: {usage.get('prompt_tokens', 'N/A')}")
        print(f"  - completion_tokens: {usage.get('completion_tokens', 'N/A')}")
        print(f"  - total_tokens: {usage.get('total_tokens', 'N/A')}")
        
        # Buscar campos relacionados con cache
        print("\n📊 CAMPOS EN 'usage':")
        for key, value in usage.items():
            print(f"  - {key}: {value}")
    else:
        print("  ⚠️ No se encontró campo 'usage' en la respuesta")
    
    print("\n" + "=" * 60)
    print("\n💬 CONTENIDO DE LA RESPUESTA:")
    if 'choices' in data and len(data['choices']) > 0:
        content = data['choices'][0].get('message', {}).get('content', 'N/A')
        print(f"  {content}")
    
    print("\n" + "=" * 60)
    print("\n✅ Script completado exitosamente!")
    
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

