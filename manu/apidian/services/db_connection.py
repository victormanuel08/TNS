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
        # Si ya hay una conexión activa, verificar que esté viva
        if self.connection:
            try:
                # Intentar hacer un ping para verificar que la conexión esté viva
                self.connection.ping(reconnect=False)
                logger.info("✅ [DB CONNECTION] Reutilizando conexión existente")
                print("=" * 80)
                print("✅ [DB CONNECTION] REUTILIZANDO CONEXIÓN EXISTENTE")
                print("=" * 80)
                return self.connection
            except Exception as e:
                logger.warning(f"⚠️ [DB CONNECTION] Conexión existente no válida, cerrando: {e}")
                try:
                    self.connection.close()
                except:
                    pass
                self.connection = None
        
        # 🔥 IMPRIMIR CREDENCIALES DE CONEXIÓN
        print("=" * 80)
        print("🔌 [DB CONNECTION] CONECTANDO A BD APIDIAN:")
        print(f"   🌐 Host/IP: {self.host}")
        print(f"   🔌 Puerto: {self.port}")
        print(f"   👤 Usuario: {self.user}")
        print(f"   🔑 Password: {'*' * len(self.password) if self.password else '(vacío)'} (longitud: {len(self.password) if self.password else 0})")
        print(f"   📊 Database: {self.database}")
        print("=" * 80)
        logger.info(f"🔌 [DB CONNECTION] Conectando a BD APIDIAN: {self.host}:{self.port}/{self.database}")
        logger.info(f"   Usuario: {self.user}")
        
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10,
                autocommit=True  # Evitar problemas de transacciones
            )
            logger.info(f"✅ Conectado a BD APIDIAN: {self.host}:{self.port}/{self.database}")
            print("=" * 80)
            print("✅ [DB CONNECTION] CONEXIÓN EXITOSA")
            print("=" * 80)
            return self.connection
        except Exception as e:
            logger.error(f"❌ Error conectando a BD APIDIAN: {e}")
            print("=" * 80)
            print(f"❌ [DB CONNECTION] ERROR DE CONEXIÓN: {e}")
            print(f"   Tipo de error: {type(e).__name__}")
            print("=" * 80)
            # Asegurar que connection sea None si falla
            self.connection = None
            raise
    
    def disconnect(self):
        """Cierra la conexión"""
        try:
            if self.connection:
                self.connection.close()
                logger.info("🔌 Desconectado de BD APIDIAN")
                print("=" * 80)
                print("🔌 [DB CONNECTION] DESCONECTADO")
                print("=" * 80)
        except Exception as e:
            logger.warning(f"⚠️ Error al desconectar: {e}")
            print(f"⚠️ [DB CONNECTION] Error al desconectar: {e}")
        finally:
            self.connection = None
    
    def execute_query(self, query, params=None):
        """Ejecuta una consulta y retorna los resultados"""
        if not self.connection:
            self.connect()
        
        # 🔥 IMPRIMIR SQL Y PARÁMETROS
        params_str = params if params else "()"
        print("=" * 80)
        print("📝 [DB QUERY] EJECUTANDO SQL:")
        print(f"   SQL: {query}")
        print(f"   Parámetros: {params_str}")
        print("=" * 80)
        logger.info(f"📝 [DB QUERY] SQL: {query}")
        logger.info(f"📝 [DB QUERY] Parámetros: {params_str}")
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or ())
                resultados = cursor.fetchall()
                print("=" * 80)
                print(f"✅ [DB QUERY] RESULTADOS: {len(resultados)} filas")
                print("=" * 80)
                logger.info(f"✅ [DB QUERY] Resultados: {len(resultados)} filas")
                return resultados
        except Exception as e:
            logger.error(f"❌ Error ejecutando query: {e}")
            print("=" * 80)
            print(f"❌ [DB QUERY] ERROR: {e}")
            print("=" * 80)
            raise
    
    def execute_one(self, query, params=None):
        """Ejecuta una consulta y retorna un solo resultado"""
        if not self.connection:
            self.connect()
        
        # 🔥 IMPRIMIR SQL Y PARÁMETROS
        params_str = params if params else "()"
        print("=" * 80)
        print("📝 [DB QUERY] EJECUTANDO SQL (execute_one):")
        print(f"   SQL: {query}")
        print(f"   Parámetros: {params_str}")
        print("=" * 80)
        logger.info(f"📝 [DB QUERY] SQL (execute_one): {query}")
        logger.info(f"📝 [DB QUERY] Parámetros: {params_str}")
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or ())
                resultado = cursor.fetchone()
                if resultado:
                    print("=" * 80)
                    print(f"✅ [DB QUERY] RESULTADO ENCONTRADO:")
                    print(f"   Keys: {list(resultado.keys())}")
                    print(f"   Valores: {dict(resultado)}")
                    print("=" * 80)
                    logger.info(f"✅ [DB QUERY] Resultado encontrado: {list(resultado.keys())}")
                else:
                    print("=" * 80)
                    print("⚠️ [DB QUERY] NO SE ENCONTRÓ RESULTADO")
                    print("=" * 80)
                    logger.warning(f"⚠️ [DB QUERY] No se encontró resultado")
                return resultado
        except Exception as e:
            logger.error(f"❌ Error ejecutando query: {e}")
            print("=" * 80)
            print(f"❌ [DB QUERY] ERROR: {e}")
            print("=" * 80)
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

