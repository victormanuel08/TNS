#!/bin/bash
# Script para diagnosticar la configuración de WireGuard

set -e

echo "🔍 Diagnóstico de WireGuard"
echo "============================"
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Verificar variables de entorno
echo "1️⃣ Verificando variables de entorno en .env..."
ENV_FILE="/home/victus/projects/CORE/manu/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ No se encontró el archivo .env${NC}"
    exit 1
fi

# Verificar variables requeridas
REQUIRED_VARS=(
    "WG_SERVER_HOST"
    "WG_SERVER_USER"
    "WG_INTERFACE"
    "WG_SERVER_IP"
    "WG_SERVER_PORT"
    "WG_SERVER_ENDPOINT"
)

MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" "$ENV_FILE"; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ Todas las variables requeridas están configuradas${NC}"
else
    echo -e "${RED}❌ Variables faltantes:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "   - ${YELLOW}$var${NC}"
    done
fi

echo ""

# 2. Leer valores del .env
source "$ENV_FILE"

echo "2️⃣ Valores configurados:"
echo "   WG_SERVER_HOST: ${WG_SERVER_HOST:-'NO CONFIGURADO'}"
echo "   WG_SERVER_USER: ${WG_SERVER_USER:-'NO CONFIGURADO'}"
echo "   WG_INTERFACE: ${WG_INTERFACE:-'NO CONFIGURADO'}"
echo "   WG_SERVER_IP: ${WG_SERVER_IP:-'NO CONFIGURADO'}"
echo "   WG_SERVER_PORT: ${WG_SERVER_PORT:-'NO CONFIGURADO'}"
echo "   WG_SERVER_ENDPOINT: ${WG_SERVER_ENDPOINT:-'NO CONFIGURADO'}"
echo ""

# 3. Verificar si WireGuard está instalado
echo "3️⃣ Verificando instalación de WireGuard..."
if command -v wg &> /dev/null; then
    echo -e "${GREEN}✅ WireGuard está instalado${NC}"
    WG_VERSION=$(wg --version 2>&1 || echo "versión desconocida")
    echo "   Versión: $WG_VERSION"
else
    echo -e "${RED}❌ WireGuard NO está instalado${NC}"
    echo "   Instala con: sudo apt install wireguard wireguard-tools"
fi
echo ""

# 4. Verificar estado del servicio
echo "4️⃣ Verificando estado del servicio WireGuard..."
INTERFACE="${WG_INTERFACE:-wg0}"
if systemctl is-active --quiet "wg-quick@${INTERFACE}"; then
    echo -e "${GREEN}✅ Servicio wg-quick@${INTERFACE} está activo${NC}"
else
    echo -e "${YELLOW}⚠️  Servicio wg-quick@${INTERFACE} NO está activo${NC}"
    echo "   Inicia con: sudo systemctl start wg-quick@${INTERFACE}"
fi
echo ""

# 5. Verificar interfaz WireGuard
echo "5️⃣ Verificando interfaz WireGuard..."
if sudo wg show "$INTERFACE" &> /dev/null; then
    echo -e "${GREEN}✅ Interfaz ${INTERFACE} está activa${NC}"
    echo "   Información:"
    sudo wg show "$INTERFACE" | sed 's/^/   /'
else
    echo -e "${RED}❌ Interfaz ${INTERFACE} NO está activa o no existe${NC}"
fi
echo ""

# 6. Verificar configuración del servidor
echo "6️⃣ Verificando configuración del servidor..."
CONFIG_FILE="/etc/wireguard/${INTERFACE}.conf"
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${GREEN}✅ Archivo de configuración existe: ${CONFIG_FILE}${NC}"
else
    echo -e "${RED}❌ Archivo de configuración NO existe: ${CONFIG_FILE}${NC}"
fi

PUBLIC_KEY_FILE="${WG_SERVER_PUBLIC_KEY_PATH:-/etc/wireguard/public.key}"
if [ -f "$PUBLIC_KEY_FILE" ]; then
    echo -e "${GREEN}✅ Clave pública del servidor existe: ${PUBLIC_KEY_FILE}${NC}"
    echo "   Clave: $(cat "$PUBLIC_KEY_FILE" | head -c 20)..."
