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


@shared_task(bind=True, name='sistema_analitico.clasificar_factura_contable')
def clasificar_factura_contable_task(
    self,
    factura_data: dict,
    empresa_nit: str,
    empresa_ciuu_principal: str,
    empresa_ciuu_secundarios: list,
    proveedor_nit: str,
    proveedor_ciuu: str = None,
    aplica_retencion: bool = False,
    porcentaje_retencion: float = 0,
    tipo_operacion: str = "compra",
    session_dian_id: int = None
):
    """
    Tarea Celery para clasificar factura contable usando servicios de IA/Analytics.
    
    Args:
        factura_data: Dict con datos de la factura
        empresa_nit: NIT de la empresa compradora
        empresa_ciuu_principal: CIUU principal de la empresa
        empresa_ciuu_secundarios: Lista de CIUUs secundarios
        proveedor_nit: NIT del proveedor
        proveedor_ciuu: CIUU del proveedor (opcional, se busca si no se proporciona)
        aplica_retencion: Si aplica retención
        porcentaje_retencion: Porcentaje de retención
        tipo_operacion: Tipo de operación (compra/venta)
        session_dian_id: ID de sesión DIAN (opcional)
    
    Returns:
        dict con resultado de la clasificación
    """
    from .services.clasificador_contable_service import ClasificadorContableService
    
    try:
        logger.info(f"📊 Iniciando clasificación contable: Factura {factura_data.get('numero_factura')}")
        
        self.update_state(
            state='PROCESSING',
            meta={
                'factura': factura_data.get('numero_factura'),
                'status': 'Clasificando factura...'
            }
        )
        
        servicio = ClasificadorContableService()
        resultado = servicio.clasificar_factura(
            factura=factura_data,
            empresa_nit=empresa_nit,
            empresa_ciuu_principal=empresa_ciuu_principal,
            empresa_ciuu_secundarios=empresa_ciuu_secundarios,
            proveedor_nit=proveedor_nit,
            proveedor_ciuu=proveedor_ciuu,
            aplica_retencion=aplica_retencion,
            porcentaje_retencion=porcentaje_retencion,
            tipo_operacion=tipo_operacion
        )
        
        if resultado.get('success'):
            # Guardar en BD
            clasificacion = servicio.guardar_clasificacion(
                factura_numero=factura_data.get('numero_factura'),
                proveedor_nit=proveedor_nit,
                empresa_nit=empresa_nit,
                empresa_ciuu_principal=empresa_ciuu_principal,
                proveedor_ciuu=proveedor_ciuu,
                resultado=resultado,
                session_dian_id=session_dian_id
            )
            
            logger.info(f"✅ Clasificación completada: ID {clasificacion.id}")
            return {
                'status': 'SUCCESS',
                'clasificacion_id': clasificacion.id,
                'factura_numero': factura_data.get('numero_factura'),
                'costo_usd': float(resultado.get('costo', {}).get('costo_usd', 0)),
                'tiempo_segundos': resultado.get('tiempo_procesamiento', 0)
            }
        else:
            logger.error(f"❌ Error en clasificación: {resultado.get('error')}")
            return {
                'status': 'FAILED',
                'error': resultado.get('error'),
                'factura_numero': factura_data.get('numero_factura')
            }
            
    except Exception as e:
        logger.error(f"❌ Error inesperado en clasificación: {e}", exc_info=True)
        return {
            'status': 'FAILED',
            'error': str(e),
            'factura_numero': factura_data.get('numero_factura', 'DESCONOCIDA')
        }


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
        
        # Crear servicio
        servicio = BackupS3Service(config_s3)
        
        # Paso 1: Crear backup local
        self.update_state(
            state='PROCESSING',
            meta={
                'empresa_id': empresa_id,
                'empresa_nombre': empresa.nombre,
                'status': 'Paso 1/3: Creando backup local con gbak...'
            }
        )
        logger.info(f"📦 Paso 1/3: Creando backup local con gbak para {empresa.nombre}...")
        
        # Realizar backup completo (esto incluye crear backup local, subir a S3 y aplicar retención)
        # El servicio actualizará el progreso internamente
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


