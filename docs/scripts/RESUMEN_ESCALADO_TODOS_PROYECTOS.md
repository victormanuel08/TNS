# ✅ Escalado a Demanda - Todos los Proyectos

## 🎯 Respuesta Rápida

**SÍ, todos los proyectos escalan a demanda y bajan automáticamente cuando baja la demanda.**

---

## 📊 Configuración Actual de Todos los Proyectos

### 1. **backregisters**
- ✅ **Min workers:** 1 (base)
- ✅ **Max workers:** 3
- ✅ **Escala arriba:** CPU > 70% → 2 workers, CPU > 80% → 3 workers
- ✅ **Escala abajo:** CPU < 40% → 2 workers, CPU < 35% → 1 worker
- ⚠️ **Estado:** `enabled: false` (habilitar para activar)

### 2. **backdipro**
- ✅ **Min workers:** 1 (base)
- ✅ **Max workers:** 6
- ✅ **Escala arriba:** CPU > 65% → 75% → 80% → 85% → 90% (hasta 6 workers)
- ✅ **Escala abajo:** CPU < 45% → 2 workers, CPU < 35% → 1 worker
- ⚠️ **Estado:** `enabled: false` (habilitar para activar)

### 3. **backglobal**
- ✅ **Min workers:** 1 (base)
- ✅ **Max workers:** 4
- ✅ **Escala arriba:** CPU > 65% → 75% → 85% (hasta 4 workers)
- ✅ **Escala abajo:** CPU < 45% → 2 workers, CPU < 35% → 1 worker
- ⚠️ **Estado:** `enabled: false` (habilitar para activar)

### 4. **backbce**
- ✅ **Min workers:** 1 (base)
- ✅ **Max workers:** 4
- ✅ **Escala arriba:** CPU > 65% → 75% → 85% (hasta 4 workers)
- ✅ **Escala abajo:** CPU < 45% → 2 workers, CPU < 35% → 1 worker
- ⚠️ **Estado:** `enabled: false` (habilitar para activar)

### 5. **backcore** (Gunicorn)
- ✅ **Min workers:** 1 (base)
- ✅ **Max workers:** 10
- ✅ **Escala arriba:** CPU > 60% → 70% → 75% → 80% → 82% → 84% → 86% → 88% → 90% (hasta 10 workers)
- ✅ **Escala abajo:** CPU < 40% → 2 workers, CPU < 30% → 1 worker
- ⚠️ **Estado:** `enabled: false` (habilitar para activar)

### 6. **celerycore** (Celery)
- ✅ **Min workers:** 2 (base)
- ✅ **Max workers:** 12
- ✅ **Escala arriba:** Cola > 10 → 4 workers, > 20 → 6 workers, > 30 → 8 workers, > 40 → 10 workers, > 50 → 12 workers
- ✅ **Escala abajo:** Cola < 5 → 4 workers, Cola < 2 → 2 workers
- ⚠️ **Estado:** `enabled: false` (habilitar para activar)

---

## 🔄 Cómo Funciona el Escalado

### **Escalado ARRIBA (más workers):**
1. ✅ Monitorea CPU cada 2 minutos
2. ✅ Si CPU > umbral durante 3 minutos → escala arriba
3. ✅ Verifica que hay memoria suficiente (≥500MB por worker con 18GB)
4. ✅ Verifica que no alcanzó el máximo
5. ✅ **Aumenta workers automáticamente**

### **Escalado ABAJO (menos workers):**
1. ✅ Monitorea CPU cada 2 minutos
2. ✅ Si CPU < umbral durante 15 minutos → escala abajo
3. ✅ Si hay mucha memoria libre (>8GB) y CPU baja → escala abajo
4. ✅ Verifica que no está en el mínimo
5. ✅ **Reduce workers automáticamente**

---

## 📈 Ejemplo Real: Todos los Proyectos

### **Escenario: Todos los proyectos con demanda**

**Estado inicial (idle):**
```
backregisters: 1 worker
backdipro: 1 worker
backglobal: 1 worker
backbce: 1 worker
backcore: 1 worker
celerycore: 2 workers
─────────────────────
Total: 7 workers
Memoria: ~14GB disponible
```

