# sistema_analitico/models.py
from django.db import models
from django.contrib.auth.models import User
import re
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

def normalize_nit_and_extract_dv(nit_value):
    """
    Normaliza NIT y extrae el dígito verificador (DV).
    
    Args:
        nit_value: NIT en cualquier formato (ej: "900.869.750-0", "900869750-0", "9008697500")
    
    Returns:
        tuple: (nit_normalizado, dv, nit_original)
        - nit_normalizado: Solo números sin puntos ni guiones (ej: "9008697500")
        - dv: Dígito verificador si existe, None si no (ej: "0")
        - nit_original: NIT con formato original preservado
    """
    if not nit_value:
        return '', None, ''
    
    nit_str = str(nit_value).strip()
    nit_original = nit_str
    
    # Separar NIT base y DV (si tiene guión)
    if '-' in nit_str:
        parts = nit_str.split('-')
        nit_base = parts[0]
        dv = parts[1] if len(parts) > 1 else None
    else:
        # Si no tiene guión, intentar extraer DV del final
        # Los NITs colombianos tienen 9 dígitos base + 1 DV
        nit_clean = re.sub(r'\D', '', nit_str)
        if len(nit_clean) == 10:
            nit_base = nit_clean[:-1]
            dv = nit_clean[-1]
        else:
            nit_base = nit_clean
            dv = None
    
    # Normalizar: solo números
    nit_normalizado = re.sub(r'\D', '', nit_base)
    
    return nit_normalizado, dv, nit_original


class EmpresaServidor(models.Model):
    servidor = models.ForeignKey(Servidor, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=255)
    nit = models.CharField(
        max_length=20,
        help_text='NIT con formato original (ej: 900.869.750-0)'
    )
    nit_normalizado = models.CharField(
        max_length=20,
        db_index=True,
        help_text='NIT normalizado sin puntos ni guiones (ej: 9008697500) - usado para búsquedas'
    )
    dv = models.CharField(
        max_length=1,
        null=True,
        blank=True,
        help_text='Dígito verificador del NIT'
    )
    anio_fiscal = models.IntegerField()
    ruta_base = models.CharField(max_length=500)
    consulta_sql = models.TextField(null=True, blank=True)
    ultima_extraccion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, default='ACTIVO')
    configuracion = models.JSONField(default=dict, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    # ========== CONFIGURACIÓN DE BACKUPS S3 ==========
    limite_espacio_gb = models.IntegerField(
        default=1,
        help_text='Límite de espacio en GB para backups (1, 5, 10, 15, 20, 50)'
    )
    hora_backup = models.TimeField(
        default='01:00',
        help_text='Hora programada para realizar backups (formato HH:MM)'
    )
    backups_habilitados = models.BooleanField(
        default=True,
        help_text='Indica si los backups automáticos están habilitados para esta empresa'
    )

    class Meta:
        db_table = 'empresas_servidor'
        unique_together = ['servidor', 'nit_normalizado', 'anio_fiscal']  # Único por servidor (permite duplicados en diferentes servidores)
        indexes = [
            models.Index(fields=['servidor', 'nit_normalizado', 'anio_fiscal']),
            models.Index(fields=['servidor', 'nit_normalizado']),
            models.Index(fields=['nit_normalizado']),  # Índice individual para búsquedas rápidas
        ]
    
    def save(self, *args, **kwargs):
        """Normaliza NIT automáticamente antes de guardar"""
        if self.nit:
            nit_norm, dv, nit_orig = normalize_nit_and_extract_dv(self.nit)
            self.nit_normalizado = nit_norm
            self.dv = dv
            # Preservar formato original si no estaba establecido
            if not self.nit or self.nit != nit_orig:
                # Si el nit original tenía formato, preservarlo
                if '.' in str(self.nit) or '-' in str(self.nit):
                    pass  # Ya tiene formato, mantenerlo
                else:
                    # Si no tenía formato, usar el original detectado
                    self.nit = nit_orig if nit_orig else self.nit
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.nombre} ({self.nit}) - {self.anio_fiscal} - {self.servidor.nombre}"
        
# Template choices centralizados para evitar duplicación
TEMPLATE_CHOICES = [
    ('retail', 'Retail / Autopago'),  # Pantalla táctil tipo McDonald's
    ('restaurant', 'Restaurante'),     # App de pedidos tipo Makos
    ('pro', 'Profesional'),            # Software contable full
]

