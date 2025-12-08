import asyncio
import re
import logging
from pathlib import Path
from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from django.conf import settings
from django.db import models
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from django.utils.dateparse import parse_date
from django.utils import timezone
from apps.sistema_analitico.models import APIKeyCliente
from .models import ScrapingSession, DocumentProcessed, DescargaTemporalDianZip, EventoApidianEnviado
from .serializers import ScrapingSessionSerializer, DocumentProcessedSerializer, GenerarAcusesSerializer
from .tasks import run_dian_scraping_task
from .services.dian_scraper import DianScraperService

logger = logging.getLogger(__name__)


def _attach_api_key(request):
    api_key = request.META.get('HTTP_API_KEY')
    print(f"🔍 [DEBUG] HTTP_API_KEY: {api_key}")
    
    if not api_key:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        print(f"🔍 [DEBUG] HTTP_AUTHORIZATION: {auth_header}")
        if auth_header.startswith('Api-Key '):
            api_key = auth_header.replace('Api-Key ', '')
            print(f"🔍 [DEBUG] API Key extraída de Authorization: {api_key[:20]}...")
    
    if not api_key:
        print("❌ [DEBUG] No se encontró API Key en los headers")
        return False
    
    print(f"🔍 [DEBUG] Buscando API Key: {api_key[:20]}...")
    try:
        api_key_obj = APIKeyCliente.objects.get(api_key__iexact=api_key.strip(), activa=True)
        print(f"✅ [DEBUG] API Key encontrada: ID={api_key_obj.id}, NIT={api_key_obj.nit}")
        if api_key_obj.esta_expirada():
            print(f"❌ [DEBUG] API Key expirada: {api_key_obj.fecha_caducidad}")
            return False
        
        # Si permite_scraping_total está activo, no validar empresas
        if api_key_obj.permite_scraping_total:
            api_key_obj.incrementar_contador()
            request.cliente_api = api_key_obj
            request.empresas_autorizadas = []  # Lista vacía = sin restricciones
            request.scraping_sin_restricciones = True  # Flag para identificar acceso total
            return True
        
        # Validación normal: verificar empresas asociadas
        empresas = api_key_obj.empresas_asociadas.all()
        if not empresas.exists():
            api_key_obj.actualizar_empresas_asociadas()
            empresas = api_key_obj.empresas_asociadas.all()
        api_key_obj.incrementar_contador()
        request.cliente_api = api_key_obj
        request.empresas_autorizadas = empresas
        request.scraping_sin_restricciones = False
        return True
    except APIKeyCliente.DoesNotExist:
        print(f"❌ [DEBUG] API Key no encontrada en la base de datos")
        return False
    except Exception as e:
        print(f"❌ [DEBUG] Error al validar API Key: {e}")
        import traceback
        traceback.print_exc()
        return False


class AllowAuthenticatedOrAPIKey(BasePermission):
    def has_permission(self, request, view):
        print(f"🔍 [DEBUG] Verificando permisos para {request.method} {request.path}")
        
        # Intentar autenticar con API Key
        if _attach_api_key(request):
            print("✅ [DEBUG] Autenticado con API Key")
            return True
        
        # Intentar autenticar con usuario
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            print(f"✅ [DEBUG] Autenticado con usuario: {user.username}")
            return True
        
        print("❌ [DEBUG] No se pudo autenticar ni con API Key ni con usuario")
        return False

