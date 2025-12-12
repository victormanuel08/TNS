"""
Script para validar las cuentas mencionadas en el prompt vs el modelo PUC cargado.
Compara lo que el prompt dice que es cada cuenta vs lo que el PUC realmente dice.
"""
import re
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.sistema_analitico.models import CuentaPUC
from apps.sistema_analitico.services.clasificador_contable_service import PROMPTS


def extraer_cuentas_del_prompt():
    """
    Extrae todas las cuentas mencionadas en el prompt con su contexto/descripción.
    Retorna diccionario: {codigo: {'descripcion_prompt': ..., 'contexto': ...}}
    """
    cuentas = {}
    
    system_prompt = PROMPTS["clasificacion_masiva"]["system"]
    
    # Patrones para encontrar cuentas con su descripción
    # Formato: "cuenta → descripción" o "cuenta (descripción)"
    patrones = [
        # Formato: "→ 143501 (Inventario productos terminados)"
        re.compile(r'→\s*(\d{4,6})\s*\(([^)]+)\)', re.IGNORECASE),
        # Formato: "143501 (Inventario productos terminados)"
        re.compile(r'\b(\d{4,6})\s*\(([^)]+)\)', re.IGNORECASE),
        # Formato: "→ 143501 - Inventario"
        re.compile(r'→\s*(\d{4,6})\s*-\s*([^\n]+)', re.IGNORECASE),
        # Formato: "**cuenta** → descripción"
        re.compile(r'\*\*(\d{4,6})\*\*\s*→\s*([^\n]+)', re.IGNORECASE),
        # Formato: "cuenta: descripción"
        re.compile(r'(\d{4,6}):\s*([^\n]+)', re.IGNORECASE),
    ]
    
    # Buscar todas las menciones de cuentas
    for patron in patrones:
        matches = patron.finditer(system_prompt)
        for match in matches:
            codigo = match.group(1)
            descripcion = match.group(2).strip()
            
            if codigo not in cuentas:
                cuentas[codigo] = {
                    'descripcion_prompt': descripcion,
                    'contexto': '',
                    'menciones': []
                }
            cuentas[codigo]['menciones'].append(descripcion)
    
    # Buscar también cuentas mencionadas en listas o ejemplos
    # Formato: "**Salario integral** → 510503"
    patron_inverso = re.compile(r'\*\*([^*]+)\*\*\s*→\s*(\d{4,6})', re.IGNORECASE)
    matches = patron_inverso.finditer(system_prompt)
    for match in matches:
        descripcion = match.group(1).strip()
        codigo = match.group(2)
        
        if codigo not in cuentas:
            cuentas[codigo] = {
                'descripcion_prompt': descripcion,
                'contexto': '',
                'menciones': []
            }
        cuentas[codigo]['menciones'].append(descripcion)
    
    # Buscar cuentas en rangos mencionados
    # Formato: "1435 (rango 143501-143598)"
    patron_rango = re.compile(r'(\d{4})\s*\(rango\s+(\d{6})\s*-\s*(\d{6})\)', re.IGNORECASE)
    matches = patron_rango.finditer(system_prompt)
    for match in matches:
        cuenta_base = match.group(1)
        inicio = match.group(2)
        fin = match.group(3)
        
        # Agregar cuenta base
        if cuenta_base not in cuentas:
            cuentas[cuenta_base] = {
                'descripcion_prompt': f'Cuenta base (rango {inicio}-{fin})',
                'contexto': 'Rango',
                'menciones': []
            }
        
        # Agregar inicio y fin del rango
        for codigo in [inicio, fin]:
            if codigo not in cuentas:
                cuentas[codigo] = {
                    'descripcion_prompt': f'Límite de rango ({cuenta_base})',
                    'contexto': 'Rango',
                    'menciones': []
                }
    
    # Buscar cuentas mencionadas en secciones específicas
    secciones = [
        ('INVENTARIO', r'(\d{4,6})\s*\([^)]*[Ii]nventario[^)]*\)'),
        ('GASTO', r'(\d{4,6})\s*\([^)]*[Gg]asto[^)]*\)'),
        ('SERVICIO', r'(\d{4,6})\s*\([^)]*[Ss]ervicio[^)]*\)'),
        ('ACTIVO', r'(\d{4,6})\s*\([^)]*[Aa]ctivo[^)]*\)'),
        ('IMPUESTO', r'(\d{4,6})\s*\([^)]*[Ii]mpuesto[^)]*\)'),
    ]
    
    for seccion, patron in secciones:
        matches = re.finditer(patron, system_prompt, re.IGNORECASE)
        for match in matches:
            codigo = match.group(1)
            if codigo not in cuentas:
                cuentas[codigo] = {
                    'descripcion_prompt': f'Mencionada en sección {seccion}',
                    'contexto': seccion,
                    'menciones': []
                }
    
    return cuentas


