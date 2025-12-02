# Solución: Invalid Host header en MLflow

## Problema

MLflow está rechazando las conexiones con el error:
```
Invalid Host header - possible DNS rebinding attack detected
```

Esto es porque MLflow tiene protección de seguridad que solo permite hosts específicos.

## Solución: Agregar --allowed-hosts al servicio

### Actualizar el servicio systemd:

```bash
sudo nano /etc/systemd/system/mlflowcore.service
```

Cambia la línea `ExecStart` de:
```ini
ExecStart=/home/victus/projects/CORE/manu/env/bin/python -m mlflow ui --port 5050 --host 0.0.0.0
```

Por:
```ini
ExecStart=/home/victus/projects/CORE/manu/env/bin/python -m mlflow ui --port 5050 --host 0.0.0.0 --allowed-hosts mlflow.eddeso.com --allowed-hosts localhost --allowed-hosts 127.0.0.1
```

### O usar este comando directo:

```bash
sudo sed -i 's|--host 0.0.0.0|--host 0.0.0.0 --allowed-hosts mlflow.eddeso.com --allowed-hosts localhost --allowed-hosts 127.0.0.1|' /etc/systemd/system/mlflowcore.service
```

### Reiniciar el servicio:

```bash
sudo systemctl daemon-reload
sudo systemctl restart mlflowcore.service
sudo systemctl status mlflowcore.service
```

### Verificar que funciona:

```bash
# Esperar unos segundos para que inicie
sleep 3

# Probar
curl -k -H "Host: mlflow.eddeso.com" https://localhost 2>/dev/null | head -20
```

Ahora debe mostrar HTML de MLflow sin el error "Invalid Host header".

## Verificar configuración final:

```bash
# Ver el servicio actualizado
sudo cat /etc/systemd/system/mlflowcore.service | grep ExecStart

# Ver logs
sudo journalctl -u mlflowcore.service -n 20 --no-pager
```

