# sistema_analitico/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.models import User
from .models import (
    Servidor,
    EmpresaServidor,
    MovimientoInventario,
    UsuarioEmpresa,
    APIKeyCliente,
    UserTenantProfile,
    NotaRapida,
    RUT,
    EstablecimientoRUT,
    ActividadEconomica,
    ResponsabilidadTributaria,
)

# ========== ADMIN CONFIGURACIÓN GLOBAL ==========
admin.site.site_header = "🚀 Sistema Analítico - Panel de Control"
admin.site.site_title = "Sistema Analítico"
admin.site.index_title = "Gestión del Sistema"

# ========== SERVICIOR ADMIN OPTIMIZADO ==========
@admin.register(Servidor)
class ServidorAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo_servidor', 'host', 'puerto', 'estado_activo', 'fecha_creacion']
    list_filter = ['tipo_servidor', 'activo', 'fecha_creacion']
    search_fields = ['nombre', 'host', 'tipo_servidor']
    list_editable = ['puerto']
    list_per_page = 20
    ordering = ['nombre']  # ✅ ORDENAR por nombre
    
    def estado_activo(self, obj):
        color = 'green' if obj.activo else 'red'
        texto = 'ACTIVO' if obj.activo else 'INACTIVO'
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, texto)
    estado_activo.short_description = 'Estado'

# ========== EMPRESA SERVIDOR ADMIN OPTIMIZADO ==========
@admin.register(EmpresaServidor)
class EmpresaServidorAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'nit', 'anio_fiscal', 'servidor_link', 'estado_color', 'ultima_extraccion', 'total_movimientos']
    list_filter = ['estado', 'anio_fiscal', 'servidor', 'fecha_registro']
    search_fields = ['nombre', 'nit', 'codigo']
    list_select_related = ['servidor']
    readonly_fields = ['ultima_extraccion', 'fecha_registro']
    list_per_page = 25
    ordering = ['nombre', '-anio_fiscal']  # ✅ ORDENAR: nombre ASC, año DESC
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "servidor":
            kwargs["queryset"] = Servidor.objects.all().order_by('nombre')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def servidor_link(self, obj):
        return format_html('<a href="/admin/sistema_analitico/servidor/{}/change/">{}</a>', 
                          obj.servidor.id, obj.servidor.nombre)
    servidor_link.short_description = 'Servidor'
    
    def estado_color(self, obj):
        colors = {
            'ACTIVO': 'green',
            'INACTIVO': 'red', 
            'MANTENIMIENTO': 'orange'
        }
        color = colors.get(obj.estado, 'gray')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.estado)
    estado_color.short_description = 'Estado'
    
    def total_movimientos(self, obj):
        count = MovimientoInventario.objects.filter(empresa_servidor=obj).count()
        return format_html('<strong>{}</strong>', count)
    total_movimientos.short_description = 'Movimientos'

# ========== MOVIMIENTOS INVENTARIO ADMIN OPTIMIZADO ==========
@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ['articulo_codigo', 'articulo_nombre_short', 'tipo_documento_badge', 'fecha', 'cantidad', 'precio_unitario', 'empresa_link']
    list_filter = ['tipo_documento', 'fecha', 'empresa_servidor', 'es_implante', 'es_instrumental']
    search_fields = ['articulo_nombre', 'articulo_codigo', 'paciente', 'pagador', 'clinica']
    readonly_fields = ['fecha_extraccion']
    list_per_page = 50
    date_hierarchy = 'fecha'
    ordering = ['-fecha', 'articulo_codigo']  # ✅ ORDENAR: fecha DESC, código ASC
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "empresa_servidor":
            # ✅ ORDEN MEJORADO: nombre ASC, año_fiscal DESC
            kwargs["queryset"] = EmpresaServidor.objects.all().order_by('nombre', '-anio_fiscal')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def articulo_nombre_short(self, obj):
        return obj.articulo_nombre[:50] + '...' if len(obj.articulo_nombre) > 50 else obj.articulo_nombre
    articulo_nombre_short.short_description = 'Artículo'
    
    def tipo_documento_badge(self, obj):
        colors = {
            'FACTURA_VENTA': 'green',
            'FACTURA_COMPRA': 'blue',
            'REMISION_ENTRADA': 'orange',
            'DEVOLUCION_VENTA': 'red'
        }
        color = colors.get(obj.tipo_documento, 'gray')
        return format_html('<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em;">{}</span>', 
                          color, obj.get_tipo_documento_display())
    tipo_documento_badge.short_description = 'Tipo Documento'
    
    def empresa_link(self, obj):
        return format_html('<a href="/admin/sistema_analitico/empresaservidor/{}/change/">{}</a>', 
                          obj.empresa_servidor.id, f"{obj.empresa_servidor.nombre} ({obj.empresa_servidor.anio_fiscal})")
    empresa_link.short_description = 'Empresa'

