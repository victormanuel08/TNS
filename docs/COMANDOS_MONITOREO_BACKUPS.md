# Comandos para Monitorear Backups en el VPS

## 📋 Comandos Rápidos

### 1. Ver Tareas Activas de Celery (Backups en Ejecución)
```bash
# Ver todas las tareas activas
celery -A config inspect active

# Ver con más detalle (incluye argumentos)
celery -A config inspect active -d celery@$(hostname)

# Ver solo tareas de backup
celery -A config inspect active | grep -A 10 "realizar_backup_empresa"
```

### 2. Ver Estado de una Tarea Específica
```bash
# Reemplaza TASK_ID con el ID real (ej: 4eda272c-182d-4569-9ed1-739f3b0b1a94)
celery -A config result TASK_ID

# Ver con formato JSON
celery -A config result TASK_ID --format=json
```

### 3. Ver Logs de Celery en Tiempo Real
```bash
# Ver logs del servicio Celery
sudo journalctl -u celerycore -f

# Ver últimas 100 líneas y seguir
sudo journalctl -u celerycore -n 100 -f

# Ver logs filtrados por "backup"
sudo journalctl -u celerycore -f | grep -i backup
```

### 4. Consultar Backups en la Base de Datos (Django Shell)
```bash
# Entrar al shell de Django
cd ~/projects/CORE/manu
source venv/bin/activate  # Si usas venv
python manage.py shell
```

Dentro del shell de Django:
```python
from apps.sistema_analitico.models import BackupS3, EmpresaServidor
from django.utils import timezone
from datetime import timedelta

# Ver backups de las últimas 24 horas
hace_24h = timezone.now() - timedelta(hours=24)
backups_recientes = BackupS3.objects.filter(
    fecha_backup__gte=hace_24h
).order_by('-fecha_backup').select_related('empresa_servidor')

print(f"\n📊 Backups de las últimas 24 horas: {backups_recientes.count()}\n")
for backup in backups_recientes[:20]:  # Mostrar primeros 20
    estado_icono = "✅" if backup.estado == "completado" else "❌" if backup.estado == "fallido" else "⏳"
    print(f"{estado_icono} {backup.empresa_servidor.nombre} | "
          f"Estado: {backup.estado} | "
          f"Fecha: {backup.fecha_backup.strftime('%Y-%m-%d %H:%M:%S')} | "
          f"Tamaño: {backup.tamano_gb:.2f} GB")

# Ver backups en progreso
backups_en_proceso = BackupS3.objects.filter(estado='en_proceso')
print(f"\n⏳ Backups en progreso: {backups_en_proceso.count()}\n")
for backup in backups_en_proceso:
    print(f"  - {backup.empresa_servidor.nombre} | "
          f"Iniciado: {backup.fecha_backup.strftime('%Y-%m-%d %H:%M:%S')}")

# Ver backups fallidos recientes
backups_fallidos = BackupS3.objects.filter(
    estado='fallido',
    fecha_backup__gte=hace_24h
).order_by('-fecha_backup')
print(f"\n❌ Backups fallidos (últimas 24h): {backups_fallidos.count()}\n")
for backup in backups_fallidos[:10]:
    print(f"  - {backup.empresa_servidor.nombre} | "
          f"Error: {backup.mensaje_error[:100] if backup.mensaje_error else 'N/A'}")

# Verificar empresas específicas (usar los IDs de las tareas lanzadas)
empresas_ids = [246, 231, 251, 252, 253, 254, 237, 238, 239, 240, 241, 242, 236, 250, 249, 232, 233, 234, 235, 255, 256, 243, 244]
for empresa_id in empresas_ids:
    try:
        empresa = EmpresaServidor.objects.get(id=empresa_id)
        ultimo_backup = BackupS3.objects.filter(empresa_servidor=empresa).order_by('-fecha_backup').first()
        if ultimo_backup:
            estado_icono = "✅" if ultimo_backup.estado == "completado" else "❌" if ultimo_backup.estado == "fallido" else "⏳"
            print(f"{estado_icono} {empresa.nombre} (ID: {empresa_id}) | "
                  f"Estado: {ultimo_backup.estado} | "
                  f"Fecha: {ultimo_backup.fecha_backup.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"⚠️  {empresa.nombre} (ID: {empresa_id}) | Sin backups")
    except EmpresaServidor.DoesNotExist:
        print(f"❌ Empresa ID {empresa_id} no encontrada")
```

