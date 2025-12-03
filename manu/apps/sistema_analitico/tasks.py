"""
Tareas Celery para procesamiento asíncrono
"""
from celery import shared_task
from celery.schedules import crontab
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, time
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


@shared_task(bind=True, name='sistema_analitico.procesar_zip_ruts')
def procesar_zip_ruts_task(self, zip_file_path: str):
    """
    Tarea Celery para procesar un ZIP con múltiples PDFs de RUT de forma asíncrona.
    
    Args:
        zip_file_path: Ruta temporal del archivo ZIP a procesar
    
    Returns:
        dict con resultados del procesamiento
    """
    import os
    from .services.rut_batch_processor import procesar_zip_ruts
    
    try:
        logger.info(f"Iniciando procesamiento asíncrono de ZIP: {zip_file_path}")
        
        # Actualizar estado inicial
        self.update_state(
            state='PROCESSING',
            meta={
                'status': 'Abriendo archivo ZIP...',
                'total': 0,
                'procesados': 0,
                'exitosos': 0,
                'fallidos': 0
            }
        )
        
        # Procesar ZIP (pasar la tarea para actualizar progreso)
        resultados = procesar_zip_ruts(zip_file_path, task=self)
        
        # Limpiar archivo temporal
        try:
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)
        except Exception as e:
            logger.warning(f"No se pudo eliminar archivo temporal {zip_file_path}: {e}")
        
        logger.info(f"Procesamiento de ZIP completado: {len(resultados.get('exitosos', []))} exitosos, {len(resultados.get('fallidos', []))} fallidos")
        
        return {
            'status': 'SUCCESS',
            'total': resultados.get('total', 0),
            'exitosos': len(resultados.get('exitosos', [])),
            'fallidos': len(resultados.get('fallidos', [])),
            'reporte_txt': resultados.get('reporte_txt', ''),
            'detalles_exitosos': resultados.get('exitosos', []),
            'detalles_fallidos': resultados.get('fallidos', [])
        }
    
    except Exception as e:
        logger.error(f"Error en tarea Celery procesar_zip_ruts: {e}", exc_info=True)
        # Limpiar archivo temporal en caso de error
        try:
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)
        except:
            pass
        return {
            'status': 'ERROR',
            'error': str(e)
        }


