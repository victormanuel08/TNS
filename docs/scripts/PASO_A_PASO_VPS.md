# 🚀 Paso a Paso: Implementación en VPS

## 📋 Resumen

Este documento contiene los pasos exactos a ejecutar en el VPS para:
1. ✅ Optimización de código (ya aplicada en el repo)
2. ✅ Autoescalado de workers
3. ✅ Límites de memoria escalables

---

## ⚠️ IMPORTANTE: Antes de empezar

1. **Backup de servicios actuales**
2. **Verificar que todos los servicios funcionan**
3. **Tener acceso SSH al servidor**

---

## 📦 FASE 0: Preparación (5 minutos)

### 1. Conectarse al servidor

```bash
ssh victus@tu-servidor
```

### 2. Crear directorio de backups

```bash
sudo mkdir -p /home/victus/backups/systemd_services
sudo cp /etc/systemd/system/back*.service /home/victus/backups/systemd_services/
sudo cp /etc/systemd/system/celerycore.service /home/victus/backups/systemd_services/ 2>/dev/null || true
```

### 3. Verificar estado actual

```bash
# Verificar todos los servicios funcionando
systemctl status backcore backbce backglobal backregisters backdipro celerycore

# Verificar memoria actual
free -h
ps aux --sort=-%mem | grep gunicorn | head -20
```

**✅ Si todos los servicios están `active (running)`, continuar**

---

## 📥 FASE 1: Copiar archivos al servidor (10 minutos)

### Opción A: Desde tu máquina local (si tienes acceso)

```bash
# Desde tu máquina local (Windows)
# Usar SCP o WinSCP para copiar estos archivos:

# Archivos a copiar:
# - docs/scripts/autoscaler.sh
# - docs/scripts/autoscaler_metrics.sh
# - docs/scripts/autoscaler_config.json
# - docs/scripts/install_autoscaler.sh

# Destino en servidor:
# /home/victus/scripts/
```

### Opción B: Crear archivos directamente en el servidor

```bash
# En el servidor, crear directorio
mkdir -p /home/victus/scripts

# Copiar contenido de los archivos (ver sección siguiente)
```

---

## 🔧 FASE 2: Instalar autoescalador (15 minutos)

### 1. Ejecutar instalador

```bash
cd /home/victus/scripts
sudo bash install_autoscaler.sh
```

**Salida esperada:**
```
✅ Scripts copiados
✅ jq instalado (o ya está instalado)
✅ bc instalado (o ya está instalado)
✅ Servicio systemd creado
✅ Systemd recargado
```

### 2. Verificar instalación

```bash
# Verificar que los scripts existen
ls -la /home/victus/scripts/autoscaler*

# Verificar que el servicio existe
sudo systemctl status autoscaler.timer
```

---

## ⚙️ FASE 3: Configurar autoescalado (10 minutos)

### 1. Editar configuración

```bash
sudo nano /home/victus/scripts/autoscaler_config.json
```

### 2. Habilitar solo backregisters (prueba inicial)

Buscar la sección `"backregisters"` y cambiar:
```json
"enabled": false,  →  "enabled": true,
```

**Guardar y salir:** `Ctrl+X`, luego `Y`, luego `Enter`

### 3. Modificar servicio backregisters a 1 worker base

```bash
sudo nano /etc/systemd/system/backregisters.service
```

Buscar la línea con `--workers 3` y cambiar a:
```
--workers 1
```

**Guardar y salir**

### 4. Aplicar cambios

```bash
sudo systemctl daemon-reload
sudo systemctl restart backregisters
sudo systemctl status backregisters
```

**✅ Verificar que el servicio está `active (running)`**

---

## 🚀 FASE 4: Activar autoescalador (2 minutos)

### 1. Iniciar timer

```bash
sudo systemctl start autoscaler.timer
sudo systemctl enable autoscaler.timer
```

### 2. Verificar que está corriendo

```bash
sudo systemctl status autoscaler.timer
```

**Salida esperada:**
```
● autoscaler.timer
   Active: active (waiting)
   Trigger: ...
```

### 3. Ver logs en tiempo real

```bash
sudo journalctl -u autoscaler -f
```

**Deberías ver:**
```
[INFO] 🔄 Iniciando ciclo de autoescalado
[INFO] 📊 Métricas: CPU=X% Memoria=YMB disponible
[INFO] ✅ Ciclo de autoescalado completado
```

---

## 📊 FASE 5: Monitorear y verificar (30 minutos)

### 1. Monitorear workers en tiempo real

```bash
# En una terminal, ejecutar:
watch -n 5 'ps aux | grep "backregisters.*gunicorn" | grep -v grep | wc -l'
```

**Deberías ver:** `1` (un worker base)

### 2. Generar carga de prueba (opcional)

```bash
# Hacer requests al servicio para ver si escala
# (depende de tu endpoint de prueba)
curl http://localhost/registers/api/test/  # o tu endpoint
```

### 3. Verificar escalado

Después de 2-5 minutos, si hay carga:
- CPU > 70% → debería escalar a 2 workers
- CPU > 80% → debería escalar a 3 workers

Verificar:
```bash
ps aux | grep "backregisters.*gunicorn" | grep -v grep
```

---

## ✅ FASE 6: Aplicar a otros proyectos (gradualmente)

