import asyncio
from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from .models import ScrapingSession, DocumentProcessed
from .serializers import ScrapingSessionSerializer, DocumentProcessedSerializer
from .tasks import run_dian_scraping_task
from .services.dian_scraper import DianScraperService

class ScrapingSessionViewSet(viewsets.ModelViewSet):
    queryset = ScrapingSession.objects.all()
    serializer_class = ScrapingSessionSerializer
    
    @action(detail=True, methods=['post'])
    def start_scraping(self, request, pk=None):
        """Inicia el proceso de scraping para una sesión"""
        session = self.get_object()
        
        if session.status == 'running':
            return Response(
                {'error': 'El scraping ya está en ejecución'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Iniciar tarea asíncrona
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
    
    @action(detail=False, methods=['post'])
    @authentication_classes([])
    @permission_classes([AllowAny])  # 🔓 Este endpoint es público
    def test_connection(self, request):
        """Prueba la conexión a DIAN (acceso sin autenticación)"""
        url = request.data.get('url')
        
        if not url:
            return Response({'error': 'URL requerida'}, status=400)
        
        scraper = DianScraperService(0)  # Session ID temporal
        result = asyncio.run(scraper.test_dian_connection(url))
        
        return Response({
            'connected': result,
            'message': 'Conexión exitosa' if result else 'Error de autenticación'
        })
    
    @action(detail=False, methods=['post'])
    @authentication_classes([])
    @permission_classes([AllowAny])  # 🔓 Este también si quieres
    def quick_scrape(self, request):
        """Endpoint rápido para iniciar scraping (acceso sin autenticación)"""
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
    
    def get_queryset(self):
        queryset = DocumentProcessed.objects.all()
        session_id = self.request.query_params.get('session_id')
        
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
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
    
