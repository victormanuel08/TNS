# sistema_analitico/serializers.py
from rest_framework import serializers
from .models import Servidor, EmpresaServidor, MovimientoInventario, UsuarioEmpresa, APIKeyCliente

class ServidorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servidor
        fields = '__all__'

class EmpresaServidorSerializer(serializers.ModelSerializer):
    servidor_nombre = serializers.CharField(source='servidor.nombre', read_only=True)
    
    class Meta:
        model = EmpresaServidor
        fields = '__all__'
        
class UsuarioEmpresaSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa_servidor.nombre', read_only=True)
    
    class Meta:
        model = UsuarioEmpresa
        fields = ['id', 'usuario', 'empresa_servidor', 'usuario_username', 'empresa_nombre', 
                 'puede_ver', 'puede_editar', 'preferred_template', 'fecha_asignacion']

class MovimientoInventarioSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source='empresa_servidor.nombre', read_only=True)
    
    class Meta:
        model = MovimientoInventario
        fields = '__all__'

# Serializers para Sistema
class DescubrirEmpresasSerializer(serializers.Serializer):
    servidor_id = serializers.IntegerField()

class ExtraerDatosSerializer(serializers.Serializer):
    empresa_servidor_id = serializers.IntegerField()
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()
    forzar_reextraccion = serializers.BooleanField(default=False)

# Serializers para ML
class EntrenarModelosSerializer(serializers.Serializer):
    empresa_servidor_id = serializers.IntegerField()
    fecha_inicio = serializers.DateField(required=False)
    fecha_fin = serializers.DateField(required=False)

class PredecirDemandaSerializer(serializers.Serializer):
    modelo_id = serializers.CharField()
    meses = serializers.IntegerField(min_value=1, max_value=24, default=6)

class RecomendacionesComprasSerializer(serializers.Serializer):
    modelo_id = serializers.CharField()
    meses = serializers.IntegerField(min_value=1, max_value=12, default=6)
    nivel_servicio = serializers.FloatField(min_value=0.5, max_value=0.99, default=0.95)

# Serializers para Consultas Naturales
class ConsultaNaturalSerializer(serializers.Serializer):
    consulta = serializers.CharField(max_length=1000)
    empresa_servidor_id = serializers.IntegerField(required=False)
    
# Serializers para API Keys
class GenerarAPIKeySerializer(serializers.Serializer):
    nit = serializers.CharField(max_length=20)
    nombre_cliente = serializers.CharField(max_length=255)
    dias_validez = serializers.IntegerField(min_value=1, max_value=365, default=365)

class APIKeyClienteSerializer(serializers.ModelSerializer):
    empresas_asociadas_count = serializers.SerializerMethodField()
    expirada = serializers.SerializerMethodField()
    
    class Meta:
        model = APIKeyCliente
        fields = ['id', 'nit', 'nombre_cliente', 'activa', 'fecha_creacion', 
                 'fecha_caducidad', 'fecha_ultima_peticion', 'contador_peticiones',
                 'empresas_asociadas_count', 'expirada']
    
    def get_empresas_asociadas_count(self, obj):
        return obj.empresas_asociadas.count()
    
    def get_expirada(self, obj):
        return obj.esta_expirada()


class TNSBaseSerializer(serializers.Serializer):
    empresa_servidor_id = serializers.IntegerField(required=False)
    nit = serializers.CharField(required=False)
    anio_fiscal = serializers.IntegerField(required=False)

    def validate(self, attrs):
        if not attrs.get('empresa_servidor_id') and not attrs.get('nit'):
            raise serializers.ValidationError('Debes enviar empresa_servidor_id o nit.')
        return attrs


class TNSQuerySerializer(TNSBaseSerializer):
    sql = serializers.CharField()
    params = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class TNSProcedureSerializer(TNSBaseSerializer):
    procedure = serializers.CharField()
    params = serializers.DictField(child=serializers.CharField(), required=False, default=dict)


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
