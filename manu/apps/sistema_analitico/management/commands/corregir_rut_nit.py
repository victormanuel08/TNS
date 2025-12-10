"""
Comando para corregir el NIT de un RUT específico.
Útil cuando el extractor leyó mal el PDF o el NIT está mal normalizado.
"""
from django.core.management.base import BaseCommand
from apps.sistema_analitico.models import RUT, normalize_nit_and_extract_dv
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '🔧 Corrige el NIT y nit_normalizado de un RUT específico'

    def add_arguments(self, parser):
        parser.add_argument(
            '--nit-actual',
            type=str,
            required=True,
            help='NIT actual (incorrecto) del RUT en la BD (ej: 10050386382)',
        )
        parser.add_argument(
            '--nit-correcto',
            type=str,
            required=True,
            help='NIT correcto con formato (ej: 1005038638-2)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se cambiaría SIN hacer cambios reales',
        )

    def handle(self, *args, **options):
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.WARNING('🔧 CORRECCIÓN DE NIT EN RUT'))
        self.stdout.write('=' * 60)
        self.stdout.write('')

        nit_actual = options['nit_actual']
        nit_correcto = options['nit_correcto']
        dry_run = options['dry_run']

        self.stdout.write(f"📋 CONFIGURACIÓN:")
        self.stdout.write(f"   • NIT actual (incorrecto): {nit_actual}")
        self.stdout.write(f"   • NIT correcto: {nit_correcto}")
        self.stdout.write(f"   • Dry-run: {dry_run}")
        self.stdout.write('-' * 60)
        self.stdout.write('')

        # Normalizar NIT actual para buscar
        nit_actual_norm, _, _ = normalize_nit_and_extract_dv(nit_actual)
        
        # Buscar RUT con NIT actual
        try:
            rut = RUT.objects.get(nit_normalizado=nit_actual_norm)
        except RUT.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ No se encontró RUT con nit_normalizado: {nit_actual_norm}"))
            self.stdout.write('')
            return
        except RUT.MultipleObjectsReturned:
            self.stdout.write(self.style.ERROR(f"❌ Se encontraron múltiples RUTs con nit_normalizado: {nit_actual_norm}"))
            self.stdout.write('   Por favor, especifica un NIT más específico o corrige manualmente.')
            self.stdout.write('')
            return

        self.stdout.write(f"✅ RUT encontrado:")
        self.stdout.write(f"   • ID: {rut.id}")
        self.stdout.write(f"   • Razón Social: {rut.razon_social}")
        self.stdout.write(f"   • NIT actual: {rut.nit}")
        self.stdout.write(f"   • NIT normalizado actual: {rut.nit_normalizado}")
        self.stdout.write(f"   • DV actual: {rut.dv}")
        self.stdout.write('')

        # Normalizar NIT correcto
        nit_correcto_norm, dv_correcto, nit_original = normalize_nit_and_extract_dv(nit_correcto)
        
        self.stdout.write(f"📝 CAMBIOS PROPUESTOS:")
        self.stdout.write(f"   • NIT: {rut.nit} → {nit_correcto}")
        self.stdout.write(f"   • NIT normalizado: {rut.nit_normalizado} → {nit_correcto_norm}")
        self.stdout.write(f"   • DV: {rut.dv} → {dv_correcto}")
        self.stdout.write('')

        # Verificar si ya existe un RUT con el NIT correcto
        rut_existente = RUT.objects.filter(nit_normalizado=nit_correcto_norm).exclude(id=rut.id).first()
        if rut_existente:
            self.stdout.write(self.style.ERROR(f"⚠️  ADVERTENCIA: Ya existe otro RUT con nit_normalizado: {nit_correcto_norm}"))
            self.stdout.write(f"   • ID: {rut_existente.id}")
            self.stdout.write(f"   • Razón Social: {rut_existente.razon_social}")
            self.stdout.write('')
            self.stdout.write(self.style.ERROR("   No se puede corregir porque causaría un duplicado."))
            self.stdout.write('   Por favor, elimina o fusiona el RUT duplicado primero.')
            self.stdout.write('')
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 [DRY-RUN] No se realizarán cambios reales."))
            self.stdout.write('')
        else:
            # Realizar corrección
            try:
                rut.nit = nit_correcto
                rut.dv = dv_correcto
                # El nit_normalizado se actualizará automáticamente en save()
                rut.save()
                
                self.stdout.write(self.style.SUCCESS("✅ RUT corregido exitosamente"))
                self.stdout.write('')
                self.stdout.write(f"📋 VALORES FINALES:")
                self.stdout.write(f"   • NIT: {rut.nit}")
                self.stdout.write(f"   • NIT normalizado: {rut.nit_normalizado}")
                self.stdout.write(f"   • DV: {rut.dv}")
                self.stdout.write('')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error al corregir RUT: {e}"))
                logger.error(f"Error al corregir RUT: {e}", exc_info=True)
                self.stdout.write('')
                return

        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS('✅ Proceso completado'))
        self.stdout.write('=' * 60)
        self.stdout.write('')

