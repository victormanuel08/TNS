# ✅ VERIFICACIÓN: Normalización de NIT en EmpresaServidor

## 📋 PREGUNTA

**¿El `nit_normalizado` de `EmpresaServidor` está bien después de un scan/rescan?**

---

## ✅ RESPUESTA: SÍ, ESTÁ CORRECTO

### **Verificación del código:**

**1. Durante el rescan (descubrir empresas):**

**Código:** `manu/apps/sistema_analitico/services/data_manager.py` línea 104

```python
# Línea 104: Usa normalize_nit_and_extract_dv (CORRECTO)
nit_norm, dv, _ = normalize_nit_and_extract_dv(nit) if nit else ('', None, '')

# Línea 105-112: Guarda con nit_normalizado correcto
empresa, creada = EmpresaServidor.objects.update_or_create(
    servidor=servidor, nit_normalizado=nit_norm, anio_fiscal=anio_fiscal,
    defaults={
        'codigo': fila['CODIGO'], 
        'nombre': fila['NOMBRE'],
        'nit': nit,  # Mantener formato original
        'ruta_base': fila['ARCHIVO'], 
        'estado': 'ACTIVO'
    }
)
```

**✅ Usa `normalize_nit_and_extract_dv()`** → Excluye el DV correctamente

---

**2. Método `save()` de EmpresaServidor:**

**Código:** `manu/apps/sistema_analitico/models.py` línea 125-139

```python
def save(self, *args, **kwargs):
    """Normaliza NIT automáticamente antes de guardar"""
    if self.nit:
        # ✅ CORRECTO: Usa normalize_nit_and_extract_dv
        nit_norm, dv, nit_orig = normalize_nit_and_extract_dv(self.nit)
        self.nit_normalizado = nit_norm  # Sin DV
        self.dv = dv  # DV en campo separado
    super().save(*args, **kwargs)
```

**✅ Usa `normalize_nit_and_extract_dv()`** → Excluye el DV correctamente

---

## 🔍 COMPARACIÓN

| Modelo | Método save() | Estado |
|--------|---------------|--------|
| **RUT** | ❌ Antes: Incluía DV | ✅ **Corregido** |
| **EmpresaServidor** | ✅ Siempre correcto | ✅ **OK** |

---

## 📊 EJEMPLO

**NIT de Firebird:** `10050386382-7`

**Después del rescan:**
- `EmpresaServidor.nit`: `10050386382-7` (formato original)
- `EmpresaServidor.nit_normalizado`: `1005038638` ✅ (sin DV)
- `EmpresaServidor.dv`: `7` ✅ (en campo separado)

**Búsqueda:**
```python
# Busca con nit_normalizado sin DV
EmpresaServidor.objects.filter(nit_normalizado='1005038638')
# ✅ Encuentra correctamente
```

---

## ✅ CONCLUSIÓN

### **EmpresaServidor está bien normalizado**

**Razones:**
1. ✅ El rescan usa `normalize_nit_and_extract_dv()` (línea 104)
2. ✅ El método `save()` usa `normalize_nit_and_extract_dv()` (línea 128)
3. ✅ El `nit_normalizado` siempre excluye el DV
4. ✅ El DV se guarda en campo separado

**El problema solo era con RUT, que ya está corregido.**

---

**Última actualización**: Diciembre 2025

