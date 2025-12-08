from django.db import models
from django.utils import timezone
from datetime import timedelta
import secrets

class ScrapingSession(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('running', 'En ejecución'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ]
    
    url = models.URLField(max_length=500)
    tipo = models.CharField(max_length=20, default='Sent')  # Sent/Received
    nit = models.CharField(max_length=20, blank=True, default='')
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField()
    ejecutado_desde = models.DateField(null=True, blank=True)
    ejecutado_hasta = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    documents_downloaded = models.IntegerField(default=0)
    excel_file = models.FileField(upload_to='dian_exports/', null=True, blank=True)
    json_file = models.FileField(upload_to='dian_exports/', null=True, blank=True)
    zip_file = models.FileField(upload_to='dian_exports/', null=True, blank=True, help_text='ZIP permanente con todos los archivos de la sesión')
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
    supplier_nit = models.CharField(max_length=20, blank=True, null=True)
    supplier_name = models.TextField(blank=True, null=True)
    customer_nit = models.CharField(max_length=20, blank=True, null=True)
    customer_name = models.TextField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    raw_data = models.JSONField(default=dict)  # Todos los datos del XML

    class Meta:
        ordering = ['-issue_date']

class ScrapingRange(models.Model):
    nit = models.CharField(max_length=20)
    tipo = models.CharField(max_length=20, default='Sent')
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ['nit', 'tipo', 'start_date']
        verbose_name = 'Rango de scraping'
        verbose_name_plural = 'Rangos de scraping'


class DescargaTemporalDianZip(models.Model):
    """
    Links temporales y seguros para descargar ZIPs de scraping DIAN.
    Los links expiran después de 1 día y son únicos por token.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('procesando', 'Procesando'),
        ('listo', 'Listo'),
        ('expirado', 'Expirado'),
        ('descargado', 'Descargado'),
    ]
    
    session = models.ForeignKey(
        ScrapingSession,
        on_delete=models.CASCADE,
        related_name='descargas_temporales',
        help_text='Sesión de scraping que generó el ZIP'
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
        help_text='Estado del proceso de generación del ZIP'
    )
    ruta_zip_temporal = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='Ruta temporal del archivo ZIP generado'
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
        db_table = 'descargas_temporales_dian_zip'
        verbose_name = 'Descarga Temporal de ZIP DIAN'
        verbose_name_plural = 'Descargas Temporales de ZIP DIAN'
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
    
    @classmethod
    def crear_para_session(cls, session, email):
        """Crea un nuevo registro de descarga temporal"""
        token = secrets.token_urlsafe(48)
        return cls.objects.create(
            session=session,
            token=token,
            email=email,
            estado='pendiente',
            fecha_expiracion=timezone.now() + timedelta(days=1)
        )


class EventoApidianEnviado(models.Model):
    """
    Registra qué eventos se enviaron a qué CUFE (factura) a través de APIDIAN.
    """
    ESTADO_CHOICES = [
        ('exitoso', 'Exitoso'),
        ('fallido', 'Fallido'),
    ]
    
    session = models.ForeignKey(
        ScrapingSession,
        on_delete=models.CASCADE,
        related_name='eventos_enviados',
        help_text='Sesión de scraping asociada'
    )
    documento = models.ForeignKey(
        DocumentProcessed,
        on_delete=models.CASCADE,
        related_name='eventos_enviados',
        null=True,
        blank=True,
        help_text='Documento procesado asociado (opcional)'
    )
    cufe = models.CharField(
        max_length=200,
        db_index=True,
        help_text='CUFE de la factura a la que se envió el evento'
    )
    evento_id = models.IntegerField(
        help_text='ID del evento enviado (1-7)'
    )
    evento_nombre = models.CharField(
        max_length=255,
        help_text='Nombre del evento enviado'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        help_text='Estado del envío'
    )
    error = models.TextField(
        blank=True,
        null=True,
        help_text='Mensaje de error si falló'
    )
    respuesta_api = models.JSONField(
        null=True,
        blank=True,
        help_text='Respuesta de la API de APIDIAN si fue exitoso'
    )
    # Datos del emisor que envió el evento
    emisor_cedula = models.CharField(max_length=20, blank=True)
    emisor_primer_nombre = models.CharField(max_length=100, blank=True)
    emisor_segundo_nombre = models.CharField(max_length=100, blank=True)
    emisor_departamento = models.CharField(max_length=100, blank=True)
    emisor_cargo = models.CharField(max_length=100, blank=True)
    
    fecha_envio = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'eventos_apidian_enviados'
        verbose_name = 'Evento APIDIAN Enviado'
        verbose_name_plural = 'Eventos APIDIAN Enviados'
        indexes = [
            models.Index(fields=['session', 'cufe']),
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_envio']),
        ]
        ordering = ['-fecha_envio']
        # Un evento solo puede enviarse una vez por CUFE y evento_id en una sesión
        unique_together = [['session', 'cufe', 'evento_id']]
    
    def __str__(self):
        return f"Evento {self.evento_id} - CUFE {self.cufe[:20]}... - {self.estado}"