@shared_task(bind=True, name='sistema_analitico.procesar_codigos_ciiu_masivo')
def procesar_codigos_ciiu_masivo_task(self, codigos_ciiu: list):
    """
    Tarea Celery para procesar múltiples códigos CIIU en PARALELO usando asyncio.
    Mucho más rápido que lanzar tareas individuales y esperarlas secuencialmente.
    
    Args:
        codigos_ciiu: Lista de códigos CIIU a procesar
    
    Returns:
        dict con resultados de todos los códigos procesados
    """
    import asyncio
    from .services.ciiu_service import obtener_o_crear_actividad_economica
    
    try:
        logger.info(f"Iniciando procesamiento masivo PARALELO de {len(codigos_ciiu)} códigos CIIU")
        
        # Filtrar códigos válidos
        codigos_validos = [c.strip() for c in codigos_ciiu if c and c.strip()]
        
        if not codigos_validos:
            return {
                'status': 'SUCCESS',
                'total': 0,
                'exitosos': 0,
                'fallidos': 0,
                'resultados': []
            }
        
        # Actualizar estado
        self.update_state(
            state='PROCESSING',
            meta={
                'total': len(codigos_validos),
                'procesados': 0,
                'status': f'Procesando {len(codigos_validos)} códigos en paralelo...'
            }
        )
        
        # Función async para procesar un código (usa versión async pura)
        async def procesar_codigo_async(codigo: str):
            from .services.ciiu_service import obtener_info_ciiu_completa_async
            from apps.sistema_analitico.models import ActividadEconomica
            from django.utils import timezone
            from asgiref.sync import sync_to_async
            
            try:
                # Verificar si existe en BD primero (usar sync_to_async)
                @sync_to_async
                def get_actividad(codigo):
                    try:
                        return ActividadEconomica.objects.get(codigo=codigo)
                    except ActividadEconomica.DoesNotExist:
                        return None
                
                actividad = await get_actividad(codigo)
                
                # Si existe y tiene consulta reciente, retornar
                if actividad and actividad.fecha_ultima_consulta_api:
                    from datetime import timedelta
                    dias_desde_consulta = (timezone.now() - actividad.fecha_ultima_consulta_api).days
                    if dias_desde_consulta < 7:
                        return {
                            'codigo': codigo,
                            'status': 'SUCCESS',
                            'actividad_id': actividad.id,
                            'descripcion': actividad.descripcion,
                            'titulo': actividad.titulo,
                            'cached': True
                        }
                
                # Consultar API (versión async pura, mucho más rápido)
                info_api = await obtener_info_ciiu_completa_async(codigo, forzar_consulta_api=(actividad is None))
                
                if not info_api:
                    # Si no se pudo obtener pero existe, retornar existente
                    if actividad:
                        return {
                            'codigo': codigo,
                            'status': 'SUCCESS',
                            'actividad_id': actividad.id,
                            'descripcion': actividad.descripcion,
                            'titulo': actividad.titulo,
                            'cached': True
                        }
                    return {
                        'codigo': codigo,
                        'status': 'FAILED',
                        'error': 'No se pudo obtener información de la API'
                    }
                
                # Crear o actualizar actividad (usar sync_to_async)
                @sync_to_async
                def save_actividad(codigo, info_api, actividad_existente):
                    from django.utils import timezone
                    if actividad_existente:
                        actividad_existente.descripcion = info_api.get('cseDescripcion', actividad_existente.descripcion)
                        actividad_existente.titulo = info_api.get('cseTitulo', actividad_existente.titulo)
                        actividad_existente.division = info_api.get('division', actividad_existente.division)
                        actividad_existente.grupo = info_api.get('grupo', actividad_existente.grupo)
                        actividad_existente.incluye = info_api.get('incluye', actividad_existente.incluye)
                        actividad_existente.excluye = info_api.get('excluye', actividad_existente.excluye)
                        actividad_existente.fecha_ultima_consulta_api = timezone.now()
                        actividad_existente.save()
                        return actividad_existente
                    else:
                        nueva_actividad = ActividadEconomica.objects.create(
                            codigo=codigo,
                            descripcion=info_api.get('cseDescripcion', f"Actividad {codigo}"),
                            titulo=info_api.get('cseTitulo', f"CIIU {codigo}"),
                            division=info_api.get('division', codigo[:2] if len(codigo) >= 2 else ''),
                            grupo=info_api.get('grupo', codigo[:3] if len(codigo) >= 3 else ''),
                            incluye=info_api.get('incluye', []),
                            excluye=info_api.get('excluye', []),
                            fecha_ultima_consulta_api=timezone.now()
                        )
                        return nueva_actividad
                
                actividad = await save_actividad(codigo, info_api, actividad)
                
                # Guardar en cache (sync_to_async)
                @sync_to_async
                def set_cache(key, value, timeout):
                    cache.set(key, value, timeout=timeout)
                
                cache_key_modelo = f"ciiu_modelo_{codigo}"
                await set_cache(cache_key_modelo, actividad, 604800)
                
                return {
                    'codigo': codigo,
                    'status': 'SUCCESS',
                    'actividad_id': actividad.id,
                    'descripcion': actividad.descripcion,
                    'titulo': actividad.titulo
                }
            except Exception as e:
                logger.error(f"Error procesando código CIIU {codigo}: {e}", exc_info=True)
                return {
                    'codigo': codigo,
                    'status': 'ERROR',
                    'error': str(e)
                }
        
        # Procesar todos los códigos en paralelo usando asyncio.gather
        # Esto es MUCHO más rápido que esperar tareas secuencialmente
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            tareas = [procesar_codigo_async(codigo) for codigo in codigos_validos]
            resultados = loop.run_until_complete(asyncio.gather(*tareas))
        finally:
            loop.close()
        
        exitosos = sum(1 for r in resultados if r.get('status') == 'SUCCESS')
        
        logger.info(f"Procesamiento masivo PARALELO completado: {exitosos}/{len(resultados)} exitosos")
        
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


