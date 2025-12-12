"""
Comando para procesar códigos CIUU del PDF por rango.
Ejemplo: --rango 1-100 o --rango 101-1000
"""
import logging
import os
import re
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from apps.sistema_analitico.services.ciiu_pdf_processor import CIIUPDFProcessor
from apps.sistema_analitico.models import ActividadEconomica

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Procesa códigos CIUU del PDF por rango. Ejemplo: --rango 1-100'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rango',
            type=str,
            required=True,
            help='Rango de códigos a procesar. Formato: inicio-fin (ej: 1-100, 101-1000)'
        )
        parser.add_argument(
            '--pdf-path',
            type=str,
            default='data/ciiu/CIIU.pdf',
            help='Ruta al archivo PDF de CIIU. Por defecto busca data/ciiu/CIIU.pdf'
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Si se activa, procesa todos los códigos aunque estén completos en BD'
        )
        parser.add_argument(
            '--solo-contar',
            action='store_true',
            help='Solo cuenta cuántos códigos hay en el rango, no los procesa'
        )

    def _parsear_rango(self, rango_str: str) -> tuple:
        """
        Parsea el rango en formato "inicio-fin" y retorna (inicio, fin).
        """
        match = re.match(r'^(\d+)-(\d+)$', rango_str.strip())
        if not match:
            raise CommandError(f"Formato de rango inválido: {rango_str}. Use formato: inicio-fin (ej: 1-100)")
        
        inicio = int(match.group(1))
        fin = int(match.group(2))
        
        if inicio > fin:
            raise CommandError(f"El inicio del rango ({inicio}) no puede ser mayor que el fin ({fin})")
        
        return inicio, fin

    def _es_registro_completo(self, actividad: ActividadEconomica) -> bool:
        """
        Verifica si un registro de ActividadEconomica está completo.
        """
        descripcion = actividad.descripcion or actividad.titulo or ""
        es_descripcion_generica = (
            not descripcion or 
            descripcion.strip().lower() in [
                f"actividad {actividad.codigo}", 
                f"ciuu {actividad.codigo}", 
                f"actividad {actividad.codigo.lower()}", 
                ""
            ] or
            descripcion.strip() == f"Actividad {actividad.codigo}"
        )
        
        incluye_list = actividad.incluye if actividad.incluye else []
        excluye_list = actividad.excluye if actividad.excluye else []
        
        tiene_incluye = len(incluye_list) > 0
        tiene_excluye = len(excluye_list) > 0
        tiene_incluye_o_excluye = tiene_incluye or tiene_excluye
        
        return not (es_descripcion_generica and not tiene_incluye_o_excluye)

    def _codigo_en_rango(self, codigo: str, inicio: int, fin: int) -> bool:
        """
        Verifica si un código CIUU está en el rango especificado.
        Los códigos CIUU son de 4 dígitos, así que comparamos numéricamente.
        """
        try:
            codigo_num = int(codigo)
            return inicio <= codigo_num <= fin
        except ValueError:
            return False

    def handle(self, *args, **options):
        rango_str = options['rango']
        pdf_path = options['pdf_path']
        forzar = options['forzar']
        solo_contar = options['solo_contar']

        if not os.path.exists(pdf_path):
            raise CommandError(f"El archivo PDF no se encontró en la ruta: {pdf_path}")

        # Parsear rango
        inicio, fin = self._parsear_rango(rango_str)

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("PROCESAMIENTO DE CÓDIGOS CIUU POR RANGO"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(f"Rango: {inicio}-{fin}")
        self.stdout.write(f"PDF: {pdf_path}")
        self.stdout.write(f"Forzar procesamiento: {'Sí' if forzar else 'No (solo incompletos)'}")
        self.stdout.write("")

        processor = CIIUPDFProcessor(pdf_path=pdf_path)

        try:
            # Paso 1: Extraer códigos del PDF
            self.stdout.write(self.style.HTTP_INFO("🔍 Paso 1: Extrayendo códigos CIUU del PDF (desde página 136)..."))
            todos_los_codigos = processor.extraer_codigos_ciuu_del_pdf()
            
            if not todos_los_codigos:
                raise CommandError("No se encontraron códigos CIUU en el PDF")
            
            self.stdout.write(self.style.SUCCESS(f"✅ Extraídos {len(todos_los_codigos)} códigos CIUU del PDF"))
            
            # Paso 2: Filtrar por rango
            self.stdout.write(self.style.HTTP_INFO(f"\n🔍 Paso 2: Filtrando códigos en rango {inicio}-{fin}..."))
            
            codigos_en_rango = [
                codigo_info for codigo_info in todos_los_codigos
                if self._codigo_en_rango(codigo_info['codigo'], inicio, fin)
            ]
            
            total_en_rango = len(codigos_en_rango)
            self.stdout.write(self.style.SUCCESS(f"✅ {total_en_rango} códigos encontrados en rango {inicio}-{fin}"))
            
            if not codigos_en_rango:
                self.stdout.write(self.style.WARNING(f"⚠️  No hay códigos CIUU en el rango {inicio}-{fin}"))
                self.stdout.write(self.style.SUCCESS(f"\n📊 TOTAL CIUU EN RANGO {inicio}-{fin}: 0"))
                return
            
            # Si solo quiere contar, mostrar y salir
            if solo_contar:
                self.stdout.write(self.style.SUCCESS("=" * 80))
                self.stdout.write(self.style.SUCCESS("📊 CONTEO DE CÓDIGOS CIUU"))
                self.stdout.write(self.style.SUCCESS("=" * 80))
                self.stdout.write(self.style.SUCCESS(f"📊 TOTAL CIUU EN RANGO {inicio}-{fin}: {total_en_rango}"))
                self.stdout.write("=" * 80)
                return
            
            # Paso 3: Verificar cuáles están completos en BD
            self.stdout.write(self.style.HTTP_INFO(f"\n🔍 Paso 3: Verificando estado en BD..."))
            
            codigos_a_procesar = []
            codigos_completos = []
            
            for codigo_info in codigos_en_rango:
                codigo = codigo_info['codigo']
                
                try:
                    actividad = ActividadEconomica.objects.get(codigo=codigo)
                    
                    if forzar:
                        codigos_a_procesar.append(codigo_info)
                    elif self._es_registro_completo(actividad):
                        codigos_completos.append(codigo)
                    else:
                        codigos_a_procesar.append(codigo_info)
                except ActividadEconomica.DoesNotExist:
                    codigos_a_procesar.append(codigo_info)
            
            self.stdout.write(f"   - Completos en BD: {len(codigos_completos)}")
            self.stdout.write(f"   - A procesar: {len(codigos_a_procesar)}")
            
            if not codigos_a_procesar:
                self.stdout.write(self.style.SUCCESS(f"\n✅ Todos los códigos en rango {inicio}-{fin} están completos en BD."))
                self.stdout.write(self.style.SUCCESS(f"📊 TOTAL CIUU PROCESADOS EN ESTA EJECUCIÓN: 0"))
                return
            
            # Paso 4: Obtener costo inicial
            try:
                from apps.sistema_analitico.models import AIAnalyticsAPIKey
                from django.db.models import Sum
                costo_inicial = AIAnalyticsAPIKey.objects.aggregate(
                    costo_total=Sum('costo_total_usd')
                )['costo_total'] or 0
            except Exception:
                costo_inicial = 0
            
            # Paso 5: Procesar con DeepSeek (en lotes de 5)
            self.stdout.write(self.style.HTTP_INFO(f"\n🚀 Paso 4: Procesando {len(codigos_a_procesar)} códigos con DeepSeek..."))
            
            codigos_procesados = 0
            codigos_guardados = 0
            
            lote_size = 5
            for i in range(0, len(codigos_a_procesar), lote_size):
                lote = codigos_a_procesar[i:i + lote_size]
                self.stdout.write(f"   📦 Lote {i // lote_size + 1} ({len(lote)} códigos)...")
                
                try:
                    resultados = processor.procesar_lote_con_deepseek(lote)
                    
                    for resultado in resultados:
                        if 'error' in resultado:
                            continue
                        
                        actividad_guardada = processor.guardar_ciiu_en_bd(resultado)
                        if actividad_guardada:
                            codigos_guardados += 1
                            codigos_procesados += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"      ❌ Error: {e}"))
                    logger.exception("Error procesando lote")
            
            # Paso 6: Calcular costo real
            try:
                from apps.sistema_analitico.models import AIAnalyticsAPIKey
                from django.db.models import Sum
                from django.conf import settings as django_settings
                
                costo_final = AIAnalyticsAPIKey.objects.aggregate(
                    costo_total=Sum('costo_total_usd')
                )['costo_total'] or 0
                
                costo_ejecucion_usd = float(costo_final) - float(costo_inicial)
                tasa = getattr(django_settings, 'TASA_CAMBIO_COP_USD', 4000)
                costo_ejecucion_cop = costo_ejecucion_usd * tasa
                
                self.stdout.write(self.style.SUCCESS("=" * 80))
                self.stdout.write(self.style.SUCCESS("📊 RESUMEN FINAL"))
                self.stdout.write(self.style.SUCCESS("=" * 80))
                self.stdout.write(self.style.SUCCESS(f"📊 TOTAL CIUU EN RANGO {inicio}-{fin}: {total_en_rango}"))
                self.stdout.write(self.style.SUCCESS(f"📊 TOTAL CIUU PROCESADOS EN ESTA EJECUCIÓN: {codigos_procesados}"))
                self.stdout.write(f"💰 Costo: ${costo_ejecucion_usd:.10f} USD (${costo_ejecucion_cop:,.2f} COP)")
                if codigos_procesados > 0:
                    costo_por_codigo = costo_ejecucion_cop / codigos_procesados
                    self.stdout.write(f"💰 Costo por código: ${costo_por_codigo:,.2f} COP")
                self.stdout.write("=" * 80)
                
            except Exception as e:
                self.stdout.write(self.style.SUCCESS("=" * 80))
                self.stdout.write(self.style.SUCCESS(f"📊 TOTAL CIUU EN RANGO {inicio}-{fin}: {total_en_rango}"))
                self.stdout.write(self.style.SUCCESS(f"📊 TOTAL CIUU PROCESADOS EN ESTA EJECUCIÓN: {codigos_procesados}"))
                self.stdout.write("=" * 80)
                logger.exception("Error calculando costo")
            
            self.stdout.write(self.style.SUCCESS("\n✅ Procesamiento completado"))

        except Exception as e:
            logger.exception("Error general durante el procesamiento del rango de CIUU.")
            raise CommandError(f"Error general: {e}")

