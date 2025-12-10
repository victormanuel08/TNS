# 📊 Monitoreo de Escalado en Procesamiento de RUTs

## 🔍 Cómo Verificar si Está Escalando Correctamente

### **Configuración Actual**

El sistema procesa RUTs con:
- **ThreadPoolExecutor** con **5 workers** (máximo)
- **Celery** para ZIPs con más de 50 archivos
- **Procesamiento directo** para ZIPs con menos de 50 archivos

---

## 📈 Comandos para Monitorear Escalado

### **1. Ver Tareas Celery Activas (Tiempo Real)**

```bash
# Ver todas las tareas activas
celery -A config inspect active

# Ver con más detalle
celery -A config inspect active -d celery@$(hostname)

# Monitoreo continuo (actualiza cada 2 segundos)
watch -n 2 'celery -A config inspect active'
```

**Qué buscar:**
- Si ves `procesar_zip_ruts` en la lista, está usando Celery
- El número de tareas activas indica cuántos ZIPs se están procesando

---

### **2. Ver Progreso de una Tarea Específica**

Si tienes el `task_id` de la respuesta al subir el ZIP:

```bash
# Ver estado de la tarea
celery -A config result TASK_ID

# O desde Python
python manage.py shell << 'EOF'
from celery.result import AsyncResult
from config.celery import app

task_id = "TU_TASK_ID_AQUI"
result = AsyncResult(task_id, app=app)

print(f"Estado: {result.state}")
if result.info and isinstance(result.info, dict):
    meta = result.info
    print(f"Procesados: {meta.get('procesados', 0)}/{meta.get('total', 0)}")
    print(f"Exitosos: {meta.get('exitosos', 0)}")
    print(f"Fallidos: {meta.get('fallidos', 0)}")
    print(f"Status: {meta.get('status', 'N/A')}")
EOF
```

---

### **3. Ver Uso de CPU y Memoria**

```bash
# Ver uso de CPU en tiempo real
top -bn1 | head -20

# Ver uso de memoria
free -h

# Ver procesos Python relacionados con RUTs
ps aux | grep -E "python.*rut|celery.*rut" | grep -v grep

# Monitoreo continuo de recursos
watch -n 1 'free -h && echo "" && top -bn1 | head -5'
```

**Qué buscar:**
- **CPU**: Si está cerca de 100%, los workers están trabajando
- **Memoria**: Verificar que no se esté agotando
- **Procesos**: Ver cuántos procesos Python están corriendo

---

### **4. Ver Logs en Tiempo Real**

```bash
# Logs de Celery
tail -f /var/log/celery/worker.log | grep -i rut

# O si usas systemd
sudo journalctl -u celery -f | grep -i rut

# Logs de Django
tail -f /ruta/a/logs/django.log | grep -i rut
```

**Qué buscar:**
- Mensajes como `[RUT archivo.pdf]` indican procesamiento paralelo
- Si ves muchos mensajes simultáneos, está escalando bien

---

### **5. Verificar Número de Workers Activos**

```bash
python manage.py shell << 'EOF'
from config.celery import app

# Ver workers activos
active = app.control.inspect().active()
if active:
    print(f"Workers Celery activos: {len(active)}")
    for worker, tasks in active.items():
        print(f"  {worker}: {len(tasks)} tareas")
        rut_tasks = [t for t in tasks if 'rut' in t.get('name', '').lower()]
        if rut_tasks:
            print(f"    → {len(rut_tasks)} tareas RUT")
else:
    print("⚠️ No hay workers Celery activos")
EOF
```

---

### **6. Medir Velocidad de Procesamiento**

```bash
# Script para medir velocidad
python manage.py shell << 'EOF'
from apps.sistema_analitico.models import RUT
from django.utils import timezone
from datetime import timedelta

# RUTs creados en la última hora
hace_1_hora = timezone.now() - timedelta(hours=1)
ruts_recientes = RUT.objects.filter(fecha_creacion__gte=hace_1_hora).count()

print(f"RUTs procesados en la última hora: {ruts_recientes}")
print(f"Velocidad promedio: {ruts_recientes / 60:.2f} RUTs/minuto")

# RUTs creados en los últimos 10 minutos
hace_10_min = timezone.now() - timedelta(minutes=10)
ruts_10min = RUT.objects.filter(fecha_creacion__gte=hace_10_min).count()
print(f"RUTs procesados en los últimos 10 minutos: {ruts_10min}")
print(f"Velocidad reciente: {ruts_10min / 10:.2f} RUTs/minuto")
EOF
```