@shared_task(bind=True, name='sistema_analitico.realizar_backup_empresa')
def realizar_backup_empresa_task(self, empresa_id: int, configuracion_s3_id: int):
    """
    Tarea Celery para realizar backup de una empresa específica a S3.
    
    Args:
        empresa_id: ID de la empresa
        configuracion_s3_id: ID de la configuración S3 a utilizar
        
    Returns:
        dict con resultado del backup
    """
    from .models import EmpresaServidor, ConfiguracionS3
    from .services.backup_s3_service import BackupS3Service
    
    try:
        empresa = EmpresaServidor.objects.get(id=empresa_id)
        config_s3 = ConfiguracionS3.objects.get(id=configuracion_s3_id, activo=True)
        
        logger.info(f"🔄 Iniciando backup para empresa {empresa.nombre} (ID: {empresa_id})")
        
        self.update_state(
            state='PROCESSING',
            meta={
                'empresa_id': empresa_id,
                'empresa_nombre': empresa.nombre,
                'status': 'Paso 1/3: Creando backup local con gbak...'
            }
        )
        logger.info(f"📦 Paso 1/3: Creando backup local con gbak para {empresa.nombre}...")
        
        # Crear servicio y realizar backup
        servicio = BackupS3Service(config_s3)
        
        self.update_state(
            state='PROCESSING',
            meta={
                'empresa_id': empresa_id,
                'empresa_nombre': empresa.nombre,
                'status': 'Paso 2/3: Subiendo a S3...'
            }
        )
        logger.info(f"☁️ Paso 2/3: Subiendo backup a S3 (Contabo) para {empresa.nombre}...")
        
        exito, backup_s3, mensaje_error = servicio.realizar_backup_completo(empresa)
        
        if exito:
            self.update_state(
                state='PROCESSING',
                meta={
                    'empresa_id': empresa_id,
                    'empresa_nombre': empresa.nombre,
                    'status': 'Paso 3/3: Aplicando política de retención...'
                }
            )
            logger.info(f"🧹 Paso 3/3: Aplicando política de retención para {empresa.nombre}...")
        
        if exito:
            logger.info(f"Backup completado exitosamente para {empresa.nombre}: {backup_s3.ruta_s3}")
            return {
                'status': 'SUCCESS',
                'empresa_id': empresa_id,
                'backup_id': backup_s3.id,
                'ruta_s3': backup_s3.ruta_s3,
                'tamano_gb': backup_s3.tamano_gb,
                'mensaje': 'Backup completado exitosamente'
            }
        else:
            logger.error(f"Error en backup para {empresa.nombre}: {mensaje_error}")
            return {
                'status': 'ERROR',
                'empresa_id': empresa_id,
                'error': mensaje_error or 'Error desconocido al realizar backup'
            }
            
    except EmpresaServidor.DoesNotExist:
        logger.error(f"Empresa con ID {empresa_id} no existe")
        return {
            'status': 'ERROR',
            'error': f'Empresa con ID {empresa_id} no existe'
        }
    except ConfiguracionS3.DoesNotExist:
        logger.error(f"Configuración S3 con ID {configuracion_s3_id} no existe o no está activa")
        return {
            'status': 'ERROR',
            'error': f'Configuración S3 con ID {configuracion_s3_id} no existe o no está activa'
        }
    except Exception as e:
        logger.error(f"Error inesperado en backup para empresa {empresa_id}: {e}", exc_info=True)
        return {
            'status': 'ERROR',
            'error': str(e)
        }


