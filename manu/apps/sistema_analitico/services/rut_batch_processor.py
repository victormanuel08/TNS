"""
Servicio para procesar múltiples RUTs desde un archivo ZIP
"""
import zipfile
import io
from typing import Dict, List, Tuple
from django.core.files.uploadedfile import InMemoryUploadedFile
from .rut_extractor import extract_rut_data_from_pdf


def normalize_nit(nit: str) -> str:
    """Normaliza NIT eliminando puntos, guiones y espacios"""
    if not nit:
        return ''
    return ''.join(c for c in str(nit) if c.isdigit())


def procesar_zip_ruts(zip_file, task=None) -> Dict:
    """
    Procesa un archivo ZIP con múltiples PDFs de RUT.
    Busca PDFs en todos los subdirectorios del ZIP.
    
    Args:
        zip_file: Archivo ZIP a procesar (puede ser File, BytesIO, o ruta)
        task: Tarea Celery opcional para actualizar progreso
    
    Returns:
        Dict con:
        - exitosos: List[Dict] - RUTs procesados exitosamente
        - fallidos: List[Dict] - RUTs que fallaron con razón
        - total: int
        - reporte_txt: str - Reporte en formato TXT
        - pdf_files: List[str] - Lista de archivos PDF encontrados
    """
    from ..models import RUT, EmpresaServidor
    
    resultados = {
        'exitosos': [],
        'fallidos': [],
        'total': 0,
        'reporte_txt': '',
        'pdf_files': []
    }
    
    try:
        # Leer ZIP (puede ser ruta de archivo o objeto file)
        if isinstance(zip_file, str):
            # Es una ruta de archivo
            zip_ref = zipfile.ZipFile(zip_file, 'r')
        else:
            # Es un objeto file
            zip_ref = zipfile.ZipFile(zip_file, 'r')
        
        try:
            # Obtener lista de archivos PDF (incluyendo subdirectorios)
            # zip_ref.namelist() incluye todos los archivos, incluso en subdirectorios
            # Filtrar solo PDFs y excluir directorios (que terminan en /)
            pdf_files = [f for f in zip_ref.namelist() if f.lower().endswith('.pdf') and not f.endswith('/')]
            resultados['total'] = len(pdf_files)
            resultados['pdf_files'] = pdf_files
            
            if not pdf_files:
                resultados['fallidos'].append({
                    'archivo': 'ZIP',
                    'razon': 'No se encontraron archivos PDF en el ZIP'
                })
                return resultados
            
            # Procesar cada PDF
            for idx, pdf_name in enumerate(pdf_files, 1):
                # Actualizar progreso si hay tarea Celery
                if task:
                    task.update_state(
                        state='PROCESSING',
                        meta={
                            'status': f'Procesando {idx}/{len(pdf_files)}: {pdf_name}',
                            'total': len(pdf_files),
                            'procesados': idx - 1,
                            'exitosos': len(resultados['exitosos']),
                            'fallidos': len(resultados['fallidos'])
                        }
                    )
                try:
                    # Leer PDF del ZIP
                    pdf_data_bytes = zip_ref.read(pdf_name)
                    
                    # Crear archivo en memoria
                    pdf_file = io.BytesIO(pdf_data_bytes)
                    pdf_file.name = pdf_name
                    
                    # Extraer datos del PDF
                    try:
                        rut_data = extract_rut_data_from_pdf(pdf_file)
                    except Exception as e:
                        resultados['fallidos'].append({
                            'archivo': pdf_name,
                            'razon': f'Error al extraer datos del PDF: {str(e)}'
                        })
                        continue
                    
                    # Obtener NIT
                    nit_normalizado = rut_data.get('nit_normalizado')
                    if not nit_normalizado:
                        resultados['fallidos'].append({
                            'archivo': pdf_name,
                            'razon': 'No se pudo detectar el NIT del PDF'
                        })
                        continue
                    
                    # Verificar si hay empresas asociadas
                    empresas = EmpresaServidor.objects.filter(nit_normalizado=nit_normalizado)
                    if not empresas.exists():
                        resultados['fallidos'].append({
                            'archivo': pdf_name,
                            'nit': rut_data.get('nit', nit_normalizado),
                            'nit_normalizado': nit_normalizado,
                            'razon_social': rut_data.get('razon_social', 'No detectada'),
                            'razon': f'No se encontraron empresas con NIT {nit_normalizado} en ningún servidor'
                        })
                        continue
                    
                    # Buscar o crear RUT
                    rut, created = RUT.objects.get_or_create(
                        nit_normalizado=nit_normalizado,
                        defaults={
                            'nit': rut_data.get('nit', nit_normalizado),
                            'dv': rut_data.get('dv', ''),
                            'razon_social': rut_data.get('razon_social', ''),
                        }
                    )
                    
                    # Actualizar campos desde PDF
                    for key, value in rut_data.items():
                        if key not in ['_texto_completo', '_codigos_ciiu_encontrados', '_establecimientos'] and hasattr(rut, key):
                            # Si el valor es None, establecerlo explícitamente para limpiar campos
                            if value is None:
                                setattr(rut, key, None)
                            elif value:  # Solo asignar si tiene valor
                                setattr(rut, key, value)
                    
                    # Guardar PDF
                    pdf_file.seek(0)  # Resetear posición
                    if rut.archivo_pdf:
                        rut.archivo_pdf.delete(save=False)
                    
                    # Crear InMemoryUploadedFile para guardar
                    pdf_upload = InMemoryUploadedFile(
                        pdf_file,
                        None,
                        pdf_name,
                        'application/pdf',
                        len(pdf_data_bytes),
                        None
                    )
                    rut.archivo_pdf = pdf_upload
                    rut.save()
                    
                    # Procesar establecimientos
                    from ..models import EstablecimientoRUT
                    establecimientos_data = rut_data.get('_establecimientos', [])
                    # Eliminar establecimientos antiguos
                    EstablecimientoRUT.objects.filter(rut=rut).delete()
                    # Crear nuevos establecimientos
                    for est_data in establecimientos_data:
                        EstablecimientoRUT.objects.create(
                            rut=rut,
                            nombre=est_data.get('nombre', ''),
                            tipo_establecimiento=est_data.get('tipo_establecimiento'),
                            tipo_establecimiento_codigo=est_data.get('tipo_establecimiento_codigo'),
                            actividad_economica_ciiu=est_data.get('actividad_economica_ciiu'),
                            actividad_economica_descripcion=est_data.get('actividad_economica_descripcion'),
                            departamento_codigo=est_data.get('departamento_codigo'),
                            departamento_nombre=est_data.get('departamento_nombre', ''),
                            ciudad_codigo=est_data.get('ciudad_codigo'),
                            ciudad_nombre=est_data.get('ciudad_nombre', ''),
                            direccion=est_data.get('direccion', ''),
                            matricula_mercantil=est_data.get('matricula_mercantil'),
                            telefono=est_data.get('telefono'),
                        )
                    
                    # Procesar códigos CIIU
                    codigos_ciiu = rut_data.get('_codigos_ciiu_encontrados', [])
                    if not codigos_ciiu:
                        if rut_data.get('actividad_principal_ciiu'):
                            codigos_ciiu.append(rut_data['actividad_principal_ciiu'])
                        if rut_data.get('actividad_secundaria_ciiu'):
                            codigos_ciiu.append(rut_data['actividad_secundaria_ciiu'])
                        if rut_data.get('otras_actividades_ciiu'):
                            codigos_ciiu.append(rut_data['otras_actividades_ciiu'])
                    
                    codigos_ciiu = list(set([c for c in codigos_ciiu if c and c.strip()]))
                    
                    if codigos_ciiu:
                        from ..tasks import procesar_codigos_ciiu_masivo_task
                        procesar_codigos_ciiu_masivo_task.delay(codigos_ciiu)
                    
                    # Procesar responsabilidades
                    codigos_responsabilidades = rut_data.get('responsabilidades_codigos', [])
                    if codigos_responsabilidades:
                        from ..models import ResponsabilidadTributaria
                        from django.db import IntegrityError
                        
                        descripciones_responsabilidades = {
                            '7': 'Retención en la fuente a título de renta',
                            '9': 'Retención en la fuente en el impuesto',
                            '14': 'Informante de exogena',
                            '42': 'Obligado a llevar contabilidad',
                            '47': 'Régimen Simple de Tributación - SIM',
                            '48': 'Impuesto sobre las ventas - IVA',
                            '52': 'Facturador electrónico',
                            '55': 'Informante de Beneficiarios Finales',
                        }
                        
                        for codigo in codigos_responsabilidades:
                            codigo_str = str(codigo).strip()
                            if codigo_str:
                                descripcion = descripciones_responsabilidades.get(
                                    codigo_str,
                                    f'Responsabilidad tributaria código {codigo_str}'
                                )
                                try:
                                    ResponsabilidadTributaria.objects.get_or_create(
                                        codigo=codigo_str,
                                        defaults={'descripcion': descripcion}
                                    )
                                except IntegrityError:
                                    pass
                    
                    # Agregar a exitosos
                    resultados['exitosos'].append({
                        'archivo': pdf_name,
                        'nit': rut.nit,
                        'nit_normalizado': rut.nit_normalizado,
                        'razon_social': rut.razon_social,
                        'empresas_encontradas': empresas.count(),
                        'creado': created
                    })
                    
                except Exception as e:
                    resultados['fallidos'].append({
                        'archivo': pdf_name,
                        'razon': f'Error inesperado: {str(e)}'
                    })
                    continue
            
            # Generar reporte TXT
            resultados['reporte_txt'] = generar_reporte_txt(resultados)
        finally:
            zip_ref.close()
            
    except zipfile.BadZipFile:
        resultados['fallidos'].append({
            'archivo': 'ZIP',
            'razon': 'El archivo no es un ZIP válido'
        })
    except Exception as e:
        resultados['fallidos'].append({
            'archivo': 'ZIP',
            'razon': f'Error al procesar ZIP: {str(e)}'
        })
    
    return resultados


