from dataclasses import dataclass
from typing import List, Optional
from decimal import Decimal

@dataclass
class PartyInfo:
    nit: Optional[str] = None
    name: Optional[str] = None

@dataclass
class TaxDetail:
    code: Optional[str] = None
    name: Optional[str] = None
    percent: Decimal = Decimal('0')
    taxable_amount: Decimal = Decimal('0')
    amount: Decimal = Decimal('0')

@dataclass
class LineItem:
    product_name: Optional[str] = None
    reference: Optional[str] = None
    unit_measure: Optional[str] = None
    quantity: Decimal = Decimal('0')
    unit_price: Decimal = Decimal('0')
    total: Decimal = Decimal('0')
    taxes: List[TaxDetail] = None
    total_tax_line: Decimal = Decimal('0')
    
    def __post_init__(self):
        if self.taxes is None:
            self.taxes = []

@dataclass
class UBLDocument:
    document_type: str  # Invoice, CreditNote, DebitNote
    search_type: Optional[str] = None
    document_number: Optional[str] = None
    cufe: Optional[str] = None
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    supplier: PartyInfo = None
    customer: PartyInfo = None
    payment_method: Optional[str] = None
    payment_method_description: Optional[str] = None
    line_extension_amount: Decimal = Decimal('0')
    total_header_taxes: Decimal = Decimal('0')
    withholdings: Decimal = Decimal('0')
    total_payable: Decimal = Decimal('0')
    tax_breakdown: List[TaxDetail] = None
    line_items: List[LineItem] = None
    
    def __post_init__(self):
        if self.supplier is None:
            self.supplier = PartyInfo()
        if self.customer is None:
            self.customer = PartyInfo()
        if self.tax_breakdown is None:
            self.tax_breakdown = []
        if self.line_items is None:
            self.line_items = []