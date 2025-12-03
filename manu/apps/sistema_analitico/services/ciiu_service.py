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


async def obtener_info_ciiu_completa_async(codigo_ciiu: str, forzar_consulta_api: bool = False) -> Optional[Dict]:
    """
    Versión ASYNC pura de obtener_info_ciiu_completa.
    Usa directamente aiohttp sin async_to_sync, mucho más rápido.
    
    Args:
        codigo_ciiu: Código CIIU a consultar (ej: "42902")
        forzar_consulta_api: Si True, ignora el cache y consulta la API directamente
    
    Returns:
        Dict con información completa o None si hay error
    """
    # Verificar cache primero (solo si no forzamos consulta)
    if not forzar_consulta_api:
        cache_key = f"ciiu_info_{codigo_ciiu}"
        cached_info = cache.get(cache_key)
        if cached_info:
            logger.debug(f"Info CIIU {codigo_ciiu} encontrada en cache")
            return cached_info
    else:
        logger.info(f"Forzando consulta a API para código CIIU: {codigo_ciiu} (ignorando cache)")
    
    try:
        # Construir payload
        payload = _build_payload(codigo_ciiu)
        
        # Realizar búsqueda (async directo, sin async_to_sync)
        response_data = await _make_async_request(payload)
        
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
            
            # Obtener detalles completos (async directo)
            if cseId:
                activity_details = await _get_activity_details(cseId)
                
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
        cache_key = f"ciiu_info_{codigo_ciiu}"
        cache.set(cache_key, resultado, timeout=604800)
        
        logger.info(f"Info CIIU {codigo_ciiu} obtenida exitosamente desde API (async)")
        return resultado
        
    except Exception as e:
        logger.error(f"Error obteniendo info CIIU {codigo_ciiu}: {e}", exc_info=True)
        return None


def obtener_info_ciiu_completa(codigo_ciiu: str, forzar_consulta_api: bool = False) -> Optional[Dict]:
    """
    Obtiene información completa de un código CIIU desde la API externa.
    Retorna un diccionario con todos los datos de la actividad económica.
    
    Args:
        codigo_ciiu: Código CIIU a consultar (ej: "42902")
        forzar_consulta_api: Si True, ignora el cache y consulta la API directamente
    
    Returns:
        Dict con información completa o None si hay error
    """
    from asgiref.sync import async_to_sync
    
    # Verificar cache primero (solo si no forzamos consulta)
    if not forzar_consulta_api:
        cache_key = f"ciiu_info_{codigo_ciiu}"
        cached_info = cache.get(cache_key)
        if cached_info:
            logger.debug(f"Info CIIU {codigo_ciiu} encontrada en cache")
            return cached_info
    else:
        logger.info(f"Forzando consulta a API para código CIIU: {codigo_ciiu} (ignorando cache)")
    
    try:
        # Construir payload
        payload = _build_payload(codigo_ciiu)
        
        # Realizar búsqueda (usar async_to_sync para compatibilidad con código síncrono)
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
            
            # Obtener detalles completos (usar async_to_sync para compatibilidad)
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
    Obtiene o crea una ActividadEconomica. Si no existe en BD, SIEMPRE consulta la API.
    Similar a cómo funciona en BCE: busca en cache, luego en BD, y si no existe, consulta API.
    
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
    
    # Buscar en BD primero (como BCE)
    actividad = None
    try:
        actividad = ActividadEconomica.objects.get(codigo=codigo_ciiu)
        
        # Si existe en BD y no forzamos actualización, retornar (pero verificar cache de API)
        if not forzar_actualizacion:
            # Verificar si tiene fecha_ultima_consulta_api reciente (menos de 7 días)
            if actividad.fecha_ultima_consulta_api:
                from datetime import timedelta
                dias_desde_consulta = (timezone.now() - actividad.fecha_ultima_consulta_api).days
                if dias_desde_consulta < 7:
                    # Cache del modelo
                    cache_key_modelo = f"ciiu_modelo_{codigo_ciiu}"
                    cache.set(cache_key_modelo, actividad, timeout=604800)
                    logger.debug(f"ActividadEconomica {codigo_ciiu} encontrada en BD (consulta reciente)")
                    return actividad
            
            # Si no tiene consulta reciente, actualizar desde API
            logger.info(f"ActividadEconomica {codigo_ciiu} existe pero necesita actualización desde API")
        
        # Si forzamos actualización, obtener info de API
        if forzar_actualizacion:
            logger.info(f"Actualizando ActividadEconomica {codigo_ciiu} desde API (forzado)")
        
    except ActividadEconomica.DoesNotExist:
        actividad = None
        logger.info(f"ActividadEconomica {codigo_ciiu} no existe en BD, consultando API para crearla")
    
    # SIEMPRE consultar API si no existe en BD o si forzamos actualización
    # (obtener_info_ciiu_completa maneja su propio cache, pero si no existe en BD, debemos consultar)
    logger.info(f"Consultando API externa para código CIIU: {codigo_ciiu}")
    info_api = obtener_info_ciiu_completa(codigo_ciiu, forzar_consulta_api=(actividad is None or forzar_actualizacion))
    
    if not info_api:
        # Si no se pudo obtener de API pero existe en BD, retornar la existente
        if actividad:
            logger.warning(f"No se pudo obtener info de API para {codigo_ciiu}, usando datos existentes en BD")
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
        cache_key_modelo = f"ciiu_modelo_{codigo_ciiu}"
        cache.set(cache_key_modelo, actividad, timeout=604800)
        return actividad
    
    # Crear o actualizar actividad con datos de API
    if actividad:
        # Actualizar campos desde API
        actividad.descripcion = info_api.get('cseDescripcion', actividad.descripcion)
        actividad.titulo = info_api.get('cseTitulo', actividad.titulo)
        actividad.division = info_api.get('division', actividad.division)
        actividad.grupo = info_api.get('grupo', actividad.grupo)
        actividad.incluye = info_api.get('incluye', actividad.incluye)
        actividad.excluye = info_api.get('excluye', actividad.excluye)
        actividad.fecha_ultima_consulta_api = timezone.now()
        actividad.save()
        logger.info(f"ActividadEconomica {codigo_ciiu} actualizada desde API")
    else:
        # Crear nueva desde API
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
        logger.info(f"ActividadEconomica {codigo_ciiu} creada desde API")
    
    # Guardar en cache del modelo
    cache_key_modelo = f"ciiu_modelo_{codigo_ciiu}"
    cache.set(cache_key_modelo, actividad, timeout=604800)
    
    return actividad

