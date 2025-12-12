"""
Script para obtener información detallada de las cuentas PUC mencionadas en el prompt.
"""
import os
import sys
import django
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.sistema_analitico.models import CuentaPUC

def obtener_info_cuentas():
    """Obtiene información detallada de las cuentas problemáticas."""
    
    info = {}
    
    # Cuentas específicas mencionadas en el prompt
    cuentas_a_buscar = {
        '5205': 'Servicios públicos',
        '530505': 'Honorarios directores',
        '530510': 'Auditores',
        '530515': 'Abogados',
        '530520': 'Contadores',
        '530525': 'Otros honorarios',
        '6135': 'Costo de ventas',
        '110510': 'Anticipos',
        '110515': 'Cheques por cobrar',
        '5420': 'Arrendamientos',
        '5425': 'Seguros',
        '5475': 'Vigilancia',
        '5480': 'Aseo',
        '5505': 'Publicidad',
    }
    
    for codigo, desc_prompt in cuentas_a_buscar.items():
        try:
            cuenta = CuentaPUC.objects.get(codigo=codigo)
            info[codigo] = {
                'existe': True,
                'denominacion_puc': cuenta.denominacion,
                'nivel': cuenta.nivel,
                'descripcion_prompt': desc_prompt,
            }
        except CuentaPUC.DoesNotExist:
            info[codigo] = {
                'existe': False,
                'denominacion_puc': None,
                'descripcion_prompt': desc_prompt,
            }
    
    # Buscar alternativas para las cuentas que no existen
    # Servicios públicos
    servicios_publicos = list(CuentaPUC.objects.filter(
        denominacion__icontains='servicio'
    ).exclude(denominacion__icontains='personal').exclude(denominacion__icontains='honorario')[:5])
    info['alternativas_servicios_publicos'] = [{'codigo': c.codigo, 'denominacion': c.denominacion} for c in servicios_publicos]
    
    # Honorarios
    honorarios = list(CuentaPUC.objects.filter(denominacion__icontains='honorario')[:10])
    info['alternativas_honorarios'] = [{'codigo': c.codigo, 'denominacion': c.denominacion} for c in honorarios]
    
    # Arrendamientos
    arrendamientos = list(CuentaPUC.objects.filter(denominacion__icontains='arrendamiento')[:5])
    info['alternativas_arrendamientos'] = [{'codigo': c.codigo, 'denominacion': c.denominacion} for c in arrendamientos]
    
    # Seguros
    seguros = list(CuentaPUC.objects.filter(denominacion__icontains='seguro').exclude(denominacion__icontains='autoseguro')[:5])
    info['alternativas_seguros'] = [{'codigo': c.codigo, 'denominacion': c.denominacion} for c in seguros]
    
    # Vigilancia
    vigilancia = list(CuentaPUC.objects.filter(denominacion__icontains='vigilancia')[:5])
    info['alternativas_vigilancia'] = [{'codigo': c.codigo, 'denominacion': c.denominacion} for c in vigilancia]
    
    # Aseo
    aseo = list(CuentaPUC.objects.filter(denominacion__icontains='aseo')[:5])
    info['alternativas_aseo'] = [{'codigo': c.codigo, 'denominacion': c.denominacion} for c in aseo]
    
    # Publicidad
    publicidad = list(CuentaPUC.objects.filter(denominacion__icontains='publicidad')[:5])
    info['alternativas_publicidad'] = [{'codigo': c.codigo, 'denominacion': c.denominacion} for c in publicidad]
    
    # Costo de ventas
    costo_ventas = list(CuentaPUC.objects.filter(codigo__startswith='61', nivel__in=[1, 2, 4])[:5])
    info['alternativas_costo_ventas'] = [{'codigo': c.codigo, 'denominacion': c.denominacion} for c in costo_ventas]
    
    # Cuentas 5235xx (servicios)
    servicios_5235 = list(CuentaPUC.objects.filter(codigo__startswith='5235', nivel=6)[:10])
    info['cuentas_5235xx'] = [{'codigo': c.codigo, 'denominacion': c.denominacion} for c in servicios_5235]
    
    # Cuentas 5210xx (honorarios)
    honorarios_5210 = list(CuentaPUC.objects.filter(codigo__startswith='5210', nivel=6)[:10])
    info['cuentas_5210xx'] = [{'codigo': c.codigo, 'denominacion': c.denominacion} for c in honorarios_5210]
    
    # Cuentas 5110xx (honorarios)
    honorarios_5110 = list(CuentaPUC.objects.filter(codigo__startswith='5110', nivel=6)[:10])
    info['cuentas_5110xx'] = [{'codigo': c.codigo, 'denominacion': c.denominacion} for c in honorarios_5110]
    
    return info

if __name__ == '__main__':
    print("🔍 Obteniendo información detallada de cuentas PUC...")
    info = obtener_info_cuentas()
    
    print("\n" + "="*80)
    print("INFORMACIÓN DE CUENTAS MENCIONADAS EN EL PROMPT:")
    print("="*80)
    
    for codigo, datos in sorted(info.items()):
        if codigo.startswith('alternativas_') or codigo.startswith('cuentas_'):
            continue
        
        print(f"\n{codigo}:")
        print(f"  Prompt dice: {datos['descripcion_prompt']}")
        if datos['existe']:
            print(f"  PUC dice: {datos['denominacion_puc']} (nivel: {datos['nivel']})")
        else:
            print(f"  ❌ NO EXISTE en el PUC")
    
    print("\n" + "="*80)
    print("ALTERNATIVAS ENCONTRADAS:")
    print("="*80)
    
    for key, value in info.items():
        if key.startswith('alternativas_') or key.startswith('cuentas_'):
            print(f"\n{key}:")
            for item in value:
                print(f"  {item['codigo']}: {item['denominacion']}")
    
    # Guardar en JSON para uso posterior
    with open('manu/scripts/info_cuentas_puc.json', 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=2, default=str)
    
    print("\n✅ Información guardada en manu/scripts/info_cuentas_puc.json")

