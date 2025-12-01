"""
Helper para consultar datos de factura desde TNS y generar PDFs directamente.
Usa el mismo sistema de bce/backend: wkhtmltopdf + Django templates.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from io import BytesIO
import base64
import qrcode
import os
import glob
import traceback
import platform
import time
import subprocess
import tempfile
from django.template.loader import get_template
from django.http import HttpResponse
from django.conf import settings

logger = logging.getLogger(__name__)


def find_wkhtmltopdf():
    """Busca wkhtmltopdf - optimizado con ruta fija en Windows"""
    if platform.system() == "Windows":
        fixed_path = 'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'
        if os.path.exists(fixed_path):
            logger.info(f"✅ wkhtmltopdf (ruta fija): {fixed_path}")
            return fixed_path

    linux_paths = [
        'wkhtmltopdf',
        '/usr/bin/wkhtmltopdf',
        '/usr/local/bin/wkhtmltopdf',
    ]

    for path in linux_paths:
        try:
            result = subprocess.run([path, '--version'],
                                    capture_output=True,
                                    text=True,
                                    timeout=5)
            if result.returncode == 0:
                logger.info(f"✅ wkhtmltopdf encontrado: {path}")
                return path
        except:
            continue

    logger.error("❌ wkhtmltopdf no encontrado")
    return None


def render_to_pdf(template_src, context_dict={}, custom_options=None):
    """
    VERSIÓN MULTIPLATAFORMA - funciona en Windows y Ubuntu
    CON SOPORTE PARA OPCIONES PERSONALIZADAS (MANTIENE COMPATIBILIDAD)
    Copiado de bce/backend/utils/pdf.py
    """
    try:
        logger.info("🚀 [PDF] Iniciando generación...")
        start_time = time.time()

        template = get_template(template_src)
        html = template.render(context_dict)

        # Fecha en español para el footer
        meses_espanol = [
            'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
        ]
        
        fecha_actual = datetime.now()
        dia = fecha_actual.day
        mes = meses_espanol[fecha_actual.month - 1]
        año = fecha_actual.year
        hora = fecha_actual.strftime("%H:%M:%S")
        
        fecha_espanol = f"{dia} de {mes} de {año} {hora}"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html)
            html_path = f.name

        pdf_path = html_path.replace('.html', '.pdf')

        # Footer HTML
        footer_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        margin: 0;
                        padding: 0;
                    }}
                    .footer {{
                        font-size: 8px;
                        font-family: Arial, sans-serif;
                        text-align: center;
                        color: #666;
                        padding: 10px 0;
                        line-height: 1.3;
                        margin-top: 15px;
                    }}
                    .company {{
                        font-weight: bold;
                    }}
                </style>
            </head>
            <body>
                <div class="footer">
                    Documento generado el {fecha_espanol} - <span class="company"></span><br>
                    Página <span id="pageNum"></span> de <span id="pageCount"></span>
                </div>

                <script type="text/javascript">
                    var pdfInfo = {{}};
                    var x = document.location.search.substring(1).split('&');
                    for (var i in x) {{ var z = x[i].split('=',2); pdfInfo[z[0]] = unescape(z[1]); }}
                    function setPdfNum() {{
                        document.getElementById('pageNum').textContent = pdfInfo.page || '1';
                        document.getElementById('pageCount').textContent = pdfInfo.topage || '1';
                    }}
                    if (document.readyState === 'loading') {{
                        document.addEventListener('DOMContentLoaded', setPdfNum);
                    }} else {{
                        setPdfNum();
                    }}
                </script>
            </body>
            </html>
            """

        with tempfile.NamedTemporaryFile(mode='w', suffix='_footer.html', delete=False, encoding='utf-8') as f:
            f.write(footer_html)
            footer_path = f.name

        try:
            wkhtml_path = find_wkhtmltopdf()
            if not wkhtml_path:
                raise FileNotFoundError("wkhtmltopdf no encontrado")

            # Construir comando base
            cmd = [
                wkhtml_path,
                '--quiet',
                '--page-size', 'Letter',  # Por defecto
                '--margin-top', '10mm',
                '--margin-bottom', '15mm', 
                '--margin-left', '10mm',
                '--margin-right', '10mm',
                '--dpi', '150',
                '--enable-local-file-access',
                '--footer-html', footer_path,
                '--footer-spacing', '1',
                '--enable-javascript',
                '--javascript-delay', '1000',
            ]

            # Agregar opciones personalizadas si se proporcionan
            if custom_options:
                logger.info(f"🎨 [PDF] Aplicando opciones personalizadas: {custom_options}")
                
                # Manejar page-width y page-height (deben reemplazar --page-size si existe)
                if 'page-width' in custom_options or 'page-height' in custom_options:
                    if '--page-size' in cmd:
                        idx = cmd.index('--page-size')
                        del cmd[idx:idx+2]
                    if 'page-width' in custom_options:
                        cmd.extend(['--page-width', custom_options['page-width']])
                    if 'page-height' in custom_options:
                        cmd.extend(['--page-height', custom_options['page-height']])
                
                # Sobrescribir opciones por defecto
                if 'margin-top' in custom_options:
                    cmd[cmd.index('--margin-top') + 1] = custom_options['margin-top']
                if 'margin-bottom' in custom_options:
                    cmd[cmd.index('--margin-bottom') + 1] = custom_options['margin-bottom']
                if 'margin-left' in custom_options:
                    cmd[cmd.index('--margin-left') + 1] = custom_options['margin-left']
                if 'margin-right' in custom_options:
                    cmd[cmd.index('--margin-right') + 1] = custom_options['margin-right']
                if 'dpi' in custom_options:
                    cmd[cmd.index('--dpi') + 1] = str(custom_options['dpi'])
                
                # Opciones booleanas
                if custom_options.get('no-outline'):
                    if '--no-outline' not in cmd:
                        cmd.append('--no-outline')
                if custom_options.get('no-footer'):
                    if '--footer-html' in cmd:
                        idx = cmd.index('--footer-html')
                        del cmd[idx:idx+4]
            
            # Agregar archivos al final
            cmd.extend([html_path, pdf_path])

            logger.info(f"   📦 Ejecutando: {wkhtml_path}")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                with open(pdf_path, 'rb') as f:
                    pdf_value = f.read()

                total_time = time.time() - start_time
                logger.info(f"✅ [PDF] Generado en: {total_time:.2f}s")

                # Retornar BytesIO en lugar de HttpResponse para uso interno
                pdf_buffer = BytesIO(pdf_value)
                return pdf_buffer
            else:
                error_msg = result.stderr[:500] if result.stderr else "Error desconocido"
                raise Exception(f"wkhtmltopdf: {error_msg}")

        except subprocess.TimeoutExpired:
            raise Exception("Timeout generando PDF (5 minutos)")
        finally:
            # Limpiar archivos temporales
            if os.path.exists(html_path):
                os.remove(html_path)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            if os.path.exists(footer_path):
                os.remove(footer_path)

    except Exception as e:
        logger.error(f"❌ [PDF] Error: {e}")
        error_trace = traceback.format_exc()

        if platform.system() == "Windows":
            log_path = "C:\\temp\\pdf_errors.txt"
        else:
            log_path = "/home/victus/pdf_errors.txt"

        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write(f"❌ Error: {str(e)}\n")
            log_file.write(f"📋 Traceback: {error_trace}\n")

        return None


