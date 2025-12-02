"""
Tareas Celery para procesamiento asíncrono
"""
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='sistema_analitico.procesar_factura_dian')
def procesar_factura_dian_task(self, nit_normalizado, kardex_id, empresa_servidor_id=None):
    """
    Tarea Celery para procesar factura electrónica DIAN de forma asíncrona
    
    Args:
        nit_normalizado: NIT de la empresa (normalizado)
        kardex_id: ID del documento a procesar
        empresa_servidor_id: ID de la empresa (opcional)
    
    Returns:
        dict con resultado del procesamiento
    """
    from .services.dian_processor import procesar_factura_dian
    
    try:
        logger.info(f"Iniciando procesamiento de factura DIAN: NIT={nit_normalizado}, KardexID={kardex_id}")
        
        # Actualizar estado de la tarea
        self.update_state(
            state='PROCESSING',
            meta={
                'nit': nit_normalizado,
                'kardex_id': kardex_id,
                'status': 'Procesando factura...'
            }
        )
        
        # Procesar factura
        resultado = procesar_factura_dian(nit_normalizado, kardex_id, empresa_servidor_id)
        
        if resultado.get('success'):
            logger.info(f"Factura procesada exitosamente: CUFE={resultado.get('cufe')}")
            return {
                'status': 'SUCCESS',
                'cufe': resultado.get('cufe'),
                'mensaje': resultado.get('mensaje', 'Documento procesado exitosamente')
            }
        else:
            logger.error(f"Error procesando factura: {resultado.get('error')}")
            return {
                'status': 'FAILED',
                'error': resultado.get('error', 'Error desconocido'),
                'cufe': resultado.get('cufe', '')
            }
    
    except Exception as e:
        logger.error(f"Excepción en tarea Celery: {e}", exc_info=True)
        return {
            'status': 'ERROR',
            'error': str(e)
        }


@shared_task(bind=True, name='sistema_analitico.descubrir_empresas')
def descubrir_empresas_task(self, servidor_id):
    """
    Tarea Celery para descubrir empresas en un servidor de forma asíncrona
    
    Args:
        servidor_id: ID del servidor donde se buscarán las empresas
    
    Returns:
        dict con resultado del descubrimiento
    """
    from .services.data_manager import DataManager
    from .models import Servidor
    
    try:
        logger.info(f"Iniciando descubrimiento de empresas: servidor_id={servidor_id}")
        
        # Obtener servidor
        try:
            servidor = Servidor.objects.get(id=servidor_id)
        except Servidor.DoesNotExist:
            return {
                'status': 'ERROR',
                'error': f'Servidor con ID {servidor_id} no existe'
            }
        
        # Actualizar estado de la tarea
        self.update_state(
            state='PROCESSING',
            meta={
                'servidor_id': servidor_id,
                'servidor_nombre': servidor.nombre,
                'status': 'Conectando al servidor...',
                'empresas_encontradas': 0
            }
        )
        
        # Descubrir empresas
        data_manager = DataManager()
        empresas = data_manager.descubrir_empresas(servidor_id)
        
        logger.info(f"Descubrimiento completado: {len(empresas)} empresas encontradas")
        
        return {
            'status': 'SUCCESS',
            'servidor_id': servidor_id,
            'servidor_nombre': servidor.nombre,
            'total_empresas': len(empresas),
            'empresas': empresas,
            'mensaje': f'Se encontraron {len(empresas)} empresas en el servidor {servidor.nombre}'
        }
    
    except Exception as e:
        logger.error(f"Excepción en tarea descubrir_empresas: {e}", exc_info=True)
        return {
            'status': 'ERROR',
            'error': str(e),
            'servidor_id': servidor_id
        }


