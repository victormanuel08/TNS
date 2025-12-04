"""
Script de diagnóstico detallado para un PDF de RUT específico.
Muestra TODO lo que se puede extraer y por qué falla cada patrón.
"""
import os
import sys
import io
import re
from django.core.management.base import BaseCommand
from django.db import connection

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


class Command(BaseCommand):
    help = 'Diagnóstico DETALLADO de un PDF de RUT - muestra TODO lo que se puede extraer'

    def add_arguments(self, parser):
        parser.add_argument('pdf_path', type=str, help='Ruta al archivo PDF del RUT')
        parser.add_argument('--save-text', type=str, help='Guardar texto extraído en un archivo', default=None)

    def handle(self, *args, **options):
        pdf_path = options['pdf_path']
        save_text_path = options.get('save_text')

        if not os.path.exists(pdf_path):
            self.stderr.write(self.style.ERROR(f"❌ El archivo no existe: {pdf_path}"))
            return

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("DIAGNÓSTICO DETALLADO DE PDF RUT"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(f"\n📄 Archivo: {pdf_path}\n")

        # 1. EXTRAER TEXTO COMPLETO
        self.stdout.write(self.style.HTTP_INFO("\n" + "=" * 80))
        self.stdout.write(self.style.HTTP_INFO("1. EXTRACCIÓN DE TEXTO COMPLETO"))
        self.stdout.write(self.style.HTTP_INFO("=" * 80))

        texto_completo = ""
        try:
            if PDFPLUMBER_AVAILABLE:
                with pdfplumber.open(pdf_path) as pdf:
                    self.stdout.write(f"   📊 Total de páginas: {len(pdf.pages)}")
                    for i, page in enumerate(pdf.pages, 1):
                        page_text = page.extract_text() or ""
                        texto_completo += page_text
                        self.stdout.write(f"   📄 Página {i}: {len(page_text)} caracteres")
            elif PYPDF2_AVAILABLE:
                import PyPDF2
                with open(pdf_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    self.stdout.write(f"   📊 Total de páginas: {len(pdf_reader.pages)}")
                    for i, page in enumerate(pdf_reader.pages, 1):
                        page_text = page.extract_text() or ""
                        texto_completo += page_text
                        self.stdout.write(f"   📄 Página {i}: {len(page_text)} caracteres")
            else:
                self.stderr.write(self.style.ERROR("❌ No hay biblioteca de PDF disponible (pdfplumber o PyPDF2)"))
                return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error leyendo PDF: {e}"))
            return

        self.stdout.write(f"\n   ✅ Texto total extraído: {len(texto_completo)} caracteres")

        # Guardar texto si se solicita
        if save_text_path:
            try:
                with open(save_text_path, 'w', encoding='utf-8') as f:
                    f.write(texto_completo)
                self.stdout.write(self.style.SUCCESS(f"   💾 Texto guardado en: {save_text_path}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"   ❌ Error guardando texto: {e}"))

        # 2. BUSCAR PATRONES DE NIT
        self.stdout.write(self.style.HTTP_INFO("\n" + "=" * 80))
        self.stdout.write(self.style.HTTP_INFO("2. ANÁLISIS DE PATRONES DE NIT"))
        self.stdout.write(self.style.HTTP_INFO("=" * 80))

        # Patrón 1: Método original BCE
        self.stdout.write("\n   🔍 PATRÓN 1: Método original BCE")
        self.stdout.write("      Buscando: 5. N(úmero|IT)[...]Tributaria[...](NIT)[...]\\n([\\d\\s]+[^\\n]*)")
        nit_match1 = re.search(
            r"5\.\s*N(?:úmero|IT)[^\n]*Tributaria\s*\(?NIT\)?[^\n]*\n([\d\s]+[^\n]*)",
            texto_completo,
            re.IGNORECASE
        )
        if nit_match1:
            linea_nit = nit_match1.group(1).strip()
            self.stdout.write(self.style.SUCCESS(f"      ✅ ENCONTRADO: '{linea_nit}'"))
            self.stdout.write(f"      📝 Analizando línea...")
            patron = re.compile(r'^([\d\s]+)([^\d]+)(\d+)$')
            partes = patron.match(linea_nit)
            if partes:
                numeros = partes.group(1).replace(" ", "")
                self.stdout.write(f"         Números extraídos: '{numeros}' ({len(numeros)} dígitos)")
                if len(numeros) >= 9:
                    nit = numeros[:-1]
                    dv = numeros[-1]
                    self.stdout.write(self.style.SUCCESS(f"         ✅ NIT: {nit}, DV: {dv}"))
                else:
                    self.stdout.write(self.style.WARNING(f"         ⚠️ Muy corto: {len(numeros)} dígitos (mínimo 9)"))
            else:
                self.stdout.write(self.style.WARNING(f"         ⚠️ No coincide con patrón esperado"))
        else:
            self.stdout.write(self.style.ERROR("      ❌ NO ENCONTRADO"))

        # Patrón 2: NIT y DV separados
        self.stdout.write("\n   🔍 PATRÓN 2: NIT y DV separados")
        self.stdout.write("      Buscando: 5. NIT[...]\\n([\\d\\s]{9,15})\\n\\s*6. DV\\n\\s*(\\d)")
        nit_match2 = re.search(
            r'5\.\s*N(?:úmero|IT)[^\n]*Tributaria[^\n]*\(?NIT\)?[^\n]*\n([\d\s]{9,15})\s*\n\s*6\.\s*DV[^\n]*\n\s*(\d)',
            texto_completo,
            re.IGNORECASE | re.DOTALL
        )
        if nit_match2:
            nit_raw = nit_match2.group(1).replace(' ', '').replace('\n', '').strip()
            dv = nit_match2.group(2).strip()
            self.stdout.write(self.style.SUCCESS(f"      ✅ ENCONTRADO: NIT='{nit_raw}' ({len(nit_raw)} dígitos), DV='{dv}'"))
            if 9 <= len(nit_raw) <= 11:
                self.stdout.write(self.style.SUCCESS(f"         ✅ VÁLIDO"))
            else:
                self.stdout.write(self.style.WARNING(f"         ⚠️ Longitud inválida: {len(nit_raw)}"))
        else:
            self.stdout.write(self.style.ERROR("      ❌ NO ENCONTRADO"))

        # Patrón 3: Cualquier secuencia después de "5. NIT"
        self.stdout.write("\n   🔍 PATRÓN 3: Secuencia de dígitos después de '5. NIT'")
        self.stdout.write("      Buscando: 5. NIT[...]\\n\\s*([\\d\\s]{9,15})")
        nit_match3 = re.search(
            r'5\.\s*N(?:úmero|IT)[^\n]*Tributaria[^\n]*\(?NIT\)?[^\n]*\n\s*([\d\s]{9,15})',
            texto_completo,
            re.IGNORECASE
        )
        if nit_match3:
            nit_raw = nit_match3.group(1).replace(' ', '').replace('\n', '').strip()
            self.stdout.write(self.style.SUCCESS(f"      ✅ ENCONTRADO: '{nit_raw}' ({len(nit_raw)} dígitos)"))
            if 9 <= len(nit_raw) <= 11:
                nit = nit_raw[:-1]
                dv = nit_raw[-1]
                self.stdout.write(self.style.SUCCESS(f"         ✅ NIT: {nit}, DV: {dv}"))
            else:
                self.stdout.write(self.style.WARNING(f"         ⚠️ Longitud inválida: {len(nit_raw)}"))
        else:
            self.stdout.write(self.style.ERROR("      ❌ NO ENCONTRADO"))

        # Patrón 4: Formato "NIT: 123456789-0"
        self.stdout.write("\n   🔍 PATRÓN 4: Formato 'NIT: 123456789-0'")
        self.stdout.write("      Buscando: (NIT|Nit|nit)[\\s:]*([\\d]{8,11})[\\s\\-]*(\\d)?")
        nit_match4 = re.search(
            r'(?:NIT|Nit|nit)[\s:]*([\d]{8,11})[\s\-]*(\d)?',
            texto_completo,
            re.IGNORECASE
        )
        if nit_match4:
            nit_raw = nit_match4.group(1)
            dv = nit_match4.group(2) if nit_match4.group(2) else ''
            self.stdout.write(self.style.SUCCESS(f"      ✅ ENCONTRADO: NIT='{nit_raw}' ({len(nit_raw)} dígitos), DV='{dv}'"))
            if 9 <= len(nit_raw) <= 11:
                if dv:
                    self.stdout.write(self.style.SUCCESS(f"         ✅ VÁLIDO: NIT={nit_raw}, DV={dv}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"         ✅ VÁLIDO (DV al final): NIT={nit_raw[:-1]}, DV={nit_raw[-1]}"))
            else:
                self.stdout.write(self.style.WARNING(f"         ⚠️ Longitud inválida: {len(nit_raw)}"))
        else:
            self.stdout.write(self.style.ERROR("      ❌ NO ENCONTRADO"))

        # 3. MOSTRAR CONTEXTO ALREDEDOR DE "5. NIT"
        self.stdout.write(self.style.HTTP_INFO("\n" + "=" * 80))
        self.stdout.write(self.style.HTTP_INFO("3. CONTEXTO ALREDEDOR DE '5. NIT'"))
        self.stdout.write(self.style.HTTP_INFO("=" * 80))

        # Buscar todas las ocurrencias de "5." cerca de "NIT"
        nit_contexts = re.finditer(
            r'5\.\s*[^\n]{0,100}',
            texto_completo,
            re.IGNORECASE
        )
        contexts = list(nit_contexts)
        if contexts:
            self.stdout.write(f"\n   📍 Encontradas {len(contexts)} líneas que empiezan con '5.'")
            for i, match in enumerate(contexts[:5], 1):  # Mostrar solo las primeras 5
                context = match.group(0)
                self.stdout.write(f"\n   {i}. {context[:200]}")
        else:
            self.stdout.write(self.style.WARNING("   ⚠️ No se encontraron líneas que empiecen con '5.'"))

        # Buscar "NIT" en el texto
        nit_positions = [m.start() for m in re.finditer(r'\bNIT\b', texto_completo, re.IGNORECASE)]
        if nit_positions:
            self.stdout.write(f"\n   📍 Encontradas {len(nit_positions)} ocurrencias de 'NIT'")
            for i, pos in enumerate(nit_positions[:3], 1):  # Mostrar solo las primeras 3
                start = max(0, pos - 100)
                end = min(len(texto_completo), pos + 200)
                context = texto_completo[start:end]
                self.stdout.write(f"\n   {i}. Contexto (posición {pos}):")
                self.stdout.write(f"      ...{context}...")

        # 4. BUSCAR NÚMEROS QUE PARECEN NITs
        self.stdout.write(self.style.HTTP_INFO("\n" + "=" * 80))
        self.stdout.write(self.style.HTTP_INFO("4. NÚMEROS QUE PODRÍAN SER NITs"))
        self.stdout.write(self.style.HTTP_INFO("=" * 80))

        # Buscar secuencias de 9-11 dígitos
        posibles_nits = re.findall(r'\b\d{9,11}\b', texto_completo)
        if posibles_nits:
            self.stdout.write(f"\n   📊 Encontradas {len(posibles_nits)} secuencias de 9-11 dígitos:")
            # Mostrar únicos
            unicos = list(set(posibles_nits))[:10]  # Primeros 10 únicos
            for nit in unicos:
                # Verificar si está cerca de "NIT" o "5."
                pos = texto_completo.find(nit)
                if pos != -1:
                    start = max(0, pos - 50)
                    end = min(len(texto_completo), pos + len(nit) + 50)
                    context = texto_completo[start:end]
                    self.stdout.write(f"\n   • {nit} (contexto: ...{context}...)")
        else:
            self.stdout.write(self.style.WARNING("   ⚠️ No se encontraron secuencias de 9-11 dígitos"))

        # 5. MOSTRAR PRIMERAS Y ÚLTIMAS LÍNEAS DEL TEXTO
        self.stdout.write(self.style.HTTP_INFO("\n" + "=" * 80))
        self.stdout.write(self.style.HTTP_INFO("5. PRIMERAS Y ÚLTIMAS LÍNEAS DEL TEXTO"))
        self.stdout.write(self.style.HTTP_INFO("=" * 80))

        lineas = texto_completo.split('\n')
        self.stdout.write(f"\n   📄 Total de líneas: {len(lineas)}")
        self.stdout.write(f"\n   📝 Primeras 20 líneas:")
        for i, linea in enumerate(lineas[:20], 1):
            if linea.strip():
                self.stdout.write(f"      {i:3d}. {linea[:100]}")

        self.stdout.write(f"\n   📝 Últimas 20 líneas:")
        for i, linea in enumerate(lineas[-20:], len(lineas) - 19):
            if linea.strip():
                self.stdout.write(f"      {i:3d}. {linea[:100]}")

        # 6. RESUMEN Y RECOMENDACIONES
        self.stdout.write(self.style.HTTP_INFO("\n" + "=" * 80))
        self.stdout.write(self.style.HTTP_INFO("6. RESUMEN Y RECOMENDACIONES"))
        self.stdout.write(self.style.HTTP_INFO("=" * 80))

        # Verificar si algún patrón encontró algo
        nits_encontrados = []
        if nit_match1:
            linea_nit = nit_match1.group(1).strip()
            patron = re.compile(r'^([\d\s]+)([^\d]+)(\d+)$')
            partes = patron.match(linea_nit)
            if partes:
                numeros = partes.group(1).replace(" ", "")
                if len(numeros) >= 9:
                    nits_encontrados.append(('Patrón 1', numeros[:-1], numeros[-1]))

        if nit_match2:
            nit_raw = nit_match2.group(1).replace(' ', '').replace('\n', '').strip()
            dv = nit_match2.group(2).strip()
            if 9 <= len(nit_raw) <= 11:
                nits_encontrados.append(('Patrón 2', nit_raw, dv))

        if nit_match3:
            nit_raw = nit_match3.group(1).replace(' ', '').replace('\n', '').strip()
            if 9 <= len(nit_raw) <= 11:
                nits_encontrados.append(('Patrón 3', nit_raw[:-1], nit_raw[-1]))

        if nit_match4:
            nit_raw = nit_match4.group(1)
            dv = nit_match4.group(2) if nit_match4.group(2) else nit_raw[-1]
            if 9 <= len(nit_raw) <= 11:
                nits_encontrados.append(('Patrón 4', nit_raw if dv else nit_raw[:-1], dv))

        if nits_encontrados:
            self.stdout.write(self.style.SUCCESS(f"\n   ✅ NITs encontrados por patrón:"))
            for patron, nit, dv in nits_encontrados:
                self.stdout.write(f"      • {patron}: {nit}-{dv}")
        else:
            self.stdout.write(self.style.ERROR("\n   ❌ NO SE ENCONTRÓ NINGÚN NIT VÁLIDO"))
            self.stdout.write("\n   💡 RECOMENDACIONES:")
            self.stdout.write("      1. Revisar el texto extraído (usar --save-text para guardarlo)")
            self.stdout.write("      2. Verificar si el PDF está corrupto o es una imagen escaneada")
            self.stdout.write("      3. Intentar OCR si es necesario")
            self.stdout.write("      4. Proporcionar el NIT manualmente")

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("DIAGNÓSTICO COMPLETADO"))
        self.stdout.write(self.style.SUCCESS("=" * 80 + "\n"))

        connection.close()

