"""
Servicio para extraer información de PDFs de RUT
Basado en el extractor de BCE pero adaptado al modelo de MANU
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
    """
    if not nit:
        return ''
    return ''.join(c for c in str(nit) if c.isdigit())


def parse_date(date_str: str) -> Optional[datetime]:
    """Intenta parsear una fecha en formato YYYYMMDD"""
    if not date_str:
        return None
    
    # Limpiar espacios
    date_str = date_str.replace(' ', '').strip()
    
    if len(date_str) == 8:
        try:
            return datetime.strptime(date_str, '%Y%m%d')
        except:
            pass
    
    return None


def extract_rut_data_from_pdf(pdf_file) -> Dict:
    """
    Extrae datos del RUT desde un archivo PDF.
    Basado en el extractor de BCE pero adaptado al modelo de MANU.
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
    
    # Guardar texto completo para debugging
    data = {'_texto_completo': texto_completo}
    
    # ========== EXTRACCIÓN GENERAL ==========
    # Número de formulario
    if match := re.search(r"4\.\s*Número de formulario\s*(\d+)", texto_completo):
        data['numero_formulario'] = match.group(1).strip()
    
    # NIT y DV - método de BCE (más robusto) con múltiples patrones
    nit_encontrado = False
    
    # Patrón 1: Método original de BCE
    nit_match = re.search(
        r"5\.\s*N(?:úmero|IT)[^\n]*Tributaria\s*\(?NIT\)?[^\n]*\n([\d\s]+[^\n]*)", 
        texto_completo, 
        re.IGNORECASE
    )
    if nit_match:
        linea_nit = nit_match.group(1).strip()
        # ✅ LÓGICA CORREGIDA: Capturar todos los dígitos hasta que empiecen las letras
        # El último dígito antes de las letras es el DV, los anteriores son el NIT
        # Ejemplo: "4 1 0 3 1 5 4 3 Impuestos de Cúcuta 7" 
        #   -> Capturar: "4 1 0 3 1 5 4 3" (hasta antes de "Impuestos")
        #   -> NIT: "4103154", DV: "3" (último dígito antes de las letras)
        #   -> El "7" es parte del código de "Impuestos de Cúcuta", NO es el DV
        
        # Buscar donde empiezan las letras (dirección seccional)
        patron_digitos = re.compile(r'^([\d\s]+?)(?=[A-Za-zÁÉÍÓÚáéíóúÑñ])')
        match_digitos = patron_digitos.match(linea_nit)
        
        if match_digitos:
            # Capturar todos los dígitos hasta antes de las letras
            numeros_con_dv = match_digitos.group(1).replace(" ", "").strip()
            
            # ✅ LÓGICA: El último dígito antes de las letras es el DV
            # Ejemplo: "1 0 0 5 0 3 8 6 3 8 2" -> NIT: "1005038638", DV: "2"
            # Ejemplo: "4 1 0 3 1 5 4 3" -> NIT: "4103154", DV: "3"
            if len(numeros_con_dv) >= 9:
                # Si tiene 9+ dígitos, el último es el DV
                # Ejemplo: "10050386382" -> NIT: "1005038638", DV: "2"
                nit = numeros_con_dv[:-1]
                dv = numeros_con_dv[-1]
            elif len(numeros_con_dv) == 8:
                # Si tiene exactamente 8 dígitos, el último es el DV
                # Ejemplo: "41031543" -> NIT: "4103154", DV: "3"
                nit = numeros_con_dv[:-1]
                dv = numeros_con_dv[-1]
            else:
                # Si tiene menos de 8 dígitos, algo está mal
                nit = numeros_con_dv
                dv = ''
            
            # ✅ CORRECCIÓN: Validar longitud del NIT (sin DV) - mínimo 7 dígitos (algunos NITs tienen 7 dígitos + 1 DV = 8 total)
            if 7 <= len(nit) <= 11:  # Validar longitud del NIT (sin DV)
                # ✅ IMPORTANTE: Guardar NIT con formato completo (con guión y DV) para que normalize_nit_and_extract_dv lo procese correctamente
                # Si no, save() asumirá que el último dígito es el DV y lo quitará
                if dv:
                    data['nit'] = f"{nit}-{dv}"  # Formato: "4103154-3"
                else:
                    data['nit'] = nit
                data['nit_normalizado'] = nit  # Sin DV
                data['dv'] = dv
                nit_encontrado = True
        else:
            # Fallback: Si no encuentra letras, usar el método anterior
            patron = re.compile(r'^([\d\s]+)([^\d]+)(\d+)$')
            partes = patron.match(linea_nit)
            
            if partes:
                numeros = partes.group(1).replace(" ", "")
                if len(numeros) >= 9:
                    nit = numeros[:-1]
                    dv = numeros[-1]
                elif len(numeros) == 8:
                    nit = numeros[:-1]
                    dv = numeros[-1]
                else:
                    nit = numeros
                    dv = ''
                
                # ✅ CORRECCIÓN: Validar longitud del NIT (sin DV) - mínimo 7 dígitos
                if 7 <= len(nit) <= 11:
                    # ✅ IMPORTANTE: Guardar NIT con formato completo (con guión y DV)
                    if dv:
                        data['nit'] = f"{nit}-{dv}"  # Formato: "4103154-3"
                    else:
                        data['nit'] = nit
                    data['nit_normalizado'] = nit  # Sin DV
                    data['dv'] = dv
                    nit_encontrado = True
    
    # Patrón 2: Buscar NIT y DV por separado (más flexible)
    # Este patrón busca cuando el campo "6. DV" está explícitamente separado
    if not nit_encontrado:
        nit_dv_match = re.search(
            r'5\.\s*N(?:úmero|IT)[^\n]*Tributaria[^\n]*\(?NIT\)?[^\n]*\n([\d\s]{8,15})\s*\n\s*6\.\s*DV[^\n]*\n\s*(\d)', 
            texto_completo, 
            re.IGNORECASE | re.DOTALL
        )
        if nit_dv_match:
            nit_raw = nit_dv_match.group(1).replace(' ', '').replace('\n', '').strip()
            dv = nit_dv_match.group(2).strip()
            # ✅ CORRECCIÓN: Cuando el campo "6. DV" está separado, el NIT NO incluye el DV
            # Ejemplo: NIT: "1005038638", DV: "2" (separados)
            # El nit_raw ya es el NIT completo, NO necesita quitar el último dígito
            nit = nit_raw
            if 8 <= len(nit) <= 11:
                # ✅ IMPORTANTE: Guardar NIT con formato completo (con guión y DV) para que normalize_nit_and_extract_dv lo procese correctamente
                if dv:
                    data['nit'] = f"{nit}-{dv}"  # Formato: "1005038638-2"
                else:
                    data['nit'] = nit
                data['nit_normalizado'] = nit  # Sin DV
                data['dv'] = dv
                nit_encontrado = True
    
    # Patrón 3: Buscar cualquier secuencia de 9-11 dígitos después de "5. Número" o "5. NIT"
    if not nit_encontrado:
        nit_pattern3 = re.search(
            r'5\.\s*N(?:úmero|IT)[^\n]*Tributaria[^\n]*\(?NIT\)?[^\n]*\n\s*([\d\s]{9,15})',
            texto_completo,
            re.IGNORECASE
        )
        if nit_pattern3:
            nit_raw = nit_pattern3.group(1).replace(' ', '').replace('\n', '').strip()
            if 8 <= len(nit_raw) <= 11:
                # Si tiene 9+ dígitos, el último es el DV; si tiene 8, todos son NIT
                if len(nit_raw) >= 9:
                    nit = nit_raw[:-1]
                    dv = nit_raw[-1]
                else:
                    nit = nit_raw
                    dv = ''
                # ✅ IMPORTANTE: Guardar NIT con formato completo (con guión y DV)
                if dv:
                    data['nit'] = f"{nit}-{dv}"  # Formato: "1005038638-2"
                else:
                    data['nit'] = nit
                data['nit_normalizado'] = nit  # Sin DV
                data['dv'] = dv
                nit_encontrado = True
    
    # Patrón 4: Buscar en formato "NIT: 123456789-0" o similar
    if not nit_encontrado:
        nit_pattern4 = re.search(
            r'(?:NIT|Nit|nit)[\s:]*([\d]{8,11})[\s\-]*(\d)?',
            texto_completo,
            re.IGNORECASE
        )
        if nit_pattern4:
            nit_raw = nit_pattern4.group(1)
            dv = nit_pattern4.group(2) if nit_pattern4.group(2) else ''
            if 9 <= len(nit_raw) <= 11:
                if dv:
                    # ✅ IMPORTANTE: Guardar NIT con formato completo (con guión y DV)
                    data['nit'] = f"{nit_raw}-{dv}"  # Formato: "1005038638-2"
                    data['nit_normalizado'] = nit_raw  # Sin DV
                    data['dv'] = dv
                else:
                    # Si no hay DV separado, asumir que está al final
                    nit = nit_raw[:-1]
                    dv = nit_raw[-1]
                    data['nit'] = f"{nit}-{dv}"  # Formato: "1005038638-2"
                    data['nit_normalizado'] = nit  # Sin DV
                    data['dv'] = dv
                nit_encontrado = True
    
    # Patrón 5: Buscar cualquier secuencia de 8-11 dígitos cerca de "Identificación" o "Número"
    if not nit_encontrado:
        # Buscar después de "Identificación Tributaria" o "Número de Identificación"
        nit_pattern5 = re.search(
            r'(?:Identificación\s+Tributaria|Número\s+de\s+Identificación)[^\d]*([\d\s]{8,15})',
            texto_completo,
            re.IGNORECASE
        )
        if nit_pattern5:
            nit_raw = nit_pattern5.group(1).replace(' ', '').replace('\n', '').strip()
            if 8 <= len(nit_raw) <= 11:
                # Si tiene 9+ dígitos, asumir que el último es DV
                if len(nit_raw) >= 9:
                    nit = nit_raw[:-1]
                    dv = nit_raw[-1]
                    # ✅ IMPORTANTE: Guardar NIT con formato completo (con guión y DV)
                    data['nit'] = f"{nit}-{dv}"  # Formato: "1005038638-2"
                    data['nit_normalizado'] = nit  # Sin DV
                    data['dv'] = dv
                else:
                    data['nit'] = nit_raw
                    data['nit_normalizado'] = nit_raw
                    data['dv'] = ''
                nit_encontrado = True
    
    # Patrón 6: Buscar en la línea que contiene "5." y números después
    if not nit_encontrado:
        # Buscar línea que empieza con "5." y contiene números
        nit_pattern6 = re.search(
            r'5\.\s*[^\n]*\n\s*([\d\s]{8,15})',
            texto_completo,
            re.IGNORECASE | re.MULTILINE
        )
        if nit_pattern6:
            nit_raw = nit_pattern6.group(1).replace(' ', '').replace('\n', '').strip()
            if 8 <= len(nit_raw) <= 11:
                if len(nit_raw) >= 9:
                    nit = nit_raw[:-1]
                    dv = nit_raw[-1]
                    # ✅ IMPORTANTE: Guardar NIT con formato completo (con guión y DV)
                    data['nit'] = f"{nit}-{dv}"  # Formato: "1005038638-2"
                    data['nit_normalizado'] = nit  # Sin DV
                    data['dv'] = dv
                else:
                    data['nit'] = nit_raw
                    data['nit_normalizado'] = nit_raw
                    data['dv'] = ''
                nit_encontrado = True
    
    # Patrón 7: Buscar cualquier secuencia de 8-11 dígitos consecutivos en las primeras 2000 líneas
    if not nit_encontrado:
        # Buscar en las primeras líneas del documento (donde suele estar el NIT)
        primeras_lineas = '\n'.join(texto_completo.split('\n')[:50])
        todos_los_numeros = re.findall(r'\b\d{8,11}\b', primeras_lineas)
        if todos_los_numeros:
            # Tomar el primero que parezca un NIT (8-11 dígitos)
            for num in todos_los_numeros:
                if 8 <= len(num) <= 11:
                    if len(num) >= 9:
                        nit = num[:-1]
                        dv = num[-1]
                        # ✅ IMPORTANTE: Guardar NIT con formato completo (con guión y DV)
                        data['nit'] = f"{nit}-{dv}"  # Formato: "1005038638-2"
                        data['nit_normalizado'] = nit  # Sin DV
                        data['dv'] = dv
                    else:
                        data['nit'] = num
                        data['nit_normalizado'] = num
                        data['dv'] = ''
                    nit_encontrado = True
                    break
    
    if not nit_encontrado:
        # Guardar contexto para debugging
        contexto_nit = texto_completo[:2000] if len(texto_completo) > 2000 else texto_completo
        raise ValueError(
            f"No se pudo extraer el NIT del PDF. Por favor, proporciona el NIT manualmente.\n"
            f"Contexto extraído (primeros 2000 caracteres):\n{contexto_nit[:500]}..."
        )
    
    # Dirección seccional
    if match := re.search(r"12\.\s*Dirección seccional\s*\n([^\n]+)", texto_completo):
        data['direccion_seccional'] = match.group(1).strip()
    
    # Buzón electrónico
    if match := re.search(r"14\.\s*Buzón electrónico\s*(\d+)", texto_completo):
        data['buzon_electronico'] = match.group(1).strip()
    
    # ========== IDENTIFICACIÓN ==========
    # Tipo de contribuyente
    if match := re.search(r"24\.\s*Tipo de contribuyente[\s\S]*?\n\s*([^\d\n]+)", texto_completo):
        tipo = match.group(1).strip()
        if "jurídica" in tipo.lower() or "juridica" in tipo.lower():
            data['tipo_contribuyente'] = 'persona_juridica'
        elif "natural" in tipo.lower():
            data['tipo_contribuyente'] = 'persona_natural'
    
    # ========== NOMBRES PARA PERSONAS NATURALES (campos 31-34) ==========
    # Los campos 31-34 pueden estar en una sola línea: "31. Primer apellido 32. Segundo apellido 33. Primer nombre 34. Otros nombres\nPEÑALOZA OBANDO JAVIER ALEXANDER"
    # O en líneas separadas
    
    # Intentar patrón de una sola línea primero (más común)
    nombres_linea = re.search(
        r"31\.\s*Primer apellido\s*32\.\s*Segundo apellido\s*33\.\s*Primer nombre\s*34\.\s*Otros nombres\s*\n([^\n]+)",
        texto_completo,
        re.IGNORECASE
    )
    if nombres_linea:
        nombres_completos = nombres_linea.group(1).strip()
        partes = nombres_completos.split()
        if len(partes) >= 2:
            # Asumir: apellido1 apellido2 nombre1 nombre2...
            if len(partes) == 2:
                data['persona_natural_primer_apellido'] = partes[0]
                data['persona_natural_primer_nombre'] = partes[1]
            elif len(partes) == 3:
                data['persona_natural_primer_apellido'] = partes[0]
                data['persona_natural_segundo_apellido'] = partes[1]
                data['persona_natural_primer_nombre'] = partes[2]
            elif len(partes) >= 4:
                data['persona_natural_primer_apellido'] = partes[0]
                data['persona_natural_segundo_apellido'] = partes[1]
                data['persona_natural_primer_nombre'] = partes[2]
                data['persona_natural_otros_nombres'] = ' '.join(partes[3:])
    else:
        # Intentar campos separados
        if match := re.search(r"31\.\s*Primer apellido\s*\n([^\n]+)", texto_completo):
            data['persona_natural_primer_apellido'] = match.group(1).strip()
        
        if match := re.search(r"32\.\s*Segundo apellido\s*\n([^\n]+)", texto_completo):
            data['persona_natural_segundo_apellido'] = match.group(1).strip()
        
        if match := re.search(r"33\.\s*Primer nombre\s*\n([^\n]+)", texto_completo):
            data['persona_natural_primer_nombre'] = match.group(1).strip()
        
        if match := re.search(r"34\.\s*Otros nombres\s*\n([^\n]+)", texto_completo):
            data['persona_natural_otros_nombres'] = match.group(1).strip()
    
    # Razón social (campo 35) - LÓGICA ORIGINAL: Solo capturar hasta el siguiente campo numerado
    # Evitar capturar "36. Nombre comercial" o "37. Sigla" si el campo 35 está vacío
    if match := re.search(r"35\.\s*Razón social\s*\n([^\n]+?)(?=\n\s*36\.|\n\s*37\.|\n\s*\d+\.|$)", texto_completo, re.IGNORECASE):
        razon_social_raw = match.group(1).strip()
        # Solo asignar si no es un campo numerado (evitar capturar "36. Nombre comercial 37. Sigla")
        if razon_social_raw and not razon_social_raw.startswith('36.') and not razon_social_raw.startswith('37.'):
            data['razon_social'] = razon_social_raw
    
    # Nombre comercial (campo 36) - método de BCE mejorado
    if match := re.search(r"36\.\s*Nombre comercial\s*\n(.*?)(?=\n37\.\s*Sigla|\n38\.\s*País|\n\d+\.|$)", texto_completo, re.DOTALL):
        raw_value = match.group(1).strip()
        # Limpiar cualquier texto residual que no sea nombre comercial
        raw_value = re.sub(r'\s+37\.\s*Sigla.*$', '', raw_value, flags=re.IGNORECASE)
        raw_value = re.sub(r'\s+UBICACI[ÓO]N.*$', '', raw_value, flags=re.IGNORECASE)
        if any(c.isalnum() for c in raw_value):
            nombre_comercial = " ".join(raw_value.split())
            data['nombre_comercial'] = nombre_comercial
    
    # Sigla (campo 37) - método mejorado
    if match := re.search(r"37\.\s*Sigla\s*\n(.*?)(?=\n38\.\s*País|\n\d+\.|UBICACI[ÓO]N|$)", texto_completo, re.DOTALL | re.IGNORECASE):
        sigla = match.group(1).strip()
        # Limpiar cualquier texto residual
        sigla = re.sub(r'\s+UBICACI[ÓO]N.*$', '', sigla, flags=re.IGNORECASE)
        sigla = re.sub(r'\s+38\.\s*País.*$', '', sigla, flags=re.IGNORECASE)
        sigla = " ".join(sigla.split())
        data['sigla'] = sigla
    
    # ========== UBICACIÓN ==========
    # Método de BCE: extraer bloque completo entre "38. País" y "41. Dirección principal"
    bloque_ubicacion = re.search(
        r"38\.\s*País.*?40\.\s*Ciudad/Municipio\s*\n(.+?)\n41\.\s*Dirección principal",
        texto_completo, 
        re.DOTALL
    )
    
    if bloque_ubicacion:
        linea = bloque_ubicacion.group(1).strip()
        # Regex mejorado para nombres con tildes
        componentes = re.findall(
            r"([A-Za-zÁÉÍÓÚÜÑáéíóúñü\s]+?)\s*?(\d+(?:\s*\d+)*)", 
            linea, 
            re.IGNORECASE
        )
        
        if len(componentes) >= 3:
            # País
            data['pais'] = componentes[0][0].strip().title()
            # Departamento
            data['departamento_nombre'] = componentes[1][0].strip().title()
            data['departamento_codigo'] = componentes[1][1].replace(" ", "")
            # Ciudad
            ciudad_cruda = componentes[2][0].strip()
            data['ciudad_nombre'] = ciudad_cruda.title()
            data['ciudad_codigo'] = componentes[2][1].replace(" ", "")
    else:
        data['pais'] = 'COLOMBIA'
    
    # Dirección principal
    if match := re.search(r"41\.\s*Dirección principal\s*\n(.+?)(?=\n\d+\.|$)", texto_completo, re.DOTALL):
        data['direccion_principal'] = match.group(1).replace("\n", " ").strip()
    
    # Email
    if match := re.search(r"42\.\s*Correo electrónico\s*(\S+@\S+)", texto_completo):
        data['email'] = match.group(1).strip().lower()
    
    # Código postal (campo 43) - debe estar vacío si no hay valor, no capturar el siguiente número
    if match := re.search(r"43\.\s*Código postal\s*\n([^\n\d]*?)(?=\n44\.|$)", texto_completo, re.DOTALL):
        codigo_postal = match.group(1).strip()
        # Solo asignar si hay dígitos reales, no solo espacios o texto
        if codigo_postal and codigo_postal.strip().isdigit():
            data['codigo_postal'] = codigo_postal.strip()
    # También buscar si está en la misma línea, pero solo si parece un código postal real
    # (en Colombia suelen ser 5-6 dígitos, evitamos capturar "44" que es el número del campo Teléfono)
    elif match := re.search(r"43\.\s*Código postal\s+(\d{4,})", texto_completo):
        data['codigo_postal'] = match.group(1).strip()
    
    # Teléfono 1 (campo 44) - método de BCE con limpieza
    if match := re.search(r"44\.\s*Teléfono\s*1\s*((?:\d\s*)+)", texto_completo):
        telefono = match.group(1).replace(" ", "").strip()
        # Limpiar: eliminar primer 1 si existe y limitar a 10 dígitos
        telefono = telefono.lstrip('1')[:10]
        data['telefono_1'] = telefono
    
    # Teléfono 2 (campo 45)
    if match := re.search(r"45\.\s*Teléfono\s*2\s*((?:\d\s*)+)", texto_completo):
        telefono2 = match.group(1).replace(" ", "").strip()
        telefono2 = telefono2.lstrip('1')[:10]
        data['telefono_2'] = telefono2
    
    # ========== ACTIVIDADES ECONÓMICAS ==========
    # Método de BCE: capturar bloque numérico completo
    bloque_numerico = re.search(
        r"46\.\s*Código.*?51\.\s*Código.*?establecimientos\s*([\d\s]+)",
        texto_completo, 
        re.DOTALL
    )
    
    if bloque_numerico:
        secuencia = bloque_numerico.group(1).replace(" ", "").strip()
        ptr = 0
        
        # Actividad Principal (4 dígitos código + 8 dígitos fecha)
        if len(secuencia) >= 12:
            codigo = secuencia[ptr:ptr+4]
            fecha_str = secuencia[ptr+4:ptr+12]
            data['actividad_principal_ciiu'] = codigo
            fecha_parsed = parse_date(fecha_str)
            if fecha_parsed:
                data['actividad_principal_fecha_inicio'] = fecha_parsed.date()
            ptr += 12
        
        # Actividad Secundaria (4 dígitos código + 8 dígitos fecha)
        if len(secuencia) >= ptr + 12:
            codigo = secuencia[ptr:ptr+4]
            fecha_str = secuencia[ptr+4:ptr+12]
            data['actividad_secundaria_ciiu'] = codigo
            fecha_parsed = parse_date(fecha_str)
            if fecha_parsed:
                data['actividad_secundaria_fecha_inicio'] = fecha_parsed.date()
            ptr += 12
        
        # Otras Actividades (hasta 2 códigos de 4 dígitos)
        otras_actividades = []
        for i in range(2):  # Máximo 2 códigos adicionales
            if len(secuencia) >= ptr + 4:
                codigo = secuencia[ptr:ptr+4]
                otras_actividades.append(codigo)
                ptr += 4
        
        if otras_actividades:
            # Guardar el primero en otras_actividades_ciiu (campo único en MANU)
            data['otras_actividades_ciiu'] = otras_actividades[0] if otras_actividades else None
        
        # Número de Establecimientos (último dígito)
        if len(secuencia) > ptr:
            digitos_restantes = secuencia[ptr:]
            if len(digitos_restantes) > 1:
                data['numero_establecimientos'] = int(digitos_restantes[-1])
            else:
                data['numero_establecimientos'] = int(digitos_restantes) if digitos_restantes.isdigit() else 0
    
    # ========== RESPONSABILIDADES ==========
    # Inicializar listas vacías (siempre devolver algo)
    codigos_list = []
    descripciones_list = []
    
    # Método mejorado: extraer códigos de las descripciones (más confiable que la línea "53. Código")
    # Las descripciones tienen formato: "05- Impto...", "07- Retención...", "48 - IVA", etc.
    # Buscar directamente códigos con formato "XX- Descripción" en todo el texto
    # Esto es más robusto que buscar la sección primero
    # Formato: "05- Impto...", "07- Retención...", "48 - IVA", "52 - Facturador..."
    # Buscar solo si hay "Responsabilidades" en el texto para evitar falsos positivos
    if 'Responsabilidades' in texto_completo or 'responsabilidades' in texto_completo.lower():
        # Buscar todos los códigos con formato "XX- Descripción" o "XX - Descripción"
        # Patrón mejorado: captura hasta encontrar otro código o fin de línea
        # Formato: "05- Impto... 42- Obligado..." -> captura "05- Impto..." y "42- Obligado..." por separado
        patron = re.compile(
            r'(\d{1,2})\s*-\s*([A-Za-zÁÉÍÓÚáéíóúÑñ][^\n]*?)(?=\s+\d{1,2}\s*-|\n|$)',
            re.IGNORECASE | re.MULTILINE
        )
        matches = patron.findall(texto_completo)
        
        for codigo, descripcion in matches:
            codigo_str = codigo.strip()
            # Normalizar: "05" -> "5", "07" -> "7", "09" -> "9", pero mantener "10", "14", etc.
            if codigo_str.startswith('0') and len(codigo_str) == 2:
                codigo_str = codigo_str[1]  # Quitar el cero inicial
            
            descripcion_limpia = descripcion.strip()
            # Limpiar descripción: quitar espacios múltiples
            descripcion_limpia = re.sub(r'\s+', ' ', descripcion_limpia)
            
            # Validar que la descripción tenga sentido (al menos 3 caracteres y contenga letras)
            if len(descripcion_limpia) >= 3 and re.search(r'[A-Za-zÁÉÍÓÚáéíóúÑñ]', descripcion_limpia):
                # Validar que el código esté en rango válido (1-99)
                try:
                    codigo_int = int(codigo_str)
                    if 1 <= codigo_int <= 99:
                        if codigo_str not in codigos_list:
                            codigos_list.append(codigo_str)
                            descripciones_list.append(descripcion_limpia)
                except ValueError:
                    pass
    
    # Obtener descripciones desde la tabla ResponsabilidadTributaria si no las tenemos o están incompletas
    # Esto asegura que siempre tengamos descripciones correctas desde la BD
    if codigos_list:
        from ..models import ResponsabilidadTributaria
        # Si no tenemos descripciones o tenemos menos descripciones que códigos, completar desde BD
        if len(descripciones_list) < len(codigos_list):
            descripciones_list = []  # Reiniciar para alinear con códigos
            for codigo in codigos_list:
                try:
                    resp = ResponsabilidadTributaria.objects.get(codigo=str(codigo))
                    descripciones_list.append(resp.descripcion)
                except ResponsabilidadTributaria.DoesNotExist:
                    # Si no existe en BD, usar descripción genérica
                    descripciones_list.append(f'Responsabilidad tributaria código {codigo}')
    
    # Obtener descripciones desde la tabla ResponsabilidadTributaria si no las tenemos o están incompletas
    # Esto asegura que siempre tengamos descripciones correctas desde la BD (como en BCE)
    if codigos_list:
        from ..models import ResponsabilidadTributaria
        # Si no tenemos descripciones o tenemos menos descripciones que códigos, completar desde BD
        if len(descripciones_list) < len(codigos_list):
            # Reiniciar descripciones para alinear con códigos
            descripciones_list = []
            for codigo in codigos_list:
                try:
                    resp = ResponsabilidadTributaria.objects.get(codigo=str(codigo))
                    descripciones_list.append(resp.descripcion)
                except ResponsabilidadTributaria.DoesNotExist:
                    # Si no existe en BD, usar descripción genérica
                    descripciones_list.append(f'Responsabilidad tributaria código {codigo}')
    
    # SIEMPRE asignar las listas (aunque estén vacías)
    data['responsabilidades_codigos'] = codigos_list
    data['responsabilidades_descripcion'] = descripciones_list
    
    # Mapear códigos comunes a booleanos (convertir a int solo para comparación)
    codigos_set = {int(c) for c in codigos_list if c.isdigit()}
    data['responsable_iva'] = 48 in codigos_set
    data['autorretenedor'] = 7 in codigos_set or 9 in codigos_set
    data['obligado_contabilidad'] = 42 in codigos_set
    data['regimen_simple'] = 47 in codigos_set
    data['facturador_electronico'] = 52 in codigos_set
    data['informante_exogena'] = 14 in codigos_set
    data['informante_beneficiarios_finales'] = 55 in codigos_set
    
    # ========== REPRESENTANTE LEGAL ==========
    # Buscar "984. Nombre" seguido del nombre completo (múltiples patrones)
    # Patrón 1: Formato estándar "984. Nombre APELLIDO1 APELLIDO2 NOMBRE1 NOMBRE2"
    if match := re.search(r"984\.\s*Nombre\s+([A-ZÁÉÍÓÚÑ\s]+?)(?=\s+985\.|\s+\d+\.|$)", texto_completo, re.IGNORECASE):
        nombre_completo = match.group(1).strip()
        # Dividir en partes (generalmente: apellido1 apellido2 nombre1 nombre2)
        partes = nombre_completo.split()
        if len(partes) >= 2:
            # Asumir que los primeros son apellidos y los últimos nombres
            if len(partes) == 2:
                data['representante_legal_primer_apellido'] = partes[0]
                data['representante_legal_primer_nombre'] = partes[1]
            elif len(partes) == 3:
                data['representante_legal_primer_apellido'] = partes[0]
                data['representante_legal_segundo_apellido'] = partes[1]
                data['representante_legal_primer_nombre'] = partes[2]
            elif len(partes) >= 4:
                data['representante_legal_primer_apellido'] = partes[0]
                data['representante_legal_segundo_apellido'] = partes[1]
                data['representante_legal_primer_nombre'] = partes[2]
                data['representante_legal_otros_nombres'] = ' '.join(partes[3:])
    
    # Patrón 2: Buscar en formato más flexible
    if not data.get('representante_legal_primer_nombre'):
        if match := re.search(r"984\.\s*Nombre[^\n]*\n\s*([A-ZÁÉÍÓÚÑ\s]+?)(?=\n\s*985\.|\n\s*\d+\.|$)", texto_completo, re.IGNORECASE | re.MULTILINE):
            nombre_completo = match.group(1).strip()
            partes = nombre_completo.split()
            if len(partes) >= 2:
                if len(partes) == 2:
                    data['representante_legal_primer_apellido'] = partes[0]
                    data['representante_legal_primer_nombre'] = partes[1]
                elif len(partes) >= 3:
                    data['representante_legal_primer_apellido'] = partes[0]
                    data['representante_legal_segundo_apellido'] = partes[1] if len(partes) > 2 else ''
                    data['representante_legal_primer_nombre'] = partes[2] if len(partes) > 2 else partes[1]
                    if len(partes) > 3:
                        data['representante_legal_otros_nombres'] = ' '.join(partes[3:])
    
    # Cargo del representante legal
    # Cortar antes de "Fecha generación documento PDF" o de cualquier nuevo bloque numerado
    if match := re.search(r"985\.\s*Cargo\s*(.+?)(?=\n\d+\.|\nFecha generación documento PDF|$)", texto_completo, re.DOTALL):
        cargo = match.group(1).strip()
        cargo = " ".join(cargo.split())
        # Truncar a 255 caracteres si es necesario
        if len(cargo) > 255:
            cargo = cargo[:255]
        data['representante_legal_representacion'] = cargo
    
    # ========== INFORMACIÓN LEGAL ==========
    # Fecha de constitución
    if match := re.search(r"73\.\s*Fecha\s*(\d{4}[,\-]\d{2}[,\-]\d{2})", texto_completo):
        fecha_str = match.group(1).replace(",", "").replace("-", "")
        fecha_parsed = parse_date(fecha_str)
        if fecha_parsed:
            data['constitucion_fecha'] = fecha_parsed.date()
    
    # Matrícula mercantil
    if match := re.search(r"77\.\s*No\.\s*Matrícula mercantil\s*(\d+)", texto_completo):
        data['matricula_mercantil'] = match.group(1).strip()
    
    # Entidad de vigilancia
    if match := re.search(r"88\.\s*Entidad de vigilancia y control\s*(.+)", texto_completo):
        data['entidad_vigilancia'] = match.group(1).strip()
    
    # ========== PREPARAR CÓDIGOS CIIU ==========
    codigos_ciiu_encontrados = []
    if data.get('actividad_principal_ciiu'):
        codigos_ciiu_encontrados.append(data['actividad_principal_ciiu'])
    if data.get('actividad_secundaria_ciiu'):
        codigos_ciiu_encontrados.append(data['actividad_secundaria_ciiu'])
    if data.get('otras_actividades_ciiu'):
        codigos_ciiu_encontrados.append(data['otras_actividades_ciiu'])
    
    data['_codigos_ciiu_encontrados'] = list(set(codigos_ciiu_encontrados))
    
    # ========== USUARIOS ADUANEROS Y EXPORTADORES ==========
    # Usuarios aduaneros (códigos de 2 dígitos entre 55 y 56)
    data['usuarios_aduaneros'] = []
    if match := re.search(
        r"55\.\s*Forma\s*56\.\s*Tipo\s*1\s*2\s*3\s*([\d\s]+)(?=\n\d+\.|\Z)", 
        texto_completo, 
        re.DOTALL
    ):
        codigos = re.sub(r"\D", "", match.group(1))  # Eliminar todo excepto dígitos
        data['usuarios_aduaneros'] = [codigos[i:i+2] for i in range(0, len(codigos), 2) if len(codigos[i:i+2]) == 2]
    
    # Exportadores - Forma y Tipo
    data['exportadores_forma'] = None
    data['exportadores_tipo'] = None
    if match := re.search(
        r"54\.\s*Código\s*57\.\s*EMxopdoortadores.*?(\d+)\s*(\d+)(?=\n\d+\.|\Z)", 
        texto_completo, 
        re.DOTALL
    ):
        data['exportadores_forma'] = match.group(1)[-1] if match.group(1) else None  # Último dígito
        data['exportadores_tipo'] = match.group(2)[0] if match.group(2) else None  # Primer dígito
    
    # ========== ESTABLECIMIENTOS ==========
    data['_establecimientos'] = []
    # Patrón mejorado para capturar establecimientos válidos
    patron_establecimiento = re.compile(
        r"162\.\s*Nombre del establecimiento\s*\n(.+?)"
        r"\s*163\.\s*Departamento\s*(.+?)"
        r"\s*164\.\s*Ciudad/Municipio\s*(.+?)"
        r"\s*165\.\s*Dirección\s*\n(.+?)"
        r"(?:\s*166\.|\s*\d+\.|$)",
        re.DOTALL
    )
    
    for match in patron_establecimiento.finditer(texto_completo):
        # Limpiar nombre (eliminar ":" y saltos de línea)
        nombre = re.sub(r"^:\s*|\n", "", match.group(1).strip())
        
        # Procesar departamento y ciudad
        departamento_raw = match.group(2).replace("\n", " ")
        ciudad_raw = match.group(3).replace("\n", " ")
        
        # Extraer códigos y nombres (método simplificado)
        dept_match = re.search(r"(\d+)\s*(.+)", departamento_raw)
        ciudad_match = re.search(r"(\d+)\s*(.+)", ciudad_raw)
        
        departamento_codigo = dept_match.group(1) if dept_match else None
        departamento_nombre = dept_match.group(2).strip() if dept_match else departamento_raw.strip()
        ciudad_codigo = ciudad_match.group(1) if ciudad_match else None
        ciudad_nombre = ciudad_match.group(2).strip() if ciudad_match else ciudad_raw.strip()
        
        # Dirección
        direccion = match.group(4).strip()
        
        # Buscar actividad económica del establecimiento (después de la dirección)
        actividad_ciiu = None
        actividad_desc = None
        texto_despues = texto_completo[match.end():match.end()+500]  # Buscar en los siguientes 500 caracteres
        if act_match := re.search(r"166\.\s*Código.*?(\d{4})\s*(.+?)(?=\n\d+\.|$)", texto_despues, re.DOTALL):
            actividad_ciiu = act_match.group(1)
            actividad_desc = act_match.group(2).strip()
        
        # Buscar matrícula mercantil del establecimiento
        matricula = None
        if mat_match := re.search(r"167\.\s*Matrícula mercantil\s*(\d+)", texto_despues):
            matricula = mat_match.group(1)
        
        # Buscar teléfono del establecimiento
        telefono = None
        if tel_match := re.search(r"168\.\s*Teléfono\s*((?:\d\s*)+)", texto_despues):
            telefono = tel_match.group(1).replace(" ", "").strip()
            telefono = telefono.lstrip('1')[:10]
        
        if nombre and not nombre.isnumeric():  # Filtrar encabezados residuales
            data['_establecimientos'].append({
                'nombre': nombre,
                'tipo_establecimiento': None,  # No siempre está en el PDF
                'tipo_establecimiento_codigo': None,
                'actividad_economica_ciiu': actividad_ciiu,
                'actividad_economica_descripcion': actividad_desc,
                'departamento_codigo': departamento_codigo,
                'departamento_nombre': departamento_nombre,
                'ciudad_codigo': ciudad_codigo,
                'ciudad_nombre': ciudad_nombre,
                'direccion': direccion,
                'matricula_mercantil': matricula,
                'telefono': telefono,
            })
    
    return data
