import re
from rest_framework import serializers
from apps.sistema_analitico.models import EmpresaServidor, UsuarioEmpresa, APIKeyCliente
from .models import FudoScrapingSession, FudoDocumentProcessed


class FudoScrapingSessionSerializer(serializers.ModelSerializer):
    nit = serializers.CharField(required=True)
    empresa_servidor_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = FudoScrapingSession
        fields = '__all__'
        read_only_fields = (
            'status',
            'facturas_procesadas',
            'facturas_exitosas',
            'facturas_fallidas',
            'total_facturas',
            'error_message',
            'created_at',
            'completed_at',
            'started_at',
        )

    def _normalize_nit(self, value: str) -> str:
        """Normaliza NIT eliminando caracteres no numéricos"""
        if not value:
            return ''
        return re.sub(r'\D', '', value)

    def _clean_nit(self, value: str) -> str:
        """Limpia NIT eliminando dígito de verificación y separadores"""
        if not value:
            return ""
        nit_str = str(value).replace('.', '').replace(' ', '')
        base = nit_str.split('-')[0]
        return re.sub(r"\D", "", base)

    def _buscar_empresa_por_nit(self, nit_normalizado: str, request):
        """Busca la empresa más reciente (año más actual) por NIT"""
        # Buscar todas las empresas con ese NIT (sin dígito de verificación)
        empresas = EmpresaServidor.objects.filter(nit=nit_normalizado).order_by('-anio_fiscal')
        
        # Si no encuentra, buscar sin dígito de verificación
        if not empresas.exists():
            nit_clean = self._clean_nit(nit_normalizado)
            empresas = EmpresaServidor.objects.filter(
                nit__startswith=nit_clean
            ).order_by('-anio_fiscal')

        # Filtrar por permisos
        if hasattr(request, 'cliente_api') and request.cliente_api:
            # Validar permisos de API Key
            empresas_autorizadas = getattr(request, 'empresas_autorizadas', None)
            if empresas_autorizadas is not None:
                try:
                    empresas = empresas.filter(id__in=[e.id for e in empresas_autorizadas])
                except AttributeError:
                    empresas = empresas.filter(id__in=[e.id for e in empresas_autorizadas])
        elif hasattr(request, 'user') and request.user and not request.user.is_anonymous:
            user = request.user
            if not user.is_superuser:
                # Filtrar por empresas permitidas al usuario
                empresas = empresas.filter(
                    usuarios_permitidos__usuario=user,
                    usuarios_permitidos__puede_ver=True
                ).distinct()

        # Retornar la más reciente (primer resultado después de ordenar por año fiscal descendente)
        empresa = empresas.first()
        if not empresa:
            raise serializers.ValidationError(
                f'No se encontró empresa con NIT {nit_normalizado} o no tienes permisos para acceder a ella.'
            )
        
        return empresa

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('Request context is required.')

        fecha_desde = attrs.get('fecha_desde')
        fecha_hasta = attrs.get('fecha_hasta')
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            raise serializers.ValidationError('fecha_desde debe ser menor o igual a fecha_hasta')

        # Normalizar NIT
        nit = attrs.get('nit')
        if not nit:
            raise serializers.ValidationError({'nit': 'Este campo es obligatorio.'})
        
        nit_normalizado = self._normalize_nit(nit)
        attrs['nit'] = nit_normalizado

        # Validar permisos
        self._validate_permissions(request, nit_normalizado)

        # Buscar empresa
        empresa_servidor_id = attrs.get('empresa_servidor_id')
        if empresa_servidor_id:
            try:
                empresa = EmpresaServidor.objects.get(id=empresa_servidor_id)
                # Validar que el NIT coincida
                if self._normalize_nit(empresa.nit) != nit_normalizado:
                    raise serializers.ValidationError(
                        'El NIT proporcionado no coincide con la empresa seleccionada.'
                    )
            except EmpresaServidor.DoesNotExist:
                raise serializers.ValidationError('Empresa no encontrada.')
        else:
            # Buscar automáticamente la empresa más reciente
            empresa = self._buscar_empresa_por_nit(nit_normalizado, request)
            attrs['empresa_servidor'] = empresa

        return attrs

    def _validate_permissions(self, request, nit: str):
        """Valida permisos según API Key o usuario"""
        if hasattr(request, 'cliente_api') and request.cliente_api:
            # Validación para API Key
            api_key_obj = request.cliente_api
            
            # Si el usuario del API Key es superuser, permitir todas las empresas
            if api_key_obj.usuario_creador.is_superuser:
                return
            
            normalized = self._normalize_nit(nit)
            empresas = getattr(request, 'empresas_autorizadas', None)
            
            if empresas is not None:
                try:
                    # Verificar si alguna empresa autorizada tiene este NIT
                    allowed = empresas.filter(nit=normalized).exists()
                except AttributeError:
                    allowed = any(self._normalize_nit(getattr(emp, 'nit', '')) == normalized for emp in empresas)
                
                if not allowed:
                    # Verificar si el NIT del API Key coincide
                    api_nit = self._normalize_nit(api_key_obj.nit)
                    if api_nit != normalized:
                        raise serializers.ValidationError(
                            'La API Key no tiene acceso al NIT solicitado.'
                        )
            else:
                # Si no hay empresas autorizadas, verificar NIT del API Key
                api_nit = self._normalize_nit(api_key_obj.nit)
                if api_nit != normalized:
                    raise serializers.ValidationError(
                        'La API Key no tiene acceso al NIT solicitado.'
                    )
            return

        # Validación para usuario autenticado
        user = getattr(request, 'user', None)
        if not user or user.is_anonymous:
            raise serializers.ValidationError('Autenticación requerida para ejecutar el scraping.')
        
        # Si es superuser, permitir todas las empresas
        if user.is_superuser:
            return

        # Verificar permisos del usuario
        has_permission = UsuarioEmpresa.objects.filter(
            usuario=user,
            empresa_servidor__nit=nit,
        ).exists()
        
        if not has_permission:
            raise serializers.ValidationError('No tienes permisos para este NIT.')

    def create(self, validated_data):
        # Asegurar que empresa_servidor esté en validated_data
        if 'empresa_servidor' not in validated_data:
            nit = validated_data['nit']
            request = self.context.get('request')
            empresa = self._buscar_empresa_por_nit(nit, request)
            validated_data['empresa_servidor'] = empresa
        
        return super().create(validated_data)


class FudoDocumentProcessedSerializer(serializers.ModelSerializer):
    class Meta:
        model = FudoDocumentProcessed
        fields = '__all__'

