# Solución: 502 Bad Gateway

## Problema

Nginx no puede conectarse a MLflow en el puerto 5050. Esto puede ser porque:
1. MLflow no está corriendo
2. MLflow está tardando en iniciar
3. Hay un error al iniciar

## Diagnóstico

```bash
# 1. Verificar estado del servicio
sudo systemctl status mlflowcore.service

# 2. Verificar que está escuchando en el puerto 5050
sudo ss -tlnp | grep 5050

# 3. Ver logs completos del servicio
sudo journalctl -u mlflowcore.service -n 50 --no-pager

# 4. Probar directamente MLflow (sin Nginx)
curl http://localhost:5050 | head -20
```

## Soluciones

### Si MLflow no está corriendo:

```bash
# Ver qué está fallando
sudo journalctl -u mlflowcore.service -n 100 --no-pager | tail -30

# Reiniciar manualmente
sudo systemctl restart mlflowcore.service

# Esperar 10 segundos y verificar
sleep 10
sudo systemctl status mlflowcore.service
sudo ss -tlnp | grep 5050
```

### Si MLflow está tardando en iniciar:

MLflow puede tardar unos segundos en iniciar. Verifica que esté completamente iniciado:

```bash
# Ver logs en tiempo real
sudo journalctl -u mlflowcore.service -f

# En otra terminal, probar
curl http://localhost:5050
```

### Si hay errores en los logs:

Revisa los logs para ver qué error específico está ocurriendo.

