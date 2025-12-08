from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import (
    PasarelaPago, TransaccionPago,
    Servidor, EmpresaServidor, MovimientoInventario, UsuarioEmpresa,
    EmpresaPersonalizacion, GrupoMaterialImagen, MaterialImagen, CajaAutopago,
    VpnConfig, EmpresaEcommerceConfig, APIKeyCliente, EmpresaDominio, UserTenantProfile,
    RUT, EstablecimientoRUT, ActividadEconomica, ResponsabilidadTributaria,
    TipoTercero, TipoRegimen, Impuesto, VigenciaTributaria,
    Entidad, ContrasenaEntidad, ConfiguracionS3, BackupS3, ClasificacionContable
)


# ==================== Serializers para Comunicación (SMS y Llamadas) ====================

class EnviarSMSSerializer(serializers.Serializer):
    """Serializer para validar datos al enviar SMS"""
    telefono = serializers.CharField(
        max_length=15,
        help_text='Número de teléfono (10 dígitos, sin indicativo)'
    )
    mensaje = serializers.CharField(
        max_length=160,
        help_text='Mensaje a enviar (máximo 160 caracteres)'
    )
    flash = serializers.BooleanField(
        required=False,
        default=False,
        help_text='Si es True, el SMS aparece directamente en pantalla'
    )
    prioridad = serializers.BooleanField(
        required=False,
        default=True,
        help_text='Si es True, envía con prioridad alta'
    )
    
    def validate_telefono(self, value):
        """Validar formato del teléfono"""
        # Limpiar caracteres no numéricos
        telefono_limpio = ''.join(filter(str.isdigit, value))
        
        # Debe tener 10 dígitos o más (con código de país)
        if len(telefono_limpio) < 10:
            raise serializers.ValidationError("El teléfono debe tener al menos 10 dígitos")
        
        return value
    
    def validate_mensaje(self, value):
        """Validar longitud del mensaje"""
        if len(value) > 160:
            raise serializers.ValidationError("El mensaje no puede exceder 160 caracteres")
        if not value.strip():
            raise serializers.ValidationError("El mensaje no puede estar vacío")
        return value


class EnviarLlamadaSerializer(serializers.Serializer):
    """Serializer para validar datos al enviar llamada"""
    telefono = serializers.CharField(
        max_length=15,
        help_text='Número de teléfono (10 dígitos, sin indicativo)'
    )
    mensaje = serializers.CharField(
        max_length=500,
        help_text='Mensaje a convertir a voz (máximo 500 caracteres)'
    )
    duplicar_mensaje = serializers.BooleanField(
        required=False,
        default=True,
        help_text='Si es True, duplica el mensaje para mejor comprensión'
    )
    
    def validate_telefono(self, value):
        """Validar formato del teléfono"""
        telefono_limpio = ''.join(filter(str.isdigit, value))
        if len(telefono_limpio) < 10:
            raise serializers.ValidationError("El teléfono debe tener al menos 10 dígitos")
        return value
    
    def validate_mensaje(self, value):
        """Validar longitud del mensaje"""
        if len(value) > 500:
            raise serializers.ValidationError("El mensaje no puede exceder 500 caracteres")
        if not value.strip():
            raise serializers.ValidationError("El mensaje no puede estar vacío")
        return value


class EnviarMixtoSerializer(serializers.Serializer):
    """Serializer para validar datos al enviar comunicación mixta (llamada + SMS)"""
    telefono = serializers.CharField(
        max_length=15,
        help_text='Número de teléfono (10 dígitos, sin indicativo)'
    )
    mensaje = serializers.CharField(
        max_length=160,
        help_text='Mensaje a enviar (máximo 160 caracteres para SMS)'
    )
    
    def validate_telefono(self, value):
        """Validar formato del teléfono"""
        telefono_limpio = ''.join(filter(str.isdigit, value))
        if len(telefono_limpio) < 10:
            raise serializers.ValidationError("El teléfono debe tener al menos 10 dígitos")
        return value
    
    def validate_mensaje(self, value):
        """Validar longitud del mensaje"""
        if len(value) > 160:
            raise serializers.ValidationError("El mensaje no puede exceder 160 caracteres")
        if not value.strip():
            raise serializers.ValidationError("El mensaje no puede estar vacío")
        return value


class VerificarEstadoSerializer(serializers.Serializer):
    """Serializer para validar ID al verificar estado"""
    id = serializers.CharField(
        max_length=100,
        help_text='ID del SMS o llamada a verificar'
    )


class ServidorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servidor
        fields = '__all__'


