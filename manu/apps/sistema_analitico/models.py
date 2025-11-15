# sistema_analitico/models.py
from django.db import models
from django.contrib.auth.models import User
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField, EncryptedEmailField
from django.utils import timezone
from datetime import timedelta
import json

class Servidor(models.Model):
    TIPO_SERVIDOR_CHOICES = [
        ('FIREBIRD', 'Firebird'),
        ('POSTGRESQL', 'PostgreSQL'),
        ('SQLSERVER', 'SQL Server'),
        ('MYSQL', 'MySQL'),
    ]
    
    nombre = models.CharField(max_length=255)
    host = models.CharField(max_length=255)
    usuario = models.CharField(max_length=255)
    password = EncryptedTextField(max_length=500)
    tipo_servidor = models.CharField(max_length=20, choices=TIPO_SERVIDOR_CHOICES)
    ruta_maestra = models.CharField(max_length=500, null=True, blank=True)
    puerto = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'servidores'
            
    def __str__(self):
        return f"{self.nombre} ({self.tipo_servidor})"

class EmpresaServidor(models.Model):
    servidor = models.ForeignKey(Servidor, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=255)
    nit = models.CharField(max_length=20)
    anio_fiscal = models.IntegerField()
    ruta_base = models.CharField(max_length=500)
    consulta_sql = models.TextField()
    ultima_extraccion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, default='ACTIVO')
    configuracion = models.JSONField(default=dict)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'empresas_servidor'
        unique_together = ['servidor', 'nit', 'anio_fiscal']
        
    def __str__(self):
        return f"{self.nombre} ({self.nit}) - {self.anio_fiscal} - {self.servidor.nombre}"
        
