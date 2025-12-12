"""
Script para verificar si las cuentas están como rangos en el PDF.
"""
import pdfplumber
import re

def buscar_cuentas_y_rangos(pdf_path='PUC.pdf', pagina_inicio=4, pagina_fin=113):
    """Busca cuentas específicas y verifica si están como rangos."""
    
    # Cuentas a verificar
    cuentas_4_digitos = {
        '5420': 'Arrendamientos',
        '5425': 'Seguros',
        '5475': 'Vigilancia/seguridad',
        '5480': 'Aseo/limpieza',
        '5505': 'Publicidad'
    }
    
    cuentas_6_digitos = {
        '141001': 'Productos en proceso',
        '143501': 'Mercancías',
        '220501': 'Proveedores',
        '240801': 'IVA',
        '240802': 'Impoconsumo',
        '240805': 'Retención fuente'
    }
    
    resultados_4 = {}
    resultados_6 = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        texto_completo = ""
        for i in range(pagina_inicio, min(pagina_fin + 1, len(pdf.pages))):
            page = pdf.pages[i]
            texto = page.extract_text()
            if texto:
                texto_completo += texto + "\n"
        
        # Buscar en tablas
        for i in range(pagina_inicio, min(pagina_fin + 1, len(pdf.pages))):
            page = pdf.pages[i]
            tables = page.extract_tables()
            
            for table in tables:
                if not table:
                    continue
                for row in table:
                    if not row or len(row) < 2:
                        continue
                    codigo = str(row[0]).strip() if row[0] else ""
                    denominacion = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                    
                    # Verificar cuentas de 4 dígitos
                    for cuenta, desc in cuentas_4_digitos.items():
                        if cuenta in codigo:
                            if cuenta not in resultados_4:
                                resultados_4[cuenta] = {
                                    'encontrada': True,
                                    'formato': codigo,
                                    'denominacion': denominacion,
                                    'pagina': i + 1
                                }
                    
                    # Verificar cuentas de 6 dígitos
                    for cuenta, desc in cuentas_6_digitos.items():
                        if cuenta in codigo:
                            if cuenta not in resultados_6:
                                resultados_6[cuenta] = {
                                    'encontrada': True,
                                    'formato': codigo,
                                    'denominacion': denominacion,
                                    'pagina': i + 1
                                }
        
        # Buscar patrones de rango (ej: "141001 a 141098")
        patron_rango = re.compile(r'(\d{6})\s+a\s+(\d{6})', re.IGNORECASE)
        rangos_encontrados = patron_rango.findall(texto_completo)
        
        # Buscar también en formato "141001-141098" o "141001 a 141098"
        patron_rango_guion = re.compile(r'(\d{6})[\s-]+(\d{6})', re.IGNORECASE)
        rangos_guion = patron_rango_guion.findall(texto_completo)
        
        # Buscar cuentas base seguidas de "a" (indicando rango)
        patron_cuenta_rango = re.compile(r'(\d{4,6})\s+a\s+[^\n]{0,50}', re.IGNORECASE)
        cuentas_con_rango = patron_cuenta_rango.findall(texto_completo)
        
        return resultados_4, resultados_6, rangos_encontrados, rangos_guion, cuentas_con_rango

if __name__ == '__main__':
    print("🔍 Verificando cuentas específicas y rangos en el PDF...")
    resultados_4, resultados_6, rangos, rangos_guion, cuentas_rango = buscar_cuentas_y_rangos()
    
    print("\n" + "="*80)
    print("📊 CUENTAS DE 4 DÍGITOS (5420, 5425, 5475, 5480, 5505):")
    print("="*80)
    for cuenta in ['5420', '5425', '5475', '5480', '5505']:
        if cuenta in resultados_4:
            print(f"   ✅ {cuenta}: ENCONTRADA")
            print(f"      Formato: {resultados_4[cuenta]['formato']}")
            print(f"      Denominación: {resultados_4[cuenta]['denominacion'][:80]}")
            print(f"      Página: {resultados_4[cuenta]['pagina']}")
        else:
            print(f"   ❌ {cuenta}: NO ENCONTRADA")
    
    print("\n" + "="*80)
    print("📊 CUENTAS DE 6 DÍGITOS (141001, 143501, 220501, 240801, 240802, 240805):")
    print("="*80)
    for cuenta in ['141001', '143501', '220501', '240801', '240802', '240805']:
        if cuenta in resultados_6:
            print(f"   ✅ {cuenta}: ENCONTRADA")
            print(f"      Formato: {resultados_6[cuenta]['formato']}")
            print(f"      Denominación: {resultados_6[cuenta]['denominacion'][:80]}")
            print(f"      Página: {resultados_6[cuenta]['pagina']}")
        else:
            print(f"   ❌ {cuenta}: NO ENCONTRADA")
    
    print("\n" + "="*80)
    print("📊 RANGOS ENCONTRADOS EN EL PDF:")
    print("="*80)
    if rangos:
        print(f"   Encontrados {len(rangos)} rangos (formato 'XXXXXX a XXXXXX'):")
        for inicio, fin in rangos[:10]:
            print(f"      {inicio} a {fin}")
    else:
        print("   No se encontraron rangos en formato 'XXXXXX a XXXXXX'")
    
    if rangos_guion:
        print(f"\n   Encontrados {len(rangos_guion)} rangos (formato 'XXXXXX-XXXXXX'):")
        for inicio, fin in rangos_guion[:10]:
            print(f"      {inicio}-{fin}")
    
    print("\n" + "="*80)
    print("📊 CUENTAS CON INDICADOR DE RANGO ('a'):")
    print("="*80)
    if cuentas_rango:
        print(f"   Encontradas {len(cuentas_rango)} cuentas con indicador de rango:")
        cuentas_unicas = sorted(set(cuentas_rango))[:20]
        for cuenta in cuentas_unicas:
            print(f"      {cuenta}")
    
    # Buscar específicamente las cuentas base que mencionamos
    print("\n" + "="*80)
    print("📊 VERIFICACIÓN DE CUENTAS BASE (1410, 1435, 2205, 2408):")
    print("="*80)
    import pdfplumber
    pdf = pdfplumber.open('PUC.pdf')
    texto = ""
    for i in range(4, 114):
        texto += pdf.pages[i].extract_text() + "\n"
    
    for cuenta_base in ['1410', '1435', '2205', '2408']:
        # Buscar la cuenta base seguida de "a" o rango
        patron = re.compile(rf'\b{cuenta_base}\b[^\n]*', re.IGNORECASE)
        matches = patron.findall(texto)
        if matches:
            print(f"\n   ✅ {cuenta_base}: Encontrada")
            print(f"      Muestra: {matches[0][:100]}")
            # Buscar si tiene subcuentas con "a"
            patron_sub = re.compile(rf'\b{cuenta_base}\d{{2}}\s+a\b', re.IGNORECASE)
            sub_rangos = patron_sub.findall(texto)
            if sub_rangos:
                print(f"      Tiene subcuentas con rango: {len(sub_rangos)} encontradas")
                print(f"      Ejemplo: {sub_rangos[0]}")
        else:
            print(f"\n   ❌ {cuenta_base}: NO ENCONTRADA")

