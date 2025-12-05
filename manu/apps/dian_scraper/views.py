import asyncio
import re
from pathlib import Path
from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from django.conf import settings
from django.db import models
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from apps.sistema_analitico.models import APIKeyCliente
from .models import ScrapingSession, DocumentProcessed
from .serializers import ScrapingSessionSerializer, DocumentProcessedSerializer
from .tasks import run_dian_scraping_task
from .services.dian_scraper import DianScraperService


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
    def send_by_email(self, request, pk=None):
        """
        Envía por email un ZIP con JSON, Excel y carpeta de facturas (XMLs y PDFs)
        
        Body:
            email: Email del destinatario
        """
        print("=" * 80)
        print("📧 [SEND_EMAIL] Iniciando envío por email")
        print(f"📧 [SEND_EMAIL] Session ID: {pk}")
        print(f"📧 [SEND_EMAIL] Request data: {request.data}")
        
        from django.core.mail import EmailMessage
        from django.conf import settings
        import zipfile
        import io
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
            # Crear ZIP en memoria
            print("📦 [SEND_EMAIL] Creando ZIP en memoria...")
            zip_buffer = io.BytesIO()
            
            archivos_agregados = []
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
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
                    # Agregar todos los XMLs (ya tienen nombres descriptivos o originales)
                    xml_files = list(facturas_dir.glob('*.xml'))
                    print(f"📄 [SEND_EMAIL] Encontrados {len(xml_files)} archivos XML")
                    for xml_file in xml_files:
                        zip_file.write(xml_file, f'facturas/{xml_file.name}')
                        archivos_agregados.append(f'facturas/{xml_file.name}')
                        print(f"  ✅ Agregado: {xml_file.name} ({xml_file.stat().st_size} bytes)")
                    
                    # Agregar todos los PDFs (ya tienen nombres descriptivos o originales)
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
            
            zip_size = zip_buffer.tell()
            zip_buffer.seek(0)
            print(f"📦 [SEND_EMAIL] ZIP creado: {zip_size} bytes, {len(archivos_agregados)} archivos")
            print(f"📦 [SEND_EMAIL] Archivos en ZIP: {archivos_agregados}")
            
            # Preparar email
            print("📧 [SEND_EMAIL] Preparando email...")
            
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
            
            subject = f'Exportación DIAN - Sesión #{session.id}'
            message = f'''Hola,

Se adjunta el archivo comprimido con los resultados del scraping de DIAN.

Detalles de la sesión:
- ID: {session.id}
- Tipo: {session.tipo}
- Fecha desde: {session.fecha_desde}
- Fecha hasta: {session.fecha_hasta}
- Archivos ZIP descargados: {session.documents_downloaded}
- Documentos XML procesados: {documentos_procesados}{mensaje_diferencia}

El archivo ZIP contiene:
- resultado.json: Datos estructurados en JSON ({documentos_procesados} documentos)
- resultado.xlsx: Datos en formato Excel (2 hojas, {documentos_procesados} documentos)
- facturas/: Carpeta con los archivos XML y PDF de las facturas procesadas
- ziporiginales/: Carpeta con los archivos ZIP originales descargados de la DIAN ({session.documents_downloaded} archivos)

Saludos,
Sistema de Scraping DIAN'''
            
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eddeso.com')
            print(f"📧 [SEND_EMAIL] From: {from_email}")
            print(f"📧 [SEND_EMAIL] To: {email}")
            print(f"📧 [SEND_EMAIL] Subject: {subject}")
            
            # Verificar configuración de email
            print(f"📧 [SEND_EMAIL] EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'NO CONFIGURADO')}")
            print(f"📧 [SEND_EMAIL] EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'NO CONFIGURADO')}")
            print(f"📧 [SEND_EMAIL] EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'NO CONFIGURADO')}")
            print(f"📧 [SEND_EMAIL] EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'NO CONFIGURADO')}")
            
            # Crear mensaje de email con adjunto
            email_msg = EmailMessage(
                subject=subject,
                body=message,
                from_email=from_email,
                to=[email],
            )
            
            # Adjuntar ZIP
            zip_filename = f'dian_export_session_{session.id}.zip'
            zip_content = zip_buffer.read()
            print(f"📎 [SEND_EMAIL] Adjuntando ZIP: {zip_filename} ({len(zip_content)} bytes)")
            
            email_msg.attach(
                zip_filename,
                zip_content,
                'application/zip'
            )
            
            print(f"📧 [SEND_EMAIL] Enviando email...")
            # Enviar email
            resultado = email_msg.send(fail_silently=False)
            print(f"✅ [SEND_EMAIL] Email enviado. Resultado: {resultado}")
            print(f"✅ [SEND_EMAIL] Si resultado=1, el email se envió correctamente")
            
            return Response({
                'message': f'Email enviado exitosamente a {email}',
                'email': email,
                'filename': zip_filename,
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
            return Response(
                {'error': f'Error al enviar email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], authentication_classes=[], permission_classes=[AllowAny])
    def test_connection(self, request):
        """Prueba la conexion a DIAN (acceso sin autenticacion)"""
        _attach_api_key(request)
        url = request.data.get('url')

        if not url:
            return Response({'error': 'URL requerida'}, status=400)

        scraper = DianScraperService(0)  # Session ID temporal
        result = asyncio.run(scraper.test_dian_connection(url))

        return Response({
            'connected': result,
            'message': 'Conexion exitosa' if result else 'Error de autenticacion'
        })

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
    
