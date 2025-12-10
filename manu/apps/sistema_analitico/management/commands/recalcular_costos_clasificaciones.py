"""
Comando de Django para recalcular costos de clasificaciones contables.

Este comando:
1. Busca todas las clasificaciones que tienen tokens pero costo = 0 o sin costo
2. Recalcula los costos usando los precios actuales del servicio de IA/Analytics
3. Actualiza los campos costo_total_factura y costo_total_cop en la BD

Uso:
    python manage.py recalcular_costos_clasificaciones
    python manage.py recalcular_costos_clasificaciones --dry-run  # Solo muestra sin guardar
    python manage.py recalcular_costos_clasificaciones --session-id 27  # Solo una sesión
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.sistema_analitico.models import ClasificacionContable
from apps.sistema_analitico.services.clasificador_contable_service import calcular_costo_tokens
from decimal import Decimal


class Command(BaseCommand):
    help = 'Recalcula costos de clasificaciones contables usando precios actuales del servicio de IA/Analytics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra los cálculos sin guardar en BD',
        )
        parser.add_argument(
            '--session-id',
            type=int,
            help='Recalcular solo para una sesión específica',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recalcular incluso si ya tiene costo guardado (actualizar con precios nuevos)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        session_id = options.get('session_id')
        force = options.get('force', False)
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("🔄 RECALCULANDO COSTOS DE CLASIFICACIONES"))
        self.stdout.write("=" * 80)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  MODO DRY-RUN: No se guardarán cambios en BD"))
        
        if session_id:
            self.stdout.write(f"📋 Filtrando por sesión ID: {session_id}")
        
        if force:
            self.stdout.write(self.style.WARNING("⚠️  FORZANDO recálculo incluso si ya tiene costo"))
        
        self.stdout.write("")
        
        # Construir queryset
        queryset = ClasificacionContable.objects.all()
        
        if session_id:
            queryset = queryset.filter(session_dian_id=session_id)
        
        if not force:
            # Solo clasificaciones sin costo o con costo = 0
            queryset = queryset.filter(
                costo_total_factura__lte=0
            ) | queryset.filter(
                costo_total_factura__isnull=True
            )
        
        # Filtrar solo las que tienen tokens
        queryset = queryset.filter(
            tokens_input__gt=0
        ) | queryset.filter(
            tokens_output__gt=0
        )
        
        total = queryset.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS("✅ No hay clasificaciones que necesiten recálculo"))
            return
        
        self.stdout.write(f"📊 Total clasificaciones a procesar: {total}")
        self.stdout.write("")
        
        # Estadísticas
        actualizadas = 0
        sin_tokens = 0
        sin_respuesta = 0
        errores = 0
        costo_total_usd = Decimal('0')
        costo_total_cop = Decimal('0')
        
        # Procesar en lotes para mejor rendimiento
        batch_size = 100
        for i in range(0, total, batch_size):
            batch = queryset[i:i + batch_size]
            
            for clasificacion in batch:
                try:
                    # Verificar que tenga tokens
                    if clasificacion.tokens_input == 0 and clasificacion.tokens_output == 0:
                        sin_tokens += 1
                        continue
                    
                    # Intentar extraer cache hit/miss desde respuesta_json_completa
                    cache_hit_tokens = None
                    cache_miss_tokens = None
                    
                    if clasificacion.respuesta_json_completa:
                        usage = clasificacion.respuesta_json_completa.get('usage', {})
                        cache_hit_tokens = usage.get('prompt_cache_hit_tokens')
                        cache_miss_tokens = usage.get('prompt_cache_miss_tokens')
                    else:
                        sin_respuesta += 1
                    
                    # Recalcular costo
                    costo_info = calcular_costo_tokens(
                        input_tokens=clasificacion.tokens_input,
                        output_tokens=clasificacion.tokens_output,
                        cache_hit_tokens=cache_hit_tokens,
                        cache_miss_tokens=cache_miss_tokens
                    )
                    
                    nuevo_costo_usd = Decimal(str(costo_info['costo_usd']))
                    nuevo_costo_cop = Decimal(str(costo_info['costo_cop']))
                    
                    costo_total_usd += nuevo_costo_usd
                    costo_total_cop += nuevo_costo_cop
                    
                    # Mostrar progreso
                    if (actualizadas + 1) % 10 == 0 or actualizadas == 0:
                        self.stdout.write(
                            f"  📄 Procesando {actualizadas + 1}/{total}... "
                            f"Factura: {clasificacion.factura_numero} "
                            f"Costo: ${nuevo_costo_usd:.6f} USD"
                        )
                    
                    # Guardar si no es dry-run
                    if not dry_run:
                        clasificacion.costo_total_factura = nuevo_costo_usd
                        clasificacion.costo_total_cop = nuevo_costo_cop
                        clasificacion.save(update_fields=['costo_total_factura', 'costo_total_cop'])
                    
                    actualizadas += 1
                    
                except Exception as e:
                    errores += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ❌ Error procesando clasificación ID {clasificacion.id}: {e}"
                        )
                    )
        
        # Resumen
        self.stdout.write("")
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 RESUMEN DE RECÁLCULO"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"✅ Clasificaciones actualizadas: {actualizadas}")
        self.stdout.write(f"⚠️  Sin tokens suficientes: {sin_tokens}")
        self.stdout.write(f"⚠️  Sin respuesta JSON completa: {sin_respuesta}")
        self.stdout.write(f"❌ Errores: {errores}")
        self.stdout.write("")
        self.stdout.write(f"💰 Costo total recalculado (USD): ${costo_total_usd:.6f}")
        self.stdout.write(f"💰 Costo total recalculado (COP): ${costo_total_cop:,.2f}")
        self.stdout.write("")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  DRY-RUN: No se guardaron cambios. Ejecuta sin --dry-run para guardar."))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Cambios guardados en la base de datos"))
        
        self.stdout.write("=" * 80)