def generar_reporte_txt(resultados: Dict) -> str:
    """Genera un reporte en formato TXT con los RUTs fallidos"""
    reporte = []
    reporte.append("=" * 80)
    reporte.append("REPORTE DE PROCESAMIENTO DE RUTs")
    reporte.append("=" * 80)
    reporte.append("")
    reporte.append(f"Total de archivos procesados: {resultados['total']}")
    reporte.append(f"Exitosos: {len(resultados['exitosos'])}")
    reporte.append(f"Fallidos: {len(resultados['fallidos'])}")
    reporte.append("")
    
    if resultados['exitosos']:
        reporte.append("=" * 80)
        reporte.append("RUTs PROCESADOS EXITOSAMENTE")
        reporte.append("=" * 80)
        reporte.append("")
        for i, exitoso in enumerate(resultados['exitosos'], 1):
            reporte.append(f"{i}. {exitoso['archivo']}")
            reporte.append(f"   NIT: {exitoso['nit']} (Normalizado: {exitoso['nit_normalizado']})")
            reporte.append(f"   Razón Social: {exitoso['razon_social']}")
            reporte.append(f"   Empresas encontradas: {exitoso['empresas_encontradas']}")
            reporte.append(f"   Estado: {'Creado' if exitoso['creado'] else 'Actualizado'}")
            reporte.append("")
    
    if resultados['fallidos']:
        reporte.append("=" * 80)
        reporte.append("RUTs FALLIDOS")
        reporte.append("=" * 80)
        reporte.append("")
        for i, fallido in enumerate(resultados['fallidos'], 1):
            reporte.append(f"{i}. Archivo: {fallido['archivo']}")
            if 'nit' in fallido:
                reporte.append(f"   NIT: {fallido.get('nit', 'N/A')} (Normalizado: {fallido.get('nit_normalizado', 'N/A')})")
            if 'razon_social' in fallido:
                reporte.append(f"   Razón Social: {fallido['razon_social']}")
            reporte.append(f"   Razón del fallo: {fallido['razon']}")
            reporte.append("")
    
    reporte.append("=" * 80)
    reporte.append("FIN DEL REPORTE")
    reporte.append("=" * 80)
    
    return "\n".join(reporte)