**Solo si Fase 5 fue exitosa**

### 1. backdipro

```bash
# Editar configuración
sudo nano /home/victus/scripts/autoscaler_config.json
# Cambiar "backdipro": { "enabled": true }

# Modificar servicio
sudo nano /etc/systemd/system/backdipro.service
# Cambiar: --workers 2 → --workers 1

# Aplicar
sudo systemctl daemon-reload
sudo systemctl restart backdipro
```

### 2. backglobal

```bash
# Editar configuración
sudo nano /home/victus/scripts/autoscaler_config.json
# Cambiar "backglobal": { "enabled": true }

# Modificar servicio
sudo nano /etc/systemd/system/backglobal.service
# Cambiar: --workers 3 → --workers 1

# Aplicar
sudo systemctl daemon-reload
sudo systemctl restart backglobal
```

### 3. backbce

```bash
# Editar configuración
sudo nano /home/victus/scripts/autoscaler_config.json
# Cambiar "backbce": { "enabled": true }

# Modificar servicio
sudo nano /etc/systemd/system/backbce.service
# Cambiar: --workers 3 → --workers 1

# Aplicar
sudo systemctl daemon-reload
sudo systemctl restart backbce
```

### 4. backcore (Gunicorn + Celery)

```bash
# Editar configuración
sudo nano /home/victus/scripts/autoscaler_config.json
# Cambiar "backcore": { "enabled": true }
# Cambiar "celerycore": { "enabled": true }

# Modificar servicio Gunicorn
sudo nano /etc/systemd/system/backcore.service
# Cambiar: --workers 3 → --workers 1

# Modificar servicio Celery
sudo nano /etc/systemd/system/celerycore.service
# Cambiar: --concurrency=4 → --concurrency=2

# Aplicar
sudo systemctl daemon-reload
sudo systemctl restart backcore celerycore
```

---

## 🔍 FASE 7: Verificación final (10 minutos)

### 1. Verificar todos los servicios

```bash
systemctl status backcore backbce backglobal backregisters backdipro celerycore autoscaler.timer
```

**Todos deben estar `active (running)`**

### 2. Verificar memoria ahorrada

```bash
free -h
ps aux --sort=-%mem | grep -E "gunicorn|celery" | head -20
```

**Deberías ver:**
- Menos workers en idle
- Más memoria disponible

### 3. Verificar logs sin errores

```bash
sudo journalctl -u autoscaler --since "1 hour ago" | grep -i error
```

**No debería haber errores críticos**

### 4. Verificar que el código optimizado está activo

```bash
# Verificar que el código actualizado está en el servidor
cd /home/victus/projects/CORE/manu
grep -n "response.content.decode" apps/sistema_analitico/services/clasificador_contable_service.py
```

**Deberías ver la línea con la optimización**

---

## 🛠️ Troubleshooting

### El autoescalador no escala

```bash
# Verificar que está habilitado
jq '.projects.backregisters.enabled' /home/victus/scripts/autoscaler_config.json
# Debe ser: true

# Ver logs detallados
sudo journalctl -u autoscaler -n 100

# Verificar métricas manualmente
bash /home/victus/scripts/autoscaler_metrics.sh all
```

### Error al modificar servicio

```bash
# Verificar permisos
sudo systemctl status backregisters

# Verificar sintaxis del archivo
sudo systemctl daemon-reload
sudo systemctl status backregisters
```

### Workers no cambian

```bash
# Verificar que el servicio se reinició
sudo systemctl status backregisters

# Verificar número de workers
ps aux | grep "backregisters.*gunicorn" | grep -v grep

# Ver logs del autoescalador
sudo journalctl -u autoscaler -f
```

---

## 🔄 Rollback (si algo falla)

```bash
# 1. Detener autoescalador
sudo systemctl stop autoscaler.timer
sudo systemctl disable autoscaler.timer

# 2. Restaurar servicios originales
sudo cp /home/victus/backups/systemd_services/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart backcore backbce backglobal backregisters backdipro celerycore

# 3. Verificar que todo funciona
systemctl status backcore backbce backglobal backregisters backdipro celerycore
```

---

## 📊 Monitoreo continuo

### Comandos útiles

```bash
# Ver logs en tiempo real
sudo journalctl -u autoscaler -f

# Ver workers actuales de todos los proyectos
ps aux | grep gunicorn | grep -v grep

# Ver memoria disponible
free -h

# Ver CPU
top

# Ver estado de todos los servicios
systemctl status backcore backbce backglobal backregisters backdipro celerycore autoscaler.timer
```

---

## ✅ Checklist final

- [ ] Todos los servicios están `active (running)`
- [ ] Autoescalador está corriendo (`autoscaler.timer` activo)
- [ ] Workers base están en 1 (excepto celerycore en 2)
- [ ] Memoria disponible aumentó
- [ ] Logs sin errores críticos
- [ ] Código optimizado está activo

---

## 🎉 ¡Listo!

El sistema ahora:
- ✅ Ahorra ~1.1GB de memoria en idle
- ✅ Escala automáticamente según carga
- ✅ Tiene límites de memoria por worker
- ✅ Usa código optimizado para respuestas grandes

**Tiempo total estimado:** ~2 horas (con pruebas)

