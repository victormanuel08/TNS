#!/bin/bash
# Script para importar todos los datos de BCE a MANU
# Uso: ./importar_todo_en_manu.sh <ruta_archivo_entidades> <ruta_archivo_calendario>

set -e  # Salir si hay error

if [ $# -lt 1 ]; then
    echo "❌ Error: Se requiere al menos el archivo de entidades"
    echo "Uso: $0 <ruta_archivo_entidades> [ruta_archivo_calendario]"
    exit 1
fi

ENTIDADES_FILE="$1"
CALENDARIO_FILE="${2:-}"

echo "🚀 Iniciando importación completa de BCE a MANU..."
echo ""

# Configuración
MANU_DIR="/home/victus/projects/CORE/manu"

# Activar entorno virtual si existe
if [ -d "$MANU_DIR/env" ]; then
    echo "🔧 Activando entorno virtual..."
    source "$MANU_DIR/env/bin/activate"
fi

cd "$MANU_DIR"

# 1. Importar Entities y PasswordsEntities
if [ ! -f "$ENTIDADES_FILE" ]; then
    echo "❌ Error: Archivo de entidades no encontrado: $ENTIDADES_FILE"
    exit 1
fi

echo "📋 1/2 Importando Entities y PasswordsEntities..."
echo "   Archivo: $(basename $ENTIDADES_FILE)"
python manage.py importar_entidades_desde_excel "$ENTIDADES_FILE"
echo "   ✅ Importación de entidades completada"
echo ""

# 2. Importar Calendario Tributario (si se proporciona)
if [ -n "$CALENDARIO_FILE" ]; then
    if [ ! -f "$CALENDARIO_FILE" ]; then
        echo "⚠️  Advertencia: Archivo de calendario no encontrado: $CALENDARIO_FILE"
        echo "   Puedes subirlo manualmente desde el admin frontend"
    else
        echo "📅 2/2 Importando Calendario Tributario..."
        echo "   Archivo: $(basename $CALENDARIO_FILE)"
        echo "   💡 Nota: El calendario se debe subir desde el admin frontend"
        echo "   o usando la API: POST /api/calendario-tributario/subir-excel/"
        echo ""
    fi
else
    echo "📅 2/2 Calendario Tributario: No proporcionado"
    echo "   💡 Puedes subirlo manualmente desde el admin frontend"
    echo ""
fi

echo "✅ Importación completada!"
echo ""
echo "💡 Verificación:"
echo "   - Ejecuta el escaneo de empresas en un servidor para asociar contraseñas automáticamente"
echo ""

