#!/bin/bash
# Script para corregir el problema de timeout de Celery en systemd

set -e

echo "🔧 Corrección de Timeout de Celery"
echo "===================================="
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="/home/victus/projects/CORE/manu"
SERVICE_FILE="/etc/systemd/system/celerycore.service"

# Verificar que estamos como root o con sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}⚠️ Este script requiere permisos de root${NC}"
    echo "Ejecuta con: sudo bash $0"
    exit 1
fi

echo "1️⃣ Deteniendo servicio actual..."
systemctl stop celerycore.service 2>/dev/null || echo "   Servicio no estaba corriendo"

echo ""
echo "2️⃣ Creando archivo de servicio systemd..."

# Crear el archivo de servicio
cat > "$SERVICE_FILE" << 'EOF'
[Unit]
Description=Celery Worker for TNS Core
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=notify
User=victus
Group=victus
WorkingDirectory=/home/victus/projects/CORE/manu
Environment="PATH=/home/victus/projects/CORE/manu/env/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/victus/projects/CORE/manu/.env

# Comando para iniciar Celery
# -P prefork: Pool de procesos para Linux (NO usar -P solo que es para Windows)
# -E: Habilitar eventos de tareas para monitoreo
# -l info: Nivel de logging
ExecStart=/home/victus/projects/CORE/manu/env/bin/celery -A config worker -l info -P prefork --concurrency=4 -E --time-limit=3600

# Notificar a systemd cuando esté listo
NotifyAccess=all

# Timeouts aumentados para dar tiempo a Celery de iniciar
TimeoutStartSec=300
TimeoutStopSec=60

# Reiniciar automáticamente si falla
Restart=always
RestartSec=10

# Límites de recursos
LimitNOFILE=65536

# Logs
StandardOutput=journal
StandardError=journal
SyslogIdentifier=celerycore

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Archivo de servicio creado${NC}"

echo ""
echo "3️⃣ Recargando systemd..."
systemctl daemon-reload
echo -e "${GREEN}✅ Systemd recargado${NC}"

echo ""
echo "4️⃣ Iniciando servicio..."
systemctl start celerycore.service

echo ""
echo "5️⃣ Esperando 5 segundos para verificar estado..."
sleep 5

echo ""
echo "6️⃣ Verificando estado del servicio..."
if systemctl is-active --quiet celerycore.service; then
    echo -e "${GREEN}✅ Servicio está corriendo${NC}"
else
    echo -e "${RED}❌ Servicio NO está corriendo${NC}"
    echo ""
    echo "Últimos logs:"
    journalctl -u celerycore.service -n 20 --no-pager
    exit 1
fi

echo ""
echo "7️⃣ Habilitando inicio automático..."
systemctl enable celerycore.service
echo -e "${GREEN}✅ Inicio automático habilitado${NC}"

echo ""
echo "8️⃣ Verificando configuración..."
STATUS=$(systemctl status celerycore.service --no-pager | head -n 20)
echo "$STATUS"

echo ""
echo "9️⃣ Verificando logs para confirmar configuración correcta..."
LOGS=$(journalctl -u celerycore.service -n 30 --no-pager | grep -E "(prefork|task events|concurrency)" || echo "")

if echo "$LOGS" | grep -q "prefork"; then
    echo -e "${GREEN}✅ Pool prefork configurado correctamente${NC}"
else
    echo -e "${YELLOW}⚠️ No se encontró 'prefork' en los logs${NC}"
fi

if echo "$LOGS" | grep -q "task events.*ON"; then
    echo -e "${GREEN}✅ Task events habilitados${NC}"
else
    echo -e "${YELLOW}⚠️ Task events pueden no estar habilitados${NC}"
fi

echo ""
echo "📋 Resumen"
echo "=========="
echo -e "${GREEN}✅ Servicio configurado y corriendo${NC}"
echo ""
echo "Comandos útiles:"
echo "  - Ver estado: sudo systemctl status celerycore.service"
echo "  - Ver logs: sudo journalctl -u celerycore.service -f"
echo "  - Reiniciar: sudo systemctl restart celerycore.service"
echo ""
echo -e "${GREEN}✅ Corrección completada${NC}"

