"""
Servicio para procesar facturas electrónicas DIAN
Adaptado del código j.py para funcionar en Django
"""
import logging
import json
import firebirdsql
import requests
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


def FECHA_ACTUAL():
    return datetime.now().strftime("%Y-%m-%d")


def FECHA_ANTERIOR():
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def HORA_ACTUAL():
    return datetime.now().strftime("%H:%M:%S")


def conectar_firebird(ruta_db, servidor_host='localhost', usuario='SYSDBA', password='masterkey'):
    """Conexión a base de datos Firebird"""
    try:
        return firebirdsql.connect(
            host=servidor_host,
            database=ruta_db,
            user=usuario,
            password=password,
            charset='ISO8859_1'
        )
    except Exception as e:
        logger.error(f"Error conectando a Firebird: {e}")
        raise Exception(f"Error de conexión: {str(e)}")


def calculate_dv(nit):
    """Calcula dígito de verificación para NIT colombiano"""
    try:
        FACTORES = [71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3]
        
        nit_str = str(nit).strip()
        nit_digits = [int(d) for d in nit_str if d.isdigit()]

        padding = len(FACTORES) - len(nit_digits)
        if padding > 0:
            nit_digits = [0] * padding + nit_digits
        elif padding < 0:
            nit_digits = nit_digits[-len(FACTORES):]

        total = sum(d * f for d, f in zip(nit_digits, FACTORES))
        resto = total % 11
        dv = 0 if resto == 0 else (11 - resto if resto > 1 else 1)
        return str(dv)
    except Exception as e:
        logger.warning(f"Error calculando DV: {e}")
        return '0'