def buscar_cuenta_en_puc(codigo: str) -> dict:
    """
    Busca una cuenta en el modelo PUC y retorna su información.
    """
    try:
        cuenta = CuentaPUC.objects.get(codigo=codigo)
        return {
            'existe': True,
            'denominacion': cuenta.denominacion,
            'nivel': cuenta.nivel,
            'es_rango': cuenta.es_rango,
            'rango_inicio': cuenta.rango_inicio,
            'rango_fin': cuenta.rango_fin,
        }
    except CuentaPUC.DoesNotExist:
        # Verificar si está dentro de un rango
        if len(codigo) == 6:
            rangos = CuentaPUC.objects.filter(
                es_rango=True,
                nivel=6
            ).exclude(rango_inicio__isnull=True).exclude(rango_fin__isnull=True)
            
            for rango in rangos:
                if rango.es_cuenta_valida_en_rango(codigo):
                    return {
                        'existe': True,
                        'denominacion': f'Dentro del rango {rango.rango_inicio}-{rango.rango_fin}',
                        'nivel': 6,
                        'es_rango': False,
                        'rango_inicio': rango.rango_inicio,
                        'rango_fin': rango.rango_fin,
                        'rango_padre': rango.codigo,
                    }
        
        return {
            'existe': False,
            'denominacion': None,
        }


