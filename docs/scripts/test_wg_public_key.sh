#!/bin/bash
# Script para verificar y obtener la clave pública del servidor WireGuard

echo "🔍 Verificando clave pública del servidor WireGuard"
echo "=================================================="
echo ""

INTERFACE="wg-main"
CONFIG_DIR="/etc/wireguard"

echo "1️⃣ Método 1: Desde archivo public.key"
if [ -f "$CONFIG_DIR/public.key" ]; then
    echo "✅ Archivo existe: $CONFIG_DIR/public.key"
    cat "$CONFIG_DIR/public.key"
else
    echo "❌ Archivo NO existe: $CONFIG_DIR/public.key"
fi
echo ""

echo "2️⃣ Método 2: Desde 'wg show' (interfaz activa)"
if sudo wg show "$INTERFACE" &> /dev/null; then
    echo "✅ Interfaz $INTERFACE está activa"
    sudo wg show "$INTERFACE" | grep -i "public key" || echo "❌ No se encontró 'public key' en la salida"
    echo ""
    echo "Clave pública extraída:"
    sudo wg show "$INTERFACE" | grep -i "public key" | sed 's/.*public key:[[:space:]]*//' | head -1
else
    echo "❌ Interfaz $INTERFACE NO está activa"
fi
echo ""

echo "3️⃣ Método 3: Desde archivo de configuración"
CONFIG_FILE="$CONFIG_DIR/$INTERFACE.conf"
if [ -f "$CONFIG_FILE" ]; then
    echo "✅ Archivo de configuración existe: $CONFIG_FILE"
    echo "Buscando PublicKey en el archivo:"
    grep -i "publickey" "$CONFIG_FILE" | head -1 || echo "❌ No se encontró PublicKey en el archivo"
else
    echo "❌ Archivo de configuración NO existe: $CONFIG_FILE"
fi
echo ""

echo "4️⃣ Método 4: Generar desde clave privada"
PRIVATE_KEY_FILE="$CONFIG_DIR/$INTERFACE.key"
if [ -f "$PRIVATE_KEY_FILE" ]; then
    echo "✅ Archivo de clave privada existe: $PRIVATE_KEY_FILE"
    echo "Generando clave pública desde la privada:"
    cat "$PRIVATE_KEY_FILE" | wg pubkey
else
    echo "❌ Archivo de clave privada NO existe: $PRIVATE_KEY_FILE"
fi
echo ""

echo "=================================================="
echo "📋 Resumen:"
echo ""
echo "La clave pública del servidor debería ser:"
sudo wg show "$INTERFACE" 2>/dev/null | grep -i "public key" | sed 's/.*public key:[[:space:]]*//' | head -1 || echo "No disponible"
echo ""