@shared_task(name='sistema_analitico.explorar_empresas_todos_servidores')
def explorar_empresas_todos_servidores_task():
    """
    Tarea Celery programada para explorar empresas en todos los servidores activos.
    Se ejecuta automáticamente a la 1:00 AM para detectar nuevas empresas creadas.
    
    Esta tarea inicia el descubrimiento de empresas en todos los servidores de forma asíncrona.
    No espera los resultados para no bloquear, pero registra que se iniciaron las tareas.
    
    Returns:
        dict con información de las tareas iniciadas
    """
    from .models import Servidor
    
    try:
        logger.info("🔍 Iniciando exploración automática de empresas en todos los servidores (1:00 AM)")
        
        # Obtener todos los servidores activos
        servidores_activos = Servidor.objects.filter(activo=True)
        
        if not servidores_activos.exists():
            logger.warning("⚠️ No hay servidores activos para explorar")
            return {
                'status': 'SKIPPED',
                'mensaje': 'No hay servidores activos'
            }
        
        tareas_iniciadas = []
        
        for servidor in servidores_activos:
            try:
                logger.info(f"📡 Iniciando exploración de empresas en servidor: {servidor.nombre} (ID: {servidor.id})")
                
                # Llamar a la tarea de descubrimiento de forma asíncrona
                # No esperamos el resultado para que se ejecute en paralelo y no bloquee
                task_result = descubrir_empresas_task.delay(servidor.id)
                
                tareas_iniciadas.append({
                    'servidor_id': servidor.id,
                    'servidor_nombre': servidor.nombre,
                    'task_id': task_result.id,
                    'status': 'INICIADA'
                })
                
                logger.info(f"✅ Tarea de exploración iniciada para servidor {servidor.nombre} (Task ID: {task_result.id})")
                    
            except Exception as e:
                logger.error(f"❌ Error iniciando exploración en servidor {servidor.nombre}: {e}", exc_info=True)
                tareas_iniciadas.append({
                    'servidor_id': servidor.id,
                    'servidor_nombre': servidor.nombre,
                    'status': 'ERROR',
                    'error': str(e)
                })
        
        logger.info(f"✅ Exploración automática iniciada: {len(tareas_iniciadas)} tarea(s) iniciada(s)")
        
        return {
            'status': 'SUCCESS',
            'total_servidores': len(servidores_activos),
            'tareas_iniciadas': len([t for t in tareas_iniciadas if t.get('status') == 'INICIADA']),
            'tareas_por_servidor': tareas_iniciadas,
            'mensaje': f'Se iniciaron {len([t for t in tareas_iniciadas if t.get("status") == "INICIADA"])} tarea(s) de exploración en {len(servidores_activos)} servidor(es). Las tareas se ejecutan en paralelo.'
        }
        
    except Exception as e:
        logger.error(f"❌ Error en exploración automática de empresas: {e}", exc_info=True)
        return {
            'status': 'ERROR',
            'error': str(e)
        }


