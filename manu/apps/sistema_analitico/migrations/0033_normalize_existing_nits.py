# Generated migration to normalize existing NITs and make nit_normalizado required
from django.db import migrations, models
import re


def normalize_nit_and_extract_dv(nit_value):
    """Normaliza NIT y extrae el dígito verificador"""
    if not nit_value:
        return '', None
    
    nit_str = str(nit_value).strip()
    
    # Separar NIT base y DV (si tiene guión)
    if '-' in nit_str:
        parts = nit_str.split('-')
        nit_base = parts[0]
        dv = parts[1] if len(parts) > 1 else None
    else:
        # Si no tiene guión, intentar extraer DV del final
        nit_clean = re.sub(r'\D', '', nit_str)
        if len(nit_clean) == 10:
            nit_base = nit_clean[:-1]
            dv = nit_clean[-1]
        else:
            nit_base = nit_clean
            dv = None
    
    # Normalizar: solo números
    nit_normalizado = re.sub(r'\D', '', nit_base)
    
    return nit_normalizado, dv


def normalize_existing_nits(apps, schema_editor):
    """Normaliza todos los NITs existentes en EmpresaServidor"""
    EmpresaServidor = apps.get_model('sistema_analitico', 'EmpresaServidor')
    
    empresas = list(EmpresaServidor.objects.all().order_by('id'))
    total = len(empresas)
    actualizadas = 0
    duplicados_manejados = 0
    
    # Primero normalizar todos los NITs
    empresas_por_nit = {}  # (nit_normalizado, anio_fiscal) -> [empresas]
    empresas_procesadas_ids = set()
    
    for empresa in empresas:
        if empresa.nit and empresa.nit.strip():
            nit_norm, dv = normalize_nit_and_extract_dv(empresa.nit)
            if not nit_norm:
                # Si no se pudo normalizar, usar el NIT original sin caracteres especiales
                nit_norm = re.sub(r'\D', '', str(empresa.nit))
            
            if nit_norm:
                empresa.nit_normalizado = nit_norm
                empresa.dv = dv
                empresas_procesadas_ids.add(empresa.id)
                
                # Agrupar por (nit_normalizado, anio_fiscal) para detectar duplicados
                key = (nit_norm, empresa.anio_fiscal)
                if key not in empresas_por_nit:
                    empresas_por_nit[key] = []
                empresas_por_nit[key].append(empresa)
    
    # Procesar empresas sin NIT o que no se procesaron
    empresas_sin_nit = [e for e in empresas if e.id not in empresas_procesadas_ids]
    for empresa in empresas_sin_nit:
        # Asignar un NIT temporal basado en el ID para empresas sin NIT
        empresa.nit_normalizado = f"sin_nit_{empresa.id}"
        empresa.dv = None
        empresa.save(update_fields=['nit_normalizado', 'dv'])
        actualizadas += 1
        empresas_procesadas_ids.add(empresa.id)
        print(f'⚠️  Empresa sin NIT: {empresa.nombre} (ID: {empresa.id}) - Asignado NIT temporal')
    
    # Procesar y guardar, manejando duplicados
    for key, empresas_grupo in empresas_por_nit.items():
        if len(empresas_grupo) > 1:
            # Hay duplicados - mantener la primera (más antigua por ID) y marcar las otras
            empresas_grupo.sort(key=lambda e: e.id)
            empresa_principal = empresas_grupo[0]
            
            # Guardar la principal
            empresa_principal.save(update_fields=['nit_normalizado', 'dv'])
            actualizadas += 1
            
            # Para las duplicadas, agregar sufijo al nit_normalizado para evitar violación de unique
            for i, empresa_dup in enumerate(empresas_grupo[1:], 1):
                # Agregar sufijo temporal para que pase la migración
                empresa_dup.nit_normalizado = f"{key[0]}_dup{i}"
                empresa_dup.save(update_fields=['nit_normalizado', 'dv'])
                actualizadas += 1
                duplicados_manejados += 1
                print(f'⚠️  Duplicado detectado: {empresa_dup.nombre} (ID: {empresa_dup.id}) - NIT: {key[0]}, Año: {key[1]}')
        else:
            # No hay duplicados, guardar normalmente
            empresa = empresas_grupo[0]
            empresa.save(update_fields=['nit_normalizado', 'dv'])
            actualizadas += 1
    
    print(f'✅ Normalizadas {actualizadas} de {total} empresas')
    if duplicados_manejados > 0:
        print(f'⚠️  {duplicados_manejados} empresas duplicadas detectadas y marcadas (requieren revisión manual)')


def reverse_normalize_nits(apps, schema_editor):
    """No hay reversión necesaria - los campos se mantienen"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('sistema_analitico', '0032_add_nit_normalizado_dv_to_empresa_servidor'),
    ]

    operations = [
        migrations.RunPython(normalize_existing_nits, reverse_normalize_nits),
        # Hacer nit_normalizado requerido después de normalizar los datos
        migrations.AlterField(
            model_name='empresaservidor',
            name='nit_normalizado',
            field=models.CharField(
                db_index=True,
                help_text='NIT normalizado sin puntos ni guiones (ej: 9008697500) - usado para búsquedas',
                max_length=20
            ),
        ),
    ]

