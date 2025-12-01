import argparse
from email.message import EmailMessage
import json
import smtplib
import firebirdsql
import requests
from datetime import datetime, timedelta
import sys
from io import StringIO
import ctypes
import socket
import threading
import time

INTERACTIVE_MODE = False

# ==================== POOL DE CONEXIONES ====================


class ConnectionPool:
    def __init__(self, max_connections=5):
        self.pool = {}
        self.max_connections = max_connections
        self.lock = threading.Lock()

    def get_connection(self, db_path):
        """Obtiene conexión del pool o crea nueva"""
        with self.lock:
            if db_path not in self.pool:
                self.pool[db_path] = []

            if self.pool[db_path]:
                print(f"🔁 Reutilizando conexión de pool para: {db_path}")
                return self.pool[db_path].pop()
            else:
                print(f"🆕 Creando nueva conexión para: {db_path}")
                return conectar_firebird(db_path)

    def release_connection(self, db_path, connection):
        """Libera conexión al pool"""
        with self.lock:
            if connection:
                if len(self.pool.get(db_path, [])) < self.max_connections:
                    self.pool[db_path].append(connection)
                    print(f"🔄 Conexión liberada al pool: {db_path}")
                else:
                    connection.close()
                    print(f"🔒 Conexión cerrada (pool lleno): {db_path}")


# Crear pool global
connection_pool = ConnectionPool()

# Nueva función para usar pool


def obtener_conexion(db_path):
    """Obtiene conexión del pool"""
    return connection_pool.get_connection(db_path)


def liberar_conexion(db_path, conexion):
    """Libera conexión al pool"""
    connection_pool.release_connection(db_path, conexion)


def mostrar_alerta(titulo, mensaje):
    """Muestra alerta visual o en consola"""
    try:
        ctypes.windll.user32.MessageBoxW(0, mensaje, titulo, 1)
    except:
        print(f"⚠️ {titulo}: {mensaje}")


# Configuración general
DEBUG_MODE = True


def FECHA_ACTUAL():
    return datetime.now().strftime("%Y-%m-%d")

def FECHA_ANTERIOR():
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

def HORA_ACTUAL():
    return datetime.now().strftime("%H:%M:%S")


# Configuración de endpoints dinámicos
ENDPOINTS = {
    'FV': {'default': 'invoice', 'ND': 'debit-note'},
    'FC': {'default': 'support-document', 'DS': 'support-document'},
    'DV': {'default': 'credit-note'},
    'DC': {'default': 'sd-credit-note', 'DS': 'sd-credit-note'}
}


class Tee:
    """Clase para logging simultáneo en consola y archivo"""

    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files:
            try:
                f.write(obj)
                f.flush()
            except ValueError as e:
                if "I/O operation on closed file" in str(e):
                    # Remover el archivo cerrado de la lista
                    self.files = [file for file in self.files if file != f]
                else:
                    raise

    def flush(self):
        for f in self.files:
            f.flush()


def setup_logging(codcomp, codprefijo, numero):
    """Configura logging para documento específico - VERSIÓN SEGURA"""
    filename = f"{codcomp}-{codprefijo}{numero}.log"
    log_file = open(filename, 'w', encoding='utf-8')
    
    # Crear Tee solo para este proceso, sin modificar sys.stdout globalmente
    tee = Tee(sys.stdout, log_file)
    
    return log_file, tee  # Devolvemos el objeto Tee en lugar del stdout original


def restore_logging(log_file, tee):
    """Restaura recursos de logging - VERSIÓN SEGURA"""
    # No necesitamos restaurar sys.stdout ya que no lo modificamos
    log_file.close()
    # Limpiar referencia al archivo cerrado en el Tee
    tee.files = [f for f in tee.files if f != log_file]


