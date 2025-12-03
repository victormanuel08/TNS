#!/bin/bash
# Script para instalar y configurar Celery Beat en el VPS

set -e

echo "🔧 Instalación de Celery Beat"
echo "=============================="
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SERVICE_FILE="/etc/systemd/system/celerybeat.service"
PROJECT_DIR="/home/victus/projects/CORE/manu"

# Verificar que estamos como root o con sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}⚠️ Este script requiere permisos de root${NC}"
    echo "Ejecuta con: sudo bash $0"
    exit 1
fi

echo "1️⃣ Deteniendo servicio actual (si existe)..."
systemctl stop celerybeat.service 2>/dev/null || echo "   Servicio no estaba corriendo"

echo ""
echo "2️⃣ Creando archivo de servicio systemd..."

# Crear el archivo de servicio
cat > "$SERVICE_FILE" << 'EOF'
[Unit]
Description=Celery Beat Scheduler for TNS Core
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=victus
Group=victus
WorkingDirectory=/home/victus/projects/CORE/manu
Environment="PATH=/home/victus/projects/CORE/manu/env/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/victus/projects/CORE/manu/.env

# Comando para iniciar Celery Beat
# -l info: Nivel de logging
ExecStart=/home/victus/projects/CORE/manu/env/bin/celery -A config beat -l info

# Timeouts
TimeoutStartSec=60
TimeoutStopSec=30

# Reiniciar automáticamente si falla
Restart=always
RestartSec=10

# Límites de recursos
LimitNOFILE=65536

# Logs
StandardOutput=journal
StandardError=journal
SyslogIdentifier=celerybeat

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Archivo de servicio creado${NC}"

echo ""
echo "3️⃣ Recargando systemd..."
systemctl daemon-reload
echo -e "${GREEN}✅ Systemd recargado${NC}"

echo ""
echo "4️⃣ Habilitando servicio para inicio automático..."
systemctl enable celerybeat.service
echo -e "${GREEN}✅ Servicio habilitado${NC}"

echo ""
echo "5️⃣ Iniciando servicio..."
systemctl start celerybeat.service
echo -e "${GREEN}✅ Servicio iniciado${NC}"

echo ""
echo "6️⃣ Verificando estado..."
sleep 2
systemctl status celerybeat.service --no-pager

echo ""
echo -e "${GREEN}✅ Instalación completada${NC}"
echo ""
echo "📋 Comandos útiles:"
echo "   Ver logs: sudo journalctl -u celerybeat.service -f"
echo "   Reiniciar: sudo systemctl restart celerybeat.service"
echo "   Detener: sudo systemctl stop celerybeat.service"
echo "   Estado: sudo systemctl status celerybeat.service"

