import re
from datetime import timedelta

from rest_framework import serializers

from apps.sistema_analitico.models import UsuarioEmpresa
from .models import (
    ScrapingSession,
    DocumentProcessed,
    ScrapingRange,
)


class ScrapingSessionSerializer(serializers.ModelSerializer):
    nit = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ScrapingSession
        fields = '__all__'
        read_only_fields = (
            'status',
            'documents_downloaded',
            'excel_file',
            'json_file',
            'created_at',
            'completed_at',
            'error_message',
            'ejecutado_desde',
            'ejecutado_hasta',
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('Request context is required.')

        fecha_desde = attrs.get('fecha_desde')
        fecha_hasta = attrs.get('fecha_hasta')
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            raise serializers.ValidationError('fecha_desde debe ser menor o igual a fecha_hasta')

        nit = self._resolve_nit(request, attrs)
        attrs['nit'] = nit
        self._validate_permissions(request, nit)

        gap = self._find_next_gap(nit, attrs.get('tipo', 'Sent'), fecha_desde, fecha_hasta)
        if not gap:
            raise serializers.ValidationError('El rango solicitado ya fue procesado previamente.')

        attrs['ejecutado_desde'], attrs['ejecutado_hasta'] = gap
        return attrs

    def _normalize_nit(self, value: str) -> str:
        if not value:
            return ''
        return re.sub(r'\D', '', value)

    def _resolve_nit(self, request, attrs) -> str:
        if hasattr(request, 'cliente_api') and request.cliente_api:
            return self._normalize_nit(request.cliente_api.nit)

        nit = attrs.get('nit') or request.data.get('nit')
        if not nit:
            raise serializers.ValidationError({'nit': 'Este campo es obligatorio.'})
        return self._normalize_nit(nit)

    def _validate_permissions(self, request, nit: str):
        if hasattr(request, 'cliente_api') and request.cliente_api:
            api_nit = self._normalize_nit(request.cliente_api.nit)
            if api_nit != nit:
                raise serializers.ValidationError('La API Key no tiene acceso al NIT solicitado.')
            return

        user = getattr(request, 'user', None)
        if not user or user.is_anonymous:
            raise serializers.ValidationError('Autenticación requerida para ejecutar el scraping.')
        if user.is_superuser:
            return

        has_permission = UsuarioEmpresa.objects.filter(
            usuario=user,
            empresa_servidor__nit=nit,
        ).exists()
        if not has_permission:
            raise serializers.ValidationError('No tienes permisos para este NIT.')

    def _find_next_gap(self, nit: str, tipo: str, fecha_desde, fecha_hasta):
        coverages = ScrapingRange.objects.filter(nit=nit, tipo=tipo).order_by('start_date')
        current = fecha_desde
        for coverage in coverages:
            if coverage.end_date < current:
                continue
            if coverage.start_date > fecha_hasta:
                break
            if coverage.start_date > current:
                gap_end = min(fecha_hasta, coverage.start_date - timedelta(days=1))
                return current, gap_end
            if coverage.start_date <= current <= coverage.end_date:
                current = coverage.end_date + timedelta(days=1)
                if current > fecha_hasta:
                    return None
        if current <= fecha_hasta:
            return current, fecha_hasta
        return None


class DocumentProcessedSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentProcessed
        fields = '__all__'
