#!/bin/bash
# Script para verificar y configurar Firebird 2.5

echo "🔍 Verificando estructura de Firebird 2.5..."
echo ""

# Verificar si existe el directorio
if [ -d "/opt/firebird2.5" ]; then
    echo "✅ Directorio /opt/firebird2.5 existe"
    echo ""
    echo "📁 Estructura del directorio:"
    ls -la /opt/firebird2.5/
    echo ""
    echo "🔍 Buscando gbak en todo el directorio:"
    find /opt/firebird2.5 -name "gbak" -type f 2>/dev/null
    echo ""
    echo "📂 Contenido de posibles subdirectorios:"
    if [ -d "/opt/firebird2.5/bin" ]; then
        echo "  /opt/firebird2.5/bin:"
        ls -la /opt/firebird2.5/bin/
    fi
    if [ -d "/opt/firebird2.5/FirebirdSS-2.5.9.27139-0.amd64" ]; then
        echo "  /opt/firebird2.5/FirebirdSS-2.5.9.27139-0.amd64:"
        ls -la /opt/firebird2.5/FirebirdSS-2.5.9.27139-0.amd64/
        if [ -d "/opt/firebird2.5/FirebirdSS-2.5.9.27139-0.amd64/bin" ]; then
            echo "    /opt/firebird2.5/FirebirdSS-2.5.9.27139-0.amd64/bin:"
            ls -la /opt/firebird2.5/FirebirdSS-2.5.9.27139-0.amd64/bin/
        fi
    fi
else
    echo "❌ Directorio /opt/firebird2.5 no existe"
fi

