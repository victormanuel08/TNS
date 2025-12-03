"""
Comando para migrar Entities y PasswordsEntities desde BCE a MANU.
Lee los datos de BCE y los migra usando el NIT del Third.
"""
import os
import sys
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.sistema_analitico.models import Entidad, ContrasenaEntidad, EmpresaServidor


def normalize_nit(nit):
    """Normaliza NIT eliminando puntos, guiones y espacios"""
    if not nit:
        return ''
    return ''.join(c for c in str(nit) if c.isdigit())


class Command(BaseCommand):
    help = "Migra Entities y PasswordsEntities desde BCE a MANU usando NIT"

    def add_arguments(self, parser):
        parser.add_argument(
            '--bce-settings',
            type=str,
            help='Ruta al settings.py de BCE (opcional, intentará detectarlo)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin guardar (solo mostrar qué se haría)'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        # Calcular ruta de BCE
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Subir desde commands/ -> management/ -> sistema_analitico/ -> apps/ -> manu/ -> TNSFULL/
        tnsfull_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))))
        bce_backend_path = os.path.join(tnsfull_root, 'bce', 'backend')
        
        if not os.path.exists(bce_backend_path):
            self.stdout.write(self.style.ERROR(f'❌ Ruta BCE no encontrada: {bce_backend_path}'))
            return
        
        self.stdout.write(f'   📁 Ruta BCE: {bce_backend_path}')
        
        # Usar subproceso para ejecutar script de exportación con configuración de BCE
        import subprocess
        import json as json_lib
        
        script_path = os.path.join(current_dir, '_exportar_bce_entidades.py')
        bce_manage_py = os.path.join(bce_backend_path, 'manage.py')
        
        if not os.path.exists(bce_manage_py):
            self.stdout.write(self.style.ERROR(f'❌ manage.py de BCE no encontrado: {bce_manage_py}'))
            return
        
        # Detectar Python del entorno virtual de BCE
        bce_python = sys.executable  # Por defecto usar el actual
        bce_env_python = None
        
        # Buscar entorno virtual de BCE
        if sys.platform == 'win32':
            bce_env_python = os.path.join(bce_backend_path, 'env', 'Scripts', 'python.exe')
        else:
            bce_env_python = os.path.join(bce_backend_path, 'env', 'bin', 'python')
        
        if os.path.exists(bce_env_python):
            bce_python = bce_env_python
            self.stdout.write(f'   🐍 Usando Python de BCE: {bce_python}')
        else:
            self.stdout.write(self.style.WARNING(f'   ⚠️  No se encontró entorno virtual de BCE, usando Python actual'))
        
        try:
            # Crear comando para ejecutar en shell de Django
            shell_command = f'''
import json
from core.models import Entities, PasswordsEntities, Third

def exportar_entidades():
    entities = Entities.objects.all()
    data = []
    for entity in entities:
        data.append({{
            'id': entity.id,
            'name': entity.name,
            'sigla': getattr(entity, 'sigla', '') if hasattr(entity, 'sigla') else '',
        }})
    return data

def exportar_passwords_entities():
    passwords = PasswordsEntities.objects.select_related('entity', 'third').all()
    data = []
    for pwd in passwords:
        entity_data = {{
            'id': pwd.entity.id,
            'name': pwd.entity.name,
            'sigla': getattr(pwd.entity, 'sigla', '') if hasattr(pwd.entity, 'sigla') else '',
        }} if pwd.entity else None
        
        third_data = {{
            'id': pwd.third.id,
            'id_number': pwd.third.id_number,
        }} if pwd.third else None
        
        data.append({{
            'id': pwd.id,
            'user': pwd.user,
            'password': pwd.password,
            'description': getattr(pwd, 'description', '') if hasattr(pwd, 'description') else '',
            'entity': entity_data,
            'third': third_data,
        }})
    return data

output = {{
    'entities': exportar_entidades(),
    'passwords_entities': exportar_passwords_entities(),
}}
print(json.dumps(output, ensure_ascii=False, indent=2))
'''
            
            # Preparar entorno para BCE
            env = os.environ.copy()
            # Agregar el directorio de BCE al PYTHONPATH
            pythonpath = env.get('PYTHONPATH', '')
            if pythonpath:
                env['PYTHONPATH'] = f'{bce_backend_path}{os.pathsep}{pythonpath}'
            else:
                env['PYTHONPATH'] = bce_backend_path
            
            result = subprocess.run(
                [bce_python, bce_manage_py, 'shell', '--command', shell_command],
                cwd=bce_backend_path,
                capture_output=True,
                text=True,
                timeout=60,
                env=env
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                # Extraer el mensaje de error más relevante
                error_lines = error_msg.split('\n')
                module_error = None
                for line in reversed(error_lines):
                    if 'ModuleNotFoundError' in line or 'No module named' in line:
                        module_error = line.strip()
                        break
                
                if module_error:
                    self.stdout.write(self.style.ERROR('❌ Error: Faltan dependencias en el entorno de BCE'))
                    self.stdout.write(self.style.WARNING('💡 Asegúrate de tener activado el entorno virtual de BCE y todas las dependencias instaladas'))
                    self.stdout.write(self.style.WARNING(f'   Error específico: {module_error}'))
                    # Mostrar las últimas líneas del error para más contexto
                    if len(error_lines) > 5:
                        self.stdout.write(self.style.WARNING('   Últimas líneas del error:'))
                        for line in error_lines[-5:]:
                            if line.strip():
                                self.stdout.write(f'      {line.strip()[:100]}')
                else:
                    # Mostrar error completo si no es de módulos
                    self.stdout.write(self.style.ERROR(f'❌ Error ejecutando script de exportación:'))
                    # Mostrar solo las últimas 10 líneas del error
                    for line in error_lines[-10:]:
                        if line.strip():
                            self.stdout.write(f'   {line.strip()[:150]}')
                return
            
            # Parsear JSON exportado
            bce_data = json_lib.loads(result.stdout)
            
            self.stdout.write(self.style.SUCCESS(f'✅ Datos de BCE exportados: {len(bce_data.get("entities", []))} entidades, {len(bce_data.get("passwords_entities", []))} contraseñas'))
            
            self.stdout.write(self.style.SUCCESS('✅ Modelos de BCE importados correctamente'))
            
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'❌ Error importando modelos de BCE: {e}'))
            self.stdout.write(self.style.WARNING(
                '💡 Asegúrate de que BCE esté en la ruta correcta o proporciona --bce-settings'
            ))
            return
        
        # Migrar Entities
        self.stdout.write(self.style.SUCCESS('\n📋 Migrando Entities...'))
        entidades_creadas = 0
        entidades_existentes = 0
        
        try:
            entities_bce = Entities.objects.all()
            self.stdout.write(f'   Encontradas {entities_bce.count()} entidades en BCE')
            
            for entity_bce in entities_bce:
                entidad, created = Entidad.objects.get_or_create(
                    nombre=entity_bce.name,
                    defaults={
                        'sigla': entity_bce.sigla or None
                    }
                )
                if created:
                    entidades_creadas += 1
                    if not dry_run:
                        self.stdout.write(f'   ✅ Creada: {entidad.nombre}')
                else:
                    entidades_existentes += 1
                    # Actualizar sigla si cambió
                    if entidad.sigla != entity_bce.sigla:
                        if not dry_run:
                            entidad.sigla = entity_bce.sigla or None
                            entidad.save()
                            self.stdout.write(f'   🔄 Actualizada: {entidad.nombre}')
            
            self.stdout.write(self.style.SUCCESS(
                f'   ✅ Entities: {entidades_creadas} creadas, {entidades_existentes} ya existían'
            ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error migrando Entities: {e}'))
            return
        
        # Migrar PasswordsEntities
        self.stdout.write(self.style.SUCCESS('\n📋 Migrando PasswordsEntities...'))
        contrasenas_creadas = 0
        contrasenas_existentes = 0
        contrasenas_sin_nit = 0
        contrasenas_sin_empresa = 0
        
        try:
            passwords_bce = PasswordsEntities.objects.select_related('entity', 'third').all()
            self.stdout.write(f'   Encontradas {passwords_bce.count()} contraseñas en BCE')
            
            with transaction.atomic():
                for pwd_bce in passwords_bce:
                    # Obtener NIT del Third
                    nit_normalizado = None
                    empresa_servidor = None
                    
                    if pwd_bce.third:
                        # Obtener NIT del Third (id_number)
                        nit_bce = str(pwd_bce.third.id_number)
                        nit_normalizado = normalize_nit(nit_bce)
                        
                        if nit_normalizado:
                            # Buscar empresa en MANU por NIT
                            empresas = EmpresaServidor.objects.filter(nit_normalizado=nit_normalizado)
                            if empresas.exists():
                                # Usar la primera empresa encontrada
                                empresa_servidor = empresas.first()
                            else:
                                contrasenas_sin_empresa += 1
                                if not dry_run:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f'   ⚠️  NIT {nit_normalizado} no tiene empresa en MANU: '
                                            f'{pwd_bce.entity.name} - {pwd_bce.user}'
                                        )
                                    )
                        else:
                            contrasenas_sin_nit += 1
                    else:
                        contrasenas_sin_nit += 1
                        if not dry_run:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'   ⚠️  Sin Third asociado: {pwd_bce.entity.name} - {pwd_bce.user}'
                                )
                            )
                    
                    # Si no hay NIT, saltar este registro
                    if not nit_normalizado:
                        continue
                    
                    # Obtener o crear Entidad
                    try:
                        entidad = Entidad.objects.get(nombre=pwd_bce.entity.name)
                    except Entidad.DoesNotExist:
                        # Crear entidad si no existe
                        entidad = Entidad.objects.create(
                            nombre=pwd_bce.entity.name,
                            sigla=pwd_bce.entity.sigla or None
                        )
                        if not dry_run:
                            self.stdout.write(f'   📝 Entidad creada: {entidad.nombre}')
                    
                    # Crear o actualizar ContrasenaEntidad
                    contrasena, created = ContrasenaEntidad.objects.get_or_create(
                        entidad=entidad,
                        nit_normalizado=nit_normalizado,
                        usuario=pwd_bce.user,
                        defaults={
                            'empresa_servidor': empresa_servidor,
                            'descripcion': pwd_bce.description or None,
                            'contrasena': pwd_bce.password
                        }
                    )
                    
                    if created:
                        contrasenas_creadas += 1
                        if not dry_run:
                            self.stdout.write(
                                f'   ✅ Creada: {entidad.nombre} - {pwd_bce.user} '
                                f'(NIT: {nit_normalizado})'
                            )
                    else:
                        contrasenas_existentes += 1
                        # Actualizar si cambió algo
                        if not dry_run:
                            updated = False
                            if contrasena.descripcion != (pwd_bce.description or None):
                                contrasena.descripcion = pwd_bce.description or None
                                updated = True
                            if contrasena.contrasena != pwd_bce.password:
                                contrasena.contrasena = pwd_bce.password
                                updated = True
                            if contrasena.empresa_servidor != empresa_servidor:
                                contrasena.empresa_servidor = empresa_servidor
                                updated = True
                            if updated:
                                contrasena.save()
                                self.stdout.write(
                                    f'   🔄 Actualizada: {entidad.nombre} - {pwd_bce.user}'
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
                    f'   - ⚠️  {contrasenas_sin_empresa} contraseñas sin empresa en MANU'
                ))
            
        except subprocess.TimeoutExpired:
            self.stdout.write(self.style.ERROR('❌ Timeout ejecutando script de exportación'))
            return
        except json_lib.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'❌ Error parseando JSON exportado: {e}'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error en migración: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
            return
            self.stdout.write(f'   - Contraseñas creadas: {contrasenas_creadas}')
            self.stdout.write(f'   - Contraseñas existentes: {contrasenas_existentes}')
            if contrasenas_sin_nit > 0:
                self.stdout.write(self.style.WARNING(
                    f'   - Sin NIT (omitidas): {contrasenas_sin_nit}'
                ))
            if contrasenas_sin_empresa > 0:
                self.stdout.write(self.style.WARNING(
                    f'   - Sin empresa en MANU: {contrasenas_sin_empresa}'
                ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error migrando PasswordsEntities: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
            return