@shared_task(bind=True, name='sistema_analitico.obtener_info_ciiu')
def obtener_info_ciiu_task(self, codigo_ciiu: str, forzar_actualizacion: bool = False):
    """
    Tarea Celery para obtener información completa de un código CIIU desde la API externa
    y guardarla en la base de datos y cache.
    
    Args:
        codigo_ciiu: Código CIIU a consultar (ej: "42902")
        forzar_actualizacion: Si True, actualiza la info aunque ya exista
    
    Returns:
        dict con resultado del procesamiento
    """
    from .services.ciiu_service import obtener_o_crear_actividad_economica
    
    try:
        logger.info(f"Iniciando obtención de info CIIU: código={codigo_ciiu}")
        
        # Actualizar estado de la tarea
        self.update_state(
            state='PROCESSING',
            meta={
                'codigo_ciiu': codigo_ciiu,
                'status': 'Obteniendo información de la API...'
            }
        )
        
        # Obtener o crear actividad económica
        actividad = obtener_o_crear_actividad_economica(
            codigo_ciiu=codigo_ciiu,
            forzar_actualizacion=forzar_actualizacion
        )
        
        if actividad:
            logger.info(f"Info CIIU {codigo_ciiu} obtenida exitosamente")
            return {
                'status': 'SUCCESS',
                'codigo_ciiu': codigo_ciiu,
                'actividad_id': actividad.id,
                'descripcion': actividad.descripcion,
                'titulo': actividad.titulo,
                'mensaje': f'Información de CIIU {codigo_ciiu} obtenida y guardada exitosamente'
            }
        else:
            logger.error(f"No se pudo obtener info CIIU {codigo_ciiu}")
            return {
                'status': 'FAILED',
                'codigo_ciiu': codigo_ciiu,
                'error': 'No se pudo obtener información de la API'
            }
    
    except Exception as e:
        logger.error(f"Excepción en tarea obtener_info_ciiu: {e}", exc_info=True)
        return {
            'status': 'ERROR',
            'codigo_ciiu': codigo_ciiu,
            'error': str(e)
        }


@shared_task(bind=True, name='sistema_analitico.procesar_codigos_ciiu_masivo')
def procesar_codigos_ciiu_masivo_task(self, codigos_ciiu: list):
    """
    Tarea Celery para procesar múltiples códigos CIIU en paralelo.
    
    Args:
        codigos_ciiu: Lista de códigos CIIU a procesar
    
    Returns:
        dict con resultados de todos los códigos procesados
    """
    from .tasks import obtener_info_ciiu_task
    
    try:
        logger.info(f"Iniciando procesamiento masivo de {len(codigos_ciiu)} códigos CIIU")
        
        # Actualizar estado
        self.update_state(
            state='PROCESSING',
            meta={
                'total': len(codigos_ciiu),
                'procesados': 0,
                'status': 'Iniciando procesamiento...'
            }
        )
        
        # Procesar códigos (pueden ejecutarse en paralelo)
        resultados = []
        tareas = []
        
        for codigo in codigos_ciiu:
            if codigo and codigo.strip():
                # Crear tarea para cada código
                task = obtener_info_ciiu_task.delay(codigo.strip())
                tareas.append((codigo.strip(), task))
        
        # Esperar resultados (con timeout)
        for codigo, task in tareas:
            try:
                resultado = task.get(timeout=30)  # Timeout de 30 segundos por código
                resultados.append({
                    'codigo': codigo,
                    'resultado': resultado
                })
            except Exception as e:
                logger.error(f"Error procesando código CIIU {codigo}: {e}")
                resultados.append({
                    'codigo': codigo,
                    'resultado': {
                        'status': 'ERROR',
                        'error': str(e)
                    }
                })
        
        exitosos = sum(1 for r in resultados if r['resultado'].get('status') == 'SUCCESS')
        
        logger.info(f"Procesamiento masivo completado: {exitosos}/{len(resultados)} exitosos")
        
        return {
            'status': 'SUCCESS',
            'total': len(resultados),
            'exitosos': exitosos,
            'fallidos': len(resultados) - exitosos,
            'resultados': resultados
        }
    
    except Exception as e:
        logger.error(f"Excepción en tarea procesar_codigos_ciiu_masivo: {e}", exc_info=True)
        return {
            'status': 'ERROR',
            'error': str(e),
            'total': len(codigos_ciiu) if codigos_ciiu else 0
        }