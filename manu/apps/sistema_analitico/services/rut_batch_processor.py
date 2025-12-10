"""
Servicio para procesar múltiples RUTs desde un archivo ZIP
"""
import zipfile
import io
import threading
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import connection, models
from django.db import IntegrityError
from .rut_extractor import extract_rut_data_from_pdf
from ..models import RUT, EmpresaServidor, normalize_nit_and_extract_dv


def normalize_nit(nit: str) -> str:
    """Normaliza NIT eliminando puntos, guiones y espacios"""
    if not nit:
        return ''
    return ''.join(c for c in str(nit) if c.isdigit())


def truncar_campo(valor: str, max_length: int, campo_nombre: str = '') -> Tuple[str, bool]:
    """
    Trunca un campo a max_length y retorna (valor_truncado, fue_truncado).
    Si fue truncado, agrega '...' al final.
    """
    if not valor or len(valor) <= max_length:
        return valor, False
    
    # Truncar dejando espacio para '...'
    valor_truncado = valor[:max_length - 3] + '...'
    return valor_truncado, True


def obtener_razon_social_mejorada(rut_data: Dict) -> str:
    """
    Obtiene la razón social mejorada:
    - Para personas jurídicas: usa razón social (campo 35) directamente
    - Para personas naturales: si razón social está vacía/inválida, construye con campos 31-34
    """
    razon_social = rut_data.get('razon_social', '').strip()
    tipo_contribuyente = rut_data.get('tipo_contribuyente')
    
    # Verificar si la razón social es inválida
    razon_social_invalida = (
        not razon_social or 
        '36. Nombre comercial' in razon_social or 
        '37. Sigla' in razon_social or
        razon_social.startswith('36.') or
        razon_social.startswith('37.')
    )
    
    # Para personas jurídicas: usar razón social directamente (no tocar lo que funciona)
    if tipo_contribuyente == 'persona_juridica':
        if razon_social and not razon_social_invalida:
            return razon_social
        # Si está inválida, intentar nombre comercial o sigla
        nombre_comercial = rut_data.get('nombre_comercial', '').strip()
        if nombre_comercial and nombre_comercial not in ['36. Nombre comercial', '37. Sigla', '']:
            if not nombre_comercial.startswith('36.') and not nombre_comercial.startswith('37.'):
                return nombre_comercial
        sigla = rut_data.get('sigla', '').strip()
        if sigla and sigla not in ['36. Nombre comercial', '37. Sigla', '']:
            if not sigla.startswith('36.') and not sigla.startswith('37.'):
                return sigla
        return razon_social if razon_social else 'Sin razón social'
    
    # Para personas naturales: SIEMPRE construir razón social con campos 31-34 si está vacía/inválida
    # Esta es la lógica original que funcionaba: usar campos 31-34 cuando razón social está vacía
    if tipo_contribuyente == 'persona_natural':
        # Si la razón social está vacía o es inválida, construir con campos 31-34
        if not razon_social or razon_social_invalida:
            # Construir con campos 31-34: Apellidos + Nombres
            pn_apellido1 = rut_data.get('persona_natural_primer_apellido', '').strip()
            pn_apellido2 = rut_data.get('persona_natural_segundo_apellido', '').strip()
            pn_nombre = rut_data.get('persona_natural_primer_nombre', '').strip()
            pn_otros = rut_data.get('persona_natural_otros_nombres', '').strip()
            
            nombre_completo = ' '.join(filter(None, [
                pn_apellido1,
                pn_apellido2,
                pn_nombre,
                pn_otros
            ]))
            
            # Si se pudo construir un nombre completo, usarlo
            if nombre_completo and len(nombre_completo) > 3:
                return nombre_completo
            
            # Fallback: nombre comercial
            nombre_comercial = rut_data.get('nombre_comercial', '').strip()
            if nombre_comercial and nombre_comercial not in ['36. Nombre comercial', '37. Sigla', '']:
                if not nombre_comercial.startswith('36.') and not nombre_comercial.startswith('37.'):
                    return nombre_comercial
            
            # Si no hay nada, usar razón social original si existe, sino "PERSONA NATURAL"
            return razon_social if razon_social else 'PERSONA NATURAL'
        
        # Si la razón social es válida y no está vacía, usarla
        return razon_social
    
    # Si no se determinó el tipo o es otro caso, usar razón social original
    return razon_social if razon_social else 'Sin razón social'


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
            
            # Lock para actualizaciones thread-safe
            lock = threading.Lock()
            procesados_count = {'value': 0}
            
            def procesar_un_rut(pdf_name: str, idx: int) -> Dict:
                """
                Procesa un solo RUT de forma thread-safe.
                Retorna dict con 'exitoso' o 'fallido' y los datos correspondientes.
                """
                import logging
                logger = logging.getLogger(__name__)
                
                # Cada thread necesita su propia conexión de BD
                connection.close()
                
                try:
                    # Leer PDF del ZIP (thread-safe, zipfile maneja esto internamente)
                    pdf_data_bytes = zip_ref.read(pdf_name)
                    
                    # Crear archivo en memoria
                    pdf_file = io.BytesIO(pdf_data_bytes)
                    pdf_file.name = pdf_name
                    
                    # Extraer datos del PDF
                    try:
                        rut_data = extract_rut_data_from_pdf(pdf_file)
                        logger.debug(f"[RUT {pdf_name}] Datos extraídos: NIT={rut_data.get('nit_normalizado')}, "
                                   f"Razón Social Original='{rut_data.get('razon_social', '')[:50]}...', "
                                   f"Tipo={rut_data.get('tipo_contribuyente')}")
                    except Exception as e:
                        logger.error(f"[RUT {pdf_name}] Error al extraer datos del PDF: {str(e)}", exc_info=True)
                        return {
                            'tipo': 'fallido',
                            'archivo': pdf_name,
                            'razon': f'Error al extraer datos del PDF: {str(e)}'
                        }
                    
                    # Obtener NIT
                    nit_normalizado = rut_data.get('nit_normalizado')
                    if not nit_normalizado:
                        logger.warning(f"[RUT {pdf_name}] No se pudo detectar el NIT del PDF")
                        return {
                            'tipo': 'fallido',
                            'archivo': pdf_name,
                            'razon': 'No se pudo detectar el NIT del PDF. Por favor, proporciona el NIT manualmente.'
                        }
                    
                    # Obtener razón social mejorada
                    # 🔍 LOG DETALLADO: Mostrar qué se extrajo del PDF
                    tipo_contribuyente = rut_data.get('tipo_contribuyente', 'NO_DETECTADO')
                    razon_social_raw = rut_data.get('razon_social', '').strip()
                    
                    logger.info(f"[RUT {pdf_name}] 🔍 EXTRACCIÓN DEL PDF:")
                    logger.info(f"  • Tipo Contribuyente: {tipo_contribuyente}")
                    logger.info(f"  • Razón Social (campo 35): '{razon_social_raw}'")
                    
                    if tipo_contribuyente == 'persona_natural':
                        pn_apellido1 = rut_data.get('persona_natural_primer_apellido', '').strip()
                        pn_apellido2 = rut_data.get('persona_natural_segundo_apellido', '').strip()
                        pn_nombre = rut_data.get('persona_natural_primer_nombre', '').strip()
                        pn_otros = rut_data.get('persona_natural_otros_nombres', '').strip()
                        logger.info(f"  • Campo 31 (Primer Apellido): '{pn_apellido1}'")
                        logger.info(f"  • Campo 32 (Segundo Apellido): '{pn_apellido2}'")
                        logger.info(f"  • Campo 33 (Primer Nombre): '{pn_nombre}'")
                        logger.info(f"  • Campo 34 (Otros Nombres): '{pn_otros}'")
                    
                    razon_social_mejorada = obtener_razon_social_mejorada(rut_data)
                    logger.info(f"[RUT {pdf_name}] ✅ Razón Social Final: '{razon_social_mejorada}'")
                    
                    # Verificar si hay empresas asociadas
                    empresas = EmpresaServidor.objects.filter(nit_normalizado=nit_normalizado)
                    empresas_count = empresas.count()
                    sin_empresas = empresas_count == 0
                    
                    if sin_empresas:
                        logger.warning(f"[RUT {pdf_name}] NIT {nit_normalizado} no tiene empresas asociadas, pero se creará el RUT")
                    
                    # Buscar o crear RUT (ahora se crea aunque no tenga empresas)
                    razon_social_final, _ = truncar_campo(razon_social_mejorada, 255, 'razon_social')
                    
                    # Truncar TODOS los campos antes de crear/actualizar el RUT
                    campos_truncados = []
                    rut_data_truncado = {}
                    
                    # Obtener todos los campos del modelo RUT para verificar max_length
                    rut_model_fields = {f.name: f for f in RUT._meta.get_fields() 
                                       if hasattr(f, 'max_length') and f.max_length}
                    
                    # Truncar todos los campos de rut_data antes de asignarlos
                    for key, value in rut_data.items():
                        if key in ['_texto_completo', '_codigos_ciiu_encontrados', '_establecimientos']:
                            rut_data_truncado[key] = value
                            continue
                        
                        if value is None:
                            rut_data_truncado[key] = None
                        elif isinstance(value, str) and value:
                            # Verificar si el campo existe en el modelo y tiene max_length
                            if key in rut_model_fields:
                                field = rut_model_fields[key]
                                max_length = field.max_length
                                
                                if len(value) > max_length:
                                    valor_truncado, fue_truncado = truncar_campo(value, max_length, key)
                                    rut_data_truncado[key] = valor_truncado
                                    if fue_truncado:
                                        campos_truncados.append(f"{key} (truncado a {max_length} caracteres)")
                                        logger.warning(f"[RUT {pdf_name}] Campo '{key}' truncado: {len(value)} → {max_length} chars. "
                                                    f"Original: '{value[:100]}...' → Truncado: '{valor_truncado}'")
                                else:
                                    rut_data_truncado[key] = value
                            else:
                                # Si no está en el modelo, dejarlo como está
                                rut_data_truncado[key] = value
                        else:
                            rut_data_truncado[key] = value
                    
                    # Crear o actualizar RUT con datos ya truncados
                    # Manejar condiciones de carrera con try-except y reintentos
                    # ✅ IMPORTANTE: Si el nit_normalizado cambió (ej: de 10050386382 a 1005038638),
                    # buscar también por el NIT original para encontrar el RUT existente
                    rut = None
                    created = False
                    max_retries = 5  # Aumentar intentos
                    import time
                    
                    # Primero intentar buscar por el nit_normalizado actual
                    rut_existente = RUT.objects.filter(nit_normalizado=nit_normalizado).first()
                    
                    # Si no se encuentra, buscar por el NIT original (puede que el nit_normalizado haya cambiado)
                    if not rut_existente:
                        nit_original = rut_data_truncado.get('nit', '')
                        if nit_original:
                            # Intentar normalizar el NIT original de diferentes formas
                            nit_norm_alt, _, _ = normalize_nit_and_extract_dv(nit_original)
                            if nit_norm_alt != nit_normalizado:
                                rut_existente = RUT.objects.filter(nit_normalizado=nit_norm_alt).first()
                    
                    for attempt in range(max_retries):
                        try:
                            if rut_existente:
                                # Si existe, actualizar
                                rut = rut_existente
                                created = False
                                # Actualizar nit_normalizado si cambió
                                if rut.nit_normalizado != nit_normalizado:
                                    # Si el nit_normalizado cambió, necesitamos actualizar el registro
                                    # Pero como nit_normalizado es unique, primero debemos verificar que no exista otro
                                    otro_rut = RUT.objects.filter(nit_normalizado=nit_normalizado).exclude(id=rut.id).first()
                                    if otro_rut:
                                        # Si existe otro RUT con el nuevo nit_normalizado, eliminar el viejo y usar el nuevo
                                        logger.warning(f"[RUT {pdf_name}] Existe otro RUT con nit_normalizado={nit_normalizado}, usando ese")
                                        rut = otro_rut
                                        created = False
                                    else:
                                        # Actualizar el nit_normalizado
                                        rut.nit_normalizado = nit_normalizado
                            else:
                                # Si no existe, crear nuevo
                                rut, created = RUT.objects.update_or_create(
                                    nit_normalizado=nit_normalizado,
                                    defaults={
                                        'nit': rut_data_truncado.get('nit', nit_normalizado),
                                        'dv': rut_data_truncado.get('dv', ''),
                                        'razon_social': razon_social_final,
                                    }
                                )
                            break  # Éxito, salir del loop
                        except IntegrityError as e:
                            # Si hay duplicado (condición de carrera), esperar un poco y buscar el existente
                            logger.debug(f"[RUT {pdf_name}] IntegrityError en intento {attempt + 1}: {str(e)}")
                            
                            # Esperar un poco para que la transacción del otro thread se complete
                            time.sleep(0.2 * (attempt + 1))
                            
                            # Intentar obtener el RUT existente de múltiples maneras
                            rut = RUT.objects.filter(nit_normalizado=nit_normalizado).first()
                            
                            if not rut:
                                # Si no se encuentra, puede ser que el nit_normalizado cambió durante normalización
                                # Intentar buscar por el NIT original también
                                nit_original = rut_data_truncado.get('nit', nit_normalizado)
                                if nit_original and nit_original != nit_normalizado:
                                    nit_norm_alt, _, _ = normalize_nit_and_extract_dv(nit_original)
                                    if nit_norm_alt != nit_normalizado:
                                        rut = RUT.objects.filter(nit_normalizado=nit_norm_alt).first()
                            
                            if rut:
                                created = False
                                break  # Encontrado, salir del loop
                            
                            # Si después de varios intentos no se encuentra, intentar usar get_or_create
                            if attempt >= max_retries - 1:
                                # Último intento: usar get_or_create que es más robusto
                                try:
                                    rut, created = RUT.objects.get_or_create(
                                        nit_normalizado=nit_normalizado,
                                        defaults={
                                            'nit': rut_data_truncado.get('nit', nit_normalizado),
                                            'dv': rut_data_truncado.get('dv', ''),
                                            'razon_social': razon_social_final,
                                        }
                                    )
                                    break
                                except IntegrityError:
                                    # Si aún falla, buscar una vez más
                                    rut = RUT.objects.filter(nit_normalizado=nit_normalizado).first()
                                    if rut:
                                        created = False
                                        break
                    
                    # Si después de todos los intentos no se encontró, lanzar error con más detalles
                    if not rut:
                        # Intentar una búsqueda final más amplia
                        rut = RUT.objects.filter(nit_normalizado=nit_normalizado).first()
                        if not rut:
                            nit_original = rut_data_truncado.get('nit', nit_normalizado)
                            if nit_original:
                                nit_norm_alt, _, _ = normalize_nit_and_extract_dv(nit_original)
                                if nit_norm_alt != nit_normalizado:
                                    rut = RUT.objects.filter(nit_normalizado=nit_norm_alt).first()
                        
                        if not rut:
                            raise Exception(
                                f"No se pudo crear ni obtener RUT con nit_normalizado={nit_normalizado} "
                                f"(NIT original: {rut_data_truncado.get('nit', 'N/A')}) después de {max_retries} intentos. "
                                f"Esto puede indicar un problema de normalización o una condición de carrera persistente."
                            )
                    
                    # Actualizar campos desde PDF (ya truncados)
                    # Asegurar que todos los campos se trunquen antes de asignar
                    for key, value in rut_data_truncado.items():
                        if key not in ['_texto_completo', '_codigos_ciiu_encontrados', '_establecimientos'] and hasattr(rut, key):
                            try:
                                # Obtener el campo del modelo para verificar max_length
                                field = rut._meta.get_field(key)
                                if isinstance(field, models.CharField) and value:
                                    # Truncar si excede max_length
                                    if field.max_length and len(str(value)) > field.max_length:
                                        value = str(value)[:field.max_length]
                                        logger.warning(f"[RUT {pdf_name}] Campo '{key}' truncado a {field.max_length} caracteres")
                                setattr(rut, key, value)
                            except (AttributeError, ValueError) as e:
                                logger.error(f"[RUT {pdf_name}] Error asignando campo '{key}': {str(e)}")
                                # Continuar con el siguiente campo
                            except Exception as e:
                                # Para otros errores (como campos que no existen), solo loguear
                                logger.debug(f"[RUT {pdf_name}] Campo '{key}' no se pudo asignar: {str(e)}")
                                pass
                    
                    # Actualizar razón social si fue mejorada
                    if razon_social_mejorada != rut_data.get('razon_social', ''):
                        rut.razon_social = razon_social_final
                    
                    # Guardar campos 31-34 en informacion_adicional para persona natural
                    if rut_data.get('tipo_contribuyente') == 'persona_natural':
                        if not rut.informacion_adicional:
                            rut.informacion_adicional = {}
                        rut.informacion_adicional.update({
                            'persona_natural_primer_apellido': rut_data.get('persona_natural_primer_apellido', ''),
                            'persona_natural_segundo_apellido': rut_data.get('persona_natural_segundo_apellido', ''),
                            'persona_natural_primer_nombre': rut_data.get('persona_natural_primer_nombre', ''),
                            'persona_natural_otros_nombres': rut_data.get('persona_natural_otros_nombres', ''),
                        })
                    
                    # Guardar PDF
                    pdf_file.seek(0)
                    if rut.archivo_pdf:
                        rut.archivo_pdf.delete(save=False)
                    
                    pdf_upload = InMemoryUploadedFile(
                        pdf_file,
                        None,
                        pdf_name,
                        'application/pdf',
                        len(pdf_data_bytes),
                        None
                    )
                    rut.archivo_pdf = pdf_upload
                    # Guardar RUT, manejando posibles errores de duplicados en procesamiento paralelo
                    try:
                        rut.save()
                    except IntegrityError as e:
                        # Si hay duplicado (otro thread lo creó), obtener el existente y actualizar
                        # Usar el nit_normalizado del objeto rut (ya normalizado) en caso de que haya cambiado
                        nit_actual = getattr(rut, 'nit_normalizado', nit_normalizado)
                        # Intentar obtener el RUT existente usando filter().first() para evitar DoesNotExist
                        rut = RUT.objects.filter(nit_normalizado=nit_actual).first()
                        if not rut:
                            # Si no existe con ese nit_normalizado, usar el original
                            rut = RUT.objects.filter(nit_normalizado=nit_normalizado).first()
                        if not rut:
                            # Si realmente no existe, reintentar update_or_create
                            rut, _ = RUT.objects.update_or_create(
                                nit_normalizado=nit_normalizado,
                                defaults={
                                    'nit': rut_data_truncado.get('nit', nit_normalizado),
                                    'dv': rut_data_truncado.get('dv', ''),
                                    'razon_social': razon_social_final,
                                }
                            )
                        
                        # Re-asignar campos actualizados
                        for key, value in rut_data_truncado.items():
                            if key not in ['_texto_completo', '_codigos_ciiu_encontrados', '_establecimientos'] and hasattr(rut, key):
                                try:
                                    field = rut._meta.get_field(key)
                                    if isinstance(field, models.CharField) and value:
                                        if field.max_length and len(str(value)) > field.max_length:
                                            value = str(value)[:field.max_length]
                                    setattr(rut, key, value)
                                except (AttributeError, ValueError, Exception):
                                    pass
                        rut.archivo_pdf = pdf_upload
                        rut.razon_social = razon_social_final
                        # Actualizar informacion_adicional si es persona natural
                        if rut_data.get('tipo_contribuyente') == 'persona_natural':
                            if not rut.informacion_adicional:
                                rut.informacion_adicional = {}
                            rut.informacion_adicional.update({
                                'persona_natural_primer_apellido': rut_data.get('persona_natural_primer_apellido', ''),
                                'persona_natural_segundo_apellido': rut_data.get('persona_natural_segundo_apellido', ''),
                                'persona_natural_primer_nombre': rut_data.get('persona_natural_primer_nombre', ''),
                                'persona_natural_otros_nombres': rut_data.get('persona_natural_otros_nombres', ''),
                            })
                        rut.save()
                    
                    # Procesar establecimientos
                    from ..models import EstablecimientoRUT
                    establecimientos_data = rut_data.get('_establecimientos', [])
                    EstablecimientoRUT.objects.filter(rut=rut).delete()
                    for est_data in establecimientos_data:
                        # Truncar campos de EstablecimientoRUT antes de crear
                        est_nombre = est_data.get('nombre', '')
                        est_tipo = est_data.get('tipo_establecimiento', '')
                        est_departamento = est_data.get('departamento_nombre', '')
                        est_ciudad = est_data.get('ciudad_nombre', '')
                        est_direccion = est_data.get('direccion', '')
                        
                        # Truncar según max_length del modelo
                        if len(est_nombre) > 255:
                            est_nombre = est_nombre[:255]
                            logger.warning(f"[RUT {pdf_name}] Campo 'nombre' de establecimiento truncado a 255 caracteres")
                        if est_tipo and len(est_tipo) > 100:
                            est_tipo = est_tipo[:100]
                            logger.warning(f"[RUT {pdf_name}] Campo 'tipo_establecimiento' truncado a 100 caracteres")
                        if est_departamento and len(est_departamento) > 100:
                            est_departamento = est_departamento[:100]
                            logger.warning(f"[RUT {pdf_name}] Campo 'departamento_nombre' de establecimiento truncado a 100 caracteres")
                        if est_ciudad and len(est_ciudad) > 100:
                            est_ciudad = est_ciudad[:100]
                            logger.warning(f"[RUT {pdf_name}] Campo 'ciudad_nombre' de establecimiento truncado a 100 caracteres")
                        
                        EstablecimientoRUT.objects.create(
                            rut=rut,
                            nombre=est_nombre,
                            tipo_establecimiento=est_tipo,
                            tipo_establecimiento_codigo=est_data.get('tipo_establecimiento_codigo'),
                            actividad_economica_ciiu=est_data.get('actividad_economica_ciiu'),
                            actividad_economica_descripcion=est_data.get('actividad_economica_descripcion'),
                            departamento_codigo=est_data.get('departamento_codigo'),
                            departamento_nombre=est_departamento,
                            ciudad_codigo=est_data.get('ciudad_codigo'),
                            ciudad_nombre=est_ciudad,
                            direccion=est_direccion,
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
                    
                    # Mensaje de advertencia si hay campos truncados
                    advertencia = ''
                    if campos_truncados:
                        advertencia = f" (Campos truncados: {', '.join(campos_truncados)})"
                    
                    # Si no tiene empresas, marcar como exitoso pero con advertencia
                    if sin_empresas:
                        return {
                            'tipo': 'exitoso',
                            'archivo': pdf_name,
                            'nit': rut.nit,
                            'nit_normalizado': rut.nit_normalizado,
                            'razon_social': rut.razon_social,
                            'empresas_encontradas': 0,
                            'creado': created,
                            'advertencia': f'RUT creado pero sin empresas asociadas{advertencia}'
                        }
                    
                    return {
                        'tipo': 'exitoso',
                        'archivo': pdf_name,
                        'nit': rut.nit,
                        'nit_normalizado': rut.nit_normalizado,
                        'razon_social': rut.razon_social,
                        'empresas_encontradas': empresas_count,
                        'creado': created,
                        'advertencia': advertencia if campos_truncados else None
                    }
                    
                except Exception as e:
                    logger.error(f"[RUT {pdf_name}] Error inesperado al procesar RUT: {str(e)}", exc_info=True)
                    return {
                        'tipo': 'fallido',
                        'archivo': pdf_name,
                        'razon': f'Error inesperado: {str(e)}'
                    }
            
            # Procesar PDFs en paralelo (máximo 5 workers para no sobrecargar)
            max_workers = min(5, len(pdf_files))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Enviar todas las tareas
                future_to_pdf = {
                    executor.submit(procesar_un_rut, pdf_name, idx): pdf_name 
                    for idx, pdf_name in enumerate(pdf_files, 1)
                }
                
                # Procesar resultados conforme se completan
                for future in as_completed(future_to_pdf):
                    pdf_name = future_to_pdf[future]
                    try:
                        resultado = future.result()
                        
                        # Agregar resultado de forma thread-safe
                        with lock:
                            if resultado['tipo'] == 'exitoso':
                                resultados['exitosos'].append({
                                    'archivo': resultado['archivo'],
                                    'nit': resultado['nit'],
                                    'nit_normalizado': resultado['nit_normalizado'],
                                    'razon_social': resultado['razon_social'],
                                    'empresas_encontradas': resultado['empresas_encontradas'],
                                    'creado': resultado['creado']
                                })
                            else:
                                fallido = {'archivo': resultado['archivo'], 'razon': resultado['razon']}
                                if 'nit' in resultado:
                                    fallido['nit'] = resultado['nit']
                                if 'nit_normalizado' in resultado:
                                    fallido['nit_normalizado'] = resultado['nit_normalizado']
                                if 'razon_social' in resultado:
                                    fallido['razon_social'] = resultado['razon_social']
                                resultados['fallidos'].append(fallido)
                            
                            # Actualizar contador y progreso
                            procesados_count['value'] += 1
                            
                            # Actualizar progreso en Celery (thread-safe)
                            if task:
                                try:
                                    task.update_state(
                                        state='PROCESSING',
                                        meta={
                                            'status': f'Procesando {procesados_count["value"]}/{len(pdf_files)}: {pdf_name}',
                                            'total': len(pdf_files),
                                            'procesados': procesados_count['value'],
                                            'exitosos': len(resultados['exitosos']),
                                            'fallidos': len(resultados['fallidos'])
                                        }
                                    )
                                except Exception:
                                    # Si falla actualizar estado, continuar de todas formas
                                    pass
                    
                    except Exception as e:
                        # Error al obtener resultado del future
                        with lock:
                            resultados['fallidos'].append({
                                'archivo': pdf_name,
                                'razon': f'Error procesando future: {str(e)}'
                            })
                            procesados_count['value'] += 1
            
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
            if exitoso.get('advertencia'):
                reporte.append(f"   ⚠️ Advertencia: {exitoso['advertencia']}")
            reporte.append("")
    
    if resultados['fallidos']:
        # Agrupar fallidos por tipo de error
        fallidos_por_tipo = {}
        for fallido in resultados['fallidos']:
            razon = fallido.get('razon', 'Error desconocido')
            tipo_error = 'Otros errores'
            
            if 'No se pudo detectar el NIT' in razon:
                tipo_error = 'NIT no detectado'
            elif 'Error al extraer datos del PDF' in razon:
                tipo_error = 'Error de extracción de PDF'
            elif 'Error inesperado' in razon:
                tipo_error = 'Error inesperado'
            elif 'Error procesando future' in razon:
                tipo_error = 'Error de procesamiento'
            
            if tipo_error not in fallidos_por_tipo:
                fallidos_por_tipo[tipo_error] = []
            fallidos_por_tipo[tipo_error].append(fallido)
        
        # Resumen de estadísticas
        reporte.append("=" * 80)
        reporte.append("RESUMEN DE FALLIDOS POR TIPO")
        reporte.append("=" * 80)
        reporte.append("")
        for tipo, lista in fallidos_por_tipo.items():
            reporte.append(f"  {tipo}: {len(lista)} archivos")
        reporte.append("")
        
        # Detalle de fallidos agrupados
        reporte.append("=" * 80)
        reporte.append("DETALLE DE RUTs FALLIDOS")
        reporte.append("=" * 80)
        reporte.append("")
        
        contador = 1
        for tipo_error, lista_fallidos in sorted(fallidos_por_tipo.items()):
            reporte.append(f"\n--- {tipo_error.upper()} ({len(lista_fallidos)} archivos) ---")
            reporte.append("")
            for fallido in lista_fallidos:
                reporte.append(f"{contador}. Archivo: {fallido['archivo']}")
                if 'nit' in fallido:
                    reporte.append(f"   NIT: {fallido.get('nit', 'N/A')} (Normalizado: {fallido.get('nit_normalizado', 'N/A')})")
                if 'razon_social' in fallido:
                    reporte.append(f"   Razón Social: {fallido['razon_social']}")
                reporte.append(f"   Razón del fallo: {fallido['razon']}")
                reporte.append("")
                contador += 1
    
    reporte.append("=" * 80)
    reporte.append("FIN DEL REPORTE")
    reporte.append("=" * 80)
    
    return "\n".join(reporte)

