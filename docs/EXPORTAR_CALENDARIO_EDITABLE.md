# Exportar Calendario Tributario Editable

## 🎯 Propósito

Este comando exporta **TODOS** los registros del calendario tributario actual en formato Excel, listo para que solo modifiques las **fechas** y lo reimportes.

## 📋 Uso

### Exportar todo el calendario:

```bash
cd bce/backend
python manage.py exportar_calendario_editable --output-dir ../../docs
```

### Exportar solo un año específico:

```bash
python manage.py exportar_calendario_editable --year 2025 --output-dir ../../docs
```

## 📊 Formato del Excel Generado

El Excel contiene:

1. **Hoja INSTRUCCIONES**: Guía rápida de cómo editar
2. **Hoja CALENDARIO_TRIBUTARIO**: Todos los registros con estas columnas:
   - `tax_code`: Código del impuesto (NO MODIFICAR)
   - `expirations_digits`: Últimos dígitos del NIT (NO MODIFICAR)
   - `third_type_code`: Tipo de tercero (NO MODIFICAR)
   - `regiment_type_code`: Régimen tributario (NO MODIFICAR)
   - `date`: **⭐ MODIFICA ESTA COLUMNA** (formato: DD/MM/YYYY)
   - `description`: Descripción (puedes modificar si es necesario)

## ✏️ Cómo Editar

1. **Abre el Excel** generado
2. **Ve a la hoja CALENDARIO_TRIBUTARIO**
3. **Modifica solo la columna `date`** con las nuevas fechas (formato: DD/MM/YYYY)
   - Ejemplo: Cambiar `11/02/2024` por `11/02/2025`
4. **Opcional**: Modifica `description` si es necesario
5. **Guarda el archivo**
6. **Súbelo desde el admin de MANU**

## ⚠️ Importante

- ✅ **SÍ puedes**: Modificar fechas, agregar nuevas filas, eliminar filas
- ❌ **NO modifiques**: Nombres de columnas, formato de tax_code, digits, third_type_code, regiment_type_code
- 📅 **Formato de fecha**: DD/MM/YYYY (ejemplo: `11/02/2025`)

## 🔄 Flujo Completo

1. **Exportar** desde BCE: `exportar_calendario_editable`
2. **Editar** fechas en Excel
3. **Subir** desde admin de MANU
4. **Listo** ✅

