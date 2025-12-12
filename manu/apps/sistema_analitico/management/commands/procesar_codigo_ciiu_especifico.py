"""
Comando para procesar un código CIUU específico (simulado o con DeepSeek).

Uso:
    # Simulado (solo muestra qué se enviaría)
    python manage.py procesar_codigo_ciiu_especifico 0111 --simulado
    
    # Real (llama a DeepSeek)
    python manage.py procesar_codigo_ciiu_especifico 0111
    
    # Validar inserción en modelo
    python manage.py procesar_codigo_ciiu_especifico 0111 --validar-modelo
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import json
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Procesa un código CIUU específico (simulado o con DeepSeek)'

    def add_arguments(self, parser):
        parser.add_argument(
            'codigo',
            type=str,
            help='Código CIUU a procesar (ej: 0111, 2829)'
        )
        parser.add_argument(
            '--simulado',
            action='store_true',
            help='Solo muestra qué se enviaría a DeepSeek (no llama realmente)'
        )
        parser.add_argument(
            '--validar-modelo',
            action='store_true',
            help='Valida que el resultado se inserta correctamente en el modelo'
        )
        parser.add_argument(
            '--pdf-path',
            type=str,
            default='data/ciiu/CIIU.pdf',
            help='Ruta al PDF (default: data/ciiu/CIIU.pdf)'
        )

    def handle(self, *args, **options):
        codigo = options['codigo'].strip()
        simulado = options['simulado']
        validar_modelo = options['validar_modelo']
        pdf_path = options['pdf_path']
        
        if not os.path.exists(pdf_path):
            self.stdout.write(self.style.ERROR(f'❌ No se encontró el archivo: {pdf_path}'))
            return
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS(f'PROCESAMIENTO DE CÓDIGO CIUU: {codigo}'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')
        
        try:
            from apps.sistema_analitico.services.ciiu_pdf_processor import CIIUPDFProcessor
            
            # Crear processor (puede fallar si no hay API key, pero para simulado no importa)
            try:
                processor = CIIUPDFProcessor(pdf_path=pdf_path)
            except ValueError as e:
                if simulado:
                    # Para simulado, crear un processor sin API key
                    import sys
                    from unittest.mock import MagicMock
                    processor = CIIUPDFProcessor.__new__(CIIUPDFProcessor)
                    processor.pdf_path = pdf_path
                    processor.api_key = None
                    processor.base_url = "https://api.deepseek.com/chat/completions"
                else:
                    raise
            
            # Extraer código del PDF
            self.stdout.write('🔍 Paso 1: Extrayendo código del PDF...')
            codigos_extraidos = processor.extraer_codigos_ciuu_del_pdf()
            
            codigo_info = next((c for c in codigos_extraidos if c['codigo'] == codigo), None)
            
            if not codigo_info:
                self.stdout.write(self.style.ERROR(f'❌ Código {codigo} no encontrado en el PDF'))
                self.stdout.write(f'📋 Códigos encontrados (primeros 10): {[c["codigo"] for c in codigos_extraidos[:10]]}')
                return
            
            self.stdout.write(self.style.SUCCESS(f'✅ Código {codigo} encontrado'))
            self.stdout.write(f'📝 Descripción: {codigo_info["descripcion"]}')
            self.stdout.write(f'📄 Texto completo: {len(codigo_info["texto_completo"])} caracteres')
            self.stdout.write('')
            
            # Mostrar qué se enviaría
            self.stdout.write('=' * 80)
            self.stdout.write('📤 QUÉ SE ENVIARÍA A DEEPSEEK:')
            self.stdout.write('=' * 80)
            
            texto_para_deepseek = codigo_info['texto_completo'][:3000]
            prompt_ejemplo = f"""
CÓDIGO CIUU: {codigo_info['codigo']}
DESCRIPCIÓN: {codigo_info['descripcion']}
TEXTO COMPLETO (incluye secciones "Esta clase incluye:" y "Esta clase excluye:"):
{texto_para_deepseek}

---
"""
            self.stdout.write(prompt_ejemplo[:1000])
            if len(prompt_ejemplo) > 1000:
                self.stdout.write(f'\n... (truncado, total: {len(prompt_ejemplo)} caracteres)')
            self.stdout.write('')
            
            if simulado:
                self.stdout.write('=' * 80)
                self.stdout.write('⚠️  MODO SIMULADO - No se llama a DeepSeek')
                self.stdout.write('=' * 80)
                self.stdout.write('\n💡 Para llamar realmente a DeepSeek, ejecuta sin --simulado')
                return
            
            # Llamar realmente a DeepSeek
            if not getattr(settings, 'DEEPSEEK_API_KEY', None):
                self.stdout.write(self.style.ERROR('❌ DEEPSEEK_API_KEY no configurada'))
                return
            
            self.stdout.write('🚀 Paso 2: Llamando a DeepSeek...')
            resultado = processor.procesar_lote_con_deepseek([codigo_info])
            
            if not resultado:
                self.stdout.write(self.style.ERROR('❌ Error procesando con DeepSeek'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'✅ Respuesta recibida de DeepSeek'))
            self.stdout.write('')
            
            # Mostrar respuesta
            self.stdout.write('=' * 80)
            self.stdout.write('📥 RESPUESTA DE DEEPSEEK:')
            self.stdout.write('=' * 80)
            self.stdout.write(json.dumps(resultado[0], indent=2, ensure_ascii=False))
            self.stdout.write('')
            
            # Validar modelo si se solicita
            if validar_modelo:
                self.stdout.write('=' * 80)
                self.stdout.write('💾 Paso 3: Validando inserción en modelo...')
                self.stdout.write('=' * 80)
                
                num_guardados = processor.guardar_en_bd(resultado)
                
                if num_guardados > 0:
                    self.stdout.write(self.style.SUCCESS(f'✅ Guardado en modelo: {num_guardados} código(s)'))
                    
                    # Verificar que se guardó correctamente
                    from apps.sistema_analitico.models import ActividadEconomica
                    actividad = ActividadEconomica.objects.get(codigo=codigo)
                    
                    self.stdout.write(f'\n📊 DATOS GUARDADOS EN MODELO:')
                    self.stdout.write(f'  • Código: {actividad.codigo}')
                    self.stdout.write(f'  • Descripción: {actividad.descripcion}')
                    self.stdout.write(f'  • División: {actividad.division}')
                    self.stdout.write(f'  • Grupo: {actividad.grupo}')
                    self.stdout.write(f'  • Incluye: {len(actividad.incluye) if actividad.incluye else 0} actividades')
                    self.stdout.write(f'  • Excluye: {len(actividad.excluye) if actividad.excluye else 0} actividades')
                    
                    if actividad.incluye:
                        self.stdout.write(f'\n  📋 Primeras 2 actividades INCLUYE:')
                        for act in actividad.incluye[:2]:
                            self.stdout.write(f'    - {act.get("actDescripcion", "")[:80]}...')
                    
                    if actividad.excluye:
                        self.stdout.write(f'\n  📋 Primeras 2 actividades EXCLUYE:')
                        for act in actividad.excluye[:2]:
                            self.stdout.write(f'    - {act.get("actDescripcion", "")[:80]}...')
                else:
                    self.stdout.write(self.style.ERROR('❌ No se pudo guardar en modelo'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            logger.exception("Error procesando código CIUU específico")
            raise

