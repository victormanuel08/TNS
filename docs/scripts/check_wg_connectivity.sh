#!/bin/bash
# Script para verificar conectividad WireGuard

echo "🔍 Verificando conectividad WireGuard"
echo "======================================"
echo ""

# 1. Ver IP del servidor
echo "1️⃣ IP del servidor en wg-main:"
ip addr show wg-main | grep "inet " || echo "❌ No se encontró IP"
echo ""

# 2. Ver routing
echo "2️⃣ Rutas relacionadas con WireGuard:"
ip route | grep "wg-main\|10.8.3" || echo "No hay rutas específicas"
echo ""

# 3. Ver configuración del servidor
echo "3️⃣ Configuración del servidor (sin claves privadas):"
sudo grep -v "PrivateKey" /etc/wireguard/wg-main.conf 2>/dev/null | head -20 || echo "❌ No se encontró configuración"
echo ""

# 4. Verificar peers y su estado
echo "4️⃣ Estado de los peers:"
sudo wg show wg-main | grep -E "peer:|allowed ips:|latest handshake:" | head -20
echo ""

# 5. Verificar si el servidor puede hacer ping a sí mismo
echo "5️⃣ Verificando IP del servidor:"
SERVER_IP=$(ip addr show wg-main | grep "inet " | awk '{print $2}' | cut -d'/' -f1)
if [ -n "$SERVER_IP" ]; then
    echo "   IP del servidor: $SERVER_IP"
    echo "   Probando ping al servidor mismo:"
    ping -c 2 $SERVER_IP 2>&1 | tail -3
else
    echo "   ❌ No se encontró IP del servidor"
fi
echo ""

# 6. Verificar firewall
echo "6️⃣ Verificando firewall:"
if command -v ufw &> /dev/null; then
    echo "   Estado UFW:"
    sudo ufw status | head -5
fi
echo ""

echo "======================================"
echo "📋 Diagnóstico:"
echo ""
echo "Si el peer tiene handshake y tráfico pero el ping no funciona:"
echo "1. El cliente puede tener firewall bloqueando ICMP"
echo "2. El cliente puede no tener routing configurado correctamente"
echo "3. El AllowedIPs del cliente puede ser muy restrictivo"
echo ""
echo "El tráfico bidireccional indica que la conexión funciona,"
echo "pero el ping específicamente puede estar bloqueado."

