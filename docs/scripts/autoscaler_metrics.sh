#!/bin/bash
# Script para obtener métricas del sistema (CPU, memoria, cola Celery)
# Uso: ./autoscaler_metrics.sh [cpu|memory|celery_queue]

set -e

METRIC_TYPE="${1:-all}"

# Función para obtener CPU promedio (último minuto)
get_cpu_usage() {
    # Obtener load average (1 minuto) y convertir a porcentaje
    # load average / número de cores * 100
    local cores=$(nproc)
    local load_1min=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    local cpu_percent=$(echo "scale=2; ($load_1min / $cores) * 100" | bc)
    
    # También obtener CPU real con top (más preciso)
    local cpu_real=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    
    # Usar el mayor de los dos
    if (( $(echo "$cpu_real > $cpu_percent" | bc -l) )); then
        echo "$cpu_real"
    else
        echo "$cpu_percent"
    fi
}

# Función para obtener memoria disponible (MB)
get_memory_available() {
    free -m | awk '/^Mem:/ {print $7}'
}

# Función para obtener memoria total (MB)
get_memory_total() {
    free -m | awk '/^Mem:/ {print $2}'
}

# Función para obtener porcentaje de memoria usada
get_memory_usage_percent() {
    local total=$(get_memory_total)
    local used=$(free -m | awk '/^Mem:/ {print $3}')
    echo "scale=2; ($used / $total) * 100" | bc
}

# Función para obtener tamaño de cola Celery
get_celery_queue_size() {
    local redis_url="${1:-redis://localhost:6379/0}"
    
    # Extraer host y puerto de redis_url
    local redis_host=$(echo "$redis_url" | sed -n 's/redis:\/\/\([^:]*\):.*/\1/p')
    local redis_port=$(echo "$redis_url" | sed -n 's/redis:\/\/[^:]*:\([0-9]*\).*/\1/p')
    local redis_db=$(echo "$redis_url" | sed -n 's/.*\/\([0-9]*\)$/\1/p')
    
    if [ -z "$redis_host" ]; then
        redis_host="localhost"
    fi
    if [ -z "$redis_port" ]; then
        redis_port="6379"
    fi
    if [ -z "$redis_db" ]; then
        redis_db="0"
    fi
    
    # Obtener tamaño de cola desde Redis
    # Celery usa claves como "celery" para la cola por defecto
    local queue_size=$(redis-cli -h "$redis_host" -p "$redis_port" -n "$redis_db" LLEN celery 2>/dev/null || echo "0")
    
    # Si no hay cola "celery", intentar otras colas comunes
    if [ "$queue_size" = "0" ] || [ -z "$queue_size" ]; then
        # Intentar obtener todas las colas
        queue_size=$(redis-cli -h "$redis_host" -p "$redis_port" -n "$redis_db" KEYS "*celery*" 2>/dev/null | wc -l)
    fi
    
    echo "${queue_size:-0}"
}

# Función para obtener número de workers actuales de un servicio
get_current_workers() {
    local service_name="$1"
    
    # Obtener PID del proceso principal
    local main_pid=$(systemctl show -p MainPID "$service_name" 2>/dev/null | cut -d= -f2)
    
    if [ -z "$main_pid" ] || [ "$main_pid" = "0" ]; then
        echo "0"
        return
    fi
    
    # Contar procesos hijos (workers) del proceso principal
    local workers=$(pgrep -P "$main_pid" 2>/dev/null | wc -l)
    
    # Si no hay procesos hijos, el servicio podría estar usando prefork de otra manera
    # Intentar contar procesos gunicorn/celery relacionados
    if [ "$workers" = "0" ]; then
        # Para gunicorn, buscar procesos que contengan el nombre del servicio
        if [[ "$service_name" == *"back"* ]]; then
            workers=$(ps aux | grep -E "gunicorn.*$(echo $service_name | sed 's/\.service//')" | grep -v grep | wc -l)
            # Restar 1 por el proceso principal
            workers=$((workers - 1))
        fi
    fi
    
    # Si sigue siendo 0, intentar leer del archivo de estado
    if [ "$workers" = "0" ] || [ -z "$workers" ]; then
        local state_file="/tmp/autoscaler_state.json"
        if [ -f "$state_file" ]; then
            workers=$(jq -r ".projects.\"$service_name\".current_workers // 1" "$state_file" 2>/dev/null || echo "1")
        else
            workers=1
        fi
    fi
    
    echo "${workers:-1}"
}

# Salida según tipo de métrica solicitada
case "$METRIC_TYPE" in
    cpu)
        get_cpu_usage
        ;;
    memory)
        get_memory_available
        ;;
    memory_percent)
        get_memory_usage_percent
        ;;
    celery_queue)
        get_celery_queue_size "${2:-redis://localhost:6379/0}"
        ;;
    workers)
        get_current_workers "${2}"
        ;;
    all)
        echo "CPU=$(get_cpu_usage)"
        echo "MEMORY_AVAILABLE=$(get_memory_available)"
        echo "MEMORY_TOTAL=$(get_memory_total)"
        echo "MEMORY_PERCENT=$(get_memory_usage_percent)"
        ;;
    *)
        echo "Uso: $0 [cpu|memory|memory_percent|celery_queue|workers|all] [arg_adicional]"
        exit 1
        ;;
esac

