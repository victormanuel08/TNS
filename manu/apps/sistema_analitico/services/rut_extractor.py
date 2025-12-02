"""
Servicio para extraer información de PDFs de RUT
"""
import re
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from django.core.cache import cache

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    try:
        import PyPDF2
        PYPDF2_AVAILABLE = True
    except ImportError:
        PYPDF2_AVAILABLE = False


def normalize_nit(nit: str) -> str:
    """
    Normaliza NIT eliminando puntos, guiones y espacios.
    Ejemplos:
    - "900.869.750-0" -> "9008697500"
    - "900869750-0" -> "9008697500"
    - "9008697500" -> "9008697500"
    """
    if not nit:
        return ''
    return ''.join(c for c in str(nit) if c.isdigit())


def extract_nit_from_text(text: str) -> Optional[Tuple[str, str]]:
    """
    Extrae NIT y DV del texto del PDF.
    Retorna (nit, dv) o None si no se encuentra.
    """
    # Buscar patrones como "9 0 0 8 6 9 7 5 0 0" o "9008697500"
    # El NIT suele estar después de "Número de Identificación Tributaria (NIT)"
    patterns = [
        r'Número de Identificación Tributaria.*?NIT[\)\s]*(\d[\d\s]*?)\s+(\d)',  # Con espacios
        r'NIT[\)\s]*(\d[\d\s]*?)\s+(\d)',  # Más directo
        r'(\d{9,15})\s+(\d)',  # NIT largo seguido de un dígito
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            nit_raw = match.group(1).replace(' ', '')
            dv = match.group(2)
            if len(nit_raw) >= 9:  # NIT válido tiene al menos 9 dígitos
                return (nit_raw, dv)
    
    # Buscar en formato con puntos y guiones: "900.869.750-0"
    pattern_formatted = r'(\d{1,3}(?:\.\d{3}){2,4})-(\d)'
    match = re.search(pattern_formatted, text)
    if match:
        nit_raw = match.group(1).replace('.', '')
        dv = match.group(2)
        return (nit_raw, dv)
    
    return None


def parse_date(date_str: str) -> Optional[datetime]:
    """Intenta parsear una fecha en formato DDMMYYYY o YYYYMMDD"""
    if not date_str:
        return None
    
    # Limpiar espacios
    date_str = date_str.replace(' ', '')
    
    # Formato YYYYMMDD
    if len(date_str) == 8:
        try:
            return datetime.strptime(date_str, '%Y%m%d')
        except:
            pass
    
    # Formato DDMMYYYY
    if len(date_str) == 8:
        try:
            return datetime.strptime(date_str, '%d%m%Y')
        except:
            pass
    
    return None


def extract_rut_data_from_pdf(pdf_file) -> Dict:
    """
    Extrae datos del RUT desde un archivo PDF.
    Retorna un diccionario con los campos extraídos.
    Basado en el formato real del RUT colombiano.
    """
    if not PDFPLUMBER_AVAILABLE and not PYPDF2_AVAILABLE:
        raise ImportError("Se requiere pdfplumber o PyPDF2 para extraer datos del PDF")
    
    texto_completo = ""
    
    # Leer PDF
    if PDFPLUMBER_AVAILABLE:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                texto_completo += page.extract_text() or ""
    elif PYPDF2_AVAILABLE:
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            texto_completo += page.extract_text() or ""
    
    # Extraer NIT y DV
    nit_dv = extract_nit_from_text(texto_completo)
    if not nit_dv:
        raise ValueError("No se pudo extraer el NIT del PDF. Por favor, proporciona el NIT manualmente.")
    
    nit, dv = nit_dv
    nit_normalizado = normalize_nit(nit)
    
    # Inicializar datos
    data = {
        'nit': nit,
        'nit_normalizado': nit_normalizado,
        'dv': dv,
    }
    
    # Extraer Número de Formulario
    form_match = re.search(r'Número de formulario\s+(\d+)', texto_completo, re.IGNORECASE)
    if form_match:
        data['numero_formulario'] = form_match.group(1).strip()
    
    # Extraer Tipo de Contribuyente
    tipo_match = re.search(r'Tipo de contribuyente\s+Persona\s+(jurídica|natural)', texto_completo, re.IGNORECASE)
    if tipo_match:
        tipo = tipo_match.group(1).lower()
        data['tipo_contribuyente'] = 'persona_juridica' if 'jurídica' in tipo or 'juridica' in tipo else 'persona_natural'
    
    # Extraer Razón Social (formato: "35. Razón social\nCONSTRUCTORES UNIDOS DEL SIGLO 21 S.A.S")
    razon_match = re.search(r'Razón social\s+([A-Z][A-Z0-9\s\.\&]+(?:S\.A\.S|S\.A|LTDA|S\.A\.S\.|INC)?)', texto_completo, re.IGNORECASE | re.MULTILINE)
    if razon_match:
        data['razon_social'] = razon_match.group(1).strip()
    
    # Extraer Nombre Comercial
    nombre_com_match = re.search(r'Nombre comercial\s+([A-Z][A-Z0-9\s\.]+)', texto_completo, re.IGNORECASE | re.MULTILINE)
    if nombre_com_match:
        data['nombre_comercial'] = nombre_com_match.group(1).strip()
    
    # Extraer Sigla
    sigla_match = re.search(r'Sigla\s+([A-Z0-9\s\.]+)', texto_completo, re.IGNORECASE | re.MULTILINE)
    if sigla_match:
        data['sigla'] = sigla_match.group(1).strip()
    
    # Extraer Dirección Principal
    direccion_match = re.search(r'Dirección principal\s+([A-Z0-9\s\.\#\-]+)', texto_completo, re.IGNORECASE | re.MULTILINE)
    if direccion_match:
        data['direccion_principal'] = direccion_match.group(1).strip()
    
    # Extraer Email
    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', texto_completo)
    if email_match:
        data['email'] = email_match.group(1).strip().lower()
    
    # Extraer Teléfono (formato: "44. Teléfono 1 3 1 4 3 3 0 2 5 2 4")
    telefono_match = re.search(r'Teléfono\s+1\s+(\d[\d\s]+)', texto_completo, re.IGNORECASE)
    if telefono_match:
        telefono = telefono_match.group(1).replace(' ', '')
        data['telefono_1'] = telefono
    
    # Extraer Código Postal
    codigo_postal_match = re.search(r'Código postal\s+(\d+)', texto_completo, re.IGNORECASE)
    if codigo_postal_match:
        data['codigo_postal'] = codigo_postal_match.group(1).strip()
    
    # Extraer Ciudad y Departamento (formato: "5 4 Cúcuta 0 0 1" o "Norte de Santander 5 4 Cúcuta 0 0 1")
    # Buscar patrón: Departamento código nombre Ciudad código
    dept_ciudad_match = re.search(r'(\d+)\s+([A-Z][A-Z\s]+)\s+(\d+)\s+([A-Z][A-Z\s]+)\s+(\d+)', texto_completo)
    if dept_ciudad_match:
        # Puede ser: código_dept nombre_dept código_ciudad nombre_ciudad código
        data['departamento_codigo'] = dept_ciudad_match.group(1).strip()
        data['departamento_nombre'] = dept_ciudad_match.group(2).strip()
        data['ciudad_codigo'] = dept_ciudad_match.group(3).strip()
        data['ciudad_nombre'] = dept_ciudad_match.group(4).strip()
    
    # Extraer Dirección Seccional
    seccional_match = re.search(r'Dirección seccional\s+([A-Z][A-Z\s]+)', texto_completo, re.IGNORECASE)
    if seccional_match:
        data['direccion_seccional'] = seccional_match.group(1).strip()
    
    # Extraer Buzón Electrónico
    buzon_match = re.search(r'Buzón electrónico\s+(\d+)', texto_completo, re.IGNORECASE)
    if buzon_match:
        data['buzon_electronico'] = buzon_match.group(1).strip()
    
    # Extraer Actividad Principal CIIU (formato: "4 2 9 0 2" o "42902")
    actividad_principal_match = re.search(r'Actividad principal.*?Código\s+(\d[\d\s]+)', texto_completo, re.IGNORECASE | re.DOTALL)
    if actividad_principal_match:
        codigo = actividad_principal_match.group(1).replace(' ', '').strip()
        if len(codigo) >= 4:
            data['actividad_principal_ciiu'] = codigo[:5]  # CIIU tiene hasta 5 dígitos
    
    # Extraer Fecha de Actividad Principal (formato: "2 0 1 5 0 7 0 1")
    fecha_act_match = re.search(r'Fecha inicio actividad\s+(\d[\d\s]+)', texto_completo, re.IGNORECASE)
    if fecha_act_match:
        fecha_str = fecha_act_match.group(1).replace(' ', '')
        fecha_parsed = parse_date(fecha_str)
        if fecha_parsed:
            data['actividad_principal_fecha_inicio'] = fecha_parsed.date()
    
    # Extraer Responsabilidades (códigos como "7 9 1 4 4 2 4 7 4 8 5 2 5 5")
    responsabilidades_match = re.search(r'53\.\s*Código\s+(\d[\d\s]+)', texto_completo, re.IGNORECASE)
    if responsabilidades_match:
        codigos_str = responsabilidades_match.group(1).replace(' ', '')
        # Separar en códigos de 2 dígitos
        codigos = [codigos_str[i:i+2] for i in range(0, len(codigos_str), 2) if i+2 <= len(codigos_str)]
        data['responsabilidades_codigos'] = [int(c) for c in codigos if c.isdigit()]
        
        # Mapear códigos comunes a booleanos
        codigos_set = set(data['responsabilidades_codigos'])
        data['responsable_iva'] = 48 in codigos_set  # Código 48 = IVA
        data['autorretenedor'] = 7 in codigos_set or 9 in codigos_set  # Retención
        data['obligado_contabilidad'] = 42 in codigos_set
        data['regimen_simple'] = 47 in codigos_set
        data['facturador_electronico'] = 52 in codigos_set
        data['informante_exogena'] = 14 in codigos_set
        data['informante_beneficiarios_finales'] = 55 in codigos_set
    
    # Extraer Representante Legal (formato: "984. Nombre GELVEZ MARIO ALBERTO")
    rep_nombre_match = re.search(r'Nombre\s+(GELVEZ|([A-Z]+))\s+([A-Z]+)\s+([A-Z]+)', texto_completo)
    if rep_nombre_match:
        data['representante_legal_primer_apellido'] = rep_nombre_match.group(1).strip()
        data['representante_legal_primer_nombre'] = rep_nombre_match.group(3).strip() if rep_nombre_match.group(3) else ''
        data['representante_legal_otros_nombres'] = rep_nombre_match.group(4).strip() if rep_nombre_match.group(4) else ''
    
    # Extraer Tipo de Documento del Representante
    rep_tipo_doc_match = re.search(r'Tipo de documento\s+(Cédula|NIT|CE|Pasaporte)', texto_completo, re.IGNORECASE)
    if rep_tipo_doc_match:
        tipo_doc = rep_tipo_doc_match.group(1).strip()
        if 'Cédula' in tipo_doc:
            data['representante_legal_tipo_doc'] = 'CC'
        elif 'NIT' in tipo_doc:
            data['representante_legal_tipo_doc'] = 'NIT'
        else:
            data['representante_legal_tipo_doc'] = tipo_doc
    
    # Extraer Número de Documento del Representante
    rep_num_doc_match = re.search(r'Número de identificación\s+(\d[\d\s]+)', texto_completo, re.IGNORECASE)
    if rep_num_doc_match:
        num_doc = rep_num_doc_match.group(1).replace(' ', '').strip()
        data['representante_legal_numero_doc'] = num_doc
    
    # Extraer Fecha de Constitución (formato: "2 0 1 5 0 7 0 1")
    constitucion_fecha_match = re.search(r'Fecha\s+(\d[\d\s]+)', texto_completo, re.IGNORECASE)
    if constitucion_fecha_match:
        fecha_str = constitucion_fecha_match.group(1).replace(' ', '')
        fecha_parsed = parse_date(fecha_str)
        if fecha_parsed:
            data['constitucion_fecha'] = fecha_parsed.date()
    
    # Extraer Matrícula Mercantil
    matricula_match = re.search(r'Matrícula mercantil\s+(\d+)', texto_completo, re.IGNORECASE)
    if matricula_match:
        data['matricula_mercantil'] = matricula_match.group(1).strip()
    
    # Extraer Fecha de Registro
    registro_fecha_match = re.search(r'Fecha de registro\s+(\d[\d\s]+)', texto_completo, re.IGNORECASE)
    if registro_fecha_match:
        fecha_str = registro_fecha_match.group(1).replace(' ', '')
        fecha_parsed = parse_date(fecha_str)
        if fecha_parsed:
            data['registro_fecha'] = fecha_parsed.date()
    
    # País por defecto
    data['pais'] = 'COLOMBIA'
    
    # Intentar obtener información completa de códigos CIIU encontrados (opcional, no bloquea)
    # Esto se hará de forma asíncrona en el ViewSet, pero aquí podemos preparar los códigos
    codigos_ciiu_encontrados = []
    if data.get('actividad_principal_ciiu'):
        codigos_ciiu_encontrados.append(data['actividad_principal_ciiu'])
    if data.get('actividad_secundaria_ciiu'):
        codigos_ciiu_encontrados.append(data['actividad_secundaria_ciiu'])
    if data.get('otras_actividades_ciiu'):
        codigos_ciiu_encontrados.append(data['otras_actividades_ciiu'])
    
    # Guardar códigos encontrados para procesamiento posterior
    data['_codigos_ciiu_encontrados'] = codigos_ciiu_encontrados
    
    return data

