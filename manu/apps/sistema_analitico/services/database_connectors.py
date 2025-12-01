import pandas as pd
import firebirdsql
import pyodbc
from sqlalchemy import create_engine
import logging

logger = logging.getLogger(__name__)

class DatabaseConnector:

    @staticmethod
    def conectar_firebird(servidor, ruta_base=None):
        try:
            # Validar que ruta_base no esté vacía
            if not ruta_base:
                raise ValueError("La ruta a la base de datos no puede estar vacía. Verifica la configuración del servidor.")
            
            # Validar formato de host
            host = servidor.host.strip()
            if not host:
                raise ValueError("El host del servidor no puede estar vacío")
            
            # Si el host parece ser solo un número (ej: "3.100"), podría ser una IP incompleta
            # En ese caso, asumimos que es parte de la red VPN 10.8.3.x
            if host.replace('.', '').isdigit() and host.count('.') < 3:
                logger.warning(f"Host '{host}' parece ser una IP incompleta. Si estás en la red VPN, debería ser '10.8.3.{host}'")
            
            config = {
                'host': host,
                'database': ruta_base,
                'user': servidor.usuario,
                'password': servidor.password,
                'port': servidor.puerto or 3050,
                'charset': 'WIN1252',
                'timeout': 30  # Reducido a 30 segundos para fallar más rápido
            }
            
            logger.info(f"Conectando a Firebird: {host}:{config['port']} - Base: {ruta_base}")
            return firebirdsql.connect(**config)
        except Exception as e:
            logger.error(f"Error conectando a Firebird ({servidor.host}:{servidor.puerto or 3050}): {e}")
            raise
    
    @staticmethod
    def conectar_postgresql(servidor, ruta_base=None):
        try:
            connection_string = f"postgresql://{servidor.usuario}:{servidor.password}@{servidor.host}:{servidor.puerto or 5432}/{ruta_base or 'postgres'}"
            return create_engine(connection_string)
        except Exception as e:
            logger.error(f"Error conectando a PostgreSQL: {e}")
            raise
    
    @staticmethod
    def conectar_sqlserver(servidor, ruta_base=None):
        try:
            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={servidor.host};"
                f"DATABASE={ruta_base or 'master'};"
                f"UID={servidor.usuario};"
                f"PWD={servidor.password}"
            )
            return pyodbc.connect(connection_string)
        except Exception as e:
            logger.error(f"Error conectando a SQL Server: {e}")
            raise
    
    @staticmethod
    def ejecutar_consulta(conexion, consulta, params=None, tipo_servidor='FIREBIRD', chunk_size=10000):
        try:
            if tipo_servidor == 'FIREBIRD':
                cursor = conexion.cursor()
                cursor.execute(consulta, params or [])

                
                chunks = []
                columnas = [desc[0] for desc in cursor.description]

                while True:
                    resultados = cursor.fetchmany(chunk_size)
                    if not resultados:
                        break
                    chunks.extend(resultados)

                cursor.close()

                if not chunks:
                    return pd.DataFrame(columns=columnas)

                print(f"Total filas obtenidas desde Firebird: {len(chunks)}")
                return pd.DataFrame(chunks, columns=columnas)

           
            elif tipo_servidor in ['POSTGRESQL', 'MYSQL']:
                return pd.read_sql_query(consulta, conexion, params=params)

            elif tipo_servidor == 'SQLSERVER':
                return pd.read_sql_query(consulta, conexion, params=params)

        except Exception as e:
            logger.error(f"Error ejecutando consulta: {e}")
            raise