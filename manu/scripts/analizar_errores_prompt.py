"""
Script para analizar los errores del prompt consultando el modelo PUC.
"""
import os
import sys
import django

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.sistema_analitico.models import CuentaPUC

def buscar_cuentas_relacionadas():
    """Busca cuentas relacionadas con los conceptos mencionados en el prompt."""
    
    resultados = {
        'servicios_publicos': [],
        'honorarios': [],
        'costos': [],
        'arrendamientos': [],
        'seguros': [],
        'vigilancia': [],
        'aseo': [],
        'publicidad': [],
        'cuentas_52xx': [],
        'cuentas_53xx': [],
        'cuentas_54xx': [],
        'cuentas_55xx': [],
        'cuentas_1105xx': [],
        'cuentas_61xx': [],
    }
    
    # Servicios públicos
    resultados['servicios_publicos'] = list(CuentaPUC.objects.filter(
        denominacion__icontains='servicio'
    ).exclude(denominacion__icontains='personal').exclude(denominacion__icontains='honorario')[:15])
    
    # Honorarios
    resultados['honorarios'] = list(CuentaPUC.objects.filter(
        denominacion__icontains='honorario'
    )[:15])
    
    # Costos
    resultados['costos'] = list(CuentaPUC.objects.filter(
        codigo__startswith='61'
    )[:20])
    
    # Arrendamientos
    resultados['arrendamientos'] = list(CuentaPUC.objects.filter(
        denominacion__icontains='arrend'
    )[:15])
    
    # Seguros
    resultados['seguros'] = list(CuentaPUC.objects.filter(
        denominacion__icontains='seguro'
    )[:15])
    
    # Vigilancia
    resultados['vigilancia'] = list(CuentaPUC.objects.filter(
        denominacion__icontains='vigilancia'
    )[:15])
    
    # Aseo
    resultados['aseo'] = list(CuentaPUC.objects.filter(
        denominacion__icontains='aseo'
    )[:15])
    
    # Publicidad
    resultados['publicidad'] = list(CuentaPUC.objects.filter(
        denominacion__icontains='publicidad'
    )[:15])
    
    # Cuentas 52xx
    resultados['cuentas_52xx'] = list(CuentaPUC.objects.filter(
        codigo__startswith='52',
        nivel=4
    )[:20])
    
    # Cuentas 53xx
    resultados['cuentas_53xx'] = list(CuentaPUC.objects.filter(
        codigo__startswith='53',
        nivel=4
    )[:20])
    
    # Cuentas 54xx
    resultados['cuentas_54xx'] = list(CuentaPUC.objects.filter(
        codigo__startswith='54',
        nivel=4
    )[:20])
    
    # Cuentas 55xx
    resultados['cuentas_55xx'] = list(CuentaPUC.objects.filter(
        codigo__startswith='55',
        nivel=4
    )[:20])
    
    # Cuentas 1105xx
    resultados['cuentas_1105xx'] = list(CuentaPUC.objects.filter(
        codigo__startswith='1105'
    )[:20])
    
    # Cuentas 61xx
    resultados['cuentas_61xx'] = list(CuentaPUC.objects.filter(
        codigo__startswith='61',
        nivel=4
    )[:20])
    
    return resultados

if __name__ == '__main__':
    print("🔍 Analizando modelo PUC para encontrar cuentas correctas...")
    resultados = buscar_cuentas_relacionadas()
    
    print("\n" + "="*80)
    print("SERVICIOS PÚBLICOS:")
    print("="*80)
    for c in resultados['servicios_publicos']:
        print(f"  {c.codigo}: {c.denominacion}")
    
    print("\n" + "="*80)
    print("HONORARIOS:")
    print("="*80)
    for c in resultados['honorarios']:
        print(f"  {c.codigo}: {c.denominacion}")
    
    print("\n" + "="*80)
    print("COSTOS (61xx):")
    print("="*80)
    for c in resultados['costos']:
        print(f"  {c.codigo}: {c.denominacion}")
    
    print("\n" + "="*80)
    print("ARRENDAMIENTOS:")
    print("="*80)
    for c in resultados['arrendamientos']:
        print(f"  {c.codigo}: {c.denominacion}")
    
    print("\n" + "="*80)
    print("SEGUROS:")
    print("="*80)
    for c in resultados['seguros']:
        print(f"  {c.codigo}: {c.denominacion}")
    
    print("\n" + "="*80)
    print("VIGILANCIA:")
    print("="*80)
    for c in resultados['vigilancia']:
        print(f"  {c.codigo}: {c.denominacion}")
    
    print("\n" + "="*80)
    print("ASEO:")
    print("="*80)
    for c in resultados['aseo']:
        print(f"  {c.codigo}: {c.denominacion}")
    
    print("\n" + "="*80)
    print("PUBLICIDAD:")
    print("="*80)
    for c in resultados['publicidad']:
        print(f"  {c.codigo}: {c.denominacion}")
    
    print("\n" + "="*80)
    print("CUENTAS 52xx (4 dígitos):")
    print("="*80)
    for c in resultados['cuentas_52xx']:
        print(f"  {c.codigo}: {c.denominacion}")
    
    print("\n" + "="*80)
    print("CUENTAS 53xx (4 dígitos):")
    print("="*80)
    for c in resultados['cuentas_53xx']:
        print(f"  {c.codigo}: {c.denominacion}")
    
    print("\n" + "="*80)
    print("CUENTAS 54xx (4 dígitos):")
    print("="*80)
    for c in resultados['cuentas_54xx']:
        print(f"  {c.codigo}: {c.denominacion}")
    
    print("\n" + "="*80)
    print("CUENTAS 55xx (4 dígitos):")
    print("="*80)
    for c in resultados['cuentas_55xx']:
        print(f"  {c.codigo}: {c.denominacion}")
    
    print("\n" + "="*80)
    print("CUENTAS 1105xx:")
    print("="*80)
    for c in resultados['cuentas_1105xx']:
        print(f"  {c.codigo}: {c.denominacion}")