**Cuando sube la demanda en backdipro:**
```
backregisters: 1 worker (sin cambios)
backdipro: 3 workers ← Escaló porque CPU > 75%
backglobal: 1 worker (sin cambios)
backbce: 1 worker (sin cambios)
backcore: 1 worker (sin cambios)
celerycore: 2 workers (sin cambios)
─────────────────────
Total: 9 workers
Memoria: ~13GB disponible
```

**Cuando sube la demanda en backcore:**
```
backregisters: 1 worker (sin cambios)
backdipro: 3 workers (sin cambios)
backglobal: 1 worker (sin cambios)
backbce: 1 worker (sin cambios)
backcore: 5 workers ← Escaló porque CPU > 80%
celerycore: 4 workers ← Escaló porque cola > 10
─────────────────────
Total: 14 workers
Memoria: ~11GB disponible
```

**Cuando baja la demanda (después de 30 minutos):**
```
backregisters: 1 worker (sin cambios)
backdipro: 1 worker ← Bajó porque CPU < 35% durante 15 min
backglobal: 1 worker (sin cambios)
backbce: 1 worker (sin cambios)
backcore: 2 workers ← Bajó porque CPU < 40% durante 15 min
celerycore: 2 workers ← Bajó porque cola < 2 durante 10 min
─────────────────────
Total: 8 workers
Memoria: ~14GB disponible
```

---

## ⚙️ Habilitar Todos los Proyectos

### **Opción 1: Habilitar todos de una vez**

```bash
# Editar configuración
sudo nano /home/victus/scripts/autoscaler_config.json

# Cambiar todos los "enabled": false a "enabled": true
```

### **Opción 2: Habilitar gradualmente (recomendado)**

```bash
# 1. Habilitar backregisters primero (menor riesgo)
# 2. Esperar 1 hora y verificar
# 3. Habilitar backdipro
# 4. Esperar 1 hora y verificar
# 5. Habilitar backglobal
# 6. Esperar 1 hora y verificar
# 7. Habilitar backbce
# 8. Esperar 1 hora y verificar
# 9. Habilitar backcore y celerycore (últimos)
```

---

## 🔍 Verificar Escalado de Todos los Proyectos

### **Ver workers actuales de todos:**

```bash
# Todos los proyectos
echo "=== WORKERS ACTUALES ==="
echo "backregisters: $(ps aux | grep 'backregisters.*gunicorn' | grep -v grep | wc -l) workers"
echo "backdipro: $(ps aux | grep 'backdipro.*gunicorn' | grep -v grep | wc -l) workers"
echo "backglobal: $(ps aux | grep 'backglobal.*gunicorn' | grep -v grep | wc -l) workers"
echo "backbce: $(ps aux | grep 'backbce.*gunicorn' | grep -v grep | wc -l) workers"
echo "backcore: $(ps aux | grep 'backcore.*gunicorn' | grep -v grep | wc -l) workers"
echo "celerycore: $(ps aux | grep 'celery.*worker' | grep -v grep | wc -l) workers"
```

### **Ver logs del autoescalador:**

```bash
# Ver todos los escalados
sudo journalctl -u autoscaler -f

# Ver solo escalados de hoy
sudo journalctl -u autoscaler --since today | grep "scale"
```

### **Monitoreo en tiempo real:**

```bash
# Ver workers y CPU cada 5 segundos
watch -n 5 '
echo "=== WORKERS Y CPU ==="
echo "backregisters: $(ps aux | grep "backregisters.*gunicorn" | grep -v grep | wc -l) workers"
echo "backdipro: $(ps aux | grep "backdipro.*gunicorn" | grep -v grep | wc -l) workers"
echo "backglobal: $(ps aux | grep "backglobal.*gunicorn" | grep -v grep | wc -l) workers"
echo "backbce: $(ps aux | grep "backbce.*gunicorn" | grep -v grep | wc -l) workers"
echo "backcore: $(ps aux | grep "backcore.*gunicorn" | grep -v grep | wc -l) workers"
echo "celerycore: $(ps aux | grep "celery.*worker" | grep -v grep | wc -l) workers"
echo ""
echo "CPU: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk "{print 100-\$1}")%"
echo "Memoria: $(free -h | grep Mem | awk "{print \$7}") disponible"
'
```