# ========== USUARIO EMPRESA ADMIN OPTIMIZADO ==========
@admin.register(UsuarioEmpresa)
class UsuarioEmpresaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'empresa_link', 'puede_ver', 'puede_editar', 'preferred_template', 'permisos_badge', 'fecha_asignacion']
    list_filter = ['puede_ver', 'puede_editar', 'preferred_template', 'fecha_asignacion']
    search_fields = ['usuario__username', 'usuario__email', 'empresa_servidor__nombre', 'empresa_servidor__nit']
    list_editable = ['puede_ver', 'puede_editar', 'preferred_template']
    list_per_page = 50
    ordering = ['usuario__username', 'empresa_servidor__nombre']
    fieldsets = (
        ('Información Principal', {
            'fields': ('usuario', 'empresa_servidor')
        }),
        ('Permisos', {
            'fields': ('puede_ver', 'puede_editar', 'preferred_template')
        }),
        ('Información Adicional', {
            'fields': ('fecha_asignacion',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['fecha_asignacion']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "usuario":
            kwargs["queryset"] = User.objects.all().order_by('username')
        elif db_field.name == "empresa_servidor":
            kwargs["queryset"] = EmpresaServidor.objects.all().order_by('nombre', '-anio_fiscal')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def empresa_link(self, obj):
        return format_html(
            '<a href="/admin/sistema_analitico/empresaservidor/{}/change/">{}</a><br><small style="color: #666;">NIT: {} | Servidor: {}</small>', 
            obj.empresa_servidor.id, 
            f"{obj.empresa_servidor.nombre} ({obj.empresa_servidor.anio_fiscal})",
            obj.empresa_servidor.nit or 'N/A',
            obj.empresa_servidor.servidor.nombre
        )
    empresa_link.short_description = 'Empresa'
    
    def permisos_badge(self, obj):
        if obj.puede_editar:
            color = 'green'
            texto = 'EDITAR'
        elif obj.puede_ver:
            color = 'blue' 
            texto = 'VER'
        else:
            color = 'red'
            texto = 'SIN ACCESO'
        return format_html('<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em;">{}</span>', color, texto)
    permisos_badge.short_description = 'Permisos'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario', 'empresa_servidor', 'empresa_servidor__servidor')

# ========== API KEYS ADMIN OPTIMIZADO ==========
@admin.register(APIKeyCliente)
class APIKeyClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre_cliente', 'nit', 'estado_badge', 'contador_peticiones', 'fecha_creacion', 'fecha_caducidad', 'dias_restantes']
    list_filter = ['activa', 'fecha_creacion', 'fecha_caducidad']
    search_fields = ['nombre_cliente', 'nit']
    readonly_fields = ['api_key', 'contador_peticiones', 'fecha_ultima_peticion', 'fecha_creacion', 'fecha_actualizacion', 'empresas_asociadas_list']
    list_per_page = 20
    ordering = ['nombre_cliente', 'fecha_caducidad']  # ✅ ORDENAR: nombre cliente ASC, fecha caducidad ASC
    actions = ['activar_keys', 'desactivar_keys', 'renovar_keys_30d', 'renovar_keys_90d', 'renovar_keys_365d']
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "empresas_asociadas":
            # ✅ ORDENAR empresas en el select ManyToMany
            kwargs["queryset"] = EmpresaServidor.objects.all().order_by('nombre', '-anio_fiscal')
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    
    def estado_badge(self, obj):
        if obj.esta_expirada():
            color = 'red'
            texto = 'EXPIRADA'
        elif obj.activa:
            color = 'green'
            texto = 'ACTIVA'
        else:
            color = 'orange'
            texto = 'INACTIVA'
        return format_html('<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em;">{}</span>', color, texto)
    estado_badge.short_description = 'Estado'
    
    def dias_restantes(self, obj):
        from django.utils import timezone
        dias = (obj.fecha_caducidad - timezone.now()).days
        color = 'green' if dias > 30 else 'orange' if dias > 0 else 'red'
        return format_html('<span style="color: {}; font-weight: bold;">{} días</span>', color, dias)
    dias_restantes.short_description = 'Días Restantes'
    
    def empresas_asociadas_list(self, obj):
        empresas = obj.empresas_asociadas.all().order_by('nombre', '-anio_fiscal')  # ✅ ORDENAR en el display
        if empresas:
            lista = ''.join([f'<li>{emp.nombre} ({emp.anio_fiscal})</li>' for emp in empresas])
            return format_html('<ul>{}</ul>'.format(lista))
        return "No hay empresas asociadas"
    empresas_asociadas_list.short_description = 'Empresas Asociadas'
    
    # ========== ACCIONES PERSONALIZADAS ==========
    def activar_keys(self, request, queryset):
        updated = queryset.update(activa=True)
        self.message_user(request, f'{updated} API Keys activadas correctamente.')
    activar_keys.short_description = "🔓 Activar API Keys seleccionadas"
    
    def desactivar_keys(self, request, queryset):
        updated = queryset.update(activa=False)
        self.message_user(request, f'{updated} API Keys desactivadas correctamente.')
    desactivar_keys.short_description = "🔒 Desactivar API Keys seleccionadas"
    
    def renovar_keys_30d(self, request, queryset):
        for key in queryset:
            key.renovar(30)
        self.message_user(request, f'{queryset.count()} API Keys renovadas por 30 días.')
    renovar_keys_30d.short_description = "🔄 Renovar por 30 días"
    
    def renovar_keys_90d(self, request, queryset):
        for key in queryset:
            key.renovar(90)
        self.message_user(request, f'{queryset.count()} API Keys renovadas por 90 días.')
    renovar_keys_90d.short_description = "🔄 Renovar por 90 días"
    
    def renovar_keys_365d(self, request, queryset):
        for key in queryset:
            key.renovar(365)
        self.message_user(request, f'{queryset.count()} API Keys renovadas por 365 días.')
    renovar_keys_365d.short_description = "🔄 Renovar por 365 días"
    
    # ========== CONFIGURACIÓN DE FORMULARIO ==========
    fieldsets = (
        ('Información Básica', {
            'fields': ('nit', 'nombre_cliente', 'activa')
        }),
        ('API Key (Solo visible al crear)', {
            'fields': ('api_key',)
        }),
        ('Estadísticas de Uso', {
            'fields': ('contador_peticiones', 'fecha_ultima_peticion')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion', 'fecha_caducidad')
        }),
        ('Empresas Asociadas', {
            'fields': ('empresas_asociadas_list', 'empresas_asociadas')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editando objeto existente
            return list(self.readonly_fields) + ['api_key']
        else:  # Creando nuevo objeto
            return [f for f in self.readonly_fields if f != 'api_key']
    
    def get_exclude(self, request, obj=None):
        return None


# ========== USER TENANT PROFILE ADMIN OPTIMIZADO ==========
@admin.register(UserTenantProfile)
class UserTenantProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'subdomain', 'preferred_template', 'user_info']
    list_filter = ['preferred_template']
    search_fields = ['user__username', 'user__email', 'subdomain']
    list_editable = ['preferred_template']
    list_per_page = 50
    ordering = ['user__username']
    fieldsets = (
        ('Información Principal', {
            'fields': ('user', 'subdomain')
        }),
        ('Preferencias', {
            'fields': ('preferred_template',)
        }),
    )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.all().order_by('username')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def user_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small style="color: #666;">Email: {}</small>',
            obj.user.username,
            obj.user.email or 'N/A'
        )
    user_info.short_description = 'Información Usuario'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

# ========== RUT ADMIN ==========
@admin.register(RUT)
class RUTAdmin(admin.ModelAdmin):
    list_display = ['nit', 'dv', 'razon_social', 'nombre_comercial', 'ciudad_nombre', 'departamento_nombre', 'fecha_actualizacion']
    list_filter = ['tipo_contribuyente', 'departamento_nombre', 'responsable_iva', 'facturador_electronico', 'fecha_actualizacion']
    search_fields = ['nit', 'nit_normalizado', 'razon_social', 'nombre_comercial', 'ciudad_nombre']
    list_per_page = 50
    ordering = ['-fecha_actualizacion']
    readonly_fields = ['nit_normalizado', 'fecha_creacion', 'fecha_actualizacion', 'fecha_ultima_consulta_dian']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('nit', 'dv', 'nit_normalizado', 'numero_formulario', 'tipo_contribuyente', 'razon_social', 'nombre_comercial', 'sigla')
        }),
        ('Ubicación', {
            'fields': ('pais', 'departamento_codigo', 'departamento_nombre', 'ciudad_codigo', 'ciudad_nombre', 
                      'direccion_principal', 'codigo_postal', 'telefono_1', 'telefono_2', 'email', 
                      'direccion_seccional', 'buzon_electronico')
        }),
        ('Actividades Económicas', {
            'fields': ('actividad_principal_ciiu', 'actividad_principal_fecha_inicio',
                      'actividad_secundaria_ciiu', 'actividad_secundaria_fecha_inicio',
                      'otras_actividades_ciiu', 'numero_establecimientos')
        }),
        ('Responsabilidades', {
            'fields': ('responsabilidades_codigos', 'responsabilidades_descripcion',
                      'responsable_iva', 'autorretenedor', 'obligado_contabilidad',
                      'regimen_simple', 'facturador_electronico', 'informante_exogena',
                      'informante_beneficiarios_finales')
        }),
        ('Constitución y Registro', {
            'fields': ('constitucion_clase', 'constitucion_numero', 'constitucion_fecha',
                      'constitucion_notaria', 'registro_entidad', 'registro_fecha',
                      'matricula_mercantil', 'registro_departamento', 'registro_ciudad',
                      'vigencia_desde', 'vigencia_hasta')
        }),
        ('Capital', {
            'fields': ('capital_nacional_porcentaje', 'capital_nacional_publico_porcentaje',
                      'capital_nacional_privado_porcentaje', 'capital_extranjero_porcentaje',
                      'capital_extranjero_publico_porcentaje', 'capital_extranjero_privado_porcentaje')
        }),
        ('Representante Legal', {
            'fields': ('representante_legal_representacion', 'representante_legal_fecha_inicio',
                      'representante_legal_tipo_doc', 'representante_legal_numero_doc',
                      'representante_legal_dv', 'representante_legal_tarjeta_profesional',
                      'representante_legal_primer_apellido', 'representante_legal_segundo_apellido',
                      'representante_legal_primer_nombre', 'representante_legal_otros_nombres',
                      'representante_legal_nit', 'representante_legal_razon_social')
        }),
        ('Vinculación Económica', {
            'fields': ('vinculacion_economica', 'grupo_economico_nombre',
                      'matriz_nit', 'matriz_dv', 'matriz_razon_social')
        }),
        ('Archivo y Metadatos', {
            'fields': ('archivo_pdf', 'informacion_adicional')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion', 'fecha_ultima_consulta_dian'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('establecimientos')

@admin.register(EstablecimientoRUT)
class EstablecimientoRUTAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ciudad_nombre', 'departamento_nombre', 'actividad_economica_ciiu', 'rut']
    list_filter = ['departamento_nombre', 'ciudad_nombre']
    search_fields = ['nombre', 'direccion', 'ciudad_nombre', 'departamento_nombre']
    list_per_page = 50
    ordering = ['nombre']


# ========== ACTIVIDADES ECONÓMICAS ADMIN ==========
@admin.register(ActividadEconomica)
class ActividadEconomicaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descripcion', 'titulo', 'division', 'grupo', 'fecha_ultima_consulta_api', 'fecha_actualizacion']
    list_filter = ['division', 'grupo', 'fecha_ultima_consulta_api']
    search_fields = ['codigo', 'descripcion', 'titulo']
    list_per_page = 50
    ordering = ['codigo']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion', 'fecha_ultima_consulta_api']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'descripcion', 'titulo')
        }),
        ('Clasificación', {
            'fields': ('division', 'grupo')
        }),
        ('Detalles', {
            'fields': ('incluye', 'excluye'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion', 'fecha_ultima_consulta_api'),
            'classes': ('collapse',)
        }),
    )


# ========== RESPONSABILIDADES TRIBUTARIAS ADMIN ==========
@admin.register(ResponsabilidadTributaria)
class ResponsabilidadTributariaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descripcion', 'fecha_creacion', 'fecha_actualizacion']
    list_filter = ['fecha_creacion']
    search_fields = ['codigo', 'descripcion']
    list_per_page = 50
    ordering = ['codigo']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']

# ========== NOTAS RÁPIDAS ADMIN ==========
@admin.register(NotaRapida)
class NotaRapidaAdmin(admin.ModelAdmin):
    list_display = ['texto', 'categorias_display', 'activo', 'orden', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion']
    search_fields = ['texto']
    list_editable = ['activo', 'orden']
    list_per_page = 30
    ordering = ['orden', 'texto']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('texto', 'activo', 'orden')
        }),
        ('Asociación a Categorías', {
            'description': 'Deja vacío para que esté disponible en todas las categorías. O selecciona categorías específicas (GM_CODIGO)',
            'fields': ('categorias',)
        }),
    )
    
    def categorias_display(self, obj):
        if not obj.categorias or len(obj.categorias) == 0:
            return format_html('<span style="color: green; font-weight: bold;">TODAS LAS CATEGORÍAS</span>')
        return ', '.join(obj.categorias) if isinstance(obj.categorias, list) else str(obj.categorias)
    categorias_display.short_description = 'Categorías'

# ========== FILTRO PERSONALIZADO PARA FECHAS ==========
class RangoFechasFilter(admin.SimpleListFilter):
    title = 'rango de fechas'
    parameter_name = 'rango_fechas'
    
    def lookups(self, request, model_admin):
        return (
            ('hoy', 'Hoy'),
            ('ultima_semana', 'Última semana'),
            ('ultimo_mes', 'Último mes'),
        )
    
    def queryset(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        
        if self.value() == 'hoy':
            return queryset.filter(fecha__date=timezone.now().date())
        if self.value() == 'ultima_semana':
            return queryset.filter(fecha__gte=timezone.now() - timedelta(days=7))
        if self.value() == 'ultimo_mes':
            return queryset.filter(fecha__gte=timezone.now() - timedelta(days=30))
        return queryset
