"""
Script temporal para extraer el PUC del PDF y comparar con las cuentas del prompt.
"""
import pdfplumber
import re
from collections import defaultdict

def extraer_cuentas_puc(pdf_path='PUC.pdf', pagina_inicio=4, pagina_fin=113):
    """
    Extrae todas las cuentas del PUC del PDF (páginas 5-114, índices 4-113).
    Retorna diccionario con cuentas por nivel (1, 2, 4, 6 dígitos).
    """
    cuentas = {
        '1_digito': set(),  # Clases: 1, 2, 3, 4, 5, 6, 7, 8, 9
        '2_digitos': set(),  # Grupos: 10, 11, 12, etc.
        '4_digitos': set(),  # Cuentas principales: 1105, 1410, 1435, etc.
        '6_digitos': set()   # Subcuentas: 110505, 141001, 143501, etc.
    }
    
    descripciones = {}  # {cuenta: descripcion}
    
    with pdfplumber.open(pdf_path) as pdf:
        total_paginas = len(pdf.pages)
        print(f"📄 Total páginas en PDF: {total_paginas}")
        print(f"📄 Extrayendo de páginas {pagina_inicio+1} a {min(pagina_fin+1, total_paginas)}")
        
        # Extraer de TABLAS (más preciso que texto plano)
        for i in range(pagina_inicio, min(pagina_fin + 1, total_paginas)):
            page = pdf.pages[i]
            tables = page.extract_tables()
            
            for table in tables:
                if not table or len(table) < 2:
                    continue
                
                # La primera fila suele ser el encabezado: ['CODIGO', 'DENOMINACION']
                for row in table[1:]:  # Saltar encabezado
                    if not row or len(row) < 2:
                        continue
                    
                    codigo_str = str(row[0]).strip() if row[0] else ""
                    denominacion = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                    
                    if not codigo_str or not codigo_str.isdigit():
                        continue
                    
                    # Determinar nivel de la cuenta
                    if len(codigo_str) == 1 and codigo_str[0] in '123456789':
                        cuentas['1_digito'].add(codigo_str)
                        descripciones[codigo_str] = denominacion
                    elif len(codigo_str) == 2:
                        # Verificar que no sea parte de una cuenta más larga
                        if not any(codigo_str == c[:2] for c in cuentas['4_digitos'] | cuentas['6_digitos']):
                            cuentas['2_digitos'].add(codigo_str)
                            descripciones[codigo_str] = denominacion
                    elif len(codigo_str) == 4:
                        # Verificar que no sea parte de una cuenta de 6 dígitos
                        if not any(codigo_str == c[:4] for c in cuentas['6_digitos']):
                            cuentas['4_digitos'].add(codigo_str)
                            descripciones[codigo_str] = denominacion
                    elif len(codigo_str) == 6:
                        cuentas['6_digitos'].add(codigo_str)
                        descripciones[codigo_str] = denominacion
        
        return cuentas, descripciones

def cuentas_del_prompt():
    """
    Retorna las cuentas mencionadas en el prompt actual.
    """
    cuentas_prompt = {
        '4_digitos': {
            '1410', '1435', '1455', '5105', '5150', '5205', '5305', '5420', '5425', 
            '5475', '5480', '5505', '6135', '1105', '1110', '1520', '1524', '1528', 
            '1540', '1610', '2205', '2408'
        },
        '6_digitos': {
            # 1410
            '141001', '141098',
            # 1435
            '143501', '143598',
            # 1455
            '145501', '145598',
            # 5105
            '510503', '510506', '510512', '510515', '510518', '510521', '510530', 
            '510536', '510539', '510568', '510569', '510570', '510575', '510578', '510595',
            # 5150
            '515005', '515015',
            # 5305
            '530505', '530510', '530515', '530520', '530525',
            # 1105
            '110505', '110510', '110515',
            # 1110
            '111005',
            # 1520
            '152001', '152098',
            # 1524
            '152405', '152410', '152495',
            # 1528
            '152805', '152810',
            # 1540
            '154005', '154010', '154015', '154030',
            # 1610
            '161005', '161010',
            # 2205
            '220501', '220598',
            # 2408
            '240801', '240802', '240805'
        }
    }
    return cuentas_prompt

