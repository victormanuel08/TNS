#!/bin/bash
# Script para recrear el archivo .env en UTF-8

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔄 Recreando archivo .env en UTF-8...${NC}"

# 1. Hacer backup del .env actual si existe
if [ -f .env ]; then
    BACKUP_NAME=".env.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}📦 Haciendo backup del .env actual a: ${BACKUP_NAME}${NC}"
    cp .env "$BACKUP_NAME"
    echo -e "${GREEN}✅ Backup creado: ${BACKUP_NAME}${NC}"
else
    echo -e "${YELLOW}⚠️  No existe archivo .env, se creará uno nuevo${NC}"
fi

# 2. Borrar el .env actual
if [ -f .env ]; then
    rm .env
    echo -e "${GREEN}✅ Archivo .env borrado${NC}"
fi

# 3. Crear nuevo .env vacío en UTF-8
echo -e "${YELLOW}📝 Creando nuevo archivo .env en UTF-8...${NC}"
touch .env
# Forzar codificación UTF-8
echo "# Archivo de configuración de entorno" > .env
echo "# Codificación: UTF-8" >> .env
echo "" >> .env

# Verificar que se creó correctamente
if [ -f .env ]; then
    # Verificar codificación
    FILE_ENCODING=$(file -bi .env | awk -F'=' '{print $2}')
    echo -e "${GREEN}✅ Archivo .env creado exitosamente${NC}"
    echo -e "${GREEN}📋 Codificación: ${FILE_ENCODING}${NC}"
    echo -e "${YELLOW}⚠️  Recuerda agregar tus variables de entorno al archivo .env${NC}"
else
    echo -e "${RED}❌ Error al crear el archivo .env${NC}"
    exit 1
fi

echo -e "${GREEN}✨ Proceso completado${NC}"