else
    echo -e "${YELLOW}⚠️  Clave pública del servidor NO existe: ${PUBLIC_KEY_FILE}${NC}"
    echo "   Genera con: sudo wg genkey | sudo tee /etc/wireguard/private.key | sudo wg pubkey | sudo tee /etc/wireguard/public.key"
fi
echo ""

# 7. Verificar conectividad SSH (si WG_SERVER_HOST no es localhost)
echo "7️⃣ Verificando conectividad SSH..."
if [ -n "$WG_SERVER_HOST" ] && [ "$WG_SERVER_HOST" != "localhost" ] && [ "$WG_SERVER_HOST" != "127.0.0.1" ]; then
    echo "   Intentando conectar a ${WG_SERVER_HOST}..."
    if timeout 5 ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p "${WG_SERVER_SSH_PORT:-22}" "${WG_SERVER_USER:-root}@${WG_SERVER_HOST}" "echo 'Conexión exitosa'" &> /dev/null; then
        echo -e "${GREEN}✅ Conexión SSH exitosa${NC}"
    else
        echo -e "${RED}❌ No se pudo conectar vía SSH${NC}"
        echo "   Verifica:"
        echo "   - Que el servidor esté accesible: ping ${WG_SERVER_HOST}"
        echo "   - Que el puerto SSH esté abierto: nc -zv ${WG_SERVER_HOST} ${WG_SERVER_SSH_PORT:-22}"
        echo "   - Que las credenciales sean correctas"
    fi
else
    echo -e "${GREEN}✅ Servidor WireGuard es local (localhost)${NC}"
fi
echo ""

# 8. Verificar firewall
echo "8️⃣ Verificando firewall..."
PORT="${WG_SERVER_PORT:-51820}"
if sudo ufw status | grep -q "${PORT}/udp.*ALLOW" || sudo firewall-cmd --list-ports 2>/dev/null | grep -q "${PORT}/udp"; then
    echo -e "${GREEN}✅ Puerto ${PORT}/udp está permitido en el firewall${NC}"
else
    echo -e "${YELLOW}⚠️  Puerto ${PORT}/udp puede estar bloqueado${NC}"
    echo "   Abre con: sudo ufw allow ${PORT}/udp"
fi
echo ""

# 9. Verificar permisos sudo
echo "9️⃣ Verificando permisos sudo..."
if sudo -n wg show &> /dev/null; then
    echo -e "${GREEN}✅ Usuario puede ejecutar 'wg' con sudo sin contraseña${NC}"
else
    echo -e "${YELLOW}⚠️  Usuario necesita contraseña para ejecutar 'wg' con sudo${NC}"
    echo "   Configura con: sudo visudo"
    echo "   Agrega: ${WG_SERVER_USER:-root} ALL=(ALL) NOPASSWD: /usr/bin/wg, /usr/bin/wg-quick"
fi
echo ""

# Resumen
echo "============================"
echo "📋 Resumen:"
echo ""

# Contar problemas
ISSUES=0

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    ISSUES=$((ISSUES + 1))
fi

if ! command -v wg &> /dev/null; then
    ISSUES=$((ISSUES + 1))
fi

if ! systemctl is-active --quiet "wg-quick@${INTERFACE}"; then
    ISSUES=$((ISSUES + 1))
fi

if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✅ Todo parece estar configurado correctamente${NC}"
    echo ""
    echo "Próximos pasos:"
    echo "1. Ve al admin panel: https://eddeso.com/admin/dashboard"
    echo "2. Haz clic en la pestaña 'VPN'"
    echo "3. Haz clic en 'Sincronizar' para importar peers existentes"
    echo "4. Verifica que los peers aparezcan en la lista"
else
    echo -e "${YELLOW}⚠️  Se encontraron $ISSUES problema(s)${NC}"
    echo ""
    echo "Revisa los puntos marcados con ❌ o ⚠️ arriba"
fi

echo ""

