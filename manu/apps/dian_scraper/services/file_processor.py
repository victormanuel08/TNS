import os
import zipfile
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import shutil
from django.conf import settings
from .xml_parser import UBLXMLParser
from .ubl_models import UBLDocument

class FileProcessor:
    def __init__(self):
        self.parser = UBLXMLParser()
        self.downloads_dir = Path(settings.MEDIA_ROOT) / 'dian_downloads'
        self.exports_dir = Path(settings.MEDIA_ROOT) / 'dian_exports'
        self.facturas_dir = Path(settings.MEDIA_ROOT) / 'dian_facturas'  # Carpeta para guardar XMLs/PDFs
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.facturas_dir.mkdir(parents=True, exist_ok=True)

    def process_downloaded_files(self, session_id: int, search_type: str) -> Dict[str, Any]:
        """Procesa todos los archivos ZIP descargados y genera JSON/Excel"""
        session_dir = self.downloads_dir / f"session_{session_id}"
        
        if not session_dir.exists():
            return {"error": "No se encontraron archivos descargados"}
        
        zip_files = list(session_dir.glob("*.zip"))
        if not zip_files:
            return {"error": "No se encontraron archivos ZIP"}

        all_documents = []
        
        # Procesar ZIPs en paralelo para acelerar
        from concurrent.futures import ThreadPoolExecutor
        import threading
        
        def process_zip_safe(zip_file):
            """Wrapper thread-safe para procesar un ZIP"""
            try:
                # Cada thread necesita su propia conexión a la BD
                from django.db import connection
                connection.close()
                return self._process_zip_file(zip_file, search_type, session_id)
            except Exception as e:
                print(f"❌ Error procesando ZIP {zip_file.name}: {e}")
                import traceback
                traceback.print_exc()
                return []
        
        # Procesar ZIPs en paralelo (configurable)
        # Nota: Cada ZIP se extrae en memoria temporal y parsea XMLs
        # Por defecto: 10 workers (configurable vía DIAN_SCRAPER_ZIP_WORKERS)
        # Si hay problemas de memoria, reducir en settings.py
        max_workers_config = getattr(settings, 'DIAN_SCRAPER_ZIP_WORKERS', 10)
        max_workers = min(max_workers_config, len(zip_files))
        print(f"🔄 Procesando {len(zip_files)} ZIPs con {max_workers} workers en paralelo...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(process_zip_safe, zip_files))
        
        # Combinar todos los documentos
        for documents in results:
            all_documents.extend(documents)
        
        print(f"✅ Procesamiento completado: {len(all_documents)} documentos extraídos")

        if not all_documents:
            return {"error": "No se encontraron documentos XML válidos"}

        # Generar archivos de salida
        return self._generate_output_files(all_documents, session_id)

    def _process_zip_file(self, zip_path: Path, search_type: str, session_id: int) -> List[Dict[str, Any]]:
        """Procesa un archivo ZIP individual y guarda XMLs/PDFs en carpeta permanente"""
        documents = []
        temp_extract_dir = zip_path.parent / f"temp_{zip_path.stem}"
        
        # Carpeta permanente para guardar facturas de esta sesión
        session_facturas_dir = self.facturas_dir / f"session_{session_id}"
        session_facturas_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Extraer ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            
            # Mapeo de nombres originales a nombres descriptivos
            xml_pdf_mapping = {}  # {nombre_original_xml: nombre_descriptivo}
            
            # Procesar cada XML y guardarlo permanentemente con nombre descriptivo
            for xml_file in temp_extract_dir.rglob("*.xml"):
                try:
                    with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
                        xml_content = f.read()
                    
                    document = self.parser.parse_xml(xml_content, search_type)
                    if document:
                        documents.append(self._document_to_dict(document))
                        
                        # Extraer información para el nombre descriptivo
                        nit_emisor = self._normalize_nit(document.supplier.nit) if document.supplier.nit else "SIN_NIT"
                        prefijo, numero = self._extraer_prefijo_numero(document.document_number)
                        
                        # Crear nombre descriptivo: {nit_emisor}_{prefijo}_{numero}.xml
                        nombre_descriptivo = f"{nit_emisor}_{prefijo}_{numero}.xml"
                        xml_dest = session_facturas_dir / nombre_descriptivo
                        
                        # Si ya existe un archivo con ese nombre, agregar sufijo
                        if xml_dest.exists():
                            contador = 1
                            while xml_dest.exists():
                                nombre_descriptivo = f"{nit_emisor}_{prefijo}_{numero}_{contador}.xml"
                                xml_dest = session_facturas_dir / nombre_descriptivo
                                contador += 1
                        
                        shutil.copy2(xml_file, xml_dest)
                        
                        # Guardar mapeo para asociar PDFs
                        xml_pdf_mapping[xml_file.stem] = nombre_descriptivo.replace('.xml', '')
                        print(f"📄 XML guardado: {xml_dest.name}")
                        
                except Exception as e:
                    print(f"Error procesando {xml_file}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Copiar PDFs con nombres descriptivos basados en los XMLs
            for pdf_file in temp_extract_dir.rglob("*.pdf"):
                try:
                    pdf_stem = pdf_file.stem  # Nombre sin extensión
                    nombre_descriptivo = None
                    
                    # Intentar encontrar el XML correspondiente
                    if pdf_stem in xml_pdf_mapping:
                        # Mismo nombre base que un XML
                        nombre_descriptivo = f"{xml_pdf_mapping[pdf_stem]}.pdf"
                    else:
                        # Buscar XML con nombre similar (sin extensión)
                        for xml_stem, nombre_base in xml_pdf_mapping.items():
                            if pdf_stem.startswith(xml_stem) or xml_stem.startswith(pdf_stem):
                                nombre_descriptivo = f"{nombre_base}.pdf"
                                break
                    
                    # Si no se encontró mapeo, usar nombre original pero en carpeta descriptiva
                    if not nombre_descriptivo:
                        # Intentar extraer info del nombre original o usar nombre genérico
                        nombre_descriptivo = f"FACTURA_{pdf_stem}.pdf"
                    
                    pdf_dest = session_facturas_dir / nombre_descriptivo
                    
                    # Si ya existe, agregar sufijo
                    if pdf_dest.exists():
                        contador = 1
                        base_name = nombre_descriptivo.replace('.pdf', '')
                        while pdf_dest.exists():
                            nombre_descriptivo = f"{base_name}_{contador}.pdf"
                            pdf_dest = session_facturas_dir / nombre_descriptivo
                            contador += 1
                    
                    shutil.copy2(pdf_file, pdf_dest)
                    print(f"📄 PDF guardado: {pdf_dest.name}")
                except Exception as e:
                    print(f"Error copiando PDF {pdf_file}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                    
        except Exception as e:
            print(f"Error procesando ZIP {zip_path}: {e}")
        finally:
            # Limpiar directorio temporal
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
        
        return documents
    
    def _normalize_nit(self, nit: str) -> str:
        """Normaliza NIT: quita puntos, guiones y espacios"""
        if not nit:
            return "SIN_NIT"
        import re
        return re.sub(r'\D', '', str(nit))
    
    def _extraer_prefijo_numero(self, document_number: str) -> Tuple[str, str]:
        """
        Extrae prefijo y número de un número de documento.
        Ejemplos:
        - "FV-001" -> ("FV", "001")
        - "NC-123" -> ("NC", "123")
        - "FV001" -> ("FV", "001")
        - "001" -> ("DOC", "001")
        """
        if not document_number:
            return ("DOC", "000")
        
        import re
        # Intentar separar por guión: "FV-001"
        if '-' in document_number:
            parts = document_number.split('-', 1)
            if len(parts) == 2:
                prefijo = parts[0].strip().upper()
                numero = parts[1].strip()
                return (prefijo, numero)
        
        # Intentar separar por espacios: "FV 001"
        if ' ' in document_number:
            parts = document_number.split(' ', 1)
            if len(parts) == 2:
                prefijo = parts[0].strip().upper()
                numero = parts[1].strip()
                return (prefijo, numero)
        
        # Intentar extraer prefijo alfabético y número: "FV001" -> ("FV", "001")
        match = re.match(r'^([A-Za-z]+)(\d+)$', document_number.strip())
        if match:
            prefijo = match.group(1).upper()
            numero = match.group(2)
            return (prefijo, numero)
        
        # Si solo hay números, usar "DOC" como prefijo
        if document_number.strip().isdigit():
            return ("DOC", document_number.strip())
        
        # Si no se puede separar, usar todo como número
        return ("DOC", document_number.strip())

    def _document_to_dict(self, document: UBLDocument) -> Dict[str, Any]:
        """Convierte UBLDocument a dict para JSON"""
        return {
            'TipoDocumento': document.document_type,
            'TipoBusqueda': document.search_type,
            'Numero de Factura': document.document_number,
            'CUFE': document.cufe,
            'Fecha de Creación': document.issue_date,
            'Fecha de Vencimiento': document.due_date,
            'Moneda': document.currency,
            'NIT del Emisor': document.supplier.nit,
            'Razon Social del Emisor': document.supplier.name,
            'NIT del Receptor': document.customer.nit,
            'Razon Social del Receptor': document.customer.name,
            'Metodo de Pago': document.payment_method,
            'Sub Total': float(document.line_extension_amount),
            'Impuestos Cabecera': float(document.total_header_taxes),
            'Retenciones': float(document.withholdings),
            'Total a Pagar': float(document.total_payable),
            'TaxBreakdown': [
                {
                    'code': tax.code,
                    'name': tax.name,
                    'percent': float(tax.percent),
                    'taxable_amount': float(tax.taxable_amount),
                    'amount': float(tax.amount),
                }
                for tax in document.tax_breakdown
            ],
            'LineItems': [
                {
                    'Nombre del Producto': line.product_name,
                    'Referencia': line.reference,
                    'Unidad de Medida': line.unit_measure,
                    'Cantidad': float(line.quantity),
                    'Precio Unitario': float(line.unit_price),
                    'Total': float(line.total),
                    'taxes': [
                        {
                            'code': tax.code,
                            'name': tax.name,
                            'percent': float(tax.percent),
                            'taxable_amount': float(tax.taxable_amount),
                            'amount': float(tax.amount),
                        }
                        for tax in line.taxes
                    ],
                    'total_tax_line': float(line.total_tax_line),
                }
                for line in document.line_items
            ]
        }

    def _generate_output_files(self, documents: List[Dict[str, Any]], session_id: int) -> Dict[str, Any]:
        """Genera archivos JSON y Excel"""
        from django.utils import timezone
        import pandas as pd
        from datetime import datetime
        
        timestamp = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Generar JSON
        json_filename = f"resultado_{timestamp}.json"
        json_path = self.exports_dir / json_filename
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
        
        # Generar Excel con dos hojas
        excel_filename = f"resultado_{timestamp}.xlsx"
        excel_path = self.exports_dir / excel_filename
        
        # Hoja 1: Resumen de documentos
        summary_data = []
        for doc in documents:
            summary_data.append({
                'TipoDocumento': doc.get('TipoDocumento', ''),
                'Numero': doc.get('Numero de Factura', ''),
                'CUFE': doc.get('CUFE', ''),
                'Fecha': doc.get('Fecha de Creación', ''),
                'Vencimiento': doc.get('Fecha de Vencimiento', ''),
                'Moneda': doc.get('Moneda', ''),
                'NIT_Emisor': doc.get('NIT del Emisor', ''),
                'Nombre_Emisor': doc.get('Razon Social del Emisor', ''),
                'NIT_Receptor': doc.get('NIT del Receptor', ''),
                'Nombre_Receptor': doc.get('Razon Social del Receptor', ''),
                'MetodoPago': doc.get('Metodo de Pago', ''),
                'Subtotal': doc.get('Sub Total', 0),
                'ImpuestosCabecera': doc.get('Impuestos Cabecera', 0),
                'Retenciones': doc.get('Retenciones', 0),
                'TotalPagar': doc.get('Total a Pagar', 0),
                'Lineas': len(doc.get('LineItems', [])),
            })
        
        # Hoja 2: Detalle de líneas
        line_data = []
        for doc in documents:
            cufe = doc.get('CUFE', '')
            numero = doc.get('Numero de Factura', '')
            tipo = doc.get('TipoDocumento', '')
            fecha = doc.get('Fecha de Creación', '')
            nit_emi = doc.get('NIT del Emisor', '')
            nit_rec = doc.get('NIT del Receptor', '')
            
            for idx, line in enumerate(doc.get('LineItems', [])):
                taxes = line.get('taxes', [])
                if not taxes:
                    taxes = [{}]
                
                for tax in taxes:
                    line_data.append({
                        'TipoDocumento': tipo,
                        'Numero': numero,
                        'CUFE': cufe,
                        'Fecha': fecha,
                        'NIT_Emisor': nit_emi,
                        'NIT_Receptor': nit_rec,
                        'Linea': idx + 1,
                        'Nombre_Producto': line.get('Nombre del Producto', ''),
                        'Referencia': line.get('Referencia', ''),
                        'Medida': line.get('Unidad de Medida', ''),
                        'Cantidad': line.get('Cantidad', 0),
                        'PrecioUnitario': line.get('Precio Unitario', 0),
                        'TotalLinea': line.get('Total', 0),
                        'ImpCode': tax.get('code', ''),
                        'ImpName': tax.get('name', ''),
                        'ImpPercent': tax.get('percent', 0),
                        'ImpBase': tax.get('taxable_amount', 0),
                        'ImpValor': tax.get('amount', 0),
                    })
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Documentos', index=False)
            pd.DataFrame(line_data).to_excel(writer, sheet_name='Lineas', index=False)
        
        return {
            'json_file': f"dian_exports/{json_filename}",
            'excel_file': f"dian_exports/{excel_filename}",
            'documents_count': len(documents),
            'documents': documents
        }
        