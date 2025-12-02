#!/bin/bash
# Script para verificar el estado real de WireGuard

echo "🔍 Estado de WireGuard"
echo "======================"
echo ""

# 1. Verificar servicio wg-main
echo "1️⃣ Estado del servicio wg-quick@wg-main:"
sudo systemctl status wg-quick@wg-main --no-pager -l | head -20
echo ""

# 2. Verificar interfaz wg-main
echo "2️⃣ Estado de la interfaz wg-main:"
if sudo wg show wg-main &> /dev/null; then
    echo "✅ Interfaz wg-main está activa"
    echo ""
    sudo wg show wg-main
    echo ""
    echo "📊 Resumen de peers:"
    sudo wg show wg-main dump | tail -n +2 | while read line; do
        if [ -n "$line" ]; then
            PEER_KEY=$(echo "$line" | cut -f1)
            PEER_IP=$(echo "$line" | cut -f4 | cut -d'/' -f1)
            LAST_HANDSHAKE=$(echo "$line" | cut -f5)
            TX_BYTES=$(echo "$line" | cut -f6)
            RX_BYTES=$(echo "$line" | cut -f7)
            
            if [ "$LAST_HANDSHAKE" != "0" ]; then
                # Calcular tiempo desde último handshake
                NOW=$(date +%s)
                SECONDS_AGO=$((NOW - LAST_HANDSHAKE))
                if [ $SECONDS_AGO -lt 180 ]; then
                    STATUS="🟢 CONECTADO"
                else
                    STATUS="🟡 DESCONECTADO (hace ${SECONDS_AGO}s)"
                fi
            else
                STATUS="🔴 NUNCA CONECTADO"
            fi
            
            echo "   IP: ${PEER_IP}"
            echo "   Key: ${PEER_KEY:0:20}..."
            echo "   Estado: ${STATUS}"
            echo "   TX: ${TX_BYTES} bytes | RX: ${RX_BYTES} bytes"
            echo ""
        fi
    done
else
    echo "❌ Interfaz wg-main NO está activa"
fi
echo ""

# 3. Verificar configuración
echo "3️⃣ Archivos de configuración:"
CONFIG_FILE="/etc/wireguard/wg-main.conf"
if [ -f "$CONFIG_FILE" ]; then
    echo "✅ Configuración existe: ${CONFIG_FILE}"
    echo "   Contenido (sin claves privadas):"
    sudo grep -v "PrivateKey" "$CONFIG_FILE" | head -20
else
    echo "❌ Configuración NO existe: ${CONFIG_FILE}"
fi
echo ""

# 4. Verificar IPs asignadas
echo "4️⃣ IPs de la interfaz:"
ip addr show wg-main 2>/dev/null | grep "inet " || echo "❌ No se encontró IP en wg-main"
echo ""

# 5. Verificar puerto
echo "5️⃣ Puerto WireGuard:"
if sudo ss -ulnp | grep -q ":51820"; then
    echo "✅ Puerto 51820/udp está escuchando"
    sudo ss -ulnp | grep ":51820"
else
    echo "❌ Puerto 51820/udp NO está escuchando"
fi
echo ""

# 6. Verificar si 10.8.1.11 está en la configuración
echo "6️⃣ Buscando peer con IP 10.8.1.11:"
if sudo wg show wg-main dump 2>/dev/null | grep -q "10.8.1.11"; then
    echo "✅ Peer con IP 10.8.1.11 encontrado en la configuración"
    sudo wg show wg-main dump | grep "10.8.1.11"
else
    echo "❌ Peer con IP 10.8.1.11 NO encontrado en la configuración"
    echo "   Esto significa que:"
    echo "   - El peer no está configurado en el servidor"
    echo "   - O el peer está en otra interfaz WireGuard"
    echo "   - O el peer nunca se conectó"
fi
echo ""

echo "======================"
echo "📋 Resumen:"
echo ""
echo "Si el peer 10.8.1.11 no aparece:"
echo "1. El peer no está configurado en el servidor WireGuard"
echo "2. El peer necesita descargar e instalar su archivo .conf"
echo "3. El peer necesita conectarse a la VPN"
echo ""

