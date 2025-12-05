"""
Serializers para APIDIAN
"""
from rest_framework import serializers


class SendEventSerializer(serializers.Serializer):
    """Serializer para enviar eventos a APIDIAN"""
    event_id = serializers.IntegerField(help_text="ID del evento (1=enviar, etc.)")
    allow_cash_documents = serializers.BooleanField(default=False, required=False)
    sendmail = serializers.BooleanField(default=False, required=False)
    base64_attacheddocument_name = serializers.CharField(max_length=255, help_text="Nombre del documento XML")
    base64_attacheddocument = serializers.CharField(help_text="Contenido del XML en base64")
    type_rejection_id = serializers.IntegerField(required=False, allow_null=True)
    resend_consecutive = serializers.BooleanField(default=False, required=False)
    
    def validate_event_id(self, value):
        """Validar que el event_id sea válido"""
        if value < 1:
            raise serializers.ValidationError("event_id debe ser mayor a 0")
        return value
    
    def validate_base64_attacheddocument(self, value):
        """Validar que el base64 sea válido"""
        import base64
        try:
            base64.b64decode(value)
            return value
        except Exception:
            raise serializers.ValidationError("base64_attacheddocument no es un base64 válido")


class SendEventFromFileSerializer(serializers.Serializer):
    """Serializer para enviar eventos desde un archivo XML"""
    event_id = serializers.IntegerField()
    xml_file_path = serializers.CharField(max_length=500, help_text="Ruta al archivo XML")
    allow_cash_documents = serializers.BooleanField(default=False, required=False)
    sendmail = serializers.BooleanField(default=False, required=False)
    type_rejection_id = serializers.IntegerField(required=False, allow_null=True)
    resend_consecutive = serializers.BooleanField(default=False, required=False)


class SendEventFromDocumentIdSerializer(serializers.Serializer):
    """Serializer para enviar eventos desde un ID de documento en APIDIAN"""
    event_id = serializers.IntegerField()
    document_id = serializers.IntegerField(help_text="ID del documento en la BD de APIDIAN")
    allow_cash_documents = serializers.BooleanField(default=False, required=False)
    sendmail = serializers.BooleanField(default=False, required=False)
    type_rejection_id = serializers.IntegerField(required=False, allow_null=True)
    resend_consecutive = serializers.BooleanField(default=False, required=False)

