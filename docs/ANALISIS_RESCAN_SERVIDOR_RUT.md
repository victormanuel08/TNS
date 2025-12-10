# 🔍 ANÁLISIS: ¿El Rescan del Servidor tiene que ver con RUT/CIUU?

## 📋 PREGUNTA

**¿El problema del CIUU no encontrado tiene que ver con el rescan del servidor?**

---

## 🔍 ANÁLISIS DEL PROCESO DE RESCAN

### **¿Qué hace el rescan (descubrir empresas)?**

**Endpoint:** `POST /assistant/api/sistema/descubrir_empresas/`

**Proceso:**
```
1. Conecta al servidor Firebird
   ↓
2. Ejecuta: SELECT CODIGO, NOMBRE, NIT, ANOFIS, ARCHIVO FROM EMPRESAS
   ↓
3. Para cada empresa encontrada:
   - Normaliza el NIT
   - Crea/actualiza EmpresaServidor
   - Asocia contraseñas pendientes
   ↓
4. Retorna lista de empresas encontradas
```

**Código:** `manu/apps/sistema_analitico/services/data_manager.py` línea 65-133

---

## ❌ CONCLUSIÓN: NO TIENE NADA QUE VER

### **El rescan NO busca RUT**

**Lo que hace el rescan:**
- ✅ Crea/actualiza `EmpresaServidor` (empresas del servidor)
- ✅ Normaliza NIT para `EmpresaServidor`
- ✅ Asocia contraseñas pendientes

**Lo que NO hace el rescan:**
- ❌ NO busca RUT en la base de datos
- ❌ NO busca CIUU
- ❌ NO crea registros RUT
- ❌ NO consulta Cámara de Comercio

---

## 🔍 FLUJO REAL

### **Rescan del Servidor:**
```
Rescan → Crea EmpresaServidor → Fin
         (NO busca RUT)
```

### **Búsqueda de CIUU (cuando clasificas factura):**
```
Clasificar Factura
   ↓
buscar_rut_por_nit()
   ↓
1. Buscar en RUT (tabla RUT)
2. Buscar en Proveedor (cache)
3. Consultar Cámara de Comercio
```

**Son procesos independientes.**

---

## ✅ VERIFICACIÓN

### **Código del rescan (línea 105-112):**

```python
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

**No hay:**
- ❌ Búsqueda de RUT
- ❌ Búsqueda de CIUU
- ❌ Creación de RUT

---

## 🎯 PROBLEMA REAL

### **El problema NO es del rescan**

**El problema es:**
1. ❌ El RUT tiene `nit_normalizado` incorrecto (con DV)
2. ❌ La búsqueda usa `nit_normalizado` sin DV
3. ❌ No coinciden → No encuentra el RUT

**Solución ya aplicada:**
- ✅ Corregí el método `save()` del RUT
- ✅ Al subir el ZIP, se corregirán automáticamente

---

## 📝 CONCLUSIÓN

### **¿El rescan tiene que ver?**

**NO**, el rescan del servidor:
- Solo crea/actualiza `EmpresaServidor`
- NO busca ni crea RUT
- NO tiene relación con la búsqueda de CIUU

**El problema es:**
- Discrepancia en `nit_normalizado` del RUT (ya corregido)
- Al subir el ZIP, se actualizarán automáticamente

---

**Última actualización**: Diciembre 2025