def parse_fecha(fecha_raw):
    """Parseo seguro de fechas"""
    try:
        if isinstance(fecha_raw, datetime):
            return fecha_raw.strftime("%Y-%m-%d")
        elif isinstance(fecha_raw, str) and fecha_raw.strip():
            return datetime.strptime(fecha_raw.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
        else:
            return FECHA_ACTUAL()
    except Exception:
        return FECHA_ACTUAL()


def consultar_medios_pago(conexion, kardex_id):
    """Consulta códigos de medios de pago del kardex, ordenados por valor descendente"""
    sql = """
        SELECT mp.codigo
        FROM dekardexfp dkfp
        INNER JOIN FORMAPAGO fp ON fp.formapagoid = dkfp.formapagoid
        INNER JOIN mediopago mp ON mp.mediopagoid = fp.mediopagoid
        WHERE dkfp.kardexid = ?
        ORDER BY dkfp.valor DESC
    """
    cursor = conexion.cursor()
    cursor.execute(sql, (kardex_id,))
    resultado = [fila[0] for fila in cursor.fetchall()]
    if resultado:
        return resultado[0]
    return 47  # Valor por defecto


def consultar_kardex(conexion, kardex_id):
    """Consulta principal del kardex"""
    cursor = conexion.cursor()

    # Verificar si campo HE existe
    cursor.execute("""
        SELECT COUNT(*) FROM rdb$relation_fields 
        WHERE rdb$relation_name = 'KARDEX' AND rdb$field_name = 'HE'
    """)
    he_existe = cursor.fetchone()[0] > 0

    campos_base = """
        k.kardexid, t.dv,
        iif(P.Contingencia='S', 3, 
            case k.codcomp 
                when 'FV' then '1' 
                when 'DV' then '4' 
                when 'FC' then '11' 
                when 'DC' then '13' 
                else '1' 
            end) tipoDocumento,
        k.numero, k.fecha, k.hora, k.formapago, k.plazodias, k.fecvence,
        k.vrbase, k.vriva,
        iif(k.retcree=0, 
            k.fpcontado + k.fpcredito + k.vrrfte + k.vrrica + k.vrdctos,
            iif((k.fpcontado + k.fpcredito + k.vrrcree) = k.neto,
                k.neto + k.vrrfte + k.vrrica,
                (k.fpcontado + k.fpcredito + k.vrrfte + k.vrrica)
            )
        ) total,
        iif(p.preimp='', p.codprefijo, p.preimp) as prefix,
        t.nittri as nit, t.nombre, 
        rpad(substring(t.telef1 from 1 for 10), 10, '0') as telef1,
        iif(t.direcc1 is null, 'null', t.direcc1) as direcc1,
        t.email,
        case t.tipodociden 
            when 'U' then '1' 
            when 'T' then '2' 
            when 'C' then '3' 
            when 'TE' then '4' 
            when 'E' then '5' 
            when 'N' then '6' 
            when 'F' then '7' 
            when 'D' then '8' 
            when 'O' then '9' 
            when 'NUIP' then '10' 
            when 'P' then '11' 
            when 'L' then '12' 
            else '3' 
        end as tipodociden,
        case t.natjuridica 
            when 'J' then '1' 
            when 'N' then '2' 
            else '1' 
        end as tipoOrganizacion,
        c.codmin as municipio, p.resolucion, p.contingencia, p.prefe,
        k.NUMEROFACTANT numerodev, k2.cufe cufedev, k2.fecha fechadev,
        iif(m.codfactelect is null, 2, m.codfactelect) motivo,
        k.observ as notes,
        iif(k.exportacion is null, 'N', k.exportacion) as exportacion,
        k.factorconv,
        c.nombre as ciudad, c.departamento, ps.country_id,
        iif(k.estadodian is null, '', k.estadodian) as estadodian,
        p.numfinfacele
    """

    campos_health = "'' as health" if not he_existe else "iif(k.he is null, '', k.he) as health"

    sql = f"""
    SELECT DISTINCT {campos_base}, {campos_health}
    FROM 
        kardex k
        INNER JOIN prefijo p ON p.codprefijo = k.codprefijo
        INNER JOIN terceros t ON t.terid = k.cliente
        INNER JOIN ciudane c ON c.ciudaneid = t.ciudaneid
        LEFT JOIN pais ps ON ps.paisid = c.paisid
        LEFT JOIN motivodev m ON m.motivodevid = k.motivodevid
        LEFT JOIN kardexself ks ON ks.kardexid = k.kardexid
        LEFT JOIN kardex k2 ON k2.numero = k.NUMEROFACTANT
    WHERE 
        t.nit <> 'ANULA' 
        AND k.kardexid = ?
        AND k.fecasentad IS NOT NULL 
        AND k.codcomp IN ('FV', 'FC', 'DV', 'DC')
    order by K2.CUFE DESC
    """

    cursor.execute(sql, (kardex_id,))
    resultado = cursor.fetchone()
    return resultado


def obtener_configuracion(conexion):
    """Obtiene configuración dinámica de la BD"""
    claves = [
        'TOKENDIANVM', 'ENDPOINTDIANVM', 'GTIPIMPVM', 'GTIPCOTVM',
        'FOOTERDIANVM', 'DIANVMEMAIL', 'DIANVMADDRESS', 'CABECERADIANVM', 'ZESEVM'
    ]

    config = {}
    cursor = conexion.cursor()

    for clave in claves:
        sql = "SELECT CAST(contenido AS VARCHAR(500)) FROM varios WHERE variab = ?"
        try:
            cursor.execute(sql, (clave,))
            fila = cursor.fetchone()
            valor = fila[0] if fila and fila[0] else None
            config[clave] = valor
        except Exception as e:
            logger.error(f"Error al obtener '{clave}': {e}")
            config[clave] = None

    return config


def actualizar_kardex(conexion, kardex_id, cufe, mensaje, estado_dian):
    """Actualiza el kardex con la respuesta de la DIAN"""
    if estado_dian != 'EXITOSA':
        cufe = ''
        sql = """
            UPDATE KARDEX 
            SET 
                MENSAJEFE = ?,
                ESTADODIAN = ?
            WHERE KARDEXID = ?
        """
        cursor = conexion.cursor()
        cursor.execute(sql, (mensaje, estado_dian, kardex_id))
        conexion.commit()
    else:
        sql = """
        UPDATE KARDEX 
        SET 
            CUFE = ?,
            MENSAJEFE = ?,
            ESTADODIAN = ?
        WHERE KARDEXID = ?
        """
        cursor = conexion.cursor()
        cursor.execute(sql, (cufe, mensaje, estado_dian, kardex_id))
        conexion.commit()

    logger.info(f"Kardex actualizado: CUFE={cufe}, Estado={estado_dian}, Mensaje={mensaje}")


def consultar_tax_totals(conexion, kardex_id):
    """Consulta totales de impuestos"""
    sql = """
        SELECT
            CASE WHEN dk.precioiconsumo > 0 THEN '4' ELSE '1' END AS tax_id,
            CASE WHEN dk.precioiconsumo > 0 THEN 8 ELSE dk.porciva END AS percent,
            ROUND(SUM(dk.preciobase * dk.canlista), 2) AS taxable_amount,
            ROUND(SUM(CASE
                WHEN dk.precioiconsumo > 0 THEN dk.precioiconsumo * dk.canlista
                ELSE dk.precioiva * dk.canlista
            END), 2) AS tax_amount
        FROM dekardex dk
        WHERE dk.kardexid = ?
        GROUP BY 
            CASE WHEN dk.precioiconsumo > 0 THEN '4' ELSE '1' END,
            CASE WHEN dk.precioiconsumo > 0 THEN 8 ELSE dk.porciva END
    """
    cursor = conexion.cursor()
    cursor.execute(sql, (kardex_id,))
    return cursor.fetchall()


def consultar_holding_tax_totals(conexion, kardex_id):
    """Consulta impuestos de retención"""
    sql = """
    SELECT
        C.DESCRIP, C.CODIGO, C.RETTIPO,
        CASE
            WHEN C.RETTIPO = 'I' THEN 5
            WHEN C.RETTIPO = 'R' THEN 6
            WHEN C.RETTIPO = 'C' THEN 7
            ELSE NULL
        END AS tipo_codigo,
        SUM(DKD.VALORDTO) AS VALOR,
        SUM(DKD.BASERETD) AS BASE,
        MIN(CASE
            WHEN C.RETTIPO = 'C' THEN DKD.PORCRETD / 10
            ELSE DKD.PORCRETD
        END) AS PORC
    FROM DEKARDEXDTO DKD
    INNER JOIN CONCEPTO C ON C.CONCID = DKD.CONCID
    WHERE DKD.KARDEXID = ?
    GROUP BY C.DESCRIP, C.CODIGO, C.RETTIPO
    """
    cursor = conexion.cursor()
    cursor.execute(sql, (kardex_id,))
    return cursor.fetchall()


def consultar_items(conexion, kardex_id):
    """Consulta ítems del kardex"""
    sql = """
        SELECT 
            c.codigo as unidad, 
            dk.canlista,
            round((dk.preciobase*dk.canlista),2) as parcvta,
            IIF(dk.precioiconsumo > 0, 8, dk.porciva) as porciva,
            dk.descuento, 
            round(dk.precioiva*dk.canlista,2) as precioiva,
            round(dk.precioiconsumo*dk.canlista,2) as precioico,
            round(dk.preciovta,2) as vrbase,
            m.descrip, 
            m.codigo,
            iif(dk.precioiconsumo>0,'4','1') as taxid 
        FROM material m 
        INNER JOIN dekardex dk ON dk.matid=m.matid 
        LEFT JOIN codigosunidades c ON c.codunidadid=m.codunidadid 
        WHERE dk.kardexid=? AND dk.parcvta>0
    """
    cursor = conexion.cursor()
    cursor.execute(sql, (kardex_id,))
    return cursor.fetchall()


ENDPOINTS = {
    'FV': {'default': 'invoice', 'ND': 'debit-note'},
    'FC': {'default': 'support-document', 'DS': 'support-document'},
    'DV': {'default': 'credit-note'},
    'DC': {'default': 'sd-credit-note', 'DS': 'sd-credit-note'}
}


def obtener_endpoint(codcomp, codprefijo):
    """Obtiene endpoint según tipo de documento"""
    endpoint_config = ENDPOINTS.get(codcomp, ENDPOINTS['FV'])
    if isinstance(endpoint_config, dict):
        return endpoint_config.get(codprefijo, endpoint_config['default'])
    return endpoint_config


def procesar_respuesta_api(respuesta):
    """Procesa respuesta de la API DIAN"""
    resultado = {
        'success': respuesta.get('success'),
        'message': respuesta.get('message', ''),
        'cufe': respuesta.get("cufe") or respuesta.get("cuds") or respuesta.get("cude", ""),
        'QRStr': respuesta.get('QRStr', ''),
        'dian_response': {
            'IsValid': False,
            'StatusCode': '',
            'StatusDescription': '',
            'StatusMessage': '',
            'Rechazos': [],
            'Notificaciones': []
        }
    }

    if resultado['message'] == 'Este documento ya fue enviado anteriormente, se registra en la base de datos.':
        resultado['dian_response']['IsValid'] = True

    # Manejo de errores 422
    if 'errors' in respuesta or respuesta.get('status_code') == 422:
        errors = respuesta.get('errors', {})
        rechazos = []

        for campo, mensajes in errors.items():
            if isinstance(mensajes, list):
                rechazos.extend(mensajes)
            elif isinstance(mensajes, dict):
                for subcampo, submensajes in mensajes.items():
                    if isinstance(submensajes, list):
                        rechazos.extend(submensajes)
                    else:
                        rechazos.append(str(submensajes))
            else:
                rechazos.append(str(mensajes))

        resultado['dian_response']['Rechazos'] = rechazos
        resultado['dian_response']['StatusCode'] = '422'
        resultado['dian_response']['StatusDescription'] = 'Error de validación'
        resultado['message'] = "Errores: " + " | ".join(rechazos)
        resultado['success'] = False
        return resultado

    # Procesar respuesta DIAN
    if 'ResponseDian' in respuesta:
        dian = respuesta['ResponseDian']
        try:
            if 'Envelope' in dian and 'Body' in dian['Envelope']:
                send_result = dian['Envelope']['Body']['SendBillSyncResponse']['SendBillSyncResult']
            elif 'Body' in dian:
                send_result = dian['Body']['SendBillSyncResponse']['SendBillSyncResult']
            else:
                send_result = dian

            resultado['dian_response']['IsValid'] = send_result.get('IsValid', 'false') == 'true'
            resultado['dian_response']['StatusCode'] = send_result.get('StatusCode', '')
            resultado['dian_response']['StatusDescription'] = send_result.get('StatusDescription', '')
            resultado['dian_response']['StatusMessage'] = send_result.get('StatusMessage', '')

            error_msgs = []
            if 'ErrorMessage' in send_result:
                em = send_result['ErrorMessage']
                if isinstance(em, dict) and 'string' in em:
                    error_msgs = em['string'] if isinstance(em['string'], list) else [em['string']]
                elif isinstance(em, list):
                    error_msgs = em
                elif isinstance(em, str):
                    error_msgs = [em]

            for msg in error_msgs:
                if isinstance(msg, str):
                    if 'Rechazo:' in msg:
                        resultado['dian_response']['Rechazos'].append(msg.split('Rechazo:', 1)[-1].strip())
                    elif 'Notificación:' in msg:
                        resultado['dian_response']['Notificaciones'].append(msg.split('Notificación:', 1)[-1].strip())

        except Exception as e:
            logger.error(f"Error procesando respuesta DIAN: {e}")

    # Validar documento previamente procesado
    for rechazo in resultado['dian_response']['Rechazos']:
        if "Documento procesado anteriormente." in rechazo:
            resultado['dian_response']['IsValid'] = True
            break

    return resultado


def enviar_documento_api(documento_json, codcomp, codprefijo, base_url, token):
    """Envía documento a la API DIAN"""
    endpoint = obtener_endpoint(codcomp, codprefijo)
    url = f"{base_url}/{endpoint}" if not base_url.endswith('/') else f"{base_url}{endpoint}"

    auth_token = f"Bearer {token}"

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': auth_token
    }

    logger.info(f"Enviando a: {url} - Tipo: {codcomp}-{codprefijo}")

    try:
        response = requests.post(url, headers=headers, json=documento_json, timeout=30)
        response.raise_for_status()
        response_data = response.json()

        logger.info("Respuesta exitosa de DIAN")
        return {
            'success': True,
            'status_code': response.status_code,
            'response': response_data,
            'processed_response': procesar_respuesta_api(response_data),
            'endpoint_used': url
        }
    except requests.exceptions.RequestException as e:
        error_data = {
            'success': False,
            'error': str(e),
            'status_code': getattr(e.response, 'status_code', None),
            'endpoint_used': url
        }

        if getattr(e.response, 'status_code', None) == 422:
            try:
                error_data['response'] = e.response.json()
            except ValueError:
                error_data['response'] = {'message': str(e), 'errors': {'validation': [str(e.response.text)]}}

        if 'response' in error_data:
            error_data['processed_response'] = procesar_respuesta_api(error_data['response'])
        else:
            error_data['processed_response'] = procesar_respuesta_api({'errors': {'general': [str(e)]}})

        logger.error(f"Error enviando a DIAN: {e}")
        return error_data


