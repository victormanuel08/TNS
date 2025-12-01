#!/bin/bash
# Script para obtener información de WireGuard de forma segura (solo lectura)
# Ejecutar en el servidor Ubuntu: bash get_wireguard_info.sh

echo "=========================================="
echo "Información de WireGuard (Solo Lectura)"
echo "=========================================="
echo ""

echo "1. Interfaz WireGuard activa:"
echo "----------------------------------------"
sudo wg show
echo ""

echo "2. Nombre de la interfaz:"
echo "----------------------------------------"
ip link show | grep wg | awk '{print $2}' | sed 's/://'
echo ""

echo "3. Configuración del servidor:"
echo "----------------------------------------"
INTERFACE=$(ip link show | grep wg | awk '{print $2}' | sed 's/://' | head -1)
if [ -n "$INTERFACE" ]; then
    echo "Interfaz encontrada: $INTERFACE"
    sudo cat /etc/wireguard/$INTERFACE.conf 2>/dev/null || echo "Archivo no encontrado"
else
    echo "No se encontró interfaz WireGuard"
fi
echo ""

echo "4. IP Pública del servidor:"
echo "----------------------------------------"
PUBLIC_IP=$(curl -s -4 ifconfig.me || curl -s -4 icanhazip.com)
echo "IP Pública: $PUBLIC_IP"
echo ""

echo "5. IP Local del servidor:"
echo "----------------------------------------"
hostname -I | awk '{print $1}'
echo ""

echo "6. Usuario actual:"
echo "----------------------------------------"
whoami
echo ""

echo "7. Verificar permisos sudo:"
echo "----------------------------------------"
if sudo -n true 2>/dev/null; then
    echo "✓ Sudo sin password configurado"
else
    echo "⚠ Necesitas password para sudo"
fi
echo ""

echo "8. Puerto y Endpoint:"
echo "----------------------------------------"
if [ -n "$INTERFACE" ]; then
    LISTEN_PORT=$(sudo grep -i "ListenPort" /etc/wireguard/$INTERFACE.conf 2>/dev/null | awk '{print $3}')
    SERVER_IP=$(sudo wg show $INTERFACE 2>/dev/null | grep "listening on" | awk '{print $3}' | cut -d: -f2)
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP=$(sudo grep -i "Address" /etc/wireguard/$INTERFACE.conf 2>/dev/null | awk '{print $3}' | cut -d/ -f1)
    fi
    echo "Puerto: ${LISTEN_PORT:-51820}"
    echo "IP VPN del servidor: ${SERVER_IP:-10.8.0.1}"
    echo "Endpoint sugerido: $PUBLIC_IP:${LISTEN_PORT:-51820}"
fi
echo ""

echo "=========================================="
echo "Resumen para .env:"
echo "=========================================="
echo "WG_SERVER_HOST=$PUBLIC_IP"
echo "WG_SERVER_USER=$(whoami)"
echo "WG_SERVER_SSH_PORT=22"
echo "WG_INTERFACE=${INTERFACE:-wg0}"
echo "WG_SERVER_IP=${SERVER_IP:-10.8.0.1}"
echo "WG_SERVER_PORT=${LISTEN_PORT:-51820}"
echo "WG_SERVER_ENDPOINT=$PUBLIC_IP:${LISTEN_PORT:-51820}"
echo ""