def comparar_cuentas(cuentas_pdf, cuentas_prompt):
    """
    Compara las cuentas del PDF con las del prompt y reporta inconsistencias.
    """
    print("\n" + "="*80)
    print("🔍 COMPARACIÓN DE CUENTAS PUC")
    print("="*80)
    
    # Comparar cuentas de 4 dígitos
    print("\n📊 CUENTAS DE 4 DÍGITOS:")
    print(f"   En PDF: {len(cuentas_pdf['4_digitos'])} cuentas")
    print(f"   En Prompt: {len(cuentas_prompt['4_digitos'])} cuentas")
    
    cuentas_prompt_4 = cuentas_prompt['4_digitos']
    cuentas_pdf_4 = cuentas_pdf['4_digitos']
    
    # Cuentas en prompt pero NO en PDF
    faltantes_4 = cuentas_prompt_4 - cuentas_pdf_4
    if faltantes_4:
        print(f"\n   ⚠️  INCONSISTENCIAS - Cuentas en prompt pero NO en PDF ({len(faltantes_4)}):")
        for cuenta in sorted(faltantes_4):
            print(f"      ❌ {cuenta}")
    else:
        print(f"\n   ✅ Todas las cuentas de 4 dígitos del prompt están en el PDF")
    
    # Comparar cuentas de 6 dígitos
    print("\n📊 CUENTAS DE 6 DÍGITOS:")
    print(f"   En PDF: {len(cuentas_pdf['6_digitos'])} cuentas")
    print(f"   En Prompt (específicas): {len(cuentas_prompt['6_digitos'])} cuentas")
    
    cuentas_prompt_6 = cuentas_prompt['6_digitos']
    cuentas_pdf_6 = cuentas_pdf['6_digitos']
    
    # Cuentas en prompt pero NO en PDF
    faltantes_6 = cuentas_prompt_6 - cuentas_pdf_6
    if faltantes_6:
        print(f"\n   ⚠️  INCONSISTENCIAS - Cuentas en prompt pero NO en PDF ({len(faltantes_6)}):")
        for cuenta in sorted(faltantes_6):
            print(f"      ❌ {cuenta}")
    else:
        print(f"\n   ✅ Todas las cuentas de 6 dígitos del prompt están en el PDF")
    
    # Verificar rangos mencionados en prompt
    print("\n📊 VERIFICACIÓN DE RANGOS MENCIONADOS EN PROMPT:")
    rangos_prompt = [
        ('1410', '141001', '141098'),
        ('1435', '143501', '143598'),
        ('1455', '145501', '145598'),
        ('1520', '152001', '152098'),
        ('2205', '220501', '220598')
    ]
    
    for cuenta_base, inicio, fin in rangos_prompt:
        # Verificar que la cuenta base existe
        if cuenta_base not in cuentas_pdf_4:
            print(f"   ⚠️  Cuenta base {cuenta_base} NO existe en PDF")
            continue
        
        # Contar cuentas en el rango que existen en PDF
        inicio_num = int(inicio)
        fin_num = int(fin)
        cuentas_en_rango = [c for c in cuentas_pdf_6 if inicio_num <= int(c) <= fin_num]
        
        print(f"   📋 {cuenta_base} (rango {inicio}-{fin}): {len(cuentas_en_rango)} cuentas encontradas en PDF")
        if len(cuentas_en_rango) == 0:
            print(f"      ⚠️  ADVERTENCIA: No se encontraron cuentas en este rango")
    
    return {
        'faltantes_4': faltantes_4,
        'faltantes_6': faltantes_6,
        'total_pdf_4': len(cuentas_pdf_4),
        'total_pdf_6': len(cuentas_pdf_6)
    }

if __name__ == '__main__':
    print("🔍 Extrayendo PUC del PDF...")
    cuentas_pdf, descripciones = extraer_cuentas_puc()
    
    print(f"\n✅ Extracción completada:")
    print(f"   - 1 dígito: {len(cuentas_pdf['1_digito'])} cuentas")
    print(f"   - 2 dígitos: {len(cuentas_pdf['2_digitos'])} cuentas")
    print(f"   - 4 dígitos: {len(cuentas_pdf['4_digitos'])} cuentas")
    print(f"   - 6 dígitos: {len(cuentas_pdf['6_digitos'])} cuentas")
    
    cuentas_prompt = cuentas_del_prompt()
    resultado = comparar_cuentas(cuentas_pdf, cuentas_prompt)
    
    print("\n" + "="*80)
    print("📋 RESUMEN:")
    print("="*80)
    print(f"   Total cuentas en PDF: {resultado['total_pdf_4']} (4 dígitos) + {resultado['total_pdf_6']} (6 dígitos)")
    print(f"   Cuentas faltantes (4 dígitos): {len(resultado['faltantes_4'])}")
    print(f"   Cuentas faltantes (6 dígitos): {len(resultado['faltantes_6'])}")
    
    if len(resultado['faltantes_4']) == 0 and len(resultado['faltantes_6']) == 0:
        print("\n   ✅ NO HAY INCONSISTENCIAS - Todas las cuentas del prompt están en el PDF")
    else:
        print("\n   ⚠️  HAY INCONSISTENCIAS - Revisar antes de proceder")