def consultar_datos_factura_para_pdf(bridge, kardex_id: int) -> Dict[str, Any]:
    """
    Consulta los datos de una factura desde TNS para generar PDF.
    Usa los mismos SELECTs que el procesador DIAN.
    
    Args:
        bridge: Instancia de TNSBridge ya conectada
        kardex_id: ID del KARDEX
        
    Returns:
        dict con todos los datos necesarios para generar el PDF
    """
    try:
        cursor = bridge.conn.cursor()
        
        # 1. Consultar datos principales del KARDEX (similar a consultar_kardex de DIAN)
        sql_kardex = """
        SELECT DISTINCT 
            k.kardexid, 
            k.codprefijo,
            k.numero,
            t.nit,
            t.dv,
            t.nombre,
            t.direcc1,
            t.telef1,
            t.email,
            k.fecha,
            k.hora,
            k.observ,
            k.total,
            k.cufe,
            p.prefe,
            p.fecinifel,
            p.fecfinfel,
            p.resolucion,
            p.numinifacele,
            p.numfinfacele,
            ci.nombre as ciudad_nombre,
            pa.nombre as pais_nombre
        FROM kardex k
        INNER JOIN terceros t ON t.terid = k.cliente
        LEFT JOIN prefijo p ON p.codprefijo = k.codprefijo
        LEFT JOIN ciudane ci ON ci.ciudaneid = t.ciudaneid
        LEFT JOIN pais pa ON pa.paisid = ci.paisid
        WHERE k.kardexid = ?
        """
        
        cursor.execute(sql_kardex, (kardex_id,))
        row = cursor.fetchone()
        
        if not row:
            logger.error(f"❌ No se encontró KARDEX con ID {kardex_id}")
            return None
        
        # 2. Consultar items de la factura
        sql_items = """
        SELECT 
            cu.codigo as unidad, 
            dk.canlista as cantidad,
            round((dk.preciobase*dk.canlista),2) as parcvta,
            IIF(dk.precioiconsumo > 0, 8, dk.porciva) as porciva,
            dk.descuento, 
            dk.preciobase,
            dk.preciovta,
            m.descrip as descripcion,
            m.codigo as codigo_material
        FROM material m 
        INNER JOIN dekardex dk ON dk.matid=m.matid 
        LEFT JOIN codigosunidades cu ON cu.codunidadid=m.codunidadid 
        WHERE dk.kardexid=? AND dk.parcvta>0
        ORDER BY dk.dekardexid
        """
        
        cursor.execute(sql_items, (kardex_id,))
        items_rows = cursor.fetchall()
        
        # Procesar items
        items = []
        subtotal = 0
        iva_total = 0
        
        for item_row in items_rows:
            cantidad = float(item_row[1] or 0)
            precio_vta = float(item_row[6] or 0)
            descuento = float(item_row[4] or 0)
            porciva = float(item_row[3] or 0)
            
            subtotal_item = (precio_vta * cantidad) - descuento
            iva_item = subtotal_item * (porciva / 100)
            total_item = subtotal_item + iva_item
            
            subtotal += subtotal_item
            iva_total += iva_item
            
            items.append({
                'codigo': str(item_row[8]) if item_row[8] else '',
                'descripcion': str(item_row[7]) if item_row[7] else '',
                'name': str(item_row[7]) if item_row[7] else '',
                'cantidad': cantidad,
                'quantity': cantidad,
                'invoiced_quantity': cantidad,
                'unidad': str(item_row[0]) if item_row[0] else 'UND',
                'price': precio_vta,
                'precio': precio_vta,
                'descuento': descuento,
                'subtotal': subtotal_item,
                'iva': iva_item,
                'total': total_item,
                'line_extension_amount': f"{subtotal_item:.2f}",
                'code': str(item_row[8]) if item_row[8] else '',
                'description': str(item_row[8]) if item_row[8] else ''
            })
        
        # 3. Construir datos de factura
        # Mapeo según la consulta SQL:
        # row[0] = k.kardexid
        # row[1] = k.codprefijo (no usar, usar p.prefe)
        # row[2] = k.numero
        # row[3] = t.nit
        # row[4] = t.dv
        # row[5] = t.nombre
        # row[6] = t.direcc1
        # row[7] = t.telef1
        # row[8] = t.email
        # row[9] = k.fecha
        # row[10] = k.hora
        # row[11] = k.observ
        # row[12] = k.total
        # row[13] = k.cufe
        # row[14] = p.prefe (PREFIJO A USAR)
        # row[15] = p.fecinifel
        # row[16] = p.fecfinfel
        # row[17] = p.resolucion
        # row[18] = p.numinifacele
        # row[19] = p.numfinfacele
        # row[20] = ci.nombre (ciudad_nombre)
        # row[21] = pa.nombre (pais_nombre)
        
        total = float(row[12] or 0)
        cufe = str(row[13] or '').strip() if row[13] else ''
        
        factura_data = {
            'kardex_id': row[0],
            'prefijo': str(row[14] or ''),  # p.prefe
            'numero': str(row[2] or ''),  # k.numero
            'fecha': row[9].strftime('%Y-%m-%d') if row[9] else '',  # k.fecha
            'hora': str(row[10] or ''),  # k.hora
            'observacion': str(row[11] or ''),  # k.observ
            'total': total,  # k.total
            'subtotal': subtotal,
            'iva': iva_total,
            'empresa_nombre': '',  # Viene del frontend
            'empresa_nit': '',  # Viene del frontend
            'empresa_direccion': '',  # Omitido por el momento
            'empresa_telefono': '',
            'empresa_email': '',
            'cliente_nombre': str(row[5] or 'Consumidor Final'),  # t.nombre
            'cliente_nit': str(row[3] or ''),  # t.nit
            'cliente_dv': str(row[4] or ''),  # t.dv
            'cliente_direccion': str(row[6] or ''),  # t.direccion
            'cliente_telefono': str(row[7] or ''),  # t.telefono
            'cliente_email': str(row[8] or ''),  # t.email
            'cliente_ciudad': str(row[20] or ''),  # ci.nombre
            'cliente_pais': str(row[21] or ''),  # pa.nombre
            'resolucion': str(row[17] or ''),  # p.resolucion
            'fecinifel': row[15].strftime('%Y-%m-%d') if row[15] else '',  # p.fecinifel
            'fecfinfel': row[16].strftime('%Y-%m-%d') if row[16] else '',  # p.fecfinfel
            'numinifacele': str(row[18] or ''),  # p.numinifacele
            'numfinfacele': str(row[19] or ''),  # p.numfinfacele
            'items': items,
            'cufe': cufe,  # k.cufe (puede estar vacío)
        }
        
        logger.info(f"✅ Datos de factura consultados: {factura_data['prefijo']}-{factura_data['numero']}")
        return factura_data
        
    except Exception as e:
        logger.error(f"❌ Error consultando datos de factura: {e}", exc_info=True)
        return None


