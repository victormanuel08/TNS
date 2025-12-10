"""
Comando para mostrar el prompt literal que se enviaría al servicio de IA/Analytics
para un XML específico.

Uso:
    python manage.py mostrar_prompt_ia --xml ruta/al/archivo.xml --empresa_nit 123456789 --session_id 1
    python manage.py mostrar_prompt_ia --document_id 123
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import json
from pathlib import Path
from apps.sistema_analitico.services.clasificador_contable_service import (
    ClasificadorContableService,
    PROMPTS
)


class Command(BaseCommand):
    help = 'Muestra el prompt literal que se enviaría al servicio de IA/Analytics para un XML o documento'

    def add_arguments(self, parser):
        parser.add_argument(
            '--xml',
            type=str,
            help='Ruta al archivo XML a procesar'
        )
        parser.add_argument(
            '--document_id',
            type=int,
            help='ID del DocumentProcessed a usar'
        )
        parser.add_argument(
            '--empresa_nit',
            type=str,
            help='NIT de la empresa (requerido si se usa --xml)'
        )
        parser.add_argument(
            '--session_id',
            type=int,
            help='ID de sesión (requerido si se usa --xml)'
        )

    def handle(self, *args, **options):
        servicio = ClasificadorContableService()
        
        if options['document_id']:
            # Usar documento existente
            self.stdout.write(self.style.SUCCESS(f'\n📄 Procesando documento ID: {options["document_id"]}\n'))
            
            try:
                from apps.dian_scraper.models import DocumentProcessed
                doc = DocumentProcessed.objects.select_related('session').get(id=options['document_id'])
                
                # Leer documento usando el servicio
                resultado = servicio.leer_documento_por_id(options['document_id'])
                
                if not resultado:
                    self.stdout.write(self.style.ERROR('❌ No se pudo leer el documento'))
                    return
                
                factura = resultado.get('factura')
                empresa_nit = resultado.get('empresa_nit')
                empresa_ciuu_info = resultado.get('empresa_ciuu_info', {})
                proveedor_nit = resultado.get('proveedor_nit', '')
                
                # Obtener información de CIUU
                empresa_ciuu_principal = empresa_ciuu_info.get('ciuu_principal')
                empresa_ciuu_secundarios = empresa_ciuu_info.get('ciuu_secundarios', [])
                
                # Buscar CIUU del proveedor
                rut_proveedor = servicio.buscar_rut_por_nit(proveedor_nit)
                proveedor_ciuu = rut_proveedor.get('ciuu_principal') if rut_proveedor else None
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
                return
                
        elif options['xml']:
            # Procesar XML directamente
            xml_path = Path(options['xml'])
            if not xml_path.exists():
                self.stdout.write(self.style.ERROR(f'❌ Archivo XML no encontrado: {xml_path}'))
                return
            
            if not options['empresa_nit'] or not options['session_id']:
                self.stdout.write(self.style.ERROR('❌ --empresa_nit y --session_id son requeridos cuando se usa --xml'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'\n📄 Procesando XML: {xml_path}\n'))
            
            # Parsear XML
            from apps.dian_scraper.services.xml_parser import UBLXMLParser
            parser = UBLXMLParser()
            
            with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
                xml_content = f.read()
            
            document = parser.parse_xml(xml_content, 'Received')
            if not document:
                self.stdout.write(self.style.ERROR('❌ No se pudo parsear el XML'))
                return
            
            # Convertir a formato de factura
            empresa_nit = options['empresa_nit']
            proveedor_nit = document.supplier.nit if document.supplier else ''
            
            # Obtener CIUU
            rut_empresa = servicio.buscar_rut_por_nit(empresa_nit)
            empresa_ciuu_principal = rut_empresa.get('ciuu_principal') if rut_empresa else None
            empresa_ciuu_secundarios = rut_empresa.get('ciuu_secundarios', []) if rut_empresa else []
            
            rut_proveedor = servicio.buscar_rut_por_nit(proveedor_nit)
            proveedor_ciuu = rut_proveedor.get('ciuu_principal') if rut_proveedor else None
            
            # Construir factura básica
            from datetime import datetime
            factura = {
                "numero_factura": document.document_number or 'N/A',
                "fecha": document.issue_date or str(datetime.now().date()),
                "cufe": document.cufe or '',
                "modalidad_pago": "credito",  # Por defecto
                "forma_pago": "efectivo",
                "forma_pago_codigo": document.payment_method or None,
                "forma_pago_descripcion": document.payment_method_description or None,
                "fecha_vencimiento": document.due_date,
                "proveedor_nit": proveedor_nit,
                "articulos": [
                    {
                        "nombre": item.product_name or f"Artículo {idx+1}",
                        "ref": item.reference or document.document_number,
                        "cantidad": float(item.quantity),
                        "valor_unitario": float(item.unit_price),
                        "valor_total": float(item.total),
                        "impuestos": [
                            {
                                "code": tax.code or '',
                                "nombre": tax.name or '',
                                "porcentaje": float(tax.percent),
                                "base": float(tax.taxable_amount),
                                "valor": float(tax.amount)
                            }
                            for tax in item.taxes
                        ]
                    }
                    for idx, item in enumerate(document.line_items)
                ] if document.line_items else []
            }
            
        else:
            self.stdout.write(self.style.ERROR('❌ Debes proporcionar --xml o --document_id'))
            return
        
        # Obtener información de CIUUs
        mi_ciuu_info = servicio.obtener_info_ciuu_cached(empresa_ciuu_principal)
        mi_ciuu_sec_info = [servicio.obtener_info_ciuu_cached(ciuu) for ciuu in empresa_ciuu_secundarios]
        
        empresa_desc = f"{mi_ciuu_info['descripcion']} [Fuente: {mi_ciuu_info['fuente']}]"
        if mi_ciuu_info.get('incluye'):
            empresa_desc += f". INCLUYE: {mi_ciuu_info['incluye']}"
        if mi_ciuu_info.get('excluye'):
            empresa_desc += f". EXCLUYE: {mi_ciuu_info['excluye']}"
        
        mi_ciuu_sec_desc = "\n".join([
            f"- {info['descripcion']} [Fuente: {info['fuente']}]. INCLUYE: {info.get('incluye', '')}. EXCLUYE: {info.get('excluye', '')}"
            for info in mi_ciuu_sec_info
        ])
        
        prov_ciuu_info = servicio.obtener_info_ciuu_cached(proveedor_ciuu) if proveedor_ciuu else {
            "descripcion": "No especificado",
            "incluye": "",
            "excluye": "",
            "fuente": "desconocido"
        }
        prov_desc = f"{prov_ciuu_info['descripcion']} [Fuente: {prov_ciuu_info['fuente']}]"
        if prov_ciuu_info.get('incluye'):
            prov_desc += f". INCLUYE: {prov_ciuu_info['incluye']}"
        if prov_ciuu_info.get('excluye'):
            prov_desc += f". EXCLUYE: {prov_ciuu_info['excluye']}"
        
        # Construir prompt
        user_content = PROMPTS["clasificacion_masiva"]["user"].format(
            empresa_id=empresa_nit,
            mi_ciuu=empresa_ciuu_principal or "N/A",
            mi_ciuu_desc=empresa_desc,
            mi_ciuu_sec=mi_ciuu_sec_desc or "Ninguno",
            proveedor_id=proveedor_nit or "N/A",
            ciuu_proveedor=proveedor_ciuu or "N/A",
            ciuu_proveedor_desc=prov_desc,
            tipo_operacion="Compra",
            aplica_retencion=False,
            porcentaje_retencion=0,
            modalidad_pago=factura.get('modalidad_pago', 'credito'),
            forma_pago_codigo=factura.get('forma_pago_codigo') or 'N/A',
            forma_pago_nombre=factura.get('forma_pago', 'efectivo'),
            forma_pago_descripcion=factura.get('forma_pago_descripcion') or 'N/A',
            facturas=json.dumps([factura], ensure_ascii=False, indent=2)
        )
        
        # Mostrar prompt completo
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('PROMPT SYSTEM (ROLE: system)'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        self.stdout.write(PROMPTS["clasificacion_masiva"]["system"])
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('PROMPT USER (ROLE: user)'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        self.stdout.write(user_content)
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('JSON DE FACTURA ENVIADA'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        self.stdout.write(json.dumps(factura, ensure_ascii=False, indent=2))
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('MESSAGES COMPLETO (como se envía al servicio de IA)'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        messages = [
            {"role": "system", "content": PROMPTS["clasificacion_masiva"]["system"]},
            {"role": "user", "content": user_content}
        ]
        self.stdout.write(json.dumps(messages, ensure_ascii=False, indent=2))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Prompt mostrado correctamente\n'))

