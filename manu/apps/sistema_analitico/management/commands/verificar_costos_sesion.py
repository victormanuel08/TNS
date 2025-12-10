"""
Comando para verificar y comparar costos calculados vs costos reales de DeepSeek
"""
from django.core.management.base import BaseCommand
from django.db.models import Sum, Q
from apps.dian_scraper.models import ScrapingSession
from apps.sistema_analitico.models import ClasificacionContable
from apps.sistema_analitico.services.clasificador_contable_service import calcular_costo_tokens
from django.conf import settings


class Command(BaseCommand):
    help = 'Verifica y compara costos calculados vs costos reales para una sesión'

    def add_arguments(self, parser):
        parser.add_argument(
            'session_id',
            type=int,
            help='ID de la sesión de scraping a verificar'
        )

    def handle(self, *args, **options):
        session_id = options['session_id']
        
        try:
            session = ScrapingSession.objects.get(id=session_id)
        except ScrapingSession.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Sesión {session_id} no encontrada'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 Verificando costos para sesión #{session_id}'))
        self.stdout.write(f'   Rango: {session.fecha_desde} - {session.fecha_hasta}')
        self.stdout.write(f'   Estado: {session.status}')
        self.stdout.write('=' * 80)
        
        # Obtener todas las clasificaciones de esta sesión
        clasificaciones = ClasificacionContable.objects.filter(session_dian_id=session_id)
        total_clasificaciones = clasificaciones.count()
        
        self.stdout.write(f'\n📋 Total de clasificaciones: {total_clasificaciones}')
        
        # Costo acumulado desde BD
        costo_acumulado_bd = clasificaciones.aggregate(
            total=Sum('costo_total_factura')
        )['total'] or 0
        
        self.stdout.write(f'\n💰 COSTO ACUMULADO EN BD: ${float(costo_acumulado_bd):.6f} USD')
        
        # Recalcular desde tokens guardados
        total_input_tokens = 0
        total_output_tokens = 0
        total_cache_hit = 0
        total_cache_miss = 0
        clasificaciones_con_datos = 0
        
        for clasif in clasificaciones:
            if clasif.tokens_input > 0 or clasif.tokens_output > 0:
                clasificaciones_con_datos += 1
                total_input_tokens += clasif.tokens_input
                total_output_tokens += clasif.tokens_output
                
                # Intentar extraer cache hit/miss desde respuesta_json_completa
                if clasif.respuesta_json_completa:
                    usage = clasif.respuesta_json_completa.get('usage', {})
                    cache_hit = usage.get('prompt_cache_hit_tokens', 0)
                    cache_miss = usage.get('prompt_cache_miss_tokens', 0)
                    
                    if cache_hit > 0 or cache_miss > 0:
                        total_cache_hit += cache_hit
                        total_cache_miss += cache_miss
                    else:
                        # Estimación conservadora (70% hit, 30% miss)
                        total_cache_hit += int(clasif.tokens_input * 0.7)
                        total_cache_miss += int(clasif.tokens_input * 0.3)
                else:
                    # Estimación conservadora
                    total_cache_hit += int(clasif.tokens_input * 0.7)
                    total_cache_miss += int(clasif.tokens_input * 0.3)
        
        self.stdout.write(f'\n📊 TOKENS TOTALES:')
        self.stdout.write(f'   - Input tokens: {total_input_tokens:,}')
        self.stdout.write(f'   - Output tokens: {total_output_tokens:,}')
        self.stdout.write(f'   - Cache HIT: {total_cache_hit:,} ({total_cache_hit/total_input_tokens*100:.1f}% del input)' if total_input_tokens > 0 else '   - Cache HIT: 0')
        self.stdout.write(f'   - Cache MISS: {total_cache_miss:,} ({total_cache_miss/total_input_tokens*100:.1f}% del input)' if total_input_tokens > 0 else '   - Cache MISS: 0')
        self.stdout.write(f'   - Clasificaciones con datos: {clasificaciones_con_datos}/{total_clasificaciones}')
        
        # Recalcular costo
        if total_input_tokens > 0 or total_output_tokens > 0:
            costo_recalculado = calcular_costo_tokens(
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cache_hit_tokens=total_cache_hit if total_cache_hit > 0 else None,
                cache_miss_tokens=total_cache_miss if total_cache_miss > 0 else None
            )
            
            self.stdout.write(f'\n💰 COSTO RECALCULADO DESDE TOKENS:')
            self.stdout.write(f'   - Costo Input: ${costo_recalculado["costo_input_usd"]:.6f} USD')
            self.stdout.write(f'   - Costo Output: ${costo_recalculado["costo_output_usd"]:.6f} USD')
            self.stdout.write(f'   - Costo Total: ${costo_recalculado["costo_usd"]:.6f} USD')
            self.stdout.write(f'   - Costo Total COP: ${costo_recalculado["costo_cop"]:,.2f} COP')
            
            # Comparar
            diferencia = float(costo_recalculado["costo_usd"]) - float(costo_acumulado_bd)
            porcentaje_diferencia = (diferencia / float(costo_acumulado_bd) * 100) if costo_acumulado_bd > 0 else 0
            
            self.stdout.write(f'\n🔍 COMPARACIÓN:')
            self.stdout.write(f'   - Diferencia: ${diferencia:.6f} USD ({porcentaje_diferencia:+.2f}%)')
            
            if abs(diferencia) > 0.001:
                self.stdout.write(self.style.WARNING(f'   ⚠️ Hay una diferencia significativa entre BD y recálculo'))
            else:
                self.stdout.write(self.style.SUCCESS(f'   ✅ Los costos coinciden'))
        
        # Mostrar precios actuales
        self.stdout.write(f'\n⚙️ PRECIOS CONFIGURADOS:')
        precio_output = getattr(settings, 'AIANALYTICS_PRICE_OUTPUT_TOKEN', None) or getattr(settings, 'DEEPSEEK_PRICE_OUTPUT_TOKEN', 0.00000042)
        precio_cache_hit = getattr(settings, 'AIANALYTICS_PRICE_INPUT_CACHE_HIT', None) or getattr(settings, 'DEEPSEEK_PRICE_INPUT_CACHE_HIT', 0.000000028)
        precio_cache_miss = getattr(settings, 'AIANALYTICS_PRICE_INPUT_CACHE_MISS', None) or getattr(settings, 'DEEPSEEK_PRICE_INPUT_CACHE_MISS', 0.00000056)
        
        self.stdout.write(f'   - Output token: ${precio_output:.10f} USD')
        self.stdout.write(f'   - Input cache HIT: ${precio_cache_hit:.10f} USD')
        self.stdout.write(f'   - Input cache MISS: ${precio_cache_miss:.10f} USD')
        
        # Mostrar detalles por factura (primeras 5)
        self.stdout.write(f'\n📄 DETALLE DE PRIMERAS 5 CLASIFICACIONES:')
        for i, clasif in enumerate(clasificaciones[:5], 1):
            self.stdout.write(f'\n   {i}. Factura {clasif.factura_numero}:')
            self.stdout.write(f'      - Costo BD: ${float(clasif.costo_total_factura):.6f} USD')
            self.stdout.write(f'      - Tokens Input: {clasif.tokens_input:,}')
            self.stdout.write(f'      - Tokens Output: {clasif.tokens_output:,}')
            
            if clasif.respuesta_json_completa:
                usage = clasif.respuesta_json_completa.get('usage', {})
                cache_hit = usage.get('prompt_cache_hit_tokens', None)
                cache_miss = usage.get('prompt_cache_miss_tokens', None)
                
                if cache_hit is not None and cache_miss is not None:
                    self.stdout.write(f'      - Cache HIT: {cache_hit:,}')
                    self.stdout.write(f'      - Cache MISS: {cache_miss:,}')
                    
                    costo_detalle = calcular_costo_tokens(
                        input_tokens=clasif.tokens_input,
                        output_tokens=clasif.tokens_output,
                        cache_hit_tokens=cache_hit,
                        cache_miss_tokens=cache_miss
                    )
                    self.stdout.write(f'      - Costo recalculado: ${costo_detalle["costo_usd"]:.6f} USD')
                    
                    diff = float(costo_detalle["costo_usd"]) - float(clasif.costo_total_factura)
                    if abs(diff) > 0.0001:
                        self.stdout.write(self.style.WARNING(f'      ⚠️ Diferencia: ${diff:.6f} USD'))
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('✅ Verificación completada'))

