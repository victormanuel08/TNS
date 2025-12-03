"""
Comando para importar Entities y PasswordsEntities desde Excel exportado de BCE
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.sistema_analitico.models import Entidad, ContrasenaEntidad, EmpresaServidor
import os


def normalize_nit(nit):
    """Normaliza NIT eliminando puntos, guiones y espacios"""
    if not nit:
        return ''
    return ''.join(c for c in str(nit) if c.isdigit())


class Command(BaseCommand):
    help = "Importa Entities y PasswordsEntities desde Excel exportado de BCE"

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_file',
            type=str,
            help='Ruta al archivo Excel exportado de BCE'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin guardar (solo mostrar qué se haría)'
        )

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        dry_run = options.get('dry_run', False)
        
        # Agregar extensión .xlsx si no la tiene
        if not excel_file.lower().endswith('.xlsx'):
            excel_file = excel_file + '.xlsx'
        
        # Calcular ruta base correcta (TNSFULL)
        # El comando está en: manu/apps/sistema_analitico/management/commands/
        # Necesitamos subir hasta TNSFULL
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        tnsfull_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file_dir)))))
        
        # Intentar diferentes rutas si el archivo no se encuentra
        posibles_rutas = []
        
        # 1. Ruta exacta proporcionada
        posibles_rutas.append(excel_file)
        
        # 2. Ruta absoluta si es relativa
        if not os.path.isabs(excel_file):
            posibles_rutas.append(os.path.abspath(excel_file))
            # Ruta relativa desde el directorio actual de trabajo
            posibles_rutas.append(os.path.join(os.getcwd(), excel_file))
        
        # 3. Desde exports de BCE (ruta relativa desde TNSFULL)
        bce_exports_path = os.path.join(tnsfull_root, 'bce', 'backend', 'exports')
        posibles_rutas.append(os.path.join(bce_exports_path, excel_file))
        
        # 4. Si solo es el nombre del archivo, buscar en exports de BCE
        if os.path.sep not in excel_file or excel_file.startswith('..'):
            posibles_rutas.append(os.path.join(bce_exports_path, os.path.basename(excel_file)))
        
        # 5. Intentar con la ruta relativa desde manu
        if excel_file.startswith('../'):
            posibles_rutas.append(os.path.join(tnsfull_root, excel_file.lstrip('../')))
        
        archivo_encontrado = None
        for ruta in posibles_rutas:
            ruta_normalizada = os.path.normpath(ruta)
            if os.path.exists(ruta_normalizada):
                archivo_encontrado = ruta_normalizada
                break
        
        if not archivo_encontrado:
            self.stdout.write(self.style.ERROR(f'❌ Archivo no encontrado: {options["excel_file"]}'))
            self.stdout.write(self.style.WARNING('💡 Rutas intentadas:'))
            for ruta in posibles_rutas:
                ruta_norm = os.path.normpath(ruta)
                existe = '✅' if os.path.exists(ruta_norm) else '❌'
                self.stdout.write(f'   {existe} {ruta_norm}')
            self.stdout.write(self.style.WARNING(f'\n💡 Directorio de exports de BCE: {bce_exports_path}'))
            self.stdout.write(self.style.WARNING('💡 Sugerencias:'))
            self.stdout.write('   1. Usa la ruta completa del archivo')
            self.stdout.write('   2. O usa: ../bce/backend/exports/nombre_archivo.xlsx')
            self.stdout.write('   3. O solo el nombre del archivo si está en exports de BCE')
            return
        
        excel_file = archivo_encontrado
        self.stdout.write(self.style.SUCCESS(f'✅ Archivo encontrado: {excel_file}'))
        
        try:
            import pandas as pd
        except ImportError:
            self.stdout.write(self.style.ERROR('❌ pandas no está instalado. Instala con: pip install pandas openpyxl'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'📂 Leyendo archivo: {excel_file}'))
        
        try:
            # Leer hojas del Excel
            df_entities = pd.read_excel(excel_file, sheet_name='Entities')
            df_passwords = pd.read_excel(excel_file, sheet_name='PasswordsEntities')
            
            self.stdout.write(f'   ✅ Entities: {len(df_entities)} registros')
            self.stdout.write(f'   ✅ PasswordsEntities: {len(df_passwords)} registros')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error leyendo Excel: {e}'))
            return
        
        # Migrar Entities
        self.stdout.write(self.style.SUCCESS('\n📋 Migrando Entities...'))
        entidades_creadas = 0
        entidades_existentes = 0
        
        try:
            for _, row in df_entities.iterrows():
                entidad, created = Entidad.objects.get_or_create(
                    nombre=row['name'],
                    defaults={
                        'sigla': row.get('sigla') or None
                    }
                )
                if created:
                    entidades_creadas += 1
                    if not dry_run:
                        self.stdout.write(f'   ✅ Creada: {entidad.nombre}')
                else:
                    entidades_existentes += 1
                    # Actualizar sigla si cambió
                    if entidad.sigla != (row.get('sigla') or None):
                        if not dry_run:
                            entidad.sigla = row.get('sigla') or None
                            entidad.save()
                            self.stdout.write(f'   🔄 Actualizada: {entidad.nombre}')
            
            self.stdout.write(self.style.SUCCESS(
                f'   ✅ Entities: {entidades_creadas} creadas, {entidades_existentes} ya existían'
            ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error migrando Entities: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
            return
        
        # Migrar PasswordsEntities
        self.stdout.write(self.style.SUCCESS('\n📋 Migrando PasswordsEntities...'))
        contrasenas_creadas = 0
        contrasenas_existentes = 0
        contrasenas_sin_nit = 0
        contrasenas_sin_empresa = 0
        nits_sin_empresa = {}  # Para rastrear qué NITs no tienen empresa
        
        try:
            with transaction.atomic():
                for _, row in df_passwords.iterrows():
                    # Obtener NIT del Third
                    nit_normalizado = None
                    empresa_servidor = None
                    
                    third_id_number = row.get('third_id_number')
                    if third_id_number and pd.notna(third_id_number):
                        nit_normalizado = normalize_nit(str(third_id_number))
                        
                        if nit_normalizado:
                            # Buscar empresa en MANU por NIT normalizado
                            empresas = EmpresaServidor.objects.filter(nit_normalizado=nit_normalizado)
                            if empresas.exists():
                                empresa_servidor = empresas.first()
                            else:
                                # No crear empresa automáticamente - dejar empresa_servidor=None
                                # Se asociará automáticamente cuando se descubra la empresa en un servidor
                                contrasenas_sin_empresa += 1
                                empresa_servidor = None  # Dejar en None
                                
                                # Rastrear NITs sin empresa
                                if nit_normalizado not in nits_sin_empresa:
                                    nits_sin_empresa[nit_normalizado] = []
                                nits_sin_empresa[nit_normalizado].append({
                                    'entity': row.get("entity_name", "N/A"),
                                    'user': row.get("user", "N/A")
                                })
                                
                                if not dry_run:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f'   ⚠️  NIT {nit_normalizado} no tiene empresa (contraseña guardada sin empresa, '
                                            f'se asociará cuando se descubra la empresa en un servidor): '
                                            f'{row.get("entity_name", "N/A")} - {row.get("user", "N/A")}'
                                        )
                                    )
                        else:
                            contrasenas_sin_nit += 1
                    else:
                        contrasenas_sin_nit += 1
                        if not dry_run:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'   ⚠️  Sin NIT: {row.get("entity_name", "N/A")} - {row.get("user", "N/A")}'
                                )
                            )
                    
                    # Si no hay NIT, saltar este registro
                    if not nit_normalizado:
                        continue
                    
                    # Obtener o crear Entidad
                    entity_name = row.get('entity_name')
                    if not entity_name or pd.isna(entity_name):
                        continue
                    
                    try:
                        entidad = Entidad.objects.get(nombre=entity_name)
                    except Entidad.DoesNotExist:
                        # Crear entidad si no existe
                        entidad = Entidad.objects.create(
                            nombre=entity_name,
                            sigla=None
                        )
                        if not dry_run:
                            self.stdout.write(f'   📝 Entidad creada: {entidad.nombre}')
                    
                    # Crear o actualizar ContrasenaEntidad
                    contrasena, created = ContrasenaEntidad.objects.get_or_create(
                        entidad=entidad,
                        nit_normalizado=nit_normalizado,
                        usuario=row['user'],
                        defaults={
                            'empresa_servidor': empresa_servidor,
                            'descripcion': row.get('description') or None,
                            'contrasena': row['password']
                        }
                    )
                    
                    if created:
                        contrasenas_creadas += 1
                        if not dry_run:
                            self.stdout.write(
                                f'   ✅ Creada: {entidad.nombre} - {row["user"]} '
                                f'(NIT: {nit_normalizado})'
                            )
                    else:
                        contrasenas_existentes += 1
                        # Actualizar si cambió algo
                        if not dry_run:
                            updated = False
                            if contrasena.descripcion != (row.get('description') or None):
                                contrasena.descripcion = row.get('description') or None
                                updated = True
                            if contrasena.contrasena != row['password']:
                                contrasena.contrasena = row['password']
                                updated = True
                            if contrasena.empresa_servidor != empresa_servidor:
                                contrasena.empresa_servidor = empresa_servidor
                                updated = True
                            if updated:
                                contrasena.save()
                                self.stdout.write(
                                    f'   🔄 Actualizada: {entidad.nombre} - {row["user"]}'
                                )
                
                if dry_run:
                    self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN - No se guardaron cambios'))
                    transaction.set_rollback(True)
            
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Migración completada:'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   - Entities: {entidades_creadas} creadas, {entidades_existentes} ya existían'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   - Contraseñas: {contrasenas_creadas} creadas, {contrasenas_existentes} ya existían'
            ))
            if contrasenas_sin_nit > 0:
                self.stdout.write(self.style.WARNING(
                    f'   - ⚠️  {contrasenas_sin_nit} contraseñas sin NIT (omitidas)'
                ))
            if contrasenas_sin_empresa > 0:
                self.stdout.write(self.style.WARNING(
                    f'   - ⚠️  {contrasenas_sin_empresa} contraseñas guardadas sin empresa asociada'
                ))
                if nits_sin_empresa:
                    self.stdout.write(self.style.WARNING('\n📋 NITs sin empresa en MANU (contraseñas guardadas, se asociarán automáticamente cuando se descubra la empresa):'))
                    for nit, detalles in sorted(nits_sin_empresa.items()):
                        self.stdout.write(f'   - NIT {nit}: {len(detalles)} contraseña(s)')
                        for detalle in detalles[:3]:  # Mostrar máximo 3 ejemplos
                            self.stdout.write(f'     • {detalle["entity"]} - {detalle["user"]}')
                        if len(detalles) > 3:
                            self.stdout.write(f'     ... y {len(detalles) - 3} más')
            
            if contrasenas_sin_empresa > 0:
                self.stdout.write(self.style.SUCCESS(
                    f'\n💡 Las contraseñas sin empresa fueron guardadas con nit_normalizado. '
                    f'Se asociarán automáticamente cuando ejecutes el escaneo de empresas en un servidor '
                    f'y se descubra una empresa con ese NIT.'
                ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error migrando PasswordsEntities: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
            return

