# 🚀 Guía Rápida VPS - Autoescalador

## 📦 Archivos a Subir al VPS

### **Archivos necesarios:**

```
docs/scripts/
├── autoscaler.sh              ← Subir
├── autoscaler_metrics.sh      ← Subir
├── autoscaler_config.json     ← Subir
└── install_autoscaler.sh      ← Subir
```

### **Dónde ponerlos en el VPS:**

```
/home/victus/scripts/
├── autoscaler.sh
├── autoscaler_metrics.sh
├── autoscaler_config.json
└── install_autoscaler.sh
```

---

## 📤 Cómo Subir los Archivos

### **Opción 1: SCP (desde tu máquina Windows)**

```powershell
# Desde PowerShell en tu máquina local
scp docs/scripts/autoscaler.sh victus@tu-servidor:/home/victus/scripts/
scp docs/scripts/autoscaler_metrics.sh victus@tu-servidor:/home/victus/scripts/
scp docs/scripts/autoscaler_config.json victus@tu-servidor:/home/victus/scripts/
scp docs/scripts/install_autoscaler.sh victus@tu-servidor:/home/victus/scripts/
```

### **Opción 2: WinSCP (interfaz gráfica)**

1. Conectar a tu servidor con WinSCP
2. Navegar a `/home/victus/scripts/` (crear si no existe)
3. Arrastrar los 4 archivos desde `docs/scripts/` a `/home/victus/scripts/`

### **Opción 3: Crear directorio y copiar manualmente**

```bash
# En el VPS
mkdir -p /home/victus/scripts
# Luego copiar los archivos manualmente (nano, vim, etc.)
```

---

## ⚡ Comandos a Ejecutar en el VPS

### **1. Conectarse al VPS**

```bash
ssh victus@tu-servidor
```

### **2. Verificar que los archivos están ahí**

```bash
ls -la /home/victus/scripts/
# Debe mostrar los 4 archivos
```

### **3. Ejecutar el instalador (TODO AUTOMÁTICO)**

```bash
sudo bash /home/victus/scripts/install_autoscaler.sh
```

**Eso es todo. El script hace:**
- ✅ Copia scripts
- ✅ Instala dependencias
- ✅ Crea servicio systemd
- ✅ Modifica servicios a 1 worker base
- ✅ Crea backups automáticos
- ✅ Reinicia servicios
- ✅ Inicia autoescalador

### **4. Verificar que funciona**

```bash
# Ver estado del autoescalador
sudo systemctl status autoscaler.timer

# Ver logs en tiempo real
sudo journalctl -u autoscaler -f

# Ver workers actuales (deben estar en 1)
ps aux | grep gunicorn | grep -v grep
```

---

## 🔄 Rollback (Si Algo Sale Mal)

### **El instalador crea backups automáticamente:**

Los backups se guardan en:
```
/etc/systemd/system/backregisters.service.backup.YYYYMMDD_HHMMSS
/etc/systemd/system/backdipro.service.backup.YYYYMMDD_HHMMSS
/etc/systemd/system/backglobal.service.backup.YYYYMMDD_HHMMSS
/etc/systemd/system/backbce.service.backup.YYYYMMDD_HHMMSS
/etc/systemd/system/backcore.service.backup.YYYYMMDD_HHMMSS
/etc/systemd/system/celerycore.service.backup.YYYYMMDD_HHMMSS
```

### **Comando de Rollback:**

```bash
# 1. Detener autoescalador
sudo systemctl stop autoscaler.timer
sudo systemctl disable autoscaler.timer

# 2. Restaurar servicios desde backups
# Encontrar el backup más reciente
ls -lt /etc/systemd/system/*.backup.* | head -6

# Restaurar cada servicio (ejemplo con backregisters)
sudo cp /etc/systemd/system/backregisters.service.backup.* /etc/systemd/system/backregisters.service
# Repetir para todos los servicios

# 3. Recargar y reiniciar
sudo systemctl daemon-reload
sudo systemctl restart backcore backbce backglobal backregisters backdipro celerycore

# 4. Verificar
systemctl status backcore backbce backglobal backregisters backdipro celerycore
```

### **Script de Rollback Automático:**

```bash
# Crear script de rollback
cat > /home/victus/scripts/rollback_autoscaler.sh << 'EOF'
#!/bin/bash
# Script de rollback automático

echo "🔄 Restaurando servicios desde backups..."

# Detener autoescalador
systemctl stop autoscaler.timer
systemctl disable autoscaler.timer

# Encontrar y restaurar backups más recientes
for service in backregisters backdipro backglobal backbce backcore celerycore; do
    backup=$(ls -t /etc/systemd/system/${service}.service.backup.* 2>/dev/null | head -1)
    if [ -n "$backup" ]; then
        echo "Restaurando $service desde $backup"
        cp "$backup" /etc/systemd/system/${service}.service
    fi
done

# Recargar y reiniciar
systemctl daemon-reload
systemctl restart backcore backbce backglobal backregisters backdipro celerycore

echo "✅ Rollback completado"
EOF

chmod +x /home/victus/scripts/rollback_autoscaler.sh
```

**Usar rollback:**
```bash
sudo bash /home/victus/scripts/rollback_autoscaler.sh
```

---

## 📋 Checklist Completo

### **Antes de ejecutar:**

- [ ] Archivos subidos a `/home/victus/scripts/`
- [ ] Tienes acceso SSH al servidor
- [ ] Tienes permisos sudo

### **Ejecutar:**

- [ ] `sudo bash /home/victus/scripts/install_autoscaler.sh`

### **Verificar:**

- [ ] Autoescalador activo: `sudo systemctl status autoscaler.timer`
- [ ] Servicios funcionando: `systemctl status backcore backbce backglobal backregisters backdipro celerycore`
- [ ] Workers en 1: `ps aux | grep gunicorn | grep -v grep | wc -l`
- [ ] Logs sin errores: `sudo journalctl -u autoscaler -n 50`

---

## 🎯 Resumen Ultra Rápido

```bash
# 1. Subir 4 archivos a /home/victus/scripts/
# 2. Ejecutar:
sudo bash /home/victus/scripts/install_autoscaler.sh

# 3. Listo! ✅
```

---

## 📞 Si Algo Sale Mal

### **Ver logs:**
```bash
sudo journalctl -u autoscaler -n 100
sudo journalctl -u backcore -n 50
```

### **Verificar servicios:**
```bash
systemctl status backcore backbce backglobal backregisters backdipro celerycore
```

### **Rollback:**
```bash
sudo bash /home/victus/scripts/rollback_autoscaler.sh
```

---

## ✅ Todo Listo

**Solo necesitas:**
1. Subir 4 archivos
2. Ejecutar 1 comando
3. El resto es automático

**El instalador:**
- ✅ Crea backups automáticos
- ✅ Modifica servicios automáticamente
- ✅ Inicia autoescalador automáticamente
- ✅ Todo listo para usar

