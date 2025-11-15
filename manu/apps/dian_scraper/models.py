from django.db import models

class ScrapingSession(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('running', 'En ejecución'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ]
    
    url = models.URLField(max_length=500)
    tipo = models.CharField(max_length=20, default='Sent')  # Sent/Received
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    documents_downloaded = models.IntegerField(default=0)
    excel_file = models.FileField(upload_to='dian_exports/', null=True, blank=True)
    json_file = models.FileField(upload_to='dian_exports/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

class DocumentProcessed(models.Model):
    session = models.ForeignKey(ScrapingSession, on_delete=models.CASCADE, related_name='documents')
    document_number = models.CharField(max_length=100)
    cufe = models.CharField(max_length=200, blank=True)
    issue_date = models.DateField(null=True)
    supplier_nit = models.CharField(max_length=20, blank=True)
    supplier_name = models.TextField(blank=True)
    customer_nit = models.CharField(max_length=20, blank=True)
    customer_name = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    raw_data = models.JSONField(default=dict)  # Todos los datos del XML

    class Meta:
        ordering = ['-issue_date']