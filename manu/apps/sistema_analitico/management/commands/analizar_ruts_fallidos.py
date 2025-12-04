"""
Comando para analizar RUTs fallidos de un ZIP y su reporte TXT.
Identifica patrones de errores y propone soluciones.

Uso:
    python manage.py analizar_ruts_fallidos ruta/al/zip.zip ruta/al/reporte.txt
"""
import sys
import zipfile
import io
import re
from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import InMemoryUploadedFile
from apps.sistema_analitico.services.rut_extractor import extract_rut_data_from_pdf
from apps.sistema_analitico.services.rut_batch_processor import (
    obtener_razon_social_mejorada,
    truncar_campo
)
from apps.sistema_analitico.models import RUT, EmpresaServidor
import json
from collections import defaultdict


class Command(BaseCommand):
    help = 'Analiza RUTs fallidos de un ZIP y su reporte para identificar problemas'

    def add_arguments(self, parser):
        parser.add_argument('archivo_zip', type=str, help='Ruta al archivo ZIP con RUTs')
        parser.add_argument('reporte_txt', type=str, help='Ruta al reporte TXT de fallos')
        parser.add_argument('--fix', action='store_true', help='Intentar aplicar correcciones automáticas')

    def handle(self, *args, **options):
        archivo_zip = options['archivo_zip']
        reporte_txt = options['reporte_txt']
        aplicar_fixes = options.get('fix', False)

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('ANÁLISIS DE RUTs FALLIDOS'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')

        # Leer reporte de fallos
        try:
            with open(reporte_txt, 'r', encoding='utf-8') as f:
                reporte_contenido = f.read()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error leyendo reporte: {str(e)}'))
            return

        # Extraer información de fallos del reporte
        fallos = self._extraer_fallos_del_reporte(reporte_contenido)
        
        self.stdout.write(self.style.SUCCESS(f'✅ Encontrados {len(fallos)} RUTs fallidos en el reporte'))
        self.stdout.write('')

        # Categorizar fallos
        categorias = self._categorizar_fallos(fallos)
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('CATEGORIZACIÓN DE ERRORES'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')
        
        for categoria, lista_fallos in categorias.items():
            self.stdout.write(f'{categoria}: {len(lista_fallos)} casos')
            for fallo in lista_fallos[:3]:  # Mostrar primeros 3
                self.stdout.write(f'  - {fallo["archivo"]}')
            if len(lista_fallos) > 3:
                self.stdout.write(f'  ... y {len(lista_fallos) - 3} más')
            self.stdout.write('')
        
        # Abrir ZIP y analizar cada fallo
        try:
            with zipfile.ZipFile(archivo_zip, 'r') as zip_ref:
                pdf_files = {f: None for f in zip_ref.namelist() if f.lower().endswith('.pdf') and not f.endswith('/')}
                
                self.stdout.write(self.style.SUCCESS('=' * 80))
                self.stdout.write(self.style.SUCCESS('ANÁLISIS DETALLADO DE CADA FALLO'))
                self.stdout.write(self.style.SUCCESS('=' * 80))
                self.stdout.write('')
                
                analisis_detallado = []
                
                for i, fallo in enumerate(fallos, 1):
                    archivo_nombre = fallo['archivo']
                    
                    # Buscar el archivo en el ZIP (puede estar en subdirectorios)
                    pdf_path = None
                    for pdf_file in pdf_files.keys():
                        if archivo_nombre in pdf_file or pdf_file.endswith(archivo_nombre):
                            pdf_path = pdf_file
                            break
                    
                    if not pdf_path:
                        self.stdout.write(self.style.WARNING(f'{i}. {archivo_nombre}: ⚠️ No encontrado en ZIP'))
                        continue
                    
                    self.stdout.write(self.style.SUCCESS(f'{i}. Analizando: {archivo_nombre}'))
                    
                    try:
                        # Leer PDF
                        pdf_data_bytes = zip_ref.read(pdf_path)
                        pdf_file = io.BytesIO(pdf_data_bytes)
                        pdf_file.name = archivo_nombre
                        
                        # Extraer datos
                        try:
                            rut_data = extract_rut_data_from_pdf(pdf_file)
                        except Exception as e:
                            analisis = {
                                'archivo': archivo_nombre,
                                'error': 'Error al extraer PDF',
                                'detalle': str(e),
                                'categoria': 'ERROR_EXTRACCION',
                                'solucion': 'Revisar formato del PDF o usar NIT manual'
                            }
                            analisis_detallado.append(analisis)
                            self.stdout.write(f'   ❌ Error al extraer: {str(e)}')
                            continue
                        
                        # Analizar datos extraídos
                        analisis = self._analizar_rut_data(rut_data, fallo, archivo_nombre)
                        analisis_detallado.append(analisis)
                        
                        # Mostrar resumen
                        self._mostrar_resumen_analisis(analisis)
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'   ❌ Error procesando: {str(e)}'))
                        import traceback
                        self.stdout.write(traceback.format_exc())
                
                # Resumen final y recomendaciones
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('=' * 80))
                self.stdout.write(self.style.SUCCESS('RESUMEN Y RECOMENDACIONES'))
                self.stdout.write(self.style.SUCCESS('=' * 80))
                self.stdout.write('')
                
                self._generar_recomendaciones(analisis_detallado, categorias)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error procesando ZIP: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())

    def _extraer_fallos_del_reporte(self, reporte_contenido: str) -> list:
        """Extrae información de los fallos del reporte TXT"""
        fallos = []
        
        # Buscar sección de fallos
        seccion_fallos = re.search(r'RUTs FALLIDOS.*?=(.*?)(?:FIN DEL REPORTE|$)', reporte_contenido, re.DOTALL)
        if not seccion_fallos:
            return fallos
        
        contenido_fallos = seccion_fallos.group(1)
        
        # Extraer cada fallo (formato: "1. Archivo: ...")
        patron_fallo = re.compile(
            r'(\d+)\.\s*Archivo:\s*([^\n]+)\n'
            r'(?:\s*NIT:\s*([^\n]+))?\n?'
            r'(?:\s*Razón Social:\s*([^\n]+))?\n?'
            r'\s*Razón del fallo:\s*([^\n]+)',
            re.MULTILINE
        )
        
        for match in patron_fallo.finditer(contenido_fallos):
            fallo = {
                'numero': match.group(1),
                'archivo': match.group(2).strip(),
                'nit': match.group(3).strip() if match.group(3) else None,
                'razon_social': match.group(4).strip() if match.group(4) else None,
                'razon': match.group(5).strip()
            }
            fallos.append(fallo)
        
        return fallos

    def _categorizar_fallos(self, fallos: list) -> dict:
        """Categoriza los fallos por tipo de error"""
        categorias = defaultdict(list)
        
        for fallo in fallos:
            razon = fallo['razon'].lower()
            
            if 'no se encontraron empresas' in razon:
                categorias['SIN_EMPRESAS'].append(fallo)
            elif 'demasiado largo' in razon or 'character varying' in razon:
                categorias['CAMPO_DEMASIADO_LARGO'].append(fallo)
            elif 'no se pudo detectar el nit' in razon or 'no se pudo extraer el nit' in razon:
                categorias['NIT_NO_EXTRAIBLE'].append(fallo)
            elif 'error al extraer datos' in razon:
                categorias['ERROR_EXTRACCION'].append(fallo)
            elif 'error inesperado' in razon:
                categorias['ERROR_INESPERADO'].append(fallo)
            else:
                categorias['OTROS'].append(fallo)
        
        return dict(categorias)

    def _analizar_rut_data(self, rut_data: dict, fallo: dict, archivo_nombre: str) -> dict:
        """Analiza los datos extraídos de un RUT y compara con el fallo reportado"""
        analisis = {
            'archivo': archivo_nombre,
            'fallo_original': fallo,
            'rut_data': rut_data,
            'problemas': [],
            'soluciones': []
        }
        
        # Verificar NIT
        nit_normalizado = rut_data.get('nit_normalizado')
        if not nit_normalizado:
            analisis['problemas'].append('NIT no extraíble del PDF')
            analisis['soluciones'].append('Usar NIT manual o mejorar regex de extracción')
        else:
            # Verificar empresas
            empresas = EmpresaServidor.objects.filter(nit_normalizado=nit_normalizado)
            if not empresas.exists():
                analisis['problemas'].append(f'NIT {nit_normalizado} no tiene empresas asociadas')
                analisis['soluciones'].append('Crear RUT sin empresas (ya implementado)')
        
        # Verificar razón social
        razon_social_original = rut_data.get('razon_social', '')
        razon_social_mejorada = obtener_razon_social_mejorada(rut_data)
        
        if not razon_social_original or '36. Nombre comercial' in razon_social_original:
            analisis['problemas'].append('Razón social inválida o vacía')
            analisis['soluciones'].append(f'Usar razón social mejorada: "{razon_social_mejorada}"')
        
        # Verificar campos largos
        from apps.sistema_analitico.models import RUT
        campos_largos = []
        for key, value in rut_data.items():
            if key not in ['_texto_completo', '_codigos_ciiu_encontrados', '_establecimientos']:
                try:
                    field = RUT._meta.get_field(key)
                    max_length = getattr(field, 'max_length', None)
                    if max_length and isinstance(value, str) and len(value) > max_length:
                        campos_largos.append({
                            'campo': key,
                            'longitud': len(value),
                            'max_length': max_length,
                            'valor': value[:100] + '...' if len(value) > 100 else value
                        })
                except:
                    pass
        
        if campos_largos:
            analisis['problemas'].append(f'{len(campos_largos)} campo(s) exceden max_length')
            analisis['soluciones'].append('Truncar automáticamente (ya implementado)')
            analisis['campos_largos'] = campos_largos
        
        # Determinar categoría
        if 'NIT no extraíble' in str(analisis['problemas']):
            analisis['categoria'] = 'NIT_NO_EXTRAIBLE'
        elif 'no tiene empresas' in str(analisis['problemas']):
            analisis['categoria'] = 'SIN_EMPRESAS'
        elif campos_largos:
            analisis['categoria'] = 'CAMPO_DEMASIADO_LARGO'
        else:
            analisis['categoria'] = 'OTROS'
        
        return analisis

    def _mostrar_resumen_analisis(self, analisis: dict):
        """Muestra un resumen del análisis"""
        self.stdout.write(f'   Categoría: {analisis["categoria"]}')
        self.stdout.write(f'   Problemas: {len(analisis["problemas"])}')
        for problema in analisis['problemas']:
            self.stdout.write(f'     - {problema}')
        
        if analisis.get('campos_largos'):
            self.stdout.write('   Campos largos:')
            for campo in analisis['campos_largos']:
                self.stdout.write(f'     - {campo["campo"]}: {campo["longitud"]} chars (max: {campo["max_length"]})')
        
        self.stdout.write(f'   Soluciones: {len(analisis["soluciones"])}')
        for solucion in analisis['soluciones']:
            self.stdout.write(f'     ✓ {solucion}')
        self.stdout.write('')

    def _generar_recomendaciones(self, analisis_detallado: list, categorias: dict):
        """Genera recomendaciones basadas en el análisis"""
        self.stdout.write('📊 Estadísticas:')
        self.stdout.write('')
        
        # Contar por categoría
        categorias_analisis = defaultdict(int)
        for analisis in analisis_detallado:
            categorias_analisis[analisis.get('categoria', 'DESCONOCIDO')] += 1
        
        for categoria, count in categorias_analisis.items():
            self.stdout.write(f'  {categoria}: {count} casos')
        
        self.stdout.write('')
        self.stdout.write('💡 Recomendaciones:')
        self.stdout.write('')
        
        # Recomendaciones específicas
        if categorias_analisis.get('SIN_EMPRESAS', 0) > 0:
            self.stdout.write('  ✅ RUTs sin empresas: Ya se crean automáticamente (implementado)')
        
        if categorias_analisis.get('CAMPO_DEMASIADO_LARGO', 0) > 0:
            self.stdout.write('  ✅ Campos largos: Ya se truncarán automáticamente (implementado)')
        
        if categorias_analisis.get('NIT_NO_EXTRAIBLE', 0) > 0:
            self.stdout.write('  ⚠️ NITs no extraíbles: Requieren NIT manual o mejorar regex')
            self.stdout.write('     - Opción 1: Mejorar regex de extracción de NIT')
            self.stdout.write('     - Opción 2: Permitir subir PDF con NIT manual')
        
        if categorias_analisis.get('ERROR_EXTRACCION', 0) > 0:
            self.stdout.write('  ⚠️ Errores de extracción: Revisar formato de PDFs')
            self.stdout.write('     - Algunos PDFs pueden estar corruptos o en formato no estándar')
        
        self.stdout.write('')
        self.stdout.write('🔧 Correcciones aplicadas automáticamente:')
        self.stdout.write('  ✓ Crear RUT aunque no tenga empresas')
        self.stdout.write('  ✓ Truncar campos largos automáticamente')
        self.stdout.write('  ✓ Mejorar razón social para personas naturales')
        self.stdout.write('')