class UsuarioEmpresa(models.Model):
    """Relación directa entre usuarios y empresas"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='empresas_permitidas')
    empresa_servidor = models.ForeignKey(EmpresaServidor, on_delete=models.CASCADE, related_name='usuarios_permitidos')
    
    puede_ver = models.BooleanField(default=True)
    puede_editar = models.BooleanField(default=False)
    
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'usuario_empresa_permisos'
        unique_together = ['usuario', 'empresa_servidor']
    
    def __str__(self):
        return f"{self.usuario.username} - {self.empresa_servidor.nombre}"

class MovimientoInventario(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('FACTURA_VENTA', 'Factura de Venta'),
        ('REMISION_ENTRADA', 'Remisión de Entrada'),
        ('DEVOLUCION_VENTA', 'Devolución de Venta'),
        ('FACTURA_COMPRA', 'Factura de Compra'),
    ]
    
    empresa_servidor = models.ForeignKey(EmpresaServidor, on_delete=models.CASCADE)
    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOCUMENTO_CHOICES)
    fecha = models.DateTimeField()
    fecha_orden_pedido = models.DateTimeField(null=True, blank=True)
    
    # Campos paciente
    paciente = models.CharField(max_length=255, null=True, blank=True)
    cedula_paciente = models.CharField(max_length=20, null=True, blank=True)
    
    # Campos pagador
    pagador = models.CharField(max_length=255, null=True, blank=True)
    nit_pagador = models.CharField(max_length=20, null=True, blank=True)
    
    # Campos clínica
    clinica = models.CharField(max_length=255, null=True, blank=True)
    nit_clinica = models.CharField(max_length=20, null=True, blank=True)
    
    # Campos médico
    medico = models.CharField(max_length=255, null=True, blank=True)
    cedula_medico = models.CharField(max_length=20, null=True, blank=True)
    medico2 = models.CharField(max_length=255, null=True, blank=True)
    cedula_medico2 = models.CharField(max_length=20, null=True, blank=True)
    
    procedimientos = models.TextField(null=True, blank=True)
    
    # Campos ubicación
    codigo_ciudad = models.CharField(max_length=10, null=True, blank=True)
    ciudad = models.CharField(max_length=100)
    
    # Campos bodega
    tipo_bodega = models.CharField(max_length=100)
    codigo_bodega = models.CharField(max_length=10, null=True, blank=True)
    sistema_bodega = models.CharField(max_length=255)
    bodega_contenedor = models.CharField(max_length=255, null=True, blank=True)
    
    # Campos artículo
    articulo_nombre = models.CharField(max_length=255)
    articulo_codigo = models.CharField(max_length=100)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    lote = models.CharField(max_length=100, null=True, blank=True)
    stock_previo = models.IntegerField(null=True, blank=True)
    stock_nuevo = models.IntegerField(null=True, blank=True)
    
    # Campos calculados
    valor_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    lead_time_dias = models.IntegerField(null=True, blank=True)
    es_implante = models.BooleanField(default=False)
    es_instrumental = models.BooleanField(default=False)
    es_equipo_poder = models.BooleanField(default=False)
    
    fecha_extraccion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'movimientos_inventario'
        indexes = [
            # Índices existentes
            models.Index(fields=['empresa_servidor', 'fecha']),
            models.Index(fields=['articulo_codigo', 'tipo_bodega']),
            
            # NUEVOS ÍNDICES para consultas rápidas
            models.Index(fields=['nit_pagador']),
            models.Index(fields=['nit_clinica']),
            models.Index(fields=['cedula_paciente']),
            models.Index(fields=['cedula_medico']),
            models.Index(fields=['cedula_medico2']),
            models.Index(fields=['paciente']),
            models.Index(fields=['pagador']),
            models.Index(fields=['clinica']),
            models.Index(fields=['medico']),
            models.Index(fields=['medico2']),
            models.Index(fields=['ciudad']),
            models.Index(fields=['codigo_ciudad']),
            models.Index(fields=['codigo_bodega']),
            models.Index(fields=['tipo_bodega']),
            models.Index(fields=['articulo_codigo']),
            models.Index(fields=['articulo_nombre']),
            models.Index(fields=['fecha']),  # Índice individual para fecha
        ]
        
        
    def __str__(self):
        return f"{self.tipo_documento} - {self.articulo_codigo} ({self.cantidad})"
        
class APIKeyCliente(models.Model):
    nit = models.CharField(max_length=20, unique=True)
    nombre_cliente = models.CharField(max_length=255)
    api_key = models.CharField(max_length=100, unique=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_caducidad = models.DateTimeField()
    usuario_creador = models.ForeignKey(User, on_delete=models.CASCADE)
    empresas_asociadas = models.ManyToManyField('EmpresaServidor', blank=True)
    contador_peticiones = models.IntegerField(default=0)
    fecha_ultima_peticion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'api_keys_clientes'
    
    def __str__(self):
        return f"{self.nombre_cliente} ({self.nit})"
    
    def actualizar_empresas_asociadas(self):
        """Actualiza automáticamente las empresas asociadas a este NIT"""
        empresas = EmpresaServidor.objects.filter(nit=self.nit)
        self.empresas_asociadas.set(empresas)
        return empresas.count()
    
    def incrementar_contador(self):
        """Incrementa el contador y actualiza última petición"""
        self.contador_peticiones += 1
        self.fecha_ultima_peticion = timezone.now()
        self.save()
    
    def esta_expirada(self):
        """Verifica si la API Key ha expirado"""
        return timezone.now() > self.fecha_caducidad
    
    def renovar(self, dias=365):
        """Renueva la API Key por más días"""
        self.fecha_caducidad = timezone.now() + timedelta(days=dias)
        self.save()


class ConfiguracionSistema(models.Model):
    clave = models.CharField(max_length=100, unique=True)
    valor = models.TextField()
    descripcion = models.TextField(null=True, blank=True)
    tipo = models.CharField(max_length=50, default='TEXTO')
    
    class Meta:
        db_table = 'configuracion_sistema'
        
        
    def __str__(self):
        return f"{self.clave} ({self.tipo})"
        
def user_has_empresa_permission(self, empresa_servidor, permiso='ver'):
    if self.is_superuser:
        return True
    
    try:
        usuario_empresa = UsuarioEmpresa.objects.get(
            usuario=self, 
            empresa_servidor=empresa_servidor
        )
        return getattr(usuario_empresa, f'puede_{permiso}', False)
    except UsuarioEmpresa.DoesNotExist:
        return False

def user_empresas_permitidas(self):
    if self.is_superuser:
        return EmpresaServidor.objects.all()
    return EmpresaServidor.objects.filter(
        usuarios_permitidos__usuario=self,
        usuarios_permitidos__puede_ver=True
    ).distinct()
    
# Extender User para API Keys
def user_puede_gestionar_api_keys(self):
    if self.is_superuser:
        return True
    # Usuarios con permisos de edición en al menos una empresa pueden gestionar API Keys
    return UsuarioEmpresa.objects.filter(usuario=self, puede_editar=True).exists()

# Extender el modelo User
User.add_to_class('puede_gestionar_api_keys', user_puede_gestionar_api_keys)
User.add_to_class('has_empresa_permission', user_has_empresa_permission)
User.add_to_class('empresas_permitidas', user_empresas_permitidas)