def comparar_cuentas(cuentas_prompt: dict):
    """
    Compara las cuentas del prompt con las del modelo PUC.
    """
    print("=" * 100)
    print("🔍 VALIDACIÓN DE CUENTAS: PROMPT vs MODELO PUC")
    print("=" * 100)
    print()
    
    total_cuentas = len(cuentas_prompt)
    existentes = 0
    no_existentes = 0
    inconsistencias = []
    
    # Ordenar cuentas por código
    cuentas_ordenadas = sorted(cuentas_prompt.items(), key=lambda x: x[0])
    
    print(f"📊 Total de cuentas mencionadas en el prompt: {total_cuentas}")
    print()
    
    for codigo, info_prompt in cuentas_ordenadas:
        info_puc = buscar_cuenta_en_puc(codigo)
        
        if not info_puc['existe']:
            no_existentes += 1
            print(f"❌ {codigo}: NO EXISTE en el modelo PUC")
            print(f"   Prompt dice: {info_prompt['descripcion_prompt']}")
            print()
            inconsistencias.append({
                'codigo': codigo,
                'tipo': 'NO_EXISTE',
                'prompt': info_prompt['descripcion_prompt'],
                'puc': None
            })
        else:
            existentes += 1
            denominacion_puc = info_puc['denominacion']
            descripcion_prompt = info_prompt['descripcion_prompt']
            
            # Comparar descripciones (simple: verificar si hay palabras clave en común)
            palabras_prompt = set(descripcion_prompt.lower().split())
            palabras_puc = set(denominacion_puc.lower().split())
            
            # Eliminar palabras comunes que no aportan
            palabras_comunes = {'de', 'la', 'el', 'y', 'o', 'a', 'en', 'por', 'para', 'con', 'sin', 'los', 'las', 'un', 'una', 'del', 'al'}
            palabras_prompt = palabras_prompt - palabras_comunes
            palabras_puc = palabras_puc - palabras_comunes
            
            # Calcular similitud (palabras en común)
            palabras_comunes_encontradas = palabras_prompt & palabras_puc
            similitud = len(palabras_comunes_encontradas) / max(len(palabras_prompt), len(palabras_puc), 1) * 100
            
            if similitud < 30:  # Menos del 30% de similitud = posible inconsistencia
                print(f"⚠️  {codigo}: POSIBLE INCONSISTENCIA")
                print(f"   Prompt dice: {descripcion_prompt}")
                print(f"   PUC dice: {denominacion_puc}")
                print(f"   Similitud: {similitud:.1f}%")
                if info_puc.get('es_rango'):
                    print(f"   ⚠️  Es parte de un rango: {info_puc.get('rango_inicio')} - {info_puc.get('rango_fin')}")
                print()
                inconsistencias.append({
                    'codigo': codigo,
                    'tipo': 'INCONSISTENCIA_DESCRIPCION',
                    'prompt': descripcion_prompt,
                    'puc': denominacion_puc,
                    'similitud': similitud
                })
            else:
                # Mostrar solo si es rango o tiene información especial
                if info_puc.get('es_rango') or info_puc.get('rango_padre'):
                    print(f"✅ {codigo}: EXISTE")
                    print(f"   Prompt: {descripcion_prompt}")
                    print(f"   PUC: {denominacion_puc}")
                    if info_puc.get('es_rango'):
                        print(f"   📋 Es rango: {info_puc.get('rango_inicio')} - {info_puc.get('rango_fin')}")
                    elif info_puc.get('rango_padre'):
                        print(f"   📋 Dentro del rango: {info_puc.get('rango_inicio')} - {info_puc.get('rango_fin')}")
                    print()
    
    print("=" * 100)
    print("📊 RESUMEN")
    print("=" * 100)
    print(f"   Total cuentas en prompt: {total_cuentas}")
    print(f"   ✅ Existentes en PUC: {existentes}")
    print(f"   ❌ No existentes: {no_existentes}")
    print(f"   ⚠️  Inconsistencias: {len(inconsistencias)}")
    print()
    
    if inconsistencias:
        print("=" * 100)
        print("⚠️  INCONSISTENCIAS DETECTADAS")
        print("=" * 100)
        for inc in inconsistencias:
            print(f"\n🔴 {inc['codigo']}: {inc['tipo']}")
            print(f"   Prompt: {inc['prompt']}")
            if inc['puc']:
                print(f"   PUC: {inc['puc']}")
                if 'similitud' in inc:
                    print(f"   Similitud: {inc['similitud']:.1f}%")
    
    return {
        'total': total_cuentas,
        'existentes': existentes,
        'no_existentes': no_existentes,
        'inconsistencias': inconsistencias
    }


if __name__ == '__main__':
    print("🔍 Extrayendo cuentas del prompt...")
    cuentas_prompt = extraer_cuentas_del_prompt()
    
    print(f"✅ Extraídas {len(cuentas_prompt)} cuentas del prompt")
    print()
    
    # Verificar que el modelo PUC tenga datos
    total_puc = CuentaPUC.objects.count()
    if total_puc == 0:
        print("⚠️  ADVERTENCIA: El modelo PUC está vacío.")
        print("   Ejecuta primero: python manage.py cargar_puc_desde_pdf")
        sys.exit(1)
    
    print(f"📊 Total de cuentas en modelo PUC: {total_puc}")
    print()
    
    # Comparar
    resultado = comparar_cuentas(cuentas_prompt)
    
    print()
    print("=" * 100)
    print("✅ VALIDACIÓN COMPLETADA")
    print("=" * 100)

