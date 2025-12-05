# Comandos para Verificar Logs PM2 en el Servidor

## Ver Logs en Tiempo Real

```bash
# Ver logs de todos los procesos PM2
pm2 logs

# Ver logs de un proceso específico (Django/Manu)
pm2 logs manu

# Ver solo los últimos 100 líneas
pm2 logs --lines 100

# Ver logs sin colores (útil para copiar)
pm2 logs --no-color
```

## Ver Logs de Errores

```bash
# Ver solo errores
pm2 logs --err

# Ver errores de un proceso específico
pm2 logs manu --err
```

## Ver Estado de los Procesos

```bash
# Listar todos los procesos
pm2 list

# Ver información detallada de un proceso
pm2 show manu

# Ver monitoreo en tiempo real
pm2 monit
```

## Ver Logs de Django Específicamente

```bash
# Si el proceso se llama 'manu' o 'django'
pm2 logs manu --lines 200

# Ver logs con filtro para errores de DIAN
pm2 logs manu | grep -i "dian\|test_connection\|error"
```

## Ver Logs del Sistema (Django logs)

```bash
# Si Django guarda logs en archivos
tail -f /ruta/a/manu/logs/*.log

# Ver logs de errores de Django
tail -f /ruta/a/manu/logs/error.log

# Ver últimos 100 líneas de error
tail -n 100 /ruta/a/manu/logs/error.log
```

## Comandos Útiles para Diagnóstico

```bash
# Ver qué proceso está escuchando en el puerto 8001
netstat -tulpn | grep 8001
# o
ss -tulpn | grep 8001

# Ver procesos de Python/Django
ps aux | grep python
ps aux | grep manage.py

# Ver espacio en disco
df -h

# Ver memoria disponible
free -h

# Ver logs del sistema (systemd)
journalctl -u pm2-* -n 100 --no-pager
```

## Reiniciar el Proceso

```bash
# Reiniciar proceso específico
pm2 restart manu

# Reiniciar todos los procesos
pm2 restart all

# Recargar sin downtime (zero-downtime)
pm2 reload manu
```