class EmpresaServidorSerializer(serializers.ModelSerializer):
    servidor_nombre = serializers.CharField(source='servidor.nombre', read_only=True)
    
    class Meta:
        model = EmpresaServidor
        fields = '__all__'
        # Asegurar que servidor_nombre esté incluido explícitamente
        extra_kwargs = {
            'servidor': {'write_only': False}
        }
    
    def validate(self, attrs):
        """Valida que no exista otra empresa con el mismo NIT y año fiscal en otro servidor"""
        nit = attrs.get('nit')
        anio_fiscal = attrs.get('anio_fiscal')
        
        if nit and anio_fiscal:
            # Normalizar NIT antes de buscar
            from .models import normalize_nit_and_extract_dv
            nit_norm, _, _ = normalize_nit_and_extract_dv(nit)
            
            if nit_norm:
                # Buscar si existe otra empresa con el mismo NIT normalizado y año fiscal
                existing = EmpresaServidor.objects.filter(
                    nit_normalizado=nit_norm,
                    anio_fiscal=anio_fiscal
                )
                
                # Si estamos editando, excluir la instancia actual
                if self.instance:
                    existing = existing.exclude(pk=self.instance.pk)
                
                if existing.exists():
                    raise serializers.ValidationError(
                        f'Ya existe una empresa con NIT {nit} (normalizado: {nit_norm}) y año fiscal {anio_fiscal} en otro servidor.'
                    )
        
        return attrs


class UsuarioEmpresaSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    usuario_email = serializers.CharField(source='usuario.email', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa_servidor.nombre', read_only=True)
    empresa_nit = serializers.CharField(source='empresa_servidor.nit', read_only=True)
    empresa_anio_fiscal = serializers.IntegerField(source='empresa_servidor.anio_fiscal', read_only=True)
    empresa_servidor_nombre = serializers.CharField(source='empresa_servidor.servidor.nombre', read_only=True)
    
    class Meta:
        model = UsuarioEmpresa
        fields = [
            'id', 'usuario', 'usuario_username', 'usuario_email',
            'empresa_servidor', 'empresa_nombre', 'empresa_nit', 
            'empresa_anio_fiscal', 'empresa_servidor_nombre',
            'puede_ver', 'puede_editar', 'preferred_template', 
            'fecha_asignacion'
        ]
        read_only_fields = ['id', 'fecha_asignacion']


class UserTenantProfileSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = UserTenantProfile
        fields = ['id', 'user', 'user_username', 'user_email', 'subdomain', 'preferred_template']
        read_only_fields = ['id']

class MovimientoInventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoInventario
        fields = '__all__'


# ========== TNS Serializers ==========

class TNSBaseSerializer(serializers.Serializer):
    """Base serializer para endpoints TNS"""
    empresa_servidor_id = serializers.IntegerField(required=False)
    nit = serializers.CharField(required=False)
    anio_fiscal = serializers.IntegerField(required=False)
    
    def validate(self, attrs):
        if not attrs.get('empresa_servidor_id') and not (attrs.get('nit') and attrs.get('anio_fiscal')):
            raise serializers.ValidationError(
                'Debe proporcionar empresa_servidor_id o (nit y anio_fiscal)'
            )
        return attrs


class TNSQuerySerializer(TNSBaseSerializer):
    sql = serializers.CharField()
    params = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class TNSProcedureSerializer(TNSBaseSerializer):
    procedure = serializers.CharField()
    params = serializers.DictField(child=serializers.CharField(), required=False, default=dict)


class TNSValidarTerceroSerializer(TNSBaseSerializer):
    """Serializer para validar tercero por documento"""
    document_type = serializers.ChoiceField(
        choices=[('cedula', 'Cédula'), ('nit', 'NIT')],
        help_text='Tipo de documento: cedula (9) o nit (31)'
    )
    document_number = serializers.CharField(
        max_length=20,
        help_text='Número de documento sin puntos ni guiones'
    )
    telefono = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text='Teléfono del tercero (opcional, para actualizar en TNS)'
    )


class TNSCrearTerceroSerializer(TNSBaseSerializer):
    """Serializer para crear tercero en TNS usando TNS_INS_TERCERO"""
    document_type = serializers.ChoiceField(
        choices=[('cedula', 'Cédula'), ('nit', 'NIT')],
        help_text='Tipo de documento: cedula o nit'
    )
    document_number = serializers.CharField(
        max_length=20,
        help_text='Número de documento sin puntos ni guiones'
    )
    nombre = serializers.CharField(
        max_length=200,
        help_text='Nombre completo o razón social'
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        help_text='Email del tercero'
    )
    telefono = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text='Teléfono del tercero'
    )
    nature = serializers.ChoiceField(
        choices=[('natural', 'Natural'), ('juridica', 'Jurídica')],
        help_text='Naturaleza: natural o juridica (determina tipo de documento J o N)'
    )


class TNSFacturaSerializer(TNSBaseSerializer):
    codcomp = serializers.CharField(required=False)
    codprefijo = serializers.CharField(required=False)
    fecha = serializers.DateField(required=False)
    periodo = serializers.IntegerField(required=False)
    formapago = serializers.CharField(required=False)
    plazodias = serializers.IntegerField(required=False)
    usuario = serializers.CharField(required=False)
    banco = serializers.CharField(required=False)
    nittri = serializers.CharField(required=False)
    numdocu = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    vid = serializers.CharField(required=False)


class TNSAdminEmpresasSerializer(TNSBaseSerializer):
    search_nit = serializers.CharField()


class TNSUserValidationSerializer(TNSBaseSerializer):
    username = serializers.CharField()
    password = serializers.CharField()


class TNSRecordsSerializer(TNSBaseSerializer):
    """Serializer para consultas dinámicas de tablas TNS"""
    table_name = serializers.CharField()
    fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    foreign_keys = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )
    filters = serializers.DictField(required=False, default=dict)
    order_by = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=50, min_value=1, max_value=500)


