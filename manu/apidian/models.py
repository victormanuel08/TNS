"""
Modelos para facilitar el trabajo con APIDIAN
Estos modelos NO se guardan en la BD de MANU, solo facilitan la serialización
"""
from django.db import models


class ApidianEventRequest(models.Model):
    """
    Modelo para representar una solicitud de envío de evento a APIDIAN
    No se guarda en BD, solo para serialización
    """
    event_id = models.IntegerField(help_text="ID del evento (1=enviar, etc.)")
    allow_cash_documents = models.BooleanField(default=False, help_text="Permitir documentos de efectivo")
    sendmail = models.BooleanField(default=False, help_text="Enviar por email")
    base64_attacheddocument_name = models.CharField(max_length=255, help_text="Nombre del documento XML")
    base64_attacheddocument = models.TextField(help_text="Contenido del XML en base64")
    type_rejection_id = models.IntegerField(null=True, blank=True, help_text="ID del tipo de rechazo")
    resend_consecutive = models.BooleanField(default=False, help_text="Reenviar consecutivo")
    
    class Meta:
        managed = False  # No crear tabla en BD
        verbose_name = "Solicitud de Evento APIDIAN"
        verbose_name_plural = "Solicitudes de Eventos APIDIAN"
