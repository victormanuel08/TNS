from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from apps.sistema_analitico.models import APIKeyCliente
from .models import FudoScrapingSession, FudoDocumentProcessed
from .serializers import FudoScrapingSessionSerializer, FudoDocumentProcessedSerializer
from .tasks import run_fudo_scraping_task


def _attach_api_key(request):
    """Adjunta información de API Key al request si existe"""
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
    """Permite acceso con autenticación normal o API Key"""
    def has_permission(self, request, view):
        if _attach_api_key(request):
            return True
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)


class FudoScrapingSessionViewSet(viewsets.ModelViewSet):
    queryset = FudoScrapingSession.objects.all()
    serializer_class = FudoScrapingSessionSerializer
    permission_classes = [AllowAuthenticatedOrAPIKey]

    def get_queryset(self):
        """Filtra queryset según permisos"""
        queryset = super().get_queryset()
        
        # Si hay API Key, filtrar por empresas autorizadas
        if hasattr(self.request, 'cliente_api') and self.request.cliente_api:
            empresas_autorizadas = getattr(self.request, 'empresas_autorizadas', None)
            if empresas_autorizadas is not None:
                try:
                    queryset = queryset.filter(empresa_servidor__in=empresas_autorizadas)
                except AttributeError:
                    empresa_ids = [e.id for e in empresas_autorizadas]
                    queryset = queryset.filter(empresa_servidor_id__in=empresa_ids)
        
        # Si es usuario normal (no superuser), filtrar por permisos
        elif hasattr(self.request, 'user') and self.request.user and not self.request.user.is_anonymous:
            if not self.request.user.is_superuser:
                queryset = queryset.filter(
                    empresa_servidor__usuarios_permitidos__usuario=self.request.user,
                    empresa_servidor__usuarios_permitidos__puede_ver=True
                ).distinct()
        
        return queryset

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
        run_fudo_scraping_task.delay(session.id)

        return Response({
            'message': 'Scraping iniciado',
            'session_id': session.id,
            'status': 'pending'
        })

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Consulta el estado actual del scraping"""
        session = self.get_object()
        
        return Response({
            'session_id': session.id,
            'status': session.status,
            'facturas_procesadas': session.facturas_procesadas,
            'facturas_exitosas': session.facturas_exitosas,
            'facturas_fallidas': session.facturas_fallidas,
            'total_facturas': session.total_facturas,
            'created_at': session.created_at,
            'started_at': session.started_at,
            'completed_at': session.completed_at,
            'error_message': session.error_message if session.error_message else None,
            'progreso_porcentaje': (
                (session.facturas_procesadas / session.total_facturas * 100)
                if session.total_facturas > 0 else 0
            )
        })

    @action(detail=False, methods=['post'])
    def quick_scrape(self, request):
        """Endpoint rápido para iniciar scraping"""
        _attach_api_key(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = serializer.save()
        run_fudo_scraping_task.delay(session.id)

        return Response({
            'message': 'Scraping iniciado',
            'session_id': session.id,
            'status': 'pending'
        }, status=status.HTTP_201_CREATED)


class FudoDocumentProcessedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FudoDocumentProcessedSerializer
    permission_classes = [AllowAuthenticatedOrAPIKey]

    def get_queryset(self):
        queryset = FudoDocumentProcessed.objects.all()
        params = self.request.query_params

        session_id = params.get('session_id')
        if session_id:
            queryset = queryset.filter(session_id=session_id)

        estado = params.get('estado_insercion')
        if estado:
            queryset = queryset.filter(estado_insercion=estado)

        # Filtrar por permisos de sesión
        if hasattr(self.request, 'cliente_api') and self.request.cliente_api:
            empresas_autorizadas = getattr(self.request, 'empresas_autorizadas', None)
            if empresas_autorizadas is not None:
                try:
                    queryset = queryset.filter(
                        session__empresa_servidor__in=empresas_autorizadas
                    )
                except AttributeError:
                    empresa_ids = [e.id for e in empresas_autorizadas]
                    queryset = queryset.filter(
                        session__empresa_servidor_id__in=empresa_ids
                    )
        elif hasattr(self.request, 'user') and self.request.user and not self.request.user.is_anonymous:
            if not self.request.user.is_superuser:
                queryset = queryset.filter(
                    session__empresa_servidor__usuarios_permitidos__usuario=self.request.user,
                    session__empresa_servidor__usuarios_permitidos__puede_ver=True
                ).distinct()

        return queryset

