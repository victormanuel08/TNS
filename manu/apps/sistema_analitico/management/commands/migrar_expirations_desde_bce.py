#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comando para migrar Expirations (Vigencias Tributarias) directamente desde BCE a MANU.

Lee directamente desde core_expirations en la base de datos BCE y reinserta correctamente
en MANU, corrigiendo el problema de que se insertó con "TODOS" en tipo_tercero y tipo_regimen.

La homologación se hace por:
- Código del impuesto (tax_code)
- Código del tipo de tercero (third_type_code) o NULL
- Código del tipo de régimen (regiment_type_code) o NULL
- Dígitos del NIT (digits)
- Fecha límite (date)

Ejecutar desde el directorio manu/:
    python manage.py migrar_expirations_desde_bce

O con dry-run (solo muestra qué haría sin hacer cambios):
    python manage.py migrar_expirations_desde_bce --dry-run
"""

import os
import sys
import django
from django.core.management.base import BaseCommand
from django.db import transaction

# Configurar Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    sys.exit(1)

from apps.sistema_analitico.models import TipoTercero, TipoRegimen, Impuesto, VigenciaTributaria
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

# Credenciales hardcodeadas de BCE
BCE_DB_CONFIG = {
    'dbname': 'bcemanagement',
    'user': 'postgres',
    'password': 'Bce2024.',
    'host': '198.7.113.197',  # IP pública del servidor BCE
    'port': '5432'
}


class Command(BaseCommand):
    help = 'Migra Expirations (Vigencias Tributarias) desde BCE a MANU, corrigiendo tipos incorrectos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin guardar (solo mostrar qué se haría)'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        self.stdout.write("=" * 70)
        self.stdout.write("Migración de Expirations (Vigencias Tributarias) desde BCE")
        self.stdout.write("=" * 70)
        self.stdout.write("")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY RUN - No se guardarán cambios'))
            self.stdout.write("")
        
        # Conectar a BCE
        try:
            bce_conn = psycopg2.connect(**BCE_DB_CONFIG)
            self.stdout.write(self.style.SUCCESS('✅ Conexión a base de datos BCE establecida'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error conectando a BCE: {e}'))
            return
        
        try:
            # Leer datos de BCE
            self.stdout.write("")
            self.stdout.write("📋 Leyendo datos de BCE...")
            
            with bce_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Obtener Expirations con todas sus relaciones
                # Nota: Expirations tiene relación ManyToMany con Tax, necesitamos usar la tabla intermedia
                cursor.execute("""
                    SELECT DISTINCT
                        e.id as expiration_id,
                        t.code as tax_code,
                        t.name as tax_name,
                        t.description as tax_description,
                        e.third_types_id,
                        tt.code as third_type_code,
                        tt.name as third_type_name,
                        e.regiments_types_id,
                        rt.code as regiment_type_code,
                        rt.name as regiment_type_name,
                        e.digits,
                        e.date,
                        e.description
                    FROM core_expirations e
                    INNER JOIN core_tax_expirations cte ON e.id = cte.expirations_id
                    INNER JOIN core_tax t ON cte.tax_id = t.id
                    LEFT JOIN core_third_types tt ON e.third_types_id = tt.id
                    LEFT JOIN core_regiments_types rt ON e.regiments_types_id = rt.id
                    ORDER BY t.code, e.date, e.digits
                """)
                expirations_data = cursor.fetchall()
            
            self.stdout.write(f'   📊 {len(expirations_data)} Expirations encontradas en BCE')
            self.stdout.write("")
            
            # Mostrar algunos ejemplos
            if expirations_data:
                self.stdout.write("   Ejemplos de datos a migrar:")
                for i, row in enumerate(expirations_data[:5]):
                    third_code = row.get('third_type_code') or 'NULL'
                    regiment_code = row.get('regiment_type_code') or 'NULL'
                    digits = row.get('digits') or '""'
                    self.stdout.write(f"      {i+1}. {row.get('tax_code')} | Dígitos: {digits} | Tipo: {third_code} | Régimen: {regiment_code} | Fecha: {row.get('date')}")
                if len(expirations_data) > 5:
                    self.stdout.write(f"      ... y {len(expirations_data) - 5} más")
                self.stdout.write("")
            
            if dry_run:
                self.stdout.write(self.style.WARNING('⚠️  DRY RUN - No se guardarán cambios'))
                return
            
            # Confirmar borrado
            total_actual = VigenciaTributaria.objects.count()
            self.stdout.write(self.style.WARNING(f'⚠️  Se borrarán {total_actual} vigencias actuales en MANU'))
            self.stdout.write(self.style.WARNING(f'⚠️  Se insertarán {len(expirations_data)} vigencias desde BCE'))
            respuesta = input("¿Continuar? (s/N): ")
            if respuesta.lower() != 's':
                self.stdout.write("❌ Migración cancelada")
                return
            
            # Realizar migración
            self.stdout.write("")
            self.stdout.write("🚀 Iniciando migración...")
            self.stdout.write("")
            
            tipos_tercero_creados = 0
            tipos_regimen_creados = 0
            impuestos_creados = 0
            vigencias_creadas = 0
            vigencias_actualizadas = 0
            errores = 0
            
            with transaction.atomic():
                # PASO 1: Borrar todas las vigencias actuales
                self.stdout.write("🗑️  Borrando vigencias actuales en MANU...")
                total_borradas = VigenciaTributaria.objects.all().delete()[0]
                self.stdout.write(f"   ✅ {total_borradas} vigencias borradas")
                self.stdout.write("")
                
                # PASO 2: Migrar tipos de tercero y régimen (si no existen)
                self.stdout.write("📋 Verificando tipos de tercero y régimen...")
                tipos_tercero_codes = set()
                tipos_regimen_codes = set()
                
                for row in expirations_data:
                    if row.get('third_type_code'):
                        tipos_tercero_codes.add(row['third_type_code'])
                    if row.get('regiment_type_code'):
                        tipos_regimen_codes.add(row['regiment_type_code'])
                
                # Crear tipos de tercero que falten
                for code in tipos_tercero_codes:
                    tipo, created = TipoTercero.objects.get_or_create(
                        codigo=code,
                        defaults={'nombre': code}
                    )
                    if created:
                        tipos_tercero_creados += 1
                
                # Crear tipos de régimen que falten
                for code in tipos_regimen_codes:
                    tipo, created = TipoRegimen.objects.get_or_create(
                        codigo=code,
                        defaults={'nombre': code}
                    )
                    if created:
                        tipos_regimen_creados += 1
                
                self.stdout.write(f"   ✅ Tipos de tercero: {len(tipos_tercero_codes)} encontrados ({tipos_tercero_creados} creados)")
                self.stdout.write(f"   ✅ Tipos de régimen: {len(tipos_regimen_codes)} encontrados ({tipos_regimen_creados} creados)")
                self.stdout.write("")
                
                # PASO 3: Migrar impuestos (si no existen)
                self.stdout.write("📋 Verificando impuestos...")
                impuestos_codes = set()
                for row in expirations_data:
                    impuestos_codes.add(row['tax_code'])
                
                for code in impuestos_codes:
                    # Buscar el primer registro con este código para obtener nombre y descripción
                    ejemplo = next((r for r in expirations_data if r['tax_code'] == code), None)
                    if ejemplo:
                        impuesto, created = Impuesto.objects.get_or_create(
                            codigo=code,
                            defaults={
                                'nombre': ejemplo.get('tax_name') or code,
                                'descripcion': ejemplo.get('tax_description') or ''
                            }
                        )
                        if created:
                            impuestos_creados += 1
                
                self.stdout.write(f"   ✅ Impuestos: {len(impuestos_codes)} encontrados ({impuestos_creados} creados)")
                self.stdout.write("")
                
                # PASO 4: Migrar Expirations (Vigencias Tributarias)
                self.stdout.write("📋 Migrando vigencias tributarias...")
                
                for i, row in enumerate(expirations_data, 1):
                    try:
                        tax_code = row.get('tax_code')
                        tax_name = row.get('tax_name')
                        tax_description = row.get('tax_description')
                        third_type_code = row.get('third_type_code')
                        regiment_type_code = row.get('regiment_type_code')
                        digits = row.get('digits') or ''
                        date = row.get('date')
                        description = row.get('description') or 'Sin definir'
                        
                        # Obtener Impuesto
                        try:
                            impuesto = Impuesto.objects.get(codigo=tax_code)
                        except Impuesto.DoesNotExist:
                            impuesto = Impuesto.objects.create(
                                codigo=tax_code,
                                nombre=tax_name or tax_code,
                                descripcion=tax_description or ''
                            )
                            impuestos_creados += 1
                        
                        # Obtener TipoTercero (si existe código, sino NULL)
                        tipo_tercero = None
                        if third_type_code:
                            try:
                                tipo_tercero = TipoTercero.objects.get(codigo=third_type_code)
                            except TipoTercero.DoesNotExist:
                                tipo_tercero = TipoTercero.objects.create(
                                    codigo=third_type_code,
                                    nombre=row.get('third_type_name') or third_type_code
                                )
                                tipos_tercero_creados += 1
                        
                        # Obtener TipoRegimen (si existe código, sino NULL)
                        tipo_regimen = None
                        if regiment_type_code:
                            try:
                                tipo_regimen = TipoRegimen.objects.get(codigo=regiment_type_code)
                            except TipoRegimen.DoesNotExist:
                                tipo_regimen = TipoRegimen.objects.create(
                                    codigo=regiment_type_code,
                                    nombre=row.get('regiment_type_name') or regiment_type_code
                                )
                                tipos_regimen_creados += 1
                        
                        # Crear o actualizar VigenciaTributaria
                        # La clave única es: impuesto + digitos_nit + tipo_tercero + tipo_regimen + fecha_limite
                        vigencia, created = VigenciaTributaria.objects.update_or_create(
                            impuesto=impuesto,
                            digitos_nit=digits,
                            tipo_tercero=tipo_tercero,  # NULL si no hay código
                            tipo_regimen=tipo_regimen,  # NULL si no hay código
                            fecha_limite=date,
                            defaults={'descripcion': description}
                        )
                        
                        if created:
                            vigencias_creadas += 1
                        else:
                            vigencias_actualizadas += 1
                        
                        if i % 100 == 0:
                            self.stdout.write(f"   Procesadas {i}/{len(expirations_data)} vigencias...")
                            
                    except Exception as e:
                        logger.error(f"Error procesando vigencia {i}: {e}", exc_info=True)
                        errores += 1
                        self.stdout.write(self.style.ERROR(f"   ❌ Error en vigencia {i}: {e}"))
                
                self.stdout.write("")
            
            # Resumen final
            self.stdout.write("=" * 70)
            self.stdout.write("Resumen de migración:")
            self.stdout.write(f"   ✅ Tipos de tercero creados: {tipos_tercero_creados}")
            self.stdout.write(f"   ✅ Tipos de régimen creados: {tipos_regimen_creados}")
            self.stdout.write(f"   ✅ Impuestos creados: {impuestos_creados}")
            self.stdout.write(f"   ✅ Vigencias creadas: {vigencias_creadas}")
            self.stdout.write(f"   🔄 Vigencias actualizadas: {vigencias_actualizadas}")
            if errores > 0:
                self.stdout.write(self.style.ERROR(f"   ❌ Errores: {errores}"))
            self.stdout.write("=" * 70)
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("✅ Migración completada exitosamente"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante la migración: {e}'))
            import traceback
            traceback.print_exc()
        finally:
            bce_conn.close()

