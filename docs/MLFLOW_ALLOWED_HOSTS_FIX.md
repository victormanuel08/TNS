# Solución: Invalid Host header persistente

## Problema

Aunque agregamos `--allowed-hosts`, MLflow sigue rechazando las conexiones.

## Posibles causas

1. **MLflow no ha cargado completamente** (solo muestra 1 tarea, 2.8M de memoria)
2. **Sintaxis incorrecta** de `--allowed-hosts`
3. **Necesita deshabilitar host header check**

## Solución 1: Ver logs para diagnosticar

```bash
# Ver logs completos del servicio
sudo journalctl -u mlflowcore.service -n 50 --no-pager

# Ver si hay errores al iniciar
sudo journalctl -u mlflowcore.service --since "5 minutes ago" | grep -i error
```

## Solución 2: Deshabilitar host header check

MLflow puede necesitar deshabilitar la verificación del header Host:

```bash
sudo nano /etc/systemd/system/mlflowcore.service
```

Cambiar `ExecStart` a:
```ini
ExecStart=/home/victus/projects/CORE/manu/env/bin/python -m mlflow ui --port 5050 --host 0.0.0.0 --host-header-check false
```

O si esa opción no existe, usar:
```ini
ExecStart=/home/victus/projects/CORE/manu/env/bin/python -m mlflow ui --port 5050 --host 0.0.0.0 --no-host-header-check
```

## Solución 3: Verificar versión de MLflow

```bash
/home/victus/projects/CORE/manu/env/bin/python -m mlflow --version

# Ver opciones disponibles
/home/victus/projects/CORE/manu/env/bin/python -m mlflow ui --help | grep -i host
```

## Solución 4: Usar variable de entorno

Algunas versiones de MLflow usan variables de entorno:

```bash
sudo nano /etc/systemd/system/mlflowcore.service
```

Agregar en la sección `[Service]`:
```ini
Environment="MLFLOW_ALLOWED_HOSTS=mlflow.eddeso.com,localhost,127.0.0.1"
```

## Solución 5: Probar directamente sin proxy

```bash
# Probar directamente MLflow (sin Nginx)
curl http://localhost:5050 | head -20

# Si esto funciona, el problema es la configuración de Nginx o el header Host
```

