"""
Script para verificar cuentas específicas del prompt en el PDF.
"""
import pdfplumber
import re

def buscar_cuentas_en_pdf(pdf_path='PUC.pdf', pagina_inicio=4, pagina_fin=113):
    """Busca cuentas específicas mencionadas en el prompt."""
    
    cuentas_a_buscar_4 = ['1410', '1435', '1455', '2205', '2408', '5420', '5425', '5475', '5480', '5505']
    cuentas_a_buscar_6 = ['141001', '143501', '220501', '240801', '240802', '240805']
    
    encontradas_4 = {}
    encontradas_6 = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        texto_completo = ""
        for i in range(pagina_inicio, min(pagina_fin + 1, len(pdf.pages))):
            page = pdf.pages[i]
            texto = page.extract_text()
            if texto:
                texto_completo += texto + "\n"
        
        # Buscar en texto
        for cuenta in cuentas_a_buscar_4:
            patron = re.compile(rf'\b{cuenta}\b[^\n]*', re.IGNORECASE)
            matches = patron.findall(texto_completo)
            if matches:
                encontradas_4[cuenta] = matches[:3]
        
        for cuenta in cuentas_a_buscar_6:
            patron = re.compile(rf'\b{cuenta}\b[^\n]*')
            matches = patron.findall(texto_completo)
            if matches:
                encontradas_6[cuenta] = matches[:3]
        
        # También buscar en tablas
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
                    
                    if codigo in cuentas_a_buscar_4:
                        if codigo not in encontradas_4:
                            encontradas_4[codigo] = [f"Tabla página {i+1}: {row[1] if len(row) > 1 else ''}"]
                    
                    if codigo in cuentas_a_buscar_6:
                        if codigo not in encontradas_6:
                            encontradas_6[codigo] = [f"Tabla página {i+1}: {row[1] if len(row) > 1 else ''}"]
    
    return encontradas_4, encontradas_6

if __name__ == '__main__':
    print("🔍 Buscando cuentas específicas del prompt en el PDF...")
    encontradas_4, encontradas_6 = buscar_cuentas_en_pdf()
    
    print("\n📊 CUENTAS DE 4 DÍGITOS:")
    for cuenta in ['1410', '1435', '1455', '2205', '2408', '5420', '5425', '5475', '5480', '5505']:
        if cuenta in encontradas_4:
            print(f"   ✅ {cuenta}: {encontradas_4[cuenta][0][:80]}")
        else:
            print(f"   ❌ {cuenta}: NO ENCONTRADA")
    
    print("\n📊 CUENTAS DE 6 DÍGITOS:")
    for cuenta in ['141001', '143501', '220501', '240801', '240802', '240805']:
        if cuenta in encontradas_6:
            print(f"   ✅ {cuenta}: {encontradas_6[cuenta][0][:80]}")
        else:
            print(f"   ❌ {cuenta}: NO ENCONTRADA")

