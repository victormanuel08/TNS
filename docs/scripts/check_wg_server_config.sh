#!/bin/bash
# Script para verificar y actualizar configuración de WireGuard en el servidor

echo "🔍 Verificación de Configuración WireGuard en el Servidor"
echo "=========================================================="
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

echo "1️⃣ Verificando interfaces WireGuard activas..."
echo "-----------------------------------------------"
INTERFACES=$(wg show | grep -E "^interface:" | awk '{print $2}' | sort -u)
if [ -z "$INTERFACES" ]; then
    echo -e "${RED}❌ No se encontraron interfaces WireGuard activas${NC}"
    exit 1
fi

for IFACE in $INTERFACES; do
    echo -e "${GREEN}✅ Interfaz encontrada: $IFACE${NC}"
done

echo ""
echo "2️⃣ Verificando configuración de cada interfaz..."
echo "------------------------------------------------"

for IFACE in $INTERFACES; do
    echo ""
    echo -e "${YELLOW}📡 Interfaz: $IFACE${NC}"
    echo "----------------------------------------"
    
    # Ver IP del servidor
    SERVER_IP=$(ip addr show $IFACE 2>/dev/null | grep "inet " | awk '{print $2}' | cut -d'/' -f1)
    if [ -n "$SERVER_IP" ]; then
        echo -e "   IP del servidor: ${GREEN}$SERVER_IP${NC}"
    else
        echo -e "   ${RED}❌ No se encontró IP para $IFACE${NC}"
    fi
    
    # Ver peers configurados
    echo ""
    echo "   Peers configurados:"
    wg show $IFACE | grep -A 3 "peer:" | while read line; do
        if [[ $line == *"peer:"* ]]; then
            PEER_KEY=$(echo $line | awk '{print $2}')
            echo -e "   ${CYAN}Peer: ${PEER_KEY:0:20}...${NC}"
        elif [[ $line == *"allowed ips:"* ]]; then
            ALLOWED_IPS=$(echo $line | awk '{print $3}')
            echo -e "      ${GREEN}AllowedIPs: $ALLOWED_IPS${NC}"
        fi
    done
    
    # Ver peers con más detalle
    echo ""
    echo "   Detalles de peers:"
    wg show $IFACE dump | while IFS=$'\t' read -r private_key public_key endpoint allowed_ips last_handshake transfer_rx transfer_tx persistent_keepalive; do
        if [ "$public_key" != "public key" ]; then
            echo -e "   ${CYAN}Public Key: ${public_key:0:20}...${NC}"
            echo -e "      ${GREEN}AllowedIPs: $allowed_ips${NC}"
            echo -e "      ${YELLOW}Endpoint: ${endpoint:-N/A}${NC}"
            if [ -n "$last_handshake" ] && [ "$last_handshake" != "0" ]; then
                echo -e "      ${GREEN}Último handshake: $(date -d @$last_handshake 2>/dev/null || echo 'Reciente')${NC}"
            else
                echo -e "      ${RED}❌ Sin handshake (no conectado)${NC}"
            fi
            echo ""
        fi
    done
done

echo ""
echo "3️⃣ Buscando peer 10.8.3.10 específicamente..."
echo "----------------------------------------------"
FOUND_PEER=false
for IFACE in $INTERFACES; do
    PEER_INFO=$(wg show $IFACE dump | grep "10.8.3.10")
    if [ -n "$PEER_INFO" ]; then
        FOUND_PEER=true
        echo -e "${GREEN}✅ Peer 10.8.3.10 encontrado en interfaz: $IFACE${NC}"
        echo "$PEER_INFO" | while IFS=$'\t' read -r private_key public_key endpoint allowed_ips last_handshake transfer_rx transfer_tx persistent_keepalive; do
            echo -e "   ${CYAN}Public Key: ${public_key:0:20}...${NC}"
            echo -e "   ${GREEN}AllowedIPs: $allowed_ips${NC}"
            if [ "$allowed_ips" = "10.8.3.10/32" ]; then
                echo -e "   ${GREEN}✅ Configuración correcta${NC}"
            else
                echo -e "   ${YELLOW}⚠️ AllowedIPs puede necesitar actualización${NC}"
            fi
        done
    fi
done

if [ "$FOUND_PEER" = false ]; then
    echo -e "${RED}❌ Peer 10.8.3.10 NO encontrado en ninguna interfaz${NC}"
    echo ""
    echo "Necesitas agregar el peer al servidor. Para hacerlo:"
    echo "1. Obtén la clave pública del cliente desde la base de datos"
    echo "2. Ejecuta: sudo wg set [INTERFAZ] peer [CLAVE_PUBLICA] allowed-ips 10.8.3.10/32"
fi

echo ""
echo "4️⃣ Verificando conectividad..."
echo "-------------------------------"
if ping -c 2 10.8.3.10 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Puedo hacer ping a 10.8.3.10${NC}"
else
    echo -e "${RED}❌ NO puedo hacer ping a 10.8.3.10${NC}"
    echo "   Esto puede ser normal si el cliente no está conectado o la configuración está incorrecta"
fi

echo ""
echo "✅ Verificación completada"

