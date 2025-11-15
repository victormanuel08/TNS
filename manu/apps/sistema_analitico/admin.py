# sistema_analitico/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.models import User
from .models import Servidor, EmpresaServidor, MovimientoInventario, UsuarioEmpresa, APIKeyCliente

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
    list_display = ['usuario', 'empresa_link', 'puede_ver', 'puede_editar', 'permisos_badge', 'fecha_asignacion']
    list_filter = ['puede_ver', 'puede_editar', 'fecha_asignacion']
    search_fields = ['usuario__username', 'empresa_servidor__nombre']
    list_editable = ['puede_ver', 'puede_editar']
    list_per_page = 30
    ordering = ['usuario__username', 'empresa_servidor__nombre']  # ✅ Ordenar lista principal
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "usuario":
            kwargs["queryset"] = User.objects.all().order_by('username')
        elif db_field.name == "empresa_servidor":
            # ✅ ORDEN CORREGIDO: nombre ASC, año_fiscal DESC
            kwargs["queryset"] = EmpresaServidor.objects.all().order_by('nombre', '-anio_fiscal')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def empresa_link(self, obj):
        return format_html('<a href="/admin/sistema_analitico/empresaservidor/{}/change/">{}</a>', 
                          obj.empresa_servidor.id, f"{obj.empresa_servidor.nombre} ({obj.empresa_servidor.anio_fiscal})")
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
            return self.readonly_fields + ('api_key',)
        else:  # Creando nuevo objeto
            return [f for f in self.readonly_fields if f != 'api_key']
    
    def get_exclude(self, request, obj=None):
        return None

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