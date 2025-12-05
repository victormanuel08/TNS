#!/bin/bash
# Script para generar configuraciones de Nginx con valores reales del servidor
# Basado en verificación manual del 2025-12-04

set -e

# ============================================
# CONFIGURACIÓN (VALORES REALES DEL SERVIDOR)
# ============================================
PM2_SERVICE_NAME="Eddeso"
FRONTEND_PORT="3006"
NGINX_DIR="/etc/nginx"
OUTPUT_DIR="/etc/nginx/sites-available"
PROJECT_DIR="/home/victus/projects/CORE/manu"
VENV_PATH="/home/victus/projects/CORE/manu/env"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================
# FUNCIONES
# ============================================

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Verificar que estamos en el directorio correcto
check_environment() {
    print_header "VERIFICANDO AMBIENTE"
    
    # Verificar que el proyecto existe
    if [ ! -d "$PROJECT_DIR" ]; then
        print_error "Directorio del proyecto no encontrado: $PROJECT_DIR"
        exit 1
    fi
    print_success "Directorio del proyecto: $PROJECT_DIR"
    
    # Verificar que el virtualenv existe
    if [ ! -d "$VENV_PATH" ]; then
        print_error "Virtualenv no encontrado: $VENV_PATH"
        exit 1
    fi
    print_success "Virtualenv encontrado: $VENV_PATH"
    
    # Verificar que PM2 tiene el servicio
    if ! pm2 describe "$PM2_SERVICE_NAME" > /dev/null 2>&1; then
        print_error "Servicio PM2 '$PM2_SERVICE_NAME' no encontrado"
        print_info "Ejecuta: pm2 list"
        exit 1
    fi
    print_success "Servicio PM2 encontrado: $PM2_SERVICE_NAME"
    
    # Verificar que el puerto está en uso
    if ! sudo netstat -tlnp 2>/dev/null | grep -q ":$FRONTEND_PORT" && ! sudo ss -tlnp 2>/dev/null | grep -q ":$FRONTEND_PORT"; then
        print_warning "Puerto $FRONTEND_PORT no parece estar en uso"
        print_info "Verifica con: sudo netstat -tlnp | grep $FRONTEND_PORT"
    else
        print_success "Puerto $FRONTEND_PORT está en uso"
    fi
    
    # Verificar permisos de Nginx
    if [ ! -w "$OUTPUT_DIR" ] && [ "$EUID" -ne 0 ]; then
        print_warning "No tienes permisos de escritura en $OUTPUT_DIR"
        print_info "Este script necesita ejecutarse con sudo"
        print_info "Ejecuta: sudo $0"
        exit 1
    fi
    print_success "Permisos de escritura verificados"
}

