#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de migración para reorganizar backups S3 por servidor.

Estructura antigua: {nit}/{anio}/backups/{archivo}
Estructura nueva: {server_name}/{nit}/{anio}/backups/{archivo}

Este script:
1. Lista todos los backups existentes en la estructura antigua
2. Los mueve a la nueva estructura organizada por servidor
3. Actualiza las rutas en la base de datos (BackupS3)

Ejecutar desde el directorio manu/:
    python manage.py migrar_backups_s3_por_servidor

O con dry-run (solo muestra qué haría sin hacer cambios):
    python manage.py migrar_backups_s3_por_servidor --dry-run
"""

import os
import sys
import django
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

# Configurar Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    sys.exit(1)

from apps.sistema_analitico.models import EmpresaServidor, ConfiguracionS3, BackupS3, Servidor
from apps.sistema_analitico.services.backup_s3_service import BackupS3Service
from botocore.exceptions import ClientError
import re


class Command(BaseCommand):
    help = 'Migra backups S3 de estructura antigua a nueva organizada por servidor'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra qué haría sin hacer cambios reales',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write("=" * 70)
        self.stdout.write("Migración de Backups S3 - Reorganización por Servidor")
        self.stdout.write("=" * 70)
        self.stdout.write("")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  MODO DRY-RUN: No se harán cambios reales"))
            self.stdout.write("")
        
        # Obtener configuración S3
        config_s3 = ConfiguracionS3.objects.filter(activo=True).first()
        if not config_s3:
            self.stdout.write(self.style.ERROR("❌ No hay configuración S3 activa"))
            return
        
        servicio = BackupS3Service(config_s3)
        
        # Obtener nombres de servidores conocidos (normalizados)
        servidores = Servidor.objects.all()
        nombres_servidores = set()
        for servidor in servidores:
            nombre_normalizado = servidor.nombre.replace(' ', '_').replace('/', '_').replace('\\', '_')
            nombres_servidores.add(nombre_normalizado)
        
        self.stdout.write(f"📋 Servidores conocidos: {', '.join(sorted(nombres_servidores)) if nombres_servidores else 'Ninguno'}")
        self.stdout.write("")
        
        # Listar todos los objetos en S3 con estructura antigua
        self.stdout.write("📋 Buscando backups con estructura antigua...")
        self.stdout.write("")
        
        try:
            # Listar todos los objetos en el bucket
            paginator = servicio.s3_client.get_paginator('list_objects_v2')
            objetos_antiguos = []
            objetos_totales = 0
            objetos_ignorados = []
            
            for page in paginator.paginate(Bucket=servicio.bucket_name):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objetos_totales += 1
                        key = obj['Key']
                        
                        # Detectar estructura antigua: {nit}/{anio}/backups/{archivo}
                        # El primer segmento debe ser solo números (NIT normalizado)
                        # y NO debe ser un nombre de servidor conocido
                        match = re.match(r'^([^/]+)/(\d+)/backups/(.+)$', key)
                        if match:
                            primer_segmento, anio_str, archivo = match.groups()
                            
                            # Verificar que el primer segmento sea solo números (NIT normalizado)
                            # y que NO sea un nombre de servidor conocido
                            if primer_segmento.isdigit() and primer_segmento not in nombres_servidores:
                                objetos_antiguos.append({
                                    'key': key,
                                    'nit_anio': primer_segmento,
                                    'anio': int(anio_str),
                                    'archivo': archivo,
                                    'size': obj['Size']
                                })
                            else:
                                objetos_ignorados.append({
                                    'key': key,
                                    'razon': 'servidor_ conocido' if primer_segmento in nombres_servidores else 'no_es_nit_numerico'
                                })
                        elif '/backups/' in key:
                            # Tiene /backups/ pero no coincide con el patrón esperado
                            objetos_ignorados.append({
                                'key': key,
                                'razon': 'patron_no_coincide'
                            })
            
            self.stdout.write(f"📊 Total de objetos en S3: {objetos_totales}")
            if objetos_ignorados:
                self.stdout.write(f"   Objetos ignorados: {len(objetos_ignorados)}")
                # Mostrar algunos ejemplos de objetos ignorados
                if len(objetos_ignorados) <= 10:
                    self.stdout.write("   Ejemplos de objetos ignorados:")
                    for obj_ign in objetos_ignorados[:5]:
                        self.stdout.write(f"      - {obj_ign['key']} ({obj_ign['razon']})")
            self.stdout.write("")
            
            if not objetos_antiguos:
                self.stdout.write(self.style.WARNING("⚠️  No se encontraron backups con estructura antigua"))
                self.stdout.write("")
                self.stdout.write("   Posibles razones:")
                self.stdout.write("   - Todos los backups ya están en la nueva estructura")
                self.stdout.write("   - No hay backups en S3")
                self.stdout.write("   - Los backups tienen una estructura diferente")
                self.stdout.write("")
                if objetos_ignorados:
                    self.stdout.write("   Ejemplos de objetos encontrados (pero ignorados):")
                    for obj_ign in objetos_ignorados[:10]:
                        self.stdout.write(f"      - {obj_ign['key']} ({obj_ign['razon']})")
                return
            
            self.stdout.write(f"📦 Encontrados {len(objetos_antiguos)} backups con estructura antigua")
            self.stdout.write("")
            # Mostrar algunos ejemplos
            self.stdout.write("   Ejemplos de backups encontrados:")
            for obj in objetos_antiguos[:5]:
                self.stdout.write(f"      - {obj['key']} ({obj['size'] / (1024*1024):.2f} MB)")
            if len(objetos_antiguos) > 5:
                self.stdout.write(f"      ... y {len(objetos_antiguos) - 5} más")
            self.stdout.write("")
            
            # Agrupar por NIT y año para encontrar la empresa correspondiente
            self.stdout.write("🔍 Buscando empresas correspondientes...")
            self.stdout.write("")
            
            migraciones = []
            no_encontrados = []
            
            for obj in objetos_antiguos:
                nit_anio = obj['nit_anio']
                anio = obj['anio']
                
                # Buscar empresa con este NIT y año fiscal
                empresa = EmpresaServidor.objects.filter(
                    nit_normalizado=nit_anio,
                    anio_fiscal=anio
                ).first()
                
                if empresa:
                    # Calcular nueva ruta
                    server_name = empresa.servidor.nombre.replace(' ', '_').replace('/', '_').replace('\\', '_')
                    nueva_ruta = f"{server_name}/{nit_anio}/{anio}/backups/{obj['archivo']}"
                    
                    migraciones.append({
                        'objeto': obj,
                        'empresa': empresa,
                        'ruta_antigua': obj['key'],
                        'ruta_nueva': nueva_ruta
                    })
                else:
                    no_encontrados.append(obj)
            
            # Mostrar resumen
            self.stdout.write(f"✅ Empresas encontradas: {len(migraciones)}")
            if no_encontrados:
                self.stdout.write(self.style.WARNING(f"⚠️  Backups sin empresa correspondiente: {len(no_encontrados)}"))
                self.stdout.write("")
                self.stdout.write("   Backups sin empresa (no se migrarán):")
                for obj in no_encontrados[:10]:  # Mostrar primeros 10
                    self.stdout.write(f"      - {obj['key']} (NIT: {obj['nit_anio']}, Año: {obj['anio']})")
                if len(no_encontrados) > 10:
                    self.stdout.write(f"      ... y {len(no_encontrados) - 10} más")
                self.stdout.write("")
            
            if not migraciones:
                self.stdout.write(self.style.WARNING("⚠️  No hay backups para migrar"))
                return
            
            # Mostrar plan de migración
            self.stdout.write("📋 Plan de migración:")
            self.stdout.write("")
            
            # Agrupar por servidor para mostrar mejor
            por_servidor = {}
            for mig in migraciones:
                server_name = mig['empresa'].servidor.nombre
                if server_name not in por_servidor:
                    por_servidor[server_name] = []
                por_servidor[server_name].append(mig)
            
            for server_name, migs in por_servidor.items():
                self.stdout.write(f"   📁 Servidor: {server_name} ({len(migs)} backups)")
            
            self.stdout.write("")
            
            if dry_run:
                self.stdout.write(self.style.WARNING("⚠️  DRY-RUN: No se realizarán cambios"))
                return
            
            # Confirmar
            self.stdout.write(self.style.WARNING("⚠️  Se moverán los archivos y se actualizarán las rutas en BD"))
            respuesta = input("¿Continuar? (s/N): ")
            if respuesta.lower() != 's':
                self.stdout.write("❌ Migración cancelada")
                return
            
            # Realizar migración
            self.stdout.write("")
            self.stdout.write("🚀 Iniciando migración...")
            self.stdout.write("")
            
            migrados = 0
            errores = 0
            actualizados_bd = 0
            
            with transaction.atomic():
                for i, mig in enumerate(migraciones, 1):
                    try:
                        ruta_antigua = mig['ruta_antigua']
                        ruta_nueva = mig['ruta_nueva']
                        empresa = mig['empresa']
                        
                        self.stdout.write(f"[{i}/{len(migraciones)}] {empresa.nombre} ({empresa.servidor.nombre})")
                        self.stdout.write(f"   Antigua: {ruta_antigua}")
                        self.stdout.write(f"   Nueva:   {ruta_nueva}")
                        
                        # Copiar objeto a nueva ubicación
                        servicio.s3_client.copy_object(
                            CopySource={'Bucket': servicio.bucket_name, 'Key': ruta_antigua},
                            Bucket=servicio.bucket_name,
                            Key=ruta_nueva
                        )
                        
                        # Eliminar objeto antiguo
                        servicio.s3_client.delete_object(
                            Bucket=servicio.bucket_name,
                            Key=ruta_antigua
                        )
                        
                        # Actualizar rutas en BD
                        # Buscar por empresa y nombre de archivo (más confiable)
                        nombre_archivo = mig['objeto']['archivo']
                        backups_bd = BackupS3.objects.filter(
                            empresa_servidor=empresa,
                            nombre_archivo=nombre_archivo
                        )
                        
                        # Si no encuentra por nombre, buscar por ruta antigua
                        if not backups_bd.exists():
                            backups_bd = BackupS3.objects.filter(
                                empresa_servidor=empresa,
                                ruta_s3=ruta_antigua
                            )
                        
                        # Si aún no encuentra, buscar por empresa y año fiscal (último recurso)
                        if not backups_bd.exists():
                            backups_bd = BackupS3.objects.filter(
                                empresa_servidor=empresa,
                                anio_fiscal=empresa.anio_fiscal
                            ).order_by('-fecha_backup')[:1]  # Solo el más reciente
                        
                        if backups_bd.exists():
                            count = backups_bd.count()
                            backups_bd.update(ruta_s3=ruta_nueva)
                            actualizados_bd += count
                            self.stdout.write(f"   📝 Actualizados en BD: {count} registro(s)")
                        else:
                            self.stdout.write(self.style.WARNING("   ⚠️  No se encontró registro en BD para actualizar"))
                        
                        migrados += 1
                        self.stdout.write(self.style.SUCCESS("   ✅ Migrado"))
                        
                    except ClientError as e:
                        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                        self.stdout.write(self.style.ERROR(f"   ❌ Error: {error_code}"))
                        errores += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"   ❌ Error: {e}"))
                        errores += 1
                    
                    self.stdout.write("")
            
            # Resumen final
            self.stdout.write("")
            self.stdout.write("=" * 70)
            self.stdout.write("Resumen de migración:")
            self.stdout.write(f"   ✅ Migrados exitosamente: {migrados}")
            self.stdout.write(f"   📝 Rutas actualizadas en BD: {actualizados_bd}")
            if errores > 0:
                self.stdout.write(self.style.ERROR(f"   ❌ Errores: {errores}"))
            if no_encontrados:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Sin empresa correspondiente: {len(no_encontrados)}"))
            self.stdout.write("=" * 70)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error durante la migración: {e}"))
            import traceback
            traceback.print_exc()