---

## 🎯 Indicadores de Escalado Correcto

### ✅ **Está Escalando Bien Si:**

1. **Múltiples procesos activos**:
   ```bash
   ps aux | grep python | grep -E "rut|celery" | wc -l
   # Debe mostrar > 1 si hay procesamiento paralelo
   ```

2. **CPU alta pero estable**:
   - Si el CPU está entre 50-90%, los workers están trabajando
   - Si está en 100% constantemente, puede necesitar más workers

3. **Progreso constante**:
   - Los contadores `procesados` aumentan constantemente
   - No se queda "atorado" en un archivo

4. **Logs simultáneos**:
   - Ver múltiples `[RUT archivo1.pdf]`, `[RUT archivo2.pdf]` al mismo tiempo

---

## ⚠️ Indicadores de Problemas

### ❌ **No Está Escalando Si:**

1. **Solo un proceso activo**:
   ```bash
   ps aux | grep python | grep rut | wc -l
   # Si muestra solo 1, no está paralelizando
   ```

2. **CPU bajo (< 20%)**:
   - Los workers no están trabajando
   - Puede haber un cuello de botella (I/O, BD, etc.)

3. **Progreso lento o estancado**:
   - Los contadores no aumentan
   - Puede haber un error o bloqueo

---

## 🔧 Ajustar Número de Workers

El número de workers está hardcoded en `rut_batch_processor.py` línea 610:

```python
max_workers = min(5, len(pdf_files))
```

Para cambiarlo, edita el archivo o agrega configuración en `settings.py`:

```python
# En settings.py
RUT_ZIP_WORKERS = 10  # Aumentar a 10 workers

# Luego en rut_batch_processor.py, cambiar:
max_workers = min(getattr(settings, 'RUT_ZIP_WORKERS', 5), len(pdf_files))
```

---

## 📊 Script Completo de Monitoreo

```bash
#!/bin/bash
# Guardar como monitorear_ruts.sh

echo "=========================================="
echo "📊 MONITOREO DE PROCESAMIENTO DE RUTs"
echo "=========================================="
echo ""

# 1. Tareas Celery
echo "1️⃣ Tareas Celery:"
celery -A config inspect active 2>/dev/null | head -20
echo ""

# 2. Recursos
echo "2️⃣ Recursos:"
echo "CPU: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}')"
echo "Memoria: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo ""

# 3. Procesos
echo "3️⃣ Procesos RUT:"
ps aux | grep -E "python.*rut|celery.*rut" | grep -v grep | wc -l
echo ""

# 4. Velocidad
echo "4️⃣ Velocidad (últimos 10 min):"
python manage.py shell << 'EOF'
from apps.sistema_analitico.models import RUT
from django.utils import timezone
from datetime import timedelta

hace_10_min = timezone.now() - timedelta(minutes=10)
ruts = RUT.objects.filter(fecha_creacion__gte=hace_10_min).count()
print(f"   {ruts} RUTs procesados ({ruts/10:.2f} RUTs/min)")
EOF
echo ""

echo "=========================================="
```

Ejecutar con:
```bash
chmod +x monitorear_ruts.sh
watch -n 2 ./monitorear_ruts.sh
```

---

## 🚀 Comando Rápido Todo-en-Uno

```bash
# Monitoreo completo en una línea
watch -n 2 'echo "=== CELERY ===" && celery -A config inspect active 2>/dev/null | head -5 && echo "" && echo "=== CPU/MEM ===" && top -bn1 | head -3 && echo "" && echo "=== PROCESOS ===" && ps aux | grep -E "python.*rut|celery.*rut" | grep -v grep | wc -l && echo "procesos activos"'
```

