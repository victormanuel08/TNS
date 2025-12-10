"""
ViewSet para administración de configuraciones de Firebird
Permite gestionar resoluciones (PREFIJO) y configuraciones (VARIOS) desde endpoints
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.authentication import BaseAuthentication
from django.db import transaction
from .models import EmpresaServidor, APIKeyCliente
from .services.tns_bridge import TNSBridge
from .services.permisos import HasValidAPIKey
import logging

logger = logging.getLogger(__name__)


class FirebirdAdminViewSet(viewsets.ViewSet):
    """
    ViewSet para administrar configuraciones de bases de datos Firebird.
    Requiere API Key o autenticación JWT.
    """
    permission_classes = [HasValidAPIKey]
    authentication_classes = []
    
    def initial(self, request, *args, **kwargs):
        """Valida API Key antes de procesar la petición"""
        super().initial(request, *args, **kwargs)
        
        # Validar API Key si se proporciona
        # Obtener API Key de headers
        api_key = request.META.get('HTTP_API_KEY') or request.META.get('HTTP_X_API_KEY')
        if not api_key:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Api-Key '):
                api_key = auth_header.replace('Api-Key ', '')
            elif auth_header.startswith('Bearer '):
                # Verificar que sea una API Key (formato sk_...) y no un JWT (formato eyJ...)
                bearer_token = auth_header.replace('Bearer ', '').strip()
                if bearer_token.startswith('sk_'):
                    api_key = bearer_token
                # Si es JWT (eyJ...), ignorarlo - no es una API Key
        
        if api_key:
            try:
                api_key_obj = APIKeyCliente.objects.get(
                    api_key__iexact=api_key.strip(),
                    activa=True
                )
                if not api_key_obj.esta_expirada():
                    request.cliente_api = api_key_obj
                    request.empresas_autorizadas = api_key_obj.empresas_asociadas.all()
            except APIKeyCliente.DoesNotExist:
                pass
    
    def _get_empresa(self, empresa_servidor_id):
        """Obtiene empresa y valida que exista"""
        try:
            return EmpresaServidor.objects.get(id=empresa_servidor_id)
        except EmpresaServidor.DoesNotExist:
            raise ValueError(f"Empresa con ID {empresa_servidor_id} no encontrada")
    
    def _get_bridge(self, empresa):
        """Obtiene conexión TNSBridge"""
        bridge = TNSBridge(empresa)
        bridge.connect()
        return bridge
    
    # ==================== RESOLUCIONES (PREFIJO) ====================
    
    @action(detail=False, methods=['get'], url_path='resoluciones')
    def listar_resoluciones(self, request):
        """
        Lista todas las resoluciones (tabla PREFIJO) de una empresa.
        
        Query params:
        - empresa_servidor_id: ID de la empresa (requerido)
        """
        empresa_servidor_id = request.query_params.get('empresa_servidor_id')
        if not empresa_servidor_id:
            return Response(
                {'error': 'empresa_servidor_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = self._get_empresa(int(empresa_servidor_id))
            bridge = self._get_bridge(empresa)
            
            try:
                cursor = bridge.conn.cursor()
                cursor.execute("""
                    SELECT 
                        PREFIJOID,
                        CODPREFIJO,
                        PREIMP,
                        RESOLUCION,
                        NUMFINFACELE,
                        CONTINGENCIA,
                        PREFE
                    FROM PREFIJO
                    ORDER BY CODPREFIJO
                """)
                
                resoluciones = []
                for row in cursor.fetchall():
                    resoluciones.append({
                        'id': row[0],
                        'codprefijo': row[1] or '',
                        'preimp': row[2] or '',
                        'resolucion': row[3] or '',
                        'numfinfacele': row[4] or '',
                        'contingencia': row[5] or '',
                        'prefe': row[6] or ''
                    })
                
                return Response({
                    'empresa': empresa.nombre,
                    'empresa_id': empresa.id,
                    'resoluciones': resoluciones,
                    'total': len(resoluciones)
                })
            finally:
                cursor.close()
                bridge.close()
                
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error listando resoluciones: {e}", exc_info=True)
            return Response(
                {'error': f'Error al listar resoluciones: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['put', 'patch'], url_path='resoluciones/actualizar')
    def actualizar_resolucion(self, request):
        """
        Actualiza una resolución (registro en tabla PREFIJO).
        
        Body:
        {
            "empresa_servidor_id": 1,
            "codprefijo": "FE",
            "preimp": "FE",  # Opcional
            "resolucion": "1234567890",  # Opcional
            "numfinfacele": "1000",  # Opcional
            "contingencia": "N",  # Opcional
            "prefijo": "FE"  # Opcional
        }
        """
        empresa_servidor_id = request.data.get('empresa_servidor_id')
        codprefijo = request.data.get('codprefijo')
        
        if not empresa_servidor_id or not codprefijo:
            return Response(
                {'error': 'empresa_servidor_id y codprefijo son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = self._get_empresa(int(empresa_servidor_id))
            bridge = self._get_bridge(empresa)
            
            try:
                # Construir UPDATE dinámico
                campos_actualizables = {
                    'preimp': request.data.get('preimp'),
                    'resolucion': request.data.get('resolucion'),
                    'numfinfacele': request.data.get('numfinfacele'),
                    'contingencia': request.data.get('contingencia'),
                    'prefijo': request.data.get('prefijo')
                }
                
                # Filtrar solo campos que se enviaron
                campos_a_actualizar = {
                    k: v for k, v in campos_actualizables.items()
                    if v is not None
                }
                
                if not campos_a_actualizar:
                    return Response(
                        {'error': 'Debes enviar al menos un campo para actualizar'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Construir SQL
                set_clauses = []
                params = []
                # Mapear nombres de campos del frontend a nombres de columnas en Firebird
                campo_mapping = {
                    'preimp': 'PREIMP',
                    'resolucion': 'RESOLUCION',
                    'numfinfacele': 'NUMFINFACELE',
                    'contingencia': 'CONTINGENCIA',
                    'prefe': 'PREFE'
                }
                
                for campo, valor in campos_a_actualizar.items():
                    columna_firebird = campo_mapping.get(campo, campo.upper())
                    set_clauses.append(f"{columna_firebird} = ?")
                    params.append(valor)
                
                params.append(codprefijo)
                
                sql = f"""
                    UPDATE PREFIJO
                    SET {', '.join(set_clauses)}
                    WHERE CODPREFIJO = ?
                """
                
                cursor = bridge.conn.cursor()
                cursor.execute(sql, params)
                bridge.conn.commit()
                
                # Verificar si se actualizó
                if cursor.rowcount == 0:
                    return Response(
                        {'error': f'No se encontró resolución con codprefijo={codprefijo}'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                return Response({
                    'success': True,
                    'message': f'Resolución {codprefijo} actualizada exitosamente',
                    'campos_actualizados': list(campos_a_actualizar.keys())
                })
            finally:
                cursor.close()
                bridge.close()
                
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error actualizando resolución: {e}", exc_info=True)
            return Response(
                {'error': f'Error al actualizar resolución: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # ==================== CONFIGURACIONES (VARIOS) ====================
    
    @action(detail=False, methods=['get'], url_path='configuraciones')
    def listar_configuraciones(self, request):
        """
        Lista todas las configuraciones (tabla VARIOS) de una empresa.
        
        Query params:
        - empresa_servidor_id: ID de la empresa (requerido)
        - clave: (opcional) Filtrar por una clave específica
        """
        empresa_servidor_id = request.query_params.get('empresa_servidor_id')
        clave = request.query_params.get('clave')
        
        if not empresa_servidor_id:
            return Response(
                {'error': 'empresa_servidor_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = self._get_empresa(int(empresa_servidor_id))
            bridge = self._get_bridge(empresa)
            
            try:
                cursor = bridge.conn.cursor()
                
                if clave:
                    # Buscar una clave específica
                    cursor.execute("""
                        SELECT variab, CAST(contenido AS VARCHAR(500))
                        FROM varios
                        WHERE variab = ?
                    """, (clave,))
                    
                    row = cursor.fetchone()
                    if row:
                        configuraciones = {row[0]: row[1] or ''}
                    else:
                        configuraciones = {}
                else:
                    # Listar todas las configuraciones comunes de DIAN
                    claves_comunes = [
                        'TOKENDIANVM', 'ENDPOINTDIANVM', 'GTIPIMPVM', 'GTIPCOTVM',
                        'FOOTERDIANVM', 'DIANVMEMAIL', 'DIANVMADDRESS', 
                        'CABECERADIANVM', 'ZESEVM'
                    ]
                    
                    configuraciones = {}
                    for clave in claves_comunes:
                        cursor.execute("""
                            SELECT CAST(contenido AS VARCHAR(500))
                            FROM varios
                            WHERE variab = ?
                        """, (clave,))
                        
                        row = cursor.fetchone()
                        configuraciones[clave] = row[0] if row and row[0] else ''
                
                return Response({
                    'empresa': empresa.nombre,
                    'empresa_id': empresa.id,
                    'configuraciones': configuraciones
                })
            finally:
                cursor.close()
                bridge.close()
                
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error listando configuraciones: {e}", exc_info=True)
            return Response(
                {'error': f'Error al listar configuraciones: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['put', 'post'], url_path='configuraciones/actualizar')
    def actualizar_configuracion(self, request):
        """
        Actualiza o crea una configuración (registro en tabla VARIOS).
        
        Body:
        {
            "empresa_servidor_id": 1,
            "clave": "TOKENDIANVM",
            "valor": "nuevo_token_123"
        }
        """
        empresa_servidor_id = request.data.get('empresa_servidor_id')
        clave = request.data.get('clave')
        valor = request.data.get('valor')
        
        if not empresa_servidor_id or not clave:
            return Response(
                {'error': 'empresa_servidor_id y clave son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = self._get_empresa(int(empresa_servidor_id))
            bridge = self._get_bridge(empresa)
            
            try:
                cursor = bridge.conn.cursor()
                
                # Verificar si existe
                cursor.execute("""
                    SELECT COUNT(*) FROM varios WHERE variab = ?
                """, (clave,))
                
                existe = cursor.fetchone()[0] > 0
                
                if existe:
                    # Actualizar
                    cursor.execute("""
                        UPDATE varios
                        SET contenido = ?
                        WHERE variab = ?
                    """, (valor or '', clave))
                else:
                    # Insertar
                    cursor.execute("""
                        INSERT INTO varios (variab, contenido)
                        VALUES (?, ?)
                    """, (clave, valor or ''))
                
                bridge.conn.commit()
                
                return Response({
                    'success': True,
                    'message': f'Configuración {clave} {"actualizada" if existe else "creada"} exitosamente',
                    'accion': 'actualizada' if existe else 'creada'
                })
            finally:
                cursor.close()
                bridge.close()
                
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error actualizando configuración: {e}", exc_info=True)
            return Response(
                {'error': f'Error al actualizar configuración: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # ==================== SCRIPTS (TABLA SCRIPTS) ====================
    
    @action(detail=False, methods=['get'], url_path='scripts')
    def listar_scripts(self, request):
        """
        Lista todos los scripts (tabla SCRIPTS) de una empresa.
        
        Query params:
        - empresa_servidor_id: ID de la empresa (requerido)
        - nomscript: (opcional) Filtrar por nombre de script
        """
        empresa_servidor_id = request.query_params.get('empresa_servidor_id')
        nomscript = request.query_params.get('nomscript')
        
        if not empresa_servidor_id:
            return Response(
                {'error': 'empresa_servidor_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = self._get_empresa(int(empresa_servidor_id))
            bridge = self._get_bridge(empresa)
            
            try:
                cursor = bridge.conn.cursor()
                
                if nomscript:
                    cursor.execute("""
                        SELECT nomscript, concepto
                        FROM scripts
                        WHERE nomscript = ?
                    """, (nomscript,))
                else:
                    cursor.execute("""
                        SELECT nomscript, concepto
                        FROM scripts
                        ORDER BY nomscript
                    """)
                
                scripts = []
                for row in cursor.fetchall():
                    scripts.append({
                        'nomscript': row[0] or '',
                        'concepto': row[1] or ''
                    })
                
                return Response({
                    'empresa': empresa.nombre,
                    'empresa_id': empresa.id,
                    'scripts': scripts,
                    'total': len(scripts)
                })
            finally:
                cursor.close()
                bridge.close()
                
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error listando scripts: {e}", exc_info=True)
            return Response(
                {'error': f'Error al listar scripts: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='scripts/obtener')
    def obtener_script(self, request):
        """
        Obtiene el contenido de un script específico (CONSCRIPT).
        
        Query params:
        - empresa_servidor_id: ID de la empresa (requerido)
        - nomscript: Nombre del script (requerido)
        """
        empresa_servidor_id = request.query_params.get('empresa_servidor_id')
        nomscript = request.query_params.get('nomscript')
        
        if not empresa_servidor_id or not nomscript:
            return Response(
                {'error': 'empresa_servidor_id y nomscript son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = self._get_empresa(int(empresa_servidor_id))
            bridge = self._get_bridge(empresa)
            
            try:
                cursor = bridge.conn.cursor()
                cursor.execute("""
                    SELECT concepto, conscript
                    FROM scripts
                    WHERE nomscript = ?
                """, (nomscript,))
                
                row = cursor.fetchone()
                if not row:
                    return Response(
                        {'error': f'Script {nomscript} no encontrado'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Leer BLOB como texto
                concepto = row[0] or ''
                conscript_blob = row[1]
                
                if conscript_blob:
                    conscript_texto = conscript_blob.read().decode('utf-8', errors='ignore')
                else:
                    conscript_texto = ''
                
                return Response({
                    'nomscript': nomscript,
                    'concepto': concepto,
                    'conscript': conscript_texto
                })
            finally:
                cursor.close()
                bridge.close()
                
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error obteniendo script: {e}", exc_info=True)
            return Response(
                {'error': f'Error al obtener script: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generar_script_jexe(self, ruta_bd: str) -> str:
        """Genera el script estándar para ejecutar j.exe"""
        return f"""var
  vid,  ruta_bd, prefijo, numero, comando: String;

