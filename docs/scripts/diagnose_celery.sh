#!/bin/bash
# Script para diagnosticar problemas con Celery

set -e

echo "🔍 Diagnóstico de Celery"
echo "========================"
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="/home/victus/projects/CORE/manu"
VENV_DIR="$PROJECT_DIR/env"

# 1. Verificar Redis
echo "1️⃣ Verificando Redis..."
if systemctl is-active --quiet redis-server || systemctl is-active --quiet redis; then
    echo -e "${GREEN}✅ Redis está corriendo${NC}"
    REDIS_STATUS=$(systemctl is-active redis-server 2>/dev/null || systemctl is-active redis 2>/dev/null)
    echo "   Estado: $REDIS_STATUS"
else
    echo -e "${RED}❌ Redis NO está corriendo${NC}"
    echo "   Ejecuta: sudo systemctl start redis-server"
fi

# Probar conexión
if redis-cli -h localhost -p 6379 ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Conexión a Redis exitosa (puerto 6379)${NC}"
else
    echo -e "${RED}❌ No se puede conectar a Redis en puerto 6379${NC}"
fi

echo ""

# 2. Verificar REDIS_URL en .env
echo "2️⃣ Verificando REDIS_URL en .env..."
if [ -f "$PROJECT_DIR/.env" ]; then
    REDIS_URL=$(grep "^REDIS_URL=" "$PROJECT_DIR/.env" | cut -d'=' -f2- || echo "")
    if [ -z "$REDIS_URL" ]; then
        echo -e "${YELLOW}⚠️ REDIS_URL no encontrado en .env${NC}"
    else
        echo "   REDIS_URL=$REDIS_URL"
        if [[ "$REDIS_URL" == *"6379"* ]]; then
            echo -e "${GREEN}✅ Puerto correcto (6379)${NC}"
        else
            echo -e "${YELLOW}⚠️ Puerto puede ser incorrecto (debe ser 6379)${NC}"
        fi
    fi
else
    echo -e "${RED}❌ Archivo .env no encontrado${NC}"
fi

echo ""

# 3. Verificar Celery Worker
echo "3️⃣ Verificando Celery Worker..."
if systemctl is-active --quiet celerycore.service; then
    echo -e "${GREEN}✅ Celery Worker está corriendo${NC}"
    CELERY_STATUS=$(systemctl is-active celerycore.service)
    echo "   Estado: $CELERY_STATUS"
else
    echo -e "${RED}❌ Celery Worker NO está corriendo${NC}"
    echo "   Ejecuta: sudo systemctl start celerycore.service"
fi

# Verificar procesos
CELERY_PROCESSES=$(ps aux | grep -c "[c]elery.*worker" || echo "0")
if [ "$CELERY_PROCESSES" -gt 0 ]; then
    echo -e "${GREEN}✅ Hay $CELERY_PROCESSES proceso(s) de Celery corriendo${NC}"
else
    echo -e "${RED}❌ No hay procesos de Celery corriendo${NC}"
fi

echo ""

# 4. Verificar archivos de configuración
echo "4️⃣ Verificando archivos de configuración..."

# celery.py
if [ -f "$PROJECT_DIR/config/celery.py" ]; then
    echo -e "${GREEN}✅ config/celery.py existe${NC}"
else
    echo -e "${RED}❌ config/celery.py NO existe${NC}"
fi

# __init__.py
if [ -f "$PROJECT_DIR/config/__init__.py" ]; then
    if grep -q "celery_app" "$PROJECT_DIR/config/__init__.py"; then
        echo -e "${GREEN}✅ config/__init__.py importa celery_app${NC}"
    else
        echo -e "${YELLOW}⚠️ config/__init__.py NO importa celery_app${NC}"
        echo "   Debe contener: from .celery import app as celery_app"
    fi
else
    echo -e "${RED}❌ config/__init__.py NO existe${NC}"
fi

echo ""

# 5. Verificar venv y dependencias
echo "5️⃣ Verificando entorno virtual..."
if [ -d "$VENV_DIR" ]; then
    echo -e "${GREEN}✅ Entorno virtual existe${NC}"
    
    if [ -f "$VENV_DIR/bin/celery" ]; then
        echo -e "${GREEN}✅ Celery está instalado en el venv${NC}"
    else
        echo -e "${RED}❌ Celery NO está instalado en el venv${NC}"
        echo "   Ejecuta: source $VENV_DIR/bin/activate && pip install celery redis"
    fi
else
    echo -e "${RED}❌ Entorno virtual NO existe${NC}"
fi

echo ""

# 6. Ver logs recientes
echo "6️⃣ Últimos logs de Celery (últimas 10 líneas):"
echo "----------------------------------------"
sudo journalctl -u celerycore.service -n 10 --no-pager 2>/dev/null || echo "No se pudieron obtener logs"
echo ""

# 7. Resumen y recomendaciones
echo "📋 Resumen y Recomendaciones"
echo "============================"
echo ""

if systemctl is-active --quiet redis-server || systemctl is-active --quiet redis; then
    if systemctl is-active --quiet celerycore.service; then
        echo -e "${GREEN}✅ Todo parece estar bien configurado${NC}"
        echo ""
        echo "Si las tareas siguen en PENDING, prueba:"
        echo "  1. Reiniciar Celery: sudo systemctl restart celerycore.service"
        echo "  2. Ver logs en tiempo real: sudo journalctl -u celerycore.service -f"
        echo "  3. Probar tarea manualmente desde Django shell"
    else
        echo -e "${YELLOW}⚠️ Celery Worker no está corriendo${NC}"
        echo "   Ejecuta: sudo systemctl start celerycore.service"
    fi
else
    echo -e "${RED}❌ Redis no está corriendo${NC}"
    echo "   Ejecuta: sudo systemctl start redis-server"
fi

echo ""
echo "✅ Diagnóstico completado"


