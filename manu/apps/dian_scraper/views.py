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
    if not api_key:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Api-Key '):
            api_key = auth_header.replace('Api-Key ', '')
    if not api_key:
        return False
    try:
        api_key_obj = APIKeyCliente.objects.get(api_key__iexact=api_key.strip(), activa=True)
        if api_key_obj.esta_expirada():
            return False
        empresas = api_key_obj.empresas_asociadas.all()
        if not empresas.exists():
            api_key_obj.actualizar_empresas_asociadas()
            empresas = api_key_obj.empresas_asociadas.all()
        api_key_obj.incrementar_contador()
        request.cliente_api = api_key_obj
        request.empresas_autorizadas = empresas
        return True
    except APIKeyCliente.DoesNotExist:
        return False
    except Exception:
        return False


class AllowAuthenticatedOrAPIKey(BasePermission):
    def has_permission(self, request, view):
        if _attach_api_key(request):
            return True
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)

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
        _attach_api_key(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = serializer.save()
        run_dian_scraping_task.delay(session.id)

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
    
