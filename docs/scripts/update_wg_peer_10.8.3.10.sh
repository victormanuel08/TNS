#!/bin/bash
# Script para actualizar el peer 10.8.3.10 en el servidor WireGuard

echo "🔧 Actualización de Peer 10.8.3.10 en WireGuard"
echo "================================================"
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Verificar que estamos como root o con sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}⚠️ Este script requiere permisos de root${NC}"
    echo "Ejecuta con: sudo bash $0"
    exit 1
fi

# Detectar interfaz WireGuard (generalmente wg-main o wg0)
INTERFACE=""
if wg show wg-main > /dev/null 2>&1; then
    INTERFACE="wg-main"
elif wg show wg0 > /dev/null 2>&1; then
    INTERFACE="wg0"
else
    echo -e "${RED}❌ No se encontró interfaz WireGuard activa${NC}"
    echo "Interfaces disponibles:"
    wg show
    read -p "Ingresa el nombre de la interfaz: " INTERFACE
fi

echo -e "${GREEN}✅ Usando interfaz: $INTERFACE${NC}"
echo ""

# Ver configuración actual del peer
echo "1️⃣ Verificando configuración actual del peer 10.8.3.10..."
PEER_INFO=$(wg show $INTERFACE dump | grep "10.8.3.10")
if [ -z "$PEER_INFO" ]; then
    echo -e "${RED}❌ Peer 10.8.3.10 NO está configurado${NC}"
    echo ""
    echo "Necesitas agregar el peer. Para hacerlo necesitas:"
    echo "1. La clave pública del cliente (desde la base de datos o el archivo .conf)"
    echo ""
    read -p "¿Tienes la clave pública del cliente? (S/N): " HAS_KEY
    if [ "$HAS_KEY" = "S" ] || [ "$HAS_KEY" = "s" ]; then
        read -p "Ingresa la clave pública del cliente: " CLIENT_PUBLIC_KEY
        echo ""
        echo "Agregando peer..."
        if wg set $INTERFACE peer "$CLIENT_PUBLIC_KEY" allowed-ips 10.8.3.10/32; then
            echo -e "${GREEN}✅ Peer agregado exitosamente${NC}"
            echo "Guardando configuración..."
            wg-quick save $INTERFACE 2>/dev/null || echo "Nota: wg-quick save puede no estar disponible, la configuración se perderá al reiniciar"
        else
            echo -e "${RED}❌ Error agregando peer${NC}"
            exit 1
        fi
    else
        echo "Obtén la clave pública del cliente desde:"
        echo "  - El archivo .conf del cliente (línea PublicKey en [Peer])"
        echo "  - La base de datos (tabla vpn_config)"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Peer encontrado${NC}"
    echo "$PEER_INFO" | while IFS=$'\t' read -r private_key public_key endpoint allowed_ips last_handshake transfer_rx transfer_tx persistent_keepalive; do
        echo "   Public Key: ${public_key:0:20}..."
        echo "   AllowedIPs actual: $allowed_ips"
        echo "   Endpoint: ${endpoint:-N/A}"
    done
    
    echo ""
    read -p "¿Actualizar AllowedIPs a 10.8.3.10/32? (S/N): " UPDATE_IPS
    if [ "$UPDATE_IPS" = "S" ] || [ "$UPDATE_IPS" = "s" ]; then
        # Extraer la clave pública del peer
        PEER_PUBLIC_KEY=$(echo "$PEER_INFO" | awk -F'\t' '{print $2}')
        echo ""
        echo "Actualizando peer..."
        if wg set $INTERFACE peer "$PEER_PUBLIC_KEY" allowed-ips 10.8.3.10/32; then
            echo -e "${GREEN}✅ Peer actualizado exitosamente${NC}"
            echo "Guardando configuración..."
            wg-quick save $INTERFACE 2>/dev/null || echo "Nota: wg-quick save puede no estar disponible"
        else
            echo -e "${RED}❌ Error actualizando peer${NC}"
            exit 1
        fi
    fi
fi

echo ""
echo "2️⃣ Verificando configuración actualizada..."
wg show $INTERFACE | grep -A 5 "10.8.3.10"

echo ""
echo "3️⃣ Probando conectividad..."
if ping -c 2 10.8.3.10 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Puedo hacer ping a 10.8.3.10${NC}"
else
    echo -e "${YELLOW}⚠️ Aún no puedo hacer ping a 10.8.3.10${NC}"
    echo "   Esto puede ser porque:"
    echo "   - El cliente no está conectado a la VPN"
    echo "   - La configuración del cliente necesita actualizarse"
    echo "   - Hay un problema de firewall"
fi

echo ""
echo "✅ Proceso completado"

