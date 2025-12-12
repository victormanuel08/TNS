"""
Comando de management para cargar el PUC completo desde el PDF.

Uso:
    python manage.py cargar_puc_desde_pdf --pdf-path data/puc/PUC.pdf
    python manage.py cargar_puc_desde_pdf --dry-run  # Solo muestra qué haría
    python manage.py cargar_puc_desde_pdf --forzar  # Sobrescribe cuentas existentes
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import os
import re
import logging
import pdfplumber
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Carga el Plan Único de Cuentas (PUC) completo desde el PDF a la base de datos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pdf-path',
            type=str,
            default='data/puc/PUC.pdf',
            help='Ruta al archivo PDF del PUC (default: data/puc/PUC.pdf)'
        )
        parser.add_argument(
            '--pagina-inicio',
            type=int,
            default=5,
            help='Página inicial del PDF (default: 5)'
        )
        parser.add_argument(
            '--pagina-fin',
            type=int,
            default=114,
            help='Página final del PDF (default: 114)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra qué haría sin guardar realmente'
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Sobrescribe cuentas existentes si ya existen'
        )
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Elimina todas las cuentas PUC antes de cargar (CUIDADO)'
        )

    def handle(self, *args, **options):
        pdf_path = options['pdf_path']
        pagina_inicio = options['pagina_inicio'] - 1  # Convertir a índice 0-based
        pagina_fin = options['pagina_fin'] - 1
        dry_run = options['dry_run']
        forzar = options['forzar']
        limpiar = options['limpiar']
        
        # Verificar que existe el PDF
        if not os.path.exists(pdf_path):
            self.stdout.write(self.style.ERROR(f'❌ El archivo PDF no existe: {pdf_path}'))
            self.stdout.write(self.style.WARNING(f'   Asegúrate de que el PDF esté en: {pdf_path}'))
            return
        
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("CARGA DEL PLAN ÚNICO DE CUENTAS (PUC) DESDE PDF"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(f"📄 PDF: {pdf_path}")
        self.stdout.write(f"📄 Páginas: {pagina_inicio + 1} a {pagina_fin + 1}")
        self.stdout.write(f"🔧 Modo: {'DRY RUN (simulación)' if dry_run else 'REAL'}")
        self.stdout.write("")
        
        if limpiar and not dry_run:
            from apps.sistema_analitico.models import CuentaPUC
            count = CuentaPUC.objects.count()
            CuentaPUC.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"🗑️  Eliminadas {count} cuentas PUC existentes"))
        
        # Extraer cuentas del PDF
        self.stdout.write("📖 Extrayendo cuentas del PDF...")
        cuentas_extraidas = self._extraer_cuentas_puc(pdf_path, pagina_inicio, pagina_fin)
        
        self.stdout.write(self.style.SUCCESS(f"✅ Extraídas {len(cuentas_extraidas)} cuentas del PDF"))
        self.stdout.write("")
        
        # Mostrar resumen por nivel
        resumen = self._contar_por_nivel(cuentas_extraidas)
        self.stdout.write("📊 RESUMEN DE CUENTAS EXTRAÍDAS:")
        for nivel, count in sorted(resumen.items()):
            nivel_nombre = {1: 'Clase (1 dígito)', 2: 'Grupo (2 dígitos)', 4: 'Cuenta (4 dígitos)', 6: 'Subcuenta (6 dígitos)'}[nivel]
            self.stdout.write(f"   - {nivel_nombre}: {count} cuentas")
        self.stdout.write("")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN: No se guardarán las cuentas"))
            self.stdout.write(self.style.WARNING("   Ejecuta sin --dry-run para guardar realmente"))
            return
        
        # Guardar en base de datos
        self.stdout.write("💾 Guardando cuentas en base de datos...")
        resultado = self._guardar_cuentas(cuentas_extraidas, forzar)
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("✅ CARGA COMPLETADA"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(f"   - Creadas: {resultado['creadas']}")
        self.stdout.write(f"   - Actualizadas: {resultado['actualizadas']}")
        self.stdout.write(f"   - Omitidas: {resultado['omitidas']}")
        self.stdout.write(f"   - Errores: {resultado['errores']}")
        self.stdout.write("")
        
        # Mostrar total en BD
        from apps.sistema_analitico.models import CuentaPUC
        total_bd = CuentaPUC.objects.count()
        self.stdout.write(self.style.SUCCESS(f"📊 Total de cuentas PUC en BD: {total_bd}"))

    def _extraer_cuentas_puc(self, pdf_path: str, pagina_inicio: int, pagina_fin: int) -> List[Dict]:
        """
        Extrae todas las cuentas del PUC del PDF.
        Retorna lista de diccionarios con información de cada cuenta.
        """
        cuentas = []
        
        with pdfplumber.open(pdf_path) as pdf:
            total_paginas = len(pdf.pages)
            logger.info(f"Procesando PDF con {total_paginas} páginas")
            
            if pagina_inicio >= total_paginas:
                logger.warning(f"⚠️  La página {pagina_inicio + 1} no existe en el PDF (solo tiene {total_paginas} páginas).")
                return []
            
            # Extraer de TABLAS
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
                        
                        if not codigo_str:
                            continue
                        
                        # Detectar formato de rango: "240801 a 240898" o "240801-240898"
                        patron_rango = re.compile(r'(\d{4,6})\s*(?:a|-)\s*(\d{4,6})', re.IGNORECASE)
                        match_rango = patron_rango.search(codigo_str)
                        
                        if match_rango:
                            # Es un rango: extraer inicio y fin
                            inicio = match_rango.group(1)
                            fin = match_rango.group(2)
                            
                            # Agregar ambas cuentas (inicio y fin del rango)
                            for codigo in [inicio, fin]:
                                cuenta_info = self._procesar_cuenta(codigo, denominacion, es_rango=True, rango_inicio=inicio, rango_fin=fin)
                                if cuenta_info:
                                    cuentas.append(cuenta_info)
                            continue
                        
                        # Si no es rango, verificar si es solo número
                        codigo_limpio = codigo_str.replace(' ', '')
                        if not codigo_limpio.isdigit():
                            continue
                        
                        # Procesar cuenta normal
                        cuenta_info = self._procesar_cuenta(codigo_limpio, denominacion)
                        if cuenta_info:
                            cuentas.append(cuenta_info)
        
        return cuentas

    def _procesar_cuenta(self, codigo: str, denominacion: str, es_rango: bool = False, rango_inicio: Optional[str] = None, rango_fin: Optional[str] = None) -> Optional[Dict]:
        """
        Procesa una cuenta individual y retorna su información estructurada.
        """
        if not codigo or not codigo.isdigit():
            return None
        
        # Determinar nivel
        nivel = len(codigo)
        if nivel not in [1, 2, 4, 6]:
            return None
        
        # Extraer jerarquía
        clase = codigo[0] if len(codigo) >= 1 else None
        grupo = codigo[:2] if len(codigo) >= 2 else None
        cuenta_principal = codigo[:4] if len(codigo) >= 4 else None
        
        return {
            'codigo': codigo,
            'denominacion': denominacion,
            'nivel': nivel,
            'clase': clase,
            'grupo': grupo,
            'cuenta_principal': cuenta_principal,
            'es_rango': es_rango,
            'rango_inicio': rango_inicio if es_rango else None,
            'rango_fin': rango_fin if es_rango else None,
        }

    def _contar_por_nivel(self, cuentas: List[Dict]) -> Dict[int, int]:
        """Cuenta cuentas por nivel."""
        resumen = {}
        for cuenta in cuentas:
            nivel = cuenta['nivel']
            resumen[nivel] = resumen.get(nivel, 0) + 1
        return resumen

    def _guardar_cuentas(self, cuentas: List[Dict], forzar: bool) -> Dict[str, int]:
        """
        Guarda las cuentas en la base de datos.
        """
        from apps.sistema_analitico.models import CuentaPUC
        
        creadas = 0
        actualizadas = 0
        omitidas = 0
        errores = 0
        
        for cuenta_info in cuentas:
            try:
                codigo = cuenta_info['codigo']
                
                # Verificar si ya existe
                cuenta_existente = CuentaPUC.objects.filter(codigo=codigo).first()
                
                if cuenta_existente and not forzar:
                    omitidas += 1
                    continue
                
                # Preparar datos
                defaults = {
                    'denominacion': cuenta_info['denominacion'],
                    'nivel': cuenta_info['nivel'],
                    'clase': cuenta_info.get('clase'),
                    'grupo': cuenta_info.get('grupo'),
                    'cuenta_principal': cuenta_info.get('cuenta_principal'),
                    'es_rango': cuenta_info.get('es_rango', False),
                    'rango_inicio': cuenta_info.get('rango_inicio'),
                    'rango_fin': cuenta_info.get('rango_fin'),
                }
                
                # Crear o actualizar
                cuenta, creada = CuentaPUC.objects.update_or_create(
                    codigo=codigo,
                    defaults=defaults
                )
                
                if creada:
                    creadas += 1
                else:
                    actualizadas += 1
                    
            except Exception as e:
                logger.error(f"❌ Error al guardar cuenta {cuenta_info.get('codigo', 'N/A')}: {e}", exc_info=True)
                errores += 1
        
        return {
            'creadas': creadas,
            'actualizadas': actualizadas,
            'omitidas': omitidas,
            'errores': errores
        }

