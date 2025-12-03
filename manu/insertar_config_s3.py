#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para insertar/actualizar configuración S3 en la base de datos MANU.
Funciona en Windows y Ubuntu/Linux.

Ejecutar desde el directorio manu/:
    python insertar_config_s3.py

O desde cualquier lugar:
    python C:/ruta/completa/manu/insertar_config_s3.py
"""

import os
import sys
import django

# === CONFIGURACIÓN S3 (HARDCODEADA) ===
# Datos extraídos del script PowerShell que monta rclone:
#   rclone mount contabo:tns.gdb.firebird X:
#
# Remoto rclone: contabo
# Bucket/Path: tns.gdb.firebird
# Credenciales: Contabo Object Storage US-central 8601 Backup GDB

S3_CONFIG = {
    'nombre': 'Backups Principal',
    'bucket_name': 'tns.gdb.firebird',  # Del comando: contabo:tns.gdb.firebird
    'region': 'us-central-1',  # United States (Central) - Contabo
    'access_key_id': '3e673f951c2da05cf2b7a7798369c889',  # Credenciales de Contabo Object Storage
    'secret_access_key': 'b7052f69bb63b32b821ee2d79b0a8d4c',  # Credenciales de Contabo Object Storage
    'endpoint_url': 'https://usc1.contabostorage.com',  # Endpoint de Contabo Object Storage (S3-compatible) - US Central 1
    'activo': True
}

# 💡 Para obtener access_key_id y secret_access_key:
#    1. Abre: %APPDATA%\rclone\rclone.conf (Windows) o ~/.config/rclone/rclone.conf (Linux)
#    2. Busca la sección [contabo]
#    3. Copia los valores de access_key_id y secret_access_key aquí arriba

# ========================================

# Configurar Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    print(f"   Asegúrate de ejecutar este script desde el directorio 'manu/'")
    sys.exit(1)

from apps.sistema_analitico.models import ConfiguracionS3

def main():
    print("=" * 60)
    print("Configuración S3 para Backups - MANU")
    print("=" * 60)
    print()
    
    # Validar que los datos estén completos
    if not S3_CONFIG['access_key_id'] or not S3_CONFIG['secret_access_key']:
        print("❌ ERROR: Faltan credenciales en S3_CONFIG")
        sys.exit(1)
    
    try:
        # Crear o actualizar configuración
        config, created = ConfiguracionS3.objects.update_or_create(
            nombre=S3_CONFIG['nombre'],
            defaults={
                'bucket_name': S3_CONFIG['bucket_name'],
                'region': S3_CONFIG['region'],
                'access_key_id': S3_CONFIG['access_key_id'],
                'secret_access_key': S3_CONFIG['secret_access_key'],
                'endpoint_url': S3_CONFIG['endpoint_url'],
                'activo': S3_CONFIG['activo']
            }
        )
        
        if created:
            print("✅ Configuración S3 CREADA exitosamente")
        else:
            print("✅ Configuración S3 ACTUALIZADA exitosamente")
        
        print()
        print("📋 Detalles de la configuración:")
        print(f"   ID: {config.id}")
        print(f"   Nombre: {config.nombre}")
        print(f"   Bucket: {config.bucket_name}")
        print(f"   Región: {config.region}")
        print(f"   Access Key: {config.access_key_id[:10]}...")
        print(f"   Endpoint: {config.endpoint_url or 'AWS S3 (default)'}")
        print(f"   Activo: {'Sí' if config.activo else 'No'}")
        print()
        print("💡 Próximos pasos:")
        print("   1. Ve al admin frontend → pestaña '11. Backups S3'")
        print("   2. Verifica que la configuración aparece correctamente")
        print("   3. Selecciona una empresa y crea un backup de prueba")
        print()
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error al insertar/actualizar configuración S3: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

