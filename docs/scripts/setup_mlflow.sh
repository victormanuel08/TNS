#!/bin/bash
# Script para configurar MLflow en mlflow.eddeso.com
# Ejecutar en el servidor VPS

set -e  # Salir si hay error

echo "🚀 Configurando MLflow en mlflow.eddeso.com..."

# Paso 1: Crear configuración de Nginx
echo "📝 Creando configuración de Nginx..."
sudo tee /etc/nginx/sites-available/mlflow > /dev/null <<EOF
server {
    listen 80;
    server_name mlflow.eddeso.com;

    location / {
        proxy_pass http://localhost:5050;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts para operaciones largas
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF

# Paso 2: Habilitar configuración
echo "🔗 Habilitando configuración de Nginx..."
sudo ln -sf /etc/nginx/sites-available/mlflow /etc/nginx/sites-enabled/mlflow

# Paso 3: Verificar configuración
echo "✅ Verificando configuración de Nginx..."
sudo nginx -t

# Paso 4: Recargar Nginx
echo "🔄 Recargando Nginx..."
sudo systemctl reload nginx

# Paso 5: Crear servicio Systemd
echo "📦 Creando servicio Systemd para MLflow..."
sudo tee /etc/systemd/system/mlflowcore.service > /dev/null <<EOF
[Unit]
Description=MLflow Tracking Server (CORE)
After=network.target

[Service]
Type=simple
User=victus
Group=victus
WorkingDirectory=/home/victus/projects/CORE/manu
Environment="PATH=/home/victus/projects/CORE/manu/venv/bin"
ExecStart=/home/victus/projects/CORE/manu/venv/bin/mlflow ui --port 5050 --host 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Paso 6: Habilitar e iniciar servicio
echo "🎯 Habilitando servicio MLflow..."
sudo systemctl daemon-reload
sudo systemctl enable mlflowcore.service
sudo systemctl start mlflowcore.service

# Paso 7: Verificar que está corriendo
echo "🔍 Verificando estado del servicio..."
sleep 2
sudo systemctl status mlflowcore.service --no-pager -l

# Paso 8: Verificar puerto
echo "🔍 Verificando que MLflow está escuchando en el puerto 5050..."
sudo ss -tlnp | grep 5050 || echo "⚠️  MLflow aún no está escuchando. Espera unos segundos..."

echo ""
echo "✅ Configuración completada!"
echo ""
echo "📋 Próximos pasos:"
echo "1. Agrega el registro DNS en Cloudflare:"
echo "   - Tipo: A"
echo "   - Name: mlflow"
echo "   - IPv4: TU_IP_SERVIDOR"
echo "   - Proxy: ✅ Proxied (nube naranja)"
echo ""
echo "2. Configura SSL con Certbot:"
echo "   sudo certbot --nginx -d mlflow.eddeso.com"
echo ""
echo "3. Accede a: https://mlflow.eddeso.com"
echo ""

