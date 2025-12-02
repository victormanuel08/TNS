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
