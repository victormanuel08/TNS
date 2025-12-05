# Comandos para Verificar Servicio y Puerto del Frontend

## 🔍 Paso 1: Identificar el Nombre del Servicio PM2

```bash
# Ver todos los procesos PM2
pm2 list

# Ver en formato JSON (más detallado)
pm2 jlist

# Ver solo los nombres de los procesos
pm2 jlist | jq -r '.[].name'

# Si no tienes jq, usar:
pm2 list --format json | python3 -m json.tool | grep '"name"'
```

**Ejemplo de salida esperada:**
```
┌─────┬─────────────┬─────────────┬─────────┬─────────┬──────────┐
│ id  │ name       │ mode        │ ↺       │ status  │ cpu     │
├─────┼────────────┼─────────────┼─────────┼─────────┼──────────┤
│ 0   │ livecore   │ cluster     │ 0       │ online  │ 0%      │
│ 1   │ api        │ fork        │ 0       │ online  │ 0%      │
└─────┴────────────┴─────────────┴─────────┴─────────┴──────────┘
```

**Comando para extraer solo el nombre del frontend:**
```bash
# Buscar procesos que contengan "live", "front", "nuxt", "eddeso"
pm2 list | grep -i "live\|front\|nuxt\|eddeso" | awk '{print $4}'

# O ver todos y elegir manualmente
pm2 list
```

---

## 🔍 Paso 2: Identificar el Puerto del Frontend

### Opción A: Desde PM2 (Recomendado)

```bash
# Ver información detallada del proceso (reemplaza "livecore" con el nombre real)
pm2 show livecore

# Ver el script que ejecuta PM2
pm2 describe livecore | grep "script path"

# Ver variables de entorno (puede contener PORT)
pm2 env livecore
```

### Opción B: Desde el Proceso en Ejecución

```bash
# Obtener el PID del proceso
PID=$(pm2 pid livecore)  # Reemplaza "livecore" con el nombre real

# Ver puertos abiertos por ese PID
sudo lsof -p $PID | grep LISTEN

# O usar netstat
sudo netstat -tlnp | grep $PID

# O usar ss
sudo ss -tlnp | grep $PID
```

### Opción C: Desde Nginx

```bash
# Ver todas las configuraciones de Nginx que apuntan a localhost
sudo grep -r "proxy_pass.*localhost" /etc/nginx/sites-enabled/

# Ver específicamente la configuración de livecore
sudo cat /etc/nginx/sites-available/livecore | grep proxy_pass

# Ver todas las configuraciones que mencionan puertos 300x
sudo grep -r "300[0-9]" /etc/nginx/sites-available/
```

### Opción D: Desde el Código

```bash
# Verificar en nuxt.config.ts
cd /home/victus/projects/CORE/front
cat nuxt.config.ts | grep -i "port\|300"

# Verificar en package.json
cat package.json | grep -A 5 -B 5 "start\|dev\|300"

# Verificar en .env (si existe)
cat .env 2>/dev/null | grep -i "port\|300" || echo "No hay archivo .env"
```

### Opción E: Desde el Proceso Node Directamente

```bash
# Ver todos los procesos Node y sus puertos
sudo netstat -tlnp | grep node

# O con ss
sudo ss -tlnp | grep node

# Ver solo los puertos en escucha
sudo netstat -tlnp | grep node | awk '{print $4}' | awk -F: '{print $NF}'
```

---

## 🔍 Paso 3: Verificar el Puerto en Uso

```bash
# Ver qué proceso está usando el puerto 3001
sudo lsof -i :3001

# O con netstat
sudo netstat -tlnp | grep :3001

# O con ss
sudo ss -tlnp | grep :3001

# Probar otros puertos comunes
for port in 3000 3001 3002 3003; do
  echo "Puerto $port:"
  sudo lsof -i :$port || echo "  No en uso"
done
```

---

## 🔍 Paso 4: Script de Verificación Completa

Crea este script y ejecútalo:

