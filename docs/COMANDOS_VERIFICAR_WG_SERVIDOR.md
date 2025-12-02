# Comandos para Verificar y Actualizar WireGuard en el Servidor

## Comandos Rápidos

### 1. Ver todas las interfaces WireGuard

```bash
sudo wg show
```

### 2. Ver configuración de una interfaz específica (generalmente wg-main)

```bash
sudo wg show wg-main
```

### 3. Ver configuración detallada (dump)

```bash
sudo wg show wg-main dump
```

### 4. Buscar específicamente el peer 10.8.3.10

```bash
sudo wg show wg-main | grep -A 5 "10.8.3.10"
# O
sudo wg show wg-main dump | grep "10.8.3.10"
```

### 5. Ver IP del servidor en la interfaz

```bash
ip addr show wg-main | grep "inet "
```

### 6. Verificar si el peer está conectado (último handshake)

```bash
sudo wg show wg-main | grep -A 3 "10.8.3.10"
```

Si ves `latest handshake: [número]` significa que está conectado. Si dice `latest handshake: 0` o no aparece, no está conectado.

## Actualizar Peer 10.8.3.10

### Si el peer NO existe en el servidor:

Necesitas agregarlo. Primero obtén la clave pública del cliente desde:
- El archivo .conf del cliente (línea `PublicKey` en `[Peer]`)
- O desde la base de datos

Luego ejecuta:

```bash
# Reemplaza [CLAVE_PUBLICA] con la clave pública real del cliente
sudo wg set wg-main peer [CLAVE_PUBLICA] allowed-ips 10.8.3.10/32
```

### Si el peer YA existe pero tiene AllowedIPs incorrecto:

```bash
# Primero obtén la clave pública del peer actual
PEER_KEY=$(sudo wg show wg-main dump | grep "10.8.3.10" | awk -F'\t' '{print $2}')

# Actualizar AllowedIPs
sudo wg set wg-main peer "$PEER_KEY" allowed-ips 10.8.3.10/32
```

### Guardar la configuración permanentemente

```bash
# Opción 1: Si tienes wg-quick
sudo wg-quick save wg-main

# Opción 2: Guardar manualmente en el archivo de configuración
# Edita /etc/wireguard/wg-main.conf y agrega/actualiza el peer
sudo nano /etc/wireguard/wg-main.conf
```

## Scripts Automatizados

He creado dos scripts que puedes usar:

### Script 1: Verificar configuración

```bash
cd /home/victus/projects/CORE
sudo bash docs/scripts/check_wg_server_config.sh
```

### Script 2: Actualizar peer 10.8.3.10

```bash
cd /home/victus/projects/CORE
sudo bash docs/scripts/update_wg_peer_10.8.3.10.sh
```

## Verificación Rápida (Una Línea)

```bash
# Ver si el peer 10.8.3.10 está configurado
sudo wg show wg-main dump | grep "10.8.3.10" && echo "✅ Peer encontrado" || echo "❌ Peer NO encontrado"
```

## Obtener Clave Pública del Cliente

Si necesitas la clave pública del cliente 10.8.3.10, puedes obtenerla de:

1. **Desde el archivo .conf del cliente:**
   - Busca la línea `PublicKey = ...` en la sección `[Peer]`

2. **Desde la base de datos (si tienes acceso):**
   ```bash
   cd /home/victus/projects/CORE/manu
   source env/bin/activate
   python manage.py shell
   ```
   ```python
   from apps.sistema_analitico.models import VpnConfig
   vpn = VpnConfig.objects.filter(ip_address='10.8.3.10').first()
   if vpn:
       print(f"Clave pública: {vpn.public_key}")
   ```

## Ejemplo de Configuración Correcta en el Servidor

El servidor debe tener algo como esto en `/etc/wireguard/wg-main.conf`:

```ini
[Interface]
PrivateKey = [clave_privada_del_servidor]
Address = 10.8.3.1/24
ListenPort = 46587

[Peer]
# Cliente 10.8.3.10
PublicKey = [clave_publica_del_cliente_10.8.3.10]
AllowedIPs = 10.8.3.10/32
```

## Troubleshooting

### El peer no aparece en `wg show`

1. Verifica que el archivo de configuración tenga el peer
2. Recarga la configuración: `sudo wg-quick down wg-main && sudo wg-quick up wg-main`

### El peer aparece pero no hay handshake

1. Verifica que el cliente esté conectado a la VPN
2. Verifica que el cliente tenga la configuración correcta (con PostUp/PostDown y AllowedIPs correctos)
3. Verifica que el firewall del servidor permita el tráfico

### No puedo hacer ping al cliente

1. Verifica que el peer esté en el servidor: `sudo wg show wg-main | grep "10.8.3.10"`
2. Verifica que el cliente esté conectado (handshake reciente)
3. Verifica que el firewall del cliente permita conexiones desde 10.8.3.1

