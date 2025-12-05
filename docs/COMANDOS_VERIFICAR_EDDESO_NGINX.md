# Comandos para Verificar Configuración de Eddeso en Nginx

## 🔍 Comandos para Encontrar la Configuración de Eddeso

### 1. Buscar archivos que mencionen "eddeso.com"

```bash
# Buscar en sites-available
sudo grep -r "eddeso.com" /etc/nginx/sites-available/

# Buscar en sites-enabled
sudo grep -r "eddeso.com" /etc/nginx/sites-enabled/

# Buscar en toda la configuración de Nginx
sudo nginx -T | grep -i "eddeso"
```

### 2. Buscar archivos que apunten al puerto 3006 (Eddeso)

```bash
# Buscar proxy_pass al puerto 3006
sudo grep -r "proxy_pass.*3006" /etc/nginx/sites-available/

# Ver el archivo completo
sudo grep -l "proxy_pass.*3006" /etc/nginx/sites-available/ | xargs -I {} sudo cat {}
```

### 3. Ver todos los server_name configurados

```bash
# Ver todos los server_name en sites-available
sudo grep -r "server_name" /etc/nginx/sites-available/ | grep -v "#"

# Ver en formato más legible
sudo nginx -T | grep "server_name" | sort
```

### 4. Ver qué archivo maneja eddeso.com específicamente

```bash
# Ver configuración completa de eddeso.com
sudo nginx -T | grep -B 10 -A 20 "server_name.*eddeso.com"

# Ver solo el nombre del archivo
sudo nginx -T | grep -B 50 "server_name.*eddeso.com" | grep -E "^# configuration file" | tail -1
```

### 5. Listar todos los archivos de configuración

```bash
# Ver archivos en sites-available
ls -la /etc/nginx/sites-available/

# Ver archivos en sites-enabled (enlaces simbólicos)
ls -la /etc/nginx/sites-enabled/

# Ver solo nombres de archivos
ls -1 /etc/nginx/sites-available/ | sort
```

### 6. Buscar archivos que contengan "livecore" o nombres similares

```bash
# Buscar archivos con "live" en el nombre
ls -1 /etc/nginx/sites-available/ | grep -i "live"

# Ver contenido de esos archivos
for file in /etc/nginx/sites-available/*live*; do
    echo "=== $file ==="
    sudo cat "$file"
    echo ""
done
```

## 📋 Script Completo de Verificación

Copia y pega este script:

```bash
#!/bin/bash
echo "=========================================="
echo "🔍 VERIFICACIÓN DE CONFIGURACIÓN EDDESO"
echo "=========================================="
echo ""

echo "1️⃣ ARCHIVOS QUE MENCIONAN 'eddeso.com':"
echo "----------------------------------------"
sudo grep -r "eddeso.com" /etc/nginx/sites-available/ 2>/dev/null | head -20
echo ""

echo "2️⃣ ARCHIVOS QUE APUNTAN AL PUERTO 3006:"
echo "----------------------------------------"
sudo grep -r "proxy_pass.*3006" /etc/nginx/sites-available/ 2>/dev/null
echo ""

echo "3️⃣ ARCHIVOS EN sites-available:"
echo "--------------------------------"
ls -1 /etc/nginx/sites-available/ | sort
echo ""

echo "4️⃣ CONFIGURACIÓN DE eddeso.com EN NGINX:"
echo "----------------------------------------"
sudo nginx -T 2>/dev/null | grep -B 10 -A 20 "server_name.*eddeso.com" | head -40
echo ""

echo "5️⃣ ARCHIVO QUE CONTIENE eddeso.com:"
echo "------------------------------------"
EDDESO_FILE=$(sudo grep -r "server_name.*eddeso.com" /etc/nginx/sites-available/ 2>/dev/null | cut -d: -f1 | head -1)
if [ ! -z "$EDDESO_FILE" ]; then
    echo "Archivo: $EDDESO_FILE"
    echo ""
    echo "Contenido completo:"
    sudo cat "$EDDESO_FILE"
else
    echo "⚠️  No se encontró archivo con eddeso.com"
fi
echo ""

echo "=========================================="
```

Guarda y ejecuta:

```bash
cat > verify_eddeso_nginx.sh << 'EOF'
#!/bin/bash
echo "=========================================="
echo "🔍 VERIFICACIÓN DE CONFIGURACIÓN EDDESO"
echo "=========================================="
echo ""

echo "1️⃣ ARCHIVOS QUE MENCIONAN 'eddeso.com':"
echo "----------------------------------------"
sudo grep -r "eddeso.com" /etc/nginx/sites-available/ 2>/dev/null | head -20
echo ""

echo "2️⃣ ARCHIVOS QUE APUNTAN AL PUERTO 3006:"
echo "----------------------------------------"
sudo grep -r "proxy_pass.*3006" /etc/nginx/sites-available/ 2>/dev/null
echo ""

echo "3️⃣ ARCHIVOS EN sites-available:"
echo "--------------------------------"
ls -1 /etc/nginx/sites-available/ | sort
echo ""

echo "4️⃣ CONFIGURACIÓN DE eddeso.com EN NGINX:"
echo "----------------------------------------"
sudo nginx -T 2>/dev/null | grep -B 10 -A 20 "server_name.*eddeso.com" | head -40
echo ""

echo "5️⃣ ARCHIVO QUE CONTIENE eddeso.com:"
echo "------------------------------------"
EDDESO_FILE=$(sudo grep -r "server_name.*eddeso.com" /etc/nginx/sites-available/ 2>/dev/null | cut -d: -f1 | head -1)
if [ ! -z "$EDDESO_FILE" ]; then
    echo "Archivo: $EDDESO_FILE"
    echo ""
    echo "Contenido completo:"
    sudo cat "$EDDESO_FILE"
else
    echo "⚠️  No se encontró archivo con eddeso.com"
fi
echo ""

echo "=========================================="
EOF

chmod +x verify_eddeso_nginx.sh
./verify_eddeso_nginx.sh
```

## 🎯 Resultado Esperado

Después de ejecutar, deberías ver:
- El nombre del archivo que contiene la configuración de eddeso.com
- El contenido completo de ese archivo
- Qué `server_name` tiene configurado
- Si tiene wildcards como `*.eddeso.com`

Con esta información, el script de generación sabrá qué archivo excluir para no duplicar configuraciones.

