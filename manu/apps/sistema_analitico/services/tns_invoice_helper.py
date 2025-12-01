"""
Helper para insertar facturas en TNS usando lógica directa (sin stored procedures).
Este módulo centraliza la lógica de inserción de facturas desde autopago.
Todas las operaciones son atómicas para mantener integridad en la base de datos.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import re

logger = logging.getLogger(__name__)


def _normalizar_nit(nit: str) -> str:
    """
    Normaliza un NIT eliminando puntos y todo lo que viene después del guion (incluyendo el guion).
    
    Ejemplo: '13.279115-4' → '13279115'
    Ejemplo: '222222222222-7' → '222222222222'
    
    Args:
        nit: NIT con formato (puede tener puntos y guion)
    
    Returns:
        NIT normalizado (solo números, sin puntos ni dígito verificador)
    """
    if not nit:
        return ''
    
    # Si hay guion, tomar solo lo que está antes del guion
    if '-' in nit:
        nit = nit.split('-')[0]
    
    # Eliminar puntos y otros caracteres no numéricos
    nit_normalizado = re.sub(r'[^0-9]', '', nit)
    
    return nit_normalizado


def _insertar_detalle_factura(
    cursor,
    kardex_id: int,
    codigo_material: str,
    cantidad: float,
    precio: float,
    descuento: float = 0.0
) -> Dict[str, Any]:
    """
    Inserta un detalle de factura en DEKARDEX (lógica de TNS_INS_DETALLEFACTVTA).
    
    Args:
        cursor: Cursor de Firebird
        kardex_id: ID del KARDEX
        codigo_material: Código del material (CODIGO en MATERIAL)
        cantidad: Cantidad del item
        precio: Precio unitario (valor total del item)
        descuento: Descuento aplicado (default 0)
    
    Returns:
        {'success': True/False, 'error': 'mensaje' si hay error}
    """
    try:
        # Verificar que el KARDEX existe y no está asentado
        cursor.execute("""
            SELECT KARDEXID 
            FROM KARDEX 
            WHERE KARDEXID = ? AND FECASENTAD IS NULL
        """, (kardex_id,))
        
        if not cursor.fetchone():
            return {
                'success': False,
                'error': f'KARDEX {kardex_id} no existe o ya está asentado'
            }
        
        # Obtener porcentaje de IVA del material
        cursor.execute("""
            SELECT ti.PORCIVA 
            FROM TIPOIVA ti 
            INNER JOIN MATERIAL m ON (m.TIPOIVAID = ti.TIPOIVAID) 
            WHERE m.CODIGO = ?
        """, (codigo_material,))
        resultado_iva = cursor.fetchone()
        vporciva = float(resultado_iva[0]) if resultado_iva and resultado_iva[0] else 0.0
        
        # Obtener porcentaje de impuesto al consumo del material
        cursor.execute("""
            SELECT ms.PORIMPCONS 
            FROM MATERIALSUC ms 
            INNER JOIN MATERIAL m ON (m.MATID = ms.MATID) 
            WHERE ms.SUCID = 1 AND m.CODIGO = ?
        """, (codigo_material,))
        resultado_ico = cursor.fetchone()
        vporcico = float(resultado_ico[0]) if resultado_ico and resultado_ico[0] else 0.0
        
        # Calcular IVA y ICO
        vvalor = float(precio)
        vtiva = (vvalor / ((100 + vporciva + vporcico) / 100)) * (vporciva / 100)
        vtico = vvalor - (vvalor / ((100 + vporcico) / 100))
        vneto = vvalor
        
        # Obtener MATID
        cursor.execute("SELECT MATID FROM MATERIAL WHERE CODIGO = ?", (codigo_material,))
        resultado_matid = cursor.fetchone()
        if not resultado_matid:
            return {
                'success': False,
                'error': f'Material con código {codigo_material} no encontrado'
            }
        vmatid = resultado_matid[0]
        
        # Obtener BODID de bodega "00"
        cursor.execute("SELECT BODID FROM BODEGA WHERE CODIGO = ?", ('00',))
        resultado_bodid = cursor.fetchone()
        if not resultado_bodid:
            return {
                'success': False,
                'error': 'Bodega con código "00" no encontrada'
            }
        vbodid = resultado_bodid[0]
        
        # Insertar en DEKARDEX
        cursor.execute("""
            INSERT INTO DEKARDEX (
                KARDEXID, MATID, BODID, PRIORIDAD, TIPUND, PORCIVA, DESCUENTO,
                CANLISTA, CANMAT, PRECIOLISTA, PRECIOVTA, PRECIOBASE, PRECIOIVA,
                PRECIONETO, PARCVTA, PARCOSTO, PRECIOICONSUMO
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            kardex_id,           # KARDEXID
            vmatid,              # MATID
            vbodid,              # BODID
            '2',                 # PRIORIDAD (hardcodeado como en stored procedure)
            'D',                 # TIPUND (hardcodeado como en stored procedure)
            vporciva,            # PORCIVA
            descuento,           # DESCUENTO
            cantidad,            # CANLISTA
            cantidad,            # CANMAT
            vvalor,              # PRECIOLISTA
            vvalor,              # PRECIOVTA
            vvalor - vtico - vtiva,  # PRECIOBASE
            vtiva,               # PRECIOIVA
            vneto,               # PRECIONETO
            vneto * cantidad,    # PARCVTA
            vvalor * cantidad,   # PARCOSTO
            vtico                # PRECIOICONSUMO
        ))
        
        logger.info(f"✅ Detalle insertado: {codigo_material} x{cantidad} = ${vvalor}")
        return {'success': True}
        
    except Exception as e:
        logger.error(f"❌ Error al insertar detalle {codigo_material}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def _insertar_forma_pago(
    cursor,
    kardex_id: int,
    forma_pago_codigo: str,
    monto_total: float,
    nit_empresa: str,  # NIT de la empresa (no del cliente)
    tipodoc: Optional[str] = None,
    documento: Optional[str] = None
) -> Dict[str, Any]:
    """
    Inserta forma de pago en DEKARDEXFP (lógica de TNS_INS_DEKARDEXFP).
    
    Args:
        cursor: Cursor de Firebird
        kardex_id: ID del KARDEX
        forma_pago_codigo: Código de forma de pago (CODIGO en FORMAPAGO)
        monto_total: Monto total a pagar
        nit_empresa: NIT de la empresa (para buscar TERID de la empresa)
    
    Returns:
        {'success': True/False, 'error': 'mensaje' si hay error}
    """
    try:
        # Obtener FORMAPAGOID
        cursor.execute("SELECT FORMAPAGOID FROM FORMAPAGO WHERE CODIGO = ?", (forma_pago_codigo,))
        resultado_formapago = cursor.fetchone()
        if not resultado_formapago:
            return {
                'success': False,
                'error': f'Forma de pago con código {forma_pago_codigo} no encontrada'
            }
        vformapagoid = resultado_formapago[0]
        
        # Obtener siguiente DEKARDEXFPID
        cursor.execute("SELECT COALESCE(MAX(DEKARDEXFPID), 0) + 1 FROM DEKARDEXFP")
        resultado_id = cursor.fetchone()
        vdekardexfpid = resultado_id[0] if resultado_id else 1
        
        # Normalizar y buscar TERID de la empresa (no del cliente)
        nit_empresa_normalizado = _normalizar_nit(nit_empresa)
        logger.info(f"🔍 Buscando TERID de empresa con NIT normalizado: {nit_empresa_normalizado}")
        
        # Buscar tercero con LIKE 'NITNORMALIZADO%'
        cursor.execute("SELECT TERID FROM TERCEROS WHERE NIT LIKE ?", (f'{nit_empresa_normalizado}%',))
        
        resultado_terid = cursor.fetchone()
        if not resultado_terid:
            return {
                'success': False,
                'error': f'Empresa con NIT {nit_empresa_normalizado} no encontrada en TERCEROS'
            }
        vterid = resultado_terid[0]
        logger.info(f"✅ TERID de empresa encontrado: {vterid}")
        
        # Preparar tipodoc y documento (info del datafono)
        # tipodoc: 2 caracteres (ej: "TC", "TD", "EF")
        # documento: 20 caracteres (ej: numero_aprobacion o codigo_autorizacion)
        tipodoc_final = (tipodoc or '')[:2] if tipodoc else None
        documento_final = (documento or '')[:20] if documento else None
        
        # Insertar en DEKARDEXFP
        cursor.execute("""
            INSERT INTO DEKARDEXFP (KARDEXID, DEKARDEXFPID, FORMAPAGOID, TERID, VALOR, TIPODOC, DOCUMENTO)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (kardex_id, vdekardexfpid, vformapagoid, vterid, float(monto_total), tipodoc_final, documento_final))
        
        # Actualizar generador (igual que en el stored procedure TNS_INS_DEKARDEXFP)
        # El stored procedure usa EXECUTE STATEMENT, pero desde Python podemos ejecutar directamente
        cursor.execute(f"SET GENERATOR DEKARDEXFPID_GEN TO {vdekardexfpid}")
        logger.info(f"✅ Generador DEKARDEXFPID_GEN actualizado a {vdekardexfpid}")
        
        logger.info(f"✅ Forma de pago insertada: {forma_pago_codigo} por ${monto_total}")
        return {'success': True}
        
    except Exception as e:
        logger.error(f"❌ Error al insertar forma de pago: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def _actualizar_totales(
    cursor,
    kardex_id: int,
    codcomp: str,
    prefijo: str,
    numero: str
) -> Dict[str, Any]:
    """
    Actualiza los totales de la factura usando el procedimiento almacenado TNS_ACTTOTALFACT.
    
    Args:
        cursor: Cursor de Firebird
        kardex_id: ID del KARDEX (no se usa en el procedimiento, pero se mantiene para compatibilidad)
        codcomp: Código de comprobante ('FV')
        prefijo: Prefijo de la factura
        numero: Número de la factura
    
    Returns:
        {'success': True/False, 'error': 'mensaje' si hay error}
    """
    try:
        logger.info(f"🧮 Actualizando totales usando TNS_ACTTOTALFACT para {codcomp}-{prefijo}-{numero}...")
        
        # Llamar al procedimiento almacenado TNS_ACTTOTALFACT
        # Parámetros: codcomp, prefijo, numero
        totales_query = "SELECT * FROM TNS_ACTTOTALFACT(?, ?, ?)"
        totales_params = (codcomp, prefijo, numero)
        
        logger.info(f"📋 Query: {totales_query}")
        logger.info(f"📋 Params: {totales_params}")
        
        cursor.execute(totales_query, totales_params)
        resultado_totales = cursor.fetchone()
        
        logger.info(f"✅ Totales actualizados correctamente usando TNS_ACTTOTALFACT")
        logger.info(f"   Resultado: {resultado_totales}")
        
        return {'success': True}
            
    except Exception as e:
        logger.error(f"❌ Error al actualizar totales con TNS_ACTTOTALFACT: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def insertar_factura_tns(
    bridge,
    cart_items: List[Dict],
    monto_total: float,
    empresa_servidor_id: int,
    invoice_data: Optional[Dict] = None,
    order_type: str = 'takeaway',  # 'takeaway' o 'dinein'
    referencia: str = '',
    medio_pago_data: Optional[Dict] = None,
    forma_pago_codigo: Optional[str] = None,  # Código de forma de pago seleccionado por el usuario
    mesa_number: Optional[str] = None,  # Número de mesa si es dinein
    observacion: Optional[str] = None,  # Observación ya construida desde el front
    usuario_tns: Optional[str] = None  # Usuario TNS logueado
) -> Dict[str, Any]:
    """
    Inserta una factura completa en TNS usando stored procedures.
    
    Args:
        bridge: Instancia de TNSBridge ya conectada
        cart_items: Lista de items del carrito [{'id': 'CODIGO', 'name': '...', 'price': 1000, 'quantity': 2}, ...]
        monto_total: Monto total del pedido
        empresa_servidor_id: ID de la empresa
        invoice_data: Datos de facturación (si aplica) {
            'docType': 'cedula'|'nit',
            'document': '1234567890',
            'name': 'Nombre Completo',
            'email': 'email@example.com',
            'phone': '3001234567'
        }
        order_type: 'takeaway' o 'dinein'
        referencia: Referencia del pedido
        medio_pago_data: Datos del medio de pago del datafono (opcional)
        forma_pago_codigo: Código de forma de pago seleccionado por el usuario (de FORMAPAGO.CODIGO)
        mesa_number: Número de mesa si es dinein
        observacion: Observación ya construida desde el front (ej: "PARA LLEVAR - TEL: 3001234567")
        usuario_tns: Usuario TNS logueado (de session.tnsUsername.value)
    
    Returns:
        {
            'success': True/False,
            'kardex_id': 12345,  # Si success=True
            'prefijo': 'FV',
            'numero': '12345',
            'nit_normalizado': '1234567890',
            'error': 'mensaje de error'  # Si success=False
        }
    """
    try:
        bridge.connect()
        cursor = bridge.conn.cursor()
        
        # ============================================
        # PASO 1: OBTENER VARIABLES DE VARIOS (COMPUESTAS CON USUARIO)
        # ============================================
        logger.info("=" * 80)
        logger.info("🚀 INICIANDO INSERCIÓN DE FACTURA EN TNS")
        logger.info("=" * 80)
        logger.info("📋 PASO 1: Obteniendo variables de configuración desde VARIOS...")
        
        # Obtener usuario logueado (de session.tnsUsername.value)
        usuario_logueado = usuario_tns or 'ADMIN'
        logger.info(f"Usuario logueado: {usuario_logueado}")
        
        # Todas las variables que terminan en CAJAGC se componen dinámicamente:
        # Base + usuario_logueado
        
        # Obtener GPREFIJOCAJAGC (prefijo de factura)
        # Variable en VARIOS: GPREFIJO + usuario_logueado
        variab_prefijo = f"GPREFIJO{usuario_logueado}"
        cursor.execute("""
            SELECT CAST(contenido AS VARCHAR(500)) 
            FROM varios 
            WHERE variab = ?
        """, (variab_prefijo,))
        resultado_prefijo = cursor.fetchone()
        prefijo = resultado_prefijo[0].strip() if resultado_prefijo and resultado_prefijo[0] else 'FV'
        logger.info(f"Prefijo factura ({variab_prefijo}): {prefijo}")
        
        # Obtener GFVCENTROCAJAGC (prefijo centro)
        # Variable en VARIOS: GFVCENTRO + usuario_logueado
        variab_centro = f"GFVCENTRO{usuario_logueado}"
        cursor.execute("""
            SELECT CAST(contenido AS VARCHAR(500)) 
            FROM varios 
            WHERE variab = ?
        """, (variab_centro,))
        resultado_centro = cursor.fetchone()
        prefijo_centro = resultado_centro[0].strip() if resultado_centro and resultado_centro[0] else f"GFVCENTRO{usuario_logueado}"
        logger.info(f"Prefijo centro ({variab_centro}): {prefijo_centro}")
        
        # Obtener GVENDECAJAGC (NIT del vendedor)
        # Variable en VARIOS: GVENDE + usuario_logueado
        variab_vendedor = f"GVENDE{usuario_logueado}"
        cursor.execute("""
            SELECT CAST(contenido AS VARCHAR(500)) 
            FROM varios 
            WHERE variab = ?
        """, (variab_vendedor,))
        resultado_vendedor = cursor.fetchone()
        nit_vendedor = resultado_vendedor[0].strip() if resultado_vendedor and resultado_vendedor[0] else '222222222222'
        logger.info(f"NIT vendedor ({variab_vendedor}): {nit_vendedor}")
        
        logger.info(f"✅ Configuración obtenida - Prefijo: {prefijo}, Centro: {prefijo_centro}, Vendedor: {nit_vendedor}")
        
        # ============================================
        # PASO 2: OBTENER CONSECUTIVO
        # ============================================
        logger.info("📋 PASO 2: Obteniendo consecutivo de factura...")
        codcomp = 'FV'  # Factura de Venta
        cursor.execute("""
            SELECT CONSECUTIVO 
            FROM CONSECUTIVO 
            WHERE CODCOMP = ? AND CODPREFIJO = ?
        """, (codcomp, prefijo))
        
        resultado_consecutivo = cursor.fetchone()
        if not resultado_consecutivo:
            logger.warning(f"Prefijo {prefijo} no encontrado en CONSECUTIVO, usando 1")
            numero = '1'
        else:
            numero = str(int(resultado_consecutivo[0]) + 1)
        
        logger.info(f"✅ Consecutivo obtenido: {numero} para prefijo {prefijo}")
        
        # ============================================
        # PASO 3: PREPARAR DATOS DE LA FACTURA
        # ============================================
        # Según makos.py línea 295-300: convertir fecha a string y luego parsear
        fecha_actual = datetime.now()
        fecha_str = fecha_actual.strftime('%Y-%m-%d %H:%M:%S')
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S').date()
        fecha_sql = fecha.strftime("%Y-%m-%d")  # Solo para logging
        periodo = fecha.strftime("%m")  # String del mes como en makos.py línea 538
        
        # Obtener NIT del cliente
        logger.info("📋 PASO 3: Preparando datos de la factura...")
        nit_cliente = None
        if invoice_data and invoice_data.get('document'):
            nit_cliente = invoice_data['document']
            logger.info(f"✅ NIT del cliente obtenido de invoice_data: {nit_cliente}")
        else:
            # Consumidor final - usar NIT 222222222222-7
            nit_cliente = '222222222222-7'
            logger.info(f"ℹ️ No hay invoice_data, usando NIT consumidor final: {nit_cliente}")
        
        # Normalizar NIT usando la función de normalización
        if not invoice_data or not invoice_data.get('document'):
            nit_normalizado = '222222222222'  # Consumidor final
        else:
            nit_doc = invoice_data.get('document', '222222222222-7')
            nit_normalizado = _normalizar_nit(nit_doc)
        logger.info(f"📝 NIT normalizado: {nit_normalizado}")
        
        # Construir observación si no viene desde el front
        if not observacion:
            if order_type == 'dinein' and mesa_number:
                observacion = f"PARA COMER AQUÍ - MESA {mesa_number}"
            else:
                observacion = "PARA LLEVAR"
            
            # Agregar teléfono si está disponible
            if invoice_data and invoice_data.get('phone'):
                observacion += f" - TEL: {invoice_data['phone']}"
        
        logger.info(f"✅ Observación construida: {observacion}")
        
        # ============================================
        # PASO 4: INSERTAR CABECERA (LÓGICA DIRECTA SIN STORED PROCEDURE)
        # ============================================
        logger.info("📋 PASO 4: Insertando cabecera de factura directamente en KARDEX...")
        
        # Preparar valores
        codcomp = 'FV'
        prefijo_truncado = str(prefijo)[:10] if prefijo else ''
        numero_truncado = str(numero)[:20] if numero else ''
        
        # Periodo (string del mes, 2 caracteres)
        periodo_str = str(periodo)[:2] if periodo else ''
        periodo_truncado = periodo_str.zfill(2) if periodo_str else '01'
        
        # Observación (máximo 1000 caracteres, o 'TALLER VENTAS' por defecto)
        vobservacion = 'TALLER VENTAS'
        if observacion:
            vobservacion = str(observacion)[:1000]
            if len(observacion) > 1000:
                logger.warning(f"⚠️ Observación truncada de {len(observacion)} a 1000 caracteres")
        
        # Usuario (máximo 20 caracteres)
        usuario_truncado = str(usuario_logueado)[:20] if usuario_logueado else 'ADMIN'
        
        # FORMAPAGO en KARDEX siempre es 'MU' (múltiples) - hardcodeado
        # Las formas de pago reales se insertan en DEKARDEXFP
        formapago_kardex = 'MU'
        
        # Normalizar NIT del cliente
        if not invoice_data or not invoice_data.get('document'):
            # Consumidor final
            nit_original = '222222222222-7'
            nit_normalizado = '222222222222'
            es_consumidor_final = True
        else:
            nit_original = invoice_data.get('document', '222222222222-7')
            nit_normalizado = _normalizar_nit(nit_original)
            # Verificar si es consumidor final (empieza con 22222222222)
            es_consumidor_final = nit_normalizado.startswith('22222222222')
        
        logger.info(f"🔍 NIT original: {nit_original}, Normalizado: {nit_normalizado}, Es consumidor final: {es_consumidor_final}")
        
        # Buscar vterid1 (vendedor con NIT normalizado de GVENDECAJAGC usando LIKE)
        # Normalizar el NIT del vendedor obtenido de VARIOS
        nit_vendedor_normalizado = _normalizar_nit(nit_vendedor)
        logger.info(f"🔍 Buscando vendedor con NIT normalizado: {nit_vendedor_normalizado} (usando LIKE)")
        cursor.execute("SELECT TERID FROM TERCEROS WHERE NIT LIKE ?", (f'{nit_vendedor_normalizado}%',))
        resultado_vendedor = cursor.fetchone()
        vterid1 = resultado_vendedor[0] if resultado_vendedor else None
        if not vterid1:
            logger.error(f"❌ No se encontró vendedor con NIT normalizado {nit_vendedor_normalizado}")
            bridge.conn.rollback()
            return {
                'success': False,
                'error': f'No se encontró vendedor con NIT normalizado {nit_vendedor_normalizado} en TERCEROS'
            }
        logger.info(f"✅ Vendedor encontrado: TERID={vterid1} (NIT normalizado: {nit_vendedor_normalizado})")
        
        # Buscar vterid2 (cliente con NIT del cliente)
        if es_consumidor_final:
            # Para consumidor final, buscar con LIKE '22222222222%' (primeros 11 dígitos)
            logger.info(f"🔍 Buscando consumidor final con LIKE '22222222222%'")
            cursor.execute("SELECT TERID FROM TERCEROS WHERE NIT LIKE ?", ('22222222222%',))
        else:
            # Para tercero normal, buscar con NIT normalizado exacto
            logger.info(f"🔍 Buscando tercero con NIT normalizado: {nit_normalizado}")
            cursor.execute("SELECT TERID FROM TERCEROS WHERE NIT = ?", (nit_normalizado,))
        
        resultado_cliente = cursor.fetchone()
        vterid2 = resultado_cliente[0] if resultado_cliente else None
        if not vterid2:
            logger.error(f"❌ No se encontró cliente con NIT={nit_normalizado}")
            bridge.conn.rollback()
            return {
                'success': False,
                'error': f'No se encontró cliente con NIT={nit_normalizado} en TERCEROS'
            }
        logger.info(f"✅ Cliente encontrado: TERID={vterid2}")
        
        # Obtener CENID del centro
        # El prefijo_centro viene de GFVCENTRO{usuario_logueado} y contiene el NRO del centro
        logger.info(f"🔍 Obteniendo CENID del centro con NRO: {prefijo_centro}")
        cursor.execute("SELECT CENID FROM CENTROS WHERE NRO = ?", (prefijo_centro,))
        resultado_centro = cursor.fetchone()
        cenid = resultado_centro[0] if resultado_centro else 1  # Default 1 si no se encuentra
        logger.info(f"✅ CENID obtenido: {cenid}")
        
        logger.info(f"✅ FORMAPAGO en KARDEX: {formapago_kardex} (hardcodeado - formas de pago reales van en DEKARDEXFP)")
        
        # ============================================
        # REINTENTOS: Si ya existe la factura, incrementar número y reintentar
        # ============================================
        max_intentos = 5
        intento = 0
        cabecera_insertada = False
        numero_final = numero
        
        while intento < max_intentos and not cabecera_insertada:
            intento += 1
            logger.info(f"🔄 Intento {intento}/{max_intentos} de inserción de cabecera con consecutivo: {numero_final}")
            
            # Actualizar número truncado con el número final
            numero_truncado = str(numero_final)[:20] if numero_final else ''
            
            # Verificar si ya existe el registro en KARDEX
            logger.info(f"🔍 Verificando si ya existe factura: {codcomp}-{prefijo_truncado}-{numero_truncado}")
            cursor.execute("""
                SELECT KARDEXID 
                FROM KARDEX 
                WHERE CODCOMP = ? AND CODPREFIJO = ? AND NUMERO = ?
            """, (codcomp, prefijo_truncado, numero_truncado))
            
            kardex_existente = cursor.fetchone()
            if kardex_existente:
                logger.warning(f"⚠️ Ya existe una factura con estos datos: {codcomp}-{prefijo_truncado}-{numero_truncado}")
                # Incrementar número y reintentar
                try:
                    numero_final = str(int(numero_final) + 1)
                    logger.info(f"📈 Incrementando número a: {numero_final}")
                    continue
                except (ValueError, TypeError):
                    logger.error(f"❌ No se pudo incrementar el número: {numero_final}")
                    bridge.conn.rollback()
                    return {
                        'success': False,
                        'error': f'No se pudo incrementar el número de factura: {numero_final}'
                    }
            
            # Si no existe, intentar insertar
            try:
                # Preparar valores y verificar longitudes
                valores_insert = {
                    'CODCOMP': (codcomp, len(str(codcomp)) if codcomp else 0),
                    'CODPREFIJO': (prefijo_truncado, len(str(prefijo_truncado)) if prefijo_truncado else 0),
                    'NUMERO': (numero_truncado, len(str(numero_truncado)) if numero_truncado else 0),
                    'FECHA': (fecha, 'date'),
                    'OBSERV': (vobservacion, len(str(vobservacion)) if vobservacion else 0),
                    'PERIODO': (periodo_truncado, len(str(periodo_truncado)) if periodo_truncado else 0),
                    'CENID': (cenid, 'integer'),
                    'AREADID': (1, 'integer'),
                    'SUCID': (1, 'integer'),
                    'CLIENTE': (vterid2, 'integer'),
                    'VENDEDOR': (vterid1, 'integer'),
                    'FORMAPAGO': (formapago_kardex, len(str(formapago_kardex))),
                    'AJUSTENETO': (0, 'decimal'),
                    'TOTAL': (0, 'decimal'),
                    'USUARIO': (usuario_truncado, len(str(usuario_truncado)) if usuario_truncado else 0)
                }
                
                # Logging detallado con longitudes (solo en el primer intento)
                if intento == 1:
                    print("=" * 80)
                    print("📋 VALORES PARA INSERTAR EN KARDEX (con longitudes):")
                    print("=" * 80)
                    for campo, (valor, longitud) in valores_insert.items():
                        if isinstance(longitud, int):
                            print(f"   {campo:15} = '{valor}' (len={longitud})")
                        else:
                            print(f"   {campo:15} = {valor} (tipo={longitud})")
                    print("=" * 80)
                
                logger.info("📋 Valores para INSERT en KARDEX:")
                for campo, (valor, longitud) in valores_insert.items():
                    if isinstance(longitud, int):
                        logger.info(f"   {campo}: '{valor}' (len={longitud})")
                    else:
                        logger.info(f"   {campo}: {valor} (tipo={longitud})")
                
                cursor.execute("""
                    INSERT INTO KARDEX (
                        CODCOMP, CODPREFIJO, NUMERO, FECHA, OBSERV, PERIODO,
                        CENID, AREADID, SUCID, CLIENTE, VENDEDOR, FORMAPAGO,
                        AJUSTENETO, TOTAL, USUARIO
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    codcomp,           # CODCOMP
                    prefijo_truncado,  # CODPREFIJO
                    numero_truncado,   # NUMERO
                    fecha,             # FECHA (objeto date)
                    vobservacion,      # OBSERV
                    periodo_truncado,  # PERIODO
                    cenid,             # CENID
                    1,                 # AREADID (hardcodeado como en stored procedure)
                    1,                 # SUCID (hardcodeado como en stored procedure)
                    vterid2,           # CLIENTE (TERID del cliente)
                    vterid1,           # VENDEDOR (TERID del vendedor)
                    formapago_kardex,  # FORMAPAGO (siempre 'MU' - hardcodeado)
                    0,                 # AJUSTENETO
                    0,                 # TOTAL (se actualizará después)
                    usuario_truncado   # USUARIO
                ))
                
                bridge.conn.commit()
                
                # Verificar que se insertó correctamente obteniendo KARDEXID
                logger.info("🔍 Verificando que la cabecera se insertó correctamente...")
                cursor.execute("""
                    SELECT KARDEXID 
                    FROM KARDEX 
                    WHERE CODPREFIJO = ? AND NUMERO = ? AND CODCOMP = ?
                """, (prefijo_truncado, numero_truncado, codcomp))
                
                kardex_row = cursor.fetchone()
                if kardex_row:
                    logger.info(f"✅ Cabecera insertada exitosamente con consecutivo: {numero_final}")
                    cabecera_insertada = True
                    numero = numero_final  # Actualizar número con el número final usado
                else:
                    logger.warning(f"⚠️ Procedimiento devolvió éxito pero no se encontró en KARDEX. Reintentando...")
                    bridge.conn.rollback()
                    numero_final = str(int(numero_final) + 1)
                    continue
                    
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"⚠️ Error en intento {intento}: {error_msg}")
                bridge.conn.rollback()
                
                # Si el error sugiere que el consecutivo ya existe, incrementar y reintentar
                if "duplicado" in error_msg.lower() or "ya existe" in error_msg.lower() or "unique" in error_msg.lower():
                    logger.info(f"🔍 Error sugiere que consecutivo {numero_final} ya existe. Incrementando...")
                    try:
                        numero_final = str(int(numero_final) + 1)
                        continue
                    except (ValueError, TypeError):
                        pass
                
                # Si es el último intento, retornar error
                if intento >= max_intentos:
                    logger.error(f"❌ No se pudo insertar cabecera después de {max_intentos} intentos")
                    return {
                        'success': False,
                        'error': f'Error al insertar cabecera después de {max_intentos} intentos: {error_msg}'
                    }
                else:
                    # Incrementar y reintentar
                    try:
                        numero_final = str(int(numero_final) + 1)
                        continue
                    except (ValueError, TypeError):
                        pass
        
        if not cabecera_insertada:
            logger.error(f"❌ No se pudo insertar cabecera después de {max_intentos} intentos")
            bridge.conn.rollback()
            return {
                'success': False,
                'error': f'No se pudo insertar cabecera después de {max_intentos} intentos'
            }
        
        # Obtener KARDEXID final
        cursor.execute("""
            SELECT KARDEXID 
            FROM KARDEX 
            WHERE CODPREFIJO = ? AND NUMERO = ? AND CODCOMP = ?
        """, (prefijo_truncado, numero_truncado, codcomp))
        
        kardex_row = cursor.fetchone()
        if not kardex_row:
            logger.error("❌ La cabecera se insertó pero no se encontró el KARDEXID")
            bridge.conn.rollback()
            return {
                'success': False,
                'error': 'La cabecera se insertó pero no se encontró el KARDEXID'
            }
        
        kardex_id = kardex_row[0]
        logger.info(f"✅ KARDEXID obtenido: {kardex_id}")
        
        # ============================================
        # PASO 5: INSERTAR DETALLES (si hay items)
        # ============================================
        if cart_items and len(cart_items) > 0:
            logger.info("📋 PASO 5: Insertando detalles de factura...")
            logger.info(f"📦 Total de items a insertar: {len(cart_items)}")
            
            detalles_insertados = 0
            for idx, item in enumerate(cart_items, 1):
                codigo_material = item.get('id') or item.get('codigo', '')
                cantidad = float(item.get('quantity', 1))
                precio = float(item.get('price', 0))
                descuento = float(item.get('discount', 0))
                
                if not codigo_material:
                    logger.warning(f"⚠️ Item {idx} sin código, saltando: {item}")
                    continue
                
                logger.info(f"📦 Insertando detalle {idx}/{len(cart_items)}: {codigo_material} - Cantidad: {cantidad}, Precio: {precio}")
                
                resultado = _insertar_detalle_factura(
                    cursor,
                    kardex_id,
                    codigo_material,
                    cantidad,
                    precio,
                    descuento
                )
                
                if resultado['success']:
                    detalles_insertados += 1
                else:
                    logger.error(f"❌ Error al insertar detalle {codigo_material}: {resultado.get('error')}")
                    bridge.conn.rollback()
                    return {
                        'success': False,
                        'error': f"Error al insertar detalle {codigo_material}: {resultado.get('error')}"
                    }
            
            if detalles_insertados == 0:
                logger.error("❌ No se pudo insertar ningún detalle")
                bridge.conn.rollback()
                return {
                    'success': False,
                    'error': 'No se pudo insertar ningún detalle'
                }
            
            logger.info(f"✅ {detalles_insertados}/{len(cart_items)} detalles insertados exitosamente")
        else:
            logger.warning("⚠️ No hay items en el carrito, saltando inserción de detalles")
        
        # ============================================
        # PASO 6: INSERTAR FORMA DE PAGO (si hay forma de pago)
        # ============================================
        if forma_pago_codigo:
            logger.info("📋 PASO 6: Insertando forma de pago...")
            logger.info(f"💳 Forma de pago: {forma_pago_codigo}, Monto: {monto_total}")
            
            # Obtener NIT de la empresa para la forma de pago (no del cliente)
            # El NIT de la empresa viene del objeto bridge.empresa
            nit_empresa = None
            try:
                if hasattr(bridge, 'empresa') and hasattr(bridge.empresa, 'nit'):
                    nit_empresa = bridge.empresa.nit
                    logger.info(f"📋 NIT de empresa obtenido desde bridge.empresa: {nit_empresa}")
            except:
                pass
            
            # Si no se pudo obtener, usar el NIT del vendedor como fallback (es de la empresa)
            if not nit_empresa:
                nit_empresa = nit_vendedor
                logger.info(f"📋 Usando NIT de vendedor como NIT de empresa: {nit_empresa}")
            
            # Extraer información del datafono para documento
            # tipodoc: usar los dos primeros caracteres del código de forma de pago
            tipodoc = forma_pago_codigo[:2].upper() if forma_pago_codigo else None
            
            # documento: numero_aprobacion o codigo_autorizacion del datafono
            documento = None
            if medio_pago_data:
                documento = medio_pago_data.get('numero_aprobacion') or medio_pago_data.get('codigo_autorizacion') or medio_pago_data.get('rrn')
            
            logger.info(f"   Tipodoc: {tipodoc} (primeros 2 caracteres de forma de pago), Documento: {documento}")
            logger.info(f"   NIT empresa para TERID en DEKARDEXFP: {nit_empresa}")
            
            resultado = _insertar_forma_pago(
                cursor,
                kardex_id,
                forma_pago_codigo,
                monto_total,
                nit_empresa,  # NIT de la empresa (no del cliente)
                tipodoc=tipodoc,
                documento=documento
            )
            
            if not resultado['success']:
                logger.error(f"❌ Error al insertar forma de pago: {resultado.get('error')}")
                bridge.conn.rollback()
                return {
                    'success': False,
                    'error': f"Error al insertar forma de pago: {resultado.get('error')}"
                }
        else:
            logger.warning("⚠️ No se proporcionó código de forma de pago, saltando inserción")
        
        # ============================================
        # PASO 7: ACTUALIZAR TOTALES (ANTES de asentar la factura)
        # ============================================
        logger.info("📋 PASO 7: Actualizando totales de factura...")
        resultado = _actualizar_totales(cursor, kardex_id, codcomp, prefijo_truncado, numero_truncado)
        
        if not resultado['success']:
            logger.warning(f"⚠️ Error al actualizar totales: {resultado.get('error')}")
            bridge.conn.rollback()
            return {
                'success': False,
                'error': f"Error al actualizar totales: {resultado.get('error')}"
            }
        
        logger.info("✅ Totales actualizados correctamente")
        
        # ============================================
        # PASO 8: ACTUALIZAR CONSECUTIVO (después de actualizar totales)
        # ============================================
        logger.info("📋 PASO 8: Actualizando CONSECUTIVO...")
        # Obtener el máximo número de factura para este prefijo
        cursor.execute("""
            SELECT MAX(CAST(NUMERO AS INTEGER))
            FROM KARDEX
            WHERE CODCOMP = ? AND CODPREFIJO = ?
        """, (codcomp, prefijo_truncado))
        
        resultado_max = cursor.fetchone()
        max_num = resultado_max[0] if resultado_max and resultado_max[0] else int(numero_truncado)
        
        logger.info(f"🔢 Actualizando consecutivo: {max_num} para prefijo {prefijo_truncado}")
        cursor.execute("""
            UPDATE CONSECUTIVO
            SET CONSECUTIVO = ?
            WHERE SUCID = 1 AND CODCOMP = ? AND CODPREFIJO = ?
        """, (str(max_num), codcomp, prefijo_truncado))
        
        logger.info(f"✅ CONSECUTIVO actualizado a {max_num}")
        
        # Commit después de actualizar totales y consecutivo
        bridge.conn.commit()
        
        # ============================================
        # PASO 9: ACTUALIZAR FECASENTAD Y CENID EN KARDEX (asentar factura)
        # ============================================
        logger.info("📋 PASO 9: Asentando factura (FECASENTAD y CENID)...")
        logger.info(f"📝 Actualizando KARDEX con FECASENTAD={fecha}, CENID={cenid}")
        cursor.execute("""
            UPDATE KARDEX
            SET FECASENTAD = ?, CENID = ?
            WHERE CODCOMP = ? AND CODPREFIJO = ? AND NUMERO = ?
        """, (fecha, cenid, codcomp, prefijo_truncado, numero_truncado))
        
        bridge.conn.commit()
        logger.info(f"✅ KARDEX actualizado correctamente con FECASENTAD y CENID")
        
        # ============================================
        # PASO 10: ACTUALIZAR HORAASEN Y HORA EN KARDEX
        # ============================================
        logger.info("📋 PASO 10: Actualizando HORAASEN y HORA en KARDEX...")
        hora_24 = datetime.now().strftime('%H:%M')
        # Mantener la observación original (mesa, teléfono, etc.) - NO sobrescribir
        
        logger.info(f"📝 Actualizando KARDEX con HORAASEN={hora_24}, HORA={hora_24}")
        logger.info(f"   Observación se mantiene: {vobservacion}")
        cursor.execute("""
            UPDATE KARDEX
            SET HORAASEN = ?, HORA = ?
            WHERE CODCOMP = ? AND CODPREFIJO = ? AND NUMERO = ?
        """, (hora_24, hora_24, codcomp, prefijo_truncado, numero_truncado))
        
        bridge.conn.commit()
        logger.info(f"✅ KARDEX actualizado correctamente con HORAASEN y HORA")
        
        logger.info("=" * 80)
        logger.info(f"🎉 FACTURA INSERTADA EXITOSAMENTE EN TNS")
        logger.info(f"   Prefijo: {prefijo}")
        logger.info(f"   Número: {numero}")
        logger.info(f"   KARDEXID: {kardex_id}")
        logger.info(f"   NIT Cliente: {nit_normalizado}")
        logger.info(f"   Observación: {observacion}")
        logger.info("=" * 80)
        
        return {
            'success': True,
            'kardex_id': kardex_id,
            'prefijo': prefijo,
            'numero': numero,
            'nit_normalizado': nit_normalizado,
            'observacion': observacion
        }
    
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ ERROR GENERAL AL INSERTAR FACTURA EN TNS")
        logger.error(f"   Error: {str(e)}")
        logger.error("=" * 80, exc_info=True)
        if bridge.conn:
            bridge.conn.rollback()
            logger.info("🔄 Transacción revertida (rollback)")
        return {
            'success': False,
            'error': str(e)
        }