```bash
#!/bin/bash
# verify_service_port.sh

echo "=========================================="
echo "🔍 VERIFICACIÓN DE SERVICIO Y PUERTO"
echo "=========================================="
echo ""

# 1. Procesos PM2
echo "1️⃣ PROCESOS PM2:"
echo "----------------"
pm2 list
echo ""

# 2. Buscar proceso del frontend
echo "2️⃣ BUSCANDO PROCESO DEL FRONTEND:"
echo "----------------------------------"
FRONTEND_PROCESS=$(pm2 list | grep -i "live\|front\|nuxt\|eddeso" | head -1 | awk '{print $4}')
if [ -z "$FRONTEND_PROCESS" ]; then
    echo "⚠️  No se encontró proceso con nombres comunes"
    echo "   Por favor, identifica manualmente el proceso del frontend:"
    pm2 list
    read -p "   Ingresa el nombre del proceso: " FRONTEND_PROCESS
else
    echo "✅ Proceso encontrado: $FRONTEND_PROCESS"
fi
echo ""

# 3. Información detallada del proceso
if [ ! -z "$FRONTEND_PROCESS" ]; then
    echo "3️⃣ INFORMACIÓN DETALLADA DE '$FRONTEND_PROCESS':"
    echo "------------------------------------------------"
    pm2 show $FRONTEND_PROCESS
    echo ""
    
    # 4. Variables de entorno
    echo "4️⃣ VARIABLES DE ENTORNO:"
    echo "------------------------"
    pm2 env $FRONTEND_PROCESS | grep -i "port\|300" || echo "   No se encontró PORT en variables de entorno"
    echo ""
fi

# 5. Puertos abiertos por Node
echo "5️⃣ PUERTOS ABIERTOS POR PROCESOS NODE:"
echo "---------------------------------------"
sudo netstat -tlnp 2>/dev/null | grep node || sudo ss -tlnp | grep node
echo ""

# 6. Configuración de Nginx
echo "6️⃣ CONFIGURACIÓN DE NGINX (proxy_pass):"
echo "---------------------------------------"
sudo grep -r "proxy_pass.*localhost" /etc/nginx/sites-enabled/ 2>/dev/null | grep -v "#"
echo ""

# 7. Código del frontend
echo "7️⃣ PUERTO EN CÓDIGO DEL FRONTEND:"
echo "----------------------------------"
if [ -f "/home/victus/projects/CORE/front/nuxt.config.ts" ]; then
    echo "   nuxt.config.ts:"
    grep -i "port\|300" /home/victus/projects/CORE/front/nuxt.config.ts | head -5
else
    echo "   ⚠️  Archivo nuxt.config.ts no encontrado"
fi

if [ -f "/home/victus/projects/CORE/front/package.json" ]; then
    echo ""
    echo "   package.json:"
    grep -A 3 -B 3 "start\|dev" /home/victus/projects/CORE/front/package.json | grep -i "300" || echo "   No se encontró puerto 300x"
fi
echo ""

# 8. Resumen
echo "=========================================="
echo "📋 RESUMEN:"
echo "=========================================="
if [ ! -z "$FRONTEND_PROCESS" ]; then
    echo "   Nombre del servicio PM2: $FRONTEND_PROCESS"
else
    echo "   ⚠️  Nombre del servicio: NO IDENTIFICADO"
fi

# Intentar identificar el puerto
PORT=$(sudo netstat -tlnp 2>/dev/null | grep node | grep -oP ':\K[0-9]+' | head -1)
if [ -z "$PORT" ]; then
    PORT=$(sudo ss -tlnp 2>/dev/null | grep node | grep -oP ':\K[0-9]+' | head -1)
fi

if [ ! -z "$PORT" ]; then
    echo "   Puerto detectado: $PORT"
else
    echo "   ⚠️  Puerto: NO IDENTIFICADO (revisar manualmente)"
fi
echo ""
```

**Guarda y ejecuta:**

```bash
# Crear el script
nano verify_service_port.sh
# Pegar el contenido del script
# Guardar (Ctrl+O, Enter, Ctrl+X)

# Dar permisos
chmod +x verify_service_port.sh

# Ejecutar
./verify_service_port.sh
```

---

## 📝 Comandos Rápidos (Copia y Pega)

Ejecuta estos comandos uno por uno y comparte los resultados:

```bash
# 1. Ver procesos PM2
pm2 list

# 2. Ver información del proceso (reemplaza "livecore" si es diferente)
pm2 show livecore

# 3. Ver puertos abiertos por Node
sudo netstat -tlnp | grep node

# 4. Ver configuración de Nginx
sudo grep -r "proxy_pass.*localhost" /etc/nginx/sites-enabled/

# 5. Ver puerto en código
cd /home/victus/projects/CORE/front && cat nuxt.config.ts | grep -i port
```

---

## 🎯 Resultado Esperado

Después de ejecutar los comandos, deberías obtener:

1. **Nombre del servicio PM2**: Ejemplo: `livecore`, `frontend`, `nuxt`, etc.
2. **Puerto del frontend**: Ejemplo: `3001`, `3000`, `3002`, etc.

Con estos valores, podremos crear un script con valores fijos y reales.

