#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar el endpoint records con el payload del usuario
"""
import requests
import json
import sys
import io

# Configurar stdout para UTF-8 (evitar errores de charmap en Windows)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configuración
API_URL = "http://localhost:8001/api/tns/records/"
API_KEY = "sk_Ben0l9No0lzO_VuCBT0xlZnQSDukhSRBiYhOiitdEHU"

# Payload exacto del usuario
payload = {
    "empresa_servidor_id": 192,
    "table_name": "MATERIAL",
    "fields": [
        "CODIGO",
        "CODBARRA",
        "DESCRIP",
        "PESO",
        "UNIDAD",
        "GM_CODIGO",
        "GM_DESCRIP",
        "GC_CODIGO",
        "GC_DESCRIP",
        "COSTO",
        "PRECIO1",
        "PRECIO2",
        "PRECIO3",
        "PRECIO4",
        "PRECIO5",
        "DESCUENTO1",
        "DESCUENTO2",
        "DESCUENTO3",
        "DESCUENTO4",
        "DESCUENTO5",
        "MATID",
        "GRUPMATID",
        "GCMATID"
    ],
    "foreign_keys": [
        {
            "table": "MATERIALSUC",
            "localField": "MATID",
            "foreignField": "MATID",
            "columns": [
                {"name": "COSTO", "as": "COSTO"},
                {"name": "PRECIO1", "as": "PRECIO1"},
                {"name": "PRECIO2", "as": "PRECIO2"},
                {"name": "PRECIO3", "as": "PRECIO3"},
                {"name": "PRECIO4", "as": "PRECIO4"},
                {"name": "PRECIO5", "as": "PRECIO5"},
                {"name": "DESCUENTO1", "as": "DESCUENTO1"},
                {"name": "DESCUENTO2", "as": "DESCUENTO2"},
                {"name": "DESCUENTO3", "as": "DESCUENTO3"},
                {"name": "DESCUENTO4", "as": "DESCUENTO4"},
                {"name": "DESCUENTO5", "as": "DESCUENTO5"}
            ]
        },
        {
            "table": "GRUPMAT",
            "localField": "GRUPMATID",
            "foreignField": "GRUPMATID",
            "columns": [
                {"name": "CODIGO", "as": "GM_CODIGO"},
                {"name": "DESCRIP", "as": "GM_DESCRIP"}
            ]
        },
        {
            "table": "GCMAT",
            "localField": "GCMATID",
            "foreignField": "GCMATID",
            "columns": [
                {"name": "CODIGO", "as": "GC_CODIGO"},
                {"name": "DESCRIP", "as": "GC_DESCRIP"}
            ]
        }
    ],
    "order_by": [
        {
            "field": "CODIGO",
            "direction": "ASC"
        }
    ],
    "page": 1,
    "page_size": 200
}

def main():
    print("=" * 80)
    print("[TEST] TESTING /api/tns/records/")
    print("=" * 80)
    print(f"URL: {API_URL}")
    print(f"Encoding: {sys.getdefaultencoding()}")
    print(f"File system encoding: {sys.getfilesystemencoding()}")
    print()
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Api-Key": API_KEY
    }
    
    print("[SEND] Enviando request...")
    print(f"   Payload size: {len(json.dumps(payload))} bytes")
    print()
    
    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"[RECV] Response Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print()
        
        if response.status_code == 200:
            print("[OK] SUCCESS!")
            data = response.json()
            if 'data' in data:
                print(f"   Filas recibidas: {len(data['data'])}")
                if len(data['data']) > 0:
                    print(f"   Primera fila (primeros 3 campos):")
                    first_row = data['data'][0]
                    for i, (k, v) in enumerate(list(first_row.items())[:3]):
                        print(f"      {k}: {repr(str(v)[:50]) if v else None}")
            print()
            print("[RESPONSE] Response completo (primeros 500 chars):")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
        else:
            print("[ERROR] ERROR!")
            print(f"   Status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"   Response text: {response.text[:500]}")
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request Error: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"[ERROR] Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()

