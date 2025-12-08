"""
Servicio para obtener credenciales de empresas desde la BD MariaDB de APIDIAN
Consulta companies por identification_number (NIT) y obtiene datos relacionados
"""
import logging
from .db_connection import ApidianDBConnection

logger = logging.getLogger(__name__)


class CompanyCredentialsService:
    """Servicio para obtener credenciales de empresas desde APIDIAN"""
    
    def __init__(self):
        self.db = ApidianDBConnection()
    
    def obtener_credenciales_por_nit(self, nit):
        """
        Obtiene todas las credenciales de una empresa por su NIT (identification_number)
        
        Consulta:
        1. companies por identification_number
        2. resolutions por company_id
        3. software por company_id
        4. users por userid (de companies) para obtener email, nombre, apitoken
        
        Args:
            nit: Número de identificación tributaria (identification_number en companies)
            
        Returns:
            dict con todas las credenciales y datos relacionados
        """
        try:
            self.db.connect()
            
            # 1. Buscar company por identification_number
            logger.info(f"🔍 [CREDENCIALES] Buscando company con NIT: {nit}")
            company_query = """
                SELECT * FROM companies 
                WHERE identification_number = %s
                LIMIT 1
            """
            company = self.db.execute_one(company_query, (nit,))
            
            if not company:
                logger.warning(f"❌ [CREDENCIALES] Company no encontrada para NIT: {nit}")
                return {
                    'encontrado': False,
                    'error': f'Company no encontrada para NIT: {nit}'
                }
            
            company_id = company.get('id')
            userid = company.get('userid')
            
            logger.info(f"✅ [CREDENCIALES] Company encontrada: ID={company_id}, UserID={userid}")
            
            # 2. Buscar resolutions por company_id
            resolutions_query = """
                SELECT * FROM resolutions 
                WHERE company_id = %s
            """
            resolutions = self.db.execute_query(resolutions_query, (company_id,))
            logger.info(f"📋 [CREDENCIALES] Resolutions encontradas: {len(resolutions)}")
            
            # 3. Buscar software por company_id
            software_query = """
                SELECT * FROM software 
                WHERE company_id = %s
            """
            software = self.db.execute_query(software_query, (company_id,))
            logger.info(f"💻 [CREDENCIALES] Software encontrado: {len(software)}")
            
            # 4. Buscar user por userid para obtener email, nombre, apitoken
            user_data = None
            if userid:
                user_query = """
                    SELECT id, email, name, apitoken, razon_social 
                    FROM users 
                    WHERE id = %s
                    LIMIT 1
                """
                user_data = self.db.execute_one(user_query, (userid,))
                if user_data:
                    logger.info(f"👤 [CREDENCIALES] User encontrado: {user_data.get('email')}")
                else:
                    logger.warning(f"⚠️ [CREDENCIALES] User no encontrado para userid: {userid}")
            
            # Construir respuesta completa
            respuesta = {
                'encontrado': True,
                'nit': nit,
                'company': {
                    'id': company.get('id'),
                    'identification_number': company.get('identification_number'),
                    'name': company.get('name'),
                    'userid': company.get('userid'),
                    'datos_completos': company
                },
                'resolutions': [
                    {
                        'id': r.get('id'),
                        'company_id': r.get('company_id'),
                        'datos_completos': r
                    }
                    for r in resolutions
                ],
                'software': [
                    {
                        'id': s.get('id'),
                        'company_id': s.get('company_id'),
                        'name': s.get('name'),
                        'datos_completos': s
                    }
                    for s in software
                ],
                'user': {
                    'id': user_data.get('id') if user_data else None,
                    'email': user_data.get('email') if user_data else None,
                    'name': user_data.get('name') if user_data else None,
                    'razon_social': user_data.get('razon_social') if user_data else None,
                    'apitoken': user_data.get('apitoken') if user_data else None,  # Este es el token para eventos
                    'datos_completos': user_data
                } if user_data else None,
                'token': user_data.get('apitoken') if user_data else None,  # Token principal para usar
                'softwareidfacturacion': software[0].get('id') if software else None,
                'software_nomina_pin': None,  # Si hay un campo específico para PIN de nómina, agregarlo aquí
            }
            
            logger.info(f"✅ [CREDENCIALES] Credenciales obtenidas exitosamente para NIT: {nit}")
            logger.info(f"   - Token (apitoken): {'✅' if respuesta['token'] else '❌'}")
            logger.info(f"   - Software ID: {respuesta['softwareidfacturacion']}")
            logger.info(f"   - Resolutions: {len(respuesta['resolutions'])}")
            
            return respuesta
            
        except Exception as e:
            logger.error(f"❌ [CREDENCIALES] Error obteniendo credenciales: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'encontrado': False,
                'error': f'Error obteniendo credenciales: {str(e)}'
            }
        finally:
            self.db.disconnect()

