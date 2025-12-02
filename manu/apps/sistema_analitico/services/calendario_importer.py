"""
Servicio para importar calendario tributario desde Excel
"""
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
import re


def normalize_nit(nit: str) -> str:
    """Normaliza NIT eliminando puntos, guiones y espacios"""
    if not nit:
        return ''
    return ''.join(c for c in str(nit) if c.isdigit())


def parse_date(date_str) -> datetime:
    """Parsea fecha desde string en formato DD/MM/YYYY o YYYY-MM-DD"""
    if pd.isna(date_str) or not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Intentar formato DD/MM/YYYY
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        pass
    
    # Intentar formato YYYY-MM-DD
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        pass
    
    # Intentar parseo automático de pandas
    try:
        return pd.to_datetime(date_str).date()
    except:
        pass
    
    return None


def importar_calendario_desde_excel(excel_file) -> Dict:
    """
    Importa calendario tributario desde Excel.
    
    Formato esperado:
    - tax_code: Código del impuesto (RGC, RPJ, etc.)
    - expirations_digits: Últimos dígitos del NIT ("1", "2", "01", "99", "00", "")
    - third_type_code: Tipo de tercero ("PN", "PJ", "")
    - regiment_type_code: Régimen tributario ("GC", "SIM", "ORD", "")
    - date: Fecha límite (DD/MM/YYYY o YYYY-MM-DD)
    - description: Descripción de la obligación
    
    Returns:
        Dict con:
        - success: bool
        - total: int
        - creados: int
        - actualizados: int
        - errores: List[Dict]
        - empresas_asociadas: List[Dict] (NITs encontrados)
    """
    from ..models import (
        Impuesto, TipoTercero, TipoRegimen, VigenciaTributaria,
        EmpresaServidor
    )
    
    resultados = {
        'success': True,
        'total': 0,
        'creados': 0,
        'actualizados': 0,
        'errores': [],
        'empresas_asociadas': []
    }
    
    try:
        # Leer Excel
        df = pd.read_excel(excel_file, sheet_name='CALENDARIO_TRIBUTARIO')
        
        # Validar columnas requeridas
        columnas_requeridas = ['tax_code', 'expirations_digits', 'third_type_code', 
                              'regiment_type_code', 'date', 'description']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        if columnas_faltantes:
            resultados['success'] = False
            resultados['errores'].append({
                'fila': 0,
                'error': f'Columnas faltantes: {", ".join(columnas_faltantes)}'
            })
            return resultados
        
        # Limpiar datos
        df = df.dropna(subset=['tax_code', 'date'])  # Eliminar filas sin tax_code o date
        df = df.fillna('')  # Reemplazar NaN con strings vacíos
        
        resultados['total'] = len(df)
        
        # Obtener NITs únicos de empresas para asociación
        empresas_nits = set()
        
        # Procesar cada fila
        for idx, row in df.iterrows():
            fila_num = idx + 2  # +2 porque Excel empieza en 1 y tiene encabezado
            
            try:
                # Obtener valores
                tax_code = str(row['tax_code']).strip()
                expirations_digits = str(row['expirations_digits']).strip() if pd.notna(row['expirations_digits']) else ''
                third_type_code = str(row['third_type_code']).strip() if pd.notna(row['third_type_code']) else ''
                regiment_type_code = str(row['regiment_type_code']).strip() if pd.notna(row['regiment_type_code']) else ''
                date_str = row['date']
                description = str(row['description']).strip() if pd.notna(row['description']) else 'Sin definir'
                
                # Validar tax_code
                if not tax_code:
                    resultados['errores'].append({
                        'fila': fila_num,
                        'error': 'tax_code es requerido'
                    })
                    continue
                
                # Obtener o crear Impuesto
                impuesto, _ = Impuesto.objects.get_or_create(
                    codigo=tax_code,
                    defaults={'nombre': tax_code, 'descripcion': ''}
                )
                
                # Obtener TipoTercero (si se especifica)
                tipo_tercero = None
                if third_type_code:
                    tipo_tercero, _ = TipoTercero.objects.get_or_create(
                        codigo=third_type_code,
                        defaults={'nombre': third_type_code}
                    )
                
                # Obtener TipoRegimen (si se especifica)
                tipo_regimen = None
                if regiment_type_code:
                    tipo_regimen, _ = TipoRegimen.objects.get_or_create(
                        codigo=regiment_type_code,
                        defaults={'nombre': regiment_type_code}
                    )
                
                # Parsear fecha
                fecha_limite = parse_date(date_str)
                if not fecha_limite:
                    resultados['errores'].append({
                        'fila': fila_num,
                        'error': f'Fecha inválida: {date_str}'
                    })
                    continue
                
                # Normalizar expirations_digits
                if expirations_digits:
                    # Validar formato (1-2 dígitos)
                    if not re.match(r'^\d{1,2}$', expirations_digits):
                        resultados['errores'].append({
                            'fila': fila_num,
                            'error': f'expirations_digits inválido: {expirations_digits} (debe ser 1-2 dígitos)'
                        })
                        continue
                else:
                    expirations_digits = ''  # Vacío = aplica a todos
                
                # Buscar o crear VigenciaTributaria
                vigencia, created = VigenciaTributaria.objects.update_or_create(
                    impuesto=impuesto,
                    digitos_nit=expirations_digits,
                    tipo_tercero=tipo_tercero,
                    tipo_regimen=tipo_regimen,
                    defaults={
                        'fecha_limite': fecha_limite,
                        'descripcion': description
                    }
                )
                
                if created:
                    resultados['creados'] += 1
                else:
                    resultados['actualizados'] += 1
                
                # Si hay dígitos, buscar empresas que coincidan
                if expirations_digits:
                    # Buscar empresas cuyo NIT termine en esos dígitos
                    empresas = EmpresaServidor.objects.all()
                    for empresa in empresas:
                        nit_norm = normalize_nit(empresa.nit)
                        if nit_norm:
                            # Verificar si los últimos dígitos coinciden
                            if len(expirations_digits) == 1:
                                # Último dígito
                                if nit_norm[-1:] == expirations_digits:
                                    if nit_norm not in empresas_nits:
                                        empresas_nits.add(nit_norm)
                                        resultados['empresas_asociadas'].append({
                                            'nit': empresa.nit,
                                            'nit_normalizado': nit_norm,
                                            'nombre': empresa.nombre,
                                            'codigo': empresa.codigo
                                        })
                            elif len(expirations_digits) == 2:
                                # Últimos dos dígitos
                                if nit_norm[-2:] == expirations_digits:
                                    if nit_norm not in empresas_nits:
                                        empresas_nits.add(nit_norm)
                                        resultados['empresas_asociadas'].append({
                                            'nit': empresa.nit,
                                            'nit_normalizado': nit_norm,
                                            'nombre': empresa.nombre,
                                            'codigo': empresa.codigo
                                        })
                
            except Exception as e:
                resultados['errores'].append({
                    'fila': fila_num,
                    'error': str(e)
                })
        
        # Si hay dígitos vacíos, buscar todas las empresas
        if any(str(row.get('expirations_digits', '')).strip() == '' for _, row in df.iterrows()):
            todas_empresas = EmpresaServidor.objects.all()
            for empresa in todas_empresas:
                nit_norm = normalize_nit(empresa.nit)
                if nit_norm and nit_norm not in empresas_nits:
                    empresas_nits.add(nit_norm)
                    resultados['empresas_asociadas'].append({
                        'nit': empresa.nit,
                        'nit_normalizado': nit_norm,
                        'nombre': empresa.nombre,
                        'codigo': empresa.codigo
                    })
        
        resultados['empresas_asociadas'] = list({e['nit_normalizado']: e for e in resultados['empresas_asociadas']}.values())
        
    except Exception as e:
        resultados['success'] = False
        resultados['errores'].append({
            'fila': 0,
            'error': f'Error al procesar Excel: {str(e)}'
        })
    
    return resultados

