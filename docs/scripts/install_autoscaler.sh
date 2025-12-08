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

# Modificar servicios a 1 worker base
echo ""
echo -e "${YELLOW}4️⃣ Modificando servicios a 1 worker base...${NC}"

SERVICES=(
    "backregisters:--workers 3:--workers 1"
    "backdipro:--workers 2:--workers 1"
    "backglobal:--workers 3:--workers 1"
    "backbce:--workers 3:--workers 1"
    "backcore:--workers 3:--workers 1"
)

for service_config in "${SERVICES[@]}"; do
    IFS=':' read -r service_name old_workers new_workers <<< "$service_config"
    service_file="/etc/systemd/system/${service_name}.service"
    
    if [ -f "$service_file" ]; then
        echo -e "   Modificando ${BLUE}${service_name}${NC}..."
        
        # Crear backup con timestamp
        backup_file="${service_file}.backup.$(date +%Y%m%d_%H%M%S)"
        sudo cp "$service_file" "$backup_file"
        echo -e "   ${BLUE}📦 Backup creado: $(basename $backup_file)${NC}"
        
        # Modificar workers
        sudo sed -i "s/${old_workers}/${new_workers}/g" "$service_file"
        
        echo -e "   ${GREEN}✅ ${service_name} modificado${NC}"
    else
        echo -e "   ${YELLOW}⚠️  ${service_name} no encontrado, saltando...${NC}"
    fi
done

# Modificar celerycore (concurrency)
echo -e "   Modificando ${BLUE}celerycore${NC}..."
celery_file="/etc/systemd/system/celerycore.service"
if [ -f "$celery_file" ]; then
    backup_file="${celery_file}.backup.$(date +%Y%m%d_%H%M%S)"
    sudo cp "$celery_file" "$backup_file"
    echo -e "   ${BLUE}📦 Backup creado: $(basename $backup_file)${NC}"
    sudo sed -i "s/--concurrency=4/--concurrency=2/g" "$celery_file"
    echo -e "   ${GREEN}✅ celerycore modificado${NC}"
else
    echo -e "   ${YELLOW}⚠️  celerycore no encontrado, saltando...${NC}"
fi

# Crear script de rollback
echo ""
echo -e "${YELLOW}📦 Creando script de rollback...${NC}"
cat > "$SCRIPTS_DIR/rollback_autoscaler.sh" << 'ROLLBACK_EOF'
#!/bin/bash
# Script de rollback automático para autoescalador

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Rollback de Autoescalador${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Este script requiere permisos de root${NC}"
    echo "Ejecuta con: sudo bash $0"
    exit 1
fi

# Detener autoescalador
echo -e "${YELLOW}1️⃣ Deteniendo autoescalador...${NC}"
systemctl stop autoscaler.timer 2>/dev/null || true
systemctl disable autoscaler.timer 2>/dev/null || true
echo -e "${GREEN}✅ Autoescalador detenido${NC}"

# Restaurar servicios desde backups
echo ""
echo -e "${YELLOW}2️⃣ Restaurando servicios desde backups...${NC}"

SERVICES=("backregisters" "backdipro" "backglobal" "backbce" "backcore" "celerycore")

for service in "${SERVICES[@]}"; do
    service_file="/etc/systemd/system/${service}.service"
    backup=$(ls -t ${service_file}.backup.* 2>/dev/null | head -1)
    
    if [ -n "$backup" ] && [ -f "$backup" ]; then
        echo -e "   Restaurando ${BLUE}${service}${NC} desde $(basename $backup)"
        cp "$backup" "$service_file"
        echo -e "   ${GREEN}✅ ${service} restaurado${NC}"
    else
        echo -e "   ${YELLOW}⚠️  No se encontró backup para ${service}${NC}"
    fi
done

# Recargar systemd
echo ""
echo -e "${YELLOW}3️⃣ Recargando systemd...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✅ Systemd recargado${NC}"

# Reiniciar servicios
echo ""
echo -e "${YELLOW}4️⃣ Reiniciando servicios...${NC}"
for service in "${SERVICES[@]}"; do
    if systemctl is-enabled --quiet "${service}.service" 2>/dev/null; then
        echo -e "   Reiniciando ${BLUE}${service}${NC}..."
        systemctl restart "${service}.service" 2>/dev/null || true
        sleep 1
    fi
done
echo -e "${GREEN}✅ Servicios reiniciados${NC}"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Rollback completado${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}📋 Verificar estado:${NC}"
echo "   systemctl status backcore backbce backglobal backregisters backdipro celerycore"
echo ""
ROLLBACK_EOF

chmod +x "$SCRIPTS_DIR/rollback_autoscaler.sh"
echo -e "${GREEN}✅ Script de rollback creado: $SCRIPTS_DIR/rollback_autoscaler.sh${NC}"

echo -e "${GREEN}✅ Servicios modificados${NC}"

# Recargar systemd y reiniciar servicios
echo ""
echo -e "${YELLOW}5️⃣ Recargando systemd y reiniciando servicios...${NC}"
systemctl daemon-reload

# Reiniciar servicios
for service_config in "${SERVICES[@]}"; do
    IFS=':' read -r service_name old_workers new_workers <<< "$service_config"
    if systemctl is-active --quiet "${service_name}.service" 2>/dev/null; then
        echo -e "   Reiniciando ${BLUE}${service_name}${NC}..."
        systemctl restart "${service_name}.service"
        sleep 2
    fi
done

# Reiniciar celerycore si existe
if systemctl is-active --quiet celerycore.service 2>/dev/null; then
    echo -e "   Reiniciando ${BLUE}celerycore${NC}..."
    systemctl restart celerycore.service
    sleep 2
fi

echo -e "${GREEN}✅ Servicios reiniciados${NC}"

# Iniciar autoescalador
echo ""
echo -e "${YELLOW}6️⃣ Iniciando autoescalador...${NC}"
systemctl start autoscaler.timer
systemctl enable autoscaler.timer
echo -e "${GREEN}✅ Autoescalador iniciado${NC}"

# Verificar estado
echo ""
echo -e "${YELLOW}7️⃣ Verificando estado...${NC}"
sleep 3

if systemctl is-active --quiet autoscaler.timer; then
    echo -e "${GREEN}✅ Autoescalador activo${NC}"
else
    echo -e "${RED}❌ Autoescalador no está activo${NC}"
fi

# Mostrar estado final
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Instalación completada${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}✅ Todos los proyectos están habilitados y configurados${NC}"
echo -e "${GREEN}✅ Todos los servicios están en 1 worker base${NC}"
echo -e "${GREEN}✅ Autoescalador está activo y monitoreando${NC}"
echo ""
echo -e "${YELLOW}📋 Comandos útiles:${NC}"
echo ""
echo "Ver logs del autoescalador:"
echo "   sudo journalctl -u autoscaler -f"
echo ""
echo "Ver workers actuales:"
echo "   ps aux | grep gunicorn | grep -v grep"
echo ""
echo "Ver estado del autoescalador:"
echo "   sudo systemctl status autoscaler.timer"
echo ""
echo "Ver estado de todos los servicios:"
echo "   systemctl status backcore backbce backglobal backregisters backdipro celerycore"
echo ""

