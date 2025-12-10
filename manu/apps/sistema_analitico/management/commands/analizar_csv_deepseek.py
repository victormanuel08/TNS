"""
Comando para analizar datos de consumo de DeepSeek desde CSV
y compararlos con las clasificaciones del sistema
"""
from django.core.management.base import BaseCommand
from django.db.models import Sum, Q
from apps.dian_scraper.models import ScrapingSession
from apps.sistema_analitico.models import ClasificacionContable
from apps.sistema_analitico.services.clasificador_contable_service import calcular_costo_tokens
from django.conf import settings
import csv
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Analiza CSV de DeepSeek y compara con clasificaciones del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-usage',
            type=str,
            help='Ruta al CSV de uso detallado de DeepSeek (con columnas user_id, utc_date, model, api_key_name, api_key, type, price, amount)'
        )
        parser.add_argument(
            '--csv-cost',
            type=str,
            help='Ruta al CSV de costos de DeepSeek (con columnas user_id, utc_date, model, wallet_type, cost, currency)'
        )
        parser.add_argument(
            '--session-id',
            type=int,
            help='ID de la sesión a comparar'
        )
        parser.add_argument(
            '--fecha-desde',
            type=str,
            help='Fecha desde (YYYY-MM-DD) para filtrar en DeepSeek'
        )
        parser.add_argument(
            '--fecha-hasta',
            type=str,
            help='Fecha hasta (YYYY-MM-DD) para filtrar en DeepSeek'
        )

    def handle(self, *args, **options):
        csv_usage_path = options.get('csv_usage')
        csv_cost_path = options.get('csv_cost')
        session_id = options.get('session_id')
        fecha_desde = options.get('fecha_desde')
        fecha_hasta = options.get('fecha_hasta')
        
        self.stdout.write(self.style.SUCCESS('\n📊 ANÁLISIS DE CONSUMO DEEPSEEK'))
        self.stdout.write('=' * 80)
        
        # Analizar CSV de costos (más simple)
        if csv_cost_path:
            self.stdout.write(f'\n📄 Analizando CSV de costos: {csv_cost_path}')
            self._analizar_csv_costos(csv_cost_path, fecha_desde, fecha_hasta)
        
        # Analizar CSV de uso detallado
        if csv_usage_path:
            self.stdout.write(f'\n📄 Analizando CSV de uso detallado: {csv_usage_path}')
            self._analizar_csv_uso(csv_usage_path, fecha_desde, fecha_hasta)
        
        # Comparar con sesión del sistema
        if session_id:
            self.stdout.write(f'\n📊 Comparando con sesión #{session_id} del sistema')
            self._comparar_con_sesion(session_id)
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('✅ Análisis completado'))
    
    def _analizar_csv_costos(self, csv_path, fecha_desde=None, fecha_hasta=None):
        """Analiza el CSV de costos agregados de DeepSeek"""
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                total_cost = 0
                costos_por_fecha = {}
                costos_por_modelo = {}
                total_requests = 0
                
                for row in reader:
                    fecha = row.get('utc_date', '')
                    modelo = row.get('model', '')
                    costo = float(row.get('cost', 0))
                    currency = row.get('currency', 'USD')
                    
                    # Filtrar por fecha si se especifica
                    if fecha_desde and fecha < fecha_desde:
                        continue
                    if fecha_hasta and fecha > fecha_hasta:
                        continue
                    
                    # Solo procesar USD
                    if currency != 'USD':
                        continue
                    
                    total_cost += costo
                    total_requests += 1
                    
                    # Agrupar por fecha
                    if fecha not in costos_por_fecha:
                        costos_por_fecha[fecha] = 0
                    costos_por_fecha[fecha] += costo
                    
                    # Agrupar por modelo
                    if modelo not in costos_por_modelo:
                        costos_por_modelo[modelo] = 0
                    costos_por_modelo[modelo] += costo
                
                self.stdout.write(f'\n💰 RESUMEN DE COSTOS DEEPSEEK:')
                self.stdout.write(f'   - Total registros procesados: {total_requests}')
                self.stdout.write(f'   - Costo total: ${total_cost:.6f} USD')
                
                if fecha_desde or fecha_hasta:
                    self.stdout.write(f'   - Filtro aplicado: {fecha_desde or "inicio"} - {fecha_hasta or "fin"}')
                
                self.stdout.write(f'\n📅 Costos por fecha:')
                for fecha in sorted(costos_por_fecha.keys()):
                    self.stdout.write(f'   - {fecha}: ${costos_por_fecha[fecha]:.6f} USD')
                
                self.stdout.write(f'\n🤖 Costos por modelo:')
                for modelo, costo in costos_por_modelo.items():
                    self.stdout.write(f'   - {modelo}: ${costo:.6f} USD')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error leyendo CSV de costos: {e}'))
    
    def _analizar_csv_uso(self, csv_path, fecha_desde=None, fecha_hasta=None):
        """Analiza el CSV de uso detallado de DeepSeek"""
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                total_output_tokens = 0
                total_input_cache_hit = 0
                total_input_cache_miss = 0
                total_requests = 0
                tokens_por_fecha = {}
                tokens_por_modelo = {}
                
                for row in reader:
                    fecha = row.get('utc_date', '')
                    modelo = row.get('model', '')
                    tipo = row.get('type', '')
                    amount_str = row.get('amount', '')
                    
                    # Filtrar por fecha si se especifica
                    if fecha_desde and fecha < fecha_desde:
                        continue
                    if fecha_hasta and fecha > fecha_hasta:
                        continue
                    
                    # El CSV tiene columnas separadas: type, price, amount
                    # type contiene el nombre de la métrica directamente
                    if tipo and amount_str:
                        try:
                            cantidad = int(float(amount_str))
                            metric_name = tipo.strip()
                            
                            if 'output_tokens' in metric_name:
                                total_output_tokens += cantidad
                                if fecha not in tokens_por_fecha:
                                    tokens_por_fecha[fecha] = {'output': 0, 'cache_hit': 0, 'cache_miss': 0}
                                tokens_por_fecha[fecha]['output'] += cantidad
                                
                                if modelo not in tokens_por_modelo:
                                    tokens_por_modelo[modelo] = {'output': 0, 'cache_hit': 0, 'cache_miss': 0}
                                tokens_por_modelo[modelo]['output'] += cantidad
                            
                            elif 'input_cache_hit_tokens' in metric_name:
                                total_input_cache_hit += cantidad
                                if fecha not in tokens_por_fecha:
                                    tokens_por_fecha[fecha] = {'output': 0, 'cache_hit': 0, 'cache_miss': 0}
                                tokens_por_fecha[fecha]['cache_hit'] += cantidad
                                
                                if modelo not in tokens_por_modelo:
                                    tokens_por_modelo[modelo] = {'output': 0, 'cache_hit': 0, 'cache_miss': 0}
                                tokens_por_modelo[modelo]['cache_hit'] += cantidad
                            
                            elif 'input_cache_miss_tokens' in metric_name:
                                total_input_cache_miss += cantidad
                                if fecha not in tokens_por_fecha:
                                    tokens_por_fecha[fecha] = {'output': 0, 'cache_hit': 0, 'cache_miss': 0}
                                tokens_por_fecha[fecha]['cache_miss'] += cantidad
                                
                                if modelo not in tokens_por_modelo:
                                    tokens_por_modelo[modelo] = {'output': 0, 'cache_hit': 0, 'cache_miss': 0}
                                tokens_por_modelo[modelo]['cache_miss'] += cantidad
                            
                            elif 'request_count' in metric_name:
                                total_requests += cantidad
                        except (ValueError, TypeError):
                            pass
                
                self.stdout.write(f'\n📊 RESUMEN DE TOKENS DEEPSEEK:')
                self.stdout.write(f'   - Total requests: {total_requests}')
                self.stdout.write(f'   - Output tokens: {total_output_tokens:,}')
                self.stdout.write(f'   - Input cache HIT: {total_input_cache_hit:,}')
                self.stdout.write(f'   - Input cache MISS: {total_input_cache_miss:,}')
                self.stdout.write(f'   - Input total: {total_input_cache_hit + total_input_cache_miss:,}')
                
                # Calcular costo desde tokens
                if total_output_tokens > 0 or total_input_cache_hit > 0 or total_input_cache_miss > 0:
                    precio_output = getattr(settings, 'AIANALYTICS_PRICE_OUTPUT_TOKEN', 0.00000042)
                    precio_cache_hit = getattr(settings, 'AIANALYTICS_PRICE_INPUT_CACHE_HIT', 0.000000028)
                    precio_cache_miss = getattr(settings, 'AIANALYTICS_PRICE_INPUT_CACHE_MISS', 0.00000056)
                    
                    costo_output = total_output_tokens * precio_output
                    costo_input = (total_input_cache_hit * precio_cache_hit) + (total_input_cache_miss * precio_cache_miss)
                    costo_total = costo_input + costo_output
                    
                    self.stdout.write(f'\n💰 COSTO CALCULADO DESDE TOKENS:')
                    self.stdout.write(f'   - Costo Input: ${costo_input:.6f} USD')
                    self.stdout.write(f'   - Costo Output: ${costo_output:.6f} USD')
                    self.stdout.write(f'   - Costo Total: ${costo_total:.6f} USD')
                
                if tokens_por_fecha:
                    self.stdout.write(f'\n📅 Tokens por fecha:')
                    for fecha in sorted(tokens_por_fecha.keys()):
                        datos = tokens_por_fecha[fecha]
                        self.stdout.write(f'   - {fecha}: Output={datos["output"]:,}, Cache HIT={datos["cache_hit"]:,}, Cache MISS={datos["cache_miss"]:,}')
                
                if tokens_por_modelo:
                    self.stdout.write(f'\n🤖 Tokens por modelo:')
                    for modelo, datos in tokens_por_modelo.items():
                        self.stdout.write(f'   - {modelo}: Output={datos["output"]:,}, Cache HIT={datos["cache_hit"]:,}, Cache MISS={datos["cache_miss"]:,}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error leyendo CSV de uso: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
    
    def _comparar_con_sesion(self, session_id):
        """Compara los datos de DeepSeek con una sesión del sistema"""
        try:
            session = ScrapingSession.objects.get(id=session_id)
            clasificaciones = ClasificacionContable.objects.filter(session_dian_id=session_id)
            
            costo_sistema = clasificaciones.aggregate(total=Sum('costo_total_factura'))['total'] or 0
            
            self.stdout.write(f'\n🔍 COMPARACIÓN CON SESIÓN #{session_id}:')
            self.stdout.write(f'   - Rango de la sesión: {session.fecha_desde} - {session.fecha_hasta}')
            self.stdout.write(f'   - Clasificaciones: {clasificaciones.count()}')
            self.stdout.write(f'   - Costo en sistema: ${float(costo_sistema):.6f} USD')
            
        except ScrapingSession.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Sesión {session_id} no encontrada'))