def log_consulta(nombre_consulta, sql, resultados):
    """Log de consultas SQL para debugging"""
    if DEBUG_MODE:
        print(f"\n🔍 CONSULTA: {nombre_consulta}")
        print("SQL:", sql.strip())
        print("\n📊 RESULTADOS:")
        if resultados:
            if isinstance(resultados, list):
                if len(resultados) > 0:
                    headers = [
                        f"Columna {i+1}" for i in range(len(resultados[0]))]
                    print(" | ".join(headers))
                    print("-" * (len(" | ".join(headers)) + 1))
                    for row in resultados:
                        print(" | ".join(str(x) for x in row))
            else:
                print(resultados)
        else:
            print("(Sin resultados)")
        print("\n" + "="*80 + "\n")


def conectar_firebird(ruta_db):
    """Conexión a base de datos Firebird"""
    try:
        return firebirdsql.connect(
            host='localhost',
            database=ruta_db,
            user='SYSDBA',
            password='masterkey',
            charset='ISO8859_1'
        )
    except Exception as e:
        print(f"❌ Error conectando a Firebird: {e}")
        # ❌ ELIMINA ESTA LÍNEA: exit(1)
        # ✅ REEMPLAZA CON:
        raise Exception(f"Error de conexión: {str(e)}")


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
    resultado = [fila[0] for fila in cursor.fetchall()]  # Solo extrae mp.codigo
    log_consulta("Medios de Pago", sql, resultado)
    if resultado:
        return resultado[0]  # Retorna el código del medio de pago con mayor valor
    return 47  # Valor por defecto si no se encuentra ninguno


def consultar_kardex(conexion, kardex_id):
    """Consulta principal del kardex"""
    cursor = conexion.cursor()

    # Verificar si campo HE existe
    cursor.execute("""
        SELECT COUNT(*) FROM rdb$relation_fields 
        WHERE rdb$relation_name = 'KARDEX' AND rdb$field_name = 'HE'
    """)
    he_existe = cursor.fetchone()[0] > 0

    # Construir SELECT dinámicamente
    # 🧱 Construir el bloque de SELECT dinámicamente
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
    log_consulta("Kardex Principal", sql, [resultado])

    return resultado


def obtener_configuracion(conexion):
    """Obtiene configuración dinámica de la BD"""
    print("\n🔍 OBTENIENDO CONFIGURACIÓN DINÁMICA")

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
            print(f"❌ Error al obtener '{clave}': {e}")
            config[clave] = None

    print("\n✅ Configuración final obtenida:")
    for k, v in config.items():
        print(f"  {k}: {v}")

    return config


def actualizar_kardex(conexion, kardex_id, cufe, mensaje, estado_dian, certificate_days_left=None, resolution_days_left=None, db_path=None):

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

    print(
        f"\n✅ Kardex actualizado: CUFE={cufe}, Estado={estado_dian}, Mensaje={mensaje}")
    if certificate_days_left is not None and certificate_days_left < 2:
        mostrar_alerta("Días restantes del certificado",
                       str(certificate_days_left))
        enviar_email(f"⚠️ ADVERTENCIA: Quedan {certificate_days_left} días del certificado. Ruta DB: {db_path}")
    if resolution_days_left is not None and resolution_days_left < 2:
        mostrar_alerta("Días restantes de la resolución",
                       str(resolution_days_left))
        enviar_email(f"⚠️ ADVERTENCIA: Quedan {resolution_days_left} días de la resolución. Ruta DB: {db_path}")


