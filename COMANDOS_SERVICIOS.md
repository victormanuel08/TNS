# 🚀 Comandos para Gestión de Servicios

Guía rápida de comandos para reiniciar servicios específicos sin reiniciar el servidor completo.

## 📍 Ubicación de Proyectos

```bash
# Backend Django (CORE)
cd ~/projects/CORE/manu

# Frontend (BCE)
cd ~/projects/BCE
```

---

## 🔄 Celery (Procesamiento Asíncrono)

### Reiniciar Celery Worker
```bash
sudo systemctl restart celerycore
```

### Ver Estado de Celery
```bash
sudo systemctl status celerycore
```

### Ver Logs de Celery (últimas 50 líneas)
```bash
sudo journalctl -u celerycore -n 50 --no-pager
```

### Ver Logs de Celery en Tiempo Real
```bash
sudo journalctl -u celerycore -f
```

### Verificar Procesos de Celery
```bash
ps aux | grep celery
```

### Reiniciar Celery Beat (Tareas Programadas)
```bash
sudo systemctl restart celerybeat
# O si está corriendo como proceso de usuario:
pkill -f "celery.*beat"
```

---

## 🌐 Django/Gunicorn (Backend API)

### Reiniciar Gunicorn
```bash
sudo systemctl restart gunicorn
# O si está en otro servicio:
sudo systemctl restart django
```

### Ver Estado de Gunicorn
```bash
sudo systemctl status gunicorn
```

### Ver Logs de Gunicorn
```bash
sudo journalctl -u gunicorn -n 50 --no-pager
sudo journalctl -u gunicorn -f  # Tiempo real
```

### Verificar Procesos de Gunicorn
```bash
ps aux | grep gunicorn
```

---

## 🗄️ Base de Datos

### Aplicar Migraciones
```bash
cd ~/projects/CORE/manu
python manage.py migrate
```

### Aplicar Migración Específica
```bash
python manage.py migrate dian_scraper
python manage.py migrate sistema_analitico
```

### Ver Estado de Migraciones
```bash
python manage.py showmigrations
```

### Crear Migraciones
```bash
python manage.py makemigrations
python manage.py makemigrations nombre_app
```

---

## 🔍 Verificación y Diagnóstico

### Ver Todos los Servicios Activos
```bash
sudo systemctl list-units --type=service --state=running | grep -E "(celery|gunicorn|django)"
```

### Ver Servicios Fallidos
```bash
sudo systemctl --failed
```

### Ver Uso de Recursos
```bash
# CPU y Memoria
htop
# O
top

# Espacio en disco
df -h

# Memoria específica
free -h
```

---

## 📝 Logs Específicos

### Logs de Django (si está configurado)
```bash
tail -f ~/projects/CORE/manu/logs/django.log
```

### Logs de Scraping DIAN
```bash
# Ver logs recientes de scraping
sudo journalctl -u celerycore | grep -i "scraping\|dian" | tail -50
```

### Logs de Clasificación Contable
```bash
sudo journalctl -u celerycore | grep -i "clasificacion\|deepseek" | tail -50
```

---

## 🔧 Comandos Útiles Adicionales

### Recargar Configuración de Systemd (después de cambios)
```bash
sudo systemctl daemon-reload
```

### Ver Variables de Entorno
```bash
# Ver .env del proyecto
cat ~/projects/CORE/manu/.env | grep -v "PASSWORD\|SECRET\|KEY"  # Sin mostrar secrets
```

### Verificar Conexión a Base de Datos
```bash
cd ~/projects/CORE/manu
python manage.py dbshell
```

### Verificar Conexión a Redis
```bash
redis-cli ping
# Debe responder: PONG
```

### Limpiar Cache de Django
```bash
cd ~/projects/CORE/manu
python manage.py clear_cache
# O si usa Redis directamente:
redis-cli FLUSHALL
```

---

## 🚨 Solución de Problemas

### Si Celery no responde
```bash
# 1. Verificar estado
sudo systemctl status celerycore

# 2. Ver logs de error
sudo journalctl -u celerycore -n 100 --no-pager | grep -i error

# 3. Matar procesos zombie
pkill -9 -f celery

# 4. Reiniciar
sudo systemctl restart celerycore
```

### Si Gunicorn no responde
```bash
# 1. Verificar estado
sudo systemctl status gunicorn

# 2. Ver logs
sudo journalctl -u gunicorn -n 100 --no-pager

# 3. Reiniciar
sudo systemctl restart gunicorn
```

### Si hay problemas con migraciones
```bash
# Ver migraciones pendientes
python manage.py showmigrations --plan

# Aplicar todas
python manage.py migrate

# Si hay conflicto, hacer merge
python manage.py makemigrations --merge nombre_app
```

---

## 📋 Checklist Rápido

### Después de hacer `git pull` en el backend:
```bash
cd ~/projects/CORE/manu
git pull
python manage.py migrate          # Si hay migraciones nuevas
sudo systemctl restart celerycore # Para cargar código nuevo
```

### Después de hacer `git pull` en el frontend:
```bash
cd ~/projects/BCE
git pull
# Si hay cambios en package.json:
npm install
# Reiniciar servicio frontend si es necesario
```

### Después de cambios en modelos Django:
```bash
cd ~/projects/CORE/manu
python manage.py makemigrations
python manage.py migrate
sudo systemctl restart celerycore
sudo systemctl restart gunicorn  # Si aplica
```

---

## 🔐 Permisos

### Si hay problemas de permisos:
```bash
# Verificar permisos de archivos
ls -la ~/projects/CORE/manu/

# Ajustar permisos si es necesario (cuidado con esto)
chmod -R 755 ~/projects/CORE/manu/
```

---

## 📞 Comandos de Emergencia

### Reiniciar TODO (último recurso)
```bash
sudo systemctl restart celerycore
sudo systemctl restart gunicorn
sudo systemctl restart redis
sudo systemctl restart postgresql  # Si aplica
```

### Ver todos los servicios relacionados
```bash
sudo systemctl list-units | grep -E "(celery|gunicorn|django|redis|postgres)"
```

---

**Nota:** Estos comandos están diseñados para el servidor VPS. Ajusta las rutas según tu configuración específica.

