# Guía Completa: Migración de BCE a MANU

Esta guía explica cómo migrar todos los datos desde BCE a MANU.

## 📋 Datos a Migrar

1. **Entities y PasswordsEntities** (Entidades y Contraseñas)
2. **Calendario Tributario** (Vigencias Tributarias)
3. **Datos de Referencia** (Third_Types, Regiments_Types, Tax, Responsabilitys_Types)

---

## 🚀 MÉTODO RECOMENDADO: Migración Directa desde Base de Datos

Si MANU tiene acceso a la misma base de datos de BCE (o puede conectarse a ella), puedes migrar directamente sin exportar/importar archivos.

### Paso 1: Configurar Credenciales de BCE en MANU

Edita el archivo `.env` de MANU y agrega:

```bash
# Base de datos de BCE (si está en la misma instancia, usa las mismas credenciales)
BCE_DB_ENGINE=django.db.backends.postgresql
BCE_DB_NAME=bce  # Nombre de la base de datos de BCE
BCE_DB_USER=postgres
BCE_DB_PASSWORD=postgres
BCE_DB_HOST=127.0.0.1
BCE_DB_PORT=5432
```

**Nota:** Si BCE y MANU están en la misma base de datos PostgreSQL, puedes usar las mismas credenciales o incluso la misma base de datos.

### Paso 2: Ejecutar Migración Directa

```bash
cd /ruta/a/manu
source env/bin/activate
python manage.py migrar_desde_bce_directo
```

**Opciones:**
- `--dry-run`: Ver qué se haría sin guardar cambios
- `--solo-entidades`: Migrar solo Entities y PasswordsEntities
- `--solo-calendario`: Migrar solo Calendario Tributario

**Ejemplo:**
```bash
# Ver qué se haría
python manage.py migrar_desde_bce_directo --dry-run

# Migrar solo entidades
python manage.py migrar_desde_bce_directo --solo-entidades

# Migrar todo
python manage.py migrar_desde_bce_directo
```

---

## 📤 MÉTODO ALTERNATIVO: Exportar/Importar desde Excel

Si no puedes acceder directamente a la base de datos de BCE, usa este método.

---

## 🚀 PASO 1: Exportar desde BCE (en el VPS)

### Opción A: Script Automático (Recomendado)

```bash
cd /ruta/a/bce/backend
chmod +x docs/scripts/exportar_todo_desde_bce.sh
./docs/scripts/exportar_todo_desde_bce.sh
```

### Opción B: Comandos Manuales

### 1.1 Conectarse al VPS

```bash
ssh usuario@tu_vps
cd /ruta/a/bce/backend
source env/bin/activate  # O tu entorno virtual
```

### 1.2 Exportar Entities y PasswordsEntities

```bash
python manage.py exportar_entidades_para_manu --output-dir ./exports
```

**Resultado:** Se crea `exports/entidades_para_manu_YYYYMMDD_HHMMSS.xlsx`

### 1.3 Exportar Calendario Tributario

```bash
python manage.py exportar_calendario_editable --output-dir ./exports
```

**Resultado:** Se crea `exports/calendario_tributario_editable_YYYYMMDD_HHMMSS.xlsx`

### 1.4 (Opcional) Exportar datos de referencia del calendario

```bash
python manage.py exportar_datos_para_manu --format excel --output-dir ./exports
```

**Resultado:** Se crea `exports/export_bce_para_manu_YYYYMMDD_HHMMSS.xlsx` con:
- Third_Types
- Regiments_Types
- Tax
- Responsabilitys_Types

---

## 📥 PASO 2: Descargar Archivos del VPS

### Opción A: Usando SCP

```bash
# Desde tu máquina local
scp usuario@vps:/ruta/a/bce/backend/exports/entidades_para_manu_*.xlsx ./
scp usuario@vps:/ruta/a/bce/backend/exports/calendario_tributario_editable_*.xlsx ./
```

### Opción B: Usando SFTP o cliente FTP

Conecta al VPS y descarga los archivos desde `bce/backend/exports/`

---

## 📤 PASO 3: Importar en MANU (Local)

### 3.1 Importar Entities y PasswordsEntities

```bash
cd /ruta/a/manu
source env/bin/activate  # O tu entorno virtual
python manage.py importar_entidades_desde_excel ../bce/backend/exports/entidades_para_manu_YYYYMMDD_HHMMSS.xlsx
```

