#!/bin/bash
# Script para crear/actualizar el archivo .env del frontend en producción

set -e

echo "🔧 Configurando variables de entorno del frontend..."

FRONTEND_DIR="/home/victus/projects/CORE/front"

# Verificar que el directorio existe
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Error: No se encontró el directorio $FRONTEND_DIR"
    exit 1
fi

# Crear o actualizar el archivo .env
cat > "$FRONTEND_DIR/.env" <<EOF
# URL del backend Django (API)
# IMPORTANTE: Esta URL debe coincidir con tu dominio de producción
DJANGO_API_URL=https://api.eddeso.com

# Habilitar conexión al backend
ENABLE_BACKEND=true
EOF

echo "✅ Archivo .env creado/actualizado en $FRONTEND_DIR/.env"
echo ""
echo "📋 Contenido del archivo:"
cat "$FRONTEND_DIR/.env"
echo ""
echo "⚠️  IMPORTANTE: Después de crear/actualizar el .env, debes:"
echo "   1. Reconstruir el frontend: cd $FRONTEND_DIR && npm run build"
echo "   2. Reiniciar PM2: pm2 restart Eddeso"
echo ""