@shared_task(bind=True, name='sistema_analitico.convertir_backup_a_gdb')
def convertir_backup_a_gdb_task(self, descarga_temporal_id: int):
    """
    Tarea Celery para convertir un backup FBK a GDB y enviar el link de descarga por correo.
    
    Args:
        descarga_temporal_id: ID del registro DescargaTemporalBackup
        
    Returns:
        dict con resultado de la conversión
    """
    from .models import DescargaTemporalBackup, ConfiguracionS3
    from .services.backup_s3_service import BackupS3Service
    import tempfile
    import os
    import subprocess
    import secrets
    
    try:
        descarga = DescargaTemporalBackup.objects.get(id=descarga_temporal_id)
        backup = descarga.backup
        empresa = backup.empresa_servidor
        
        # Actualizar estado
        descarga.estado = 'procesando'
        descarga.save()
        
        logger.info(f"🔄 Iniciando conversión de backup {backup.id} a GDB para {descarga.email}")
        
        # Obtener configuración S3 y servicio
        config_s3 = backup.configuracion_s3
        if not config_s3:
            raise ValueError('Backup no tiene configuración S3 asociada')
        
        servicio = BackupS3Service(config_s3)
        
        # Descargar FBK desde S3
        temp_dir = tempfile.gettempdir()
        # Generar nombre de archivo temporal: usar backup.nombre_archivo si existe y no está vacío, sino generar uno por defecto
        if backup.nombre_archivo and backup.nombre_archivo.strip():
            nombre_temp = backup.nombre_archivo
        else:
            fecha_str = backup.fecha_backup.strftime('%Y%m%d_%H%M%S') if backup.fecha_backup else 'unknown'
            nombre_temp = f"backup_{empresa.nit_normalizado if empresa else 'unknown'}_{fecha_str}.fbk"
        temp_fbk = os.path.join(temp_dir, f"backup_{backup.id}_{nombre_temp}")
        
        servicio.s3_client.download_file(
            servicio.bucket_name,
            backup.ruta_s3,
            temp_fbk
        )
        
        # Obtener nombre del archivo GDB
        ruta_base = empresa.ruta_base
        nombre_gdb = os.path.basename(ruta_base)
        
        # Limpiar nombre: remover caracteres especiales y rutas de Windows
        # Si la ruta es de Windows (contiene \ o :), extraer solo el nombre del archivo
        if '\\' in nombre_gdb or ':' in nombre_gdb:
            # Es una ruta de Windows, extraer solo el nombre del archivo
            nombre_gdb = nombre_gdb.replace('\\', '/').split('/')[-1]
        
        # Limpiar caracteres especiales que pueden causar problemas en Linux
        import re
        nombre_gdb = re.sub(r'[^\w\-_.]', '_', nombre_gdb)
        
        # Asegurar que termine en .gdb o .GDB
        if not nombre_gdb.lower().endswith('.gdb'):
            if nombre_gdb:
                # Remover extensión si existe y agregar .GDB
                nombre_gdb = os.path.splitext(nombre_gdb)[0] + '.GDB'
            else:
                nombre_gdb = f"{empresa.codigo}.GDB"
        
        # Crear ruta temporal para GDB (en una carpeta persistente para que dure 1 día)
        gdb_dir = os.path.join(temp_dir, 'backups_gdb_temporales')
        os.makedirs(gdb_dir, exist_ok=True)
        temp_gdb = os.path.join(gdb_dir, f"{descarga.token}_{nombre_gdb}")
        
        # Buscar gbak
        gbak_path = None
        posibles_rutas = [
            '/opt/firebird2.5/bin/gbak',
            '/opt/firebird2.5/opt/firebird/bin/gbak',
            '/usr/local/bin/gbak',
            '/usr/bin/gbak',
            'gbak'
        ]
        
        for ruta in posibles_rutas:
            if os.path.exists(ruta) or ruta == 'gbak':
                try:
                    result = subprocess.run(
                        [ruta, '-?'],
                        capture_output=True,
                        timeout=5
                    )
                    gbak_path = ruta
                    break
                except:
                    continue
        
        if not gbak_path:
            descarga.estado = 'expirado'
            descarga.save()
            raise ValueError('No se encontró gbak para convertir el backup')
        
        # Verificar si el servidor Firebird está instalado (no solo gbak)
        # Si gbak está en /opt/firebird2.5, el servidor probablemente también está ahí
        firebird_server_path = None
        posibles_servidores = [
            '/opt/firebird2.5/bin/fbserver',
            '/opt/firebird2.5/opt/firebird/bin/fbserver',
            '/opt/firebird2.5/bin/firebird',
            '/usr/sbin/fbserver',
            '/usr/lib/firebird/2.5/bin/fbserver',
            '/usr/lib/firebird/3.0/bin/fbserver'
        ]
        for ruta_servidor in posibles_servidores:
            if os.path.exists(ruta_servidor):
                firebird_server_path = ruta_servidor
                logger.info(f"✅ Servidor Firebird encontrado en: {ruta_servidor}")
                break
        
        # Si gbak está en /opt/firebird2.5, buscar servidor en la misma ubicación
        if not firebird_server_path and gbak_path and '/opt/firebird2.5' in gbak_path:
            # Extraer directorio base de gbak
            gbak_dir = os.path.dirname(gbak_path)
            posibles_rutas_relativas = [
                os.path.join(gbak_dir, 'fbserver'),
                os.path.join(gbak_dir, 'firebird'),
                os.path.join(os.path.dirname(gbak_dir), 'fbserver'),
                os.path.join(os.path.dirname(gbak_dir), 'firebird'),
            ]
            for ruta_rel in posibles_rutas_relativas:
                if os.path.exists(ruta_rel):
                    firebird_server_path = ruta_rel
                    logger.info(f"✅ Servidor Firebird encontrado cerca de gbak: {ruta_rel}")
                    break
        
        # Verificar si el servidor Firebird está corriendo (gbak -c lo requiere)
        # Intentar verificar con systemctl o ps
        firebird_running = False
        try:
            # Verificar si firebird está corriendo
            check_firebird = subprocess.run(
                ['systemctl', 'is-active', '--quiet', 'firebird2.5'],
                capture_output=True,
                timeout=2
            )
            if check_firebird.returncode == 0:
                firebird_running = True
                logger.info("✅ Servidor Firebird 2.5 está corriendo")
        except:
            try:
                # Intentar con firebird3.0
                check_firebird = subprocess.run(
                    ['systemctl', 'is-active', '--quiet', 'firebird3.0'],
                    capture_output=True,
                    timeout=2
                )
                if check_firebird.returncode == 0:
                    firebird_running = True
                    logger.info("✅ Servidor Firebird 3.0 está corriendo")
            except:
                pass
        
        if not firebird_running:
            # Intentar verificar con ps
            try:
                check_ps = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if 'firebird' in check_ps.stdout.lower() or 'fbserver' in check_ps.stdout.lower():
                    firebird_running = True
                    logger.info("✅ Servidor Firebird detectado en procesos")
            except:
                pass
        
        if not firebird_running:
            logger.warning("⚠️ Servidor Firebird no detectado como corriendo. Intentando iniciarlo...")
            
            # Primero intentar con systemctl (si está configurado como servicio)
            try:
                start_result = subprocess.run(
                    ['sudo', 'systemctl', 'start', 'firebird2.5'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if start_result.returncode == 0:
                    logger.info("✅ Servidor Firebird 2.5 iniciado exitosamente (systemctl)")
                    firebird_running = True
                    import time
                    time.sleep(2)
            except Exception as e:
                logger.debug(f"systemctl firebird2.5 no disponible: {e}")
            
            # Si aún no está corriendo, intentar con firebird3.0
            if not firebird_running:
                try:
                    start_result = subprocess.run(
                        ['sudo', 'systemctl', 'start', 'firebird3.0'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if start_result.returncode == 0:
                        logger.info("✅ Servidor Firebird 3.0 iniciado exitosamente (systemctl)")
                        firebird_running = True
                        import time
                        time.sleep(2)
                except Exception as e:
                    logger.debug(f"systemctl firebird3.0 no disponible: {e}")
            
            # Si tenemos la ruta del servidor pero no está corriendo, intentar iniciarlo directamente
            # (para instalaciones manuales de Firebird 2.5 que no tienen systemd)
            if not firebird_running and firebird_server_path:
                logger.info(f"💡 Intentando iniciar servidor Firebird directamente desde: {firebird_server_path}")
                logger.warning("⚠️ NOTA: Para instalaciones manuales, el servidor puede necesitar iniciarse manualmente.")
                logger.warning("💡 Si el servidor no está corriendo, gbak -c fallará.")
                logger.warning("💡 Opciones:")
                logger.warning("   1. Iniciar servidor manualmente antes de solicitar conversión GDB")
                logger.warning("   2. Configurar Firebird como servicio systemd")
                logger.warning("   3. Usar Firebird en modo embedded (si está disponible)")
            
            if not firebird_running:
                logger.error("❌ No se pudo iniciar el servidor Firebird. gbak -c requiere que el servidor esté corriendo.")
                if firebird_server_path:
                    logger.error(f"💡 Servidor encontrado en: {firebird_server_path}")
                    logger.error("💡 Inicia manualmente el servidor antes de solicitar conversión GDB")
                else:
                    logger.error("💡 Instala el servidor Firebird: sudo apt-get install firebird3.0-server")
                    logger.error("   O instala Firebird 2.5 manualmente (ver docs/INSTALAR_FIREBIRD_2.5_UBUNTU.md)")
        
        # Asegurar que el archivo de destino no exista (gbak -c requiere que no exista)
        if os.path.exists(temp_gdb):
            logger.warning(f"⚠️ El archivo GDB ya existe, eliminándolo: {temp_gdb}")
            os.remove(temp_gdb)
        
        # Convertir FBK a GDB
        # NOTA: gbak -c requiere que el servidor Firebird esté corriendo
        # Para Firebird, el formato correcto para archivos locales es:
        # - Con localhost/3050:ruta (puerto explícito) - más confiable
        # - Con localhost:ruta (puerto por defecto 3050)
        # Intentar primero con localhost/3050: (más explícito y confiable)
        temp_gdb_firebird = f"localhost/3050:{temp_gdb}"
        
        comando = [
            gbak_path,
            '-c',  # Create database
            '-v',  # Verbose
            '-user', 'SYSDBA',
            '-password', 'masterkey',
            temp_fbk,  # Archivo FBK de origen (local)
            temp_gdb_firebird  # Archivo GDB de destino (formato localhost/3050:)
        ]
        
        logger.info(f"⏳ Convirtiendo backup a GDB: {' '.join(comando)}")
        logger.info(f"📁 FBK origen: {temp_fbk}")
        logger.info(f"📁 GDB destino: {temp_gdb} (formato Firebird: {temp_gdb_firebird})")
        
        # Configurar variables de entorno para manejar caracteres especiales
        env = os.environ.copy()
        env['LC_ALL'] = 'C.UTF-8'
        env['LANG'] = 'C.UTF-8'
        
        # Asegurar que el directorio temporal existe y tiene permisos correctos
        gdb_dir = os.path.dirname(temp_gdb)
        os.makedirs(gdb_dir, exist_ok=True)
        # Establecer umask para que los archivos se creen con permisos 644
        import stat
        old_umask = os.umask(0o022)  # Permisos: 644 (rw-r--r--)
        
        # Obtener tamaño del FBK para validar después
        fbk_size = os.path.getsize(temp_fbk) if os.path.exists(temp_fbk) else 0
        logger.info(f"📊 Tamaño del FBK: {fbk_size / (1024*1024):.2f} MB")
        
        try:
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutos máximo
                env=env
            )
        finally:
            # Restaurar umask original
            os.umask(old_umask)
        
        # Verificar si hubo errores (incluso si returncode es 0, gbak puede reportar errores)
        output_completo = (resultado.stdout or '') + (resultado.stderr or '')
        tiene_error = (
            resultado.returncode != 0 or
            'ERROR:' in output_completo or
            'failed to create database' in output_completo.lower() or
            'Error reading data from the connection' in output_completo or
            'do not recognize record type' in output_completo.lower()
        )
        
        # Si falla, intentar con formato alternativo (sin puerto explícito)
        if tiene_error:
            error_msg = resultado.stderr or resultado.stdout or "Error desconocido"
            logger.warning(f"⚠️ Primer intento falló. Error: {error_msg[:200]}")
            
            # Limpiar archivo parcial si existe
            if os.path.exists(temp_gdb):
                logger.warning(f"⚠️ Eliminando archivo GDB parcial: {temp_gdb}")
                os.remove(temp_gdb)
            
            if "Error reading data from the connection" in error_msg or "Unable to complete network request" in error_msg:
                logger.warning(f"⚠️ Intentando con formato localhost: (sin puerto explícito)...")
                temp_gdb_firebird = f"localhost:{temp_gdb}"
                comando[-1] = temp_gdb_firebird
                logger.info(f"🔄 Reintentando con: {' '.join(comando)}")
                
                resultado = subprocess.run(
                    comando,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    env=env
                )
                
                # Verificar de nuevo
                output_completo = (resultado.stdout or '') + (resultado.stderr or '')
                tiene_error = (
                    resultado.returncode != 0 or
                    'ERROR:' in output_completo or
                    'failed to create database' in output_completo.lower() or
                    'Error reading data from the connection' in output_completo
                )
        
        # Limpiar FBK temporal
        if os.path.exists(temp_fbk):
            os.remove(temp_fbk)
        
        # Verificar que el archivo GDB se creó y tiene un tamaño razonable
        gdb_existe = os.path.exists(temp_gdb)
        gdb_size = os.path.getsize(temp_gdb) if gdb_existe else 0
        
        if gdb_existe:
            logger.info(f"📊 Archivo GDB creado. Tamaño: {gdb_size / (1024*1024):.2f} MB")
            # El GDB normalmente es más pequeño que el FBK (el FBK está comprimido)
            # Para un FBK de 24MB, un GDB de 1.6MB puede ser razonable si está muy comprimido
            # Pero si es menor a 500KB para un FBK grande, probablemente está incompleto
            if fbk_size > 0 and gdb_size < (fbk_size * 0.02):  # Menos del 2% del tamaño del FBK
                logger.error(f"❌ Archivo GDB demasiado pequeño ({gdb_size} bytes, {gdb_size / (1024*1024):.2f} MB) para un FBK de {fbk_size / (1024*1024):.2f} MB. Probablemente incompleto.")
                tiene_error = True
            elif gdb_size < 500 * 1024:  # Menos de 500KB en general
                logger.error(f"❌ Archivo GDB demasiado pequeño ({gdb_size} bytes). Probablemente incompleto.")
                tiene_error = True
        
        if tiene_error or not gdb_existe:
            error_msg = resultado.stderr or resultado.stdout or "Error desconocido"
            logger.error(f"❌ Error convirtiendo backup a GDB: {error_msg}")
            logger.error(f"📊 Estado: returncode={resultado.returncode}, GDB existe={gdb_existe}, tamaño={gdb_size}")
            
            # Limpiar archivo parcial si existe
            if gdb_existe:
                try:
                    os.remove(temp_gdb)
                except:
                    pass
            
            # Agregar mensaje más claro según el tipo de error
            if "Unable to complete network request" in error_msg or "Error reading data from the connection" in error_msg:
                error_msg += "\n\n💡 NOTA: gbak -c requiere que el servidor Firebird esté corriendo. Verifica con: sudo systemctl status firebird2.5 o firebird3.0"
                error_msg += "\n💡 Si el servidor está corriendo, puede ser un problema de timeout o buffer. Intenta aumentar el timeout o verificar los logs del servidor."
            elif "do not recognize record type" in error_msg.lower():
                error_msg += "\n\n💡 NOTA: Este error puede indicar que el backup FBK está corrupto, incompleto, o fue creado con una versión incompatible de Firebird."
                error_msg += "\n💡 Verifica que el backup FBK esté completo y no corrupto. Intenta crear un nuevo backup si el problema persiste."
            
            descarga.estado = 'expirado'
            descarga.save()
            raise Exception(f'Error al convertir backup a GDB: {error_msg}')
        
        # Guardar ruta del GDB
        descarga.ruta_gdb_temporal = temp_gdb
        descarga.estado = 'listo'
        descarga.save()
        
        # Asegurar permisos de lectura para el usuario de Django/Celery
        # El archivo GDB puede haber sido creado por el servidor Firebird con permisos del usuario 'firebird'
        # Necesitamos hacerlo legible por el usuario que corre Django/Celery (probablemente 'victus')
        try:
            import stat
            import pwd
            
            # Obtener el usuario actual que ejecuta Celery/Django
            try:
                current_uid = os.getuid()
                current_user_info = pwd.getpwuid(current_uid)
                current_user = current_user_info.pw_name
                current_gid = current_user_info.pw_gid
                logger.info(f"👤 Usuario actual de Celery/Django: {current_user} (UID: {current_uid}, GID: {current_gid})")
            except Exception as e:
                # Fallback si no podemos obtener el usuario (Windows o error)
                current_user = os.getenv('USER') or os.getenv('USERNAME') or 'victus'
                logger.warning(f"⚠️ No se pudo obtener UID, usando usuario por defecto: {current_user}")
            
            # Obtener propietario actual del archivo
            try:
                file_stat = os.stat(temp_gdb)
                file_uid = file_stat.st_uid
                file_gid = file_stat.st_gid
                file_owner = pwd.getpwuid(file_uid).pw_name if file_uid else 'unknown'
                logger.info(f"📁 Propietario actual del GDB: {file_owner} (UID: {file_uid}, GID: {file_gid})")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo obtener propietario del archivo: {e}")
                file_owner = 'unknown'
            
            # Si el archivo no pertenece al usuario actual, cambiar propietario
            if file_owner != current_user:
                logger.info(f"🔄 Cambiando propietario de {file_owner} a {current_user}...")
                try:
                    # Intentar cambiar propietario con sudo
                    subprocess.run(
                        ['sudo', 'chown', f'{current_user}:{current_user}', temp_gdb],
                        check=True,
                        timeout=5
                    )
                    logger.info(f"✅ Propietario cambiado exitosamente a {current_user}")
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo cambiar propietario con sudo: {e}")
                    # Si falla, al menos intentar hacer el archivo legible por todos
                    try:
                        subprocess.run(
                            ['sudo', 'chmod', '644', temp_gdb],
                            check=True,
                            timeout=5
                        )
                        logger.info(f"✅ Permisos establecidos a 644 (lectura para todos)")
                    except Exception as e2:
                        logger.error(f"❌ No se pudieron establecer permisos: {e2}")
                        raise Exception(f"No se pudieron establecer permisos de lectura para el archivo GDB: {e2}")
            else:
                logger.info(f"✅ El archivo ya pertenece al usuario correcto ({current_user})")
            
            # Establecer permisos 644 (rw-r--r--) para asegurar lectura
            try:
                os.chmod(temp_gdb, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)  # 644
                logger.info(f"✅ Permisos del GDB establecidos a 644")
            except PermissionError:
                # Si chmod directo falla, intentar con sudo
                logger.warning(f"⚠️ chmod directo falló, intentando con sudo...")
                try:
                    subprocess.run(
                        ['sudo', 'chmod', '644', temp_gdb],
                        check=True,
                        timeout=5
                    )
                    logger.info(f"✅ Permisos del GDB establecidos a 644 (con sudo)")
                except Exception as e:
                    logger.error(f"❌ No se pudieron establecer permisos con sudo: {e}")
                    raise Exception(f"No se pudieron establecer permisos de lectura para el archivo GDB: {e}")
            
            # Verificar que el archivo es legible
            if not os.access(temp_gdb, os.R_OK):
                logger.error(f"❌ El archivo GDB aún no es legible después de cambiar permisos")
                # Intentar una última vez con sudo chmod y chown
                try:
                    subprocess.run(['sudo', 'chmod', '644', temp_gdb], check=True, timeout=5)
                    subprocess.run(['sudo', 'chown', f'{current_user}:{current_user}', temp_gdb], check=True, timeout=5)
                    if not os.access(temp_gdb, os.R_OK):
                        raise Exception("El archivo GDB no es legible después de todos los intentos")
                    logger.info(f"✅ Permisos corregidos en último intento")
                except Exception as e:
                    logger.error(f"❌ Error final estableciendo permisos: {e}")
                    raise Exception(f"No se pudieron establecer permisos de lectura para el archivo GDB")
            
            # Verificar propietario final
            try:
                final_stat = os.stat(temp_gdb)
                final_owner = pwd.getpwuid(final_stat.st_uid).pw_name if final_stat.st_uid else 'unknown'
                logger.info(f"✅ Permisos verificados: archivo GDB es legible, propietario: {final_owner}, permisos: {oct(final_stat.st_mode)[-3:]}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo verificar propietario final: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error crítico estableciendo permisos del GDB: {e}", exc_info=True)
            # No fallar la tarea, pero registrar el error
            # El usuario puede intentar cambiar permisos manualmente si es necesario
        
        logger.info(f"✅ Backup convertido exitosamente a GDB: {temp_gdb}")
        
        # Enviar correo con el link de descarga
        from django.core.mail import EmailMessage
        from django.conf import settings
        
        # Construir URL de descarga segura (usar el dominio del backend API)
        # Esta URL es pública y no requiere autenticación, solo el token
        # No expone información del backend ni frontend, solo el token seguro
        api_url = getattr(settings, 'API_PUBLIC_URL', None) or getattr(settings, 'FRONTEND_URL', 'https://api.eddeso.com')
        download_url = f"{api_url}/api/backups/descargar/{descarga.token}/?formato=gdb"
        
        # Obtener tamaño del archivo GDB
        gdb_size_mb = 0
        if os.path.exists(temp_gdb):
            gdb_size_mb = os.path.getsize(temp_gdb) / (1024 * 1024)
        
        # Template HTML bonito similar al de scraping
        message_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .container {{
            background-color: #f9f9f9;
            border-radius: 8px;
            padding: 30px;
            border: 1px solid #e0e0e0;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
            margin: -30px -30px 20px -30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .details {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #667eea;
        }}
        .details p {{
            margin: 8px 0;
        }}
        .details strong {{
            color: #667eea;
        }}
        .download-button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 40px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            font-size: 16px;
            margin: 20px 0;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
        }}
        .download-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
        }}
        .button-container {{
            text-align: center;
            margin: 30px 0;
        }}
        .warning {{
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 6px;
            padding: 15px;
            margin: 20px 0;
            color: #856404;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #666;
            font-size: 12px;
        }}
        .file-info {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin: 15px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💾 Backup GDB Listo</h1>
        </div>
        
        <p>Hola,</p>
        <p>Se ha generado tu archivo GDB del backup de la empresa <strong>{empresa.nombre}</strong>.</p>
        
        <div class="details">
            <p><strong>Empresa:</strong> {empresa.nombre}</p>
            <p><strong>NIT:</strong> {empresa.nit_normalizado}</p>
            <p><strong>Formato:</strong> GDB (Firebird Database)</p>
            <p><strong>Tamaño:</strong> {gdb_size_mb:.2f} MB</p>
            <p><strong>Fecha de conversión:</strong> {descarga.fecha_creacion.strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
        
        <div class="button-container">
            <a href="{download_url}" class="download-button" target="_blank">
                ⬇️ Descargar Archivo GDB
            </a>
        </div>
        
        <div class="file-info">
            <p><strong>📋 Información del archivo:</strong></p>
            <p>Este archivo GDB es una base de datos Firebird lista para usar. Puedes restaurarla directamente usando <code>gbak -c</code> o conectarte a ella con cualquier cliente Firebird.</p>
        </div>
        
        <div class="warning">
            <strong>⚠️ IMPORTANTE:</strong> Este link expirará el {descarga.fecha_expiracion.strftime('%d/%m/%Y a las %H:%M')}. Descarga el archivo lo antes posible.
        </div>
        
        <div class="footer">
            <p>Saludos,<br>Sistema de Backups TNS</p>
            <p style="margin-top: 10px; font-size: 11px; color: #999;">
                Si el botón no funciona, copia y pega este link en tu navegador:<br>
                <a href="{download_url}" style="color: #667eea; word-break: break-all;">{download_url}</a>
            </p>
            <p style="margin-top: 10px; font-size: 11px; color: #999;">
                Si no solicitaste esta descarga, puedes ignorar este correo.
            </p>
        </div>
    </div>
</body>
</html>'''
        
        # Enviar correo
        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eddeso.com')
            email_msg = EmailMessage(
                subject=f'💾 Backup GDB Listo - {empresa.nombre}',
                body=message_html,
                from_email=from_email,
                to=[descarga.email],
            )
            email_msg.content_subtype = "html"
            email_msg.send(fail_silently=False)
            logger.info(f"✅ Correo enviado exitosamente a {descarga.email}")
        except Exception as e:
            logger.error(f"❌ Error enviando correo: {e}", exc_info=True)
            # No fallar la tarea si falla el correo, el link ya está listo
        
        return {
            'status': 'SUCCESS',
            'mensaje': 'Backup convertido y correo enviado exitosamente',
            'token': descarga.token
        }
        
    except DescargaTemporalBackup.DoesNotExist:
        logger.error(f"❌ DescargaTemporalBackup {descarga_temporal_id} no encontrado")
        return {
            'status': 'ERROR',
            'error': 'Descarga temporal no encontrada'
        }
    except Exception as e:
        logger.error(f"❌ Error en convertir_backup_a_gdb_task: {e}", exc_info=True)
        try:
            descarga = DescargaTemporalBackup.objects.get(id=descarga_temporal_id)
            descarga.estado = 'expirado'
            descarga.save()
        except:
            pass
        return {
            'status': 'ERROR',
            'error': str(e)
        }


@shared_task(bind=True, name='sistema_analitico.enviar_backup_fbk_por_email')
def enviar_backup_fbk_por_email_task(self, descarga_temporal_id: int):
    """
    Tarea Celery para enviar un backup FBK por correo con link de descarga seguro.
    Similar a convertir_backup_a_gdb_task pero para FBK (no requiere conversión).
    
    Args:
        descarga_temporal_id: ID del registro DescargaTemporalBackup
        
    Returns:
        dict con resultado del envío
    """
    from .models import DescargaTemporalBackup, ConfiguracionS3
    from .services.backup_s3_service import BackupS3Service
    from django.core.mail import EmailMessage
    from django.conf import settings
    from django.urls import reverse
    import tempfile
    import os
    
    try:
        descarga = DescargaTemporalBackup.objects.get(id=descarga_temporal_id)
        backup = descarga.backup
        empresa = backup.empresa_servidor
        
        # Actualizar estado
        descarga.estado = 'listo'  # Para FBK no necesitamos conversión, está listo inmediatamente
        descarga.save()
        
        logger.info(f"📧 Enviando backup FBK {backup.id} por email a {descarga.email}")
        
        # Generar URL de descarga directa usando el token
        # El endpoint descargar_backup_token ya existe y maneja la descarga con token
        # Usar la misma lógica que GDB para consistencia
        api_url = getattr(settings, 'API_PUBLIC_URL', None) or getattr(settings, 'FRONTEND_URL', 'https://api.eddeso.com')
        download_url = f"{api_url}/api/backups/descargar/{descarga.token}/?formato=fbk"
        
        # Obtener nombre del archivo o generar uno por defecto
        nombre_archivo = backup.nombre_archivo if backup.nombre_archivo else f"backup_{empresa.nit_normalizado}_{backup.fecha_backup.strftime('%Y%m%d_%H%M%S')}.fbk"
        
        # Template HTML bonito similar al de scraping
        message_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .container {{
            background-color: #f9f9f9;
            border-radius: 8px;
            padding: 30px;
            border: 1px solid #e0e0e0;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
            margin: -30px -30px 20px -30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .details {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #667eea;
        }}
        .details p {{
            margin: 8px 0;
        }}
        .details strong {{
            color: #667eea;
        }}
        .download-button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 40px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            font-size: 16px;
            margin: 20px 0;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
        }}
        .download-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
        }}
        .button-container {{
            text-align: center;
            margin: 30px 0;
        }}
        .warning {{
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 6px;
            padding: 15px;
            margin: 20px 0;
            color: #856404;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #666;
            font-size: 12px;
        }}
        .file-info {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin: 15px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💾 Backup FBK Listo</h1>
        </div>
        
        <p>Hola,</p>
        <p>Se ha solicitado la descarga del backup FBK para la empresa <strong>{empresa.nombre}</strong>.</p>
        
        <div class="details">
            <p><strong>Empresa:</strong> {empresa.nombre}</p>
            <p><strong>NIT:</strong> {empresa.nit_normalizado}</p>
            <p><strong>Archivo:</strong> {nombre_archivo}</p>
            <p><strong>Formato:</strong> FBK (Firebird Backup)</p>
            <p><strong>Fecha del backup:</strong> {backup.fecha_backup.strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p><strong>Tamaño:</strong> {backup.tamano_gb:.2f} GB</p>
        </div>
        
        <div class="button-container">
            <a href="{download_url}" class="download-button" target="_blank">
                ⬇️ Descargar Archivo FBK
            </a>
        </div>
        
        <div class="file-info">
            <p><strong>📋 Información del archivo:</strong></p>
            <p>Este archivo FBK es un backup completo de la base de datos Firebird. Puedes restaurarlo usando <code>gbak -c</code> o cualquier herramienta de gestión de Firebird.</p>
        </div>
        
        <div class="warning">
            <strong>⚠️ IMPORTANTE:</strong> Este link expirará el {descarga.fecha_expiracion.strftime('%d/%m/%Y a las %H:%M')}. Descarga el archivo lo antes posible.
        </div>
        
        <div class="footer">
            <p>Saludos,<br>Sistema de Backups TNS</p>
            <p style="margin-top: 10px; font-size: 11px; color: #999;">
                Si el botón no funciona, copia y pega este link en tu navegador:<br>
                <a href="{download_url}" style="color: #667eea; word-break: break-all;">{download_url}</a>
            </p>
            <p style="margin-top: 10px; font-size: 11px; color: #999;">
                Si no solicitaste esta descarga, puedes ignorar este correo.
            </p>
        </div>
    </div>
</body>
</html>'''
        
        # Enviar correo con formato HTML
        from django.core.mail import EmailMessage
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eddeso.com')
        email_msg = EmailMessage(
            subject=f'💾 Backup FBK Listo - {empresa.nombre}',
            body=message_html,
            from_email=from_email,
            to=[descarga.email],
        )
        email_msg.content_subtype = "html"
        email_msg.send(fail_silently=False)
        
        # Actualizar estado
        descarga.estado = 'listo'
        descarga.save()
        
        logger.info(f"✅ Email enviado exitosamente a {descarga.email} para backup {backup.id}")
        
        return {
            'status': 'SUCCESS',
            'email': descarga.email,
            'download_url': download_url
        }
        
    except DescargaTemporalBackup.DoesNotExist:
        logger.error(f"❌ DescargaTemporalBackup {descarga_temporal_id} no encontrado")
        return {
            'status': 'ERROR',
            'error': 'Descarga temporal no encontrada'
        }
    except Exception as e:
        logger.error(f"❌ Error en enviar_backup_fbk_por_email_task: {e}", exc_info=True)
        try:
            descarga = DescargaTemporalBackup.objects.get(id=descarga_temporal_id)
            descarga.estado = 'expirado'
            descarga.save()
        except:
            pass
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