def consultar_impuestos(conexion, kardex_id):
    """Consulta impuestos del kardex"""
    sql = """
        SELECT 
            IIF(dk.precioiconsumo > 0, 8, dk.porciva) as porciva,
            round(sum(dk.preciobase*dk.canlista),2) as base,
            round(sum(
                IIF(dk.precioiconsumo > 0, dk.precioiconsumo*dk.canlista, dk.precioiva*dk.canlista)
            ),2) as iva 
        FROM kardex k
        INNER JOIN dekardex dk ON k.kardexid=dk.kardexid 
        WHERE k.kardexid=? 
        GROUP BY IIF(dk.precioiconsumo > 0, 8, dk.porciva)
    """
    cursor = conexion.cursor()
    cursor.execute(sql, (kardex_id,))
    resultado = cursor.fetchone() or (0, 0, 0)
    log_consulta("Cálculo de Impuestos", sql, [resultado])
    return resultado


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
    resultado = cursor.fetchall()
    log_consulta("Totales de Impuestos", sql, resultado)
    return resultado


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
    resultado = cursor.fetchall()
    log_consulta("Totales de Holding Taxes", sql, resultado)
    return resultado


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
    resultado = cursor.fetchall()
    log_consulta("Ítems de Factura", sql, resultado)
    return resultado


def obtener_endpoint(codcomp, codprefijo):
    """Obtiene endpoint según tipo de documento"""
    endpoint_config = ENDPOINTS.get(codcomp, ENDPOINTS['FV'])
    if isinstance(endpoint_config, dict):
        return endpoint_config.get(codprefijo, endpoint_config['default'])
    return endpoint_config


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
        print(f"⚠️ Error calculando DV: {e}")
        return '0'


def procesar_respuesta_api(respuesta):
    print("\n🔍 Procesando respuesta de la API DIAN...")
    print(f"Respuesta recibida: {json.dumps(respuesta, indent=4)}")
    """Procesa respuesta de la API DIAN"""
    resultado = {
        'success': respuesta.get('success'),
        'message': respuesta.get('message', ''),
        'cufe': respuesta.get("cufe") or respuesta.get("cuds") or respuesta.get("cude", ""),
        'QRStr': respuesta.get('QRStr', ''),
        'certificate_days_left': respuesta.get('certificate_days_left'),
        'resolution_days_left': respuesta.get('resolution_days_left'),
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

            resultado['dian_response']['IsValid'] = send_result.get(
                'IsValid', 'false') == 'true'
            resultado['dian_response']['StatusCode'] = send_result.get(
                'StatusCode', '')
            resultado['dian_response']['StatusDescription'] = send_result.get(
                'StatusDescription', '')
            resultado['dian_response']['StatusMessage'] = send_result.get(
                'StatusMessage', '')

            error_msgs = []
            if 'ErrorMessage' in send_result:
                em = send_result['ErrorMessage']
                if isinstance(em, dict) and 'string' in em:
                    error_msgs = em['string'] if isinstance(
                        em['string'], list) else [em['string']]
                elif isinstance(em, list):
                    error_msgs = em
                elif isinstance(em, str):
                    error_msgs = [em]

            for msg in error_msgs:
                if isinstance(msg, str):
                    if 'Rechazo:' in msg:
                        resultado['dian_response']['Rechazos'].append(
                            msg.split('Rechazo:', 1)[-1].strip())
                    elif 'Notificación:' in msg:
                        resultado['dian_response']['Notificaciones'].append(
                            msg.split('Notificación:', 1)[-1].strip())

        except Exception as e:
            print(f"⚠️ Error procesando respuesta DIAN: {e}")

    # Validar documento previamente procesado
    for rechazo in resultado['dian_response']['Rechazos']:
        if "Documento procesado anteriormente." in rechazo:
            resultado['dian_response']['IsValid'] = True
            break

    return resultado


def enviar_documento_api(documento_json, codcomp, codprefijo, base_url, token):
    """Envía documento a la API DIAN"""
    endpoint = obtener_endpoint(codcomp, codprefijo)
    url = f"{base_url}/{endpoint}" if not base_url.endswith(
        '/') else f"{base_url}{endpoint}"

    auth_token = f"Bearer {token}"

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': auth_token
    }

    if DEBUG_MODE:
        print(f"\n🚀 ENVIANDO A: {url}")
        print(f"📄 Tipo: {codcomp}-{codprefijo}")

    try:
        response = requests.post(url, headers=headers,
                                 json=documento_json, timeout=30)
        response.raise_for_status()
        response_data = response.json()

        if DEBUG_MODE:
            print("\n✅ RESPUESTA EXITOSA:")
            print(json.dumps(response_data, indent=2, ensure_ascii=False))

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
                error_data['response'] = {'message': str(
                    e), 'errors': {'validation': [str(e.response.text)]}}

        if 'response' in error_data:
            error_data['processed_response'] = procesar_respuesta_api(
                error_data['response'])
        else:
            error_data['processed_response'] = procesar_respuesta_api(
                {'errors': {'general': [str(e)]}})

        if DEBUG_MODE:
            print(f"\n❌ ERROR: {e}")

        return error_data

