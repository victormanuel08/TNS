"""
Script admin para gestionar configuraciones de Firebird desde línea de comandos.
Se puede compilar a .exe con: pyinstaller --onefile --windowed admin_firebird.py
"""
import requests
import json
import sys
import os
from typing import Dict, Optional

# Configuración
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000/api')
API_KEY = os.getenv('API_KEY', '')

def mostrar_menu():
    """Muestra el menú principal"""
    print("\n" + "="*60)
    print("  ADMINISTRADOR DE CONFIGURACIONES FIREBIRD")
    print("="*60)
    print("1. Listar resoluciones (PREFIJO)")
    print("2. Actualizar resolución")
    print("3. Listar configuraciones (VARIOS)")
    print("4. Actualizar configuración")
    print("5. Información de empresa")
    print("0. Salir")
    print("="*60)

def hacer_request(method: str, url: str, data: Optional[Dict] = None) -> Dict:
    """Hace una petición HTTP con API Key"""
    headers = {
        'Content-Type': 'application/json',
        'API-Key': API_KEY,
        'x-api-key': API_KEY
    }
    
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=data)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=headers, json=data)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data)
        else:
            return {'error': f'Método {method} no soportado'}
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': f'Error de conexión: {str(e)}'}
    except Exception as e:
        return {'error': f'Error: {str(e)}'}

def listar_resoluciones(empresa_id: int):
    """Lista todas las resoluciones"""
    url = f"{API_BASE_URL}/firebird-admin/resoluciones/"
    result = hacer_request('GET', url, {'empresa_servidor_id': empresa_id})
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"\n📋 Resoluciones de: {result.get('empresa', 'N/A')}")
    print(f"Total: {result.get('total', 0)}")
    print("-" * 80)
    
    for res in result.get('resoluciones', []):
        print(f"\nCódigo Prefijo: {res.get('codprefijo')}")
        print(f"  Preimp: {res.get('preimp')}")
        print(f"  Resolución: {res.get('resolucion')}")
        print(f"  Número Fin: {res.get('numfinfacele')}")
        print(f"  Contingencia: {res.get('contingencia')}")
        print(f"  Prefijo: {res.get('prefijo')}")

def actualizar_resolucion(empresa_id: int):
    """Actualiza una resolución"""
    print("\n📝 Actualizar Resolución")
    codprefijo = input("Código Prefijo: ").strip()
    
    if not codprefijo:
        print("❌ Código prefijo es requerido")
        return
    
    print("\nDeja vacío para no actualizar:")
    preimp = input("Preimp: ").strip() or None
    resolucion = input("Resolución: ").strip() or None
    numfinfacele = input("Número Fin Facturación Electrónica: ").strip() or None
    contingencia = input("Contingencia (S/N): ").strip() or None
    prefijo = input("Prefijo: ").strip() or None
    
    data = {
        'empresa_servidor_id': empresa_id,
        'codprefijo': codprefijo
    }
    
    if preimp is not None:
        data['preimp'] = preimp
    if resolucion is not None:
        data['resolucion'] = resolucion
    if numfinfacele is not None:
        data['numfinfacele'] = numfinfacele
    if contingencia is not None:
        data['contingencia'] = contingencia
    if prefijo is not None:
        data['prefijo'] = prefijo
    
    url = f"{API_BASE_URL}/firebird-admin/resoluciones/actualizar/"
    result = hacer_request('PUT', url, data)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ {result.get('message', 'Actualizado exitosamente')}")

def listar_configuraciones(empresa_id: int):
    """Lista configuraciones"""
    url = f"{API_BASE_URL}/firebird-admin/configuraciones/"
    result = hacer_request('GET', url, {'empresa_servidor_id': empresa_id})
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"\n⚙️  Configuraciones de: {result.get('empresa', 'N/A')}")
    print("-" * 80)
    
    configs = result.get('configuraciones', {})
    for clave, valor in configs.items():
        # Ocultar tokens sensibles
        if 'TOKEN' in clave.upper():
            valor_display = valor[:10] + "..." if len(valor) > 10 else "***"
        else:
            valor_display = valor
        print(f"{clave}: {valor_display}")

def actualizar_configuracion(empresa_id: int):
    """Actualiza una configuración"""
    print("\n📝 Actualizar Configuración")
    clave = input("Clave (ej: TOKENDIANVM): ").strip()
    
    if not clave:
        print("❌ Clave es requerida")
        return
    
    valor = input("Valor: ").strip()
    
    data = {
        'empresa_servidor_id': empresa_id,
        'clave': clave,
        'valor': valor
    }
    
    url = f"{API_BASE_URL}/firebird-admin/configuraciones/actualizar/"
    result = hacer_request('PUT', url, data)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ {result.get('message', 'Actualizado exitosamente')}")

def info_empresa(empresa_id: int):
    """Muestra información de la empresa"""
    url = f"{API_BASE_URL}/firebird-admin/info/"
    result = hacer_request('GET', url, {'empresa_servidor_id': empresa_id})
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    empresa = result.get('empresa', {})
    print(f"\n📊 Información de Empresa")
    print("-" * 80)
    print(f"ID: {empresa.get('id')}")
    print(f"Nombre: {empresa.get('nombre')}")
    print(f"NIT: {empresa.get('nit')}")
    print(f"NIT Normalizado: {empresa.get('nit_normalizado')}")
    print(f"Año Fiscal: {empresa.get('anio_fiscal')}")
    print(f"Código: {empresa.get('codigo')}")
    print(f"Ruta Base: {empresa.get('ruta_base')}")

def main():
    """Función principal"""
    global API_BASE_URL, API_KEY
    
    # Cargar configuración desde archivo si existe
    config_file = 'admin_config.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                API_BASE_URL = config.get('api_base_url', API_BASE_URL)
                API_KEY = config.get('api_key', API_KEY)
        except:
            pass
    
    # Si no hay API_KEY, pedirla
    if not API_KEY:
        print("⚠️  No se encontró API_KEY")
        API_KEY = input("Ingresa tu API Key: ").strip()
        if not API_KEY:
            print("❌ API Key es requerida")
            return
    
    # Pedir empresa_id
    try:
        empresa_id = int(input("\nIngresa el ID de la empresa: "))
    except ValueError:
        print("❌ ID de empresa inválido")
        return
    
    while True:
        mostrar_menu()
        opcion = input("\nSelecciona una opción: ").strip()
        
        if opcion == '0':
            print("\n👋 ¡Hasta luego!")
            break
        elif opcion == '1':
            listar_resoluciones(empresa_id)
        elif opcion == '2':
            actualizar_resolucion(empresa_id)
        elif opcion == '3':
            listar_configuraciones(empresa_id)
        elif opcion == '4':
            actualizar_configuracion(empresa_id)
        elif opcion == '5':
            info_empresa(empresa_id)
        else:
            print("❌ Opción inválida")
        
        input("\nPresiona Enter para continuar...")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()

