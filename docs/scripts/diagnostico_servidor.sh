#!/bin/bash
# Script de diagnóstico completo del servidor
# Uso: bash diagnostico_servidor.sh

echo "=========================================="
echo "🔍 DIAGNÓSTICO COMPLETO DEL SERVIDOR"
echo "=========================================="
echo ""

# 1. Información básica del sistema
echo "📊 1. INFORMACIÓN BÁSICA DEL SISTEMA"
echo "-----------------------------------"
echo "Fecha/Hora: $(date)"
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime)"
echo "Kernel: $(uname -r)"
echo "Distribución: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo ""

# 2. Memoria detallada
echo "💾 2. MEMORIA DETALLADA"
echo "-----------------------------------"
free -h
echo ""
echo "Top 10 procesos por uso de RAM:"
ps aux --sort=-%mem | head -11 | awk '{printf "%-10s %-6s %-6s %-6s %s\n", $1, $2, $3"%", $4"%", $11}'
echo ""

# 3. CPU detallada
echo "⚙️  3. CPU DETALLADA"
echo "-----------------------------------"
echo "Cores físicos: $(nproc)"
echo "Load Average: $(uptime | awk -F'load average:' '{print $2}')"
echo ""
echo "Top 10 procesos por uso de CPU:"
ps aux --sort=-%cpu | head -11 | awk '{printf "%-10s %-6s %-6s %-6s %s\n", $1, $2, $3"%", $4"%", $11}'
echo ""

# 4. Disco detallado
echo "💿 4. DISCO DETALLADO"
echo "-----------------------------------"
df -h
echo ""
echo "Top 10 directorios más grandes en /:"
du -h --max-depth=1 / 2>/dev/null | sort -rh | head -11
echo ""

# 5. Swap
echo "🔄 5. SWAP"
echo "-----------------------------------"
swapon --show
echo ""
echo "Uso de swap por proceso:"
for pid in $(pgrep -f .); do
    swap=$(grep VmSwap /proc/$pid/status 2>/dev/null | awk '{print $2}')
    if [ ! -z "$swap" ] && [ "$swap" -gt 0 ]; then
        name=$(ps -p $pid -o comm= 2>/dev/null)
        echo "PID $pid ($name): $(($swap / 1024)) MB"
    fi
done | head -10
echo ""

# 6. Servicios activos
echo "🔧 6. SERVICIOS ACTIVOS"
echo "-----------------------------------"
echo "Servicios systemd activos:"
systemctl list-units --type=service --state=running | head -20
echo ""

# 7. PM2 procesos
echo "🚀 7. PROCESOS PM2"
echo "-----------------------------------"
if command -v pm2 &> /dev/null; then
    pm2 list
    echo ""
    echo "Uso de memoria por proceso PM2:"
    pm2 list | tail -n +4 | awk '{print $4, $2}' | sort -rn | head -10
else
    echo "PM2 no está instalado"
fi
echo ""

# 8. Conexiones de red
echo "🌐 8. CONEXIONES DE RED"
echo "-----------------------------------"
echo "Conexiones activas:"
ss -tunap | head -20
echo ""
echo "Puertos en escucha:"
ss -tlnp | grep LISTEN
echo ""

# 9. Logs recientes (errores)
echo "📋 9. LOGS RECIENTES (ERRORES)"
echo "-----------------------------------"
echo "Últimos errores del sistema (últimas 20 líneas):"
journalctl -p err -n 20 --no-pager 2>/dev/null || tail -20 /var/log/syslog 2>/dev/null
echo ""

# 10. Uso de memoria por aplicación
echo "📱 10. USO DE MEMORIA POR APLICACIÓN"
echo "-----------------------------------"
echo "Docker (si está instalado):"
if command -v docker &> /dev/null; then
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | head -10
else
    echo "Docker no está instalado"
fi
echo ""

# 11. Recomendaciones
echo "💡 11. RECOMENDACIONES"
echo "-----------------------------------"
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
USED_RAM=$(free -g | awk '/^Mem:/{print $3}')
AVAIL_RAM=$(free -g | awk '/^Mem:/{print $7}')
SWAP_USED=$(free -g | awk '/^Swap:/{print $3}')

echo "RAM Total: ${TOTAL_RAM}GB"
echo "RAM Usada: ${USED_RAM}GB"
echo "RAM Disponible: ${AVAIL_RAM}GB"
echo "Swap Usado: ${SWAP_USED}GB"

if [ "$SWAP_USED" -gt 0 ]; then
    echo "⚠️  ADVERTENCIA: El swap está siendo usado. Considera aumentar RAM o optimizar procesos."
else
    echo "✅ Swap no está siendo usado (óptimo)"
fi

if [ "$AVAIL_RAM" -lt 2 ]; then
    echo "⚠️  ADVERTENCIA: Poca RAM disponible. Considera optimizar o aumentar RAM."
else
    echo "✅ RAM disponible suficiente"
fi

DISK_USE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USE" -gt 80 ]; then
    echo "⚠️  ADVERTENCIA: Disco casi lleno (${DISK_USE}%). Considera limpiar espacio."
else
    echo "✅ Espacio en disco suficiente (${DISK_USE}% usado)"
fi

echo ""
echo "=========================================="
echo "✅ Diagnóstico completado"
echo "=========================================="