#asi kardex_id puede ser pasado a la funcion generar_json, 
def generar_json(datos_kardex, impuestos, tax_totals, holding_tax_totals, items, config, db_path, medio_pago_id):
    """Genera JSON para envío a DIAN"""
    HEADNOTE = config['CABECERADIANVM'] or ""
    FOOTNOTE = config['FOOTERDIANVM'] or ""
    ZESE = config['ZESEVM'] or ""

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
        numero_documento = safe_int(datos_kardex[3])
        numero_max_resolucion = safe_int(datos_kardex[35])
        prefijo_resolucion = safe_str(datos_kardex[12])
        #  si faltan 100 o 50 o 10 enviar un print de advertencia
        if numero_max_resolucion - numero_documento in [100, 50, 10]:
            enviar_email(f"⚠️ ADVERTENCIA: Quedan {numero_max_resolucion - numero_documento} documentos en la resolución {prefijo_resolucion}. Ruta DB: {db_path}")
            
                
        #if datos_kardex[18] == 6 or datos_kardex[18] == "6":
        nit, dv = datos_kardex[13].split(
            '-') if '-' in safe_str(datos_kardex[13]) else (safe_str(datos_kardex[13]), '0')
        dv = calculate_dv(nit)

        #recorrer caracter por caracter buscando que no sea digito
        for char in nit:
            if not char.isdigit():
                dv = 0
        #else:
        #    nit = datos_kardex[13]
        #    dv = 0
        # Procesar tax_totals
        processed_taxes = []
        total_impuestos = 0.0
        total_base = 0.0


        #eliminar los tax_totals que tengan tax_base 0 0.00
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
        # eliminar los taxable_amount que tengan valor 0 0.00
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
                    "amount": "0.00", #safe_currency(item[3]),
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

        # Construir documento base
        documento = {
            "prefix": safe_str(datos_kardex[12]),
            "number": safe_int(datos_kardex[3]),
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
        # Versión con restricciones por tipo de documento (corregida)
        tipo_documento = safe_int(datos_kardex[2], 1)
        documentos_permitidos = [1, 4]  # Factura, NC, ND, etc.

        if HEADNOTE.strip() and tipo_documento in documentos_permitidos:
            documento["head_note"] = HEADNOTE.strip()

        if FOOTNOTE.strip() and tipo_documento in documentos_permitidos:
            documento["foot_note"] = FOOTNOTE.strip()

        if ZESE.strip() and tipo_documento in documentos_permitidos:
            documento["seze"] = ZESE.strip()
        
        
        if datos_kardex[18] != 6 or datos_kardex[18] != "6":
            #eliminar campo de tipo_documento
            documento.pop("dv", None)

        # Manejar campo health_fields
        if datos_kardex[36]:
            try:
                parsed = json.loads(datos_kardex[36])
                documento["health_fields"] = parsed.get("health_fields", {})
            except json.JSONDecodeError:
                documento["health_fields"] = {}

        if safe_str(datos_kardex[12]) == 'ND' and safe_int(datos_kardex[2], 1) == 1 and safe_str(datos_kardex[25]):
            
            documento["type_document_id"] = 5
            documento["discrepancy_response_code"] = 4
            documento["discrepancy_response_description"] = safe_str(
                datos_kardex[28], "REACTIVACION")
            documento["billing_reference"] = {
                "number": safe_str(datos_kardex[24]),
                "uuid": safe_str(datos_kardex[25]),
                "issue_date": parse_fecha(datos_kardex[26]),
            }
            if "legal_monetary_totals" in documento:
                documento["requested_monetary_totals"] = documento.pop(
                    "legal_monetary_totals")
            if "invoice_lines" in documento:
                documento["debit_note_lines"] = documento.pop("invoice_lines")
            if processed_holding_taxes:
                documento["with_holding_tax_total"] = []

        # Manejar notas crédito/débito
        if safe_int(datos_kardex[2]) == 11 or safe_int(datos_kardex[2]) == 13 or safe_int(datos_kardex[2]) == 4:
            if processed_holding_taxes and safe_int(datos_kardex[2]) == 13:
                documento["with_holding_tax_total"] = []

            if safe_int(datos_kardex[2]) == 11 or safe_int(datos_kardex[2]) == 13:
                documento["seller"] = documento.pop("customer")
                #AGREGAR CAMPO "postal_zone_code": "000000"
                documento["seller"]["postal_zone_code"] = "54001"

            if safe_int(datos_kardex[2]) == 11:
                for line in documento["invoice_lines"]:
                    line["type_generation_transmition_id"] = 1
                    line["start_date"] = FECHA_ACTUAL()
                    
            if safe_str(datos_kardex[25]):
                documento["billing_reference"] = {
                    "number": safe_str(datos_kardex[24]),
                    "uuid": safe_str(datos_kardex[25]),
                    "issue_date": parse_fecha(datos_kardex[26]),
                }

            if (safe_int(datos_kardex[2]) == 13 or safe_int(datos_kardex[2]) == 4):
                
                if "invoice_lines" in documento:
                    documento["credit_note_lines"] = documento.pop(
                        "invoice_lines")
                    
                if safe_int(datos_kardex[2]) == 4:   
                    if processed_holding_taxes:
                        documento.pop("with_holding_tax_total", None)

                if safe_int(datos_kardex[2]) == 13:
                    documento["discrepancyresponsecode"] = safe_str(
                        datos_kardex[27], "2")
                    documento["discrepancyresponsedescription"] = safe_str(
                        datos_kardex[28], "DEVOLUCIÓN")
                else:
                    if safe_str(datos_kardex[25]):                   
                        documento["discrepancy_response_code"] = safe_str(
                            datos_kardex[27], "2")
                        documento["discrepancy_response_description"] = safe_str(
                            datos_kardex[28], "DEVOLUCIÓN")
                    else:
                        documento["discrepancyresponsecode"] =  "1"
                        documento["type_operation_id"] = "8"
                        documento["invoice_period"] = {
                            "start_date": FECHA_ANTERIOR(),
                            "end_date": FECHA_ANTERIOR(),
                        }

            if safe_str(datos_kardex[25]) is None and safe_int(datos_kardex[2]) == 4:
                # SI HAY WITHHOLDING TAX TOTAL, BORRARLO TOTALEMENTE QUE NO EXISTA EL ITEM
         
                if "invoice_lines" in documento:
                    documento["credit_note_lines"] = documento.pop(
                        "invoice_lines")
                documento["discrepancyresponsecode"] = safe_str(
                    datos_kardex[27], "2")
                documento["type_operation_id"] = "8"
                # borrar eliminar el item resolution_number
                documento.pop("resolution_number", None)

        # Guardar JSON en archivo
        json_filename = f"{safe_str(datos_kardex[12])}-{safe_int(datos_kardex[3])}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(documento, f, indent=2, ensure_ascii=False)
        print(f"\n💾 JSON guardado: {json_filename}")

        return documento

    except Exception as e:
        import traceback
        error_msg = f"Error generando JSON: {str(e)}\n{traceback.format_exc()}"
        print(f"\n❌ {error_msg}")
        return {"error": error_msg}

def enviar_email(mensaje):
    """Envía un correo electrónico de alerta sin bloquear el programa si falla"""
    try:
        import smtplib
        from email.message import EmailMessage

        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_user = "rinconvargasvictormanuel@gmail.com"
        smtp_password = "xcviupgagoyqxyrm"

        msg = EmailMessage()
        msg.set_content(mensaje)
        msg['Subject'] = "Alerta de procesamiento de factura"
        msg['From'] = smtp_user
        msg['To'] = "rinconvargasvictormanuel@gmail.com"
        msg['Cc'] = "informacion.bce1@gmail.com"

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

    except Exception as e:
        # Logging embellecido opcional
        print(f"[WARN] No se pudo enviar el correo: {e}")
        # O simplemente: pass
        pass



def procesar_factura(db_path, kardex_id, alert_days=0):
    """Función principal para procesar una factura (con pool)"""
    conexion = None
    log_file = None
    tee = None

    try:
        # 🆕 1. Obtener conexión del pool
        conexion = obtener_conexion(db_path)

        # 2. Datos básicos
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
            return "ERROR:No se encontró el kardex especificado"

        codcomp, codprefijo, numero, tipo_doc = datos_basicos

        # 3. Configurar logging
        log_file, tee = setup_logging(codcomp, codprefijo, numero)

        # Usar tee para logging en lugar de sys.stdout
        print = lambda *args, **kwargs: __builtins__.print(*args, **kwargs, file=tee)
        
        print(f"\n🏁 PROCESANDO: {codcomp}-{codprefijo}{numero} (ID: {kardex_id})")

        # 4. Consultar datos principales
        datos_kardex = consultar_kardex(conexion, kardex_id)
        if not datos_kardex:
            return "ERROR:No se encontraron datos para el kardex"

        # 5. Obtener configuración
        config = obtener_configuracion(conexion)
        TOKEN = config['TOKENDIANVM']
        BASE_URL = config['ENDPOINTDIANVM'] or "http://45.149.204.184:81/api/ubl2.1"
        HEADNOTE = config['CABECERADIANVM'] or ""
        FOOTNOTE = config['FOOTERDIANVM'] or ""
        ZESE= config['ZESEVM'] or ""

        #print(f"\n🔧 Configuración obtenida: BASE_URL={BASE_URL}, TOKEN={TOKEN}, HEADNOTE={HEADNOTE}, FOOTNOTE={FOOTNOTE}, ZESE={ZESE}")
        
        if not TOKEN:
            return "ERROR:Token no configurado (TOKENDIANVM)"

        # 6. Consultar datos adicionales
        impuestos = consultar_impuestos(conexion, kardex_id)
        tax_totals = consultar_tax_totals(conexion, kardex_id)
        holding_tax_totals = consultar_holding_tax_totals(conexion, kardex_id)
        items = consultar_items(conexion, kardex_id)
        
        #6.1 Obtener medio de pago
        medio_pago_id = consultar_medios_pago(conexion, kardex_id)

        # 7. Generar JSON
        documento_json = generar_json(
            datos_kardex, impuestos, tax_totals, holding_tax_totals, items, config, db_path, medio_pago_id)
        if "error" in documento_json:
            return f"ERROR:{documento_json['error']}"



        # 8. Enviar a API
        resultado_api = enviar_documento_api(
            documento_json, codcomp, codprefijo, BASE_URL, TOKEN)

        if not resultado_api.get('processed_response'):
            resultado_api['processed_response'] = procesar_respuesta_api(
                resultado_api.get('response', {}))

        respuesta_procesada = resultado_api['processed_response']

        # 9. Actualizar kardex
        mensaje_actualizacion = respuesta_procesada.get('message', '')

        if respuesta_procesada['dian_response']['Rechazos']:
            mensaje_actualizacion = " | ".join(
                respuesta_procesada['dian_response']['Rechazos'])
        elif not respuesta_procesada.get('success') and resultado_api.get('error'):
            mensaje_actualizacion = resultado_api['error']

        actualizar_kardex(
            conexion,
            kardex_id,
            respuesta_procesada.get('cufe', ''),
            mensaje_actualizacion[:250],
            'EXITOSA' if respuesta_procesada.get(
                'dian_response', {}).get('IsValid') else 'NO EXITOSA',
            respuesta_procesada.get('certificate_days_left'),
            respuesta_procesada.get('resolution_days_left'),
            db_path
        )

        if respuesta_procesada.get('dian_response', {}).get('IsValid'):
            return f"SUCCESS:{respuesta_procesada.get('cufe', '')}"
        else:
            return f"FAILED:{mensaje_actualizacion[:100]}"

    except Exception as e:
        error_msg = f"Error general: {str(e)}"
        if tee:
            print(error_msg)  # Usamos nuestro print seguro
        else:
            __builtins__.print(error_msg)  # Fallback al print normal

            try:
                actualizar_kardex(conexion, kardex_id, '',
                                  error_msg[:250], 'NO EXITOSA', db_path=db_path)
            except:
                pass
                pass
        return f"ERROR:{error_msg}"
    finally:
        # 🆕 10. Liberar conexión al pool en lugar de cerrarla
        if conexion:
            liberar_conexion(db_path, conexion)
        if log_file:
            restore_logging(log_file, tee)


class FacturaServer:
    """Servidor TCP para procesamiento en background"""

    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.running = False
        self.libs_precargadas = False

    def precalentar_recursos(self):
        """Pre-calienta librerías sin conexiones específicas"""
        try:
            print("🔥 Precalentando recursos...")
            sys.stdout.flush()  # 🆕 FLUSH

            # Pre-importar librerías pesadas
            import requests
            import json
            import firebirdsql
            import threading

            # Pre-crear objetos
            _ = requests.Session()
            _ = json.dumps({})

            print("✅ Librerías precalentadas")
            sys.stdout.flush()  # 🆕 FLUSH
            self.libs_precargadas = True

        except Exception as e:
            print(f"⚠️ Error precalentando recursos: {e}")
            sys.stdout.flush()  # 🆕 FLUSH

    def handle_client(self, client_socket):
        """Maneja conexiones de clientes"""
        try:
            data = client_socket.recv(1024).decode('utf-8').strip()
            print(f"📨 Comando recibido: {data}")

            if data.startswith("PROCESS "):
                try:
                    import re
                    match = re.match(r'PROCESS "([^"]+)" (\d+)', data)
                    if match:
                        db_path = match.group(1)
                        kardex_id = int(match.group(2))
                    else:
                        match = re.match(r"PROCESS '([^']+)' (\d+)", data)
                        if match:
                            db_path = match.group(1)
                            kardex_id = int(match.group(2))
                        else:
                            parts = data.split()
                            if len(parts) >= 3:
                                db_path = parts[1]
                                kardex_id = int(parts[2])
                            else:
                                client_socket.send(
                                    "ERROR:Formato incorrecto".encode('utf-8'))
                                return

                    print(f"🔍 Procesando: {db_path} - {kardex_id}")
                    resultado = procesar_factura(db_path, kardex_id, 0)
                    client_socket.send(resultado.encode('utf-8'))

                except Exception as e:
                    error_msg = f"ERROR:Parseo: {str(e)}"
                    print(error_msg)
                    client_socket.send(error_msg.encode('utf-8'))

            elif data == "PING":
                client_socket.send("READY".encode('utf-8'))

            elif data == "EXIT":
                self.running = False
                client_socket.send("SHUTDOWN".encode('utf-8'))

        except Exception as e:
            error_msg = f"ERROR:Conexión: {str(e)}"
            print(error_msg)
            client_socket.send(error_msg.encode('utf-8'))
        finally:
            client_socket.close()

    def start_server(self):
        """Inicia el servidor con precalentamiento"""
        # 🆕 FORZAR FLUSH INMEDIATO
        sys.stdout.flush()
        sys.stderr.flush()

        # 🆕 Precalentar antes de escuchar
        self.precalentar_recursos()

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)

        # 🆕 FLUSH después de cada mensaje importante
        print(f"🚀 Servidor iniciado en {self.host}:{self.port}")
        sys.stdout.flush()

        print("💡 Desde otra consola usa:")
        print('  echo PROCESS "C:\\ruta\\bd.gdb" 12345 | nc localhost 12345')
        sys.stdout.flush()

        self.running = True
        while self.running:
            try:
                client_socket, addr = server_socket.accept()
                print(f"🔗 Cliente conectado: {addr}")
                sys.stdout.flush()

                threading.Thread(target=self.handle_client,
                                 args=(client_socket,)).start()
            except Exception as e:
                print(f"❌ Error aceptando conexión: {e}")
                sys.stdout.flush()
                break

        server_socket.close()
        print("🛑 Servidor detenido")
        sys.stdout.flush()


