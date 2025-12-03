"""
Servicio para obtener eventos del calendario tributario basado en RUT y NIT
"""
from typing import List, Dict, Optional
from datetime import date
from ..models import (
    VigenciaTributaria, Impuesto, TipoTercero, TipoRegimen,
    RUT, EmpresaServidor
)


def normalize_nit(nit: str) -> str:
    """Normaliza NIT eliminando puntos, guiones y espacios"""
    if not nit:
        return ''
    return ''.join(c for c in str(nit) if c.isdigit())


def obtener_tipo_tercero_desde_rut(nit_normalizado: str) -> Optional[str]:
    """
    Obtiene el tipo de tercero (PN o PJ) desde el RUT.
    Retorna 'PN' para persona natural, 'PJ' para persona jurídica, o None si no se encuentra.
    """
    try:
        rut = RUT.objects.get(nit_normalizado=nit_normalizado)
        if rut.tipo_contribuyente == 'persona_natural':
            return 'PN'
        elif rut.tipo_contribuyente == 'persona_juridica':
            return 'PJ'
    except RUT.DoesNotExist:
        pass
    return None


def obtener_eventos_calendario_tributario(
    nit: str,
    tipo_regimen: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None
) -> List[Dict]:
    """
    Obtiene los eventos del calendario tributario para un NIT específico.
    
    Args:
        nit: NIT de la empresa (puede tener formato o estar normalizado)
        tipo_regimen: Código del régimen tributario (opcional, se intentará obtener del RUT)
        fecha_desde: Fecha desde la cual obtener eventos (opcional)
        fecha_hasta: Fecha hasta la cual obtener eventos (opcional)
    
    Returns:
        Lista de diccionarios con información de eventos tributarios
    """
    # Normalizar NIT
    nit_normalizado = normalize_nit(nit)
    if not nit_normalizado:
        return []
    
    # Obtener tipo de tercero desde RUT
    tipo_tercero_code = obtener_tipo_tercero_desde_rut(nit_normalizado)
    
    # Obtener últimos dígitos del NIT
    ultimo_digito = nit_normalizado[-1:] if len(nit_normalizado) > 0 else ''
    ultimos_dos_digitos = nit_normalizado[-2:] if len(nit_normalizado) > 1 else ''
    
    # Construir query base
    from django.db.models import Q
    
    # Filtros para dígitos: vacío (todos), último dígito, o últimos dos dígitos
    filtro_digitos = Q(digitos_nit='') | Q(digitos_nit=ultimo_digito)
    if len(ultimos_dos_digitos) == 2:
        filtro_digitos |= Q(digitos_nit=ultimos_dos_digitos)
    
    # Filtros para tipo de tercero
    filtro_tipo_tercero = Q(tipo_tercero__isnull=True)  # Aplica a todos
    if tipo_tercero_code:
        try:
            tipo_tercero = TipoTercero.objects.get(codigo=tipo_tercero_code)
            filtro_tipo_tercero |= Q(tipo_tercero=tipo_tercero)
        except TipoTercero.DoesNotExist:
            pass
    
    # Filtros para régimen
    filtro_regimen = Q(tipo_regimen__isnull=True)  # Aplica a todos
    if tipo_regimen:
        try:
            regimen = TipoRegimen.objects.get(codigo=tipo_regimen)
            filtro_regimen |= Q(tipo_regimen=regimen)
        except TipoRegimen.DoesNotExist:
            pass
    
    # Aplicar filtros de fecha
    filtro_fecha = Q()
    if fecha_desde:
        filtro_fecha &= Q(fecha_limite__gte=fecha_desde)
    if fecha_hasta:
        filtro_fecha &= Q(fecha_limite__lte=fecha_hasta)
    
    # Obtener vigencias
    vigencias = VigenciaTributaria.objects.filter(
        filtro_digitos,
        filtro_tipo_tercero,
        filtro_regimen,
        filtro_fecha
    ).select_related('impuesto', 'tipo_tercero', 'tipo_regimen').order_by('fecha_limite')
    
    # Convertir a lista de diccionarios
    eventos = []
    for vigencia in vigencias:
        eventos.append({
            'id': vigencia.id,
            'impuesto': {
                'codigo': vigencia.impuesto.codigo,
                'nombre': vigencia.impuesto.nombre,
                'descripcion': vigencia.impuesto.descripcion
            },
            'fecha_limite': vigencia.fecha_limite.isoformat(),
            'descripcion': vigencia.descripcion,
            'tipo_tercero': vigencia.tipo_tercero.codigo if vigencia.tipo_tercero else None,
            'tipo_regimen': vigencia.tipo_regimen.codigo if vigencia.tipo_regimen else None,
            'digitos_nit': vigencia.digitos_nit or 'TODOS',
            'dias_restantes': (vigencia.fecha_limite - date.today()).days if vigencia.fecha_limite else None
        })
    
    return eventos


def obtener_eventos_para_empresa(
    empresa_id: int,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None
) -> List[Dict]:
    """
    Obtiene eventos del calendario tributario para una empresa específica.
    """
    try:
        empresa = EmpresaServidor.objects.get(id=empresa_id)
        # Usar nit_normalizado directamente (ya está normalizado)
        return obtener_eventos_calendario_tributario(
            nit=empresa.nit_normalizado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
    except EmpresaServidor.DoesNotExist:
        return []

