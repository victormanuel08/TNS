from rest_framework import serializers
from .models import (
    PasarelaPago, TransaccionPago,
    Servidor, EmpresaServidor, MovimientoInventario, UsuarioEmpresa,
    EmpresaPersonalizacion, GrupoMaterialImagen, MaterialImagen, CajaAutopago,
    VpnConfig, EmpresaEcommerceConfig, APIKeyCliente
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
            # Buscar si existe otra empresa con el mismo NIT y año fiscal
            existing = EmpresaServidor.objects.filter(
                nit=nit,
                anio_fiscal=anio_fiscal
            )
            
            # Si estamos editando, excluir la instancia actual
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise serializers.ValidationError(
                    f'Ya existe una empresa con NIT {nit} y año fiscal {anio_fiscal} en otro servidor.'
                )
        
        return attrs


class UsuarioEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsuarioEmpresa
        fields = '__all__'


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
    class Meta:
        model = PasarelaPago
        fields = ['id', 'codigo', 'nombre', 'activa', 'configuracion']
        read_only_fields = ['id']


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
    
    class Meta:
        model = APIKeyCliente
        fields = [
            'id', 'nit', 'nombre_cliente', 'api_key', 'activa',
            'fecha_creacion', 'fecha_actualizacion', 'fecha_caducidad',
            'contador_peticiones', 'fecha_ultima_peticion',
            'empresas_asociadas', 'empresas_asociadas_count', 'expirada'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']
    
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


class GenerarAPIKeySerializer(serializers.Serializer):
    """Serializer para generar API Key"""
    nit = serializers.CharField(required=True, help_text="NIT de la empresa (sin puntos ni guiones)")
    nombre_cliente = serializers.CharField(required=True, max_length=255, help_text="Nombre descriptivo del cliente")
    dias_validez = serializers.IntegerField(required=True, min_value=1, max_value=3650, help_text="Días de validez de la API Key (1-3650)")
    
    def validate_nit(self, value):
        """Normalizar NIT (eliminar puntos, guiones, espacios)"""
        import re
        return re.sub(r"\D", "", str(value))


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
