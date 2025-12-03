"""
Comando para migrar datos directamente desde la base de datos de BCE a MANU.
Lee directamente usando conexión directa a PostgreSQL.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from apps.sistema_analitico.models import (
    Entidad, ContrasenaEntidad, EmpresaServidor,
    TipoTercero, TipoRegimen, Impuesto, VigenciaTributaria,
    normalize_nit_and_extract_dv
)
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

# Credenciales hardcodeadas de BCE
BCE_DB_CONFIG = {
    'dbname': 'bcemanagement',
    'user': 'postgres',
    'password': 'Bce2024.sas',
    'host': '127.0.0.1',
    'port': '5432'
}


class Command(BaseCommand):
    help = "Migra Entities, PasswordsEntities y Calendario Tributario directamente desde la BD de BCE"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin guardar (solo mostrar qué se haría)'
        )
        parser.add_argument(
            '--solo-entidades',
            action='store_true',
            help='Migrar solo Entities y PasswordsEntities (no calendario)'
        )
        parser.add_argument(
            '--solo-calendario',
            action='store_true',
            help='Migrar solo Calendario Tributario (no entidades)'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        solo_entidades = options.get('solo_entidades', False)
        solo_calendario = options.get('solo_calendario', False)

        # Conectar a BCE
        try:
            bce_conn = psycopg2.connect(**BCE_DB_CONFIG)
            self.stdout.write(self.style.SUCCESS('✅ Conexión a base de datos BCE establecida'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error conectando a BCE: {e}'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN - No se guardarán cambios'))

        try:
            # Migrar Entities y PasswordsEntities
            if not solo_calendario:
                self.migrar_entidades_y_passwords(bce_conn, dry_run)

            # Migrar Calendario Tributario
            if not solo_entidades:
                self.migrar_calendario_tributario(bce_conn, dry_run)

            self.stdout.write(self.style.SUCCESS('\n✅ Migración completada!'))
        finally:
            bce_conn.close()

    def migrar_entidades_y_passwords(self, bce_conn, dry_run):
        """Migra Entities y PasswordsEntities desde BCE"""
        self.stdout.write('\n📋 Migrando Entities y PasswordsEntities...')

        with bce_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Obtener Entities
            cursor.execute("""
                SELECT id, name, sigla
                FROM core_entities
                ORDER BY name
            """)
            entities_data = cursor.fetchall()

            self.stdout.write(f'   📊 {len(entities_data)} Entities encontradas')

            # Obtener PasswordsEntities
            cursor.execute("""
                SELECT 
                    pe.id,
                    pe.entity_id,
                    e.name as entity_name,
                    pe.third_id,
                    t.id_number as third_id_number,
                    pe.user,
                    pe.password,
                    pe.description
                FROM core_passwordsentities pe
                LEFT JOIN core_entities e ON pe.entity_id = e.id
                LEFT JOIN core_third t ON pe.third_id = t.id
                ORDER BY e.name, pe.user
            """)
            passwords_data = cursor.fetchall()

            self.stdout.write(f'   📊 {len(passwords_data)} PasswordsEntities encontradas')

        if dry_run:
            self.stdout.write(self.style.WARNING('   ⚠️  DRY RUN - No se guardarán cambios'))
            return

        entidades_creadas = 0
        entidades_existentes = 0
        contrasenas_creadas = 0
        contrasenas_existentes = 0
        contrasenas_sin_empresa = {}

        with transaction.atomic():
            # Migrar Entities
            for row in entities_data:
                entity_id = row['id']
                name = row['name']
                sigla = row.get('sigla')
                entidad, created = Entidad.objects.get_or_create(
                    nombre=name,
                    defaults={'sigla': sigla if sigla else None}
                )
                if created:
                    entidades_creadas += 1
                else:
                    entidades_existentes += 1
                    if entidad.sigla != (sigla if sigla else None):
                        entidad.sigla = sigla if sigla else None
                        entidad.save(update_fields=['sigla'])

            self.stdout.write(f'   ✅ Entities: {entidades_creadas} creadas, {entidades_existentes} ya existían')

            # Migrar PasswordsEntities
            for row in passwords_data:
                entity_id = row.get('entity_id')
                entity_name = row.get('entity_name')
                third_id = row.get('third_id')
                third_id_number = row.get('third_id_number')
                user = row.get('user')
                password = row.get('password')
                description = row.get('description')

                if not entity_name:
                    continue

                # Obtener o crear Entidad
                try:
                    entidad = Entidad.objects.get(nombre=entity_name)
                except Entidad.DoesNotExist:
                    entidad = Entidad.objects.create(nombre=entity_name, sigla=None)

                # Normalizar NIT
                nit_normalizado = None
                empresa_servidor = None

                if third_id_number:
                    nit_normalizado, _, _ = normalize_nit_and_extract_dv(str(third_id_number))

                    if nit_normalizado:
                        # Buscar empresa en MANU
                        empresas = EmpresaServidor.objects.filter(nit_normalizado=nit_normalizado)
                        if empresas.exists():
                            empresa_servidor = empresas.first()
                        else:
                            # Registrar para asociación posterior
                            if nit_normalizado not in contrasenas_sin_empresa:
                                contrasenas_sin_empresa[nit_normalizado] = []
                            contrasenas_sin_empresa[nit_normalizado].append({
                                'entity_name': entity_name,
                                'user': user
                            })

                if not nit_normalizado:
                    continue

                # Crear o actualizar ContrasenaEntidad
                contrasena, created = ContrasenaEntidad.objects.get_or_create(
                    entidad=entidad,
                    nit_normalizado=nit_normalizado,
                    usuario=user,
                    defaults={
                        'empresa_servidor': empresa_servidor,
                        'descripcion': description if description else None,
                        'contrasena': password
                    }
                )

                if created:
                    contrasenas_creadas += 1
                else:
                    contrasenas_existentes += 1
                    # Actualizar si cambió algo
                    updated = False
                    if contrasena.descripcion != (description if description else None):
                        contrasena.descripcion = description if description else None
                        updated = True
                    if contrasena.contrasena != password:
                        contrasena.contrasena = password
                        updated = True
                    if contrasena.empresa_servidor != empresa_servidor:
                        contrasena.empresa_servidor = empresa_servidor
                        updated = True
                    if updated:
                        contrasena.save(update_fields=['descripcion', 'contrasena', 'empresa_servidor', 'fecha_actualizacion'])

        self.stdout.write(f'   ✅ Contraseñas: {contrasenas_creadas} creadas, {contrasenas_existentes} ya existían')

        if contrasenas_sin_empresa:
            self.stdout.write(self.style.WARNING(
                f'   ⚠️  {sum(len(v) for v in contrasenas_sin_empresa.values())} contraseñas guardadas sin empresa asociada'
            ))
            self.stdout.write('   📋 NITs sin empresa (se asociarán automáticamente cuando se descubra la empresa):')
            for nit, pwds in list(contrasenas_sin_empresa.items())[:10]:  # Mostrar solo los primeros 10
                self.stdout.write(f'      - NIT {nit}: {len(pwds)} contraseña(s)')
            if len(contrasenas_sin_empresa) > 10:
                self.stdout.write(f'      ... y {len(contrasenas_sin_empresa) - 10} más')

    def migrar_calendario_tributario(self, bce_conn, dry_run):
        """Migra Calendario Tributario desde BCE"""
        self.stdout.write('\n📅 Migrando Calendario Tributario...')

        with bce_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Obtener Third_Types
            cursor.execute("SELECT code, name FROM core_third_types")
            third_types_data = cursor.fetchall()

            # Obtener Regiments_Types
            cursor.execute("SELECT code, name, description FROM core_regiments_types")
            regiments_data = cursor.fetchall()

            # Obtener Tax
            cursor.execute("SELECT code, name, description FROM core_tax")
            taxes_data = cursor.fetchall()

            # Obtener Expirations (calendario)
            # Nota: Expirations tiene relación ManyToMany con Tax, necesitamos usar la tabla intermedia
            cursor.execute("""
                SELECT DISTINCT
                    e.id,
                    t.code as tax_code,
                    t.name as tax_name,
                    t.description as tax_description,
                    e.third_types_id,
                    tt.code as third_type_code,
                    e.regiments_types_id,
                    rt.code as regiment_type_code,
                    e.digits,
                    e.date,
                    e.description
                FROM core_expirations e
                INNER JOIN core_tax_expirations cte ON e.id = cte.expirations_id
                INNER JOIN core_tax t ON cte.tax_id = t.id
                LEFT JOIN core_third_types tt ON e.third_types_id = tt.id
                LEFT JOIN core_regiments_types rt ON e.regiments_types_id = rt.id
                ORDER BY t.code, e.date
            """)
            expirations_data = cursor.fetchall()

            self.stdout.write(f'   📊 {len(third_types_data)} Third_Types encontrados')
            self.stdout.write(f'   📊 {len(regiments_data)} Regiments_Types encontrados')
            self.stdout.write(f'   📊 {len(taxes_data)} Tax encontrados')
            self.stdout.write(f'   📊 {len(expirations_data)} Expirations encontradas')

        if dry_run:
            self.stdout.write(self.style.WARNING('   ⚠️  DRY RUN - No se guardarán cambios'))
            return

        tipos_tercero_creados = 0
        tipos_regimen_creados = 0
        impuestos_creados = 0
        vigencias_creadas = 0
        vigencias_actualizadas = 0

        with transaction.atomic():
            # Migrar Third_Types
            for row in third_types_data:
                code = row['code']
                name = row['name']
                tipo, created = TipoTercero.objects.get_or_create(
                    codigo=code,
                    defaults={'nombre': name}
                )
                if created:
                    tipos_tercero_creados += 1

            # Migrar Regiments_Types
            for row in regiments_data:
                code = row['code']
                name = row['name']
                description = row.get('description')
                tipo, created = TipoRegimen.objects.get_or_create(
                    codigo=code,
                    defaults={
                        'nombre': name,
                        'descripcion': description if description else ''
                    }
                )
                if created:
                    tipos_regimen_creados += 1

            # Migrar Tax
            for row in taxes_data:
                code = row['code']
                name = row['name']
                description = row.get('description')
                impuesto, created = Impuesto.objects.get_or_create(
                    codigo=code,
                    defaults={
                        'nombre': name,
                        'descripcion': description if description else ''
                    }
                )
                if created:
                    impuestos_creados += 1

            # Migrar Expirations (Vigencias Tributarias)
            for row in expirations_data:
                tax_code = row.get('tax_code')
                tax_name = row.get('tax_name')
                tax_description = row.get('tax_description')
                third_type_code = row.get('third_type_code')
                regiment_type_code = row.get('regiment_type_code')
                digits = row.get('digits')
                date = row.get('date')
                description = row.get('description')

                # Obtener Impuesto
                try:
                    impuesto = Impuesto.objects.get(codigo=tax_code)
                except Impuesto.DoesNotExist:
                    impuesto = Impuesto.objects.create(
                        codigo=tax_code,
                        nombre=tax_name or tax_code,
                        descripcion=tax_description or ''
                    )

                # Obtener TipoTercero (si existe)
                tipo_tercero = None
                if third_type_code:
                    tipo_tercero, _ = TipoTercero.objects.get_or_create(
                        codigo=third_type_code,
                        defaults={'nombre': third_type_code}
                    )

                # Obtener TipoRegimen (si existe)
                tipo_regimen = None
                if regiment_type_code:
                    tipo_regimen, _ = TipoRegimen.objects.get_or_create(
                        codigo=regiment_type_code,
                        defaults={'nombre': regiment_type_code}
                    )

                # Crear o actualizar VigenciaTributaria
                vigencia, created = VigenciaTributaria.objects.update_or_create(
                    impuesto=impuesto,
                    digitos_nit=digits or '',
                    tipo_tercero=tipo_tercero,
                    tipo_regimen=tipo_regimen,
                    fecha_limite=date,
                    defaults={'descripcion': description or 'Sin definir'}
                )

                if created:
                    vigencias_creadas += 1
                else:
                    vigencias_actualizadas += 1

        self.stdout.write(f'   ✅ Tipos Tercero: {tipos_tercero_creados} creados')
        self.stdout.write(f'   ✅ Tipos Régimen: {tipos_regimen_creados} creados')
        self.stdout.write(f'   ✅ Impuestos: {impuestos_creados} creados')
        self.stdout.write(f'   ✅ Vigencias: {vigencias_creadas} creadas, {vigencias_actualizadas} actualizadas')

