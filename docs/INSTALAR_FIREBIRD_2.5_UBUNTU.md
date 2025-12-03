# Instalación de Firebird 2.5 en Ubuntu (VPS)

## ⚠️ Importante

Las bases de datos son **Firebird 2.5**, por lo que es **recomendable usar gbak 2.5** para evitar problemas de compatibilidad al restaurar backups en servidores Firebird 2.5.

## ⚠️ IMPORTANTE: Firebird 2.5 no está disponible fácilmente en Ubuntu 22.04

Los repositorios PPA y paquetes oficiales de Firebird 2.5 ya no están disponibles para Ubuntu 22.04 (Jammy).

**Opciones disponibles:**

1. **Instalar Firebird 3.0** (funciona para backups, pero puede tener problemas al restaurar en servidores 2.5)
2. **Descargar Firebird 2.5 manualmente desde SourceForge** (más trabajo pero garantiza compatibilidad)

---

## Opción 1: Instalar Firebird 3.0 (Solución Rápida - Temporal)

⚠️ **ADVERTENCIA**: Firebird 3.0 puede hacer backup de bases de datos 2.5, pero al restaurar puede convertir la base de datos al formato 3.0, causando problemas si intentas restaurar en un servidor Firebird 2.5.

```bash
# Instalar Firebird 3.0 (disponible en repositorios)
sudo apt-get update
sudo apt-get install firebird3.0-utils

# Verificar instalación
which gbak
# Debería mostrar: /usr/bin/gbak

gbak -?
# Debería mostrar información de Firebird 3.0
```

**Nota**: El código detectará que es Firebird 3.0 y mostrará una advertencia, pero funcionará para hacer backups.

---

## Opción 2: Instalación Manual de Firebird 2.5 desde SourceForge (Recomendado para Producción)

### Paso 1: Descargar Firebird 2.5

```bash
# Conectarse al VPS
ssh victus@tu_vps

# Crear directorio temporal
cd /tmp

# Opción A: Descargar desde GitHub (más confiable)
wget https://github.com/FirebirdSQL/firebird/releases/download/R2_5_9/FirebirdSS-2.5.9.27139-0.amd64.tar.gz

# Si el nombre del archivo es diferente después de descargar, renombrarlo:
# mv FirebirdSS-2.5.9.27139-0.amd64.tar.gz Firebird-2.5.9.tar.gz

# Opción B: Si GitHub no funciona, descargar manualmente desde:
# https://sourceforge.net/projects/firebird/files/firebird/2.5.9-Release/
# Buscar: "FirebirdSS-2.5.9.27139-0.amd64.tar.gz" o "Firebird-2.5.9.27139-0.amd64.tar.gz"
# Luego subir al servidor con scp desde tu máquina local:
# scp FirebirdSS-2.5.9.27139-0.amd64.tar.gz victus@tu_vps:/tmp/
```

### Paso 2: Extraer e Instalar

```bash
# Verificar qué archivo se descargó
ls -lh /tmp/Firebird*.tar.gz

# Extraer el archivo (el nombre puede variar)
tar -xzf FirebirdSS-2.5.9.27139-0.amd64.tar.gz
# O si el nombre es diferente:
# tar -xzf Firebird-2.5.9.27139-0.amd64.tar.gz

# Ver qué se extrajo
ls -la

# El directorio extraído puede ser "FirebirdSS-2.5.9.27139-0.amd64" o "firebird"
# Mover a ubicación permanente
if [ -d "FirebirdSS-2.5.9.27139-0.amd64" ]; then
    sudo mv FirebirdSS-2.5.9.27139-0.amd64 /opt/firebird2.5
elif [ -d "firebird" ]; then
    sudo mv firebird /opt/firebird2.5
else
    echo "Error: No se encontró el directorio extraído"
    exit 1
fi

# Extraer buildroot.tar.gz que contiene los binarios
cd /opt/firebird2.5
sudo tar -xzf buildroot.tar.gz

# Buscar dónde está gbak (puede estar en estructura anidada)
sudo find /opt/firebird2.5 -name "gbak" -type f

# La ruta típica es: /opt/firebird2.5/opt/firebird/bin/gbak
# O puede ser: /opt/firebird2.5/bin/gbak

# Si ya existe un symlink, removerlo primero
sudo rm -f /usr/local/bin/gbak

# Crear symlink apuntando a la ruta correcta
# Ajusta la ruta según lo que encontró el comando find
sudo ln -s /opt/firebird2.5/opt/firebird/bin/gbak /usr/local/bin/gbak

# Instalar dependencias faltantes (libncurses.so.5)
sudo apt-get update
sudo apt-get install libncurses5

# Verificar instalación
which gbak
# Debería mostrar: /usr/local/bin/gbak

# Probar gbak (puede que -? no funcione, pero el backup sí)
# Probar con un backup real para verificar que funciona
# gbak -b -v -user SYSDBA -password masterkey host:/ruta/base.gdb /tmp/test.fbk
```

### Paso 3: Verificar que el código lo encuentra

El código buscará automáticamente en:
- `/opt/firebird2.5/bin/gbak` ✅
- `/usr/local/bin/gbak` ✅ (si creaste el symlink)
- `/usr/bin/gbak` (Firebird 3.0, si está instalado)

## Limpiar PPA que no funciona (si lo agregaste)

Si agregaste el PPA `ppa:mapopa` y no funciona, removerlo:

```bash
sudo add-apt-repository --remove ppa:mapopa
sudo apt-get update
```

---

⚠️ **ADVERTENCIA**: Firebird 3.0 puede hacer backup de bases de datos 2.5, pero al restaurar puede convertir la base de datos al formato 3.0, causando problemas si intentas restaurar en un servidor Firebird 2.5.

```bash
sudo apt-get update
sudo apt-get install firebird3.0-utils
```

## Opción 4: Configurar Ruta Manual en settings.py

Si instalaste Firebird 2.5 en otra ubicación:

```python
# En manu/config/settings.py
FIREBIRD_GBAK_PATH = "/ruta/completa/a/gbak"  # Ejemplo: /opt/firebird2.5/bin/gbak
```

## Verificación

Después de instalar, verifica que funciona:

```bash
# Verificar que gbak está disponible
which gbak

# Verificar versión
gbak -?

# Probar backup (ejemplo)
gbak -b -v -user SYSDBA -password masterkey \
  10.8.1.1:/ruta/a/base.gdb \
  /tmp/test_backup.fbk
```

## Estructura de Directorios Recomendada

```
/opt/firebird2.5/
├── bin/
│   ├── gbak          ← Herramienta de backup
│   ├── gfix
│   └── ...
├── lib/
└── ...
```

## Notas

- El código buscará automáticamente `gbak` en múltiples ubicaciones
- Si encuentra Firebird 2.5, lo usará preferentemente
- Si solo encuentra Firebird 3.0, mostrará una advertencia pero funcionará
- Para máxima compatibilidad, usa Firebird 2.5