def generar_qr_code(cufe: str) -> Optional[str]:
    """Genera un QR code en base64 a partir del CUFE"""
    try:
        if not cufe:
            return None
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(cufe)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        qr_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        return qr_base64
    except Exception as e:
        logger.error(f"Error generando QR code: {e}")
        return None


def obtener_logo_base64_empresa(nit: str) -> Optional[str]:
    """
    Busca el logo de la empresa en media/logo/{nit}.*
    Similar a la función en bce/backend/core/views.py
    
    Args:
        nit: NIT de la empresa (sin puntos ni guiones)
    
    Returns:
        data URI con el logo en base64 o None si no se encuentra
    """
    try:
        nit_limpio = str(nit).strip().replace('.', '').replace('-', '')
        logger.info(f"🔍 [LOGO] Buscando logo para NIT: {nit_limpio}")
        
        # Buscar en media/logo/ (similar a bce/backend)
        base_dir = Path(settings.BASE_DIR)
        logo_dir = base_dir / 'media' / 'logo'
        
        # Si no existe, intentar desde la raíz del proyecto
        if not logo_dir.exists():
            logo_dir = base_dir.parent / 'media' / 'logo'
        
        if not logo_dir.exists():
            logger.warning(f"❌ [LOGO] El directorio {logo_dir} no existe")
            return None
        
        # Buscar archivos
        patron = str(logo_dir / f"{nit_limpio}.*")
        archivos_logo = glob.glob(patron)
        logger.info(f"📄 [LOGO] Archivos encontrados: {archivos_logo}")
        
        # Procesar archivos encontrados
        for archivo in archivos_logo:
            ext = os.path.splitext(archivo)[1].lower()
            if ext in ['.png', '.jpg', '.jpeg']:
                logger.info(f"✅ [LOGO] Cargando: {archivo}")
                
                with open(archivo, "rb") as img_file:
                    logo_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                
                mime_type = "image/png" if ext == '.png' else "image/jpeg"
                return f"data:{mime_type};base64,{logo_base64}"
        
        logger.warning(f"❌ [LOGO] No se encontró {nit_limpio}.* en {logo_dir}")
        return None
        
    except Exception as e:
        logger.error(f"❌ [LOGO] Error obteniendo logo: {e}", exc_info=True)
        return None


