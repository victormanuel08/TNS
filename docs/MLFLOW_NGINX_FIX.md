# Solución: mlflow.eddeso.com redirige al frontend

## Problema

`mlflow.eddeso.com` está siendo capturado por el frontend Nuxt (`livecore`) en lugar de ir a MLflow (puerto 5050).

## Causa

Nginx procesa los `server_name` en orden alfabético de los archivos en `sites-enabled`. Si `livecore` tiene un wildcard `*.eddeso.com` o está antes alfabéticamente, captura todas las peticiones.

## Solución: Dar Prioridad a MLflow

### Opción 1: Renombrar para dar prioridad alfabética (Recomendado)

```bash
# Ver archivos actuales
ls -la /etc/nginx/sites-enabled/ | grep -E "mlflow|livecore"

# Renombrar mlflow para que tenga prioridad (0- hace que vaya primero)
sudo mv /etc/nginx/sites-enabled/mlflow /etc/nginx/sites-enabled/0-mlflow

# Verificar orden
ls -la /etc/nginx/sites-enabled/ | sort

# Verificar configuración
sudo nginx -t

# Recargar
sudo systemctl reload nginx
```

### Opción 2: Verificar y ajustar configuración de livecore

```bash
# Ver configuración de livecore
sudo cat /etc/nginx/sites-available/livecore | grep -A 5 "server_name"

# Si tiene wildcard *.eddeso.com, necesitamos excluir mlflow
```

Si `livecore` tiene `server_name *.eddeso.com`, debemos cambiarlo para excluir `mlflow`:

```nginx
# En lugar de:
server_name *.eddeso.com;

# Debe ser:
server_name ~^(?!mlflow\.)eddeso\.com$ ~^(?!mlflow\.).+\.eddeso\.com$;
```

O mejor, listar explícitamente los subdominios permitidos.

### Opción 3: Verificar orden actual y prioridad

```bash
# Ver todas las configuraciones activas
sudo nginx -T | grep -E "server_name|listen" | head -20

# Ver qué configuración está capturando mlflow.eddeso.com
sudo nginx -T | grep -B 5 -A 10 "mlflow.eddeso.com"
```

## Verificación

### 1. Verificar que mlflow tiene prioridad:

```bash
# Ver orden de archivos
ls -1 /etc/nginx/sites-enabled/ | sort

# Debe aparecer 0-mlflow antes que livecore
```

### 2. Probar desde el servidor:

```bash
# Probar que mlflow responde directamente
curl -H "Host: mlflow.eddeso.com" http://localhost

# Debe devolver HTML de MLflow, no del frontend
```

### 3. Verificar configuración activa:

```bash
# Ver qué server block está activo para mlflow.eddeso.com
sudo nginx -T | grep -A 15 "server_name mlflow.eddeso.com"
```

## Comandos de Diagnóstico

```bash
# Ver todas las configuraciones de server_name
sudo nginx -T | grep "server_name" | sort

# Ver qué está capturando mlflow.eddeso.com
curl -v -H "Host: mlflow.eddeso.com" http://localhost 2>&1 | head -30

# Ver logs de Nginx
sudo tail -f /var/log/nginx/access.log | grep mlflow
```

## Solución Definitiva

Si después de renombrar a `0-mlflow` aún no funciona, verifica que la configuración de `livecore` no tenga un `default_server` o wildcard que capture todo:

```bash
# Ver configuración completa de livecore
sudo cat /etc/nginx/sites-available/livecore

# Buscar si tiene default_server o catch-all
sudo grep -E "default_server|server_name.*\*" /etc/nginx/sites-available/livecore
```

Si `livecore` tiene `default_server`, quítalo o mueve `mlflow` antes en el orden alfabético.

