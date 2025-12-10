"""
Comando para importar Actividades Económicas (CIUUs) desde la base de datos de BCE a MANU.

Lee directamente desde core_economicactivities en la base de datos BCE y los importa
a la tabla ActividadEconomica en MANU.

Ejecutar desde el directorio manu/:
    python manage.py importar_actividades_economicas_desde_bce

O con dry-run (solo muestra qué haría sin hacer cambios):
    python manage.py importar_actividades_economicas_desde_bce --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.sistema_analitico.models import ActividadEconomica
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import json

logger = logging.getLogger(__name__)

# Credenciales de BCE (mismas que en migrar_desde_bce_directo.py)
BCE_DB_CONFIG = {
    'dbname': 'bcemanagement',
    'user': 'postgres',
    'password': 'Bce2024.',
    'host': '198.7.113.197',  # IP pública del servidor BCE
    'port': '5432'
}


class Command(BaseCommand):
    help = 'Importa Actividades Económicas (CIUUs) desde BCE a MANU'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin guardar (solo mostrar qué se haría)'
        )
        parser.add_argument(
            '--forzar-actualizacion',
            action='store_true',
            help='Actualizar registros existentes aunque ya tengan datos'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        forzar_actualizacion = options.get('forzar_actualizacion', False)

        # Conectar a BCE
        try:
            self.stdout.write('🔗 Conectando a base de datos BCE...')
            bce_conn = psycopg2.connect(**BCE_DB_CONFIG)
            self.stdout.write(self.style.SUCCESS('✅ Conexión a BCE establecida'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error conectando a BCE: {e}'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN - No se guardarán cambios'))

        try:
            self.importar_actividades_economicas(bce_conn, dry_run, forzar_actualizacion)
            self.stdout.write(self.style.SUCCESS('\n✅ Importación completada!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error durante la importación: {e}'))
            logger.error(f"Error importando actividades económicas: {e}", exc_info=True)
        finally:
            bce_conn.close()

    def importar_actividades_economicas(self, bce_conn, dry_run, forzar_actualizacion):
        """Importa Actividades Económicas desde BCE"""
        
        self.stdout.write('\n📊 Importando Actividades Económicas (CIUUs)...')
        
        # Consultar actividades desde BCE
        with bce_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    "cseCodigo",
                    "cseDescripcion",
                    "cseTitulo",
                    "division",
                    "grupo",
                    "incluye",
                    "excluye",
                    "created_at",
                    "updated_at"
                FROM core_economicactivities
                ORDER BY "cseCodigo"
            """)
            
            actividades_bce = cursor.fetchall()
            total = len(actividades_bce)
            self.stdout.write(f'📋 Encontradas {total} actividades en BCE')
        
        if total == 0:
            self.stdout.write(self.style.WARNING('⚠️  No se encontraron actividades en BCE'))
            return
        
        # Procesar cada actividad
        creadas = 0
        actualizadas = 0
        sin_cambios = 0
        errores = 0
        
        with transaction.atomic():
            for idx, actividad_bce in enumerate(actividades_bce, 1):
                codigo = actividad_bce['cseCodigo']
                
                if not codigo:
                    self.stdout.write(self.style.WARNING(f'⚠️  Actividad {idx}/{total}: Sin código, saltando...'))
                    errores += 1
                    continue
                
                try:
                    # Normalizar código (eliminar espacios)
                    codigo = str(codigo).strip()
                    
                    # Buscar si ya existe en MANU
                    actividad_manu = ActividadEconomica.objects.filter(codigo=codigo).first()
                    
                    # Preparar datos
                    descripcion = actividad_bce.get('cseDescripcion') or actividad_bce.get('cseTitulo') or f"Actividad {codigo}"
                    titulo = actividad_bce.get('cseTitulo') or descripcion
                    division = actividad_bce.get('division') or (codigo[:2] if len(codigo) >= 2 else '')
                    grupo = actividad_bce.get('grupo') or (codigo[:3] if len(codigo) >= 3 else '')
                    
                    # Procesar incluye/excluye (pueden ser JSON o None)
                    incluye = actividad_bce.get('incluye')
                    if incluye:
                        if isinstance(incluye, str):
                            try:
                                incluye = json.loads(incluye)
                            except:
                                incluye = [incluye] if incluye else []
                        elif not isinstance(incluye, list):
                            incluye = [incluye] if incluye else []
                    else:
                        incluye = []
                    
                    excluye = actividad_bce.get('excluye')
                    if excluye:
                        if isinstance(excluye, str):
                            try:
                                excluye = json.loads(excluye)
                            except:
                                excluye = [excluye] if excluye else []
                        elif not isinstance(excluye, list):
                            excluye = [excluye] if excluye else []
                    else:
                        excluye = []
                    
                    if actividad_manu:
                        # Ya existe, verificar si actualizar
                        necesita_actualizacion = False
                        
                        if forzar_actualizacion:
                            necesita_actualizacion = True
                        else:
                            # Actualizar solo si falta información importante
                            if not actividad_manu.descripcion or actividad_manu.descripcion == f"Actividad {codigo}":
                                necesita_actualizacion = True
                            elif not actividad_manu.incluye or len(actividad_manu.incluye) == 0:
                                if incluye and len(incluye) > 0:
                                    necesita_actualizacion = True
                            elif not actividad_manu.excluye or len(actividad_manu.excluye) == 0:
                                if excluye and len(excluye) > 0:
                                    necesita_actualizacion = True
                        
                        if necesita_actualizacion:
                            if not dry_run:
                                actividad_manu.descripcion = descripcion
                                actividad_manu.titulo = titulo
                                actividad_manu.division = division
                                actividad_manu.grupo = grupo
                                actividad_manu.incluye = incluye
                                actividad_manu.excluye = excluye
                                actividad_manu.fecha_ultima_consulta_api = timezone.now()
                                actividad_manu.save()
                            
                            actualizadas += 1
                            self.stdout.write(f'   🔄 {idx}/{total}: {codigo} - {descripcion[:50]}... (ACTUALIZADO)')
                        else:
                            sin_cambios += 1
                            if idx % 100 == 0:
                                self.stdout.write(f'   ✓ {idx}/{total}: {codigo} (sin cambios)')
                    else:
                        # Crear nuevo
                        if not dry_run:
                            ActividadEconomica.objects.create(
                                codigo=codigo,
                                descripcion=descripcion,
                                titulo=titulo,
                                division=division,
                                grupo=grupo,
                                incluye=incluye,
                                excluye=excluye,
                                fecha_ultima_consulta_api=timezone.now()
                            )
                        
                        creadas += 1
                        self.stdout.write(f'   ✅ {idx}/{total}: {codigo} - {descripcion[:50]}... (CREADO)')
                
                except Exception as e:
                    errores += 1
                    self.stdout.write(self.style.ERROR(f'   ❌ {idx}/{total}: Error procesando {codigo}: {e}'))
                    logger.error(f"Error procesando actividad {codigo}: {e}", exc_info=True)
            
            if dry_run:
                # En dry-run, no hacer commit
                transaction.set_rollback(True)
        
        # Resumen
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('📊 RESUMEN DE IMPORTACIÓN')
        self.stdout.write('=' * 60)
        self.stdout.write(f'   Total en BCE: {total}')
        self.stdout.write(self.style.SUCCESS(f'   ✅ Creadas: {creadas}'))
        self.stdout.write(self.style.WARNING(f'   🔄 Actualizadas: {actualizadas}'))
        self.stdout.write(f'   ✓ Sin cambios: {sin_cambios}')
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'   ❌ Errores: {errores}'))
        self.stdout.write('=' * 60)

