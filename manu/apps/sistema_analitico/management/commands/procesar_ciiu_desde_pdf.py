"""
Comando de management para procesar el PDF de CIIU usando DeepSeek.

Uso:
    python manage.py procesar_ciiu_desde_pdf --pdf-path CIIU.pdf --lote-size 10
    python manage.py procesar_ciiu_desde_pdf --dry-run  # Solo muestra qué haría
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Procesa el PDF de CIIU usando DeepSeek para extraer información estructurada'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pdf-path',
            type=str,
            default='data/ciiu/CIIU.pdf',
            help='Ruta al archivo PDF de CIIU (default: data/ciiu/CIIU.pdf)'
        )
        parser.add_argument(
            '--lote-size',
            type=int,
            default=10,
            help='Tamaño del lote para procesar (default: 10 códigos por llamada)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra qué haría sin procesar realmente'
        )
        parser.add_argument(
            '--solo-extraer',
            action='store_true',
            help='Solo extrae códigos del PDF sin procesar con DeepSeek'
        )

    def handle(self, *args, **options):
        pdf_path = options['pdf_path']
        lote_size = options['lote_size']
        dry_run = options['dry_run']
        solo_extraer = options['solo_extraer']
        
        # Verificar que existe el PDF
        if not os.path.exists(pdf_path):
            self.stdout.write(self.style.ERROR(f'❌ No se encontró el archivo: {pdf_path}'))
            return
        
        # Verificar API key
        if not getattr(settings, 'DEEPSEEK_API_KEY', None) and not solo_extraer:
            self.stdout.write(self.style.ERROR('❌ DEEPSEEK_API_KEY no configurada en settings'))
            return
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('PROCESADOR DE CIIU DESDE PDF CON DEEPSEEK'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(f'📄 PDF: {pdf_path}')
        self.stdout.write(f'📦 Tamaño de lote: {lote_size} códigos')
        self.stdout.write(f'🔧 Modo: {"DRY RUN" if dry_run else "PROCESAMIENTO REAL"}')
        self.stdout.write('')
        
        try:
            from apps.sistema_analitico.services.ciiu_pdf_processor import CIIUPDFProcessor
            
            processor = CIIUPDFProcessor(pdf_path=pdf_path)
            
            if solo_extraer:
                # Solo extraer códigos
                self.stdout.write('🔍 Extrayendo códigos CIUU del PDF...')
                codigos = processor.extraer_codigos_ciuu_del_pdf()
                self.stdout.write(self.style.SUCCESS(f'✅ Encontrados {len(codigos)} códigos CIUU'))
                
                # Mostrar primeros 5
                self.stdout.write('\n📋 Primeros 5 códigos encontrados:')
                for codigo_info in codigos[:5]:
                    self.stdout.write(f'  • {codigo_info["codigo"]}: {codigo_info["descripcion"][:60]}...')
                
                return
            
            if dry_run:
                # Solo mostrar qué haría
                self.stdout.write('🔍 [DRY RUN] Extrayendo códigos CIUU del PDF...')
                codigos = processor.extraer_codigos_ciuu_del_pdf()
                self.stdout.write(self.style.SUCCESS(f'✅ [DRY RUN] Encontrados {len(codigos)} códigos CIUU'))
                
                num_lotes = (len(codigos) + lote_size - 1) // lote_size
                costo_estimado = num_lotes * 0.0002  # ~$0.0002 USD por lote de 10
                
                self.stdout.write(f'\n📊 [DRY RUN] Estadísticas:')
                self.stdout.write(f'  • Total códigos: {len(codigos)}')
                self.stdout.write(f'  • Lotes necesarios: {num_lotes}')
                self.stdout.write(f'  • Costo estimado: ~${costo_estimado:.4f} USD (~${costo_estimado * 4000:.2f} COP)')
                self.stdout.write(f'\n⚠️  [DRY RUN] No se procesó realmente. Ejecuta sin --dry-run para procesar.')
                return
            
            # Procesamiento real
            self.stdout.write('🚀 Iniciando procesamiento completo...')
            self.stdout.write('')
            
            # Paso 1: Extraer códigos
            self.stdout.write('Paso 1/3: Extrayendo códigos CIUU del PDF...')
            codigos_extraidos = processor.extraer_codigos_ciuu_del_pdf()
            self.stdout.write(self.style.SUCCESS(f'✅ Extraídos {len(codigos_extraidos)} códigos'))
            self.stdout.write('')
            
            # Paso 2: Procesar con DeepSeek
            self.stdout.write(f'Paso 2/3: Procesando con DeepSeek (lotes de {lote_size})...')
            datos_estructurados = processor.procesar_pdf_completo(tamanio_lote=lote_size)
            self.stdout.write(self.style.SUCCESS(f'✅ Procesados {len(datos_estructurados)} códigos'))
            self.stdout.write('')
            
            # Paso 3: Guardar en BD
            self.stdout.write('Paso 3/3: Guardando en base de datos...')
            num_guardados = processor.guardar_en_bd(datos_estructurados)
            self.stdout.write(self.style.SUCCESS(f'✅ Guardados/actualizados {num_guardados} códigos'))
            self.stdout.write('')
            
            # Resumen final
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write(self.style.SUCCESS('✅ PROCESAMIENTO COMPLETADO'))
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write(f'📊 Códigos extraídos: {len(codigos_extraidos)}')
            self.stdout.write(f'📊 Códigos procesados: {len(datos_estructurados)}')
            self.stdout.write(f'💾 Códigos guardados: {num_guardados}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            logger.exception("Error procesando CIIU desde PDF")
            raise