class UsuarioEmpresa(models.Model):
    """Relación directa entre usuarios y empresas"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='empresas_permitidas')
    empresa_servidor = models.ForeignKey(EmpresaServidor, on_delete=models.CASCADE, related_name='usuarios_permitidos')
    
    puede_ver = models.BooleanField(default=True)
    puede_editar = models.BooleanField(default=False)
    preferred_template = models.CharField(max_length=20, choices=TEMPLATE_CHOICES, default='pro')
    
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'usuario_empresa_permisos'
        unique_together = ['usuario', 'empresa_servidor']
    
    def __str__(self):
        return f"{self.usuario.username} - {self.empresa_servidor.nombre}"


class UserTenantProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='tenant_profile'
    )
    subdomain = models.CharField(max_length=50, unique=True)
    preferred_template = models.CharField(
        max_length=20,
        choices=TEMPLATE_CHOICES,
        default='pro'
    )

    class Meta:
        db_table = 'user_tenant_profiles'

    def __str__(self):
        return f"{self.user.username} -> {self.subdomain}"


class RUT(models.Model):
    """
    Modelo para almacenar información del Registro Único Tributario (RUT)
    de empresas colombianas. Se identifica por NIT normalizado (sin puntos ni guiones).
    Un RUT aplica para todas las empresas con el mismo NIT, independientemente del año fiscal.
    """
    
    # ========== IDENTIFICACIÓN PRINCIPAL ==========
    nit_normalizado = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text='NIT normalizado (sin puntos ni guiones) - Identificador único'
    )
    nit = models.CharField(
        max_length=20,
        help_text='NIT con formato original'
    )
    dv = models.CharField(
        max_length=1,
        help_text='Dígito de Verificación'
    )
    numero_formulario = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Número de formulario del RUT'
    )
    
    TIPO_CONTRIBUYENTE_CHOICES = [
        ('persona_juridica', 'Persona jurídica'),
        ('persona_natural', 'Persona natural'),
    ]
    tipo_contribuyente = models.CharField(
        max_length=20,
        choices=TIPO_CONTRIBUYENTE_CHOICES,
        null=True,
        blank=True,
        help_text='Tipo de contribuyente'
    )
    
    razon_social = models.CharField(
        max_length=255,
        help_text='Razón social de la empresa'
    )
    nombre_comercial = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Nombre comercial'
    )
    sigla = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Sigla de la empresa'
    )
    
    # ========== UBICACIÓN ==========
    pais = models.CharField(
        max_length=100,
        default='COLOMBIA',
        help_text='País'
    )
    departamento_codigo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código del departamento'
    )
    departamento_nombre = models.CharField(
        max_length=100,
        help_text='Nombre del departamento'
    )
    ciudad_codigo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código de la ciudad/municipio'
    )
    ciudad_nombre = models.CharField(
        max_length=100,
        help_text='Nombre de la ciudad/municipio'
    )
    direccion_principal = models.TextField(
        help_text='Dirección de la sede principal'
    )
    codigo_postal = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código postal'
    )
    telefono_1 = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Teléfono principal'
    )
    telefono_2 = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Teléfono secundario'
    )
    email = models.EmailField(
        null=True,
        blank=True,
        help_text='Correo electrónico'
    )
    direccion_seccional = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Dirección seccional de la DIAN'
    )
    buzon_electronico = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Buzón electrónico'
    )
    
    # ========== ACTIVIDADES ECONÓMICAS ==========
    actividad_principal_ciiu = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código CIIU de actividad principal'
    )
    actividad_principal_fecha_inicio = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de inicio de actividad principal'
    )
    actividad_secundaria_ciiu = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código CIIU de actividad secundaria'
    )
    actividad_secundaria_fecha_inicio = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de inicio de actividad secundaria'
    )
    otras_actividades_ciiu = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código CIIU de otras actividades'
    )
    numero_establecimientos = models.IntegerField(
        default=0,
        help_text='Número de establecimientos'
    )
    
    # ========== RESPONSABILIDADES Y ATRIBUTOS ==========
    responsabilidades_codigos = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de códigos de responsabilidades'
    )
    responsabilidades_descripcion = models.JSONField(
        default=list,
        blank=True,
        help_text='Descripciones de las responsabilidades'
    )
    
    responsable_iva = models.BooleanField(
        default=False,
        help_text='Es responsable de IVA'
    )
    autorretenedor = models.BooleanField(
        default=False,
        help_text='Es autorretenedor'
    )
    obligado_contabilidad = models.BooleanField(
        default=False,
        help_text='Obligado a llevar contabilidad'
    )
    regimen_simple = models.BooleanField(
        default=False,
        help_text='Régimen Simple de Tributación - SIM'
    )
    facturador_electronico = models.BooleanField(
        default=False,
        help_text='Facturador electrónico'
    )
    informante_exogena = models.BooleanField(
        default=False,
        help_text='Informante de exogena'
    )
    informante_beneficiarios_finales = models.BooleanField(
        default=False,
        help_text='Informante de Beneficiarios Finales'
    )
    
    # ========== USUARIOS ADUANEROS Y EXPORTADORES ==========
    usuarios_aduaneros = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de códigos de usuarios aduaneros'
    )
    exportadores_forma = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Forma de exportador'
    )
    exportadores_tipo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Tipo de exportador'
    )
    
    # ========== CONSTITUCIÓN Y REGISTRO ==========
    constitucion_clase = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Clase de constitución'
    )
    constitucion_numero = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Número de constitución'
    )
    constitucion_fecha = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de constitución'
    )
    constitucion_notaria = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Número de notaría'
    )
    registro_entidad = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Entidad de registro'
    )
    registro_fecha = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de registro'
    )
    matricula_mercantil = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Número de matrícula mercantil'
    )
    registro_departamento = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código departamento de registro'
    )
    registro_ciudad = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código ciudad de registro'
    )
    vigencia_desde = models.DateField(
        null=True,
        blank=True,
        help_text='Vigencia desde'
    )
    vigencia_hasta = models.DateField(
        null=True,
        blank=True,
        help_text='Vigencia hasta'
    )
    
    # ========== COMPOSICIÓN DEL CAPITAL ==========
    capital_nacional_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Porcentaje de capital nacional'
    )
    capital_nacional_publico_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Porcentaje de capital nacional público'
    )
    capital_nacional_privado_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Porcentaje de capital nacional privado'
    )
    capital_extranjero_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Porcentaje de capital extranjero'
    )
    capital_extranjero_publico_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Porcentaje de capital extranjero público'
    )
    capital_extranjero_privado_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Porcentaje de capital extranjero privado'
    )
    
    # ========== ENTIDAD DE VIGILANCIA ==========
    entidad_vigilancia = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Entidad de vigilancia y control'
    )
    entidad_vigilancia_codigo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código de entidad de vigilancia'
    )
    
    # ========== REPRESENTANTE LEGAL ==========
    representante_legal_representacion = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Tipo de representación'
    )
    representante_legal_fecha_inicio = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha inicio ejercicio representación'
    )
    representante_legal_tipo_doc = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Tipo de documento'
    )
    representante_legal_numero_doc = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Número de identificación'
    )
    representante_legal_dv = models.CharField(
        max_length=1,
        null=True,
        blank=True,
        help_text='Dígito verificador'
    )
    representante_legal_tarjeta_profesional = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Número de tarjeta profesional'
    )
    representante_legal_primer_apellido = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Primer apellido'
    )
    representante_legal_segundo_apellido = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Segundo apellido'
    )
    representante_legal_primer_nombre = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Primer nombre'
    )
    representante_legal_otros_nombres = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Otros nombres'
    )
    representante_legal_nit = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='NIT del representante legal'
    )
    representante_legal_razon_social = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Razón social del representante legal'
    )
    
    # ========== VINCULACIÓN ECONÓMICA ==========
    vinculacion_economica = models.BooleanField(
        default=False,
        help_text='Tiene vinculación económica'
    )
    grupo_economico_nombre = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Nombre del grupo económico y/o empresarial'
    )
    matriz_nit = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='NIT de la matriz o controlante'
    )
    matriz_dv = models.CharField(
        max_length=1,
        null=True,
        blank=True,
        help_text='DV de la matriz'
    )
    matriz_razon_social = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Razón social de la matriz o controlante'
    )
    
    # ========== ARCHIVO Y METADATOS ==========
    archivo_pdf = models.FileField(
        upload_to='ruts/',
        null=True,
        blank=True,
        help_text='Archivo PDF del RUT original'
    )
    informacion_adicional = models.JSONField(
        default=dict,
        blank=True,
        help_text='Información adicional no estructurada'
    )
    
    # ========== AUDITORÍA ==========
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_ultima_consulta_dian = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Última vez que se consultó en DIAN'
    )
    
    class Meta:
        db_table = 'ruts'
        verbose_name = 'RUT'
        verbose_name_plural = 'RUTs'
        indexes = [
            models.Index(fields=['nit_normalizado']),
            models.Index(fields=['nit']),
            models.Index(fields=['razon_social']),
        ]
    
    def __str__(self):
        return f"{self.razon_social} - NIT: {self.nit}-{self.dv}"
    
    def save(self, *args, **kwargs):
        """Normalizar NIT antes de guardar y truncar campos si exceden límites"""
        if self.nit:
            # Normalizar NIT: eliminar puntos, guiones y espacios
            self.nit_normalizado = ''.join(c for c in str(self.nit) if c.isdigit())
        
        # Truncar campos CharField si exceden su max_length
        # Obtener todos los campos CharField del modelo dinámicamente
        from django.db import models as django_models
        for field in self._meta.get_fields():
            if isinstance(field, django_models.CharField):
                try:
                    value = getattr(self, field.name, None)
                    if value and field.max_length and len(str(value)) > field.max_length:
                        setattr(self, field.name, str(value)[:field.max_length])
                except (AttributeError, ValueError):
                    # Ignorar errores al acceder a campos relacionados o valores inválidos
                    pass
        
        super().save(*args, **kwargs)


class EstablecimientoRUT(models.Model):
    """
    Establecimientos adicionales de una empresa (sucursales, agencias, etc.)
    """
    rut = models.ForeignKey(
        RUT,
        on_delete=models.CASCADE,
        related_name='establecimientos',
        help_text='RUT al que pertenece este establecimiento'
    )
    
    tipo_establecimiento = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Tipo de establecimiento'
    )
    tipo_establecimiento_codigo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código del tipo de establecimiento'
    )
    actividad_economica_ciiu = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código CIIU de actividad económica'
    )
    actividad_economica_descripcion = models.TextField(
        null=True,
        blank=True,
        help_text='Descripción de la actividad económica'
    )
    nombre = models.CharField(
        max_length=255,
        help_text='Nombre del establecimiento'
    )
    departamento_codigo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código del departamento'
    )
    departamento_nombre = models.CharField(
        max_length=100,
        help_text='Nombre del departamento'
    )
    ciudad_codigo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Código de la ciudad/municipio'
    )
    ciudad_nombre = models.CharField(
        max_length=100,
        help_text='Nombre de la ciudad/municipio'
    )
    direccion = models.TextField(
        help_text='Dirección del establecimiento'
    )
    matricula_mercantil = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Número de matrícula mercantil'
    )
    fecha_matricula_mercantil = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de la matrícula mercantil'
    )
    telefono = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Teléfono del establecimiento'
    )
    fecha_cierre = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de cierre (si aplica)'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rut_establecimientos'
        verbose_name = 'Establecimiento RUT'
        verbose_name_plural = 'Establecimientos RUT'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} - {self.ciudad_nombre}"


class ActividadEconomica(models.Model):
    """
    Modelo para almacenar información completa de códigos CIIU (Clasificación Industrial Internacional Uniforme).
    Similar a EconomicActivities de BCE. El código CIIU es el índice único, no el ID.
    """
    codigo = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        help_text='Código CIIU completo (4-5 dígitos) - Índice único'
    )
    descripcion = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='Descripción de la actividad económica'
    )
    titulo = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='Título de la actividad económica'
    )
    division = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='División CIIU (primeros 2 dígitos)'
    )
    grupo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='Grupo CIIU (primeros 3 dígitos)'
    )
    incluye = models.JSONField(
        null=True,
        blank=True,
        default=list,
        help_text='Lista de actividades que incluye'
    )
    excluye = models.JSONField(
        null=True,
        blank=True,
        default=list,
        help_text='Lista de actividades que excluye'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_ultima_consulta_api = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Última vez que se consultó la API para actualizar información'
    )
    
    class Meta:
        db_table = 'actividades_economicas'
        verbose_name = 'Actividad Económica'
        verbose_name_plural = 'Actividades Económicas'
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['division']),
            models.Index(fields=['grupo']),
        ]
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.descripcion or self.titulo or 'Sin descripción'}"


class ResponsabilidadTributaria(models.Model):
    """
    Modelo para almacenar códigos de responsabilidades tributarias del RUT.
    El código es el índice único, no el ID.
    """
    codigo = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        help_text='Código de responsabilidad tributaria (ej: "7", "9", "14", "48", "52") - Índice único'
    )
    descripcion = models.CharField(
        max_length=255,
        help_text='Descripción de la responsabilidad tributaria'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'responsabilidades_tributarias'
        verbose_name = 'Responsabilidad Tributaria'
        verbose_name_plural = 'Responsabilidades Tributarias'
        indexes = [
            models.Index(fields=['codigo']),
        ]
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


# ========== MODELOS PARA CALENDARIO TRIBUTARIO ==========

class TipoTercero(models.Model):
    """
    Tipos de tercero para el calendario tributario (Persona Natural, Persona Jurídica).
    """
    codigo = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        help_text='Código del tipo de tercero (ej: "PN", "PJ")'
    )
    nombre = models.CharField(
        max_length=100,
        help_text='Nombre del tipo de tercero'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tipos_tercero'
        verbose_name = 'Tipo de Tercero'
        verbose_name_plural = 'Tipos de Tercero'
        indexes = [
            models.Index(fields=['codigo']),
        ]
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class TipoRegimen(models.Model):
    """
    Tipos de régimen tributario (Gran Contribuyente, Régimen Simple, Ordinario, etc.).
    """
    codigo = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        help_text='Código del régimen (ej: "GC", "SIM", "ORD")'
    )
    nombre = models.CharField(
        max_length=100,
        help_text='Nombre del régimen tributario'
    )
    descripcion = models.TextField(
        null=True,
        blank=True,
        help_text='Descripción del régimen tributario'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tipos_regimen'
        verbose_name = 'Tipo de Régimen'
        verbose_name_plural = 'Tipos de Régimen'
        indexes = [
            models.Index(fields=['codigo']),
        ]
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Impuesto(models.Model):
    """
    Impuestos tributarios (RGC, RPJ, RPN, IVB, IVC, AEE, RSA, RET, etc.).
    """
    codigo = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        help_text='Código del impuesto (ej: "RGC", "RPJ", "IVB", "IVC")'
    )
    nombre = models.CharField(
        max_length=100,
        help_text='Nombre del impuesto'
    )
    descripcion = models.TextField(
        null=True,
        blank=True,
        help_text='Descripción del impuesto'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'impuestos'
        verbose_name = 'Impuesto'
        verbose_name_plural = 'Impuestos'
        indexes = [
            models.Index(fields=['codigo']),
        ]
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class VigenciaTributaria(models.Model):
    """
    Vigencias tributarias: fechas límite de obligaciones según:
    - Impuesto
    - Últimos dígitos del NIT (1 o 2 dígitos)
    - Tipo de tercero (PN, PJ, o null para todos)
    - Régimen tributario (GC, SIM, ORD, o null para todos)
    """
    impuesto = models.ForeignKey(
        Impuesto,
        on_delete=models.CASCADE,
        related_name='vigencias',
        help_text='Impuesto al que aplica esta vigencia'
    )
    digitos_nit = models.CharField(
        max_length=2,
        blank=True,
        default='',
        db_index=True,
        help_text='Últimos 1 o 2 dígitos del NIT. Vacío ("") = aplica a todos los NITs. Ejemplos: "1", "2", "01", "99", "00"'
    )
    tipo_tercero = models.ForeignKey(
        TipoTercero,
        on_delete=models.PROTECT,
        related_name='vigencias',
        null=True,
        blank=True,
        help_text='Tipo de tercero (PN, PJ). Null = aplica a todos los tipos'
    )
    tipo_regimen = models.ForeignKey(
        TipoRegimen,
        on_delete=models.PROTECT,
        related_name='vigencias',
        null=True,
        blank=True,
        help_text='Régimen tributario (GC, SIM, ORD). Null = aplica a todos los regímenes'
    )
    fecha_limite = models.DateField(
        help_text='Fecha límite de la obligación tributaria'
    )
    descripcion = models.TextField(
        default='Sin definir',
        help_text='Descripción de la obligación tributaria'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vigencias_tributarias'
        verbose_name = 'Vigencia Tributaria'
        verbose_name_plural = 'Vigencias Tributarias'
        indexes = [
            models.Index(fields=['impuesto', 'digitos_nit']),
            models.Index(fields=['impuesto', 'tipo_tercero', 'tipo_regimen']),
            models.Index(fields=['fecha_limite']),
        ]
        ordering = ['impuesto', 'fecha_limite', 'digitos_nit']
        # Evitar duplicados exactos
        unique_together = [
            ['impuesto', 'digitos_nit', 'tipo_tercero', 'tipo_regimen', 'fecha_limite']
        ]
    
    def __str__(self):
        tercero = self.tipo_tercero.codigo if self.tipo_tercero else 'TODOS'
        regimen = self.tipo_regimen.codigo if self.tipo_regimen else 'TODOS'
        digitos = self.digitos_nit if self.digitos_nit else 'TODOS'
        return f"{self.impuesto.codigo} | Dígitos: {digitos} | {tercero} | {regimen} | {self.fecha_limite}"


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
    usuario_creador = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,  # Si se elimina el usuario, poner NULL
        null=True,  # Permitir NULL para casos donde no hay usuario (creación automática)
        blank=True,
        related_name='api_keys_creadas'
    )
    servidor = models.ForeignKey(
        Servidor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Servidor específico para esta API Key. Si está definido, solo se asociarán empresas de este servidor.'
    )
    empresas_asociadas = models.ManyToManyField('EmpresaServidor', blank=True)
    contador_peticiones = models.IntegerField(default=0)
    fecha_ultima_peticion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'api_keys_clientes'
    
    def __str__(self):
        return f"{self.nombre_cliente} ({self.nit})"
    
    def save(self, *args, **kwargs):
        """
        Guarda el modelo. 
        NOTA: usuario_creador ahora es opcional (null=True) para permitir
        creación automática desde scripts o migraciones. Sin embargo, cuando
        se crea desde la vista (APIKeyManagementViewSet.generar_api_key),
        siempre se establece automáticamente via request.user.
        """
        super().save(*args, **kwargs)
    
    def actualizar_empresas_asociadas(self):
        """
        Actualiza automáticamente las empresas asociadas a este NIT.
        Si la API Key tiene un servidor asociado, solo busca empresas de ese servidor.
        Si no tiene servidor, busca todas las empresas con el mismo NIT (comportamiento legacy).
        """
        import re
        # Normalizar NIT de la API Key (eliminar puntos, guiones, etc.)
        nit_normalizado_api = re.sub(r"\D", "", str(self.nit))
        
        # Buscar empresas por NIT normalizado
        empresas_query = EmpresaServidor.objects.filter(nit_normalizado=nit_normalizado_api)
        
        # Si la API Key tiene un servidor asociado, filtrar solo empresas de ese servidor
        if self.servidor:
            empresas_query = empresas_query.filter(servidor=self.servidor)
        
        empresas_directas = empresas_query.all()
        if empresas_directas.exists():
            self.empresas_asociadas.set(empresas_directas)
            return empresas_directas.count()
        
        # Si no se encontraron empresas, retornar 0
        return 0
    
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

class EmpresaPersonalizacion(models.Model):
    """
    Almacena logo y colores personalizados de una empresa.
    Usa NIT normalizado (sin puntos, sin guión y lo que viene después) como clave única.
    """
    nit_normalizado = models.CharField(max_length=20, unique=True, db_index=True)
    logo = models.ImageField(upload_to='empresas/logos/', null=True, blank=True)
    color_primario = models.CharField(max_length=7, default='#DC2626', help_text='Color principal (hex)')
    color_secundario = models.CharField(max_length=7, default='#FBBF24', help_text='Color secundario (hex)')
    color_fondo = models.CharField(max_length=7, default='#f5f5f5', help_text='Color de fondo (hex)')
    modo_teclado = models.CharField(
        max_length=20, 
        default='auto', 
        choices=[
            ('auto', 'Automático (inputmode)'),
            ('virtual', 'Teclado Virtual Personalizado'),
            ('hybrid', 'Híbrido (auto en móvil, virtual en desktop)')
        ],
        help_text='Modo de teclado para el terminal de autopago'
    )
    modo_visualizacion = models.CharField(
        max_length=20,
        default='vertical',
        choices=[
            ('vertical', 'Vertical (Comida) - Grid con scroll vertical'),
            ('horizontal', 'Horizontal (Otros) - Dos filas con scroll lateral')
        ],
        help_text='Modo de visualización de productos en el terminal de autopago'
    )
    # Videos para protector de pantalla
    video_por_defecto = models.FileField(
        upload_to='empresas/videos/', 
        null=True, 
        blank=True,
        help_text='Video por defecto para el protector de pantalla'
    )
    video_lunes = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    video_martes = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    video_miercoles = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    video_jueves = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    video_viernes = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    video_sabado = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    video_domingo = models.FileField(upload_to='empresas/videos/', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'empresa_personalizacion'
        verbose_name = 'Personalización de Empresa'
        verbose_name_plural = 'Personalizaciones de Empresas'

    def save(self, *args, **kwargs):
        """Redimensiona el logo al guardar si existe"""
        if self.logo:
            from PIL import Image
            import os
            from django.core.files.uploadedfile import InMemoryUploadedFile
            import io
            from django.core.files.base import ContentFile
            
            # Abrir imagen
            img = Image.open(self.logo)
            
            # Convertir a RGB si es necesario (para PNG con transparencia)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Tamaño máximo para logo: 300x100px (mantener aspect ratio)
            max_width, max_height = 300, 100
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Guardar en memoria
            thumb_io = io.BytesIO()
            img.save(thumb_io, format='JPEG', quality=85, optimize=True)
            thumb_io.seek(0)
            
            # Reemplazar el archivo original
            self.logo.save(
                os.path.basename(self.logo.name),
                ContentFile(thumb_io.read()),
                save=False
            )
            thumb_io.close()
        
        super().save(*args, **kwargs)
    
    def get_video_del_dia(self):
        """Retorna el video correspondiente al día de la semana actual"""
        from datetime import datetime
        dia_semana = datetime.now().weekday()  # 0=Lunes, 6=Domingo
        
        videos_dia = {
            0: self.video_lunes,
            1: self.video_martes,
            2: self.video_miercoles,
            3: self.video_jueves,
            4: self.video_viernes,
            5: self.video_sabado,
            6: self.video_domingo,
        }
        
        return videos_dia.get(dia_semana)
    
    def delete(self, *args, **kwargs):
        """Elimina los archivos asociados cuando se elimina el objeto"""
        import os
        videos = [
            self.video_por_defecto,
            self.video_lunes, self.video_martes, self.video_miercoles,
            self.video_jueves, self.video_viernes, self.video_sabado, self.video_domingo
        ]
        for video in videos:
            if video:
                try:
                    if os.path.exists(video.path):
                        os.remove(video.path)
                except Exception:
                    pass
        if self.logo:
            try:
                if os.path.exists(self.logo.path):
                    os.remove(self.logo.path)
            except Exception:
                pass
        super().delete(*args, **kwargs)
    

class EmpresaDominio(models.Model):
    """
    Relación entre dominio público y empresa TNS.
    Se usa para resolver la empresa (EmpresaServidor) a partir del host del request.
    Al crear, solo se requiere dominio y nit. La empresa_servidor y anio_fiscal se determinan en la primera búsqueda.
    """
    MODO_CHOICES = [
        ('autopago', 'Autopago / Retail'),
        ('ecommerce', 'E-commerce público'),
        ('pro', 'Profesional'),
    ]

    dominio = models.CharField(
        max_length=255,
        unique=True,
        help_text='Dominio completo, por ejemplo: pepito.ecommerce.miapp.com',
    )
    nit = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='NIT de la empresa (sin puntos ni guiones). Se usa para buscar la empresa con año fiscal más reciente.',
    )
    servidor = models.ForeignKey(
        Servidor,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text='Servidor autorizado para este dominio. Si está definido, solo se buscarán empresas de este servidor.',
    )
    empresa_servidor = models.ForeignKey(
        EmpresaServidor,
        on_delete=models.CASCADE,
        related_name='dominios_publicos',
        null=True,
        blank=True,
        help_text='Empresa servidor asociada a este dominio. Se determina automáticamente en la primera búsqueda, respetando el servidor autorizado.',
    )
    anio_fiscal = models.IntegerField(
        null=True,
        blank=True,
        help_text='Año fiscal más reciente de la empresa. Se actualiza automáticamente si es menor al año actual.',
    )
    modo = models.CharField(
        max_length=20,
        choices=MODO_CHOICES,
        default='ecommerce',
        help_text='Modo principal de este dominio (ecommerce, autopago, pro)',
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'empresa_dominios'
        verbose_name = 'Dominio de Empresa'
        verbose_name_plural = 'Dominios de Empresas'

    def save(self, *args, **kwargs):
        """
        Busca y actualiza automáticamente la empresa_servidor y anio_fiscal:
        1. Si no hay empresa_servidor pero hay nit, busca la empresa con año fiscal más reciente
        2. Si hay empresa_servidor pero anio_fiscal es None o menor al año actual, busca la más reciente
        """
        from django.utils import timezone
        
        # Función auxiliar para normalizar NIT (copiada de views.py)
        def normalize_nit(value: str) -> str:
            """Normaliza NIT: elimina puntos, guiones y espacios, solo dígitos"""
            if not value:
                return ''
            return ''.join(c for c in str(value) if c.isdigit())
        
        # Obtener año actual
        anio_actual = timezone.now().year
        
        # Si no hay empresa_servidor pero hay nit, buscar la empresa
        if not self.empresa_servidor_id and self.nit:
            nit_normalizado = normalize_nit(self.nit)
            if nit_normalizado:
                # Buscar empresas con el mismo NIT normalizado, ordenadas por año fiscal descendente
                empresas_mismo_nit = EmpresaServidor.objects.filter(
                    nit_normalizado=nit_normalizado
                )
                
                # Si hay un servidor autorizado, filtrar solo empresas de ese servidor
                if self.servidor:
                    empresas_mismo_nit = empresas_mismo_nit.filter(servidor=self.servidor)
                
                empresas_mismo_nit = empresas_mismo_nit.order_by('-anio_fiscal')
                
                if empresas_mismo_nit.exists():
                    empresa_mas_reciente = empresas_mismo_nit.first()
                    self.empresa_servidor = empresa_mas_reciente
                    self.anio_fiscal = empresa_mas_reciente.anio_fiscal
                    print(f"[EmpresaDominio] Dominio '{self.dominio}': empresa encontrada por NIT '{nit_normalizado}' en servidor '{self.servidor.nombre if self.servidor else 'cualquiera'}': {empresa_mas_reciente.nombre} (Año: {empresa_mas_reciente.anio_fiscal})")
        
        # Si hay empresa_servidor, verificar si necesita actualizar el año fiscal
        if self.empresa_servidor_id:
            # Si anio_fiscal no está establecido o es menor al año actual, buscar el más reciente
            if self.anio_fiscal is None or self.anio_fiscal < anio_actual:
                # Obtener NIT normalizado (del campo nit o de la empresa actual)
                nit_normalizado = None
                if self.nit:
                    nit_normalizado = normalize_nit(self.nit)
                elif self.empresa_servidor.nit:
                    nit_normalizado = normalize_nit(self.empresa_servidor.nit)
                
                if nit_normalizado:
                    # Buscar empresas con el mismo NIT normalizado
                    empresas_mismo_nit = EmpresaServidor.objects.filter(
                        nit_normalizado=nit_normalizado
                    )
                    
                    # Si hay un servidor autorizado, filtrar solo empresas de ese servidor
                    # Si ya hay empresa_servidor, usar su servidor como referencia
                    servidor_filtro = self.servidor or (self.empresa_servidor.servidor if self.empresa_servidor else None)
                    if servidor_filtro:
                        empresas_mismo_nit = empresas_mismo_nit.filter(servidor=servidor_filtro)
                    
                    empresas_mismo_nit = empresas_mismo_nit.order_by('-anio_fiscal')
                    
                    if empresas_mismo_nit.exists():
                        # Usar el año fiscal más reciente
                        empresa_mas_reciente = empresas_mismo_nit.first()
                        self.anio_fiscal = empresa_mas_reciente.anio_fiscal
                        # Actualizar también la empresa_servidor si es diferente
                        if empresa_mas_reciente.id != self.empresa_servidor_id:
                            empresa_anterior = self.empresa_servidor
                            self.empresa_servidor = empresa_mas_reciente
                            print(f"[EmpresaDominio] Actualizado dominio '{self.dominio}': empresa {empresa_anterior.id} -> {empresa_mas_reciente.id}, año fiscal {self.anio_fiscal}")
                    else:
                        # Si no se encuentra, usar el año fiscal de la empresa actual
                        if self.anio_fiscal is None:
                            self.anio_fiscal = self.empresa_servidor.anio_fiscal
                else:
                    # Si no hay NIT, usar el año fiscal de la empresa actual
                    if self.anio_fiscal is None:
                        self.anio_fiscal = self.empresa_servidor.anio_fiscal
        
        super().save(*args, **kwargs)

    def __str__(self):
        empresa_nombre = self.empresa_servidor.nombre if self.empresa_servidor else 'Sin empresa'
        return f"{self.dominio} -> {empresa_nombre} ({self.modo}, año: {self.anio_fiscal or 'N/A'})"


class EmpresaEcommerceConfig(models.Model):
    """
    Configuración completa del e-commerce para una empresa.
    Incluye colores, textos editables, footer, secciones, etc.
    """
    empresa_servidor = models.OneToOneField(
        EmpresaServidor,
        on_delete=models.CASCADE,
        related_name='ecommerce_config',
        help_text='Empresa servidor asociada'
    )
    
    # Colores y estilos
    color_primario = models.CharField(max_length=7, default='#DC2626', help_text='Color principal (hex)')
    color_secundario = models.CharField(max_length=7, default='#FBBF24', help_text='Color secundario (hex)')
    color_fondo = models.CharField(max_length=7, default='#FFFFFF', help_text='Color de fondo (hex)')
    usar_degradado = models.BooleanField(default=False, help_text='Usar degradado en lugar de color sólido')
    color_degradado_inicio = models.CharField(max_length=7, default='#DC2626', help_text='Color inicio del degradado')
    color_degradado_fin = models.CharField(max_length=7, default='#FBBF24', help_text='Color fin del degradado')
    direccion_degradado = models.CharField(
        max_length=20,
        default='to right',
        choices=[
            ('to right', 'Izquierda a Derecha'),
            ('to bottom', 'Arriba a Abajo'),
            ('to bottom right', 'Diagonal'),
        ],
        help_text='Dirección del degradado'
    )
    
    # Textos editables - Hero Section
    hero_titulo = models.CharField(max_length=200, default='Bienvenido a nuestra tienda en línea', help_text='Título principal')
    hero_subtitulo = models.CharField(max_length=200, default='Pedidos rápidos, sencillos y sin filas', help_text='Subtítulo')
    hero_descripcion = models.TextField(default='Explora nuestro menú y realiza tu pedido en pocos clics.', help_text='Descripción')
    
    # Textos editables - About
    about_titulo = models.CharField(max_length=200, default='Sobre nosotros', help_text='Título de la sección About')
    about_texto = models.TextField(
        default='Somos una marca enfocada en ofrecer la mejor experiencia gastronómica, con ingredientes frescos y recetas únicas.',
        help_text='Texto de la sección About'
    )
    
    # Textos editables - Contact
    contact_titulo = models.CharField(max_length=200, default='Contáctanos', help_text='Título de la sección Contact')
    contact_texto = models.TextField(
        default='Para más información sobre pedidos corporativos, eventos o alianzas, contáctanos a través de nuestros canales oficiales.',
        help_text='Texto de la sección Contact'
    )
    whatsapp_numero = models.CharField(max_length=20, null=True, blank=True, help_text='Número de WhatsApp (solo dígitos)')
    
    # Footer - Texto debajo del logo
    footer_texto_logo = models.TextField(
        null=True,
        blank=True,
        help_text='Texto que aparece debajo del logo en el footer'
    )
    
    # Footer - Links (JSON field para flexibilidad)
    footer_links = models.JSONField(
        default=list,
        help_text='Lista de links del footer. Formato: [{"titulo": "Título", "url": "url", "tipo": "modal|external|file", "icono": "emoji"}]'
    )
    
    # Footer - Secciones (JSON field para organizar links en secciones)
    footer_sections = models.JSONField(
        default=list,
        help_text='Lista de secciones del footer. Formato: [{"titulo": "Título Sección", "links": [{"icono": "emoji", "titulo": "Título", "url": "url", "tipo": "modal|external|file"}]}]'
    )
    
    # Menú - Items del menú principal
    menu_items = models.JSONField(
        default=list,
        help_text='Lista de items del menú. Formato: [{"icono": "emoji", "texto": "Texto", "tipo": "scroll|modal|external|file|content", "destino": "id_seccion|url", "contenido": "html/texto"}]'
    )
    
    # Pasarela de Pago
    # Nota: payment_provider almacena el código de PasarelaPago (ej: 'credibanco')
    # No tiene choices restrictivos porque las pasarelas se gestionan dinámicamente
    payment_provider = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Código de la pasarela de pago (debe coincidir con PasarelaPago.codigo, ej: credibanco)'
    )
    payment_public_key = models.CharField(max_length=255, null=True, blank=True, help_text='Clave pública del proveedor de pago')
    payment_secret_key = models.CharField(max_length=255, null=True, blank=True, help_text='Clave privada (solo backend)')
    payment_access_token = models.CharField(max_length=255, null=True, blank=True, help_text='Access Token (para Mercado Pago)')
    payment_enabled = models.BooleanField(default=False, help_text='Habilitar pagos en línea')
    payment_mode = models.CharField(
        max_length=10,
        default='test',
        choices=[('test', 'Prueba'), ('live', 'Producción')],
        help_text='Modo de la pasarela de pago'
    )
    payment_window_type = models.CharField(
        max_length=20,
        default='new_window',
        choices=[
            ('new_window', 'Nueva Ventana/Pestaña'),
            ('modal', 'Modal (iframe)'),
            ('same_window', 'Misma Ventana')
        ],
        help_text='Cómo abrir la pasarela de pago'
    )
    
    # Logo principal
    logo_url = models.URLField(null=True, blank=True, help_text='URL del logo principal (PNG transparente recomendado)')
    
    # Configuración de secciones (mostrar/ocultar)
    mostrar_menu = models.BooleanField(default=True, help_text='Mostrar menú principal')
    mostrar_hero = models.BooleanField(default=True, help_text='Mostrar sección Hero')
    mostrar_about = models.BooleanField(default=True, help_text='Mostrar sección About')
    mostrar_contact = models.BooleanField(default=True, help_text='Mostrar sección Contact')
    mostrar_footer = models.BooleanField(default=True, help_text='Mostrar footer')
    mostrar_categorias_footer = models.BooleanField(default=True, help_text='Mostrar categorías en el footer')
    
    # Credenciales TNS para inserción de facturas
    usuario_tns = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Usuario TNS para inserción de facturas (ej: ADMIN)'
    )
    password_tns = EncryptedCharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Contraseña del usuario TNS (encriptada)'
    )
    
    # Estilo general (similar a autopago)
    estilo_tema = models.CharField(
        max_length=20,
        default='balanceado',
        choices=[
            ('balanceado', 'Balanceado (Recomendado)'),
            ('moderno', 'Moderno'),
            ('minimalista', 'Minimalista'),
            ('colorido', 'Colorido'),
            ('elegante', 'Elegante'),
        ],
        help_text='Tema de estilo general'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'empresa_ecommerce_config'
        verbose_name = 'Configuración E-commerce'
        verbose_name_plural = 'Configuraciones E-commerce'
    
    def __str__(self):
        return f"E-commerce Config: {self.empresa_servidor.nombre}"


class PasarelaPago(models.Model):
    """
    Modelo para gestionar las pasarelas de pago disponibles.
    Por ahora solo tiene Credibanco, pero puede extenderse.
    """
    codigo = models.CharField(
        max_length=50,
        unique=True,
        help_text='Código único de la pasarela (ej: credibanco)'
    )
    nombre = models.CharField(
        max_length=100,
        help_text='Nombre descriptivo de la pasarela (ej: Credibanco)'
    )
    activa = models.BooleanField(
        default=True,
        help_text='Si la pasarela está activa y disponible'
    )
    configuracion = models.JSONField(
        default=dict,
        blank=True,
        help_text='Configuración específica de la pasarela (URLs, endpoints, campos adicionales). Formato JSON.'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pasarela_pago'
        verbose_name = 'Pasarela de Pago'
        verbose_name_plural = 'Pasarelas de Pago'
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class TransaccionPago(models.Model):
    """
    Modelo para guardar todas las transacciones de pago del e-commerce.
    Se crea cuando se inicia un pago y se actualiza cuando Credibanco responde.
    """
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('PROCESANDO', 'Procesando'),
        ('EXITOSA', 'Exitosa'),
        ('FALLIDA', 'Fallida'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    empresa_servidor = models.ForeignKey(
        EmpresaServidor,
        on_delete=models.CASCADE,
        related_name='transacciones_pago',
        help_text='Empresa a la que pertenece esta transacción'
    )
    pasarela_pago = models.ForeignKey(
        PasarelaPago,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transacciones',
        help_text='Pasarela de pago utilizada'
    )
    order_number = models.CharField(
        max_length=100,
        unique=True,
        help_text='Número de orden único (correlativo)'
    )
    order_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='ID de orden de la pasarela (ej: orderId de Credibanco)'
    )
    monto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Monto de la transacción'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PENDIENTE',
        help_text='Estado actual de la transacción'
    )
    datos_cliente = models.JSONField(
        default=dict,
        help_text='Datos del cliente (nombres, apellidos, email, teléfono, dirección, etc.)'
    )
    datos_respuesta = models.JSONField(
        null=True,
        blank=True,
        help_text='Respuesta completa de la pasarela de pago'
    )
    approval_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Código de autorización de la pasarela'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Mensaje de error si la transacción falló'
    )
    factura_tns_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='ID de la factura creada en TNS (si la transacción fue exitosa)'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transaccion_pago'
        verbose_name = 'Transacción de Pago'
        verbose_name_plural = 'Transacciones de Pago'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['order_id']),
            models.Index(fields=['estado']),
            models.Index(fields=['empresa_servidor', 'fecha_creacion']),
        ]
    
    def __str__(self):
        return f"Transacción {self.order_number} - {self.estado} - ${self.monto}"


class GrupoMaterialImagen(models.Model):
    """
    Almacena imágenes para grupos de materiales (categorías).
    Usa NIT normalizado y código de grupo (GM_CODIGO) como clave única.
    """
    nit_normalizado = models.CharField(max_length=20, db_index=True)
    gm_codigo = models.CharField(max_length=50, db_index=True)
    imagen = models.ImageField(upload_to='grupos/', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'grupo_material_imagen'
        unique_together = [['nit_normalizado', 'gm_codigo']]
        indexes = [
            models.Index(fields=['nit_normalizado', 'gm_codigo']),
        ]
        verbose_name = 'Imagen de Grupo de Material'
        verbose_name_plural = 'Imágenes de Grupos de Material'
    
    def save(self, *args, **kwargs):
        """Redimensiona la imagen al guardar si existe, preservando transparencia PNG"""
        import os
        # Eliminar imagen anterior si existe y se está reemplazando
        if self.pk:  # Si el objeto ya existe en la BD
            try:
                old_instance = GrupoMaterialImagen.objects.get(pk=self.pk)
                if old_instance.imagen and old_instance.imagen != self.imagen:
                    # Si hay una imagen anterior diferente, eliminarla
                    if os.path.exists(old_instance.imagen.path):
                        os.remove(old_instance.imagen.path)
            except GrupoMaterialImagen.DoesNotExist:
                pass
        
        if self.imagen:
            from PIL import Image
            from django.core.files.uploadedfile import InMemoryUploadedFile
            import io
            from django.core.files.base import ContentFile
            
            # Abrir imagen
            img = Image.open(self.imagen)
            original_format = img.format
            has_transparency = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
            
            # Si tiene transparencia, mantenerla; si no, convertir a RGB
            if has_transparency:
                # Mantener transparencia: convertir P a RGBA si es necesario
                if img.mode == 'P':
                    img = img.convert('RGBA')
                # No convertir a RGB, mantener RGBA o LA
            else:
                # Sin transparencia: convertir a RGB para optimizar
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
            
            # Tamaño para categorías: 200x200px (cuadrado, mantener aspect ratio)
            max_size = 200
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Guardar en memoria
            thumb_io = io.BytesIO()
            
            # Si tiene transparencia, guardar como PNG; si no, como JPEG
            if has_transparency:
                img.save(thumb_io, format='PNG', optimize=True)
            else:
                img.save(thumb_io, format='JPEG', quality=85, optimize=True)
            
            thumb_io.seek(0)
            
            # Reemplazar el archivo original
            self.imagen.save(
                os.path.basename(self.imagen.name),
                ContentFile(thumb_io.read()),
                save=False
            )
            thumb_io.close()
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Elimina la imagen del sistema de archivos cuando se elimina el objeto"""
        import os
        if self.imagen:
            if os.path.exists(self.imagen.path):
                os.remove(self.imagen.path)
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"Grupo {self.gm_codigo} - NIT: {self.nit_normalizado}"


