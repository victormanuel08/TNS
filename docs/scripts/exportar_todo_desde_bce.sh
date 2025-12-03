#!/bin/bash
# Script para exportar todos los datos de BCE a Excel
# Uso: ./exportar_todo_desde_bce.sh

set -e  # Salir si hay error

echo "🚀 Iniciando exportación completa de BCE a MANU..."
echo ""

# Configuración
BCE_DIR="/home/victus/projects/CORE/bce/backend"
EXPORTS_DIR="$BCE_DIR/exports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Crear directorio de exports si no existe
mkdir -p "$EXPORTS_DIR"

echo "📂 Directorio de exports: $EXPORTS_DIR"
echo ""

# Activar entorno virtual si existe
if [ -d "$BCE_DIR/env" ]; then
    echo "🔧 Activando entorno virtual..."
    source "$BCE_DIR/env/bin/activate"
fi

cd "$BCE_DIR"

# 1. Exportar Entities y PasswordsEntities
echo "📋 1/3 Exportando Entities y PasswordsEntities..."
python manage.py exportar_entidades_para_manu --output-dir "$EXPORTS_DIR"
ENTIDADES_FILE=$(ls -t "$EXPORTS_DIR"/entidades_para_manu_*.xlsx | head -1)
echo "   ✅ Archivo: $(basename $ENTIDADES_FILE)"
echo ""

# 2. Exportar Calendario Tributario
echo "📅 2/3 Exportando Calendario Tributario..."
python manage.py exportar_calendario_editable --output-dir "$EXPORTS_DIR"
CALENDARIO_FILE=$(ls -t "$EXPORTS_DIR"/calendario_tributario_editable_*.xlsx | head -1)
echo "   ✅ Archivo: $(basename $CALENDARIO_FILE)"
echo ""

# 3. (Opcional) Exportar datos de referencia
echo "📊 3/3 Exportando datos de referencia (Third_Types, Regiments_Types, Tax, Responsabilitys_Types)..."
python manage.py exportar_datos_para_manu --format excel --output-dir "$EXPORTS_DIR"
REFERENCIA_FILE=$(ls -t "$EXPORTS_DIR"/export_bce_para_manu_*.xlsx | head -1)
echo "   ✅ Archivo: $(basename $REFERENCIA_FILE)"
echo ""

echo "✅ Exportación completada!"
echo ""
echo "📦 Archivos generados:"
echo "   1. $(basename $ENTIDADES_FILE)"
echo "   2. $(basename $CALENDARIO_FILE)"
echo "   3. $(basename $REFERENCIA_FILE)"
echo ""
echo "💡 Próximos pasos:"
echo "   1. Descarga los archivos desde: $EXPORTS_DIR"
echo "   2. En MANU, ejecuta:"
echo "      python manage.py importar_entidades_desde_excel <ruta_al_archivo_entidades>"
echo "   3. Sube el calendario desde el admin frontend en la sección 'Calendario Tributario'"
echo ""

