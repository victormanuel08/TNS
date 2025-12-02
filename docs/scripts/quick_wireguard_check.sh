#!/bin/bash
# Verificación rápida de WireGuard

echo "🔍 Verificación rápida de WireGuard"
echo "===================================="
echo ""

# 1. Verificar servicio
echo "1️⃣ Estado del servicio:"
INTERFACE="wg0"
if systemctl is-active --quiet "wg-quick@${INTERFACE}"; then
    echo "✅ Servicio wg-quick@${INTERFACE} está ACTIVO"
else
    echo "❌ Servicio wg-quick@${INTERFACE} NO está activo"
    echo "   Inicia con: sudo systemctl start wg-quick@${INTERFACE}"
fi
echo ""

# 2. Verificar interfaz
echo "2️⃣ Estado de la interfaz ${INTERFACE}:"
if sudo wg show "${INTERFACE}" &> /dev/null; then
    echo "✅ Interfaz ${INTERFACE} está activa"
    echo ""
    echo "   Información de la interfaz:"
    sudo wg show "${INTERFACE}" | sed 's/^/   /'
    echo ""
    echo "   Peers configurados:"
    sudo wg show "${INTERFACE}" dump | tail -n +2 | while read line; do
        if [ -n "$line" ]; then
            PEER_KEY=$(echo "$line" | cut -f1)
            PEER_IP=$(echo "$line" | cut -f4 | cut -d'/' -f1)
            echo "   - IP: ${PEER_IP}, Key: ${PEER_KEY:0:20}..."
        fi
    done
else
    echo "❌ Interfaz ${INTERFACE} NO está activa o no existe"
fi
echo ""

# 3. Verificar configuración
echo "3️⃣ Archivos de configuración:"
CONFIG_FILE="/etc/wireguard/${INTERFACE}.conf"
if [ -f "$CONFIG_FILE" ]; then
    echo "✅ Configuración existe: ${CONFIG_FILE}"
    echo "   Tamaño: $(stat -c%s "$CONFIG_FILE") bytes"
else
    echo "❌ Configuración NO existe: ${CONFIG_FILE}"
fi

PUBLIC_KEY_FILE="/etc/wireguard/public.key"
if [ -f "$PUBLIC_KEY_FILE" ]; then
    echo "✅ Clave pública existe: ${PUBLIC_KEY_FILE}"
    echo "   Clave: $(cat "$PUBLIC_KEY_FILE")"
else
    echo "❌ Clave pública NO existe: ${PUBLIC_KEY_FILE}"
fi
echo ""

# 4. Verificar puerto
echo "4️⃣ Puerto WireGuard (51820/udp):"
if sudo netstat -ulnp 2>/dev/null | grep -q ":51820" || sudo ss -ulnp 2>/dev/null | grep -q ":51820"; then
    echo "✅ Puerto 51820/udp está escuchando"
else
    echo "❌ Puerto 51820/udp NO está escuchando"
fi
echo ""

# 5. Verificar firewall
echo "5️⃣ Firewall:"
if command -v ufw &> /dev/null; then
    if sudo ufw status | grep -q "51820/udp.*ALLOW"; then
        echo "✅ Puerto 51820/udp permitido en UFW"
    else
        echo "⚠️  Puerto 51820/udp NO está explícitamente permitido en UFW"
    fi
fi
echo ""

# 6. Verificar variables de entorno del backend
echo "6️⃣ Variables de entorno en .env:"
ENV_FILE="/home/victus/projects/CORE/manu/.env"
if [ -f "$ENV_FILE" ]; then
    if grep -q "^WG_SERVER_HOST=" "$ENV_FILE"; then
        WG_HOST=$(grep "^WG_SERVER_HOST=" "$ENV_FILE" | cut -d'=' -f2)
        echo "   WG_SERVER_HOST: ${WG_HOST}"
    else
        echo "   ❌ WG_SERVER_HOST NO configurado"
    fi
    
    if grep -q "^WG_SERVER_ENDPOINT=" "$ENV_FILE"; then
        WG_ENDPOINT=$(grep "^WG_SERVER_ENDPOINT=" "$ENV_FILE" | cut -d'=' -f2)
        echo "   WG_SERVER_ENDPOINT: ${WG_ENDPOINT}"
    else
        echo "   ❌ WG_SERVER_ENDPOINT NO configurado"
    fi
else
    echo "   ❌ Archivo .env NO encontrado"
fi
echo ""

echo "===================================="
echo "📋 Resumen:"
echo ""
echo "Si el servicio está activo pero no responde:"
echo "1. Verifica que WG_SERVER_ENDPOINT tenga la IP pública correcta"
echo "2. Verifica que el puerto 51820/udp esté abierto en el firewall"
echo "3. Verifica que los peers estén configurados correctamente"
echo ""