# Hacer backup de archivos que se van a modificar
backup_nginx_files() {
    print_header "CREANDO BACKUPS"
    
    BACKUP_DIR="$NGINX_DIR/sites-available/.backups"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_LIST_FILE="/tmp/nginx_backup_list_$TIMESTAMP.txt"
    
    # Crear directorio de backups
    if ! sudo mkdir -p "$BACKUP_DIR" 2>/dev/null; then
        print_error "No se pudo crear directorio de backups: $BACKUP_DIR"
        return 1
    fi
    
    print_info "Directorio de backups: $BACKUP_DIR"
    print_info "Timestamp: $TIMESTAMP"
    echo ""
    
    # Listar archivos que podrían modificarse (todos los de sites-available)
    FILES_TO_BACKUP=()
    
    # Buscar archivos que contengan proxy_pass al puerto del frontend (archivos del frontend)
    for file in "$NGINX_DIR/sites-available"/*; do
        if [ -f "$file" ] && ! [[ "$file" =~ \.backup$ ]] && ! [[ "$file" =~ ^\. ]]; then
            if sudo grep -q "proxy_pass.*localhost:$FRONTEND_PORT" "$file" 2>/dev/null; then
                FILES_TO_BACKUP+=("$file")
                print_info "Archivo a respaldar: $(basename "$file")"
            fi
        fi
    done
    
    # También respaldar cualquier archivo nuevo que se vaya a crear (ecommerce-*)
    # Esto lo haremos después de ver qué se va a crear
    
    # Hacer backup de archivos existentes
    BACKED_UP_FILES=()
    for file in "${FILES_TO_BACKUP[@]}"; do
        BACKUP_FILE="$BACKUP_DIR/$(basename "$file")_$TIMESTAMP.backup"
        if sudo cp "$file" "$BACKUP_FILE" 2>/dev/null; then
            BACKED_UP_FILES+=("$file|$BACKUP_FILE")
            print_success "Backup creado: $(basename "$file") → $(basename "$BACKUP_FILE")"
        else
            print_warning "No se pudo crear backup de: $(basename "$file")"
        fi
    done
    
    # Guardar lista de backups para reversión
    printf '%s\n' "${BACKED_UP_FILES[@]}" > "$BACKUP_LIST_FILE"
    echo "$BACKUP_LIST_FILE" > /tmp/nginx_backup_list_current.txt
    
    if [ ${#BACKED_UP_FILES[@]} -gt 0 ]; then
        print_success "Total de backups creados: ${#BACKED_UP_FILES[@]}"
        return 0
    else
        print_info "No hay archivos existentes para respaldar (se crearán nuevos)"
        return 0
    fi
}

# Revertir backups si algo falla
revert_backups() {
    print_header "REVIRTIENDO CAMBIOS"
    
    BACKUP_LIST_FILE="/tmp/nginx_backup_list_current.txt"
    
    if [ ! -f "$BACKUP_LIST_FILE" ]; then
        print_warning "No se encontró lista de backups para revertir"
        return 1
    fi
    
    BACKUP_LIST=$(cat "$BACKUP_LIST_FILE")
    if [ -z "$BACKUP_LIST" ]; then
        print_info "No hay backups para revertir"
        return 0
    fi
    
    REVERTED=0
    while IFS='|' read -r original backup; do
        if [ -f "$backup" ]; then
            if sudo cp "$backup" "$original" 2>/dev/null; then
                print_success "Revertido: $(basename "$original")"
                REVERTED=$((REVERTED + 1))
            else
                print_error "No se pudo revertir: $(basename "$original")"
            fi
        fi
    done <<< "$BACKUP_LIST"
    
    if [ $REVERTED -gt 0 ]; then
        print_success "Total de archivos revertidos: $REVERTED"
        return 0
    else
        print_warning "No se revirtió ningún archivo"
        return 1
    fi
}

# Ejecutar el comando Django
run_django_command() {
    print_header "GENERANDO CONFIGURACIONES DE NGINX"
    
    cd "$PROJECT_DIR"
    
    # Activar virtualenv
    source "$VENV_PATH/bin/activate"
    
    print_info "Ejecutando: python manage.py generar_configs_nginx_fixed --frontend-port $FRONTEND_PORT"
    echo ""
    
    # Ejecutar el comando
    if python manage.py generar_configs_nginx_fixed --frontend-port "$FRONTEND_PORT"; then
        print_success "Configuraciones generadas exitosamente"
        return 0
    else
        print_error "Error al generar configuraciones"
        return 1
    fi
}

# Verificar configuración de Nginx
verify_nginx_config() {
    print_header "VERIFICANDO CONFIGURACIÓN DE NGINX"
    
    OUTPUT=$(sudo nginx -t 2>&1)
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        print_success "Configuración de Nginx es válida"
        echo "$OUTPUT" | grep -i "successful\|test is successful" || true
        return 0
    else
        print_error "Error en configuración de Nginx"
        echo ""
        echo "$OUTPUT" | grep -i "error\|failed" | head -10
        echo ""
        print_warning "Se revertirán los cambios automáticamente"
        return 1
    fi
}

# Recargar Nginx
reload_nginx() {
    print_header "RECARGANDO NGINX"
    
    if sudo systemctl reload nginx; then
        print_success "Nginx recargado exitosamente"
        print_info "Los cambios ya están activos"
        return 0
    else
        print_error "Error al recargar Nginx"
        print_warning "Intenta manualmente: sudo systemctl reload nginx"
        return 1
    fi
}

# Verificar que el servicio PM2 está corriendo
verify_pm2_service() {
    print_header "VERIFICANDO SERVICIO PM2"
    
    if pm2 describe "$PM2_SERVICE_NAME" | grep -q "status.*online"; then
        print_success "Servicio PM2 '$PM2_SERVICE_NAME' está online"
        print_info "PM2 NO necesita reiniciarse"
        return 0
    else
        print_warning "Servicio PM2 '$PM2_SERVICE_NAME' no está online"
        print_info "Verifica con: pm2 list"
        return 1
    fi
}

# Mostrar resumen
show_summary() {
    print_header "RESUMEN"
    
    echo -e "Servicio PM2:     ${GREEN}$PM2_SERVICE_NAME${NC}"
    echo -e "Puerto Frontend:  ${GREEN}$FRONTEND_PORT${NC}"
    echo -e "Directorio Nginx: ${GREEN}$NGINX_DIR${NC}"
    echo ""
    
    # Contar configuraciones generadas
    CONFIG_COUNT=$(ls -1 "$OUTPUT_DIR"/ecommerce-* 2>/dev/null | wc -l)
    if [ "$CONFIG_COUNT" -gt 0 ]; then
        print_info "Configuraciones encontradas: $CONFIG_COUNT"
        echo ""
        echo "Últimas 5 configuraciones:"
        ls -1t "$OUTPUT_DIR"/ecommerce-* 2>/dev/null | head -5 | while read file; do
            echo "  - $(basename "$file")"
        done
    fi
}

# ============================================
# MAIN
# ============================================

main() {
    print_header "GENERADOR DE CONFIGURACIONES NGINX"
    echo -e "${BLUE}Servicio PM2: $PM2_SERVICE_NAME${NC}"
    echo -e "${BLUE}Puerto Frontend: $FRONTEND_PORT${NC}"
    echo ""
    
    # Verificar ambiente
    check_environment
    
    # Hacer backup ANTES de modificar
    if ! backup_nginx_files; then
        print_error "Falló la creación de backups"
        print_warning "No se continuará sin backups"
        exit 1
    fi
    
    # Ejecutar comando Django
    if ! run_django_command; then
        print_error "Falló la generación de configuraciones"
        print_warning "Los archivos originales no fueron modificados (solo se crearon backups)"
        exit 1
    fi
    
    # Verificar configuración de Nginx
    if ! verify_nginx_config; then
        print_error "La configuración de Nginx tiene errores"
        print_warning "Revirtiendo cambios automáticamente..."
        
        # Revertir backups
        if revert_backups; then
            print_success "Cambios revertidos exitosamente"
            print_info "Nginx está en su estado original"
        else
            print_error "Error al revertir cambios"
            print_warning "Revisa manualmente los backups en: $NGINX_DIR/sites-available/.backups/"
        fi
        
        exit 1
    fi
    
    # Recargar Nginx (solo si la verificación pasó)
    if ! reload_nginx; then
        print_error "No se pudo recargar Nginx"
        print_warning "Los cambios están aplicados pero Nginx no se recargó"
        print_info "Intenta manualmente: sudo systemctl reload nginx"
        exit 1
    fi
    
    # Verificar PM2 (solo informativo)
    verify_pm2_service
    
    # Mostrar resumen
    show_summary
    
    print_header "COMPLETADO"
    print_success "Todas las configuraciones se generaron y aplicaron correctamente"
    print_info "Backups guardados en: $NGINX_DIR/sites-available/.backups/"
    echo ""
}

# Ejecutar
main "$@"

