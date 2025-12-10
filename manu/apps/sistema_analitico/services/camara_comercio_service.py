"""
Servicio para consultar información de empresas desde la API de Cámara de Comercio de Bogotá.
Usa el endpoint de datos.gov.co para obtener códigos CIUU por NIT.
"""
import requests
import logging
from typing import Dict, Optional, List
from django.core.cache import cache
from django.utils import timezone
from ..models import normalize_nit_and_extract_dv

logger = logging.getLogger(__name__)

# API de Cámara de Comercio de Bogotá (datos.gov.co)
CAMARA_COMERCIO_API_URL = 'https://www.datos.gov.co/resource/c82u-588k.json'
CACHE_TIMEOUT = 86400  # 24 horas


def consultar_camara_comercio_por_nit(nit: str) -> Optional[Dict]:
    """
    Consulta la API de Cámara de Comercio de Bogotá para obtener información de una empresa por NIT.
    
    Args:
        nit: NIT de la empresa (puede tener formato con puntos y guiones)
    
    Returns:
        Dict con información de la empresa incluyendo CIUUs, o None si hay error
        Estructura:
        {
            'nit': '900869750',
            'nit_normalizado': '900869750',
            'razon_social': 'EMPRESA EJEMPLO SAS',
            'ciuu_principal': '62010',
            'ciuu_secundarios': ['62020', '62090'],
            'fuente': 'camara_comercio',
            'fecha_consulta': '2024-01-01T00:00:00Z'
        }
    """
    if not nit:
        return None
    
    # Normalizar NIT
    nit_normalizado, _, _ = normalize_nit_and_extract_dv(nit)
    
    if not nit_normalizado:
        logger.warning(f"NIT no válido para consultar Cámara de Comercio: {nit}")
        return None
    
    # Verificar cache primero
    cache_key = f"camara_comercio_{nit_normalizado}"
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.debug(f"Info Cámara de Comercio para NIT {nit_normalizado} encontrada en cache")
        return cached_data
    
    try:
        # Consultar API
        url = f"{CAMARA_COMERCIO_API_URL}?nit={nit_normalizado}"
        logger.info(f"🌐 [CÁMARA COMERCIO] Consultando API: {url}")
        logger.info(f"🌐 [CÁMARA COMERCIO] NIT normalizado: {nit_normalizado}")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        logger.info(f"🌐 [CÁMARA COMERCIO] Respuesta recibida: {len(data) if data else 0} resultados")
        
        if not data or len(data) == 0:
            logger.warning(f"⚠️ [CÁMARA COMERCIO] No se encontró información en API para NIT: {nit_normalizado}")
            logger.warning(f"⚠️ [CÁMARA COMERCIO] URL consultada: {url}")
            # Guardar en cache como "no encontrado" por 1 hora para evitar consultas repetidas
            cache.set(cache_key, None, timeout=3600)
            return None
        
        # Tomar el primer resultado (debería ser único por NIT)
        empresa = data[0]
        
        # Extraer CIUUs
        ciuu_principal = empresa.get("cod_ciiu_act_econ_pri")
        ciuu_secundarios = []
        
        # Agregar CIUU secundario si existe
        if empresa.get("cod_ciiu_act_econ_sec"):
            ciuu_secundarios.append(empresa.get("cod_ciiu_act_econ_sec"))
        
        # Agregar otros CIUUs si existen
        if empresa.get("ciiu3"):
            ciuu_secundarios.append(empresa.get("ciiu3"))
        if empresa.get("ciiu4"):
            ciuu_secundarios.append(empresa.get("ciiu4"))
        
        # Eliminar duplicados y None
        ciuu_secundarios = list(set([c for c in ciuu_secundarios if c]))
        
        # Obtener detalles de cada CIUU (incluye/excluye) desde enlinea.ccc.org.co
        # Similar a como lo hace BCE con obtener_actividades()
        actividades_detalladas = []
        todos_ciuus = [ciuu_principal] + ciuu_secundarios if ciuu_principal else ciuu_secundarios
        todos_ciuus = [c for c in todos_ciuus if c]  # Filtrar None
        
        for ciuu in todos_ciuus:
            try:
                # Usar el servicio de CIUU existente que consulta enlinea.ccc.org.co
                from .ciiu_service import obtener_info_ciiu_completa
                info_ciuu = obtener_info_ciiu_completa(ciuu, forzar_consulta_api=False)
                
                if info_ciuu:
                    actividades_detalladas.append({
                        'codigo': ciuu,
                        'descripcion': info_ciuu.get('descripcion', ''),
                        'incluye': info_ciuu.get('incluye', []),
                        'excluye': info_ciuu.get('excluye', [])
                    })
                    logger.debug(f"✅ Detalles obtenidos para CIUU {ciuu}")
                else:
                    logger.warning(f"⚠️ No se pudieron obtener detalles para CIUU {ciuu}")
            except Exception as e:
                logger.warning(f"⚠️ Error obteniendo detalles para CIUU {ciuu}: {e}")
        
        # Construir resultado
        resultado = {
            'nit': empresa.get("nit", nit_normalizado),
            'nit_normalizado': nit_normalizado,
            'razon_social': empresa.get("razon_social") or empresa.get("nombre_comercial") or '',
            'ciuu_principal': ciuu_principal,
            'ciuu_secundarios': ciuu_secundarios,
            'actividades_detalladas': actividades_detalladas,  # Detalles con incluye/excluye
            'fuente': 'camara_comercio',
            'fecha_consulta': timezone.now().isoformat(),
            'datos_completos': empresa  # Guardar datos completos por si se necesitan después
        }
        
        # Guardar en cache
        cache.set(cache_key, resultado, timeout=CACHE_TIMEOUT)
        logger.info(f"✅ Info Cámara de Comercio obtenida para NIT {nit_normalizado}: CIUU principal={ciuu_principal}, {len(actividades_detalladas)} actividades detalladas")
        
        return resultado
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión consultando Cámara de Comercio para NIT {nit_normalizado}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado consultando Cámara de Comercio para NIT {nit_normalizado}: {e}", exc_info=True)
        return None

