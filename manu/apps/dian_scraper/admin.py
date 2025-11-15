from django.contrib import admin
from .models import ScrapingSession, DocumentProcessed

# ELIMINA la clase DianScraperConfig de aquí - eso va en apps.py
# Solo deja los registros del admin

@admin.register(ScrapingSession)
class ScrapingSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'tipo', 'fecha_desde', 'fecha_hasta', 'status', 'documents_downloaded', 'created_at']
    list_filter = ['status', 'tipo', 'created_at']
    readonly_fields = ['created_at', 'completed_at', 'documents_downloaded']
    actions = ['run_scraping']

    def run_scraping(self, request, queryset):
        for session in queryset:
            from .tasks import run_dian_scraping_task
            run_dian_scraping_task.delay(session.id)
        self.message_user(request, f"Scraping iniciado para {queryset.count()} sesiones")

@admin.register(DocumentProcessed)
class DocumentProcessedAdmin(admin.ModelAdmin):
    list_display = ['document_number', 'cufe', 'issue_date', 'supplier_nit', 'total_amount', 'session']
    list_filter = ['session', 'issue_date']
    search_fields = ['document_number', 'cufe', 'supplier_nit']