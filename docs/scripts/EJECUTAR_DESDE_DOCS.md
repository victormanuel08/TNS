# 🚀 Ejecutar Autoescalador desde docs/scripts

## 📍 Situación Actual

Los archivos están en:
```
~/projects/CORE/docs/scripts/
```

## ✅ Opción 1: Copiar y Ejecutar (Recomendado)

```bash
# 1. Crear directorio destino
mkdir -p /home/victus/scripts

# 2. Copiar archivos
cp ~/projects/CORE/docs/scripts/autoscaler.sh /home/victus/scripts/
cp ~/projects/CORE/docs/scripts/autoscaler_metrics.sh /home/victus/scripts/
cp ~/projects/CORE/docs/scripts/autoscaler_config.json /home/victus/scripts/
cp ~/projects/CORE/docs/scripts/install_autoscaler.sh /home/victus/scripts/

# 3. Ejecutar instalador
sudo bash /home/victus/scripts/install_autoscaler.sh
```

## ✅ Opción 2: Ejecutar Directamente desde docs/scripts

```bash
# Desde ~/projects/CORE/docs/scripts/
cd ~/projects/CORE/docs/scripts/

# Ejecutar directamente (el script detectará su ubicación)
sudo bash install_autoscaler.sh
```

**Nota:** El script detecta automáticamente dónde está y copia los archivos a `/home/victus/scripts/` automáticamente.

## ✅ Opción 3: Todo en un Comando

```bash
# Desde cualquier lugar
sudo bash ~/projects/CORE/docs/scripts/install_autoscaler.sh
```

---

## 🎯 Recomendación

**Usa la Opción 1** para tener los archivos organizados en `/home/victus/scripts/` como está diseñado.

---

## ⚡ Comando Rápido (Todo en uno)

```bash
mkdir -p /home/victus/scripts && \
cp ~/projects/CORE/docs/scripts/{autoscaler.sh,autoscaler_metrics.sh,autoscaler_config.json,install_autoscaler.sh} /home/victus/scripts/ && \
sudo bash /home/victus/scripts/install_autoscaler.sh
```