---

## ✅ Ventajas del Escalado a Demanda

### **1. Ahorro de Recursos:**
- ✅ En idle: Solo 7 workers totales (vs 17 fijos antes)
- ✅ Ahorro: ~1.1GB de memoria en idle

### **2. Escalado Automático:**
- ✅ Cada proyecto escala independientemente
- ✅ backdipro puede tener 6 workers mientras backregisters tiene 1
- ✅ No hay interferencia entre proyectos

### **3. Optimización de Memoria:**
- ✅ Límites de memoria por worker según recursos disponibles
- ✅ Con 18GB: hasta 1.5GB por worker
- ✅ Evita OOM (Out of Memory)

### **4. Sin Intervención Manual:**
- ✅ Monitorea cada 2 minutos
- ✅ Escala automáticamente
- ✅ Registra todo en logs

---

## 🚀 Pasos para Activar Todo

### **1. Modificar servicios a 1 worker base:**

```bash
# backregisters
sudo nano /etc/systemd/system/backregisters.service
# Cambiar: --workers 3 → --workers 1

# backdipro
sudo nano /etc/systemd/system/backdipro.service
# Cambiar: --workers 2 → --workers 1

# backglobal
sudo nano /etc/systemd/system/backglobal.service
# Cambiar: --workers 3 → --workers 1

# backbce
sudo nano /etc/systemd/system/backbce.service
# Cambiar: --workers 3 → --workers 1

# backcore
sudo nano /etc/systemd/system/backcore.service
# Cambiar: --workers 3 → --workers 1

# celerycore
sudo nano /etc/systemd/system/celerycore.service
# Cambiar: --concurrency=4 → --concurrency=2
```

### **2. Aplicar cambios:**

```bash
sudo systemctl daemon-reload
sudo systemctl restart backregisters backdipro backglobal backbce backcore celerycore
```

### **3. Habilitar en configuración:**

```bash
sudo nano /home/victus/scripts/autoscaler_config.json
# Cambiar todos los "enabled": false a "enabled": true
```

### **4. Verificar:**

```bash
# Ver que todos están en 1 worker (o 2 para celery)
ps aux | grep -E "gunicorn|celery.*worker" | grep -v grep

# Ver logs
sudo journalctl -u autoscaler -f
```

---

## 📊 Resumen

| Proyecto | Min | Max | Escala Arriba | Escala Abajo | Estado |
|----------|-----|-----|---------------|--------------|--------|
| **backregisters** | 1 | 3 | CPU > 70-80% | CPU < 35-40% | ⚠️ Deshabilitado |
| **backdipro** | 1 | 6 | CPU > 65-90% | CPU < 35-45% | ⚠️ Deshabilitado |
| **backglobal** | 1 | 4 | CPU > 65-85% | CPU < 35-45% | ⚠️ Deshabilitado |
| **backbce** | 1 | 4 | CPU > 65-85% | CPU < 35-45% | ⚠️ Deshabilitado |
| **backcore** | 1 | 10 | CPU > 60-90% | CPU < 30-40% | ⚠️ Deshabilitado |
| **celerycore** | 2 | 12 | Cola > 10-50 | Cola < 2-5 | ⚠️ Deshabilitado |

**Todos están listos para escalar a demanda, solo necesitan estar habilitados.**

---

## ✅ Conclusión

**SÍ, todos los proyectos:**
- ✅ Escalan automáticamente cuando sube la demanda
- ✅ Bajan automáticamente cuando baja la demanda
- ✅ Funcionan independientemente (cada uno escala según su propia carga)
- ✅ Optimizan memoria según recursos disponibles
- ✅ No requieren intervención manual

**Solo necesitas:**
1. Habilitarlos en la configuración (`enabled: true`)
2. Dejar que el autoescalador haga su trabajo
3. Monitorear los logs si quieres ver qué está pasando