def generar_json(datos_kardex, tax_totals, holding_tax_totals, items, config, medio_pago_id):
    """Genera JSON para envío a DIAN (versión simplificada del código original)"""
    # Esta función es muy larga, la adaptaremos del código original
    # Por ahora, retornamos estructura básica
    HEADNOTE = config.get('CABECERADIANVM') or ""
    FOOTNOTE = config.get('FOOTERDIANVM') or ""
    ZESE = config.get('ZESEVM') or ""

    def safe_str(value, default=""):
        return str(value).strip() if value is not None else default

    def safe_float(value, default=0.0):
        try:
            return round(float(value or 0), 2)
        except:
            return default

    def safe_currency(value, default="0.00"):
        try:
            return "{0:.2f}".format(float(value or 0))
        except:
            return default

    def safe_int(value, default=0):
        try:
            return int(value)
        except:
            return default

    try:
        # Procesar tax_totals
        processed_taxes = []
        total_impuestos = 0.0
        total_base = 0.0

        tax_totals = [tax for tax in tax_totals if float(tax[2] or 0) > 0]
        for tax in tax_totals:
            tax_base = float(tax[2] or 0)
            tax_amount = float(tax[3] or 0)

            processed_taxes.append({
                "tax_id": safe_str(tax[0], "4"),
                "tax_amount": safe_currency(tax_amount),
                "percent": safe_currency(tax[1]),
                "taxable_amount": safe_currency(tax_base)
            })

            total_impuestos += tax_amount
            total_base += tax_base

        # Procesar holding taxes
        processed_holding_taxes = []
        holding_tax_totals = [ht for ht in holding_tax_totals if float(ht[5] or 0) > 0]
        if holding_tax_totals:
            for holding_tax in holding_tax_totals:
                if holding_tax[3] is not None:
                    processed_holding_taxes.append({
                        "tax_id": int(holding_tax[3]),
                        "tax_amount": safe_currency(holding_tax[4]),
                        "percent": safe_currency(holding_tax[6]),
                        "taxable_amount": safe_currency(holding_tax[5])
                    })

        # Calcular totales
        line_extension = safe_currency(total_base)
        tax_exclusive = safe_currency(total_base)
        tax_inclusive = safe_currency(total_base + total_impuestos)

        # Procesar ítems
        invoice_lines = []
        for item in items:
            invoice_lines.append({
                "unit_measure_id": 70,
                "invoiced_quantity": safe_currency(item[1], "1.00"),
                "line_extension_amount": safe_currency(item[2]),
                "free_of_charge_indicator": False,
                "allowance_charges": [{
                    "charge_indicator": False,
                    "allowance_charge_reason": "DESCUENTO GENERAL",
                    "amount": "0.00",
                    "base_amount": safe_currency(item[2])
                }],
                "tax_totals": [{
                    "tax_id": safe_int(item[10]),
                    "tax_amount": safe_currency(item[6] if item[6] != 0 else item[5]),
                    "taxable_amount": safe_currency(item[2]),
                    "percent": safe_currency(item[3])
                }],
                "description": safe_str(item[8]),
                "code": safe_str(item[9]),
                "type_item_identification_id": 4,
                "price_amount": safe_str(int(safe_float(item[2]) / safe_float(item[1], 1) * 100) / 100.0),
                "base_quantity": 1,
                "reference_price_id": 1
            })

        # Extraer datos del kardex
        numero_documento = safe_int(datos_kardex[3])
        nit, dv = datos_kardex[13].split('-') if '-' in safe_str(datos_kardex[13]) else (safe_str(datos_kardex[13]), '0')
        dv = calculate_dv(nit)

        # Construir documento base
        documento = {
            "prefix": safe_str(datos_kardex[12]),
            "number": numero_documento,
            "type_document_id": safe_int(datos_kardex[2], 1),
            "resolution_number": safe_str(datos_kardex[21]),
            "sendmail": True,
            "notes": safe_str(datos_kardex[28], ""),
            "date": FECHA_ACTUAL(),
            "time": HORA_ACTUAL(),
            "sendmailtome": False,
            "with_holding_tax_total": processed_holding_taxes,
            "customer": {
                "identification_number": nit,
                "dv": safe_int(dv),
                "name": safe_str(datos_kardex[14]),
                "phone": safe_str(datos_kardex[15], "0000000000"),
                "address": safe_str(datos_kardex[16], "NA"),
                "email": safe_str(datos_kardex[17], "consumidor@gmail.com"),
                "merchant_registration": "0000000-00",
                "type_document_identification_id": safe_int(datos_kardex[18], 6),
                "type_organization_id": safe_int(datos_kardex[19], 1),
                "municipality_id": safe_int(datos_kardex[20], 780),
                "type_regime_id": 1
            },
            "payment_form": {
                "payment_form_id": 1 if safe_str(datos_kardex[6]).strip().upper() != 'CR' else 2,
                "payment_method_id": medio_pago_id,
                "payment_due_date": FECHA_ACTUAL(),
                "duration_measure": safe_int(datos_kardex[7], 0)
            },
            "allowance_charges": [],
            "legal_monetary_totals": {
                "line_extension_amount": line_extension,
                "tax_exclusive_amount": tax_exclusive,
                "tax_inclusive_amount": tax_inclusive,
                "allowance_total_amount": "0.00",
                "charge_total_amount": "0.00",
                "payable_amount": tax_inclusive
            },
            "tax_totals": processed_taxes,
            "invoice_lines": invoice_lines
        }

        # Agregar notas según tipo de documento
        tipo_documento = safe_int(datos_kardex[2], 1)
        documentos_permitidos = [1, 4]

        if HEADNOTE.strip() and tipo_documento in documentos_permitidos:
            documento["head_note"] = HEADNOTE.strip()

        if FOOTNOTE.strip() and tipo_documento in documentos_permitidos:
            documento["foot_note"] = FOOTNOTE.strip()

        if ZESE.strip() and tipo_documento in documentos_permitidos:
            documento["seze"] = ZESE.strip()

        if datos_kardex[18] != 6 or datos_kardex[18] != "6":
            documento.pop("dv", None)

        # Manejar campo health_fields
        if len(datos_kardex) > 36 and datos_kardex[36]:
            try:
                parsed = json.loads(datos_kardex[36])
                documento["health_fields"] = parsed.get("health_fields", {})
            except json.JSONDecodeError:
                documento["health_fields"] = {}

        # Manejar notas crédito/débito (lógica simplificada)
        if safe_int(datos_kardex[2]) == 11 or safe_int(datos_kardex[2]) == 13 or safe_int(datos_kardex[2]) == 4:
            if safe_int(datos_kardex[2]) == 11 or safe_int(datos_kardex[2]) == 13:
                documento["seller"] = documento.pop("customer")
                documento["seller"]["postal_zone_code"] = "54001"

            if safe_str(datos_kardex[25]):
                documento["billing_reference"] = {
                    "number": safe_str(datos_kardex[24]),
                    "uuid": safe_str(datos_kardex[25]),
                    "issue_date": parse_fecha(datos_kardex[26]),
                }

            if (safe_int(datos_kardex[2]) == 13 or safe_int(datos_kardex[2]) == 4):
                if "invoice_lines" in documento:
                    documento["credit_note_lines"] = documento.pop("invoice_lines")

        return documento

    except Exception as e:
        import traceback
        error_msg = f"Error generando JSON: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return {"error": error_msg}