def numero_a_letras(numero: float) -> str:
    """
    Convierte un número a letras en español (copiado de bce/backend).
    """
    try:
        numero = round(float(numero), 2)
        entero = int(numero)
        decimal = int(round((numero - entero) * 100))
        
        if entero == 0:
            resultado_entero = "CERO"
        elif entero == 1:
            resultado_entero = "UN"
        else:
            resultado_entero = convertir_entero_a_letras(entero)
        
        if decimal == 0:
            resultado_decimal = "CON CERO CENTAVOS"
        else:
            if decimal == 1:
                resultado_decimal = f"CON {convertir_entero_a_letras(decimal)} CENTAVO"
            else:
                resultado_decimal = f"CON {convertir_entero_a_letras(decimal)} CENTAVOS"
        
        return f"{resultado_entero} PESOS {resultado_decimal} M/CTE"
    except (ValueError, TypeError):
        return "CERO PESOS CON CERO CENTAVOS M/CTE"

def convertir_entero_a_letras(numero: int) -> str:
    """
    Convierte la parte entera a letras (copiado de bce/backend).
    """
    centenas = ["", "CIEN", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", 
                "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]
    decenas = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", 
               "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
    unidades = ["", "UNO", "DOS", "TRES", "CUATRO", "CINCO", 
                "SEIS", "SIETE", "OCHO", "NUEVE"]
    especiales = ["", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", 
                  "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"]
    
    if numero == 0:
        return "CERO"
    
    texto = ""
    
    # Miles
    if numero >= 1000:
        miles_part = numero // 1000
        if miles_part == 1:
            texto += "MIL "
        else:
            texto += convertir_entero_a_letras(miles_part) + " MIL "
        numero %= 1000
    
    # Centenas
    if numero >= 100:
        centena = numero // 100
        if centena == 1 and numero % 100 != 0:
            texto += "CIENTO "
        else:
            texto += centenas[centena] + " "
        numero %= 100
    
    # Decenas y unidades
    if numero >= 10 and numero <= 19:
        texto += especiales[numero - 10] + " "
    else:
        if numero >= 20:
            decena = numero // 10
            texto += decenas[decena]
            if numero % 10 != 0:
                texto += " Y "
            numero %= 10
        
        if numero > 0:
            texto += unidades[numero] + " "
    
    return texto.strip()


def generar_pdf_factura_completa(factura_data: Dict[str, Any], logo_base64: Optional[str] = None) -> Optional[BytesIO]:
    """
    Genera PDF de factura completa usando ticket_template.html (mismo que bce/backend) con opciones 80mm.
    
    Args:
        factura_data: Datos de la factura obtenidos de consultar_datos_factura_para_pdf
        logo_base64: Logo de la empresa en base64 (opcional)
    
    Returns:
        BytesIO con el PDF generado o None si hay error
    """
    try:
        # Usar ticket_template.html (mismo que bce/backend)
        template_name = 'ticket_template.html'
        
        # Obtener CUFE de k.cufe
        cufe = factura_data.get('cufe', '').strip() if factura_data.get('cufe') else ''
        
        # Generar QR code solo si hay CUFE
        qr_base64 = None
        if cufe:
            qr_base64 = generar_qr_code(cufe)
        
        # Preparar contexto adaptado desde factura_data a formato ticket_template
        from datetime import datetime
        
        # Calcular totales de impuestos (solo si hay IVA)
        tax_totals = []
        iva_valor = factura_data.get('iva', 0)
        if iva_valor and float(iva_valor) > 0:
            tax_totals.append({
                'tax_name': 'IVA',
                'taxable_amount': f"{factura_data.get('subtotal', 0):.2f}",
                'percent': '19',
                'tax_amount': f"{iva_valor:.2f}"
            })
        
        # Preparar logo como data URI si existe (el template espera data URI completo)
        logo_data_uri = None
        if logo_base64:
            # Si ya viene como data URI, usarlo directamente; si no, agregar el prefijo
            if logo_base64.startswith('data:'):
                logo_data_uri = logo_base64
            else:
                logo_data_uri = f"data:image/png;base64,{logo_base64}"
        
        # Convertir total a letras
        total_en_letras = numero_a_letras(factura_data.get('total', 0))
        
        # Resolución: "Resolución: {p.resolucion} con numeración {numinifacele} - {numfinfacele} de {fecinifel} hasta {fecfinfel}"
        resolucion_texto = ''
        if factura_data.get('resolucion'):
            resolucion_texto = f"Resolución: {factura_data.get('resolucion', '')}"
            if factura_data.get('numinifacele') and factura_data.get('numfinfacele'):
                resolucion_texto += f" con numeración {factura_data.get('numinifacele')} - {factura_data.get('numfinfacele')}"
            if factura_data.get('fecinifel') and factura_data.get('fecfinfel'):
                resolucion_texto += f" de {factura_data.get('fecinifel')} hasta {factura_data.get('fecfinfel')}"
        
        context = {
            'document': {
                'prefix': factura_data.get('prefijo', ''),
                'number': factura_data.get('numero', ''),
                'date_issue': factura_data.get('fecha', ''),
                'cufe': cufe if cufe else 'Emitiendo...',  # Mostrar "Emitiendo..." si no hay CUFE
                'total_tax': f"{iva_valor:.2f}"
            },
            'request_api': {
                'company_name': factura_data.get('empresa_nombre', ''),
                'company_nit': factura_data.get('empresa_nit', ''),
                'company_address': factura_data.get('empresa_direccion', ''),
                'company_phone': factura_data.get('empresa_telefono', ''),
                'company_email': factura_data.get('empresa_email', ''),
                'prefix': factura_data.get('prefijo', ''),  # p.prefe
                'number': factura_data.get('numero', ''),  # k.numero
                'date': factura_data.get('fecha', ''),
                'time': factura_data.get('hora', ''),
                'customer': {
                    'name': factura_data.get('cliente_nombre', 'Consumidor Final'),
                    'identification_number': factura_data.get('cliente_nit', ''),
                    'dv': factura_data.get('cliente_dv', ''),
                    'address': factura_data.get('cliente_direccion', ''),
                    'phone': factura_data.get('cliente_telefono', ''),
                    'email': factura_data.get('cliente_email', '')
                },
                'invoice_lines': [
                    {
                        'invoiced_quantity': item.get('cantidad', item.get('quantity', 0)),
                        'description': item.get('descripcion', item.get('name', '')),
                        'code': item.get('codigo', ''),
                        'line_extension_amount': f"{item.get('subtotal', item.get('total', 0)):.2f}"
                    }
                    for item in factura_data.get('items', [])
                ],
                'tax_totals': tax_totals,  # Lista vacía si no hay impuestos
                'legal_monetary_totals': {
                    'tax_exclusive_amount': f"{factura_data.get('subtotal', 0):.2f}",
                    'payable_amount': f"{factura_data.get('total', 0):.2f}"
                },
                'payment_form': {
                    'payment_form_id': 1,  # Contado
                    'payment_method_id': 47  # Transferencia Débito
                },
                'notes': factura_data.get('observacion', ''),
                'resolution_number': resolucion_texto  # Texto completo de la resolución
            },
            'logo_base64': logo_data_uri,  # Data URI completo
            'qr_base64': qr_base64,  # Base64 sin prefijo (el template agrega data:image/png;base64,)
            'total_en_letras': total_en_letras,
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Opciones personalizadas para 80mm (igual que ticket_corto)
        custom_options = {
            'page-width': '80mm',
            'page-height': '297mm',
            'margin-top': '2mm',
            'margin-right': '2mm',
            'margin-bottom': '2mm',
            'margin-left': '8mm',
            'dpi': 200,
            'no-outline': True,
            'no-footer': True,
        }
        
        pdf_buffer = render_to_pdf(template_name, context, custom_options)
        
        if pdf_buffer:
            logger.info(f"✅ PDF de factura completa generado: {factura_data.get('prefijo')}-{factura_data.get('numero')}")
            return pdf_buffer
        else:
            logger.error("❌ No se pudo generar el PDF")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error generando PDF de factura completa: {e}", exc_info=True)
        return None


def generar_pdf_ticket_corto(factura_data: Dict[str, Any], logo_base64: Optional[str] = None) -> Optional[BytesIO]:
    """
    Genera PDF de ticket corto 80mm - básico con productos, cantidad, observaciones, fecha y hora.
    Usa ticket_corto.html con opciones para 80mm.
    
    Args:
        factura_data: Datos de la factura obtenidos de consultar_datos_factura_para_pdf
        logo_base64: Logo de la empresa en base64 (opcional)
    
    Returns:
        BytesIO con el PDF generado o None si hay error
    """
    try:
        # Usar template ticket_corto.html
        template_name = 'ticket_corto.html'
        
        # Preparar logo como data URI si existe
        logo_data_uri = None
        if logo_base64:
            if logo_base64.startswith('data:'):
                logo_data_uri = logo_base64
            else:
                logo_data_uri = f"data:image/png;base64,{logo_base64}"
        
        # Preparar contexto para ticket corto (solo lo esencial)
        context = {
            'request_api': {
                'company_name': factura_data.get('empresa_nombre', ''),
                'company_nit': factura_data.get('empresa_nit', ''),
                'prefix': factura_data.get('prefijo', ''),  # p.prefe
                'number': factura_data.get('numero', ''),  # k.numero
                'date': factura_data.get('fecha', ''),
                'time': factura_data.get('hora', ''),
                'invoice_lines': [
                    {
                        'invoiced_quantity': item.get('cantidad', item.get('quantity', 0)),
                        'description': item.get('descripcion', item.get('name', '')),
                    }
                    for item in factura_data.get('items', [])
                ],
                'legal_monetary_totals': {
                    'payable_amount': f"{factura_data.get('total', 0):.2f}"
                },
                'notes': factura_data.get('observacion', ''),
            },
            'logo_base64': logo_data_uri,  # Logo para el template
        }
        
        # Opciones personalizadas para 80mm
        custom_options = {
            'page-width': '80mm',
            'page-height': '297mm',
            'margin-top': '2mm',
            'margin-right': '2mm',
            'margin-bottom': '2mm',
            'margin-left': '8mm',
            'dpi': 200,
            'no-outline': True,
            'no-footer': True,
        }
        
        pdf_buffer = render_to_pdf(template_name, context, custom_options)
        
        if pdf_buffer:
            logger.info(f"✅ PDF de ticket corto generado: {factura_data.get('prefijo')}-{factura_data.get('numero')}")
            return pdf_buffer
        else:
            logger.error("❌ No se pudo generar el PDF")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error generando PDF de ticket corto: {e}", exc_info=True)
        return None


def generar_ticket_error_pdf(
    empresa_nit: str,
    empresa_nombre: str,
    empresa_direccion: str,
    empresa_telefono: str,
    empresa_email: str,
    monto_total: float,
    cart_items: List[Dict],
    error_message: str,
    referencia_pago: str,
    medio_pago_data: Optional[Dict] = None,
    invoice_data: Optional[Dict] = None,
    observacion: Optional[str] = None,
    fecha: Optional[str] = None,
    hora: Optional[str] = None
) -> Optional[BytesIO]:
    """
    Genera un ticket de error cuando falla la inserción en TNS pero el pago fue exitoso.
    Incluye toda la información del pago (últimos dígitos, ID transacción, etc.) para reclamos.
    Usa ticket_error.html con opciones para 80mm.
    """
    try:
        # Fecha y hora
        if not fecha:
            fecha = datetime.now().strftime("%Y-%m-%d")
        if not hora:
            hora = datetime.now().strftime("%H:%M:%S")
        
        # Obtener logo
        nit_limpio = str(empresa_nit).strip().replace('.', '').replace('-', '')
        logo_base64 = obtener_logo_base64_empresa(nit_limpio)
        
        # Usar template ticket_error.html
        template_name = 'ticket_error.html'
        
        # Calcular subtotal e IVA de los items
        subtotal = sum(item.get('price', 0) * item.get('quantity', 0) for item in cart_items)
        iva = subtotal * 0.19  # IVA 19%
        total = float(monto_total) if monto_total else (subtotal + iva)
        
        # Extraer información del cliente desde invoice_data
        cliente_nombre = 'Consumidor Final'
        cliente_nit = '0000000000'
        cliente_dv = '0'
        cliente_telefono = ''
        
        if invoice_data:
            cliente_nombre = invoice_data.get('name', cliente_nombre)
            cliente_nit = invoice_data.get('document', cliente_nit)
            cliente_telefono = invoice_data.get('phone', cliente_telefono)
        
        # Extraer información del pago desde medio_pago_data
        payment_data = {}
        transaction_id = referencia_pago
        
        if medio_pago_data:
            payment_data = {
                'numero_aprobacion': medio_pago_data.get('numero_aprobacion', ''),
                'ultimos_digitos': medio_pago_data.get('ultimos_digitos', ''),
                'franquicia': medio_pago_data.get('franquicia', ''),
                'tipo_cuenta': medio_pago_data.get('tipo_cuenta', ''),
                'referencia': medio_pago_data.get('referencia', referencia_pago),
                'rrn': medio_pago_data.get('rrn', ''),
                'codigo_autorizacion': medio_pago_data.get('codigo_autorizacion', ''),
            }
            # ID de transacción puede venir en diferentes campos
            transaction_id = (
                medio_pago_data.get('transaction_id') or 
                medio_pago_data.get('referencia') or 
                medio_pago_data.get('numero_aprobacion') or 
                referencia_pago
            )
        
        # Preparar contexto para el template ticket_error.html
        context = {
            'request_api': {
                'company_name': empresa_nombre,
                'company_nit': empresa_nit,
                'prefix': 'ERR',
                'number': referencia_pago[-6:] if len(referencia_pago) >= 6 else referencia_pago,
                'date': fecha,
                'time': hora,
                'referencia': referencia_pago,
                'observaciones': observacion or '',
                'invoice_lines': [
                    {
                        'invoiced_quantity': item.get('quantity', 0),
                        'description': item.get('name', ''),
                    }
                    for item in cart_items
                ],
                'legal_monetary_totals': {
                    'payable_amount': f"{total:.2f}"
                },
                'customer': {
                    'name': cliente_nombre,
                    'identification_number': cliente_nit,
                    'dv': cliente_dv,
                    'phone': cliente_telefono,
                },
                'payment_data': payment_data,
                'transaction_id': transaction_id,
            },
        }
        
        # Opciones personalizadas para 80mm
        custom_options = {
            'page-width': '80mm',
            'page-height': '297mm',
            'margin-top': '2mm',
            'margin-right': '2mm',
            'margin-bottom': '2mm',
            'margin-left': '8mm',
            'dpi': 200,
            'no-outline': True,
            'no-footer': True,
        }
        
        pdf_buffer = render_to_pdf(template_name, context, custom_options)
        
        if pdf_buffer:
            logger.info(f"✅ PDF de ticket de error generado: {referencia_pago}")
            return pdf_buffer
        else:
            logger.error("❌ No se pudo generar el PDF del ticket de error")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error generando PDF de ticket de error: {e}", exc_info=True)
        return None