class ScrapingSessionViewSet(viewsets.ModelViewSet):
    queryset = ScrapingSession.objects.all()
    serializer_class = ScrapingSessionSerializer
    permission_classes = [AllowAuthenticatedOrAPIKey]
    
    @action(detail=True, methods=['post'])
    def start_scraping(self, request, pk=None):
        """Inicia el proceso de scraping para una sesion"""
        session = self.get_object()

        if session.status == 'running':
            return Response(
                {'error': 'El scraping ya esta en ejecucion'},
                status=status.HTTP_400_BAD_REQUEST
            )

        run_dian_scraping_task.delay(session.id)

        return Response({
            'message': 'Scraping iniciado',
            'session_id': session.id
        })

    @action(detail=True, methods=['get'])
    def download_excel(self, request, pk=None):
        """Descarga el archivo Excel generado"""
        session = self.get_object()

        if not session.excel_file:
            return Response(
                {'error': 'No hay archivo Excel disponible'},
                status=status.HTTP_404_NOT_FOUND
            )

        file_path = session.excel_file.path
        response = FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=f"dian_export_{session.id}.xlsx"
        )
        return response

    @action(detail=True, methods=['get'])
    def download_json(self, request, pk=None):
        """Descarga el archivo JSON generado"""
        session = self.get_object()

        if not session.json_file:
            return Response(
                {'error': 'No hay archivo JSON disponible'},
                status=status.HTTP_404_NOT_FOUND
            )

        file_path = session.json_file.path
        response = FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=f"dian_export_{session.id}.json"
        )
        return response

    @action(detail=True, methods=['post'])
    def generar_acuses(self, request, pk=None):
        """
        Genera acuses automáticos para todos los documentos de una sesión.
        
        Body:
            cedula: Número de identificación del emisor
            primer_nombre: Primer nombre del emisor
            segundo_nombre: Segundo nombre del emisor (opcional)
            departamento: Departamento del emisor (default: CONTABILIDAD)
            cargo: Cargo del emisor
            eventos: Lista de IDs de eventos a aplicar (1-7)
        """
        import logging
        from apidian.services.apidian_client import ApidianAPIClient
        import time
        
        logger = logging.getLogger(__name__)
        
        session = self.get_object()
        
        if session.status != 'completed':
            return Response(
                {'error': 'La sesión debe estar completada para generar acuses'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar datos
        serializer = GenerarAcusesSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        datos = serializer.validated_data
        eventos_ids = datos['eventos']
        
        # Obtener todos los documentos de la sesión con CUFE
        documentos = DocumentProcessed.objects.filter(
            session=session,
            cufe__isnull=False
        ).exclude(cufe='')
        
        if not documentos.exists():
            return Response(
                {'error': 'No se encontraron documentos con CUFE en esta sesión'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 🔥 OBTENER NIT SEGÚN TIPO DE SESIÓN
        # Si es "Received" (recibidos), usar customer_nit
        # Si es "Sent" (enviados), usar supplier_nit
        nit = None
        primer_documento = documentos.first()
        if session.tipo == 'Received':
            nit = primer_documento.customer_nit
            logger.info(f"📥 [ACUSES] Sesión tipo Received, usando customer_nit: {nit}")
        else:  # Sent
            nit = primer_documento.supplier_nit
            logger.info(f"📤 [ACUSES] Sesión tipo Sent, usando supplier_nit: {nit}")
        
        if not nit:
            return Response(
                {'error': f'No se pudo determinar el NIT para sesión tipo {session.tipo}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 🔥 OBTENER CREDENCIALES DESDE BCE
        logger.info(f"🔍 [ACUSES] Obteniendo credenciales para NIT: {nit}")
        try:
            import requests
            from django.conf import settings
            
            # URL del backend BCE (configurable)
            bce_api_url = getattr(settings, 'BCE_API_URL', 'http://localhost:8000')
            credenciales_url = f"{bce_api_url}/api/dian/obtener-credenciales-por-nit/"
            
            response_credenciales = requests.post(
                credenciales_url,
                json={'nit': nit},
                timeout=10
            )
            
            if response_credenciales.status_code != 200:
                logger.warning(f"⚠️ [ACUSES] No se pudieron obtener credenciales desde BCE (status {response_credenciales.status_code})")
                logger.warning(f"⚠️ [ACUSES] Response text: {response_credenciales.text[:500]}")
                credenciales_data = None
            else:
                credenciales_data = response_credenciales.json()
                logger.info(f"✅ [ACUSES] Credenciales obtenidas desde BCE")
                logger.info(f"📋 [ACUSES] Credenciales recibidas (keys): {list(credenciales_data.keys()) if credenciales_data else 'None'}")
                logger.info(f"📋 [ACUSES] Credenciales completas: {credenciales_data}")
                # Imprimir literalmente el response de BCE
                print("=" * 80)
                print("📥 [ACUSES] RESPONSE EXACTO DE BCE (obtener-credenciales-por-nit):")
                print(f"Status Code: {response_credenciales.status_code}")
                print(f"Body: {credenciales_data}")
                print("=" * 80)
        except Exception as e:
            logger.warning(f"⚠️ [ACUSES] Error obteniendo credenciales desde BCE: {e}, usando valores por defecto")
            credenciales_data = None
        
        # 🔥 LLENAR PAYLOAD AUTOMÁTICAMENTE
        # identification_number: el NIT
        # first_name: "Pasante"
        # last_name: u.name recortado a 15 caracteres máximo
        # organization_department: "CONTABILIDAD"
        # job_title: "Aux Contable"
        
        user_name = credenciales_data.get('user', {}).get('name', '') if credenciales_data else ''
        last_name = user_name[:15] if user_name else ''
        
        cedula = datos.get('cedula') or nit  # Si no se proporciona, usar el NIT
        primer_nombre = datos.get('primer_nombre') or 'Pasante'
        segundo_nombre = datos.get('segundo_nombre', '')
        departamento = datos.get('departamento') or 'CONTABILIDAD'
        cargo = datos.get('cargo') or 'Aux Contable'
        
        # Si se obtuvo last_name desde credenciales, usarlo
        if credenciales_data and not datos.get('segundo_nombre'):
            segundo_nombre = last_name
        
                    # 🔥 OBTENER API TOKEN DESDE CREDENCIALES
        api_token = None
        if credenciales_data:
            api_token = credenciales_data.get('api_token') or credenciales_data.get('token')
            logger.info(f"🔑 [ACUSES] API Token desde credenciales: {'✅' if api_token else '❌'}")
            if api_token:
                logger.info(f"🔑 [ACUSES] API Token (primeros 10 chars): {api_token[:10]}...")
            else:
                logger.warning(f"⚠️ [ACUSES] No se encontró api_token en credenciales_data")
                logger.warning(f"⚠️ [ACUSES] Keys disponibles en credenciales_data: {list(credenciales_data.keys()) if credenciales_data else 'None'}")
        
        # Si no hay token desde credenciales, usar el del settings
        if not api_token:
            api_token = getattr(settings, 'TOKEN_API_DIAN_BASIC', '')
            logger.info(f"🔑 [ACUSES] Usando TOKEN_API_DIAN_BASIC del settings: {'✅' if api_token else '❌'}")
        
        logger.info(f"🔑 [ACUSES] API Token final: {'✅' if api_token else '❌'}")
        logger.info(f"👤 [ACUSES] Payload automático:")
        logger.info(f"   - identification_number: {cedula}")
        logger.info(f"   - first_name: {primer_nombre}")
        logger.info(f"   - last_name: {segundo_nombre}")
        logger.info(f"   - organization_department: {departamento}")
        logger.info(f"   - job_title: {cargo}")
        
        # 🔥 VERIFICAR VENCIMIENTOS Y ENVIAR EMAIL SI ES NECESARIO
        if credenciales_data:
            try:
                # Llamar al método de verificación de vencimientos en BCE
                email_backend = getattr(settings, 'EMAIL_HOST_USER', None)
                vencimientos_url = f"{bce_api_url}/api/dian/verificar-vencimientos/"
                requests.post(
                    vencimientos_url,
                    json={
                        'credenciales': credenciales_data,
                        'email_backend': email_backend
                    },
                    timeout=10
                )
            except Exception as e:
                logger.warning(f"⚠️ [ACUSES] Error verificando vencimientos: {e}")
        
        # Diccionario de eventos
        eventos_nombres = {
            1: "Acuse de recibo de Factura Electrónica de Venta",
            2: "Reclamo de la Factura Electrónica de Venta",
            3: "Recibo del bien y/o prestación del servicio",
            4: "Aceptación expresa",
            5: "Aceptación Tácita",
            6: "Documento validado por la DIAN",
            7: "Documento rechazado por la DIAN"
        }
        
        # Inicializar cliente APIDIAN
        apidian_client = ApidianAPIClient()
        
        # Procesar secuencialmente
        resultados = []
        total_procesados = 0
        exitosos = 0
        fallidos = 0
        
        logger.info(f"🔄 Iniciando generación de acuses para sesión {session.id}")
        logger.info(f"📊 Documentos a procesar: {documentos.count()}")
        logger.info(f"📋 Eventos seleccionados: {[eventos_nombres.get(e, f'Evento {e}') for e in eventos_ids]}")
        
        for documento in documentos:
            cufe = documento.cufe.strip()
            if not cufe:
                continue
            
            for evento_id in eventos_ids:
                total_procesados += 1
                
                try:
                    # Obtener el XML del documento desde el archivo físico
                    xml_content = None
                    xml_filename = None
                    
                    # Construir ruta esperada del XML en dian_facturas/session_{session_id}/
                    from pathlib import Path
                    from django.conf import settings
                    import os
                    
                    facturas_dir = Path(settings.MEDIA_ROOT) / 'dian_facturas' / f'session_{session.id}'
                    
                    # Buscar el XML por nombre esperado: {nit_emisor}_{prefijo}_{numero}.xml
                    supplier_nit = documento.supplier_nit or ''
                    customer_nit = documento.customer_nit or ''
                    # Determinar NIT emisor según tipo de sesión
                    nit_emisor = supplier_nit if session.tipo == 'Received' else customer_nit
                    
                    # Intentar construir nombre de archivo desde raw_data
                    raw_data = documento.raw_data or {}
                    prefix = raw_data.get('prefix', '')
                    number = raw_data.get('number', '')
                    
                    if prefix and number:
                        xml_filename_esperado = f"{nit_emisor}_{prefix}_{number}.xml"
                        xml_path = facturas_dir / xml_filename_esperado
                        
                        if xml_path.exists():
                            try:
                                with open(xml_path, 'rb') as f:
                                    xml_content = f.read()
                                xml_filename = xml_filename_esperado
                                logger.debug(f"✅ XML encontrado: {xml_filename_esperado}")
                            except Exception as e:
                                logger.warning(f"⚠️ Error leyendo XML {xml_filename_esperado}: {e}")
                    
                    # Si no se encontró, buscar cualquier XML que contenga el CUFE en el nombre
                    if not xml_content and facturas_dir.exists():
                        for xml_file in facturas_dir.glob("*.xml"):
                            try:
                                # Leer el XML y verificar si contiene el CUFE
                                with open(xml_file, 'rb') as f:
                                    content = f.read()
                                if cufe.encode('utf-8') in content or cufe[:20].encode('utf-8') in content:
                                    xml_content = content
                                    xml_filename = xml_file.name
                                    logger.debug(f"✅ XML encontrado por CUFE: {xml_filename}")
                                    break
                            except Exception as e:
                                logger.warning(f"⚠️ Error leyendo XML {xml_file.name}: {e}")
                    
                    # Si aún no hay XML, intentar desde raw_data (si tiene el XML completo)
                    if not xml_content and raw_data:
                        # Algunos sistemas guardan el XML completo en raw_data
                        xml_str = raw_data.get('xml_content') or raw_data.get('xml')
                        if xml_str:
                            xml_content = xml_str.encode('utf-8') if isinstance(xml_str, str) else xml_str
                            xml_filename = f"documento_{cufe[:20]}.xml"
                            logger.debug(f"✅ XML obtenido desde raw_data")
                    
                    # Si no hay XML, no podemos enviar el evento
                    if not xml_content:
                        raise ValueError(f"No se encontró contenido XML para el documento con CUFE {cufe[:20]}... (Buscado en {facturas_dir})")
                    
                    # Convertir a base64
                    import base64
                    if isinstance(xml_content, str):
                        xml_base64 = base64.b64encode(xml_content.encode('utf-8')).decode('utf-8')
                    else:
                        xml_base64 = base64.b64encode(xml_content).decode('utf-8')
                    
                    # Construir payload según formato requerido por APIDIAN
                    payload = {
                        "event_id": evento_id,
                        "allow_cash_documents": False,
                        "sendmail": False,
                        "base64_attacheddocument_name": xml_filename or f"documento_{cufe[:20]}.xml",
                        "base64_attacheddocument": xml_base64,
                        "type_rejection_id": None,
                        "resend_consecutive": False
                    }
                    
                    logger.info(f"📤 [ACUSES] Enviando evento {evento_id} para CUFE {cufe[:20]}...")
                    
                    # Enviar a APIDIAN usando requests directamente
                    import requests
                    from django.conf import settings
                    
                    apidian_url = getattr(settings, 'API_DIAN_ROUTE', 'http://45.149.204.184:81')
                    send_event_url = f"{apidian_url}/api/ubl2.1/send-event"
                    
                    # Usar el api_token obtenido desde credenciales
                    token = api_token
                    
                    headers = {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'Authorization': f'Bearer {token}' if token else ''
                    }
                    
                    # 🔥 LOGGING DETALLADO DEL REQUEST
                    logger.info(f"🌐 [ACUSES] URL APIDIAN: {send_event_url}")
                    logger.info(f"🔑 [ACUSES] Token usado (primeros 10 chars): {token[:10] if token else 'NO HAY TOKEN'}...")
                    logger.info(f"📋 [ACUSES] Payload enviado (sin base64):")
                    payload_log = payload.copy()
                    if 'base64_attacheddocument' in payload_log:
                        payload_log['base64_attacheddocument'] = f"[BASE64: {len(payload['base64_attacheddocument'])} chars]"
                    logger.info(f"   {payload_log}")
                    
                    response = requests.post(
                        send_event_url,
                        json=payload,
                        headers=headers,
                        timeout=30
                    )
                    
                    # 🔥 LOGGING DETALLADO DEL RESPONSE
                    logger.info(f"📥 [ACUSES] Response Status Code: {response.status_code}")
                    logger.info(f"📥 [ACUSES] Response Headers: {dict(response.headers)}")
                    
                    try:
                        resultado_api = response.json()
                        logger.info(f"📥 [ACUSES] Response Body (JSON):")
                        logger.info(f"   {resultado_api}")
                    except Exception as e:
                        resultado_api = {'raw_text': response.text}
                        logger.error(f"❌ [ACUSES] Error parseando JSON del response: {e}")
                        logger.error(f"❌ [ACUSES] Response Text (primeros 500 chars): {response.text[:500]}")
                    
                    # Imprimir el response completo literalmente
                    print("=" * 80)
                    print("📥 [ACUSES] RESPONSE EXACTO DE APIDIAN:")
                    print(f"Status Code: {response.status_code}")
                    print(f"Headers: {dict(response.headers)}")
                    print(f"Body: {resultado_api}")
                    print("=" * 80)
                    
                    response.raise_for_status()
                    
                    # Guardar en BD
                    EventoApidianEnviado.objects.update_or_create(
                        session=session,
                        cufe=cufe,
                        evento_id=evento_id,
                        defaults={
                            'documento': documento,
                            'evento_nombre': eventos_nombres.get(evento_id, f'Evento {evento_id}'),
                            'estado': 'exitoso',
                            'error': None,
                            'respuesta_api': resultado_api,
                            'emisor_cedula': cedula,
                            'emisor_primer_nombre': primer_nombre,
                            'emisor_segundo_nombre': segundo_nombre,
                            'emisor_departamento': departamento,
                            'emisor_cargo': cargo,
                        }
                    )
                    
                    exitosos += 1
                    resultados.append({
                        'cufe': cufe,
                        'evento_id': evento_id,
                        'evento_nombre': eventos_nombres.get(evento_id, f'Evento {evento_id}'),
                        'estado': 'exitoso',
                        'respuesta': resultado_api
                    })
                    
                    logger.info(f"✅ Evento {evento_id} enviado exitosamente para CUFE {cufe[:20]}...")
                    
                    # Pequeña pausa entre envíos para no sobrecargar
                    time.sleep(0.5)
                    
                except requests.exceptions.RequestException as e:
                    fallidos += 1
                    error_msg = str(e)
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            error_msg = e.response.json().get('message', error_msg)
                        except:
                            error_msg = e.response.text or error_msg
                    
                    # Guardar en BD
                    EventoApidianEnviado.objects.update_or_create(
                        session=session,
                        cufe=cufe,
                        evento_id=evento_id,
                        defaults={
                            'documento': documento,
                            'evento_nombre': eventos_nombres.get(evento_id, f'Evento {evento_id}'),
                            'estado': 'fallido',
                            'error': error_msg,
                            'respuesta_api': None,
                            'emisor_cedula': cedula,
                            'emisor_primer_nombre': primer_nombre,
                            'emisor_segundo_nombre': segundo_nombre,
                            'emisor_departamento': departamento,
                            'emisor_cargo': cargo,
                        }
                    )
                    
                    resultados.append({
                        'cufe': cufe,
                        'evento_id': evento_id,
                        'evento_nombre': eventos_nombres.get(evento_id, f'Evento {evento_id}'),
                        'estado': 'fallido',
                        'error': error_msg
                    })
                    
                    logger.error(f"❌ Error enviando evento {evento_id} para CUFE {cufe[:20]}...: {error_msg}")
                    
                except Exception as e:
                    fallidos += 1
                    error_msg = str(e)
                    
                    # Guardar en BD
                    EventoApidianEnviado.objects.update_or_create(
                        session=session,
                        cufe=cufe,
                        evento_id=evento_id,
                        defaults={
                            'documento': documento,
                            'evento_nombre': eventos_nombres.get(evento_id, f'Evento {evento_id}'),
                            'estado': 'fallido',
                            'error': error_msg,
                            'respuesta_api': None,
                            'emisor_cedula': cedula,
                            'emisor_primer_nombre': primer_nombre,
                            'emisor_segundo_nombre': segundo_nombre,
                            'emisor_departamento': departamento,
                            'emisor_cargo': cargo,
                        }
                    )
                    
                    resultados.append({
                        'cufe': cufe,
                        'evento_id': evento_id,
                        'evento_nombre': eventos_nombres.get(evento_id, f'Evento {evento_id}'),
                        'estado': 'fallido',
                        'error': error_msg
                    })
                    
                    logger.error(f"❌ Error inesperado enviando evento {evento_id} para CUFE {cufe[:20]}...: {error_msg}")
        
        logger.info(f"✅ Procesamiento completado: {exitosos} exitosos, {fallidos} fallidos de {total_procesados} totales")
        
        return Response({
            'message': 'Procesamiento de acuses completado',
            'resumen': {
                'total_documentos': documentos.count(),
                'total_eventos_enviados': total_procesados,
                'exitosos': exitosos,
                'fallidos': fallidos
            },
            'detalles': resultados
        })

    @action(detail=True, methods=['get'])
    def log_eventos(self, request, pk=None):
        """
        Obtiene el log de eventos APIDIAN enviados para esta sesión.
        Retorna resumen y detalles de eventos exitosos y fallidos.
        """
        session = self.get_object()
        
        eventos = EventoApidianEnviado.objects.filter(session=session).order_by('-fecha_envio')
        
        exitosos = eventos.filter(estado='exitoso')
        fallidos = eventos.filter(estado='fallido')
        
        return Response({
            'resumen': {
                'total': eventos.count(),
                'exitosos': exitosos.count(),
                'fallidos': fallidos.count()
            },
            'eventos': [{
                'id': e.id,
                'cufe': e.cufe,
                'evento_id': e.evento_id,
                'evento_nombre': e.evento_nombre,
                'estado': e.estado,
                'error': e.error,
                'fecha_envio': e.fecha_envio.isoformat() if e.fecha_envio else None,
                'emisor': {
                    'cedula': e.emisor_cedula,
                    'nombre_completo': f"{e.emisor_primer_nombre} {e.emisor_segundo_nombre}".strip(),
                    'departamento': e.emisor_departamento,
                    'cargo': e.emisor_cargo
                }
            } for e in eventos]
        })
    
    @action(detail=True, methods=['get'])
    def descargar_log_eventos_fallidos(self, request, pk=None):
        """
        Descarga un archivo TXT con el log de eventos fallidos para esta sesión.
        """
        import io
        from django.http import HttpResponse
        
        session = self.get_object()
        
        eventos_fallidos = EventoApidianEnviado.objects.filter(
            session=session,
            estado='fallido'
        ).order_by('-fecha_envio')
        
        if not eventos_fallidos.exists():
            return Response(
                {'error': 'No hay eventos fallidos para esta sesión'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Crear contenido del log
        contenido = []
        contenido.append("=" * 80)
        contenido.append(f"LOG DE EVENTOS FALLIDOS - SESIÓN #{session.id}")
        contenido.append("=" * 80)
        contenido.append(f"Fecha de generación: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        contenido.append(f"Total de eventos fallidos: {eventos_fallidos.count()}")
        contenido.append("")
        contenido.append("=" * 80)
        contenido.append("DETALLES DE EVENTOS FALLIDOS")
        contenido.append("=" * 80)
        contenido.append("")
        
        for evento in eventos_fallidos:
            contenido.append(f"Evento ID: {evento.evento_id} - {evento.evento_nombre}")
            contenido.append(f"CUFE: {evento.cufe}")
            contenido.append(f"Fecha de envío: {evento.fecha_envio.strftime('%Y-%m-%d %H:%M:%S') if evento.fecha_envio else 'N/A'}")
            contenido.append(f"Emisor: {evento.emisor_primer_nombre} {evento.emisor_segundo_nombre} ({evento.emisor_cedula})")
            contenido.append(f"Departamento: {evento.emisor_departamento}")
            contenido.append(f"Cargo: {evento.emisor_cargo}")
            contenido.append(f"Error: {evento.error}")
            contenido.append("-" * 80)
            contenido.append("")
        
        # Crear respuesta
        response = HttpResponse('\n'.join(contenido), content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="log_eventos_fallidos_sesion_{session.id}.txt"'
        
        return response

    @action(detail=True, methods=['post'])
    def send_by_email(self, request, pk=None):
        """
        Crea un link seguro de descarga y lo envía por email.
        Siempre usa link seguro, nunca adjunta el ZIP.
        
        Body:
            email: Email del destinatario
        """
        print("=" * 80)
        print("📧 [SEND_EMAIL] Iniciando creación de link seguro")
        print(f"📧 [SEND_EMAIL] Session ID: {pk}")
        print(f"📧 [SEND_EMAIL] Request data: {request.data}")
        
        from django.core.mail import EmailMessage
        from django.conf import settings
        from django.utils import timezone
        from datetime import timedelta
        import zipfile
        import os
        from pathlib import Path
        
        session = self.get_object()
        print(f"📧 [SEND_EMAIL] Sesión obtenida: ID={session.id}, Status={session.status}")
        
        if session.status != 'completed':
            print(f"❌ [SEND_EMAIL] Sesión no completada: {session.status}")
            return Response(
                {'error': 'La sesión debe estar completada para enviar por email'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        email = request.data.get('email')
        print(f"📧 [SEND_EMAIL] Email recibido: {email}")
        
        if not email:
            print("❌ [SEND_EMAIL] No se recibió email")
            return Response(
                {'error': 'Se requiere un email'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar formato de email
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            print(f"❌ [SEND_EMAIL] Email inválido: {email}")
            return Response(
                {'error': 'Email inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print(f"✅ [SEND_EMAIL] Email válido: {email}")
        
        try:
            # Verificar si ya existe un ZIP permanente para esta sesión
            zip_permanente_dir = Path(settings.MEDIA_ROOT) / 'dian_exports'
            zip_permanente_dir.mkdir(exist_ok=True)
            zip_permanente_nombre = f'dian_export_session_{session.id}.zip'
            zip_permanente_path = zip_permanente_dir / zip_permanente_nombre
            
            zip_path = None
            archivos_agregados = []
            
            # Si existe el ZIP permanente, usarlo
            if zip_permanente_path.exists():
                print(f"✅ [SEND_EMAIL] ZIP permanente encontrado: {zip_permanente_path}")
                zip_path = zip_permanente_path
                # Contar archivos en el ZIP existente
                try:
                    with zipfile.ZipFile(zip_path, 'r') as existing_zip:
                        archivos_agregados = existing_zip.namelist()
                    print(f"📦 [SEND_EMAIL] ZIP existente contiene {len(archivos_agregados)} archivos")
                except Exception as e:
                    print(f"⚠️ [SEND_EMAIL] No se pudo leer el ZIP existente: {e}")
                    zip_path = None
            
            # Si no existe, crearlo
            if not zip_path or not zip_path.exists():
                print(f"📦 [SEND_EMAIL] Creando ZIP permanente desde los datos de la sesión...")
                
                # Crear registro de descarga temporal
                descarga_temporal = DescargaTemporalDianZip.crear_para_session(session, email)
                descarga_temporal.estado = 'procesando'
                descarga_temporal.save()
                print(f"✅ [SEND_EMAIL] Registro de descarga temporal creado: {descarga_temporal.token[:16]}...")
                
                # Crear ZIP permanente
                zip_path = zip_permanente_path
                print(f"📦 [SEND_EMAIL] Creando ZIP permanente en: {zip_path}")
                
                archivos_agregados = []
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    # Agregar JSON
                    if session.json_file:
                        json_path = session.json_file.path
                        print(f"📄 [SEND_EMAIL] Agregando JSON: {json_path}")
                        if Path(json_path).exists():
                            zip_file.write(json_path, 'resultado.json')
                            archivos_agregados.append('resultado.json')
                            print(f"✅ [SEND_EMAIL] JSON agregado: {Path(json_path).stat().st_size} bytes")
                        else:
                            print(f"⚠️ [SEND_EMAIL] JSON no existe: {json_path}")
                    else:
                        print("⚠️ [SEND_EMAIL] No hay archivo JSON en la sesión")
                    
                    # Agregar Excel
                    if session.excel_file:
                        excel_path = session.excel_file.path
                        print(f"📊 [SEND_EMAIL] Agregando Excel: {excel_path}")
                        if Path(excel_path).exists():
                            zip_file.write(excel_path, 'resultado.xlsx')
                            archivos_agregados.append('resultado.xlsx')
                            print(f"✅ [SEND_EMAIL] Excel agregado: {Path(excel_path).stat().st_size} bytes")
                        else:
                            print(f"⚠️ [SEND_EMAIL] Excel no existe: {excel_path}")
                    else:
                        print("⚠️ [SEND_EMAIL] No hay archivo Excel en la sesión")
                    
                    # Agregar carpeta "facturas" con XMLs y PDFs
                    facturas_dir = Path(settings.MEDIA_ROOT) / 'dian_facturas' / f'session_{session.id}'
                    print(f"📁 [SEND_EMAIL] Buscando facturas en: {facturas_dir}")
                    
                    if facturas_dir.exists():
                        print(f"✅ [SEND_EMAIL] Directorio de facturas existe")
                        # Agregar todos los XMLs
                        xml_files = list(facturas_dir.glob('*.xml'))
                        print(f"📄 [SEND_EMAIL] Encontrados {len(xml_files)} archivos XML")
                        for xml_file in xml_files:
                            zip_file.write(xml_file, f'facturas/{xml_file.name}')
                            archivos_agregados.append(f'facturas/{xml_file.name}')
                            print(f"  ✅ Agregado: {xml_file.name} ({xml_file.stat().st_size} bytes)")
                        
                        # Agregar todos los PDFs
                        pdf_files = list(facturas_dir.glob('*.pdf'))
                        print(f"📄 [SEND_EMAIL] Encontrados {len(pdf_files)} archivos PDF")
                        for pdf_file in pdf_files:
                            zip_file.write(pdf_file, f'facturas/{pdf_file.name}')
                            archivos_agregados.append(f'facturas/{pdf_file.name}')
                            print(f"  ✅ Agregado: {pdf_file.name} ({pdf_file.stat().st_size} bytes)")
                    else:
                        print(f"⚠️ [SEND_EMAIL] Directorio de facturas no existe: {facturas_dir}")
                    
                    # Agregar carpeta "ziporiginales" con los ZIPs descargados originales
                    ziporiginales_dir = facturas_dir / 'ziporiginales'
                    print(f"📦 [SEND_EMAIL] Buscando ZIPs originales en: {ziporiginales_dir}")
                    
                    if ziporiginales_dir.exists():
                        print(f"✅ [SEND_EMAIL] Directorio de ZIPs originales existe")
                        zip_originales = list(ziporiginales_dir.glob('*.zip'))
                        print(f"📦 [SEND_EMAIL] Encontrados {len(zip_originales)} archivos ZIP originales")
                        for zip_original in zip_originales:
                            zip_file.write(zip_original, f'ziporiginales/{zip_original.name}')
                            archivos_agregados.append(f'ziporiginales/{zip_original.name}')
                            print(f"  ✅ Agregado: {zip_original.name} ({zip_original.stat().st_size} bytes)")
                    else:
                        print(f"⚠️ [SEND_EMAIL] Directorio de ZIPs originales no existe: {ziporiginales_dir}")
                
                # Actualizar el modelo ScrapingSession con la ruta del ZIP permanente
                if not session.zip_file or not Path(session.zip_file.path).exists():
                    # Guardar la ruta relativa en el FileField
                    from django.core.files import File
                    with open(zip_path, 'rb') as f:
                        session.zip_file.save(zip_permanente_nombre, File(f), save=True)
                    print(f"✅ [SEND_EMAIL] ZIP permanente guardado en modelo: {session.zip_file.path}")
                
                print(f"📦 [SEND_EMAIL] ZIP permanente creado: {zip_path.stat().st_size} bytes, {len(archivos_agregados)} archivos")
            else:
                # Si el ZIP ya existía, crear el registro de descarga temporal
                descarga_temporal = DescargaTemporalDianZip.crear_para_session(session, email)
                descarga_temporal.estado = 'procesando'
                descarga_temporal.save()
                print(f"✅ [SEND_EMAIL] Registro de descarga temporal creado (ZIP existente): {descarga_temporal.token[:16]}...")
            
            zip_size = zip_path.stat().st_size
            print(f"📦 [SEND_EMAIL] ZIP final: {zip_size} bytes, {len(archivos_agregados)} archivos")
            
            # Crear una copia con el token para la descarga temporal (o usar el permanente directamente)
            # Para simplificar, usaremos el ZIP permanente directamente
            zip_descarga_path = zip_path
            
            # Actualizar registro con ruta del ZIP
            descarga_temporal.ruta_zip_temporal = str(zip_descarga_path)
            descarga_temporal.estado = 'listo'
            descarga_temporal.save()
            print(f"✅ [SEND_EMAIL] Registro actualizado con ruta del ZIP")
            
            # Actualizar registro con ruta del ZIP
            descarga_temporal.ruta_zip_temporal = str(zip_path)
            descarga_temporal.estado = 'listo'
            descarga_temporal.save()
            print(f"✅ [SEND_EMAIL] Registro actualizado con ruta del ZIP")
            
            # Preparar email con link seguro
            print("📧 [SEND_EMAIL] Preparando email con link seguro...")
            
            # Obtener número real de documentos procesados del JSON/Excel
            documentos_procesados = 0
            if session.json_file:
                try:
                    import json
                    with open(session.json_file.path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                        if isinstance(json_data, list):
                            documentos_procesados = len(json_data)
                        elif isinstance(json_data, dict) and 'documents' in json_data:
                            documentos_procesados = len(json_data['documents'])
                except Exception as e:
                    print(f"⚠️ [SEND_EMAIL] No se pudo leer JSON para contar documentos: {e}")
            
            # Mensaje más claro sobre la diferencia
            diferencia = session.documents_downloaded - documentos_procesados
            mensaje_diferencia = ""
            if diferencia > 0:
                mensaje_diferencia = f"\n\n⚠️ Nota: Se descargaron {session.documents_downloaded} archivos ZIP de la DIAN, pero solo {documentos_procesados} contenían documentos XML válidos. Los otros {diferencia} ZIPs pueden estar vacíos o no contener facturas válidas."
            
            # Generar link seguro
            api_public_url = getattr(settings, 'API_PUBLIC_URL', 'https://api.eddeso.com')
            # Asegurar que la URL no tenga doble barra
            api_public_url = api_public_url.rstrip('/')
            download_url = f"{api_public_url}/dian/api/download/{descarga_temporal.token}/"
            print(f"🔗 [SEND_EMAIL] URL generada: {download_url}")
            
            subject = f'Exportación DIAN - Sesión #{session.id}'
            
            # Mensaje en texto plano (fallback)
            message_text = f'''Hola,

Se ha generado un link seguro de descarga para los resultados del scraping de DIAN.

Detalles de la sesión:
- ID: {session.id}
- Tipo: {session.tipo}
- Fecha desde: {session.fecha_desde}
- Fecha hasta: {session.fecha_hasta}
- Archivos ZIP descargados: {session.documents_downloaded}
- Documentos XML procesados: {documentos_procesados}{mensaje_diferencia}

Link de descarga (válido por 1 día):
{download_url}

El archivo ZIP contiene:
- resultado.json: Datos estructurados en JSON ({documentos_procesados} documentos)
- resultado.xlsx: Datos en formato Excel (2 hojas, {documentos_procesados} documentos)
- facturas/: Carpeta con los archivos XML y PDF de las facturas procesadas
- ziporiginales/: Carpeta con los archivos ZIP originales descargados de la DIAN ({session.documents_downloaded} archivos)

⚠️ IMPORTANTE: Este link expirará en 24 horas. Descarga el archivo lo antes posible.

Saludos,
Sistema de Scraping DIAN'''
            
            # Mensaje HTML con botón bonito
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
        .file-list {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin: 15px 0;
        }}
        .file-list ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .file-list li {{
            margin: 5px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📦 Exportación DIAN Lista</h1>
        </div>
        
        <p>Hola,</p>
        <p>Se ha generado un link seguro de descarga para los resultados del scraping de DIAN.</p>
        
        <div class="details">
            <p><strong>ID de Sesión:</strong> {session.id}</p>
            <p><strong>Tipo:</strong> {session.tipo}</p>
            <p><strong>Fecha desde:</strong> {session.fecha_desde}</p>
            <p><strong>Fecha hasta:</strong> {session.fecha_hasta}</p>
            <p><strong>Archivos ZIP descargados:</strong> {session.documents_downloaded}</p>
            <p><strong>Documentos XML procesados:</strong> {documentos_procesados}</p>
        </div>
        
        <div class="button-container">
            <a href="{download_url}" class="download-button" target="_blank">
                ⬇️ Descargar Archivo ZIP
            </a>
        </div>
        
        <div class="file-list">
            <p><strong>El archivo ZIP contiene:</strong></p>
            <ul>
                <li><strong>resultado.json:</strong> Datos estructurados en JSON ({documentos_procesados} documentos)</li>
                <li><strong>resultado.xlsx:</strong> Datos en formato Excel (2 hojas, {documentos_procesados} documentos)</li>
                <li><strong>facturas/:</strong> Carpeta con los archivos XML y PDF de las facturas procesadas</li>
                <li><strong>ziporiginales/:</strong> Carpeta con los archivos ZIP originales descargados de la DIAN ({session.documents_downloaded} archivos)</li>
            </ul>
        </div>
        
        <div class="warning">
            <strong>⚠️ IMPORTANTE:</strong> Este link expirará en 24 horas. Descarga el archivo lo antes posible.
        </div>
        
        <div class="footer">
            <p>Saludos,<br>Sistema de Scraping DIAN</p>
            <p style="margin-top: 10px; font-size: 11px; color: #999;">
                Si el botón no funciona, copia y pega este link en tu navegador:<br>
                <a href="{download_url}" style="color: #667eea; word-break: break-all;">{download_url}</a>
            </p>
        </div>
    </div>
</body>
</html>'''
            
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eddeso.com')
            print(f"📧 [SEND_EMAIL] From: {from_email}")
            print(f"📧 [SEND_EMAIL] To: {email}")
            print(f"📧 [SEND_EMAIL] Subject: {subject}")
            print(f"📧 [SEND_EMAIL] Download URL: {download_url}")
            
            # Crear mensaje de email con HTML
            email_msg = EmailMessage(
                subject=subject,
                body=message_text,
                from_email=from_email,
                to=[email],
            )
            email_msg.content_subtype = "html"  # Cambiar a HTML
            email_msg.body = message_html  # Usar el HTML
            
            print(f"📧 [SEND_EMAIL] Enviando email...")
            # Enviar email
            resultado = email_msg.send(fail_silently=False)
            print(f"✅ [SEND_EMAIL] Email enviado. Resultado: {resultado}")
            
            return Response({
                'message': f'Link de descarga enviado exitosamente a {email}',
                'email': email,
                'download_url': download_url,
                'token': descarga_temporal.token,
                'expires_at': descarga_temporal.fecha_expiracion.isoformat(),
                'zip_size': zip_size,
                'archivos_incluidos': len(archivos_agregados)
            })
            
        except Exception as e:
            import traceback
            print(f"❌ [SEND_EMAIL] ERROR: {e}")
            print(f"❌ [SEND_EMAIL] Tipo de error: {type(e).__name__}")
            print("❌ [SEND_EMAIL] Traceback completo:")
            traceback.print_exc()
            print("=" * 80)
            
            # Marcar como fallido si existe el registro
            if 'descarga_temporal' in locals():
                descarga_temporal.estado = 'expirado'
                descarga_temporal.save()
            
            return Response(
                {'error': f'Error al crear link de descarga: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], authentication_classes=[], permission_classes=[AllowAny])
    def test_connection(self, request):
        """Prueba la conexion a DIAN (acceso sin autenticacion)"""
        import traceback
        
        try:
            _attach_api_key(request)
            url = request.data.get('url')

            if not url:
                return Response({
                    'error': True,
                    'message': 'URL requerida',
                    'statusCode': 400
                }, status=400)

            print(f"🧪 [TEST_CONNECTION] Probando conexión a: {url}")
            
            scraper = DianScraperService(0)  # Session ID temporal
            
            try:
                result = asyncio.run(scraper.test_dian_connection(url))
                
                if result:
                    print(f"✅ [TEST_CONNECTION] Conexión exitosa")
                    return Response({
                        'error': False,
                        'connected': True,
                        'message': 'Conexión exitosa'
                    })
                else:
                    print(f"❌ [TEST_CONNECTION] No se pudo conectar")
                    return Response({
                        'error': True,
                        'message': 'No se pudo conectar con el servicio DIAN',
                        'statusCode': 503,
                        'statusMessage': 'No se pudo conectar con el servicio DIAN'
                    }, status=503)
                    
            except Exception as scraper_error:
                print(f"❌ [TEST_CONNECTION] Error en scraper: {scraper_error}")
                print(f"❌ [TEST_CONNECTION] Tipo: {type(scraper_error).__name__}")
                traceback.print_exc()
                
                # Mensaje más específico según el tipo de error
                error_message = 'No se pudo conectar con el servicio DIAN'
                if 'timeout' in str(scraper_error).lower():
                    error_message = 'Timeout al conectar con DIAN. Verifica la URL y tu conexión.'
                elif 'playwright' in str(scraper_error).lower() or 'browser' in str(scraper_error).lower():
                    error_message = 'Error al inicializar el navegador. Verifica que Playwright esté instalado correctamente.'
                
                return Response({
                    'error': True,
                    'message': error_message,
                    'statusCode': 503,
                    'statusMessage': 'No se pudo conectar con el servicio DIAN',
                    'details': str(scraper_error)
                }, status=503)
                
        except Exception as e:
            print(f"❌ [TEST_CONNECTION] Error general: {e}")
            traceback.print_exc()
            return Response({
                'error': True,
                'message': f'Error inesperado: {str(e)}',
                'statusCode': 500,
                'statusMessage': 'Error interno del servidor'
            }, status=500)

    @action(detail=False, methods=['post'], authentication_classes=[], permission_classes=[AllowAny])
    def quick_scrape(self, request):
        """Endpoint rapido para iniciar scraping (acceso sin autenticacion)"""
        print("=" * 80)
        print("🔍 [QUICK_SCRAPE] Iniciando quick_scrape")
        print(f"🔍 [QUICK_SCRAPE] Request data: {request.data}")
        
        _attach_api_key(request)
        
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        print(f"🔍 [QUICK_SCRAPE] Validando serializer...")
        if not serializer.is_valid():
            print(f"❌ [QUICK_SCRAPE] Errores de validación: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        print(f"✅ [QUICK_SCRAPE] Serializer válido, guardando sesión...")
        session = serializer.save()
        print(f"✅ [QUICK_SCRAPE] Sesión creada: ID={session.id}")
        
        run_dian_scraping_task.delay(session.id)
        print(f"✅ [QUICK_SCRAPE] Tarea Celery iniciada")
        print("=" * 80)

        return Response({
            'message': 'Scraping iniciado',
            'session_id': session.id
        }, status=status.HTTP_201_CREATED)


class DocumentProcessedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DocumentProcessedSerializer
    permission_classes = [AllowAuthenticatedOrAPIKey]

    def get_queryset(self):
        queryset = DocumentProcessed.objects.all()
        params = self.request.query_params

        session_id = params.get('session_id')
        if session_id:
            queryset = queryset.filter(session_id=session_id)

        nit = params.get('nit')
        if nit:
            normalized = re.sub(r'\D', '', nit)
            queryset = queryset.filter(
                models.Q(supplier_nit=normalized) | models.Q(customer_nit=normalized)
            )

        tipo = params.get('tipo')
        if tipo:
            queryset = queryset.filter(session__tipo__iexact=tipo)

        fecha_desde = parse_date(params.get('fecha_desde')) if params.get('fecha_desde') else None
        fecha_hasta = parse_date(params.get('fecha_hasta')) if params.get('fecha_hasta') else None
        if fecha_desde:
            queryset = queryset.filter(issue_date__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(issue_date__lte=fecha_hasta)

        return queryset

    @action(detail=False, methods=['get'])
    def by_session(self, request):
        """Obtiene documentos por sesión"""
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response(
                {'error': 'session_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        documents = DocumentProcessed.objects.filter(session_id=session_id)
        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def export(self, request):
        """Descarga documentos filtrados en JSON o Excel"""
        queryset = self.filter_queryset(self.get_queryset())
        export_format = request.query_params.get('format', 'json').lower()

        docs = [doc.raw_data for doc in queryset if isinstance(doc.raw_data, dict)]
        if not docs:
            return Response({'error': 'No hay documentos para exportar'}, status=404)

        if export_format == 'excel':
            return self._export_excel(docs)
        return Response(docs)

    def _export_excel(self, documents):
        from .services.file_processor import FileProcessor
        processor = FileProcessor()
        result = processor._generate_output_files(documents, session_id=0)
        excel_path = Path(settings.MEDIA_ROOT) / result['excel_file']
        return FileResponse(open(excel_path, 'rb'), as_attachment=True, filename=excel_path.name)
    
    @action(detail=True, methods=['get'], url_path='descargar_pdf')
    def descargar_pdf(self, request, pk=None):
        """
        Descarga el PDF de un documento específico.
        Busca el PDF en dian_facturas/session_{session_id}/ con el formato {nit_emisor}_{prefijo}_{numero}.pdf
        """
        from pathlib import Path
        import os
        
        logger.info(f"📄 [DESCARGAR_PDF] ========== INICIO ==========")
        logger.info(f"📄 [DESCARGAR_PDF] Documento ID solicitado: {pk}")
        logger.info(f"📄 [DESCARGAR_PDF] URL completa: {request.build_absolute_uri()}")
        logger.info(f"📄 [DESCARGAR_PDF] Método: {request.method}")
        logger.info(f"📄 [DESCARGAR_PDF] Path: {request.path}")
        
        try:
            doc = self.get_object()
            logger.info(f"✅ [DESCARGAR_PDF] Documento encontrado: ID={doc.id}, número={doc.document_number}")
        except Exception as e:
            logger.error(f"❌ [DESCARGAR_PDF] Error obteniendo documento {pk}: {e}", exc_info=True)
            return Response(
                {'error': f'Documento {pk} no encontrado: {str(e)}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        session = doc.session
        logger.info(f"📄 [DESCARGAR_PDF] Sesión asociada: ID={session.id}, tipo={session.tipo}")
        
        # Construir ruta esperada del PDF
        facturas_dir = Path(settings.MEDIA_ROOT) / 'dian_facturas' / f'session_{session.id}'
        
        # Intentar construir nombre de archivo desde raw_data
        raw_data = doc.raw_data or {}
        supplier_nit = doc.supplier_nit or ''
        customer_nit = doc.customer_nit or ''
        
        # Determinar NIT emisor según tipo de sesión
        nit_emisor = supplier_nit if session.tipo == 'Received' else customer_nit
        
        prefix = raw_data.get('prefix', '') or ''
        number = raw_data.get('number', '') or doc.document_number or ''
        
        # Normalizar valores (eliminar espacios, convertir a mayúsculas)
        prefix_clean = prefix.replace(' ', '_').replace('-', '_').upper().strip() if prefix else ''
        number_clean = number.replace(' ', '').replace('-', '').strip() if number else ''
        nit_clean = nit_emisor.replace(' ', '').replace('-', '').strip() if nit_emisor else ''
        
        # Construir múltiples variantes del nombre esperado
        posibles_nombres = []
        
        # Si hay prefix, generar variantes con prefix
        if prefix_clean:
            # Variante 1: {nit}_{prefix}_{number}.pdf
            if nit_clean and number_clean:
                posibles_nombres.append(f"{nit_clean}_{prefix_clean}_{number_clean}.pdf")
                posibles_nombres.append(f"{nit_clean}_{prefix_clean}_{number_clean}.PDF")
            
            # Variante 2: {nit}_{prefix}{number}.pdf (sin guión bajo entre prefix y number)
            if nit_clean and number_clean:
                posibles_nombres.append(f"{nit_clean}_{prefix_clean}{number_clean}.pdf")
                posibles_nombres.append(f"{nit_clean}_{prefix_clean}{number_clean}.PDF")
            
            # Variante 3: {nit}__{prefix}{number}.pdf (doble guión bajo)
            if nit_clean and number_clean:
                posibles_nombres.append(f"{nit_clean}__{prefix_clean}{number_clean}.pdf")
                posibles_nombres.append(f"{nit_clean}__{prefix_clean}{number_clean}.PDF")
        else:
            # Si NO hay prefix, generar variantes sin prefix
            # Variante 1: {nit}_{number}.pdf
            if nit_clean and number_clean:
                posibles_nombres.append(f"{nit_clean}_{number_clean}.pdf")
                posibles_nombres.append(f"{nit_clean}_{number_clean}.PDF")
            
            # Variante 2: {nit}__{number}.pdf (doble guión bajo)
            if nit_clean and number_clean:
                posibles_nombres.append(f"{nit_clean}__{number_clean}.pdf")
                posibles_nombres.append(f"{nit_clean}__{number_clean}.PDF")
            
            # Variante 3: {nit}{number}.pdf (sin guión bajo)
            if nit_clean and number_clean:
                posibles_nombres.append(f"{nit_clean}{number_clean}.pdf")
                posibles_nombres.append(f"{nit_clean}{number_clean}.PDF")
        
        # Buscar PDF con las variantes
        pdf_path = None
        for nombre in posibles_nombres:
            ruta_tentativa = facturas_dir / nombre
            if ruta_tentativa.exists():
                pdf_path = ruta_tentativa
                logger.info(f"✅ [DESCARGAR_PDF] PDF encontrado con variante: {nombre}")
                break
        
        # Si no se encuentra con las variantes, buscar por número de documento
        if not pdf_path or not pdf_path.exists():
            logger.info(f"🔍 [DESCARGAR_PDF] Buscando PDF por número de documento: {number_clean} o {doc.document_number}")
            for pdf_file in facturas_dir.glob("*.pdf"):
                nombre_archivo = pdf_file.name.upper()
                # Buscar por número de documento (sin espacios ni guiones)
                numero_limpio_archivo = nombre_archivo.replace(' ', '').replace('-', '').replace('_', '')
                if number_clean and number_clean.replace('_', '').replace('-', '') in numero_limpio_archivo:
                    pdf_path = pdf_file
                    logger.info(f"✅ [DESCARGAR_PDF] PDF encontrado por número: {pdf_file.name}")
                    break
                # También buscar por document_number original
                if doc.document_number and doc.document_number.replace(' ', '').replace('-', '').replace('_', '') in numero_limpio_archivo:
                    pdf_path = pdf_file
                    logger.info(f"✅ [DESCARGAR_PDF] PDF encontrado por document_number: {pdf_file.name}")
                    break
        
        # Si aún no se encuentra, buscar por CUFE
        if (not pdf_path or not pdf_path.exists()) and doc.cufe:
            logger.info(f"🔍 [DESCARGAR_PDF] Buscando PDF por CUFE: {doc.cufe[:20]}")
            for pdf_file in facturas_dir.glob("*.pdf"):
                if doc.cufe[:20] in pdf_file.name:  # Primeros 20 caracteres del CUFE
                    pdf_path = pdf_file
                    logger.info(f"✅ [DESCARGAR_PDF] PDF encontrado por CUFE: {pdf_file.name}")
                    break
        
        # Verificar si se encontró el PDF
        if not pdf_path or not pdf_path.exists():
            logger.error(f"❌ [DESCARGAR_PDF] PDF no encontrado en: {pdf_path}")
            logger.error(f"❌ [DESCARGAR_PDF] Directorio buscado: {facturas_dir}")
            logger.error(f"❌ [DESCARGAR_PDF] Nombres intentados: {posibles_nombres}")
            logger.error(f"❌ [DESCARGAR_PDF] NIT emisor: {nit_emisor}, Prefix: {prefix}, Number: {number}")
            logger.error(f"❌ [DESCARGAR_PDF] Document number: {doc.document_number}, CUFE: {doc.cufe}")
            archivos_en_dir = list(facturas_dir.glob('*.pdf')) if facturas_dir.exists() else []
            logger.error(f"❌ [DESCARGAR_PDF] Archivos en directorio ({len(archivos_en_dir)} encontrados): {[f.name for f in archivos_en_dir[:10]]}")
            return Response(
                {'error': f'No se encontró el PDF para el documento {doc.document_number}. Se intentaron {len(posibles_nombres)} variantes de nombre.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        logger.info(f"✅ [DESCARGAR_PDF] PDF encontrado: {pdf_path}")
        logger.info(f"✅ [DESCARGAR_PDF] Tamaño: {pdf_path.stat().st_size} bytes")
        
        # Devolver PDF
        try:
            file_handle = open(pdf_path, 'rb')
            response = FileResponse(
                file_handle,
                content_type='application/pdf',
                as_attachment=True,
                filename=pdf_path.name
            )
            logger.info(f"✅ [DESCARGAR_PDF] PDF enviado exitosamente")
            return response
        except Exception as e:
            logger.error(f"❌ [DESCARGAR_PDF] Error leyendo PDF {pdf_path}: {e}", exc_info=True)
            return Response(
                {'error': f'Error al leer el PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def descargar_zip_por_token(request, token):
    """
    Endpoint público para descargar un ZIP de scraping DIAN usando un token seguro.
    No requiere autenticación, solo el token válido.
    
    GET /dian/api/download/{token}/
    """
    from django.utils import timezone
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔍 [DOWNLOAD] Solicitud de descarga con token: {token[:16]}...")
    logger.info(f"🔍 [DOWNLOAD] URL completa: {request.build_absolute_uri()}")
    
    try:
        descarga = DescargaTemporalDianZip.objects.get(token=token)
        logger.info(f"✅ [DOWNLOAD] Descarga encontrada: ID={descarga.id}, Session={descarga.session.id}, Estado={descarga.estado}")
        
        # Verificar que no esté expirado
        if descarga.esta_expirado():
            descarga.estado = 'expirado'
            descarga.save()
            return Response(
                {'error': 'El link de descarga ha expirado. Solicita uno nuevo.'},
                status=status.HTTP_410_GONE
            )
        
        # Verificar que esté listo
        if descarga.estado != 'listo':
            return Response(
                {'error': f'El archivo aún no está listo. Estado: {descarga.estado}'},
                status=status.HTTP_202_ACCEPTED
            )
        
        # Verificar que el archivo existe
        if not descarga.ruta_zip_temporal:
            logger.error(f"❌ [DOWNLOAD] No hay ruta_zip_temporal en el registro")
            return Response(
                {'error': 'El archivo no está disponible. Contacta al administrador.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not os.path.exists(descarga.ruta_zip_temporal):
            logger.error(f"❌ [DOWNLOAD] Archivo no existe: {descarga.ruta_zip_temporal}")
            logger.error(f"❌ [DOWNLOAD] Directorio actual: {os.getcwd()}")
            logger.error(f"❌ [DOWNLOAD] MEDIA_ROOT: {settings.MEDIA_ROOT}")
            return Response(
                {'error': f'El archivo no existe en: {descarga.ruta_zip_temporal}. Contacta al administrador.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        logger.info(f"✅ [DOWNLOAD] Archivo encontrado: {descarga.ruta_zip_temporal}")
        
        # Obtener nombre del archivo original
        nombre_archivo = f'dian_export_session_{descarga.session.id}.zip'
        
        # Actualizar estadísticas
        descarga.intentos_descarga += 1
        if descarga.intentos_descarga == 1:
            descarga.fecha_descarga = timezone.now()
        descarga.save()
        
        # Devolver archivo
        try:
            file_handle = open(descarga.ruta_zip_temporal, 'rb')
            response = FileResponse(
                file_handle,
                content_type='application/zip',
                as_attachment=True,
                filename=nombre_archivo
            )
            response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
            
            logger.info(f"✅ Descarga exitosa de ZIP DIAN con token {token[:16]}...")
            logger.info(f"📁 Archivo: {descarga.ruta_zip_temporal}")
            logger.info(f"📦 Tamaño: {os.path.getsize(descarga.ruta_zip_temporal)} bytes")
            
            return response
        except Exception as file_error:
            logger.error(f"❌ Error abriendo archivo: {file_error}")
            return Response(
                {'error': f'Error al leer el archivo: {str(file_error)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except DescargaTemporalDianZip.DoesNotExist:
        return Response(
            {'error': 'Token inválido o no encontrado.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error descargando ZIP DIAN con token {token[:16]}...: {e}", exc_info=True)
        return Response(
            {'error': f'Error al descargar archivo: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
