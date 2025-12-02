#!/bin/bash
# Script rápido para verificar el estado de Celery

echo "🔍 Estado de Celery Worker"
echo "=========================="
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "1️⃣ Estado del servicio systemd:"
echo "--------------------------------"
systemctl status celerycore.service --no-pager -l | head -n 15

echo ""
echo "2️⃣ Últimos 20 logs:"
echo "-------------------"
journalctl -u celerycore.service -n 20 --no-pager

echo ""
echo "3️⃣ Procesos de Celery:"
echo "----------------------"
ps aux | grep -E "[c]elery.*worker" || echo "No hay procesos de Celery corriendo"

echo ""
echo "4️⃣ Conexión a Redis:"
echo "--------------------"
if redis-cli -h localhost -p 6379 ping 2>/dev/null | grep -q PONG; then
    echo -e "${GREEN}✅ Redis está respondiendo${NC}"
else
    echo -e "${RED}❌ Redis NO está respondiendo${NC}"
fi

echo ""
echo "5️⃣ Comandos útiles:"
echo "-------------------"
echo "  Ver logs en tiempo real: sudo journalctl -u celerycore.service -f"
echo "  Reiniciar servicio: sudo systemctl restart celerycore.service"
echo "  Ver estado detallado: sudo systemctl status celerycore.service"

