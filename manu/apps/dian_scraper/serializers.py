import re
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta

from rest_framework import serializers

from apps.sistema_analitico.models import UsuarioEmpresa
from .models import (
    ScrapingSession,
    DocumentProcessed,
    ScrapingRange,
    EventoApidianEnviado,
)


class ScrapingSessionSerializer(serializers.ModelSerializer):
    nit = serializers.CharField(required=False, allow_blank=True)
    eventos_fallidos_count = serializers.SerializerMethodField()

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
    
    def get_eventos_fallidos_count(self, obj):
        """Retorna el número de eventos fallidos para esta sesión"""
        return EventoApidianEnviado.objects.filter(
            session=obj,
            estado='fallido'
        ).count()

    def validate(self, attrs):
        print("=" * 80)
        print("🔍 [SERIALIZER] Iniciando validación")
        print(f"🔍 [SERIALIZER] attrs recibidos: {attrs}")
        
        attrs = super().validate(attrs)
        request = self.context.get('request')
        if not request:
            print("❌ [SERIALIZER] No hay request context")
            raise serializers.ValidationError('Request context is required.')

        fecha_desde = attrs.get('fecha_desde')
        fecha_hasta = attrs.get('fecha_hasta')
        print(f"🔍 [SERIALIZER] Fechas: desde={fecha_desde}, hasta={fecha_hasta}")
        
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            print("❌ [SERIALIZER] fecha_desde > fecha_hasta")
            raise serializers.ValidationError('fecha_desde debe ser menor o igual a fecha_hasta')
        
        # Validar que el rango no exceda 1 mes
        if fecha_desde and fecha_hasta:
            # Calcular el último día del mes de fecha_desde
            ultimo_dia_mes_desde = (fecha_desde.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            
            # Si es el mes actual, el máximo es el día anterior
            hoy = date.today()
            if fecha_desde.year == hoy.year and fecha_desde.month == hoy.month:
                fecha_maxima = hoy - timedelta(days=1)
            else:
                fecha_maxima = ultimo_dia_mes_desde
            
            if fecha_hasta > fecha_maxima:
                raise serializers.ValidationError(
                    f'El rango de fechas no puede exceder 1 mes. '
                    f'Fecha máxima permitida: {fecha_maxima.strftime("%Y-%m-%d")}'
                )

        try:
            nit = self._resolve_nit(request, attrs)
            print(f"🔍 [SERIALIZER] NIT resuelto: {nit}")
            attrs['nit'] = nit
            self._validate_permissions(request, nit)
            print("✅ [SERIALIZER] Permisos validados")
        except Exception as e:
            print(f"❌ [SERIALIZER] Error en validación de permisos: {e}")
            raise

        tipo = attrs.get('tipo', 'Sent')
        print(f"🔍 [SERIALIZER] Tipo: {tipo}")
        
        # Si permite_scraping_total está activo, usar el rango completo sin validar gaps
        permite_scraping_total = False
        if hasattr(request, 'cliente_api') and request.cliente_api:
            permite_scraping_total = getattr(request.cliente_api, 'permite_scraping_total', False)
            print(f"🔍 [SERIALIZER] permite_scraping_total: {permite_scraping_total}")
        
        if permite_scraping_total:
            # Con scraping total, usar el rango completo solicitado sin validar gaps
            print("✅ [SERIALIZER] Scraping total activo, usando rango completo sin validar gaps")
            attrs['ejecutado_desde'] = fecha_desde
            attrs['ejecutado_hasta'] = fecha_hasta
        else:
            # Validar gaps normalmente
            try:
                gap = self._find_next_gap(nit, tipo, fecha_desde, fecha_hasta)
                print(f"🔍 [SERIALIZER] Gap encontrado: {gap}")
                if not gap:
                    print("❌ [SERIALIZER] No se encontró gap (rango ya procesado)")
                    raise serializers.ValidationError('El rango solicitado ya fue procesado previamente.')

                attrs['ejecutado_desde'], attrs['ejecutado_hasta'] = gap
                print(f"✅ [SERIALIZER] Validación exitosa. Ejecutado: {gap[0]} -> {gap[1]}")
            except serializers.ValidationError:
                raise
            except Exception as e:
                print(f"❌ [SERIALIZER] Error en _find_next_gap: {e}")
                import traceback
                traceback.print_exc()
                raise serializers.ValidationError(f'Error al buscar gap: {str(e)}')
        
        print("=" * 80)
        return attrs

    def _normalize_nit(self, value: str) -> str:
        if not value:
            return ''
        return re.sub(r'\D', '', value)

    def _resolve_nit(self, request, attrs) -> str:
        nit = attrs.get('nit') or request.data.get('nit')
        if not nit:
            if hasattr(request, 'cliente_api') and request.cliente_api:
                return self._normalize_nit(request.cliente_api.nit)
            raise serializers.ValidationError({'nit': 'Este campo es obligatorio.'})
        return self._normalize_nit(nit)

    def _validate_permissions(self, request, nit: str):
        print(f"🔍 [SERIALIZER] Validando permisos para NIT: {nit}")
        
        if hasattr(request, 'cliente_api') and request.cliente_api:
            print(f"🔍 [SERIALIZER] API Key encontrada: ID={request.cliente_api.id}, NIT={request.cliente_api.nit}")
            print(f"🔍 [SERIALIZER] permite_scraping_total: {getattr(request.cliente_api, 'permite_scraping_total', False)}")
            
            # Si permite_scraping_total, no validar empresas
            if getattr(request.cliente_api, 'permite_scraping_total', False):
                print("✅ [SERIALIZER] API Key permite scraping total, omitiendo validación de empresas")
                return
            
            normalized = self._normalize_nit(nit)
            empresas = getattr(request, 'empresas_autorizadas', None)
            print(f"🔍 [SERIALIZER] Empresas autorizadas: {empresas}")
            
            if empresas is not None:
                # empresas puede ser QuerySet o lista evaluada
                # Verificar si alguna empresa autorizada tiene este NIT normalizado
                try:
                    allowed = empresas.filter(nit_normalizado=normalized).exists()
                    print(f"🔍 [SERIALIZER] Resultado filter().exists(): {allowed}")
                except AttributeError:
                    # Si es una lista, verificar manualmente
                    allowed = any(getattr(emp, 'nit_normalizado', None) == normalized for emp in empresas)
                    print(f"🔍 [SERIALIZER] Resultado verificación manual: {allowed}")
            else:
                allowed = False
                print("⚠️ [SERIALIZER] No hay empresas autorizadas")
            
            if not empresas or not allowed:
                api_nit = self._normalize_nit(request.cliente_api.nit)
                allowed = api_nit == normalized
                print(f"🔍 [SERIALIZER] Comparando NIT API Key ({api_nit}) con NIT solicitado ({normalized}): {allowed}")
            
            if not allowed:
                print("❌ [SERIALIZER] Acceso denegado")
                raise serializers.ValidationError('La API Key no tiene acceso al NIT solicitado.')
            
            print("✅ [SERIALIZER] Permisos validados correctamente")
            return

        user = getattr(request, 'user', None)
        if not user or user.is_anonymous:
            raise serializers.ValidationError('Autenticación requerida para ejecutar el scraping.')
        if user.is_superuser:
            return

        # Normalizar NIT antes de buscar
        nit_normalizado = self._normalize_nit(nit)
        has_permission = UsuarioEmpresa.objects.filter(
            usuario=user,
            empresa_servidor__nit_normalizado=nit_normalizado,
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
    # Campos calculados para facilitar el frontend
    fecha = serializers.DateField(source='issue_date', read_only=True)
    fecha_emision = serializers.DateField(source='issue_date', read_only=True)
    numero = serializers.CharField(source='document_number', read_only=True)
    numero_factura = serializers.CharField(source='document_number', read_only=True)
    valor_total = serializers.DecimalField(source='total_amount', max_digits=15, decimal_places=2, read_only=True)
    
    # Campos para emisor/receptor según el tipo
    nit_emisor = serializers.CharField(source='supplier_nit', read_only=True)
    razon_social_emisor = serializers.CharField(source='supplier_name', read_only=True)
    nit_receptor = serializers.CharField(source='customer_nit', read_only=True)
    razon_social_receptor = serializers.CharField(source='customer_name', read_only=True)
    
    # Campo tipo desde la sesión
    tipo = serializers.CharField(source='session.tipo', read_only=True)
    
    class Meta:
        model = DocumentProcessed
        fields = '__all__'


class GenerarAcusesSerializer(serializers.Serializer):
    """Serializer para validar datos al generar acuses automáticos.
    Ahora solo requiere eventos, el resto se obtiene automáticamente desde la sesión."""
    eventos = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=7),
        min_length=1,
        help_text='Lista de IDs de eventos a aplicar (1-7)'
    )
    # Campos opcionales para override manual
    cedula = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text='Número de identificación del emisor (opcional, se obtiene del NIT si no se proporciona)'
    )
    primer_nombre = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text='Primer nombre del emisor (opcional, default: "Pasante")'
    )
    segundo_nombre = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text='Segundo nombre del emisor (opcional)'
    )
    departamento = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default='CONTABILIDAD',
        help_text='Departamento del emisor (opcional, default: "CONTABILIDAD")'
    )
    cargo = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default='Aux Contable',
        help_text='Cargo del emisor (opcional, default: "Aux Contable")'
    )
    
    def validate_eventos(self, value):
        """Validar que los eventos sean válidos"""
        eventos_validos = [1, 2, 3, 4, 5, 6, 7]
        eventos_invalidos = [e for e in value if e not in eventos_validos]
        if eventos_invalidos:
            raise serializers.ValidationError(
                f'Eventos inválidos: {eventos_invalidos}. Eventos válidos: {eventos_validos}'
            )
        return value
