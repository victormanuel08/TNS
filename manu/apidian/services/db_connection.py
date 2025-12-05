"""
Servicio para conectarse a la base de datos MariaDB de APIDIAN
"""
import pymysql
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ApidianDBConnection:
    """Maneja la conexión a la base de datos MariaDB de APIDIAN"""
    
    def __init__(self):
        self.host = getattr(settings, 'APIDIAN_DB_HOST', '45.149.204.184')
        self.port = getattr(settings, 'APIDIAN_DB_PORT', 3307)
        self.user = getattr(settings, 'APIDIAN_DB_USER', 'apidian')
        self.password = getattr(settings, 'APIDIAN_DB_PASSWORD', '')
        self.database = getattr(settings, 'APIDIAN_DB_NAME', 'apidian')
        self.connection = None
    
    def connect(self):
        """Establece conexión a la base de datos"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10
            )
            logger.info(f"✅ Conectado a BD APIDIAN: {self.host}:{self.port}/{self.database}")
            return self.connection
        except Exception as e:
            logger.error(f"❌ Error conectando a BD APIDIAN: {e}")
            raise
    
    def disconnect(self):
        """Cierra la conexión"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("🔌 Desconectado de BD APIDIAN")
    
    def execute_query(self, query, params=None):
        """Ejecuta una consulta y retorna los resultados"""
        if not self.connection:
            self.connect()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Error ejecutando query: {e}")
            raise
    
    def execute_one(self, query, params=None):
        """Ejecuta una consulta y retorna un solo resultado"""
        if not self.connection:
            self.connect()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"❌ Error ejecutando query: {e}")
            raise
    
    def execute_update(self, query, params=None):
        """Ejecuta una actualización (INSERT, UPDATE, DELETE)"""
        if not self.connection:
            self.connect()
        
        try:
            with self.connection.cursor() as cursor:
                affected_rows = cursor.execute(query, params or ())
                self.connection.commit()
                return affected_rows
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Error ejecutando update: {e}")
            raise
    
    def __enter__(self):
        """Context manager: entrar"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: salir"""
        self.disconnect()