@shared_task(name='sistema_analitico.procesar_backups_programados', rate_limit='10/m')  # Máximo 10 por minuto
def procesar_backups_programados_task():
    """
    Tarea Celery programada para procesar backups de todas las empresas.
    
    Estrategia para evitar sobrecargar el servidor:
    - A las 1:00 AM: Procesa empresas del año fiscal actual (prioridad alta)
    - Durante el día: Procesa empresas de años anteriores que necesitan backup (más de 230 días)
    - Procesa en lotes pequeños con rate limiting
    
    Esta tarea debe ejecutarse cada hora.
    """
    from .models import EmpresaServidor, ConfiguracionS3
    from .services.backup_s3_service import BackupS3Service
    from datetime import date
    
    try:
        hora_actual = timezone.now().time()
        hora_actual_str = hora_actual.strftime('%H:%M')
        anio_actual = date.today().year
        
        logger.info(f"Procesando backups programados para hora {hora_actual_str}")
        
        # Obtener configuración S3 activa
        config_s3 = ConfiguracionS3.objects.filter(activo=True).first()
        if not config_s3:
            logger.warning("No hay configuración S3 activa. Saltando backups programados.")
            return {
                'status': 'SKIPPED',
                'mensaje': 'No hay configuración S3 activa'
            }
        
        servicio_backup = BackupS3Service(config_s3)
        
        empresas_procesadas = 0
        empresas_anio_actual = 0
        empresas_anios_anteriores = 0
        
        # PRIORIDAD 1: Empresas del año fiscal actual a la hora programada (1:00 AM)
        if hora_actual.hour == 1:  # Solo a la 1:00 AM
            logger.info("🔄 Procesando backups de empresas del año fiscal actual (1:00 AM)")
            empresas_anio_actual_list = EmpresaServidor.objects.filter(
                backups_habilitados=True,
                anio_fiscal=anio_actual
            )
            
            # Procesar en lotes de 20 para no sobrecargar
            lote_size = 20
            empresas_list = list(empresas_anio_actual_list)
            
            for i in range(0, len(empresas_list), lote_size):
                lote = empresas_list[i:i + lote_size]
                logger.info(f"Procesando lote {i//lote_size + 1} de empresas año actual ({len(lote)} empresas)")
                
                for empresa in lote:
                    # Verificar si la hora programada coincide (margen de 5 minutos)
                    hora_empresa = empresa.hora_backup
                    diferencia_minutos = abs(
                        (hora_actual.hour * 60 + hora_actual.minute) - 
                        (hora_empresa.hour * 60 + hora_empresa.minute)
                    )
                    
                    if diferencia_minutos <= 5:
                        empresas_anio_actual += 1
                        empresas_procesadas += 1
                        logger.info(f"📦 Backup programado para {empresa.nombre} (año {empresa.anio_fiscal})")
                        realizar_backup_empresa_task.delay(empresa.id, config_s3.id)
        
        # PRIORIDAD 2: Empresas de años anteriores que necesitan backup (más de 30 días)
        # Procesar solo 10 empresas por hora para no sobrecargar
        logger.info("🔄 Verificando empresas de años anteriores que necesitan backup")
        empresas_anios_anteriores_list = EmpresaServidor.objects.filter(
            backups_habilitados=True,
            anio_fiscal__lt=anio_actual
        ).order_by('anio_fiscal', 'id')  # Ordenar para procesar de forma consistente
        
        empresas_que_necesitan_backup = []
        for empresa in empresas_anios_anteriores_list[:50]:  # Verificar máximo 50 por hora
            necesita, anio = servicio_backup.necesita_backup_anio_anterior(empresa)
            if necesita:
                empresas_que_necesitan_backup.append(empresa)
        
        # Procesar máximo 10 empresas de años anteriores por hora
        for empresa in empresas_que_necesitan_backup[:10]:
            empresas_anios_anteriores += 1
            empresas_procesadas += 1
            logger.info(f"🔄 Backup necesario para {empresa.nombre} (año {empresa.anio_fiscal}, >30 días)")
            realizar_backup_empresa_task.delay(empresa.id, config_s3.id)
        
        logger.info(f"✅ Backups programados lanzados: {empresas_procesadas} empresas "
                   f"(Año actual: {empresas_anio_actual}, Años anteriores: {empresas_anios_anteriores})")
        
        return {
            'status': 'SUCCESS',
            'hora_actual': hora_actual_str,
            'empresas_procesadas': empresas_procesadas,
            'empresas_anio_actual': empresas_anio_actual,
            'empresas_anios_anteriores': empresas_anios_anteriores
        }
        
    except Exception as e:
        logger.error(f"Error procesando backups programados: {e}", exc_info=True)
        return {
            'status': 'ERROR',
            'error': str(e)
        }