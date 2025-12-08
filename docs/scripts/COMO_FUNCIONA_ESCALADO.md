# 🔄 Cómo Funciona el Autoescalado

## 📊 Escalado Automático por Proyecto

El autoescalador monitorea cada proyecto cada 2 minutos y ajusta workers automáticamente según:

1. **CPU del sistema**
2. **Memoria disponible**
3. **Cola de tareas** (solo Celery)

---

## 🎯 Ejemplo: backdipro con Varios Usuarios

### Escenario: backdipro con muchos usuarios

**Estado inicial:**
- Workers: 1 (base)
- CPU: 20%
- Memoria: 12GB disponible

**Cuando llegan varios usuarios:**

1. **CPU sube a 70%** (durante 3 minutos)
   - ✅ Autoescalador detecta: `CPU > 70%`
   - ✅ Verifica memoria: `12GB / 2 workers = 6GB por worker` ✅ Suficiente
   - ✅ **Escala a 2 workers**

2. **CPU sigue subiendo a 75%** (durante 3 minutos)
   - ✅ Autoescalador detecta: `CPU > 75%`
   - ✅ Verifica memoria: `12GB / 3 workers = 4GB por worker` ✅ Suficiente
   - ✅ **Escala a 3 workers**

3. **CPU sube a 80%** (durante 3 minutos)
   - ✅ Autoescalador detecta: `CPU > 80%`
   - ✅ Verifica memoria: `12GB / 4 workers = 3GB por worker` ✅ Suficiente
   - ✅ **Escala a 4 workers**

4. **CPU sube a 85%** (durante 3 minutos)
   - ✅ Autoescalador detecta: `CPU > 85%`
   - ✅ Verifica memoria: `12GB / 5 workers = 2.4GB por worker` ✅ Suficiente
   - ✅ **Escala a 5 workers**

5. **CPU sube a 90%** (durante 3 minutos)
   - ✅ Autoescalador detecta: `CPU > 90%`
   - ✅ Verifica memoria: `12GB / 6 workers = 2GB por worker` ✅ Suficiente
   - ✅ **Escala a 6 workers** (máximo configurado)

### Cuando los usuarios se van:

1. **CPU baja a 45%** (durante 15 minutos)
   - ✅ Autoescalador detecta: `CPU < 45%`
   - ✅ **Escala a 5 workers**

2. **CPU baja a 35%** (durante 15 minutos)
   - ✅ Autoescalador detecta: `CPU < 35%`
   - ✅ **Escala a 1 worker** (mínimo configurado)

---

## ⚙️ Configuración de backdipro

```json
{
  "backdipro": {
    "enabled": true,  // ← Debe estar en true para que funcione
    "min_workers": 1,  // Mínimo siempre activo
    "max_workers": 6,  // Máximo cuando hay mucha carga
    "cpu_thresholds": {
      "scale_up_2": 65,   // CPU > 65% → 2 workers
      "scale_up_3": 75,   // CPU > 75% → 3 workers
      "scale_up_4": 80,   // CPU > 80% → 4 workers
      "scale_up_5": 85,   // CPU > 85% → 5 workers
      "scale_up_6": 90,   // CPU > 90% → 6 workers
      "scale_down_2": 45, // CPU < 45% → bajar a 2 workers
      "scale_down_1": 35  // CPU < 35% → bajar a 1 worker
    },
    "cpu_duration_minutes": {
      "scale_up": 3,      // Esperar 3 minutos antes de escalar arriba
      "scale_down": 15    // Esperar 15 minutos antes de escalar abajo
    }
  }
}
```

---

## 🔍 Verificación en Tiempo Real

### Ver workers actuales de backdipro

```bash
ps aux | grep "backdipro.*gunicorn" | grep -v grep | wc -l
```

### Ver logs del autoescalador

```bash
sudo journalctl -u autoscaler -f | grep backdipro
```

**Salida esperada cuando escala:**
```
[INFO] 📊 backdipro.service: CPU=75.2% Mem=12000MB -> scale_up a 3 workers
[INFO] ✅ backdipro.service escalado a 3 workers (límite memoria: 500M por worker)
```

### Ver CPU y memoria en tiempo real

```bash
watch -n 5 'echo "CPU: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk "{print 100-\$1}")%"; echo "Memoria: $(free -h | grep Mem | awk "{print \$7}") disponible"'
```

---

## ⚠️ Condiciones para Escalar

### Escalar ARRIBA (más workers):
- ✅ CPU > umbral durante 3 minutos
- ✅ Memoria disponible ≥ 500MB por worker (con 18GB RAM)
- ✅ No alcanzó el máximo de workers

### Escalar ABAJO (menos workers):
- ✅ CPU < umbral durante 15 minutos
- ✅ Memoria disponible > 8GB (con 18GB RAM)
- ✅ No está en el mínimo de workers

### NO escalar si:
- ❌ Proyecto deshabilitado (`enabled: false`)
- ❌ Memoria insuficiente
- ❌ Ya está en máximo/mínimo

---

## 📈 Ejemplo Real: backdipro con 50 usuarios simultáneos

**Estado inicial:**
```
Workers: 1
CPU: 25%
Memoria: 14GB disponible
```

**Después de 5 minutos:**
```
Workers: 2  ← Escaló porque CPU > 65%
CPU: 68%
Memoria: 13GB disponible
```

**Después de 10 minutos:**
```
Workers: 3  ← Escaló porque CPU > 75%
CPU: 78%
Memoria: 12GB disponible
```

**Después de 15 minutos:**
```
Workers: 4  ← Escaló porque CPU > 80%
CPU: 82%
Memoria: 11GB disponible
```

**Cuando los usuarios se van (después de 30 minutos):**
```
Workers: 3  ← Bajó porque CPU < 45% durante 15 min
CPU: 42%
Memoria: 13GB disponible
```

**Después de 45 minutos:**
```
Workers: 1  ← Bajó porque CPU < 35% durante 15 min
CPU: 30%
Memoria: 14GB disponible
```

---

## 🚀 Habilitar Autoescalado para backdipro

### 1. Editar configuración

```bash
sudo nano /home/victus/scripts/autoscaler_config.json
```

### 2. Cambiar `enabled: false` a `enabled: true`

```json
"backdipro": {
  "enabled": true,  // ← Cambiar esto
  ...
}
```

### 3. Modificar servicio a 1 worker base

```bash
sudo nano /etc/systemd/system/backdipro.service
```

Cambiar:
```
--workers 2  →  --workers 1
```

### 4. Aplicar cambios

```bash
sudo systemctl daemon-reload
sudo systemctl restart backdipro
```

### 5. Verificar que funciona

```bash
# Ver workers actuales
ps aux | grep "backdipro.*gunicorn" | grep -v grep | wc -l
# Debe mostrar: 1

# Ver logs del autoescalador
sudo journalctl -u autoscaler -f
```

---

## ✅ Resumen

**SÍ, backdipro escalará automáticamente cuando:**
- ✅ Esté habilitado (`enabled: true`)
- ✅ CPU > umbrales configurados
- ✅ Haya memoria suficiente
- ✅ No haya alcanzado el máximo (6 workers)

**El autoescalador:**
- ✅ Monitorea cada 2 minutos
- ✅ Escala automáticamente sin intervención
- ✅ Ajusta límites de memoria por worker
- ✅ Registra todas las acciones en logs

**Solo necesitas:**
1. Habilitar el proyecto en la configuración
2. Dejar que el autoescalador haga su trabajo
3. Monitorear los logs si quieres ver qué está pasando