# ========== Branding e Imágenes Serializers ==========

class EmpresaPersonalizacionSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    video_por_defecto_url = serializers.SerializerMethodField()
    video_del_dia_url = serializers.SerializerMethodField()
    
    class Meta:
        model = EmpresaPersonalizacion
        fields = ['id', 'nit_normalizado', 'logo', 'logo_url', 'color_primario', 
                  'color_secundario', 'color_fondo', 'modo_teclado', 'modo_visualizacion',
                  'video_por_defecto', 'video_por_defecto_url',
                  'video_lunes', 'video_martes', 'video_miercoles', 'video_jueves',
                  'video_viernes', 'video_sabado', 'video_domingo', 'video_del_dia_url',
                  'fecha_creacion', 'fecha_actualizacion']
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None
    
    def get_video_por_defecto_url(self, obj):
        if obj.video_por_defecto:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.video_por_defecto.url)
            return obj.video_por_defecto.url
        return None
    
    def get_video_del_dia_url(self, obj):
        video_del_dia = obj.get_video_del_dia()
        if video_del_dia:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(video_del_dia.url)
            return video_del_dia.url
        return None


class PasarelaPagoSerializer(serializers.ModelSerializer):
    configuracion_str = serializers.SerializerMethodField()
    
    class Meta:
        model = PasarelaPago
        fields = ['id', 'codigo', 'nombre', 'activa', 'configuracion', 'configuracion_str', 'fecha_creacion', 'fecha_actualizacion']
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']
    
    def get_configuracion_str(self, obj):
        """Retorna configuración como string JSON formateado"""
        import json
        return json.dumps(obj.configuracion or {}, indent=2)


class TransaccionPagoSerializer(serializers.ModelSerializer):
    pasarela_nombre = serializers.CharField(source='pasarela_pago.nombre', read_only=True)
    
    class Meta:
        model = TransaccionPago
        fields = [
            'id', 'empresa_servidor', 'pasarela_pago', 'pasarela_nombre',
            'order_number', 'order_id', 'monto', 'estado',
            'datos_cliente', 'datos_respuesta', 'approval_code',
            'error_message', 'factura_tns_id',
            'fecha_creacion', 'fecha_actualizacion'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']


class EmpresaEcommerceConfigSerializer(serializers.ModelSerializer):
    empresa_servidor_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = EmpresaEcommerceConfig
        fields = [
            'id', 'empresa_servidor', 'empresa_servidor_id',
            'color_primario', 'color_secundario', 'color_fondo',
            'usar_degradado', 'color_degradado_inicio', 'color_degradado_fin', 'direccion_degradado',
            'hero_titulo', 'hero_subtitulo', 'hero_descripcion',
            'about_titulo', 'about_texto',
            'contact_titulo', 'contact_texto', 'whatsapp_numero',
            'footer_texto_logo', 'footer_links', 'footer_sections',
            'menu_items',
            'payment_provider', 'payment_public_key', 'payment_secret_key', 'payment_access_token',
            'payment_enabled', 'payment_mode', 'payment_window_type',
            'usuario_tns', 'password_tns',
            'logo_url',
            'mostrar_menu', 'mostrar_hero', 'mostrar_about', 'mostrar_contact', 'mostrar_footer', 'mostrar_categorias_footer',
            'estilo_tema',
            'fecha_creacion', 'fecha_actualizacion'
        ]
        read_only_fields = ['id', 'empresa_servidor', 'fecha_creacion', 'fecha_actualizacion']
    
    def validate(self, attrs):
        # Si viene empresa_servidor_id, convertirlo a empresa_servidor
        empresa_servidor_id = attrs.pop('empresa_servidor_id', None)
        if empresa_servidor_id and 'empresa_servidor' not in attrs:
            from .models import EmpresaServidor
            try:
                empresa_servidor = EmpresaServidor.objects.get(id=empresa_servidor_id)
                attrs['empresa_servidor'] = empresa_servidor
            except EmpresaServidor.DoesNotExist:
                raise serializers.ValidationError({'empresa_servidor_id': f'Empresa con ID {empresa_servidor_id} no encontrada'})
        return attrs
    
    def create(self, validated_data):
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Remover empresa_servidor_id si viene (no se puede cambiar en update)
        validated_data.pop('empresa_servidor_id', None)
        validated_data.pop('empresa_servidor', None)  # También remover empresa_servidor si viene
        return super().update(instance, validated_data)


class GrupoMaterialImagenSerializer(serializers.ModelSerializer):
    imagen_url = serializers.SerializerMethodField()
    
    class Meta:
        model = GrupoMaterialImagen
        fields = ['id', 'nit_normalizado', 'gm_codigo', 'imagen', 'imagen_url',
                  'fecha_creacion', 'fecha_actualizacion']
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']
    
    def get_imagen_url(self, obj):
        if obj.imagen:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.imagen.url)
            return obj.imagen.url
        return None


