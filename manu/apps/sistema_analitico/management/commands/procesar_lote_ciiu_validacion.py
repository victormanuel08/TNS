"""
Comando para procesar un lote de códigos CIUU del PDF.
Primero verifica si están completos en BD, solo procesa los que faltan.
Muestra costo total al final.
"""
import logging
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from apps.sistema_analitico.services.ciiu_pdf_processor import CIIUPDFProcessor
from apps.sistema_analitico.models import ActividadEconomica

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Procesa un lote de códigos CIUU del PDF. Verifica BD primero, solo procesa los incompletos. Muestra costo total.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cantidad',
            type=int,
            default=10,
            help='Número de códigos CIUU a procesar (por defecto: 10). Use --todos para procesar todos.'
        )
        parser.add_argument(
            '--todos',
            action='store_true',
            help='Procesa TODOS los códigos CIUU del PDF (ignora --cantidad)'
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

    def _es_registro_completo(self, actividad: ActividadEconomica) -> bool:
        """
        Verifica si un registro de ActividadEconomica está completo.
        Similar a la validación en obtener_contexto_ciuu_inteligente.
        """
        # Validar si la descripción es genérica
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
        
        # Obtener incluye/excluye
        incluye_list = actividad.incluye if actividad.incluye else []
        excluye_list = actividad.excluye if actividad.excluye else []
        
        tiene_incluye = len(incluye_list) > 0
        tiene_excluye = len(excluye_list) > 0
        tiene_incluye_o_excluye = tiene_incluye or tiene_excluye
        
        # Solo es incompleto si: descripción genérica Y sin incluye Y sin excluye
        return not (es_descripcion_generica and not tiene_incluye_o_excluye)

    def handle(self, *args, **options):
        cantidad = options['cantidad']
        pdf_path = options['pdf_path']
        forzar = options['forzar']
        todos = options['todos']

        if not os.path.exists(pdf_path):
            raise CommandError(f"El archivo PDF no se encontró en la ruta: {pdf_path}")

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("PROCESAMIENTO DE LOTE DE CÓDIGOS CIUU"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        if todos:
            self.stdout.write(f"Cantidad a procesar: TODOS")
        else:
            self.stdout.write(f"Cantidad a procesar: {cantidad}")
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
            
            # Determinar cuántos procesar
            cantidad_a_procesar = len(todos_los_codigos) if todos else cantidad
            
            # Paso 2: Verificar cuáles están completos en BD
            if todos:
                self.stdout.write(self.style.HTTP_INFO(f"\n🔍 Paso 2: Verificando estado en BD (TODOS los {len(todos_los_codigos)} códigos)..."))
            else:
                self.stdout.write(self.style.HTTP_INFO(f"\n🔍 Paso 2: Verificando estado en BD (primeros {cantidad})..."))
            
            codigos_a_procesar = []
            codigos_completos = []
            codigos_incompletos = []
            
            for codigo_info in todos_los_codigos[:cantidad_a_procesar]:
                codigo = codigo_info['codigo']
                
                try:
                    actividad = ActividadEconomica.objects.get(codigo=codigo)
                    
                    if forzar:
                        # Si se fuerza, procesar todos
                        codigos_a_procesar.append(codigo_info)
                        self.stdout.write(f"   ⚠️  {codigo}: Existe en BD pero se forzará procesamiento")
                    elif self._es_registro_completo(actividad):
                        # Está completo, no procesar
                        codigos_completos.append(codigo)
                        self.stdout.write(f"   ✅ {codigo}: Completo en BD (descripción: {actividad.descripcion[:50] if actividad.descripcion else 'N/A'}...)")
                    else:
                        # Está incompleto, procesar
                        codigos_incompletos.append(codigo)
                        codigos_a_procesar.append(codigo_info)
                        self.stdout.write(f"   ⚠️  {codigo}: Incompleto en BD, se procesará")
                except ActividadEconomica.DoesNotExist:
                    # No existe en BD, procesar
                    codigos_a_procesar.append(codigo_info)
                    self.stdout.write(f"   ❌ {codigo}: No existe en BD, se procesará")
            
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"📊 RESUMEN DE VERIFICACIÓN:"))
            self.stdout.write(f"   - Completos en BD: {len(codigos_completos)}")
            self.stdout.write(f"   - Incompletos/Faltantes: {len(codigos_a_procesar)}")
            self.stdout.write(f"   - Total a procesar: {len(codigos_a_procesar)}")
            
            if not codigos_a_procesar:
                self.stdout.write(self.style.SUCCESS("\n✅ Todos los códigos están completos en BD. No hay nada que procesar."))
                return
            
            # Paso 3: Procesar con DeepSeek (en lotes de 5 para optimizar)
            self.stdout.write(self.style.HTTP_INFO(f"\n🚀 Paso 3: Procesando {len(codigos_a_procesar)} códigos con DeepSeek..."))
            
            # Obtener costo inicial de las API keys para calcular el costo de esta ejecución
            try:
                from apps.sistema_analitico.models import AIAnalyticsAPIKey
                from django.db.models import Sum
                costo_inicial = AIAnalyticsAPIKey.objects.aggregate(
                    costo_total=Sum('costo_total_usd')
                )['costo_total'] or 0
            except Exception:
                costo_inicial = 0
            
            costo_total_usd = 0
            costo_total_cop = 0
            codigos_procesados = 0
            codigos_guardados = 0
            
            # Procesar en lotes de 5
            lote_size = 5
            for i in range(0, len(codigos_a_procesar), lote_size):
                lote = codigos_a_procesar[i:i + lote_size]
                self.stdout.write(f"\n   📦 Procesando lote {i // lote_size + 1} ({len(lote)} códigos)...")
                
                try:
                    # Procesar con DeepSeek
                    resultados = processor.procesar_lote_con_deepseek(lote)
                    
                    for resultado in resultados:
                        if 'error' in resultado:
                            self.stdout.write(self.style.ERROR(f"      ❌ Error en {resultado.get('codigo', 'N/A')}: {resultado['error']}"))
                            continue
                        
                        # Guardar en BD
                        actividad_guardada = processor.guardar_ciiu_en_bd(resultado)
                        if actividad_guardada:
                            codigos_guardados += 1
                            codigos_procesados += 1
                            self.stdout.write(self.style.SUCCESS(f"      ✅ {resultado['codigo']}: Procesado y guardado"))
                        else:
                            self.stdout.write(self.style.ERROR(f"      ❌ {resultado.get('codigo', 'N/A')}: Error al guardar"))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"      ❌ Error procesando lote: {e}"))
                    logger.exception("Error procesando lote")
            
            # Paso 4: Calcular costo total REAL de esta ejecución
            self.stdout.write(self.style.HTTP_INFO(f"\n💰 Paso 4: Calculando costo REAL de esta ejecución..."))
            
            try:
                from apps.sistema_analitico.models import AIAnalyticsAPIKey
                from django.db.models import Sum
                from django.conf import settings as django_settings
                
                # Obtener costo final de todas las API keys
                costo_final = AIAnalyticsAPIKey.objects.aggregate(
                    costo_total=Sum('costo_total_usd')
                )['costo_total'] or 0
                
                # Calcular costo REAL de esta ejecución (diferencia)
                costo_ejecucion_usd = float(costo_final) - float(costo_inicial)
                tasa = getattr(django_settings, 'TASA_CAMBIO_COP_USD', 4000)
                costo_ejecucion_cop = costo_ejecucion_usd * tasa
                
                # Obtener tokens de esta ejecución (diferencia)
                tokens_inicial = AIAnalyticsAPIKey.objects.aggregate(
                    tokens_input=Sum('tokens_input_total'),
                    tokens_output=Sum('tokens_output_total')
                )
                # Nota: No podemos calcular tokens exactos sin guardar el estado inicial
                # Pero podemos mostrar el costo real que sí calculamos
                
                self.stdout.write(self.style.SUCCESS("=" * 80))
                self.stdout.write(self.style.SUCCESS("📊 RESUMEN FINAL"))
                self.stdout.write(self.style.SUCCESS("=" * 80))
                self.stdout.write(f"✅ Códigos procesados exitosamente: {codigos_procesados}")
                self.stdout.write(f"💾 Códigos guardados en BD: {codigos_guardados}")
                self.stdout.write(f"📊 Códigos completos (no procesados): {len(codigos_completos)}")
                self.stdout.write("")
                self.stdout.write(self.style.SUCCESS("💰 COSTO REAL DE ESTA EJECUCIÓN (calculado desde tokens de DeepSeek):"))
                self.stdout.write(f"   - USD: ${costo_ejecucion_usd:.10f}")
                self.stdout.write(f"   - COP: ${costo_ejecucion_cop:,.2f} (tasa: {tasa} COP/USD)")
                if codigos_procesados > 0:
                    costo_por_codigo_usd = costo_ejecucion_usd / codigos_procesados
                    costo_por_codigo_cop = costo_ejecucion_cop / codigos_procesados
                    self.stdout.write(f"   - Por código: ${costo_por_codigo_usd:.10f} USD (${costo_por_codigo_cop:,.2f} COP)")
                self.stdout.write("")
                self.stdout.write(self.style.WARNING("💰 Costo acumulado TOTAL (todas las API keys, incluye ejecuciones previas):"))
                self.stdout.write(f"   - USD: ${float(costo_final):.10f}")
                self.stdout.write(f"   - COP: ${float(costo_final) * tasa:,.2f}")
                self.stdout.write("=" * 80)
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️  No se pudo calcular costo total: {e}"))
                logger.exception("Error calculando costo")
            
            self.stdout.write(self.style.SUCCESS("\n✅ Procesamiento completado"))

        except Exception as e:
            logger.exception("Error general durante el procesamiento del lote de CIUU.")
            raise CommandError(f"Error general: {e}")