### 5. Ver Backups por Empresa (Script Rápido)
```bash
# Crear un script temporal
cat > /tmp/ver_backups.sh << 'EOF'
#!/bin/bash
cd ~/projects/CORE/manu
source venv/bin/activate
python manage.py shell << 'PYTHON'
from apps.sistema_analitico.models import BackupS3, EmpresaServidor
from django.utils import timezone
from datetime import timedelta

# IDs de empresas de las tareas lanzadas
empresas_ids = [246, 231, 251, 252, 253, 254, 237, 238, 239, 240, 241, 242, 236, 250, 249, 232, 233, 234, 235, 255, 256, 243, 244]

print("\n" + "="*80)
print("📊 ESTADO DE BACKUPS - ÚLTIMAS 2 HORAS")
print("="*80 + "\n")

hace_2h = timezone.now() - timedelta(hours=2)
completados = 0
fallidos = 0
en_proceso = 0
sin_backup = 0

for empresa_id in empresas_ids:
    try:
        empresa = EmpresaServidor.objects.get(id=empresa_id)
        backups_recientes = BackupS3.objects.filter(
            empresa_servidor=empresa,
            fecha_backup__gte=hace_2h
        ).order_by('-fecha_backup')
        
        if backups_recientes.exists():
            backup = backups_recientes.first()
            if backup.estado == "completado":
                estado_icono = "✅"
                completados += 1
            elif backup.estado == "fallido":
                estado_icono = "❌"
                fallidos += 1
            else:
                estado_icono = "⏳"
                en_proceso += 1
            
            print(f"{estado_icono} {empresa.nombre[:40]:<40} | "
                  f"{backup.estado.upper():<12} | "
                  f"{backup.fecha_backup.strftime('%H:%M:%S')} | "
                  f"{backup.tamano_gb:.2f} GB")
        else:
            print(f"⚠️  {empresa.nombre[:40]:<40} | SIN BACKUP RECIENTE")
            sin_backup += 1
    except EmpresaServidor.DoesNotExist:
        print(f"❌ Empresa ID {empresa_id} no encontrada")

print("\n" + "="*80)
print(f"✅ Completados: {completados} | ❌ Fallidos: {fallidos} | ⏳ En proceso: {en_proceso} | ⚠️  Sin backup: {sin_backup}")
print("="*80 + "\n")
PYTHON
EOF

chmod +x /tmp/ver_backups.sh
/tmp/ver_backups.sh
```

### 6. Monitoreo Continuo (Watch)
```bash
# Ver tareas activas cada 5 segundos
watch -n 5 'celery -A config inspect active | head -30'

# Ver logs en tiempo real
sudo journalctl -u celerycore -f | grep -E "(backup|Backup|BACKUP|✅|❌|completado|fallido)"
```

### 7. Ver Estadísticas de Backups
```bash
cd ~/projects/CORE/manu
source venv/bin/activate
python manage.py shell << 'PYTHON'
from apps.sistema_analitico.models import BackupS3
from django.utils import timezone
from datetime import timedelta

hace_24h = timezone.now() - timedelta(hours=24)
backups_24h = BackupS3.objects.filter(fecha_backup__gte=hace_24h)

completados = backups_24h.filter(estado='completado').count()
fallidos = backups_24h.filter(estado='fallido').count()
en_proceso = backups_24h.filter(estado='en_proceso').count()

print(f"\n📊 ESTADÍSTICAS DE BACKUPS (Últimas 24 horas)")
print(f"✅ Completados: {completados}")
print(f"❌ Fallidos: {fallidos}")
print(f"⏳ En proceso: {en_proceso}")
print(f"📦 Total: {backups_24h.count()}\n")

# Tamaño total
tamano_total = sum(b.tamano_bytes for b in backups_24h.filter(estado='completado'))
print(f"💾 Tamaño total: {tamano_total / (1024**3):.2f} GB\n")
PYTHON
```

## 🔍 Verificar Tareas Específicas Lanzadas

Si tienes los task_ids de las tareas lanzadas, puedes verificar cada una:

```bash
# Lista de task_ids (del resultado anterior)
TASK_IDS=(
  "4eda272c-182d-4569-9ed1-739f3b0b1a94"
  "7fb09803-ff3a-4b27-8501-986cc24f7157"
  "dd530eeb-d9ea-4d7e-a283-fe51696c31f3"
  # ... agregar más IDs
)

# Verificar cada una
for task_id in "${TASK_IDS[@]}"; do
  echo "=== Task ID: $task_id ==="
  celery -A config result "$task_id"
  echo ""
done
```

## 📝 Notas

- Los backups pueden tardar varios minutos dependiendo del tamaño de la base de datos
- El estado `en_proceso` significa que la tarea está ejecutándose
- El estado `completado` significa que el backup se subió exitosamente a S3
- El estado `fallido` incluye el mensaje de error en `mensaje_error`

