#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para actualizar rutas de backups en la base de datos.

Este script actualiza las rutas S3 en la tabla BackupS3 de la estructura antigua
a la nueva estructura organizada por servidor.

Estructura antigua: {nit}/{anio}/backups/{archivo}
Estructura nueva: {server_name}/{nit}/{anio}/backups/{archivo}

Ejecutar desde el directorio manu/:
    python manage.py actualizar_rutas_backups_bd

O con dry-run (solo muestra qué haría sin hacer cambios):
    python manage.py actualizar_rutas_backups_bd --dry-run
"""

import os
import sys
import django
from django.core.management.base import BaseCommand
from django.db import transaction
import re

# Configurar Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    sys.exit(1)

from apps.sistema_analitico.models import EmpresaServidor, BackupS3


class Command(BaseCommand):
    help = 'Actualiza rutas de backups en BD de estructura antigua a nueva organizada por servidor'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra qué haría sin hacer cambios reales',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write("=" * 70)
        self.stdout.write("Actualización de Rutas de Backups en Base de Datos")
        self.stdout.write("=" * 70)
        self.stdout.write("")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  MODO DRY-RUN: No se harán cambios reales"))
            self.stdout.write("")
        
        try:
            # Buscar todos los backups con estructura antigua en BD
            # Estructura antigua: {nit}/{anio}/backups/{archivo}
            # NO debe empezar con un nombre de servidor conocido
            backups = BackupS3.objects.all()
            
            backups_antiguos = []
            servidores = EmpresaServidor.objects.values_list('servidor__nombre', flat=True).distinct()
            nombres_servidores = set()
            for servidor_nombre in servidores:
                nombre_normalizado = servidor_nombre.replace(' ', '_').replace('/', '_').replace('\\', '_')
                nombres_servidores.add(nombre_normalizado)
            
            self.stdout.write(f"📋 Servidores conocidos: {', '.join(sorted(nombres_servidores)) if nombres_servidores else 'Ninguno'}")
            self.stdout.write("")
            
            for backup in backups:
                ruta_actual = backup.ruta_s3
                
                # Detectar estructura antigua: {nit}/{anio}/backups/{archivo}
                match = re.match(r'^([^/]+)/(\d+)/backups/(.+)$', ruta_actual)
                if match:
                    primer_segmento, anio_str, archivo = match.groups()
                    
                    # Verificar que el primer segmento sea solo números (NIT normalizado)
                    # y que NO sea un nombre de servidor conocido
                    if primer_segmento.isdigit() and primer_segmento not in nombres_servidores:
                        # Buscar la empresa correspondiente
                        empresa = backup.empresa_servidor
                        if empresa:
                            server_name = empresa.servidor.nombre.replace(' ', '_').replace('/', '_').replace('\\', '_')
                            nueva_ruta = f"{server_name}/{primer_segmento}/{anio_str}/backups/{archivo}"
                            
                            backups_antiguos.append({
                                'backup': backup,
                                'ruta_antigua': ruta_actual,
                                'ruta_nueva': nueva_ruta,
                                'empresa': empresa
                            })
            
            if not backups_antiguos:
                self.stdout.write(self.style.SUCCESS("✅ No se encontraron backups con estructura antigua en BD"))
                self.stdout.write("   Todas las rutas ya están actualizadas o no hay backups.")
                return
            
            self.stdout.write(f"📦 Encontrados {len(backups_antiguos)} backups con estructura antigua en BD")
            self.stdout.write("")
            
            # Mostrar algunos ejemplos
            self.stdout.write("   Ejemplos de backups a actualizar:")
            for item in backups_antiguos[:5]:
                self.stdout.write(f"      - {item['empresa'].nombre}")
                self.stdout.write(f"        Antigua: {item['ruta_antigua']}")
                self.stdout.write(f"        Nueva:   {item['ruta_nueva']}")
            if len(backups_antiguos) > 5:
                self.stdout.write(f"      ... y {len(backups_antiguos) - 5} más")
            self.stdout.write("")
            
            if dry_run:
                self.stdout.write(self.style.WARNING("⚠️  DRY-RUN: No se realizarán cambios"))
                return
            
            # Confirmar
            self.stdout.write(self.style.WARNING("⚠️  Se actualizarán las rutas en la base de datos"))
            respuesta = input("¿Continuar? (s/N): ")
            if respuesta.lower() != 's':
                self.stdout.write("❌ Actualización cancelada")
                return
            
            # Actualizar rutas
            self.stdout.write("")
            self.stdout.write("🚀 Iniciando actualización...")
            self.stdout.write("")
            
            actualizados = 0
            errores = 0
            
            with transaction.atomic():
                for i, item in enumerate(backups_antiguos, 1):
                    try:
                        backup = item['backup']
                        ruta_nueva = item['ruta_nueva']
                        empresa = item['empresa']
                        
                        self.stdout.write(f"[{i}/{len(backups_antiguos)}] {empresa.nombre} ({empresa.servidor.nombre})")
                        self.stdout.write(f"   Antigua: {backup.ruta_s3}")
                        self.stdout.write(f"   Nueva:   {ruta_nueva}")
                        
                        backup.ruta_s3 = ruta_nueva
                        backup.save()
                        
                        actualizados += 1
                        self.stdout.write(self.style.SUCCESS("   ✅ Actualizado"))
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"   ❌ Error: {e}"))
                        errores += 1
                    
                    self.stdout.write("")
            
            # Resumen final
            self.stdout.write("")
            self.stdout.write("=" * 70)
            self.stdout.write("Resumen de actualización:")
            self.stdout.write(f"   ✅ Actualizados exitosamente: {actualizados}")
            if errores > 0:
                self.stdout.write(self.style.ERROR(f"   ❌ Errores: {errores}"))
            self.stdout.write("=" * 70)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error durante la actualización: {e}"))
            import traceback
            traceback.print_exc()

