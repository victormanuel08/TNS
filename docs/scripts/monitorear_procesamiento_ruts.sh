#!/bin/bash
# Script para monitorear el procesamiento de RUTs en tiempo real
# Muestra métricas de escalado, velocidad y uso de recursos

echo "=========================================="
echo "📊 MONITOREO DE PROCESAMIENTO DE RUTs"
echo "=========================================="
echo ""

# 1. Ver tareas Celery activas
echo "1️⃣ Tareas Celery Activas:"
echo "-----------------------------------"
celery -A config inspect active 2>/dev/null || echo "⚠️ Celery no está corriendo o no hay tareas activas"
echo ""

# 2. Ver workers de Celery
echo "2️⃣ Workers de Celery:"
echo "-----------------------------------"
celery -A config inspect stats 2>/dev/null | grep -A 5 "celery@" || echo "⚠️ No se encontraron workers"
echo ""

# 3. Ver uso de CPU y memoria
echo "3️⃣ Uso de Recursos del Sistema:"
echo "-----------------------------------"
echo "CPU:"
top -bn1 | grep "Cpu(s)" | awk '{print "   " $2}'
echo ""
echo "Memoria:"
free -h | grep "Mem:" | awk '{print "   Total: " $2 " | Usada: " $3 " | Libre: " $4}'
echo ""

# 4. Ver procesos Python relacionados con RUTs
echo "4️⃣ Procesos Python Procesando RUTs:"
echo "-----------------------------------"
ps aux | grep -E "python.*rut|celery.*rut" | grep -v grep || echo "   No hay procesos activos"
echo ""

# 5. Ver logs recientes de RUTs
echo "5️⃣ Logs Recientes de RUTs (últimas 10 líneas):"
echo "-----------------------------------"
if [ -f /var/log/celery/worker.log ]; then
    tail -10 /var/log/celery/worker.log | grep -i rut
elif [ -f /var/log/django.log ]; then
    tail -10 /var/log/django.log | grep -i rut
else
    echo "   ⚠️ No se encontraron logs (puede que estén en otro lugar)"
fi
echo ""

# 6. Verificar configuración de workers
echo "6️⃣ Configuración de Workers:"
echo "-----------------------------------"
python manage.py shell << 'EOF'
from django.conf import settings
import os

# Verificar si hay configuración de workers
max_workers = getattr(settings, 'RUT_ZIP_WORKERS', None)
if max_workers:
    print(f"   Workers configurados: {max_workers}")
else:
    print("   Workers por defecto: 5 (hardcoded en rut_batch_processor.py)")

# Verificar Celery
try:
    from config.celery import app
    active_workers = app.control.inspect().active()
    if active_workers:
        print(f"   Workers Celery activos: {len(active_workers)}")
        for worker, tasks in active_workers.items():
            rut_tasks = [t for t in tasks if 'rut' in t.get('name', '').lower()]
            if rut_tasks:
                print(f"      {worker}: {len(rut_tasks)} tareas RUT")
    else:
        print("   ⚠️ No hay workers Celery activos")
except Exception as e:
    print(f"   ⚠️ Error verificando Celery: {e}")
EOF
echo ""

echo "=========================================="
echo "✅ Monitoreo completado"
echo "=========================================="
echo ""
echo "💡 Para monitoreo continuo, ejecuta:"
echo "   watch -n 2 'bash monitorear_procesamiento_ruts.sh'"

