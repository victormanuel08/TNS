# 🔍 ANÁLISIS: Discrepancia en Normalización de NIT

## 📋 DATOS DEL PROBLEMA

**RUT en la BD:**
- NIT: `10050386382-7`
- NIT Normalizado (según UI): `10050386382`
- CIUU Principal: `5611` (Expendio a la mesa de comidas preparadas) ✅

**Factura:**
- NIT Empresa: `1005038638`
- Búsqueda del sistema: `nit_normalizado = '1005038638'`
- Resultado: ❌ No encontrado

---

## 🔍 ANÁLISIS DEL PROBLEMA

### **Discrepancia en Normalización:**

**RUT en BD:**
```
NIT original: "10050386382-7"
NIT normalizado guardado: "10050386382" (incluye el "2" del DV)
```

**Búsqueda del sistema:**
```
NIT factura: "1005038638"
Normalización: "1005038638" (sin el "2")
Búsqueda: RUT.objects.filter(nit_normalizado='1005038638')
Resultado: No encontrado ❌
```

---

## 🐛 CAUSA RAÍZ

### **Problema en el método `save()` del modelo RUT**

**Código actual (línea 665):**
```python
def save(self, *args, **kwargs):
    if self.nit:
        # ❌ PROBLEMA: Incluye TODOS los dígitos, incluso el DV
        self.nit_normalizado = ''.join(c for c in str(self.nit) if c.isdigit())
```

**Ejemplo:**
- Si `self.nit = "10050386382-7"`
- `nit_normalizado = "100503863827"` (incluye el 2 y el 7 del DV)

**Pero el sistema busca con:**
```python
# En buscar_rut_por_nit (línea 542)
nit_normalizado, _, _ = normalize_nit_and_extract_dv(nit)
# Si nit = "1005038638"
# nit_normalizado = "1005038638" (sin DV)
```

**Resultado:** No coincide ❌

---

## ✅ SOLUCIÓN

### **Opción 1: Corregir el método `save()` del RUT (Recomendado)**

**Cambiar línea 665 en `models.py`:**
```python
def save(self, *args, **kwargs):
    if self.nit:
        # ✅ CORRECCIÓN: Usar normalize_nit_and_extract_dv para ser consistente
        nit_norm, dv, _ = normalize_nit_and_extract_dv(self.nit)
        self.nit_normalizado = nit_norm
        if dv and not self.dv:
            self.dv = dv
```

**Ventajas:**
- ✅ Consistente con el resto del sistema
- ✅ El `nit_normalizado` será siempre sin DV
- ✅ El DV se guarda en el campo `dv` separado

**Desventajas:**
- ⚠️ Requiere migración de datos existentes
- ⚠️ Los RUTs ya guardados tendrían `nit_normalizado` incorrecto

### **Opción 2: Corregir datos existentes (Inmediato)**

**Script de migración:**
```python
from apps.sistema_analitico.models import RUT, normalize_nit_and_extract_dv

# Corregir todos los RUTs
for rut in RUT.objects.all():
    nit_norm, dv, _ = normalize_nit_and_extract_dv(rut.nit)
    if rut.nit_normalizado != nit_norm:
        print(f"Corrigiendo: {rut.nit} -> {rut.nit_normalizado} -> {nit_norm}")
        rut.nit_normalizado = nit_norm
        if dv:
            rut.dv = dv
        rut.save()
```

### **Opción 3: Búsqueda flexible (Temporal)**

**Modificar `buscar_rut_por_nit` para buscar con y sin DV:**
```python
def buscar_rut_por_nit(self, nit: str) -> Optional[Dict[str, Any]]:
    nit_normalizado, _, _ = normalize_nit_and_extract_dv(nit)
    
    # Buscar exacto
    rut = RUT.objects.filter(nit_normalizado=nit_normalizado).first()
    
    # Si no encuentra, buscar con variaciones (con/sin DV)
    if not rut:
        # Intentar con posibles DVs (0-9)
        for dv in range(10):
            nit_con_dv = f"{nit_normalizado}{dv}"
            rut = RUT.objects.filter(nit_normalizado=nit_con_dv).first()
            if rut:
                break
    
    # ... resto del código
```

**Ventajas:**
- ✅ Funciona inmediatamente
- ✅ No requiere migración

**Desventajas:**
- ⚠️ Solución temporal
- ⚠️ Puede tener falsos positivos

---

## 🔍 VERIFICACIÓN

### **Verificar el RUT actual en la BD:**

```python
from apps.sistema_analitico.models import RUT

rut = RUT.objects.filter(nit__icontains='1005038638').first()
if rut:
    print(f"NIT: {rut.nit}")
    print(f"NIT Normalizado: {rut.nit_normalizado}")
    print(f"DV: {rut.dv}")
    print(f"CIUU: {rut.actividad_principal_ciiu}")
```

### **Verificar normalización:**

```python
from apps.sistema_analitico.models import normalize_nit_and_extract_dv

# NIT de la factura
nit_factura = "1005038638"
nit_norm, dv, _ = normalize_nit_and_extract_dv(nit_factura)
print(f"Normalizado: {nit_norm}")  # Debería ser "1005038638"

# NIT del RUT
nit_rut = "10050386382-7"
nit_norm_rut, dv_rut, _ = normalize_nit_and_extract_dv(nit_rut)
print(f"Normalizado RUT: {nit_norm_rut}")  # Debería ser "1005038638"
print(f"DV: {dv_rut}")  # Debería ser "7"
```

---

## 📝 CONCLUSIÓN

### **Problema identificado:**

1. ❌ El RUT se guarda con `nit_normalizado` que **incluye el DV**
2. ❌ El sistema busca con `nit_normalizado` que **excluye el DV**
3. ❌ No coinciden → No encuentra el RUT

### **Solución recomendada:**

1. ✅ **Corregir el método `save()` del RUT** para usar `normalize_nit_and_extract_dv()`
2. ✅ **Migrar datos existentes** para corregir `nit_normalizado` en RUTs ya guardados
3. ✅ **Verificar** que la búsqueda funcione correctamente

### **Solución temporal:**

- Usar búsqueda flexible que intente con y sin DV
- O corregir manualmente el `nit_normalizado` del RUT específico

---

**Última actualización**: Diciembre 2025

