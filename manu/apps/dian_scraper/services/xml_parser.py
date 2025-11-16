import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import Optional, List
from .ubl_models import UBLDocument, PartyInfo, TaxDetail, LineItem

class UBLXMLParser:
    def __init__(self):
        self.namespaces = {
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
        }
    
    def parse_xml(self, xml_content: str, search_type: str = None) -> Optional[UBLDocument]:
        try:
            root = ET.fromstring(xml_content)
            
            # Determinar tipo de documento
            doc_type = self._get_document_type(root)
            if not doc_type:
                return None
            
            return self._parse_ubl_document(root, doc_type, search_type)
        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")
            return None
    
    def _get_document_type(self, root) -> Optional[str]:
        if root.tag.endswith('Invoice'):
            return 'Invoice'
        elif root.tag.endswith('CreditNote'):
            return 'CreditNote'
        elif root.tag.endswith('DebitNote'):
            return 'DebitNote'
        return None
    
    def _parse_ubl_document(self, root, doc_type: str, search_type: str) -> UBLDocument:
        doc = UBLDocument(document_type=doc_type, search_type=search_type)
        
        # Datos básicos
        doc.document_number = self._get_text(root, 'cbc:ID')
        doc.cufe = self._get_text(root, 'cbc:UUID')
        doc.issue_date = self._get_text(root, 'cbc:IssueDate')
        doc.due_date = self._get_text(root, 'cbc:DueDate')
        doc.currency = self._get_text(root, 'cbc:DocumentCurrencyCode')
        
        # Información de partes
        doc.supplier = self._parse_party_info(root, 'cac:AccountingSupplierParty')
        doc.customer = self._parse_party_info(root, 'cac:AccountingCustomerParty')
        
        # Método de pago
        doc.payment_method = self._get_payment_method(root)
        
        # Totales
        doc.line_extension_amount = self._parse_amount(root, 'cac:LegalMonetaryTotal/cbc:LineExtensionAmount')
        doc.total_payable = self._parse_amount(root, 'cac:LegalMonetaryTotal/cbc:PayableAmount')
        
        # Impuestos
        doc.tax_breakdown, doc.total_header_taxes = self._parse_taxes(root)
        doc.withholdings = self._calculate_withholdings(doc.tax_breakdown)
        
        # Líneas de detalle
        doc.line_items = self._parse_line_items(root, doc_type)
        
        return doc
    
    def _resolve_path(self, path: str, descendant: bool = False) -> str:
        segments = []
        for part in path.split('/'):
            if ':' in part:
                prefix, tag = part.split(':', 1)
                ns_uri = self.namespaces.get(prefix)
                part = f'{{{ns_uri}}}{tag}' if ns_uri else tag
            segments.append(part)
        resolved = '/'.join(segments)
        return f'.//{resolved}' if descendant else resolved

    def _find_element(self, element, path: str, descendant: bool = False):
        if element is None:
            return None
        try:
            search_path = self._resolve_path(path, descendant=descendant)
            return element.find(search_path)
        except Exception:
            return None

    def _get_text(self, element, path: str, descendant: bool = False) -> Optional[str]:
        target = self._find_element(element, path, descendant=descendant)
        if target is not None and target.text:
            return target.text.strip()
        return None
    
    def _parse_amount(self, element, path: str) -> Decimal:
        text = self._get_text(element, path)
        try:
            return Decimal(text) if text else Decimal('0')
        except:
            return Decimal('0')
    
    def _parse_party_info(self, root, party_path: str) -> PartyInfo:
        party_info = PartyInfo()
        party_elem = self._find_element(root, party_path, descendant=True)

        if party_elem is not None:
            company_id = self._get_text(party_elem, 'cac:PartyTaxScheme/cbc:CompanyID', descendant=True)
            if not company_id:
                company_id = self._get_text(party_elem, 'cac:PartyLegalEntity/cbc:CompanyID', descendant=True)
            if not company_id:
                company_id = self._get_text(party_elem, 'cac:PartyIdentification/cbc:ID', descendant=True)
            party_info.nit = company_id

            name_value = self._get_text(party_elem, 'cac:PartyName/cbc:Name', descendant=True)
            if not name_value:
                name_value = self._get_text(party_elem, 'cac:PartyLegalEntity/cbc:RegistrationName', descendant=True)
            if not name_value:
                name_value = self._get_text(party_elem, 'cac:PartyTaxScheme/cbc:RegistrationName', descendant=True)
            party_info.name = name_value or party_info.nit

        return party_info
    
    def _get_payment_method(self, root) -> Optional[str]:
        payment_means = root.find('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PaymentMeans')
        if payment_means is not None:
            method_code = payment_means.find('{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PaymentMeansCode')
            return method_code.text if method_code is not None else None
        return None
    
    def _parse_taxes(self, root) -> tuple[List[TaxDetail], Decimal]:
        tax_totals = root.findall('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxTotal')
        breakdown = []
        total_taxes = Decimal('0')
        
        for tax_total in tax_totals:
            tax_amount = tax_total.find('{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount')
            amount = self._parse_amount(tax_total, 'cbc:TaxAmount')
            total_taxes += amount
            
            # Subtotal de impuestos
            subtotals = tax_total.findall('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxSubtotal')
            for subtotal in subtotals:
                tax_detail = TaxDetail()
                
                # Código y nombre del impuesto
                tax_scheme = subtotal.find('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme')
                if tax_scheme is not None:
                    tax_detail.code = self._get_text(tax_scheme, 'cbc:ID')
                    tax_detail.name = self._get_text(tax_scheme, 'cbc:Name')
                
                # Porcentaje
                percent_elem = subtotal.find('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Percent')
                if percent_elem is not None and percent_elem.text:
                    try:
                        tax_detail.percent = Decimal(percent_elem.text)
                    except:
                        tax_detail.percent = Decimal('0')
                
                # Montos
                tax_detail.taxable_amount = self._parse_amount(subtotal, 'cbc:TaxableAmount')
                tax_detail.amount = self._parse_amount(subtotal, 'cbc:TaxAmount')
                
                breakdown.append(tax_detail)
        
        return breakdown, total_taxes
    
    def _calculate_withholdings(self, tax_breakdown: List[TaxDetail]) -> Decimal:
        withholdings = Decimal('0')
        for tax in tax_breakdown:
            if tax.name and 'reten' in tax.name.lower():
                withholdings += tax.amount
            elif tax.code in ['06', '07', '08']:
                withholdings += tax.amount
        return withholdings
    
    def _parse_line_items(self, root, doc_type: str) -> List[LineItem]:
        line_items = []
        
        # Determinar el tag según el tipo de documento
        if doc_type == 'CreditNote':
            line_tag = '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}CreditNoteLine'
        elif doc_type == 'DebitNote':
            line_tag = '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}DebitNoteLine'
        else:
            line_tag = '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}InvoiceLine'
        
        lines = root.findall(f'.//{line_tag}')
        
        for line in lines:
            line_item = LineItem()
            
            # Cantidad y unidad de medida
            qty_elem = self._find_quantity_element(line, doc_type)
            if qty_elem is not None:
                line_item.quantity = self._parse_amount_element(qty_elem)
                line_item.unit_measure = qty_elem.get('unitCode') if qty_elem is not None else None
            
            # Precio unitario
            price_elem = line.find('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PriceAmount')
            if price_elem is not None and price_elem.text:
                try:
                    line_item.unit_price = Decimal(price_elem.text)
                except:
                    line_item.unit_price = Decimal('0')
            
            # Total de línea
            line_ext_elem = line.find('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}LineExtensionAmount')
            line_item.total = self._parse_amount_element(line_ext_elem)
            
            # Información del producto
            item_elem = line.find('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Item')
            if item_elem is not None:
                line_item.product_name = self._get_text(item_elem, 'cbc:Name')
                if not line_item.product_name:
                    line_item.product_name = self._get_text(item_elem, 'cbc:Description')
                
                # Referencia del producto
                seller_id = item_elem.find('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}SellersItemIdentification')
                if seller_id is not None:
                    seller_id_elem = seller_id.find('{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
                    line_item.reference = seller_id_elem.text if seller_id_elem is not None else None
                
                if not line_item.reference:
                    std_id = item_elem.find('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}StandardItemIdentification')
                    if std_id is not None:
                        std_id_elem = std_id.find('{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
                        line_item.reference = std_id_elem.text if std_id_elem is not None else None
            
            # Impuestos de línea
            line_item.taxes, line_item.total_tax_line = self._parse_line_taxes(line)
            
            line_items.append(line_item)
        
        return line_items
    
    def _find_quantity_element(self, line_element, doc_type: str):
        if doc_type == 'CreditNote':
            return line_element.find('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CreditedQuantity')
        elif doc_type == 'DebitNote':
            return line_element.find('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}DebitedQuantity')
        else:
            return line_element.find('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoicedQuantity')
    
    def _parse_amount_element(self, element) -> Decimal:
        if element is not None and element.text:
            try:
                return Decimal(element.text)
            except:
                return Decimal('0')
        return Decimal('0')
    
    def _parse_line_taxes(self, line_element) -> tuple[List[TaxDetail], Decimal]:
        tax_totals = line_element.findall('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxTotal')
        taxes = []
        total_tax = Decimal('0')
        
        for tax_total in tax_totals:
            subtotals = tax_total.findall('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxSubtotal')
            for subtotal in subtotals:
                tax_detail = TaxDetail()
                
                # Información del impuesto
                tax_scheme = subtotal.find('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme')
                if tax_scheme is not None:
                    tax_detail.code = self._get_text(tax_scheme, 'cbc:ID')
                    tax_detail.name = self._get_text(tax_scheme, 'cbc:Name')
                
                # Porcentaje
                percent_elem = subtotal.find('.//{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Percent')
                if percent_elem is not None and percent_elem.text:
                    try:
                        tax_detail.percent = Decimal(percent_elem.text)
                    except:
                        tax_detail.percent = Decimal('0')
                
                # Montos
                tax_detail.taxable_amount = self._parse_amount(subtotal, 'cbc:TaxableAmount')
                tax_detail.amount = self._parse_amount(subtotal, 'cbc:TaxAmount')
                total_tax += tax_detail.amount
                
                taxes.append(tax_detail)
        
        return taxes, total_tax
