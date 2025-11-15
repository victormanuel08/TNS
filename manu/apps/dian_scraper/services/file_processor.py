import os
import zipfile
import json
from pathlib import Path
from typing import List, Dict, Any
import shutil
from django.conf import settings
from .xml_parser import UBLXMLParser
from .ubl_models import UBLDocument

class FileProcessor:
    def __init__(self):
        self.parser = UBLXMLParser()
        self.downloads_dir = Path(settings.MEDIA_ROOT) / 'dian_downloads'
        self.exports_dir = Path(settings.MEDIA_ROOT) / 'dian_exports'
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def process_downloaded_files(self, session_id: int, search_type: str) -> Dict[str, Any]:
        """Procesa todos los archivos ZIP descargados y genera JSON/Excel"""
        session_dir = self.downloads_dir / f"session_{session_id}"
        
        if not session_dir.exists():
            return {"error": "No se encontraron archivos descargados"}
        
        zip_files = list(session_dir.glob("*.zip"))
        if not zip_files:
            return {"error": "No se encontraron archivos ZIP"}

        all_documents = []
        
        for zip_file in zip_files:
            documents = self._process_zip_file(zip_file, search_type)
            all_documents.extend(documents)

        if not all_documents:
            return {"error": "No se encontraron documentos XML válidos"}

        # Generar archivos de salida
        return self._generate_output_files(all_documents, session_id)

    def _process_zip_file(self, zip_path: Path, search_type: str) -> List[Dict[str, Any]]:
        """Procesa un archivo ZIP individual"""
        documents = []
        temp_extract_dir = zip_path.parent / f"temp_{zip_path.stem}"
        
        try:
            # Extraer ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            
            # Procesar cada XML
            for xml_file in temp_extract_dir.rglob("*.xml"):
                try:
                    with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
                        xml_content = f.read()
                    
                    document = self.parser.parse_xml(xml_content, search_type)
                    if document:
                        documents.append(self._document_to_dict(document))
                        
                except Exception as e:
                    print(f"Error procesando {xml_file}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error procesando ZIP {zip_path}: {e}")
        finally:
            # Limpiar directorio temporal
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
        
        return documents

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
        