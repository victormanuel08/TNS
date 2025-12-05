"""
Cliente para interactuar con la API de APIDIAN
"""
import requests
import base64
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class ApidianAPIClient:
    """Cliente para hacer requests a la API de APIDIAN"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'API_DIAN_ROUTE', 'http://45.149.204.184:81')
        self.token = getattr(settings, 'TOKEN_API_DIAN_BASIC', '')
        self.timeout = 30
    
    def _get_headers(self):
        """Obtiene los headers para las peticiones"""
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.token}' if self.token else ''
        }
    
    def send_event(self, event_id, attached_document_name, attached_document_base64, 
                   allow_cash_documents=False, sendmail=False, 
                   type_rejection_id=None, resend_consecutive=False):
        """
        Envía un evento a APIDIAN usando el endpoint /api/ubl2.1/send-event
        
        Args:
            event_id: ID del evento (1 = enviar, etc.)
            attached_document_name: Nombre del documento XML (ej: "ad09001495660102400018741.xml")
            attached_document_base64: Contenido del XML en base64
            allow_cash_documents: Permitir documentos de efectivo
            sendmail: Enviar por email
            type_rejection_id: ID del tipo de rechazo (si aplica)
            resend_consecutive: Reenviar consecutivo
        
        Returns:
            dict: Respuesta de la API
        """
        url = f"{self.base_url}/api/ubl2.1/send-event"
        
        payload = {
            "event_id": event_id,
            "allow_cash_documents": allow_cash_documents,
            "sendmail": sendmail,
            "base64_attacheddocument_name": attached_document_name,
            "base64_attacheddocument": attached_document_base64,
            "type_rejection_id": type_rejection_id,
            "resend_consecutive": resend_consecutive
        }
        
        try:
            logger.info(f"📤 Enviando evento a APIDIAN: {url}")
            logger.debug(f"Payload: event_id={event_id}, document={attached_document_name}")
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"✅ Evento enviado exitosamente")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error enviando evento a APIDIAN: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Respuesta del servidor: {e.response.text}")
            raise
    
    def send_event_from_file(self, event_id, xml_file_path, 
                            allow_cash_documents=False, sendmail=False,
                            type_rejection_id=None, resend_consecutive=False):
        """
        Envía un evento desde un archivo XML
        
        Args:
            event_id: ID del evento
            xml_file_path: Ruta al archivo XML
            allow_cash_documents: Permitir documentos de efectivo
            sendmail: Enviar por email
            type_rejection_id: ID del tipo de rechazo
            resend_consecutive: Reenviar consecutivo
        
        Returns:
            dict: Respuesta de la API
        """
        from pathlib import Path
        
        xml_path = Path(xml_file_path)
        if not xml_path.exists():
            raise FileNotFoundError(f"Archivo XML no encontrado: {xml_file_path}")
        
        # Leer archivo y convertir a base64
        with open(xml_path, 'rb') as f:
            xml_content = f.read()
            xml_base64 = base64.b64encode(xml_content).decode('utf-8')
        
        # Obtener nombre del archivo
        document_name = xml_path.name
        
        return self.send_event(
            event_id=event_id,
            attached_document_name=document_name,
            attached_document_base64=xml_base64,
            allow_cash_documents=allow_cash_documents,
            sendmail=sendmail,
            type_rejection_id=type_rejection_id,
            resend_consecutive=resend_consecutive
        )

