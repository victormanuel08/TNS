#!/bin/bash
# Script principal de autoescalado para workers Gunicorn y Celery
# Ejecuta cada 2 minutos vía systemd timer

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Rutas
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/autoscaler_config.json"
STATE_FILE="/tmp/autoscaler_state.json"
LOG_FILE="/var/log/autoscaler.log"
METRICS_SCRIPT="${SCRIPT_DIR}/autoscaler_metrics.sh"

# Función de logging
log() {
    local level="$1"
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_error() {
    log "ERROR" "$@"
}

# Verificar que los archivos necesarios existan
if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Archivo de configuración no encontrado: $CONFIG_FILE"
    exit 1
fi

if [ ! -f "$METRICS_SCRIPT" ]; then
    log_error "Script de métricas no encontrado: $METRICS_SCRIPT"
    exit 1
fi

# Hacer ejecutable el script de métricas
chmod +x "$METRICS_SCRIPT" 2>/dev/null || true

# Cargar configuración
if ! command -v jq &> /dev/null; then
    log_error "jq no está instalado. Instalar con: sudo apt-get install jq"
    exit 1
fi

# Inicializar archivo de estado si no existe
if [ ! -f "$STATE_FILE" ]; then
    echo '{"projects": {}}' > "$STATE_FILE"
fi

# Obtener métricas del sistema
get_system_metrics() {
    local cpu=$(bash "$METRICS_SCRIPT" cpu)
    local memory_available=$(bash "$METRICS_SCRIPT" memory)
    local memory_percent=$(bash "$METRICS_SCRIPT" memory_percent)
    
    echo "$cpu|$memory_available|$memory_percent"
}

# Obtener tamaño de cola Celery
get_celery_queue() {
    local redis_url="$1"
    bash "$METRICS_SCRIPT" celery_queue "$redis_url"
}

# Obtener workers actuales de un servicio
get_service_workers() {
    local service_name="$1"
    bash "$METRICS_SCRIPT" workers "$service_name"
}

# Calcular límite de memoria por worker según recursos disponibles
# Optimizado para VPS con 18GB RAM
calculate_memory_limit_per_worker() {
    local total_memory_mb=$(free -m | awk '/^Mem:/ {print $2}')
    local available_memory_mb=$(free -m | awk '/^Mem:/ {print $7}')
    local num_workers=$1
    
    # Memoria base del sistema (reservar 3GB para sistema, PostgreSQL, Redis, etc.)
    local system_reserved_mb=3072
    local usable_memory_mb=$((total_memory_mb - system_reserved_mb))
    
    # Aprovechar mejor la memoria disponible según el tamaño total del VPS
    if [ "$total_memory_mb" -gt 16000 ]; then
        # VPS grande (18GB+): Aprovechar al máximo, hasta 1.5GB por worker
        # Esto permite manejar respuestas grandes de DeepSeek sin problemas
        local max_per_worker=1536
        system_reserved_mb=3072  # 3GB para sistema
    elif [ "$total_memory_mb" -gt 12000 ]; then
        # VPS mediano-grande (12-16GB): hasta 1GB por worker
        local max_per_worker=1024
        system_reserved_mb=2048  # 2GB para sistema
    elif [ "$total_memory_mb" -gt 8000 ]; then
        # VPS mediano (8-12GB): hasta 800MB por worker
        local max_per_worker=800
        system_reserved_mb=2048
    elif [ "$total_memory_mb" -gt 4000 ]; then
        # VPS pequeño-mediano (4-8GB): hasta 500MB por worker
        local max_per_worker=500
        system_reserved_mb=1536  # 1.5GB para sistema
    elif [ "$total_memory_mb" -gt 2000 ]; then
        # VPS pequeño (2-4GB): hasta 300MB por worker
        local max_per_worker=300
        system_reserved_mb=1024  # 1GB para sistema
    else
        # VPS muy pequeño (<2GB): hasta 200MB por worker
        local max_per_worker=200
        system_reserved_mb=512
    fi
    
    # Recalcular memoria usable con el nuevo reservado
    usable_memory_mb=$((total_memory_mb - system_reserved_mb))
    
    # Calcular límite total para todos los workers
    # Usar 70% de la memoria usable para workers (dejar 30% de margen)
    local total_worker_memory=$((usable_memory_mb * 70 / 100))
    
    # Calcular límite por worker
    local limit_per_worker=$((total_worker_memory / num_workers))
    
    # Aplicar límites: mínimo 200MB, máximo según recursos
    if [ "$limit_per_worker" -lt 200 ]; then
        limit_per_worker=200
    fi
    if [ "$limit_per_worker" -gt "$max_per_worker" ]; then
        limit_per_worker=$max_per_worker
    fi
    
    # Para backcore (clasificaciones pesadas), permitir más memoria si hay recursos
    if [ "$total_memory_mb" -gt 16000 ] && [ "$limit_per_worker" -lt 1024 ]; then
        # Con 18GB, permitir hasta 1GB por worker para backcore
        limit_per_worker=1024
    fi
    
    echo "${limit_per_worker}M"
}

# Actualizar workers de un servicio Gunicorn
update_gunicorn_workers() {
    local project_name="$1"
    local new_workers="$2"
    local config=$(jq -r ".projects.\"$project_name\"" "$CONFIG_FILE")
    
    if [ "$config" = "null" ]; then
        log_error "Proyecto no encontrado en configuración: $project_name"
        return 1
    fi
    
    local service_name=$(echo "$config" | jq -r '.service_name')
    local socket_path=$(echo "$config" | jq -r '.socket_path')
    local working_dir=$(echo "$config" | jq -r '.working_dir')
    local venv_path=$(echo "$config" | jq -r '.venv_path')
    local wsgi_module=$(echo "$config" | jq -r '.wsgi_module')
    local extra_args=$(echo "$config" | jq -r '.extra_args // ""')
    
    # Obtener workers actuales
    local current_workers=$(get_service_workers "$service_name")
    
    if [ "$current_workers" = "$new_workers" ]; then
        return 0  # Ya tiene el número correcto
    fi
    
    log_info "Escalando $service_name: $current_workers -> $new_workers workers"
    
    # Calcular límite de memoria por worker según recursos disponibles
    local memory_limit=$(calculate_memory_limit_per_worker "$new_workers")
    log_info "📊 Límite de memoria por worker: $memory_limit"
    
    # Crear nuevo archivo de servicio temporal
    local service_file="/etc/systemd/system/$service_name"
    local temp_service_file="/tmp/${service_name}.tmp"
    
    # Leer servicio actual y modificar workers
    sudo cp "$service_file" "$temp_service_file"
    
    # Modificar número de workers en el archivo
    sudo sed -i "s/--workers [0-9]*/--workers $new_workers/g" "$temp_service_file"
    
    # Agregar o actualizar límite de memoria en systemd
    # Si ya existe MemoryLimit, actualizarlo; si no, agregarlo después de [Service]
    if grep -q "^MemoryLimit=" "$temp_service_file"; then
        sudo sed -i "s/^MemoryLimit=.*/MemoryLimit=$memory_limit/" "$temp_service_file"
    else
        # Agregar después de la línea [Service] o después de User/Group
        sudo sed -i "/^\[Service\]/a MemoryLimit=$memory_limit" "$temp_service_file"
    fi
    
    # Agregar también MemoryMax (límite absoluto)
    if grep -q "^MemoryMax=" "$temp_service_file"; then
        sudo sed -i "s/^MemoryMax=.*/MemoryMax=$memory_limit/" "$temp_service_file"
    else
        sudo sed -i "/^MemoryLimit=/a MemoryMax=$memory_limit" "$temp_service_file"
    fi
    
    # Aplicar cambios
    sudo cp "$temp_service_file" "$service_file"
    sudo systemctl daemon-reload
    
    # Reiniciar servicio
    if sudo systemctl restart "$service_name"; then
        log_info "✅ $service_name escalado a $new_workers workers (límite memoria: $memory_limit por worker)"
        
        # Actualizar estado
        local state=$(cat "$STATE_FILE")
        echo "$state" | jq ".projects.\"$service_name\".current_workers = $new_workers" > "$STATE_FILE"
        
        return 0
    else
        log_error "❌ Error al escalar $service_name"
        # Restaurar archivo original
        sudo systemctl daemon-reload
        return 1
    fi
}

# Actualizar workers de Celery
update_celery_workers() {
    local project_name="$1"
    local new_workers="$2"
    local config=$(jq -r ".projects.\"$project_name\"" "$CONFIG_FILE")
    
    if [ "$config" = "null" ]; then
        log_error "Proyecto no encontrado en configuración: $project_name"
        return 1
    fi
    
    local service_name=$(echo "$config" | jq -r '.service_name')
    local working_dir=$(echo "$config" | jq -r '.working_dir')
    local venv_path=$(echo "$config" | jq -r '.venv_path')
    
    # Obtener workers actuales
    local current_workers=$(get_service_workers "$service_name")
    
    if [ "$current_workers" = "$new_workers" ]; then
        return 0
    fi
    
    log_info "Escalando $service_name: $current_workers -> $new_workers workers"
    
    # Modificar servicio systemd
    local service_file="/etc/systemd/system/$service_name"
    local temp_service_file="/tmp/${service_name}.tmp"
    
    sudo cp "$service_file" "$temp_service_file"
    sudo sed -i "s/--concurrency=[0-9]*/--concurrency=$new_workers/g" "$temp_service_file"
    
    sudo cp "$temp_service_file" "$service_file"
    sudo systemctl daemon-reload
    
    if sudo systemctl restart "$service_name"; then
        log_info "✅ $service_name escalado a $new_workers workers"
        
        local state=$(cat "$STATE_FILE")
        echo "$state" | jq ".projects.\"$service_name\".current_workers = $new_workers" > "$STATE_FILE"
        
        return 0
    else
        log_error "❌ Error al escalar $service_name"
        sudo systemctl daemon-reload
        return 1
    fi
}

# Evaluar escalado para un proyecto Gunicorn
evaluate_gunicorn_scaling() {
    local project_name="$1"
    local config=$(jq -r ".projects.\"$project_name\"" "$CONFIG_FILE")
    
    if [ "$config" = "null" ] || [ "$(echo "$config" | jq -r '.enabled')" != "true" ]; then
        return 0  # Proyecto deshabilitado, saltar
    fi
    
    local service_name=$(echo "$config" | jq -r '.service_name')
    local min_workers=$(echo "$config" | jq -r '.min_workers')
    local max_workers=$(echo "$config" | jq -r '.max_workers')
    local current_workers=$(get_service_workers "$service_name")
    
    # Obtener métricas
    local metrics=$(get_system_metrics)
    local cpu=$(echo "$metrics" | cut -d'|' -f1)
    local memory_available=$(echo "$metrics" | cut -d'|' -f2)
    local memory_percent=$(echo "$metrics" | cut -d'|' -f3)
    
    # Obtener umbrales
    local cpu_thresholds=$(echo "$config" | jq -r '.cpu_thresholds')
    local memory_threshold=$(echo "$config" | jq -r '.memory_threshold_mb')
    local cpu_duration=$(echo "$config" | jq -r '.cpu_duration_minutes')
    
    # Determinar acción de escalado
    local action="none"
    local target_workers=$current_workers
    
    # Calcular memoria disponible por worker si escalamos
    local total_memory_mb=$(free -m | awk '/^Mem:/ {print $2}')
    local memory_per_worker_if_scale_up=$((memory_available / (current_workers + 1)))
    local memory_per_worker_current=$((memory_available / current_workers))
    
    # Con 18GB RAM, ajustar umbrales de memoria para escalado
    local min_memory_per_worker=200
    if [ "$total_memory_mb" -gt 16000 ]; then
        # Con 18GB, permitir escalar con más memoria disponible
        min_memory_per_worker=500  # Mínimo 500MB por worker para escalar
    elif [ "$total_memory_mb" -gt 8000 ]; then
        min_memory_per_worker=300
    fi
    
    # Calcular umbral de memoria para escalado hacia abajo
    local memory_threshold_for_scale_down=8000
    if [ "$total_memory_mb" -gt 16000 ]; then
        memory_threshold_for_scale_down=8000  # Con 18GB, reducir solo si hay >8GB libres
    elif [ "$total_memory_mb" -gt 8000 ]; then
        memory_threshold_for_scale_down=4000
    else
        memory_threshold_for_scale_down=3000
    fi
    
    # Escalar hacia arriba: CPU alta O memoria suficiente para más workers
    if (( $(echo "$cpu > $(echo "$cpu_thresholds" | jq -r ".scale_up_$((current_workers + 1)) // 100")" | bc -l) )) && [ "$current_workers" -lt "$max_workers" ]; then
        # Verificar que hay suficiente memoria para escalar
        if [ "$memory_per_worker_if_scale_up" -ge "$min_memory_per_worker" ]; then
            action="scale_up"
            target_workers=$((current_workers + 1))
        else
            log_info "⚠️  $service_name: CPU alta pero memoria insuficiente para escalar (${memory_per_worker_if_scale_up}MB por worker < ${min_memory_per_worker}MB mínimo)"
        fi
    # Escalar hacia abajo: CPU baja Y memoria suficiente para menos workers
    elif (( $(echo "$cpu < $(echo "$cpu_thresholds" | jq -r ".scale_down_$((current_workers - 1)) // 0")" | bc -l) )) && [ "$current_workers" -gt "$min_workers" ]; then
        action="scale_down"
        target_workers=$((current_workers - 1))
    fi
    
    # Escalar hacia abajo por memoria: si hay mucha memoria disponible, reducir workers
    # Con 18GB, solo reducir si hay más de 8GB libres y CPU baja
    if [ "$memory_available" -gt "$memory_threshold_for_scale_down" ] && [ "$current_workers" -gt "$min_workers" ] && (( $(echo "$cpu < 50" | bc -l) )) && [ "$action" = "none" ]; then
        action="scale_down"
        target_workers=$((current_workers - 1))
        log_info "📊 $service_name: Memoria abundante (${memory_available}MB) y CPU baja, reduciendo workers"
    fi
    
    if [ "$action" != "none" ] && [ "$target_workers" != "$current_workers" ]; then
        log_info "📊 $service_name: CPU=${cpu}% Mem=${memory_available}MB -> $action a $target_workers workers"
        update_gunicorn_workers "$project_name" "$target_workers"
    fi
}

# Evaluar escalado para Celery
evaluate_celery_scaling() {
    local project_name="$1"
    local config=$(jq -r ".projects.\"$project_name\"" "$CONFIG_FILE")
    
    if [ "$config" = "null" ] || [ "$(echo "$config" | jq -r '.enabled')" != "true" ]; then
        return 0
    fi
    
    local service_name=$(echo "$config" | jq -r '.service_name')
    local min_workers=$(echo "$config" | jq -r '.min_workers')
    local max_workers=$(echo "$config" | jq -r '.max_workers')
    local current_workers=$(get_service_workers "$service_name")
    local redis_url=$(echo "$config" | jq -r '.redis_url')
    
    # Obtener tamaño de cola
    local queue_size=$(get_celery_queue "$redis_url")
    local queue_thresholds=$(echo "$config" | jq -r '.queue_thresholds')
    
    local action="none"
    local target_workers=$current_workers
    
    # Escalar hacia arriba
    if [ "$queue_size" -gt "$(echo "$queue_thresholds" | jq -r ".scale_up_$((current_workers + 2)) // 1000")" ] && [ "$current_workers" -lt "$max_workers" ]; then
        action="scale_up"
        target_workers=$((current_workers + 2))
    # Escalar hacia abajo
    elif [ "$queue_size" -lt "$(echo "$queue_thresholds" | jq -r ".scale_down_$((current_workers - 2)) // 0")" ] && [ "$current_workers" -gt "$min_workers" ]; then
        action="scale_down"
        target_workers=$((current_workers - 2))
    fi
    
    if [ "$action" != "none" ] && [ "$target_workers" != "$current_workers" ]; then
        log_info "📊 $service_name: Cola=$queue_size -> $action a $target_workers workers"
        update_celery_workers "$project_name" "$target_workers"
    fi
}

# Función principal
main() {
    log_info "🔄 Iniciando ciclo de autoescalado"
    
    # Obtener métricas del sistema
    local metrics=$(get_system_metrics)
    local cpu=$(echo "$metrics" | cut -d'|' -f1)
    local memory_available=$(echo "$metrics" | cut -d'|' -f2)
    
    log_info "📊 Métricas: CPU=${cpu}% Memoria=${memory_available}MB disponible"
    
    # Evaluar cada proyecto habilitado
    local projects=$(jq -r '.projects | keys[]' "$CONFIG_FILE")
    
    for project in $projects; do
        local enabled=$(jq -r ".projects.\"$project\".enabled" "$CONFIG_FILE")
        
        if [ "$enabled" = "true" ]; then
            if [ "$project" = "celerycore" ]; then
                evaluate_celery_scaling "$project"
            else
                evaluate_gunicorn_scaling "$project"
            fi
        fi
    done
    
    log_info "✅ Ciclo de autoescalado completado"
}

# Ejecutar
main "$@"