**Resultado:**
- ✅ Se crean/actualizan todas las Entities
- ✅ Se crean todas las PasswordsEntities
- ✅ Las contraseñas con NIT se guardan (se asociarán automáticamente cuando se descubra la empresa)

### 3.2 Importar Calendario Tributario

**Opción A: Desde el Admin Frontend (Recomendado)**

1. Abre el admin frontend de MANU
2. Ve a la sección "Calendario Tributario"
3. Haz clic en "Subir Calendario"
4. Selecciona el archivo `calendario_tributario_editable_YYYYMMDD_HHMMSS.xlsx`
5. Haz clic en "Subir"

**Opción B: Desde la API**

```bash
curl -X POST http://localhost:8000/api/calendario-tributario/subir-excel/ \
  -H "Authorization: Bearer TU_TOKEN" \
  -F "archivo_excel=@calendario_tributario_editable_YYYYMMDD_HHMMSS.xlsx"
```

**Opción C: Script Automático**

```bash
cd /ruta/a/manu
chmod +x docs/scripts/importar_todo_en_manu.sh
./docs/scripts/importar_todo_en_manu.sh ../bce/backend/exports/entidades_para_manu_YYYYMMDD_HHMMSS.xlsx ../bce/backend/exports/calendario_tributario_editable_YYYYMMDD_HHMMSS.xlsx
```

---

## ✅ Verificación

### Verificar Entities y Contraseñas

```bash
python manage.py shell
```

```python
from apps.sistema_analitico.models import Entidad, ContrasenaEntidad

print(f"Total Entidades: {Entidad.objects.count()}")
print(f"Total Contraseñas: {ContrasenaEntidad.objects.count()}")
print(f"Contraseñas con empresa: {ContrasenaEntidad.objects.filter(empresa_servidor__isnull=False).count()}")
print(f"Contraseñas sin empresa: {ContrasenaEntidad.objects.filter(empresa_servidor__isnull=True).count()}")
```

### Verificar Calendario Tributario

```python
from apps.sistema_analitico.models import VigenciaTributaria

print(f"Total Vigencias: {VigenciaTributaria.objects.count()}")
```

---

## 🔄 Asociación Automática de Contraseñas

Cuando ejecutes el escaneo de empresas en un servidor:

```bash
# Desde el admin frontend o API
POST /api/servidores/{servidor_id}/descubrir-empresas/
```

Las contraseñas pendientes se asociarán automáticamente a las empresas descubiertas.

---

## 📝 Resumen de Comandos

### En BCE (VPS) - Script Automático:
```bash
cd /ruta/a/bce/backend
./docs/scripts/exportar_todo_desde_bce.sh
```

### En BCE (VPS) - Comandos Manuales:
```bash
cd /ruta/a/bce/backend
source env/bin/activate
python manage.py exportar_entidades_para_manu --output-dir ./exports
python manage.py exportar_calendario_editable --output-dir ./exports
python manage.py exportar_datos_para_manu --format excel --output-dir ./exports  # Opcional
```

### En MANU (Local) - Script Automático:
```bash
cd /ruta/a/manu
./docs/scripts/importar_todo_en_manu.sh ../bce/backend/exports/entidades_para_manu_YYYYMMDD_HHMMSS.xlsx ../bce/backend/exports/calendario_tributario_editable_YYYYMMDD_HHMMSS.xlsx
```

### En MANU (Local) - Comandos Manuales:
```bash
cd /ruta/a/manu
source env/bin/activate
python manage.py importar_entidades_desde_excel ../bce/backend/exports/entidades_para_manu_YYYYMMDD_HHMMSS.xlsx
# Calendario desde admin frontend en la sección "Calendario Tributario"
```

---

## ⚠️ Notas Importantes

1. **No se crean empresas automáticamente** - Las contraseñas se guardan con `nit_normalizado` y se asocian cuando se descubra la empresa en un servidor.

2. **NITs normalizados** - Todo se maneja con NITs normalizados (sin puntos ni guiones).

3. **Calendario Tributario** - Si necesitas modificar fechas, edita el Excel exportado y vuelve a subirlo.

4. **Backup** - Siempre haz backup antes de importar datos masivos.

