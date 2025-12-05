"""
Servicios para consultar datos de la base de datos APIDIAN
Facilita el llenado de información para los endpoints
"""
from .db_connection import ApidianDBConnection
import logging

logger = logging.getLogger(__name__)


class ApidianDataQueries:
    """Servicios para consultar datos de APIDIAN desde la BD"""
    
    def __init__(self):
        self.db = ApidianDBConnection()
    
    def get_events(self):
        """Obtiene la lista de eventos disponibles"""
        query = "SELECT * FROM events ORDER BY id"
        try:
            return self.db.execute_query(query)
        except Exception as e:
            logger.error(f"Error obteniendo eventos: {e}")
            return []
    
    def get_event_by_id(self, event_id):
        """Obtiene un evento por ID"""
        query = "SELECT * FROM events WHERE id = %s"
        try:
            return self.db.execute_one(query, (event_id,))
        except Exception as e:
            logger.error(f"Error obteniendo evento {event_id}: {e}")
            return None
    
    def get_type_rejections(self):
        """Obtiene la lista de tipos de rechazo"""
        query = "SELECT * FROM type_rejections ORDER BY id"
        try:
            return self.db.execute_query(query)
        except Exception as e:
            logger.error(f"Error obteniendo tipos de rechazo: {e}")
            return []
    
    def get_documents_by_nit(self, nit, limit=100):
        """Obtiene documentos por NIT"""
        query = """
            SELECT * FROM documents 
            WHERE nit = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        try:
            return self.db.execute_query(query, (nit, limit))
        except Exception as e:
            logger.error(f"Error obteniendo documentos para NIT {nit}: {e}")
            return []
    
    def get_document_by_id(self, document_id):
        """Obtiene un documento por ID"""
        query = "SELECT * FROM documents WHERE id = %s"
        try:
            return self.db.execute_one(query, (document_id,))
        except Exception as e:
            logger.error(f"Error obteniendo documento {document_id}: {e}")
            return None
    
    def get_document_xml(self, document_id):
        """Obtiene el XML de un documento"""
        query = "SELECT xml_content, xml_filename FROM documents WHERE id = %s"
        try:
            result = self.db.execute_one(query, (document_id,))
            if result:
                return {
                    'content': result.get('xml_content'),
                    'filename': result.get('xml_filename')
                }
            return None
        except Exception as e:
            logger.error(f"Error obteniendo XML del documento {document_id}: {e}")
            return None
    
    def search_documents(self, filters=None):
        """
        Busca documentos con filtros opcionales
        
        Args:
            filters: dict con filtros (nit, fecha_desde, fecha_hasta, etc.)
        
        Returns:
            list: Lista de documentos
        """
        query = "SELECT * FROM documents WHERE 1=1"
        params = []
        
        if filters:
            if 'nit' in filters:
                query += " AND nit = %s"
                params.append(filters['nit'])
            
            if 'fecha_desde' in filters:
                query += " AND created_at >= %s"
                params.append(filters['fecha_desde'])
            
            if 'fecha_hasta' in filters:
                query += " AND created_at <= %s"
                params.append(filters['fecha_hasta'])
        
        query += " ORDER BY created_at DESC LIMIT 100"
        
        try:
            return self.db.execute_query(query, params if params else None)
        except Exception as e:
            logger.error(f"Error buscando documentos: {e}")
            return []

