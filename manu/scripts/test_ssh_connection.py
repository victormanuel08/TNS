#!/usr/bin/env python3
"""
Script para probar la conexión SSH al servidor WireGuard desde Windows.
Ejecutar: python test_ssh_connection.py
"""
import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings
import paramiko

def test_ssh_connection():
    """Prueba la conexión SSH al servidor WireGuard"""
    
    print("=" * 60)
    print("Prueba de Conexión SSH a WireGuard Server")
    print("=" * 60)
    print()
    
    # Obtener configuración
    host = getattr(settings, 'WG_SERVER_HOST', os.getenv('WG_SERVER_HOST', ''))
    user = getattr(settings, 'WG_SERVER_USER', os.getenv('WG_SERVER_USER', 'root'))
    password = getattr(settings, 'WG_SERVER_PASSWORD', os.getenv('WG_SERVER_PASSWORD', ''))
    port = int(getattr(settings, 'WG_SERVER_SSH_PORT', os.getenv('WG_SERVER_SSH_PORT', '22')))
    key_path = getattr(settings, 'WG_SSH_KEY_PATH', os.getenv('WG_SSH_KEY_PATH', ''))
    
    if not host:
        print("❌ ERROR: WG_SERVER_HOST no está configurado")
        print("   Configúralo en .env o settings.py")
        return False
    
    print(f"Host: {host}")
    print(f"User: {user}")
    print(f"Port: {port}")
    print(f"Key Path: {key_path if key_path else 'Usando password'}")
    print()
    
    # Intentar conexión
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print("Conectando...")
        
        if key_path and Path(key_path).exists():
            print(f"Usando clave SSH: {key_path}")
            client.connect(
                hostname=host,
                port=port,
                username=user,
                key_filename=key_path,
                timeout=10
            )
        elif password:
            print("Usando password...")
            client.connect(
                hostname=host,
                port=port,
                username=user,
                password=password,
                timeout=10
            )
        else:
            print("❌ ERROR: Necesitas configurar WG_SERVER_PASSWORD o WG_SSH_KEY_PATH")
            return False
        
        print("✓ Conexión SSH exitosa!")
        print()
        
        # Probar comando wg
        print("Probando comando 'wg show'...")
        stdin, stdout, stderr = client.exec_command('sudo wg show')
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            output = stdout.read().decode('utf-8')
            print("✓ Comando 'wg show' ejecutado correctamente")
            print()
            print("Salida:")
            print("-" * 60)
            print(output)
            print("-" * 60)
        else:
            error = stderr.read().decode('utf-8')
            print(f"⚠ Comando falló (exit code: {exit_status})")
            print(f"Error: {error}")
            print()
            print("Posibles causas:")
            print("  - WireGuard no está instalado")
            print("  - El usuario no tiene permisos sudo")
            print("  - La interfaz WireGuard no existe")
        
        # Probar comando de solo lectura
        print()
        print("Probando comando 'whoami'...")
        stdin, stdout, stderr = client.exec_command('whoami')
        user_output = stdout.read().decode('utf-8').strip()
        print(f"✓ Usuario conectado: {user_output}")
        
        client.close()
        print()
        print("=" * 60)
        print("✓ Prueba completada exitosamente")
        print("=" * 60)
        return True
        
    except paramiko.AuthenticationException:
        print("❌ ERROR: Autenticación fallida")
        print("   Verifica el usuario y password/clave SSH")
        return False
    except paramiko.SSHException as e:
        print(f"❌ ERROR SSH: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        import paramiko
    except ImportError:
        print("❌ ERROR: paramiko no está instalado")
        print("   Instala con: pip install paramiko")
        sys.exit(1)
    
    success = test_ssh_connection()
    sys.exit(0 if success else 1)

