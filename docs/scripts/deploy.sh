#!/bin/bash

# Script de despliegue rápido para TNSFULL
# Hace git pull, build y restart de PM2 sin reiniciar el servidor

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Iniciando despliegue de TNSFULL...${NC}"
echo ""

# Directorios
CORE_DIR="$HOME/projects/CORE"
FRONT_DIR="$CORE_DIR/front"
MANU_DIR="$CORE_DIR/manu"

# Verificar que los directorios existen
if [ ! -d "$CORE_DIR" ]; then
    echo -e "${RED}❌ Error: Directorio $CORE_DIR no existe${NC}"
    exit 1
fi

cd "$CORE_DIR"

# 1. Git Pull
echo -e "${YELLOW}📥 Haciendo git pull en CORE...${NC}"
git pull origin main || git pull origin master
echo -e "${GREEN}✅ Git pull completado${NC}"
echo ""

# 2. Build Frontend
echo -e "${YELLOW}🔨 Construyendo frontend...${NC}"
cd "$FRONT_DIR"

# Activar venv si existe
if [ -d "node_modules" ]; then
    echo "Node modules encontrados, continuando..."
else
    echo "Instalando dependencias..."
    npm install
fi

# Build
npm run build
echo -e "${GREEN}✅ Build de frontend completado${NC}"
echo ""

# 3. Reiniciar PM2 - Frontend
echo -e "${YELLOW}🔄 Reiniciando PM2 - Frontend...${NC}"
# Intentar diferentes nombres comunes
FRONT_RESTARTED=false
for name in front frontend nuxt; do
    if pm2 describe $name &>/dev/null; then
        pm2 restart $name
        FRONT_RESTARTED=true
        echo -e "${GREEN}✅ Frontend reiniciado (proceso: $name)${NC}"
        break
    fi
done

if [ "$FRONT_RESTARTED" = false ]; then
    echo -e "${YELLOW}⚠️  No se encontró proceso frontend en PM2${NC}"
    echo -e "${YELLOW}Procesos PM2 disponibles:${NC}"
    pm2 list
    echo ""
    read -p "¿Quieres especificar el nombre del proceso frontend? (Enter para omitir): " front_name
    if [ ! -z "$front_name" ]; then
        pm2 restart "$front_name"
        echo -e "${GREEN}✅ Frontend reiniciado (proceso: $front_name)${NC}"
    fi
fi
echo ""

# 4. Reiniciar PM2 - Backend (si existe)
echo -e "${YELLOW}🔄 Reiniciando PM2 - Backend (si existe)...${NC}"
BACK_RESTARTED=false
for name in back backend manu django backcore; do
    if pm2 describe $name &>/dev/null; then
        pm2 restart $name
        BACK_RESTARTED=true
        echo -e "${GREEN}✅ Backend reiniciado (proceso: $name)${NC}"
        break
    fi
done

if [ "$BACK_RESTARTED" = false ]; then
    echo -e "${YELLOW}⚠️  No se encontró proceso backend en PM2, continuando...${NC}"
fi
echo ""

# 5. Reiniciar Celery (si existe)
echo -e "${YELLOW}🔄 Reiniciando Celery (si existe)...${NC}"
CELERY_RESTARTED=false
for name in celery celerycore celerybeat; do
    if pm2 describe $name &>/dev/null; then
        pm2 restart $name
        CELERY_RESTARTED=true
        echo -e "${GREEN}✅ Celery reiniciado (proceso: $name)${NC}"
        break
    fi
done

if [ "$CELERY_RESTARTED" = false ]; then
    echo -e "${YELLOW}⚠️  No se encontró proceso Celery en PM2, continuando...${NC}"
fi
echo ""

# 6. Reiniciar servicios systemd (si existen y no están en PM2)
echo -e "${YELLOW}🔄 Verificando servicios systemd...${NC}"
if systemctl is-active --quiet backcore.service 2>/dev/null; then
    echo -e "${YELLOW}Reiniciando backcore.service...${NC}"
    sudo systemctl restart backcore.service || echo -e "${YELLOW}⚠️  No se pudo reiniciar backcore.service${NC}"
fi

if systemctl is-active --quiet celerycore.service 2>/dev/null; then
    echo -e "${YELLOW}Reiniciando celerycore.service...${NC}"
    sudo systemctl restart celerycore.service || echo -e "${YELLOW}⚠️  No se pudo reiniciar celerycore.service${NC}"
fi

if systemctl is-active --quiet celerybeat.service 2>/dev/null; then
    echo -e "${YELLOW}Reiniciando celerybeat.service...${NC}"
    sudo systemctl restart celerybeat.service || echo -e "${YELLOW}⚠️  No se pudo reiniciar celerybeat.service${NC}"
fi
echo ""

# 7. Mostrar estado de PM2
echo -e "${GREEN}📊 Estado actual de PM2:${NC}"
pm2 list
echo ""

# 8. Mostrar logs recientes
echo -e "${GREEN}📋 Últimas líneas de logs (frontend):${NC}"
for name in front frontend nuxt; do
    if pm2 describe $name &>/dev/null; then
        pm2 logs $name --lines 10 --nostream
        break
    fi
done
echo ""

echo -e "${GREEN}✅ Despliegue completado exitosamente!${NC}"
echo -e "${YELLOW}💡 Tip: Usa 'pm2 logs' para ver logs en tiempo real${NC}"
echo -e "${YELLOW}💡 Tip: Usa 'pm2 monit' para monitorear procesos${NC}"

