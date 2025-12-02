# Troubleshooting MLflow - Error 203/EXEC

## Problema: `status=203/EXEC`

Este error significa que systemd no puede ejecutar el comando. Posibles causas:

1. **MLflow no está instalado** en el venv
2. **La ruta del ejecutable es incorrecta**
3. **El venv no existe o está en otra ubicación**

## Diagnóstico

### 1. Verificar que el venv existe:
```bash
ls -la /home/victus/projects/CORE/manu/venv/bin/mlflow
```

### 2. Verificar que MLflow está instalado:
```bash
/home/victus/projects/CORE/manu/venv/bin/mlflow --version
```

### 3. Ver logs detallados del error:
```bash
sudo journalctl -u mlflowcore.service -n 50 --no-pager
```

### 4. Verificar permisos:
```bash
ls -la /home/victus/projects/CORE/manu/venv/bin/ | grep mlflow
```

## Soluciones

### Solución 1: Instalar MLflow en el venv

```bash
cd /home/victus/projects/CORE/manu
source venv/bin/activate
pip install mlflow>=2.8.0
deactivate
```

### Solución 2: Verificar la ruta correcta del ejecutable

```bash
# Buscar dónde está MLflow
which mlflow
# O si está en el venv:
/home/victus/projects/CORE/manu/venv/bin/python -m pip show mlflow
```

### Solución 3: Usar Python directamente en lugar del binario

Si el binario no funciona, modifica el servicio para usar Python:

```bash
sudo nano /etc/systemd/system/mlflowcore.service
```

Cambia la línea `ExecStart` por:

```ini
ExecStart=/home/victus/projects/CORE/manu/venv/bin/python -m mlflow ui --port 5050 --host 0.0.0.0
```

Luego:
```bash
sudo systemctl daemon-reload
sudo systemctl restart mlflowcore.service
```

### Solución 4: Verificar que el venv está activo y funcional

```bash
cd /home/victus/projects/CORE/manu
source venv/bin/activate
python --version
pip list | grep mlflow
mlflow --version
```

Si alguno de estos falla, el venv puede estar corrupto.

## Comando de Verificación Completa

```bash
echo "=== Verificar venv ===" && \
test -d /home/victus/projects/CORE/manu/venv && echo "✅ venv existe" || echo "❌ venv NO existe" && \
echo "" && \
echo "=== Verificar MLflow ===" && \
test -f /home/victus/projects/CORE/manu/venv/bin/mlflow && echo "✅ mlflow binario existe" || echo "❌ mlflow binario NO existe" && \
/home/victus/projects/CORE/manu/venv/bin/mlflow --version 2>&1 && echo "✅ mlflow funciona" || echo "❌ mlflow NO funciona" && \
echo "" && \
echo "=== Verificar Python ===" && \
/home/victus/projects/CORE/manu/venv/bin/python --version && \
echo "" && \
echo "=== Verificar MLflow instalado ===" && \
/home/victus/projects/CORE/manu/venv/bin/pip show mlflow 2>&1 | head -5
```

