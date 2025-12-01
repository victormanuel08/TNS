from django.contrib import admin
from .models import FudoScrapingSession, FudoDocumentProcessed

@admin.register(FudoScrapingSession)
class FudoScrapingSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'nit', 'empresa_servidor', 'fecha_desde', 'fecha_hasta', 'status', 'facturas_procesadas', 'total_facturas', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['nit', 'empresa_servidor__nombre']
    readonly_fields = ['created_at', 'completed_at', 'started_at']

@admin.register(FudoDocumentProcessed)
class FudoDocumentProcessedAdmin(admin.ModelAdmin):
    list_display = ['fudo_original_id', 'session', 'numero_factura', 'fecha', 'estado_insercion', 'total_amount']
    list_filter = ['estado_insercion', 'fecha']
    search_fields = ['fudo_original_id', 'numero_factura', 'nit_cliente']
    readonly_fields = ['created_at']

