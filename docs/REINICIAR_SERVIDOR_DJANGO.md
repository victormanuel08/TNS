# 🔄 Cómo Reiniciar el Servidor Django en el VPS

## 📍 Servicio Principal

El servidor Django se llama **`backcore.service`** y está gestionado por **systemd**.

## 🚀 Comandos para Reiniciar

### 1. Reiniciar solo el servidor Django

```bash
sudo systemctl restart backcore.service
```

### 2. Verificar que se reinició correctamente

```bash
sudo systemctl status backcore.service
```

**Salida esperada:**
```
● backcore.service - Django Backend Core
   Loaded: loaded (/etc/systemd/system/backcore.service; enabled)
   Active: active (running) since ...
```

### 3. Ver logs en tiempo real

```bash
sudo journalctl -u backcore.service -f
```

### 4. Ver últimos logs

```bash
sudo journalctl -u backcore.service -n 50
```

## 🔄 Reiniciar Todos los Servicios Relacionados

Si necesitas reiniciar todos los servicios del proyecto:

```bash
# Reiniciar Django
sudo systemctl restart backcore.service

# Reiniciar Celery Worker
sudo systemctl restart celerycore.service

# Reiniciar Celery Beat (tareas programadas)
sudo systemctl restart celerybeat.service
```

## 📊 Verificar Estado de Todos los Servicios

```bash
systemctl status backcore celerycore celerybeat
```

## ⚠️ Si el Servicio No Existe en systemd

Si `backcore.service` no existe, puede estar corriendo con **PM2**:

```bash
# Ver procesos PM2
pm2 list

# Reiniciar si está en PM2 (buscar por nombre: backcore, back, backend, manu, django)
pm2 restart backcore
# O
pm2 restart back
# O
pm2 restart manu
```

## 🔍 Verificar Qué Método Está Usando

```bash
# Verificar systemd
systemctl status backcore.service

# Verificar PM2
pm2 list | grep -i back

# Verificar procesos manuales
ps aux | grep gunicorn
ps aux | grep manage.py
```

## 📝 Notas Importantes

1. **Después de cambios en código Python**, siempre reinicia el servidor Django
2. **Después de cambios en `views.py`**, reinicia `backcore.service`
3. **Después de cambios en tareas Celery**, reinicia `celerycore.service` y `celerybeat.service`
4. Los cambios en **archivos estáticos** no requieren reinicio (solo recargar en el navegador)

## 🎯 Comando Rápido (Todo en Uno)

```bash
# Reiniciar todo el stack
sudo systemctl restart backcore.service celerycore.service celerybeat.service && \
systemctl status backcore.service celerycore.service celerybeat.service
```

