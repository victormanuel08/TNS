"""
Servicio para obtener información completa de códigos CIIU desde la API externa.
Reutiliza la lógica de BCE para obtener datos de actividades económicas.
"""
import aiohttp
import asyncio
from typing import Dict, Optional, List
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# API de CIIU (misma que usa BCE)
CIIU_BUSQUEDA_URL = 'https://enlinea.ccc.org.co/busquedasciiu/bqciiu/busqueda'
CIIU_DETALLES_URL = 'https://enlinea.ccc.org.co/busquedasciiu/bqciiu/actividades/{cseId}'


def _build_payload(codigo_ciiu: str) -> Dict:
    """
    Construye el payload para buscar un código CIIU en la API.
    Similar a la función en BCE.
    """
    return {
        "bdaCriterioBusqueda": codigo_ciiu,
        "bdaDispositivo": "desktop",
        "bdaIp": None,
        "bdaNavegador": "Chrome",
        "bdaQuery": codigo_ciiu,
        "bdaOpcionBusqueda": "codigo_ciiu",
        "bdaLatitud": "7.8972771",
        "bdaLongitud": "-72.4849746",
        "ciiuUsuario": {"usrId": 11294}
    }


async def _make_async_request(payload: Dict) -> Dict:
    """
    Realiza la solicitud asíncrona a la API de búsqueda CIIU.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(CIIU_BUSQUEDA_URL, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Error en API CIIU: status {response.status}")
                    return {'error': f'Error al obtener datos de la API externa: status {response.status}'}
                
                response_data = await response.json()
                return response_data
        except Exception as e:
            logger.error(f"Excepción al consultar API CIIU: {e}", exc_info=True)
            return {'error': str(e)}


async def _get_activity_details(cseId: str) -> Dict:
    """
    Obtiene los detalles completos de una actividad usando su cseId.
    """
    url = CIIU_DETALLES_URL.format(cseId=cseId)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error obteniendo detalles de actividad {cseId}: status {response.status}")
                    return {'error': f'Error al obtener detalles de actividad para cseId {cseId}'}
                
                response_data = await response.json()
                return response_data
        except Exception as e:
            logger.error(f"Excepción al obtener detalles de actividad {cseId}: {e}", exc_info=True)
            return {'error': str(e)}


def obtener_info_ciiu_completa(codigo_ciiu: str) -> Optional[Dict]:
    """
    Obtiene información completa de un código CIIU desde la API externa.
    Retorna un diccionario con todos los datos de la actividad económica.
    
    Args:
        codigo_ciiu: Código CIIU a consultar (ej: "42902")
    
    Returns:
        Dict con información completa o None si hay error
    """
    from asgiref.sync import async_to_sync
    
    # Verificar cache primero
    cache_key = f"ciiu_info_{codigo_ciiu}"
    cached_info = cache.get(cache_key)
    if cached_info:
        logger.debug(f"Info CIIU {codigo_ciiu} encontrada en cache")
        return cached_info
    
    try:
        # Construir payload
        payload = _build_payload(codigo_ciiu)
        
        # Realizar búsqueda
        response_data = async_to_sync(_make_async_request)(payload)
        
        if isinstance(response_data, dict) and 'error' in response_data:
            logger.error(f"Error en API CIIU para {codigo_ciiu}: {response_data['error']}")
            return None
        
        if not isinstance(response_data, list) or len(response_data) == 0:
            logger.warning(f"No se encontraron resultados para código CIIU {codigo_ciiu}")
            return None
        
        # Procesar resultados
        final_data = []
        for item in response_data:
            cseId = item.get('cseId')
            cseCodigo = item.get('cseCodigo', '')
            
            # Solo procesar si el código coincide
            if cseCodigo != codigo_ciiu:
                continue
            
            # Obtener detalles completos
            if cseId:
                activity_details = async_to_sync(_get_activity_details)(cseId)
                
                # Clasificar detalles en "incluye" y "excluye"
                incluye = []
                excluye = []
                
                if isinstance(activity_details, list):
                    incluye = [
                        act for act in activity_details 
                        if isinstance(act, dict) and act.get('actIncluye') == 'S'
                    ]
                    excluye = [
                        act for act in activity_details 
                        if isinstance(act, dict) and act.get('actIncluye') != 'S'
                    ]
                elif isinstance(activity_details, dict) and 'error' not in activity_details:
                    # Si es un solo objeto
                    if activity_details.get('actIncluye') == 'S':
                        incluye = [activity_details]
                    else:
                        excluye = [activity_details]
                
                # Construir objeto completo
                actividad_completa = {
                    'cseCodigo': cseCodigo,
                    'cseDescripcion': item.get('cseDescripcion', ''),
                    'cseTitulo': item.get('cseTitulo', ''),
                    'division': codigo_ciiu[:2] if len(codigo_ciiu) >= 2 else '',
                    'grupo': codigo_ciiu[:3] if len(codigo_ciiu) >= 3 else '',
                    'incluye': incluye,
                    'excluye': excluye,
                    'cseId': cseId
                }
                
                final_data.append(actividad_completa)
        
        if len(final_data) == 0:
            logger.warning(f"No se encontró información completa para código CIIU {codigo_ciiu}")
            return None
        
        # Tomar el primer resultado (debería ser único por código)
        resultado = final_data[0]
        
        # Guardar en cache (7 días, igual que BCE)
        cache.set(cache_key, resultado, timeout=604800)
        
        logger.info(f"Info CIIU {codigo_ciiu} obtenida exitosamente desde API")
        return resultado
        
    except Exception as e:
        logger.error(f"Error obteniendo info CIIU {codigo_ciiu}: {e}", exc_info=True)
        return None


def obtener_o_crear_actividad_economica(codigo_ciiu: str, forzar_actualizacion: bool = False):
    """
    Obtiene o crea una ActividadEconomica. Si no existe, la obtiene de la API.
    Si forzar_actualizacion=True, actualiza la información desde la API.
    
    Args:
        codigo_ciiu: Código CIIU
        forzar_actualizacion: Si True, actualiza la info desde la API aunque exista
    
    Returns:
        ActividadEconomica o None si hay error
    """
    from apps.sistema_analitico.models import ActividadEconomica
    
    # Normalizar código (eliminar espacios)
    codigo_ciiu = codigo_ciiu.strip()
    
    if not codigo_ciiu:
        return None
    
    # Buscar en cache de modelo (7 días)
    cache_key_modelo = f"ciiu_modelo_{codigo_ciiu}"
    actividad_cached = cache.get(cache_key_modelo)
    
    if actividad_cached and not forzar_actualizacion:
        logger.debug(f"ActividadEconomica {codigo_ciiu} encontrada en cache")
        return actividad_cached
    
    # Buscar en BD
    try:
        actividad = ActividadEconomica.objects.get(codigo=codigo_ciiu)
        
        # Si no forzamos actualización y existe, retornar
        if not forzar_actualizacion:
            cache.set(cache_key_modelo, actividad, timeout=604800)
            return actividad
        
        # Si forzamos actualización, obtener info de API
        logger.info(f"Actualizando ActividadEconomica {codigo_ciiu} desde API")
        
    except ActividadEconomica.DoesNotExist:
        actividad = None
        logger.info(f"ActividadEconomica {codigo_ciiu} no existe, creando desde API")
    
    # Obtener información desde API
    info_api = obtener_info_ciiu_completa(codigo_ciiu)
    
    if not info_api:
        # Si no se pudo obtener de API pero existe en BD, retornar la existente
        if actividad:
            return actividad
        # Si no existe, crear una básica
        logger.warning(f"No se pudo obtener info de API para {codigo_ciiu}, creando registro básico")
        actividad = ActividadEconomica.objects.create(
            codigo=codigo_ciiu,
            descripcion=f"Actividad {codigo_ciiu}",
            titulo=f"CIIU {codigo_ciiu}",
            division=codigo_ciiu[:2] if len(codigo_ciiu) >= 2 else '',
            grupo=codigo_ciiu[:3] if len(codigo_ciiu) >= 3 else '',
        )
        cache.set(cache_key_modelo, actividad, timeout=604800)
        return actividad
    
    # Crear o actualizar actividad
    if actividad:
        # Actualizar campos
        actividad.descripcion = info_api.get('cseDescripcion', actividad.descripcion)
        actividad.titulo = info_api.get('cseTitulo', actividad.titulo)
        actividad.division = info_api.get('division', actividad.division)
        actividad.grupo = info_api.get('grupo', actividad.grupo)
        actividad.incluye = info_api.get('incluye', actividad.incluye)
        actividad.excluye = info_api.get('excluye', actividad.excluye)
        actividad.fecha_ultima_consulta_api = timezone.now()
        actividad.save()
    else:
        # Crear nueva
        actividad = ActividadEconomica.objects.create(
            codigo=codigo_ciiu,
            descripcion=info_api.get('cseDescripcion', f"Actividad {codigo_ciiu}"),
            titulo=info_api.get('cseTitulo', f"CIIU {codigo_ciiu}"),
            division=info_api.get('division', codigo_ciiu[:2] if len(codigo_ciiu) >= 2 else ''),
            grupo=info_api.get('grupo', codigo_ciiu[:3] if len(codigo_ciiu) >= 3 else ''),
            incluye=info_api.get('incluye', []),
            excluye=info_api.get('excluye', []),
            fecha_ultima_consulta_api=timezone.now()
        )
    
    # Guardar en cache
    cache.set(cache_key_modelo, actividad, timeout=604800)
    
    logger.info(f"ActividadEconomica {codigo_ciiu} {'actualizada' if actividad.id else 'creada'} exitosamente")
    return actividad