begin
  // Obtener el ID del recibo (valor hardcodeado como ejemplo)
  vid := TNS_GE_LEEPARAM(1);

 if(tns_bd_lockup(vid,'kardex','kardexid','fecasentad')<>'') then

 begin
  // Definir ruta de la base de datos
  ruta_bd := '{ruta_bd}';

  // Construir el comando con todos los parámetros entre comillas
  comando := '"' +  ruta_bd + '" ' +  vid;

  // Ejecutar el comando
  TNS_GE_EjecutarExe('C:\\TEMPO\\j.exe', comando);

 end;
end."""
    
    @action(detail=False, methods=['post', 'put'], url_path='scripts/crear-actualizar')
    def crear_actualizar_script(self, request):
        """
        Crea o actualiza un script. Si no existe, lo crea. Si existe, lo actualiza.
        
        Body:
        {
            "empresa_servidor_id": 1,
            "nomscript": "ASEN_FACVTADES",
            "concepto": "Asentar facturas de ventas",
            "conscript": "var...",  // Opcional, si no se envía se genera automáticamente
            "auto_generar": true  // Si es true, genera script estándar con ruta_bd automática
        }
        """
        empresa_servidor_id = request.data.get('empresa_servidor_id')
        nomscript = request.data.get('nomscript')
        concepto = request.data.get('concepto', '')
        conscript = request.data.get('conscript')
        auto_generar = request.data.get('auto_generar', False)
        
        if not empresa_servidor_id or not nomscript:
            return Response(
                {'error': 'empresa_servidor_id y nomscript son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = self._get_empresa(int(empresa_servidor_id))
            bridge = self._get_bridge(empresa)
            
            try:
                cursor = bridge.conn.cursor()
                
                # Verificar si existe
                cursor.execute("""
                    SELECT COUNT(*) FROM scripts WHERE nomscript = ?
                """, (nomscript,))
                
                existe = cursor.fetchone()[0] > 0
                
                # Si auto_generar y no se envió conscript, generar automáticamente
                if auto_generar and not conscript:
                    conscript = self._generar_script_jexe(empresa.ruta_base)
                
                if not conscript:
                    return Response(
                        {'error': 'conscript es requerido o activa auto_generar'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Preparar BLOB usando blob_creator de firebirdsql
                conscript_bytes = conscript.encode('utf-8')
                blob_creator = bridge.conn.blob_create()
                blob_creator.write(conscript_bytes)
                
                if existe:
                    # Actualizar
                    cursor.execute("""
                        UPDATE SCRIPTS
                        SET CONCEPTO = ?, CONSCRIPT = ?
                        WHERE NOMSCRIPT = ?
                    """, (concepto, blob_creator, nomscript))
                    accion = 'actualizado'
                else:
                    # Insertar
                    cursor.execute("""
                        INSERT INTO SCRIPTS (NOMSCRIPT, CONCEPTO, CONSCRIPT)
                        VALUES (?, ?, ?)
                    """, (nomscript, concepto, blob_creator))
                    accion = 'creado'
                
                # Cerrar blob después de usarlo
                blob_creator.close()
                
                bridge.conn.commit()
                
                return Response({
                    'success': True,
                    'message': f'Script {nomscript} {accion} exitosamente',
                    'accion': accion,
                    'nomscript': nomscript
                })
            finally:
                cursor.close()
                bridge.close()
                
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creando/actualizando script: {e}", exc_info=True)
            return Response(
                {'error': f'Error al crear/actualizar script: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='scripts/crear-lotes')
    def crear_scripts_lotes(self, request):
        """
        Crea los 4 scripts estándar si no existen: ASEN_DEVVTADES, ASEN_FACVTADES, EDIT_DEVVTA, EDIT_FACVTA
        
        Body:
        {
            "empresa_servidor_id": 1
        }
        """
        empresa_servidor_id = request.data.get('empresa_servidor_id')
        
        if not empresa_servidor_id:
            return Response(
                {'error': 'empresa_servidor_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = self._get_empresa(int(empresa_servidor_id))
            bridge = self._get_bridge(empresa)
            
            scripts_estandar = [
                {'nomscript': 'ASEN_DEVVTADES', 'concepto': 'Asentar devoluciones de ventas'},
                {'nomscript': 'ASEN_FACVTADES', 'concepto': 'Asentar facturas de ventas'},
                {'nomscript': 'EDIT_DEVVTA', 'concepto': 'Editar devolución de venta'},
                {'nomscript': 'EDIT_FACVTA', 'concepto': 'Editar factura de venta'}
            ]
            
            conscript_base = self._generar_script_jexe(empresa.ruta_base)
            resultados = []
            
            try:
                cursor = bridge.conn.cursor()
                
                for script in scripts_estandar:
                    # Verificar si existe
                    cursor.execute("""
                        SELECT COUNT(*) FROM SCRIPTS WHERE NOMSCRIPT = ?
                    """, (script['nomscript'],))
                    
                    existe = cursor.fetchone()[0] > 0
                    
                    # Preparar BLOB usando blob_creator
                    conscript_bytes = script['content'].encode('utf-8')
                    blob_creator = bridge.conn.blob_create()
                    blob_creator.write(conscript_bytes)
                    
                    if existe:
                        # Actualizar
                        cursor.execute("""
                            UPDATE SCRIPTS
                            SET CONCEPTO = ?, CONSCRIPT = ?
                            WHERE NOMSCRIPT = ?
                        """, (script['concepto'], blob_creator, script['nomscript']))
                        accion = 'actualizado'
                    else:
                        # Insertar
                        cursor.execute("""
                            INSERT INTO SCRIPTS (NOMSCRIPT, CONCEPTO, CONSCRIPT)
                            VALUES (?, ?, ?)
                        """, (script['nomscript'], script['concepto'], blob_creator))
                        accion = 'creado'
                    
                    # Cerrar blob después de usarlo
                    blob_creator.close()
                    
                    resultados.append({
                        'nomscript': script['nomscript'],
                        'accion': accion
                    })
                
                bridge.conn.commit()
                
                return Response({
                    'success': True,
                    'message': f'{len(resultados)} scripts procesados',
                    'scripts': resultados
                })
            finally:
                cursor.close()
                bridge.close()
                
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creando scripts en lote: {e}", exc_info=True)
            return Response(
                {'error': f'Error al crear scripts en lote: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # ==================== INFORMACIÓN GENERAL ====================
    
    @action(detail=False, methods=['get'], url_path='info')
    def info_empresa(self, request):
        """
        Obtiene información general de la empresa y su base de datos.
        
        Query params:
        - empresa_servidor_id: ID de la empresa (requerido)
        """
        empresa_servidor_id = request.query_params.get('empresa_servidor_id')
        if not empresa_servidor_id:
            return Response(
                {'error': 'empresa_servidor_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = self._get_empresa(int(empresa_servidor_id))
            
            return Response({
                'empresa': {
                    'id': empresa.id,
                    'nombre': empresa.nombre,
                    'nit': empresa.nit,
                    'nit_normalizado': empresa.nit_normalizado,
                    'anio_fiscal': empresa.anio_fiscal,
                    'ruta_base': empresa.ruta_base,
                    'codigo': empresa.codigo
                }
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error obteniendo info: {e}", exc_info=True)
            return Response(
                {'error': f'Error al obtener información: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

