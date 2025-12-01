from django.db import models
from apps.sistema_analitico.models import EmpresaServidor

class FudoScrapingSession(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('running', 'En ejecución'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ]
    
    empresa_servidor = models.ForeignKey(
        EmpresaServidor, 
        on_delete=models.CASCADE,
        related_name='fudo_sessions'
    )
    nit = models.CharField(max_length=20)
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField()
    usuario_fudo = models.CharField(max_length=255)  # Usuario para autenticación FUDO
    password_fudo = models.CharField(max_length=255)  # Password para autenticación FUDO
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    facturas_procesadas = models.IntegerField(default=0)
    facturas_exitosas = models.IntegerField(default=0)
    facturas_fallidas = models.IntegerField(default=0)
    total_facturas = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'fudo_scraping_sessions'

    def __str__(self):
        return f"FUDO Session {self.id} - {self.nit} ({self.status})"

class FudoDocumentProcessed(models.Model):
    session = models.ForeignKey(
        FudoScrapingSession, 
        on_delete=models.CASCADE, 
        related_name='documents'
    )
    fudo_original_id = models.CharField(max_length=100, db_index=True)
    numero_factura = models.CharField(max_length=100, blank=True)
    fecha = models.DateField(null=True)
    nit_cliente = models.CharField(max_length=20, blank=True, null=True)
    nombre_cliente = models.TextField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    estado_insercion = models.CharField(max_length=20, default='pending')  # pending, success, failed
    error_message = models.TextField(blank=True)
    raw_data = models.JSONField(default=dict)  # Todos los datos de la factura FUDO
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        db_table = 'fudo_documents_processed'
        indexes = [
            models.Index(fields=['fudo_original_id']),
            models.Index(fields=['session', 'estado_insercion']),
        ]

    def __str__(self):
        return f"FUDO Doc {self.fudo_original_id} - {self.estado_insercion}"

