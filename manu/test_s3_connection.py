#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para probar conexión S3 con Contabo.
Ejecutar desde el directorio manu/: python test_s3_connection.py
"""

import os
import sys
import django

# Configurar Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    sys.exit(1)

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from apps.sistema_analitico.models import ConfiguracionS3

def test_s3_connection():
    print("=" * 60)
    print("Test de Conexión S3 - Contabo")
    print("=" * 60)
    print()
    
    # Obtener configuración
    config = ConfiguracionS3.objects.filter(activo=True).first()
    if not config:
        print("❌ No hay configuración S3 activa")
        return
    
    print(f"📋 Configuración:")
    print(f"   Endpoint: {config.endpoint_url}")
    print(f"   Bucket: {config.bucket_name}")
    print(f"   Region: {config.region}")
    print(f"   Access Key: {config.access_key_id[:10]}...")
    print()
    
    # Crear cliente S3
    s3_config = Config(
        signature_version='s3v4',
        s3={'addressing_style': 'path'}
    )
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            region_name=config.region,
            endpoint_url=config.endpoint_url,
            config=s3_config
        )
        print("✅ Cliente S3 creado")
    except Exception as e:
        print(f"❌ Error creando cliente S3: {e}")
        return
    
    # 1. Listar buckets
    print()
    print("1️⃣ Listando buckets disponibles...")
    try:
        response = s3_client.list_buckets()
        buckets = [b['Name'] for b in response.get('Buckets', [])]
        if buckets:
            print(f"   ✅ Buckets encontrados: {buckets}")
        else:
            print("   ⚠️ No se encontraron buckets")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"   ❌ Error listando buckets: {error_code} - {error_msg}")
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
    
    # 2. Verificar si el bucket existe
    print()
    print(f"2️⃣ Verificando bucket '{config.bucket_name}'...")
    try:
        s3_client.head_bucket(Bucket=config.bucket_name)
        print(f"   ✅ Bucket '{config.bucket_name}' existe y es accesible")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"   ❌ Error con bucket: {error_code} - {error_msg}")
        if error_code == '404':
            print(f"   💡 El bucket '{config.bucket_name}' NO EXISTE")
            print(f"      Crea el bucket en el panel de Contabo o usa un bucket existente")
        elif error_code == '403':
            print(f"   💡 Sin permisos para acceder al bucket")
            print(f"      Verifica las credenciales y permisos")
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
    
    # 3. Listar objetos en el bucket (si existe)
    print()
    print(f"3️⃣ Listando objetos en bucket '{config.bucket_name}'...")
    try:
        response = s3_client.list_objects_v2(Bucket=config.bucket_name, MaxKeys=5)
        if 'Contents' in response:
            print(f"   ✅ Encontrados {len(response['Contents'])} objetos (mostrando primeros 5):")
            for obj in response['Contents'][:5]:
                print(f"      - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("   ℹ️ Bucket vacío")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"   ❌ Error listando objetos: {error_code} - {error_msg}")
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
    
    # 4. Probar subir un archivo pequeño de prueba
    print()
    print(f"4️⃣ Probando subir archivo de prueba...")
    test_file = '/tmp/test_s3_upload.txt'
    test_key = 'test/upload_test.txt'
    
    try:
        # Crear archivo de prueba
        with open(test_file, 'w') as f:
            f.write("Test upload from MANU")
        
        print(f"   📝 Archivo de prueba creado: {test_file}")
        
        # Intentar subir
        s3_client.upload_file(
            test_file,
            config.bucket_name,
            test_key
        )
        print(f"   ✅ Archivo subido exitosamente a: {test_key}")
        
        # Limpiar: eliminar archivo de prueba
        try:
            s3_client.delete_object(Bucket=config.bucket_name, Key=test_key)
            print(f"   🗑️ Archivo de prueba eliminado")
        except:
            pass
        
        # Eliminar archivo local
        os.remove(test_file)
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"   ❌ Error subiendo archivo: {error_code} - {error_msg}")
        print(f"   📋 Detalles completos del error:")
        print(f"      {e.response}")
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Limpiar archivo local si existe
        if os.path.exists(test_file):
            os.remove(test_file)
    
    print()
    print("=" * 60)

if __name__ == '__main__':
    test_s3_connection()

