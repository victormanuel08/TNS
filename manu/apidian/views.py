"""
Views para APIDIAN
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
import logging

from .serializers import (
    SendEventSerializer,
    SendEventFromFileSerializer,
    SendEventFromDocumentIdSerializer
)
from .services.apidian_client import ApidianAPIClient
from .services.data_queries import ApidianDataQueries
from .services.db_connection import ApidianDBConnection

logger = logging.getLogger(__name__)


class ApidianViewSet(viewsets.ViewSet):
    """ViewSet para interactuar con APIDIAN"""
    permission_classes = [IsAuthenticated]  # Cambiar según necesidades
    
    @action(detail=False, methods=['post'], url_path='send-event')
    def send_event(self, request):
        """
        Envía un evento a APIDIAN usando el endpoint /api/ubl2.1/send-event
        
        Body:
        {
            "event_id": 1,
            "allow_cash_documents": false,
            "sendmail": false,
            "base64_attacheddocument_name": "ad09001495660102400018741.xml",
            "base64_attacheddocument": "PD94bWw....",
            "type_rejection_id": null,
            "resend_consecutive": false
        }
        """
        serializer = SendEventSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        client = ApidianAPIClient()
        
        try:
            result = client.send_event(
                event_id=data['event_id'],
                attached_document_name=data['base64_attacheddocument_name'],
                attached_document_base64=data['base64_attacheddocument'],
                allow_cash_documents=data.get('allow_cash_documents', False),
                sendmail=data.get('sendmail', False),
                type_rejection_id=data.get('type_rejection_id'),
                resend_consecutive=data.get('resend_consecutive', False)
            )
            
            return Response({
                'success': True,
                'message': 'Evento enviado exitosamente',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error enviando evento: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='send-event-from-file')
    def send_event_from_file(self, request):
        """
        Envía un evento desde un archivo XML local
        
        Body:
        {
            "event_id": 1,
            "xml_file_path": "/ruta/al/archivo.xml",
            "allow_cash_documents": false,
            "sendmail": false,
            "type_rejection_id": null,
            "resend_consecutive": false
        }
        """
        serializer = SendEventFromFileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        client = ApidianAPIClient()
        
        try:
            result = client.send_event_from_file(
                event_id=data['event_id'],
                xml_file_path=data['xml_file_path'],
                allow_cash_documents=data.get('allow_cash_documents', False),
                sendmail=data.get('sendmail', False),
                type_rejection_id=data.get('type_rejection_id'),
                resend_consecutive=data.get('resend_consecutive', False)
            )
            
            return Response({
                'success': True,
                'message': 'Evento enviado exitosamente desde archivo',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except FileNotFoundError as e:
            return Response({
                'success': False,
                'error': f'Archivo no encontrado: {str(e)}'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error enviando evento desde archivo: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='send-event-from-document')
    def send_event_from_document(self, request):
        """
        Envía un evento desde un documento existente en la BD de APIDIAN
        
        Body:
        {
            "event_id": 1,
            "document_id": 123,
            "allow_cash_documents": false,
            "sendmail": false,
            "type_rejection_id": null,
            "resend_consecutive": false
        }
        """
        serializer = SendEventFromDocumentIdSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        queries = ApidianDataQueries()
        client = ApidianAPIClient()
        
        try:
            # Obtener XML del documento
            document_xml = queries.get_document_xml(data['document_id'])
            if not document_xml:
                return Response({
                    'success': False,
                    'error': f'Documento {data["document_id"]} no encontrado en BD APIDIAN'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Enviar evento
            result = client.send_event(
                event_id=data['event_id'],
                attached_document_name=document_xml['filename'],
                attached_document_base64=document_xml['content'],
                allow_cash_documents=data.get('allow_cash_documents', False),
                sendmail=data.get('sendmail', False),
                type_rejection_id=data.get('type_rejection_id'),
                resend_consecutive=data.get('resend_consecutive', False)
            )
            
            return Response({
                'success': True,
                'message': 'Evento enviado exitosamente desde documento',
                'data': result
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error enviando evento desde documento: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='events')
    def list_events(self, request):
        """Lista los eventos disponibles en APIDIAN"""
        queries = ApidianDataQueries()
        try:
            events = queries.get_events()
            return Response({
                'success': True,
                'data': events
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error obteniendo eventos: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='type-rejections')
    def list_type_rejections(self, request):
        """Lista los tipos de rechazo disponibles"""
        queries = ApidianDataQueries()
        try:
            rejections = queries.get_type_rejections()
            return Response({
                'success': True,
                'data': rejections
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error obteniendo tipos de rechazo: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='documents')
    def list_documents(self, request):
        """Lista documentos de APIDIAN con filtros opcionales"""
        queries = ApidianDataQueries()
        
        filters = {}
        if 'nit' in request.query_params:
            filters['nit'] = request.query_params['nit']
        if 'fecha_desde' in request.query_params:
            filters['fecha_desde'] = request.query_params['fecha_desde']
        if 'fecha_hasta' in request.query_params:
            filters['fecha_hasta'] = request.query_params['fecha_hasta']
        
        try:
            documents = queries.search_documents(filters)
            return Response({
                'success': True,
                'data': documents,
                'count': len(documents)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error obteniendo documentos: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='documents/(?P<document_id>[0-9]+)')
    def get_document(self, request, document_id=None):
        """Obtiene un documento específico por ID"""
        queries = ApidianDataQueries()
        try:
            document = queries.get_document_by_id(int(document_id))
            if not document:
                return Response({
                    'success': False,
                    'error': f'Documento {document_id} no encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'success': True,
                'data': document
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error obteniendo documento: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