def send_command(command, host='localhost', port=12345):
    """Envía comando al servidor"""
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        client_socket.send(command.encode('utf-8'))
        response = client_socket.recv(1024).decode('utf-8')
        client_socket.close()
        return response
    except Exception as e:
        return f"ERROR:Conexión fallida: {str(e)}"




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true",
                        help="Iniciar como servidor")
    parser.add_argument("--command", help="Enviar comando al servidor")
    parser.add_argument("--host", default="localhost",
                        help="Host del servidor")
    parser.add_argument("--port", type=int, default=12345,
                        help="Puerto del servidor")
    parser.add_argument("--alert_days", type=int,
                        default=0, help="Días para alertas")

    # --- NUEVOS ARGUMENTOS POSICIONALES ---
    # 'nargs='?'' los hace opcionales. Si no se proporcionan, su valor será None.
    parser.add_argument("db_path", nargs='?',
                        help="Ruta a la base de datos (.GDB)")
    parser.add_argument("kardex_id", nargs='?', type=int,
                        help="ID del documento a procesar")
    # --- FIN DE NUEVOS ARGUMENTOS ---

    args = parser.parse_args()

    # --- NUEVA LÓGICA DE DECISIÓN ---
    # 1. Primero verifica si se quiere usar el modo servidor (--server)
    if args.server:
        server = FacturaServer(args.host, args.port)
        server.start_server()

    # 2. Luego verifica si se quiere usar el modo cliente de red (--command)
    elif args.command:
        response = send_command(args.command, args.host, args.port)
        print(response)

    # 3. Finalmente, verifica si se proporcionaron los argumentos posicionales
    elif args.db_path and args.kardex_id:
        # ¡Modo directo! Procesa la factura inmediatamente.
        print(
            f"🗂️  Procesando directamente: {args.db_path} (ID: {args.kardex_id})")
        resultado = procesar_factura(
            args.db_path, args.kardex_id, args.alert_days)
        print(resultado)

    else:
        # Si no se usó ningún modo conocido, muestra la ayuda
        print("📋 MODO DE USO:")
        print("  Modo Directo (Nuevo):")
        print('    j.exe "C:\\ruta\\bd.gdb" 12345')
        print("  Modo Servidor:")
        print("    j.exe --server")
        print("  Modo Cliente (Comando de red):")
        print('    j.exe --command "PROCESS \"C:\\ruta\\bd.gdb\" 12345"')
        print("    j.exe --command PING")
        print("    j.exe --command EXIT")