class MaterialImagenSerializer(serializers.ModelSerializer):
    imagen_url = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MaterialImagen
        fields = ['id', 'nit_normalizado', 'codigo_material', 'imagen', 'imagen_url',
                  'caracteristicas', 'pdf', 'pdf_url',
                  'fecha_creacion', 'fecha_actualizacion']
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']
    
    def get_imagen_url(self, obj):
        if obj.imagen:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.imagen.url)
            return obj.imagen.url
        return None
    
    def get_pdf_url(self, obj):
        if obj.pdf:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf.url)
            return obj.pdf.url
        return None


class CajaAutopagoSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source='empresa_servidor.nombre', read_only=True)
    empresa_nit = serializers.CharField(source='empresa_servidor.nit', read_only=True)
    
    class Meta:
        model = CajaAutopago
        fields = [
            'id', 'empresa_servidor', 'empresa_nombre', 'empresa_nit',
            'usuario_tns', 'nombre', 'ip_datafono', 'puerto_datafono',
            'activa', 'modo_mock', 'probabilidad_exito', 'modo_mock_dian',
            'fecha_creacion', 'fecha_actualizacion', 'usuario_creador'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']
    
    def validate_probabilidad_exito(self, value):
        """Validar que la probabilidad esté entre 0 y 1"""
        if value < 0 or value > 1:
            raise serializers.ValidationError("La probabilidad debe estar entre 0.0 y 1.0")
        return value


class VpnConfigSerializer(serializers.ModelSerializer):
    """Serializer para configuraciones VPN"""
    
    class Meta:
        model = VpnConfig
        fields = [
            'id', 'nombre', 'ip_address', 'public_key', 'activo',
            'fecha_creacion', 'fecha_actualizacion', 'notas'
        ]
        read_only_fields = ['id', 'public_key', 'fecha_creacion', 'fecha_actualizacion']
    
    def validate_ip_address(self, value):
        """Validar formato de IP (opcional)"""
        if value:
            parts = value.split('.')
            if len(parts) != 4:
                raise serializers.ValidationError("IP debe tener formato X.X.X.X")
            try:
                for part in parts:
                    num = int(part)
                    if num < 0 or num > 255:
                        raise serializers.ValidationError("Cada octeto debe estar entre 0 y 255")
            except ValueError:
                raise serializers.ValidationError("IP debe contener solo números")
        return value


class DescubrirEmpresasSerializer(serializers.Serializer):
    """Serializer para descubrir empresas en un servidor"""
    servidor_id = serializers.IntegerField(required=True, help_text="ID del servidor donde se buscarán las empresas")
    
    def validate_servidor_id(self, value):
        """Validar que el servidor exista"""
        from .models import Servidor
        try:
            Servidor.objects.get(id=value)
        except Servidor.DoesNotExist:
            raise serializers.ValidationError(f"Servidor con ID {value} no existe")
        return value


# ========== API Keys Serializers ==========

class APIKeyClienteSerializer(serializers.ModelSerializer):
    """Serializer para API Keys de clientes"""
    empresas_asociadas = serializers.SerializerMethodField()
    expirada = serializers.SerializerMethodField()
    empresas_asociadas_count = serializers.SerializerMethodField()
    servidor_nombre = serializers.CharField(source='servidor.nombre', read_only=True)
    
    class Meta:
        model = APIKeyCliente
        fields = [
            'id', 'nit', 'nombre_cliente', 'api_key', 'activa', 'servidor', 'servidor_nombre',
            'fecha_creacion', 'fecha_actualizacion', 'fecha_caducidad',
            'contador_peticiones', 'fecha_ultima_peticion',
            'empresas_asociadas', 'empresas_asociadas_count', 'expirada',
            'permite_scraping_total'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion', 'servidor_nombre']
    
    def get_empresas_asociadas(self, obj):
        """Obtener lista de empresas asociadas"""
        empresas = obj.empresas_asociadas.all()
        return [
            {
                'id': emp.id,
                'nombre': emp.nombre,
                'nit': emp.nit,
                'anio_fiscal': emp.anio_fiscal,
                'codigo': emp.codigo
            }
            for emp in empresas
        ]
    
    def get_empresas_asociadas_count(self, obj):
        """Contar empresas asociadas"""
        return obj.empresas_asociadas.count()
    
    def get_expirada(self, obj):
        """Verificar si la API Key está expirada"""
        return obj.esta_expirada()


class APIKeyNITCalendarioSerializer(serializers.ModelSerializer):
    """Serializer para NITs de RUTs asociados a API Keys para calendario tributario"""
    rut_razon_social = serializers.SerializerMethodField()
    rut_tipo_contribuyente = serializers.SerializerMethodField()
    
    class Meta:
        from .models import APIKeyNITCalendario
        model = APIKeyNITCalendario
        fields = [
            'id', 'api_key', 'nit_normalizado', 'rut', 'rut_razon_social',
            'rut_tipo_contribuyente', 'fecha_asociacion', 'activo'
        ]
        read_only_fields = ['id', 'fecha_asociacion']
    
    def get_rut_razon_social(self, obj):
        """Obtener razón social del RUT si existe"""
        if obj.rut:
            return obj.rut.razon_social
        return None
    
    def get_rut_tipo_contribuyente(self, obj):
        """Obtener tipo de contribuyente del RUT si existe"""
        if obj.rut:
            return obj.rut.tipo_contribuyente
        return None


class AsociarNITCalendarioSerializer(serializers.Serializer):
    """Serializer para asociar NITs de RUTs a una API Key"""
    nits = serializers.ListField(
        child=serializers.CharField(max_length=20),
        help_text="Lista de NITs (pueden tener formato, se normalizarán automáticamente)"
    )
    
    def validate_nits(self, value):
        """Normalizar NITs"""
        import re
        nits_normalizados = []
        for nit in value:
            nit_normalizado = re.sub(r"\D", "", str(nit))
            if nit_normalizado and len(nit_normalizado) >= 9:
                nits_normalizados.append(nit_normalizado)
        return nits_normalizados


class GenerarAPIKeySerializer(serializers.Serializer):
    """Serializer para generar API Key"""
    nit = serializers.CharField(required=True, help_text="NIT de la empresa (sin puntos ni guiones)")
    nombre_cliente = serializers.CharField(required=True, max_length=255, help_text="Nombre descriptivo del cliente")
    dias_validez = serializers.IntegerField(required=True, min_value=1, max_value=3650, help_text="Días de validez de la API Key (1-3650)")
    
    def validate_nit(self, value):
        """Normalizar NIT (eliminar puntos, guiones, espacios)"""
        import re
        return re.sub(r"\D", "", str(value))


# ========== User Management Serializers ==========

class UserSerializer(serializers.ModelSerializer):
    """Serializer para gestión de usuarios"""
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    is_superuser_display = serializers.SerializerMethodField()
    is_staff_display = serializers.SerializerMethodField()
    date_joined_formatted = serializers.SerializerMethodField()
    last_login_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'is_superuser',
            'is_superuser_display', 'is_staff_display',
            'date_joined', 'date_joined_formatted',
            'last_login', 'last_login_formatted',
            'password'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    def get_is_superuser_display(self, obj):
        return 'Sí' if obj.is_superuser else 'No'
    
    def get_is_staff_display(self, obj):
        return 'Sí' if obj.is_staff else 'No'
    
    def get_date_joined_formatted(self, obj):
        if obj.date_joined:
            return obj.date_joined.strftime('%Y-%m-%d %H:%M:%S')
        return None
    
    def get_last_login_formatted(self, obj):
        if obj.last_login:
            return obj.last_login.strftime('%Y-%m-%d %H:%M:%S')
        return 'Nunca'
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({'password': 'La contraseña es requerida al crear un usuario'})
        
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class CreateUserSerializer(serializers.ModelSerializer):
    """Serializer específico para crear usuarios"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm', 'is_active', 'is_staff', 'is_superuser']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Las contraseñas no coinciden'})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class EmpresaDominioSerializer(serializers.ModelSerializer):
    empresa_servidor_nombre = serializers.CharField(source='empresa_servidor.nombre', read_only=True)
    empresa_servidor_nit = serializers.CharField(source='empresa_servidor.nit', read_only=True)
    servidor_nombre = serializers.CharField(source='servidor.nombre', read_only=True)
    
    class Meta:
        model = EmpresaDominio
        fields = [
            'id', 'dominio', 'nit', 'servidor', 'servidor_nombre', 'empresa_servidor', 
            'empresa_servidor_nombre', 'empresa_servidor_nit', 'anio_fiscal', 'modo', 'activo',
            'fecha_creacion', 'fecha_actualizacion'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion', 'servidor_nombre']
    
    def validate_nit(self, value):
        """Normalizar NIT: eliminar puntos, guiones y espacios"""
        if not value:
            return value
        import re
        return re.sub(r"\D", "", str(value))
    
    def validate(self, attrs):
        """Auto-llenar empresa_servidor y anio_fiscal si se proporciona NIT"""
        nit = attrs.get('nit')
        if nit and not attrs.get('empresa_servidor'):
            # Normalizar NIT
            nit_normalizado = self.validate_nit(nit)
            if nit_normalizado:
                # Buscar empresa con año fiscal más reciente
                empresas = EmpresaServidor.objects.filter(nit_normalizado=nit_normalizado).order_by('-anio_fiscal')
                if empresas.exists():
                    empresa_mas_reciente = empresas.first()
                    attrs['empresa_servidor'] = empresa_mas_reciente
                    attrs['anio_fiscal'] = empresa_mas_reciente.anio_fiscal
        return attrs

class EstablecimientoRUTSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstablecimientoRUT
        fields = '__all__'
        read_only_fields = ['id', 'fecha_creacion']


class ActividadEconomicaSerializer(serializers.ModelSerializer):
    """Serializer para mostrar información completa de actividades económicas CIIU"""
    class Meta:
        model = ActividadEconomica
        fields = ['codigo', 'descripcion', 'titulo', 'division', 'grupo']


class RUTSerializer(serializers.ModelSerializer):
    establecimientos = EstablecimientoRUTSerializer(many=True, read_only=True)
    empresas_asociadas = serializers.SerializerMethodField()
    archivo_pdf_url = serializers.SerializerMethodField()
    actividad_principal_info = serializers.SerializerMethodField()
    actividad_secundaria_info = serializers.SerializerMethodField()
    otras_actividades_info = serializers.SerializerMethodField()
    persona_natural_nombre_completo = serializers.SerializerMethodField()
    responsabilidades_detalladas = serializers.SerializerMethodField()
    
    class Meta:
        model = RUT
        fields = [
            'id', 'nit_normalizado', 'nit', 'dv', 'numero_formulario',
            'tipo_contribuyente', 'razon_social', 'nombre_comercial', 'sigla',
            'pais', 'departamento_codigo', 'departamento_nombre',
            'ciudad_codigo', 'ciudad_nombre', 'direccion_principal',
            'codigo_postal', 'telefono_1', 'telefono_2', 'email',
            'direccion_seccional', 'buzon_electronico',
            'actividad_principal_ciiu', 'actividad_principal_fecha_inicio',
            'actividad_secundaria_ciiu', 'actividad_secundaria_fecha_inicio',
            'otras_actividades_ciiu', 'numero_establecimientos',
            'responsabilidades_codigos', 'responsabilidades_descripcion',
            'responsable_iva', 'autorretenedor', 'obligado_contabilidad',
            'regimen_simple', 'facturador_electronico', 'informante_exogena',
            'informante_beneficiarios_finales',
            'constitucion_clase', 'constitucion_numero', 'constitucion_fecha',
            'constitucion_notaria', 'registro_entidad', 'registro_fecha',
            'matricula_mercantil', 'registro_departamento', 'registro_ciudad',
            'vigencia_desde', 'vigencia_hasta',
            'capital_nacional_porcentaje', 'capital_nacional_publico_porcentaje',
            'capital_nacional_privado_porcentaje', 'capital_extranjero_porcentaje',
            'capital_extranjero_publico_porcentaje', 'capital_extranjero_privado_porcentaje',
            'entidad_vigilancia', 'entidad_vigilancia_codigo',
            'representante_legal_representacion', 'representante_legal_fecha_inicio',
            'representante_legal_tipo_doc', 'representante_legal_numero_doc',
            'representante_legal_dv', 'representante_legal_tarjeta_profesional',
            'representante_legal_primer_apellido', 'representante_legal_segundo_apellido',
            'representante_legal_primer_nombre', 'representante_legal_otros_nombres',
            'representante_legal_nit', 'representante_legal_razon_social',
            'vinculacion_economica', 'grupo_economico_nombre',
            'matriz_nit', 'matriz_dv', 'matriz_razon_social',
            'archivo_pdf', 'archivo_pdf_url', 'informacion_adicional',
            'establecimientos', 'empresas_asociadas',
            'actividad_principal_info', 'actividad_secundaria_info', 'otras_actividades_info',
            'persona_natural_nombre_completo', 'responsabilidades_detalladas',
            'fecha_creacion', 'fecha_actualizacion', 'fecha_ultima_consulta_dian'
        ]
        read_only_fields = ['id', 'nit_normalizado', 'fecha_creacion', 'fecha_actualizacion']
    
    def get_empresas_asociadas(self, obj):
        """Obtener todas las empresas con el mismo NIT normalizado"""
        from .models import EmpresaServidor
        empresas = EmpresaServidor.objects.filter(nit_normalizado=obj.nit_normalizado)
        return [
            {
                'id': emp.id,
                'nombre': emp.nombre,
                'nit': emp.nit,
                'anio_fiscal': emp.anio_fiscal,
                'servidor': emp.servidor.nombre if emp.servidor else None
            }
            for emp in empresas
        ]
    
    def get_archivo_pdf_url(self, obj):
        """URL del archivo PDF"""
        if obj.archivo_pdf:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.archivo_pdf.url)
            return obj.archivo_pdf.url
        return None
    
    def get_actividad_principal_info(self, obj):
        """Información detallada de la actividad principal CIIU"""
        if obj.actividad_principal_ciiu:
            try:
                actividad = ActividadEconomica.objects.get(codigo=obj.actividad_principal_ciiu)
                return ActividadEconomicaSerializer(actividad).data
            except ActividadEconomica.DoesNotExist:
                return {'codigo': obj.actividad_principal_ciiu, 'descripcion': 'No encontrada en BD'}
        return None
    
    def get_actividad_secundaria_info(self, obj):
        """Información detallada de la actividad secundaria CIIU"""
        if obj.actividad_secundaria_ciiu:
            try:
                actividad = ActividadEconomica.objects.get(codigo=obj.actividad_secundaria_ciiu)
                return ActividadEconomicaSerializer(actividad).data
            except ActividadEconomica.DoesNotExist:
                return {'codigo': obj.actividad_secundaria_ciiu, 'descripcion': 'No encontrada en BD'}
        return None
    
    def get_otras_actividades_info(self, obj):
        """Información detallada de otras actividades CIIU"""
        if obj.otras_actividades_ciiu:
            codigos = obj.otras_actividades_ciiu if isinstance(obj.otras_actividades_ciiu, list) else []
            actividades_info = []
            for codigo in codigos:
                try:
                    actividad = ActividadEconomica.objects.get(codigo=codigo)
                    actividades_info.append(ActividadEconomicaSerializer(actividad).data)
                except ActividadEconomica.DoesNotExist:
                    actividades_info.append({'codigo': codigo, 'descripcion': 'No encontrada en BD'})
            return actividades_info
        return []
    
    def get_persona_natural_nombre_completo(self, obj):
        """Obtener nombre completo para persona natural (apellidos + nombres)"""
        if obj.tipo_contribuyente == 'persona_natural':
            # Intentar obtener desde campos 31-34 si existen en informacion_adicional
            info_adicional = obj.informacion_adicional or {}
            apellido1 = info_adicional.get('persona_natural_primer_apellido', '')
            apellido2 = info_adicional.get('persona_natural_segundo_apellido', '')
            nombre1 = info_adicional.get('persona_natural_primer_nombre', '')
            nombre2 = info_adicional.get('persona_natural_otros_nombres', '')
            
            partes = [apellido1, apellido2, nombre1, nombre2]
            nombre_completo = ' '.join([p for p in partes if p])
            
            if nombre_completo:
                return {
                    'primer_apellido': apellido1,
                    'segundo_apellido': apellido2,
                    'primer_nombre': nombre1,
                    'otros_nombres': nombre2,
                    'nombre_completo': nombre_completo
                }
        return None
    
    def get_responsabilidades_detalladas(self, obj):
        """Obtener responsabilidades con códigos y descripciones"""
        codigos = obj.responsabilidades_codigos or []
        descripciones = obj.responsabilidades_descripcion or []
        
        responsabilidades = []
        for i, codigo in enumerate(codigos):
            descripcion = descripciones[i] if i < len(descripciones) else f'Responsabilidad código {codigo}'
            responsabilidades.append({
                'codigo': str(codigo),
                'descripcion': descripcion
            })
        
        return responsabilidades


class SubirRUTSerializer(serializers.Serializer):
    """Serializer para subir PDF de RUT o ZIP con múltiples PDFs"""
    archivo_pdf = serializers.FileField(
        required=False,
        help_text='Archivo PDF del RUT (para carga individual)'
    )
    archivo_zip = serializers.FileField(
        required=False,
        help_text='Archivo ZIP con múltiples PDFs de RUT (para carga masiva)'
    )
    nit = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='NIT (opcional, se detectará del PDF si no se proporciona)'
    )
    
    def validate(self, data):
        """Validar que se proporcione al menos un archivo"""
        if not data.get('archivo_pdf') and not data.get('archivo_zip'):
            raise serializers.ValidationError(
                'Debes proporcionar un archivo PDF o un archivo ZIP con PDFs'
            )
        if data.get('archivo_pdf') and data.get('archivo_zip'):
            raise serializers.ValidationError(
                'Solo puedes proporcionar un archivo PDF o un ZIP, no ambos'
            )
        return data

# ==================== Serializers para Clasificación Contable ====================

class ArticuloFacturaSerializer(serializers.Serializer):
    """Serializer para artículos de factura"""
    nombre = serializers.CharField(help_text='Nombre del artículo')
    cantidad = serializers.IntegerField(min_value=1)
    valor_unitario = serializers.DecimalField(max_digits=15, decimal_places=2)
    valor_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    ref = serializers.CharField(help_text='Referencia de factura')
    impuestos = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text='Lista de impuestos aplicados'
    )


class FacturaSerializer(serializers.Serializer):
    """Serializer para factura individual"""
    numero_factura = serializers.CharField(help_text='Número de factura')
    fecha = serializers.CharField(help_text='Fecha de factura')
    modalidad_pago = serializers.ChoiceField(
        choices=['credito', 'contado'],
        default='credito'
    )
    forma_pago = serializers.CharField(
        default='efectivo',
        help_text='Forma de pago (efectivo, transferencia, tarjeta, cheque)'
    )
    articulos = ArticuloFacturaSerializer(many=True)


class ClasificarFacturaSerializer(serializers.Serializer):
    """Serializer para clasificar una factura directamente"""
    factura = FacturaSerializer(required=False, help_text='Factura a clasificar (si no se usa session_id o document_id)')
    session_id = serializers.IntegerField(required=False, help_text='ID de sesión DIAN para cargar todas las facturas')
    document_id = serializers.IntegerField(required=False, help_text='ID de documento específico para clasificar')
    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='Lista de IDs de documentos para clasificación masiva'
    )
    empresa_nit = serializers.CharField(required=False, help_text='NIT de la empresa (se obtiene de sesión si no se proporciona)')
    empresa_ciuu_principal = serializers.CharField(required=False, help_text='CIUU principal de la empresa (se busca en RUT si no se proporciona)')
    empresa_ciuu_secundarios = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text='CIUUs secundarios de la empresa (se buscan en RUT si no se proporcionan)'
    )
    proveedor_nit = serializers.CharField(required=False, help_text='NIT del proveedor (se obtiene de documento si no se proporciona)')
    proveedor_ciuu = serializers.CharField(required=False, allow_null=True, help_text='CIUU del proveedor (se busca en RUT si no se proporciona)')
    aplica_retencion = serializers.BooleanField(default=False)
    porcentaje_retencion = serializers.FloatField(default=0, min_value=0, max_value=100)
    tipo_operacion = serializers.ChoiceField(
        choices=['compra', 'venta'],
        default='compra'
    )
    procesar_asincrono = serializers.BooleanField(
        default=False,
        help_text='Si True, procesa de forma asíncrona con Celery'
    )
    
    def validate(self, attrs):
        """Validar que se proporcione factura, session_id, document_id o document_ids"""
        factura = attrs.get('factura')
        session_id = attrs.get('session_id')
        document_id = attrs.get('document_id')
        document_ids = attrs.get('document_ids')
        
        opciones = sum([bool(factura), bool(session_id), bool(document_id), bool(document_ids)])
        
        if opciones == 0:
            raise serializers.ValidationError(
                "Debe proporcionar 'factura', 'session_id', 'document_id' o 'document_ids'"
            )
        
        if opciones > 1:
            raise serializers.ValidationError(
                "Proporcione solo una opción: 'factura', 'session_id', 'document_id' o 'document_ids'"
            )
        
        return attrs


class ClasificacionContableSerializer(serializers.ModelSerializer):
    """Serializer para modelo ClasificacionContable"""
    class Meta:
        model = ClasificacionContable
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'procesado_at']


class ExtraerDatosSerializer(serializers.Serializer):
    """Serializer para extraer datos de una empresa"""
    empresa_servidor_id = serializers.IntegerField(required=True, help_text="ID de la empresa de la cual extraer datos")
    fecha_inicio = serializers.DateField(required=True, help_text="Fecha de inicio del rango (YYYY-MM-DD)")
    fecha_fin = serializers.DateField(required=True, help_text="Fecha de fin del rango (YYYY-MM-DD)")
    forzar_reextraccion = serializers.BooleanField(required=False, default=False, help_text="Si True, fuerza la reextracción incluso si ya existe")
    
    def validate(self, attrs):
        """Validar que fecha_inicio sea anterior a fecha_fin"""
        fecha_inicio = attrs.get('fecha_inicio')
        fecha_fin = attrs.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise serializers.ValidationError("fecha_inicio debe ser anterior a fecha_fin")
        
        return attrs
    
    def validate_empresa_servidor_id(self, value):
        """Validar que la empresa exista"""
        from .models import EmpresaServidor
        try:
            EmpresaServidor.objects.get(id=value)
        except EmpresaServidor.DoesNotExist:
            raise serializers.ValidationError(f"Empresa con ID {value} no existe")
        return value


# ========== SERIALIZERS PARA CALENDARIO TRIBUTARIO ==========

class TipoTerceroSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoTercero
        fields = '__all__'
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']


class TipoRegimenSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoRegimen
        fields = '__all__'
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']


class ImpuestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Impuesto
        fields = '__all__'
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']


class VigenciaTributariaSerializer(serializers.ModelSerializer):
    impuesto_nombre = serializers.CharField(source='impuesto.nombre', read_only=True)
    impuesto_codigo = serializers.CharField(source='impuesto.codigo', read_only=True)
    tipo_tercero_nombre = serializers.CharField(source='tipo_tercero.nombre', read_only=True)
    tipo_tercero_codigo = serializers.CharField(source='tipo_tercero.codigo', read_only=True)
    tipo_regimen_nombre = serializers.CharField(source='tipo_regimen.nombre', read_only=True)
    tipo_regimen_codigo = serializers.CharField(source='tipo_regimen.codigo', read_only=True)
    
    class Meta:
        model = VigenciaTributaria
        fields = '__all__'
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']


class EntidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entidad
        fields = '__all__'
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']


class ContrasenaEntidadSerializer(serializers.ModelSerializer):
    entidad_nombre = serializers.CharField(source='entidad.nombre', read_only=True)
    entidad_sigla = serializers.CharField(source='entidad.sigla', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa_servidor.nombre', read_only=True)
    empresa_nit = serializers.CharField(source='empresa_servidor.nit', read_only=True)
    
    class Meta:
        model = ContrasenaEntidad
        fields = [
            'id', 'entidad', 'entidad_nombre', 'entidad_sigla',
            'nit_normalizado', 'empresa_servidor', 'empresa_nombre', 'empresa_nit',
            'descripcion', 'usuario', 'contrasena',
            'fecha_creacion', 'fecha_actualizacion'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']


class SubirCalendarioTributarioSerializer(serializers.Serializer):
    """Serializer para subir Excel del calendario tributario"""
    archivo_excel = serializers.FileField(
        required=True,
        help_text='Archivo Excel con el calendario tributario (formato: tax_code, expirations_digits, third_type_code, regiment_type_code, date, description)'
    )


class ConfiguracionS3Serializer(serializers.ModelSerializer):
    """Serializer para ConfiguracionS3"""
    class Meta:
        model = ConfiguracionS3
        fields = '__all__'
        extra_kwargs = {
            'secret_access_key': {'write_only': True},  # No mostrar en lectura
        }


class BackupS3Serializer(serializers.ModelSerializer):
    """Serializer para BackupS3"""
    empresa_nombre = serializers.CharField(source='empresa_servidor.nombre', read_only=True)
    empresa_nit = serializers.CharField(source='empresa_servidor.nit', read_only=True)
    configuracion_nombre = serializers.CharField(source='configuracion_s3.nombre', read_only=True)
    tamano_mb = serializers.ReadOnlyField()
    tamano_gb = serializers.ReadOnlyField()
    
    class Meta:
        model = BackupS3
        fields = '__all__'
        read_only_fields = ['fecha_creacion']
