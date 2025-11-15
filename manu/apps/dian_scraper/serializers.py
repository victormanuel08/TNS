from rest_framework import serializers
from .models import ScrapingSession, DocumentProcessed

class ScrapingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapingSession
        fields = '__all__'
        read_only_fields = ('status', 'documents_downloaded', 'excel_file', 'json_file', 
                          'created_at', 'completed_at', 'error_message')

class DocumentProcessedSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentProcessed
        fields = '__all__'