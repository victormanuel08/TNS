# 🔍 Comandos de Diagnóstico del Servidor

## 📊 Estado Actual del Servidor

- **RAM Total**: 17GB
- **RAM Usada**: 7.5GB
- **RAM Disponible**: 9.5GB
- **Swap**: 8GB (0% usado) ✅
- **Disco**: 358GB usado / 982GB total (39%) ✅

## ✅ Análisis del Swap

**El swap está perfectamente configurado:**
- 8GB de swap para 17GB de RAM es la proporción correcta (regla: swap = 50% de RAM)
- 0% de uso significa que no hay presión de memoria ✅
- **Recomendación**: Dejarlo como está, no necesita cambios

---

## 🔧 Comandos de Diagnóstico

### 1. **Ejecutar Script Completo de Diagnóstico**

```bash
# Subir el script al servidor y ejecutarlo
bash diagnostico_servidor.sh
```

O ejecutar comandos individuales:

---

### 2. **Memoria Detallada**

```bash
# Ver memoria completa
free -h

# Top 10 procesos que más RAM usan
ps aux --sort=-%mem | head -11

# Ver uso de memoria por proceso PM2
pm2 list
pm2 monit
```

---

### 3. **CPU Detallada**

```bash
# Ver carga del sistema
uptime
top -bn1 | head -20

# Top 10 procesos que más CPU usan
ps aux --sort=-%cpu | head -11

# Ver todos los cores
nproc
htop  # Si está instalado
```

---

### 4. **Disco Detallado**

```bash
# Ver uso de disco
df -h

# Ver los 10 directorios más grandes
du -h --max-depth=1 / | sort -rh | head -11

# Ver tamaño de directorios específicos
du -sh /var/log/*
du -sh /home/*
du -sh /opt/*
```

---

### 5. **Swap Detallado**

```bash
# Ver estado del swap
swapon --show
free -h | grep Swap

# Ver qué procesos están usando swap (si hay alguno)
for pid in $(pgrep -f .); do
    swap=$(grep VmSwap /proc/$pid/status 2>/dev/null | awk '{print $2}')
    if [ ! -z "$swap" ] && [ "$swap" -gt 0 ]; then
        name=$(ps -p $pid -o comm= 2>/dev/null)
        echo "PID $pid ($name): $(($swap / 1024)) MB"
    fi
done
```

---

### 6. **Servicios y Procesos**

```bash
# Ver servicios systemd activos
systemctl list-units --type=service --state=running | head -20

# Ver procesos PM2
pm2 list
pm2 monit

# Ver uso de recursos por PM2
pm2 list | tail -n +4 | awk '{print $4, $2}' | sort -rn

# Ver procesos de Node.js
ps aux | grep node
```

---

### 7. **Conexiones de Red**

```bash
# Ver conexiones activas
ss -tunap | head -20

# Ver puertos en escucha
ss -tlnp | grep LISTEN

# Ver conexiones por puerto
netstat -tulpn | grep LISTEN
```

---

### 8. **Logs y Errores**

```bash
# Últimos errores del sistema
journalctl -p err -n 50 --no-pager

# Logs de PM2
pm2 logs --lines 50

# Logs de aplicaciones específicas
tail -100 /var/log/nginx/error.log
tail -100 /var/log/nginx/access.log
```

---

### 9. **Docker (si está instalado)**

```bash
# Ver contenedores y uso de recursos
docker ps
docker stats --no-stream

# Ver uso de disco de Docker
docker system df
```

---

### 10. **Análisis de Rendimiento**

```bash
# Ver carga del sistema en tiempo real
watch -n 1 'free -h && echo "" && uptime'

# Ver procesos en tiempo real
top

# Ver I/O de disco
iostat -x 1 5

# Ver uso de red
iftop  # Si está instalado
```

---

## 💡 Recomendaciones Basadas en tu Estado Actual

### ✅ **Swap (8GB)**
- **Estado**: Perfecto, no necesita cambios
- **Razón**: 0% de uso significa que hay suficiente RAM
- **Acción**: Dejarlo como está

### ✅ **RAM (17GB)**
- **Estado**: Óptimo
- **Uso actual**: 7.5GB / 17GB (44%)
- **Disponible**: 9.5GB
- **Acción**: No necesita cambios

### ✅ **Disco (982GB)**
- **Estado**: Saludable
- **Uso actual**: 358GB / 982GB (39%)
- **Disponible**: 580GB
- **Acción**: Monitorear periódicamente

---

## 🎯 Comandos Rápidos de Monitoreo

```bash
# Dashboard rápido (todo en uno)
watch -n 2 'echo "=== MEMORIA ===" && free -h && echo "" && echo "=== CPU ===" && uptime && echo "" && echo "=== DISCO ===" && df -h / && echo "" && echo "=== TOP PROCESOS ===" && ps aux --sort=-%mem | head -6'

# Ver solo lo crítico
echo "RAM: $(free -h | awk '/^Mem:/{print $3"/"$2}') | Disco: $(df -h / | awk 'NR==2{print $3"/"$2" ("$5")}') | Load: $(uptime | awk -F'load average:' '{print $2}')"
```

---

## 📝 Notas Importantes

1. **Swap**: 8GB es perfecto para 17GB de RAM. No necesita cambios.

2. **RAM**: Con 9.5GB disponibles, el servidor tiene buen margen.

3. **Disco**: 39% de uso es saludable. Monitorear si supera 80%.

4. **Monitoreo continuo**: Considera instalar herramientas como:
   - `htop` (mejor que top)
   - `glances` (monitoreo completo)
   - `netdata` (dashboard web)

---

## 🚀 Próximos Pasos

1. Ejecutar los comandos de diagnóstico para identificar procesos que más recursos usan
2. Revisar logs para detectar posibles problemas
3. Optimizar procesos si es necesario
4. Configurar alertas si el uso supera umbrales (ej: RAM > 90%, Disco > 80%)

