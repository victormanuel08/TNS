#!/bin/bash
# Script para instalar y configurar el autoescalador
# Ejecutar con: sudo bash install_autoscaler.sh

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Instalador de Autoescalador${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verificar que se ejecuta como root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Este script requiere permisos de root${NC}"
    echo "Ejecuta con: sudo bash $0"
    exit 1
fi

# Directorios
SCRIPTS_DIR="/home/victus/scripts"
SYSTEMD_DIR="/etc/systemd/system"
DOCS_SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Crear directorio de scripts si no existe
mkdir -p "$SCRIPTS_DIR"
mkdir -p /var/log

echo -e "${YELLOW}1️⃣ Copiando scripts...${NC}"

# Copiar scripts
cp "$DOCS_SCRIPTS_DIR/autoscaler.sh" "$SCRIPTS_DIR/"
cp "$DOCS_SCRIPTS_DIR/autoscaler_metrics.sh" "$SCRIPTS_DIR/"
cp "$DOCS_SCRIPTS_DIR/autoscaler_config.json" "$SCRIPTS_DIR/"

# Hacer ejecutables
chmod +x "$SCRIPTS_DIR/autoscaler.sh"
chmod +x "$SCRIPTS_DIR/autoscaler_metrics.sh"

echo -e "${GREEN}✅ Scripts copiados${NC}"

# Verificar dependencias
echo ""
echo -e "${YELLOW}2️⃣ Verificando dependencias...${NC}"

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  jq no está instalado. Instalando...${NC}"
    apt-get update -qq
    apt-get install -y jq bc
    echo -e "${GREEN}✅ jq instalado${NC}"
else
    echo -e "${GREEN}✅ jq ya está instalado${NC}"
fi

if ! command -v bc &> /dev/null; then
    echo -e "${YELLOW}⚠️  bc no está instalado. Instalando...${NC}"
    apt-get install -y bc
    echo -e "${GREEN}✅ bc instalado${NC}"
else
    echo -e "${GREEN}✅ bc ya está instalado${NC}"
fi

# Crear servicio systemd
echo ""
echo -e "${YELLOW}3️⃣ Creando servicio systemd...${NC}"

# Crear servicio con timer
cat > "$SYSTEMD_DIR/autoscaler.service" << 'EOF'
[Unit]
Description=Autoescalador de Workers Gunicorn y Celery
After=network.target

[Service]
Type=oneshot
User=root
ExecStart=/bin/bash /home/victus/scripts/autoscaler.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=autoscaler
EOF

# Crear timer
cat > "$SYSTEMD_DIR/autoscaler.timer" << 'EOF'
[Unit]
Description=Timer para Autoescalador (cada 2 minutos)
Requires=autoscaler.service

[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
AccuracySec=1s

[Install]
WantedBy=timers.target
EOF

echo -e "${GREEN}✅ Servicio systemd creado${NC}"

# Recargar systemd
echo ""
echo -e "${YELLOW}4️⃣ Recargando systemd...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✅ Systemd recargado${NC}"

# Mostrar estado
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Instalación completada${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}📋 Próximos pasos:${NC}"
echo ""
echo "1. Editar configuración:"
echo "   sudo nano $SCRIPTS_DIR/autoscaler_config.json"
echo ""
echo "2. Habilitar proyectos gradualmente (empezar con backregisters):"
echo "   Editar autoscaler_config.json y cambiar 'enabled: false' a 'enabled: true'"
echo ""
echo "3. Iniciar autoescalador:"
echo "   sudo systemctl start autoscaler.timer"
echo "   sudo systemctl enable autoscaler.timer"
echo ""
echo "4. Ver logs:"
echo "   sudo journalctl -u autoscaler -f"
echo ""
echo "5. Ver estado:"
echo "   sudo systemctl status autoscaler.timer"
echo ""

