#!/bin/bash
# Fix rápido: Cambiar Type=notify a Type=simple

echo "🔧 Fix rápido: Cambiando Type=notify a Type=simple"
echo "=================================================="

sudo sed -i 's/Type=notify/Type=simple/' /etc/systemd/system/celerycore.service
sudo sed -i '/NotifyAccess=all/d' /etc/systemd/system/celerycore.service

echo "✅ Archivo actualizado"

sudo systemctl daemon-reload
echo "✅ Systemd recargado"

sudo systemctl restart celerycore.service
echo "✅ Servicio reiniciado"

sleep 5

if systemctl is-active --quiet celerycore.service; then
    echo "✅ Servicio está corriendo correctamente"
    sudo systemctl status celerycore.service --no-pager | head -n 10
else
    echo "❌ Servicio aún no está activo"
    echo "Ver logs: sudo journalctl -u celerycore.service -n 30 --no-pager"
fi

