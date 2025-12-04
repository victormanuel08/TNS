"""
Comando para diagnosticar la extracción de datos de un RUT PDF específico.
Útil para analizar casos problemáticos.

Uso:
    python manage.py diagnosticar_rut ruta/al/archivo.pdf
    python manage.py diagnosticar_rut ruta/al/archivo.pdf --nit 1234567890
"""
import sys
from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import InMemoryUploadedFile
from apps.sistema_analitico.services.rut_extractor import extract_rut_data_from_pdf
from apps.sistema_analitico.services.rut_batch_processor import (
    obtener_razon_social_mejorada,
    truncar_campo
)
from apps.sistema_analitico.models import RUT, EmpresaServidor
import io
import json


class Command(BaseCommand):
    help = 'Diagnostica la extracción de datos de un RUT PDF'

    def add_arguments(self, parser):
        parser.add_argument('archivo_pdf', type=str, help='Ruta al archivo PDF del RUT')
        parser.add_argument('--nit', type=str, help='NIT manual si no se puede extraer del PDF')

    def handle(self, *args, **options):
        archivo_pdf = options['archivo_pdf']
        nit_manual = options.get('nit')

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('DIAGNÓSTICO DE EXTRACCIÓN DE RUT'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')

        try:
            # Leer archivo PDF
            with open(archivo_pdf, 'rb') as f:
                pdf_data = f.read()
            
            pdf_file = io.BytesIO(pdf_data)
            pdf_file.name = archivo_pdf
            
            self.stdout.write(self.style.SUCCESS(f'✅ Archivo leído: {archivo_pdf} ({len(pdf_data)} bytes)'))
            self.stdout.write('')
            
            # Extraer datos del PDF
            self.stdout.write(self.style.WARNING('📄 Extrayendo datos del PDF...'))
            try:
                rut_data = extract_rut_data_from_pdf(pdf_file)
                self.stdout.write(self.style.SUCCESS('✅ Extracción completada'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error al extraer datos: {str(e)}'))
                import traceback
                self.stdout.write(traceback.format_exc())
                return
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write(self.style.SUCCESS('DATOS EXTRAÍDOS DEL PDF'))
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write('')
            
            # Mostrar datos extraídos (excluyendo texto completo que es muy largo)
            datos_mostrar = {k: v for k, v in rut_data.items() if k != '_texto_completo'}
            
            for key, value in datos_mostrar.items():
                if isinstance(value, (list, dict)):
                    self.stdout.write(f'{key}: {json.dumps(value, indent=2, ensure_ascii=False)}')
                else:
                    valor_str = str(value)
                    if len(valor_str) > 200:
                        valor_str = valor_str[:200] + '...'
                    self.stdout.write(f'{key}: {valor_str}')
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write(self.style.SUCCESS('ANÁLISIS DE RAZÓN SOCIAL'))
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write('')
            
            razon_social_original = rut_data.get('razon_social', '')
            tipo_contribuyente = rut_data.get('tipo_contribuyente', '')
            nombre_comercial = rut_data.get('nombre_comercial', '')
            
            self.stdout.write(f'Razón Social Original: "{razon_social_original}"')
            self.stdout.write(f'Tipo Contribuyente: {tipo_contribuyente}')
            self.stdout.write(f'Nombre Comercial: "{nombre_comercial}"')
            self.stdout.write('')
            
            # Aplicar mejora de razón social
            razon_social_mejorada = obtener_razon_social_mejorada(rut_data)
            self.stdout.write(f'Razón Social Mejorada: "{razon_social_mejorada}"')
            
            if razon_social_mejorada != razon_social_original:
                self.stdout.write(self.style.WARNING('⚠️ La razón social fue mejorada'))
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write(self.style.SUCCESS('ANÁLISIS DE NIT'))
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write('')
            
            nit_normalizado = rut_data.get('nit_normalizado')
            if not nit_normalizado and nit_manual:
                nit_normalizado = ''.join(c for c in nit_manual if c.isdigit())
                self.stdout.write(self.style.WARNING(f'⚠️ Usando NIT manual: {nit_normalizado}'))
            
            if nit_normalizado:
                self.stdout.write(f'NIT Normalizado: {nit_normalizado}')
                
                # Buscar empresas
                empresas = EmpresaServidor.objects.filter(nit_normalizado=nit_normalizado)
                self.stdout.write(f'Empresas encontradas: {empresas.count()}')
                
                if empresas.exists():
                    self.stdout.write('')
                    self.stdout.write('Empresas asociadas:')
                    for emp in empresas[:5]:  # Mostrar máximo 5
                        self.stdout.write(f'  - {emp.nombre} (ID: {emp.id}, Año: {emp.anio_fiscal}, Servidor: {emp.servidor.nombre if emp.servidor else "N/A"})')
                else:
                    self.stdout.write(self.style.WARNING('⚠️ No se encontraron empresas con este NIT'))
            else:
                self.stdout.write(self.style.ERROR('❌ No se pudo obtener NIT del PDF'))
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write(self.style.SUCCESS('ANÁLISIS DE CAMPOS (TRUNCAMIENTO)'))
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write('')
            
            # Simular truncamiento de campos
            from apps.sistema_analitico.models import RUT
            campos_truncados = []
            
            for key, value in rut_data.items():
                if key not in ['_texto_completo', '_codigos_ciiu_encontrados', '_establecimientos']:
                    try:
                        field = RUT._meta.get_field(key)
                        max_length = getattr(field, 'max_length', None)
                        
                        if max_length and isinstance(value, str) and len(value) > max_length:
                            valor_truncado, fue_truncado = truncar_campo(value, max_length, key)
                            campos_truncados.append({
                                'campo': key,
                                'longitud_original': len(value),
                                'max_length': max_length,
                                'valor_original': value[:100] + '...' if len(value) > 100 else value,
                                'valor_truncado': valor_truncado
                            })
                    except:
                        pass
            
            if campos_truncados:
                self.stdout.write(self.style.WARNING('⚠️ Campos que serían truncados:'))
                for campo in campos_truncados:
                    self.stdout.write(f'  - {campo["campo"]}: {campo["longitud_original"]} chars → {campo["max_length"]} chars')
                    self.stdout.write(f'    Original: "{campo["valor_original"]}"')
                    self.stdout.write(f'    Truncado: "{campo["valor_truncado"]}"')
                    self.stdout.write('')
            else:
                self.stdout.write('✅ No hay campos que requieran truncamiento')
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write(self.style.SUCCESS('RESUMEN'))
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write('')
            
            # Resumen final
            problemas = []
            if not nit_normalizado:
                problemas.append('❌ NIT no extraíble')
            if not empresas.exists() if nit_normalizado else False:
                problemas.append('⚠️ Sin empresas asociadas')
            if not razon_social_mejorada or razon_social_mejorada == 'Sin razón social':
                problemas.append('⚠️ Razón social no válida')
            if campos_truncados:
                problemas.append(f'⚠️ {len(campos_truncados)} campo(s) truncado(s)')
            
            if problemas:
                self.stdout.write(self.style.WARNING('Problemas detectados:'))
                for problema in problemas:
                    self.stdout.write(f'  {problema}')
            else:
                self.stdout.write(self.style.SUCCESS('✅ No se detectaron problemas'))
            
            self.stdout.write('')
            
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ Archivo no encontrado: {archivo_pdf}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())