def procesar_factura_dian(nit_normalizado, kardex_id, empresa_servidor_id=None):
    """
    Procesa una factura electrónica DIAN
    
    Args:
        nit_normalizado: NIT de la empresa (normalizado, sin puntos ni guiones)
        kardex_id: ID del documento a procesar
        empresa_servidor_id: ID de la empresa (opcional, se busca si no se proporciona)
    
    Returns:
        dict con resultado del procesamiento
    """
    from ..models import EmpresaServidor
    from .tns_bridge import TNSBridge
    
    conexion = None
    
    try:
        # 1. Buscar empresa por NIT normalizado
        if empresa_servidor_id:
            empresa = EmpresaServidor.objects.get(id=empresa_servidor_id)
        else:
            # Buscar por NIT normalizado y obtener el año fiscal más reciente
            empresas = EmpresaServidor.objects.filter(
                nit__iregex=r'^[0-9]+'  # Filtrar por NIT que empiece con números
            )
            
            # Normalizar NITs y encontrar coincidencia
            empresa = None
            for emp in empresas:
                nit_emp_normalizado = ''.join(filter(str.isdigit, emp.nit))
                if nit_emp_normalizado == nit_normalizado:
                    if empresa is None or emp.anio_fiscal > empresa.anio_fiscal:
                        empresa = emp
            
            if not empresa:
                return {
                    'success': False,
                    'error': f'Empresa con NIT {nit_normalizado} no encontrada'
                }
        
        # 2. Construir ruta completa de la BD
        # La ruta base ya incluye el año fiscal, ejemplo: C:\TNS\EMPRESA\2024\EMPRESA2024.GDB
        ruta_db = empresa.ruta_base
        
        # 3. Conectar a Firebird usando TNSBridge (ya maneja pool y credenciales)
        # TNSBridge maneja automáticamente la conexión y el pool
        bridge = TNSBridge(empresa)
        bridge.connect()
        
        # Usar la conexión del bridge directamente
        conexion = bridge.conn
        
        # 4. Consultar datos básicos del kardex
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT k.codcomp, COALESCE(NULLIF(p.preimp, ''), p.codprefijo), k.numero,
                   CASE WHEN P.Contingencia='S' THEN 3
                        WHEN k.codcomp = 'FV' THEN 1 
                        WHEN k.codcomp = 'DV' THEN 4 
                        WHEN k.codcomp = 'FC' THEN 11 
                        WHEN k.codcomp = 'DC' THEN 13 
                        ELSE 1 END
            FROM kardex k
            INNER JOIN prefijo p ON p.codprefijo = k.codprefijo
            WHERE k.kardexid = ?
        """, (kardex_id,))
        
        datos_basicos = cursor.fetchone()
        if not datos_basicos:
            return {
                'success': False,
                'error': f'No se encontró el kardex {kardex_id}'
            }
        
        codcomp, codprefijo, numero, tipo_doc = datos_basicos
        
        logger.info(f"Procesando: {codcomp}-{codprefijo}{numero} (ID: {kardex_id})")
        
        # 5. Consultar datos principales
        datos_kardex = consultar_kardex(conexion, kardex_id)
        if not datos_kardex:
            return {
                'success': False,
                'error': 'No se encontraron datos para el kardex'
            }
        
        # 6. Obtener configuración
        config = obtener_configuracion(conexion)
        TOKEN = config.get('TOKENDIANVM')
        BASE_URL = config.get('ENDPOINTDIANVM') or "http://45.149.204.184:81/api/ubl2.1"
        
        if not TOKEN:
            return {
                'success': False,
                'error': 'Token no configurado (TOKENDIANVM)'
            }
        
        # 7. Consultar datos adicionales
        tax_totals = consultar_tax_totals(conexion, kardex_id)
        holding_tax_totals = consultar_holding_tax_totals(conexion, kardex_id)
        items = consultar_items(conexion, kardex_id)
        medio_pago_id = consultar_medios_pago(conexion, kardex_id)
        
        # 8. Generar JSON
        documento_json = generar_json(
            datos_kardex, tax_totals, holding_tax_totals, items, config, medio_pago_id
        )
        
        if "error" in documento_json:
            return {
                'success': False,
                'error': documento_json['error']
            }
        
        # 9. Enviar a API DIAN
        resultado_api = enviar_documento_api(
            documento_json, codcomp, codprefijo, BASE_URL, TOKEN
        )
        
        if not resultado_api.get('processed_response'):
            resultado_api['processed_response'] = procesar_respuesta_api(
                resultado_api.get('response', {})
            )
        
        respuesta_procesada = resultado_api['processed_response']
        
        # 10. Actualizar kardex
        mensaje_actualizacion = respuesta_procesada.get('message', '')
        
        if respuesta_procesada['dian_response']['Rechazos']:
            mensaje_actualizacion = " | ".join(respuesta_procesada['dian_response']['Rechazos'])
        elif not respuesta_procesada.get('success') and resultado_api.get('error'):
            mensaje_actualizacion = resultado_api['error']
        
        estado_dian = 'EXITOSA' if respuesta_procesada.get('dian_response', {}).get('IsValid') else 'NO EXITOSA'
        
        actualizar_kardex(
            conexion,
            kardex_id,
            respuesta_procesada.get('cufe', ''),
            mensaje_actualizacion[:250],
            estado_dian
        )
        
        if respuesta_procesada.get('dian_response', {}).get('IsValid'):
            return {
                'success': True,
                'cufe': respuesta_procesada.get('cufe', ''),
                'mensaje': 'Documento procesado exitosamente'
            }
        else:
            return {
                'success': False,
                'error': mensaje_actualizacion[:100],
                'cufe': respuesta_procesada.get('cufe', '')
            }
    
    except Exception as e:
        import traceback
        error_msg = f"Error general: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        
        # Intentar actualizar kardex con error
        if conexion:
            try:
                actualizar_kardex(conexion, kardex_id, '', error_msg[:250], 'NO EXITOSA')
            except:
                pass
        
        return {
            'success': False,
            'error': error_msg
        }
    
    finally:
        # TNSBridge maneja el cierre de conexiones y el pool
        if 'bridge' in locals():
            try:
                bridge.close()
            except:
                pass

