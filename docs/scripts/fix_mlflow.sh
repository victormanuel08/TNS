#!/bin/bash
# Script para instalar MLflow y configurar el servicio

set -e

echo "🔍 Verificando venv..."

# Verificar si el venv existe
if [ ! -d "/home/victus/projects/CORE/manu/env" ]; then
    echo "❌ El venv no existe. Creando venv..."
    cd /home/victus/projects/CORE/manu
    python3 -m venv env
    echo "✅ venv creado"
else
    echo "✅ venv existe"
fi

# Activar venv e instalar MLflow
echo "📦 Instalando MLflow..."
cd /home/victus/projects/CORE/manu
source env/bin/activate
pip install --upgrade pip
pip install mlflow>=2.8.0
deactivate

echo "✅ MLflow instalado"

# Verificar instalación
echo "🔍 Verificando instalación..."
/home/victus/projects/CORE/manu/env/bin/python -m mlflow --version

# Actualizar el servicio para usar python -m mlflow (más confiable)
echo "🔧 Actualizando servicio systemd..."
sudo tee /etc/systemd/system/mlflowcore.service > /dev/null <<EOF
[Unit]
Description=MLflow Tracking Server (CORE)
After=network.target

[Service]
Type=simple
User=victus
Group=victus
WorkingDirectory=/home/victus/projects/CORE/manu
Environment="PATH=/home/victus/projects/CORE/manu/env/bin"
ExecStart=/home/victus/projects/CORE/manu/env/bin/python -m mlflow ui --port 5050 --host 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Recargar y reiniciar
echo "🔄 Reiniciando servicio..."
sudo systemctl daemon-reload
sudo systemctl restart mlflowcore.service

# Esperar un momento y verificar
sleep 3
echo "🔍 Verificando estado..."
sudo systemctl status mlflowcore.service --no-pager -l

echo ""
echo "✅ ¡Listo! MLflow debería estar corriendo ahora."
echo "🌐 Accede a: https://mlflow.eddeso.com"