class MaterialImagen(models.Model):
    """
    Almacena imágenes, características y PDF para materiales (artículos) individuales.
    Usa NIT normalizado y código de material (CODIGO) como clave única.
    """
    nit_normalizado = models.CharField(max_length=20, db_index=True)
    codigo_material = models.CharField(max_length=50, db_index=True)
    imagen = models.ImageField(upload_to='materiales/', null=True, blank=True)
    caracteristicas = models.TextField(null=True, blank=True, help_text='Características del producto')
    pdf = models.FileField(upload_to='materiales/pdfs/', null=True, blank=True, help_text='PDF con información del producto')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'material_imagen'
        unique_together = [['nit_normalizado', 'codigo_material']]
        indexes = [
            models.Index(fields=['nit_normalizado', 'codigo_material']),
        ]
        verbose_name = 'Imagen de Material'
        verbose_name_plural = 'Imágenes de Materiales'
    
    def save(self, *args, **kwargs):
        """Redimensiona la imagen al guardar si existe, preservando transparencia PNG"""
        import os
        # Eliminar imagen anterior si existe y se está reemplazando
        if self.pk:  # Si el objeto ya existe en la BD
            try:
                old_instance = MaterialImagen.objects.get(pk=self.pk)
                if old_instance.imagen and old_instance.imagen != self.imagen:
                    # Si hay una imagen anterior diferente, eliminarla
                    if os.path.exists(old_instance.imagen.path):
                        os.remove(old_instance.imagen.path)
            except MaterialImagen.DoesNotExist:
                pass
        
        if self.imagen:
            from PIL import Image
            from django.core.files.uploadedfile import InMemoryUploadedFile
            import io
            from django.core.files.base import ContentFile
            
            # Abrir imagen
            img = Image.open(self.imagen)
            original_format = img.format
            has_transparency = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
            
            # Si tiene transparencia, mantenerla; si no, convertir a RGB
            if has_transparency:
                # Mantener transparencia: convertir P a RGBA si es necesario
                if img.mode == 'P':
                    img = img.convert('RGBA')
                # No convertir a RGB, mantener RGBA o LA
            else:
                # Sin transparencia: convertir a RGB para optimizar
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
            
            # Tamaño para productos: 400x400px (cuadrado, mantener aspect ratio)
            max_size = 400
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Guardar en memoria
            thumb_io = io.BytesIO()
            
            # Si tiene transparencia, guardar como PNG; si no, como JPEG
            if has_transparency:
                img.save(thumb_io, format='PNG', optimize=True)
            else:
                img.save(thumb_io, format='JPEG', quality=85, optimize=True)
            
            thumb_io.seek(0)
            
            # Reemplazar el archivo original
            self.imagen.save(
                os.path.basename(self.imagen.name),
                ContentFile(thumb_io.read()),
                save=False
            )
            thumb_io.close()
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Elimina la imagen del sistema de archivos cuando se elimina el objeto"""
        import os
        if self.imagen:
            if os.path.exists(self.imagen.path):
                os.remove(self.imagen.path)
        if self.pdf:
            if os.path.exists(self.pdf.path):
                os.remove(self.pdf.path)
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"Material {self.codigo_material} - NIT: {self.nit_normalizado}"


class CajaAutopago(models.Model):
    """
    Configuración de cajas autopago para cada empresa.
    Relaciona empresa + usuario TNS + IP del datafono local.
    Permite que cada empresa tenga múltiples cajas, cada una con su propio datafono.
    """
    empresa_servidor = models.ForeignKey(
        EmpresaServidor, 
        on_delete=models.CASCADE, 
        related_name='cajas_autopago',
        help_text='Empresa a la que pertenece esta caja'
    )
    usuario_tns = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text='Usuario TNS que configuró esta caja (puede ser ADMIN o usuario específico)'
    )
    nombre = models.CharField(
        max_length=100,
        help_text='Nombre identificador de la caja (ej: "Caja Principal", "Caja 1", etc.)'
    )
    ip_datafono = models.CharField(
        max_length=45,  # IPv6 puede tener hasta 45 caracteres
        help_text='IP del servidor local donde está el datafono (vía WireGuard, ej: 10.8.0.5)'
    )
    puerto_datafono = models.IntegerField(
        default=8080,
        help_text='Puerto del servidor local del datafono'
    )
    activa = models.BooleanField(
        default=True,
        help_text='Si la caja está activa y disponible para procesar pagos'
    )
    modo_mock = models.BooleanField(
        default=False,
        help_text='Si está en True, simula respuestas sin usar el datafono físico'
    )
    probabilidad_exito = models.FloatField(
        default=0.8,
        help_text='Probabilidad de éxito en modo mock (0.0 a 1.0). 0.8 = 80%% de éxito'
    )
    modo_mock_dian = models.BooleanField(
        default=True,
        help_text='Si está en True, simula el envío a DIAN sin procesar realmente (espera 4 segundos y retorna exitoso)'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    usuario_creador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cajas_autopago_creadas',
        help_text='Usuario de Django que creó esta configuración'
    )
    
    class Meta:
        db_table = 'caja_autopago'
        verbose_name = 'Caja Autopago'
        verbose_name_plural = 'Cajas Autopago'
        indexes = [
            models.Index(fields=['empresa_servidor', 'activa']),
            models.Index(fields=['ip_datafono', 'puerto_datafono']),
        ]
        # Permitir múltiples cajas por empresa, pero nombres únicos por empresa
        unique_together = [['empresa_servidor', 'nombre']]
    
    def __str__(self):
        return f"{self.nombre} - {self.empresa_servidor.nombre} ({self.ip_datafono}:{self.puerto_datafono})"


class NotaRapida(models.Model):
    """
    Modelo para opciones rápidas de notas que se pueden asociar a categorías de productos.
    Ejemplo: "SIN CEBOLLA", "SIN SALSA DE TOMATE", "AL CLIMA", etc.
    """
    texto = models.CharField(max_length=100, help_text="Texto de la nota rápida (ej: SIN CEBOLLA)")
    categorias = models.JSONField(
        default=list,
        help_text="Lista de códigos de categorías (GM_CODIGO) a las que se asocia esta nota. Vacío = todas las categorías"
    )
    activo = models.BooleanField(default=True)
    orden = models.IntegerField(default=0, help_text="Orden de visualización")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notas_rapidas'
        ordering = ['orden', 'texto']
        verbose_name = 'Nota Rápida'
        verbose_name_plural = 'Notas Rápidas'
    
    def __str__(self):
        return self.texto

class ConfiguracionSistema(models.Model):
    clave = models.CharField(max_length=100, unique=True)
    valor = models.TextField()
    descripcion = models.TextField(null=True, blank=True)
    tipo = models.CharField(max_length=50, default='TEXTO')
    
    class Meta:
        db_table = 'configuracion_sistema'
        
        
    def __str__(self):
        return f"{self.clave} ({self.tipo})"


class VpnConfig(models.Model):
    """
    Configuración de túnel VPN WireGuard.
    Almacena la información de cada cliente/PC que se conecta vía VPN.
    """
    nombre = models.CharField(max_length=255, help_text="Nombre descriptivo del cliente/PC")
    ip_address = models.CharField(max_length=50, null=True, blank=True, help_text="IP asignada en la red VPN (ej: 10.8.0.5)")
    public_key = models.TextField(null=True, blank=True, help_text="Clave pública WireGuard del cliente")
    private_key = EncryptedTextField(max_length=500, null=True, blank=True, help_text="Clave privada WireGuard del cliente (encriptada)")
    config_file_path = models.CharField(max_length=500, null=True, blank=True, help_text="Ruta del archivo .conf generado")
    activo = models.BooleanField(default=True, help_text="Si el túnel está activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    notas = models.TextField(null=True, blank=True, help_text="Notas adicionales sobre esta configuración")
    
    class Meta:
        db_table = 'vpn_configs'
        verbose_name = 'Configuración VPN'
        verbose_name_plural = 'Configuraciones VPN'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.nombre} ({self.ip_address or 'Sin IP'})"
        
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

# ========== ENTIDADES Y CONTRASEÑAS (HOMOLOGACIÓN BCE) ==========

class Entidad(models.Model):
    """
    Entidades externas (bancos, plataformas, servicios, etc.)
    Homólogo de Entities en BCE
    """
    nombre = models.CharField(
        max_length=100,
        unique=True,
        help_text='Nombre de la entidad'
    )
    sigla = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Sigla o abreviatura de la entidad'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'entidades'
        verbose_name = 'Entidad'
        verbose_name_plural = 'Entidades'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class ContrasenaEntidad(models.Model):
    """
    Contraseñas y credenciales de entidades asociadas a empresas.
    Homólogo de PasswordsEntities en BCE.
    Se asocia a empresas por NIT normalizado.
    """
    empresa_servidor = models.ForeignKey(
        'EmpresaServidor',
        on_delete=models.CASCADE,
        related_name='contrasenas_entidades',
        null=True,
        blank=True,
        help_text='Empresa asociada (opcional, puede estar solo por NIT)'
    )
    nit_normalizado = models.CharField(
        max_length=20,
        db_index=True,
        help_text='NIT normalizado de la empresa (sin puntos ni guiones)'
    )
    entidad = models.ForeignKey(
        Entidad,
        on_delete=models.CASCADE,
        related_name='contrasenas',
        help_text='Entidad a la que pertenece esta contraseña'
    )
    descripcion = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Descripción o notas sobre esta contraseña'
    )
    usuario = models.CharField(
        max_length=100,
        help_text='Usuario o identificador de acceso'
    )
    contrasena = models.CharField(
        max_length=255,
        help_text='Contraseña (debería estar encriptada en producción)'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'contrasenas_entidades'
        verbose_name = 'Contraseña de Entidad'
        verbose_name_plural = 'Contraseñas de Entidades'
        indexes = [
            models.Index(fields=['nit_normalizado']),
            models.Index(fields=['entidad', 'nit_normalizado']),
        ]
        ordering = ['entidad__nombre', 'usuario']
    
    def __str__(self):
        return f"{self.entidad.nombre} - {self.usuario} (NIT: {self.nit_normalizado})"


class ConfiguracionS3(models.Model):
    """
    Configuración de credenciales y acceso a S3 para backups.
    Se puede tener múltiples configuraciones (por ejemplo, para diferentes buckets o regiones).
    """
    nombre = models.CharField(
        max_length=100,
        unique=True,
        help_text='Nombre descriptivo de la configuración (ej: "Backups Principal")'
    )
    bucket_name = models.CharField(
        max_length=255,
        help_text='Nombre del bucket S3'
    )
    region = models.CharField(
        max_length=50,
        default='us-east-1',
        help_text='Región de AWS S3 (ej: us-east-1, us-west-2)'
    )
    access_key_id = models.CharField(
        max_length=255,
        help_text='Access Key ID de AWS'
    )
    secret_access_key = models.CharField(
        max_length=255,
        help_text='Secret Access Key de AWS (encriptado)'
    )
    endpoint_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='URL del endpoint S3 (opcional, para S3-compatible como MinIO)'
    )
    activo = models.BooleanField(
        default=True,
        help_text='Indica si esta configuración está activa'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'configuracion_s3'
        verbose_name = 'Configuración S3'
        verbose_name_plural = 'Configuraciones S3'
        ordering = ['-activo', 'nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.bucket_name})"


class BackupS3(models.Model):
    """
    Registro de backups realizados a S3.
    """
    empresa_servidor = models.ForeignKey(
        EmpresaServidor,
        on_delete=models.CASCADE,
        related_name='backups_s3',
        help_text='Empresa a la que pertenece este backup'
    )
    configuracion_s3 = models.ForeignKey(
        ConfiguracionS3,
        on_delete=models.SET_NULL,
        null=True,
        help_text='Configuración S3 utilizada para este backup'
    )
    ruta_s3 = models.CharField(
        max_length=500,
        help_text='Ruta completa del archivo en S3 (ej: 9008697500/2024/backups/backup_2024-12-02_01-00.fbk)'
    )
    nombre_archivo = models.CharField(
        max_length=255,
        help_text='Nombre del archivo de backup'
    )
    tamano_bytes = models.BigIntegerField(
        help_text='Tamaño del archivo en bytes'
    )
    fecha_backup = models.DateTimeField(
        help_text='Fecha y hora en que se realizó el backup'
    )
    anio_fiscal = models.IntegerField(
        help_text='Año fiscal del backup'
    )
    estado = models.CharField(
        max_length=20,
        choices=[
            ('completado', 'Completado'),
            ('fallido', 'Fallido'),
            ('en_proceso', 'En Proceso'),
        ],
        default='completado'
    )
    mensaje_error = models.TextField(
        null=True,
        blank=True,
        help_text='Mensaje de error si el backup falló'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'backups_s3'
        verbose_name = 'Backup S3'
        verbose_name_plural = 'Backups S3'
        indexes = [
            models.Index(fields=['empresa_servidor', 'anio_fiscal']),
            models.Index(fields=['fecha_backup']),
            models.Index(fields=['estado']),
        ]
        ordering = ['-fecha_backup']
    
    def __str__(self):
        return f"{self.empresa_servidor.nombre} - {self.nombre_archivo} ({self.fecha_backup})"
    
    @property
    def tamano_mb(self):
        """Retorna el tamaño en MB"""
        return round(self.tamano_bytes / (1024 * 1024), 2)
    
    @property
    def tamano_gb(self):
        """Retorna el tamaño en GB"""
        return round(self.tamano_bytes / (1024 * 1024 * 1024), 2)


class DescargaTemporalBackup(models.Model):
    """
    Links temporales y seguros para descargar backups convertidos a GDB.
    Los links expiran después de 1 día y son únicos por token.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('procesando', 'Procesando'),
        ('listo', 'Listo'),
        ('expirado', 'Expirado'),
        ('descargado', 'Descargado'),
    ]
    
    backup = models.ForeignKey(
        BackupS3,
        on_delete=models.CASCADE,
        related_name='descargas_temporales',
        help_text='Backup que se está convirtiendo a GDB'
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text='Token único y seguro para la descarga'
    )
    email = models.EmailField(
        help_text='Email del destinatario al que se envió el link'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        help_text='Estado del proceso de conversión'
    )
    ruta_gdb_temporal = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='Ruta temporal del archivo GDB generado'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField(
        help_text='Fecha en que expira el link (1 día después de la creación)'
    )
    fecha_descarga = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha en que se descargó el archivo'
    )
    intentos_descarga = models.IntegerField(
        default=0,
        help_text='Número de veces que se ha intentado descargar'
    )
    
    class Meta:
        db_table = 'descargas_temporales_backup'
        verbose_name = 'Descarga Temporal de Backup'
        verbose_name_plural = 'Descargas Temporales de Backup'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['fecha_expiracion']),
            models.Index(fields=['estado']),
        ]
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"Descarga {self.token[:8]}... - {self.email} - {self.estado}"
    
    def esta_expirado(self):
        """Verifica si el link ha expirado"""
        return timezone.now() > self.fecha_expiracion
    
    def puede_descargar(self):
        """Verifica si el link puede ser descargado"""
        return self.estado == 'listo' and not self.esta_expirado()


# Extender el modelo User
User.add_to_class('puede_gestionar_api_keys', user_puede_gestionar_api_keys)
User.add_to_class('has_empresa_permission', user_has_empresa_permission)
User.add_to_class('empresas_permitidas', user_empresas_permitidas)
