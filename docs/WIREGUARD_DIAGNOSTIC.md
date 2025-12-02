# Diagnóstico y Configuración de WireGuard

## Problema

El panel de administración muestra que la VPN está "activa" pero:
- No responde a ping
- La sincronización no muestra información
- No hay conexión real

## Diagnóstico

### Paso 1: Verificar configuración en `.env`

El backend necesita estas variables en `manu/.env`:

```bash
# WireGuard - Configuración del servidor VPN
WG_SERVER_HOST=IP_DEL_SERVIDOR_WIREGUARD  # IP o hostname del servidor donde está WireGuard
WG_SERVER_USER=root  # Usuario SSH (debe tener sudo)
WG_SERVER_PASSWORD=tu_password  # Password SSH (o usar clave privada)
WG_SERVER_SSH_PORT=22  # Puerto SSH
WG_SSH_KEY_PATH=  # Ruta a clave SSH privada (opcional, alternativa a password)
WG_INTERFACE=wg0  # Nombre de la interfaz WireGuard
WG_CONFIG_DIR=/etc/wireguard  # Directorio de configuración
WG_SERVER_IP=10.8.0.1  # IP del servidor en la red VPN
WG_SERVER_PORT=51820  # Puerto del servidor WireGuard
WG_SERVER_PUBLIC_KEY_PATH=/etc/wireguard/public.key  # Ruta a clave pública del servidor
WG_SERVER_ENDPOINT=IP_PUBLICA:51820  # Endpoint público (ej: 45.149.204.184:51820)
```

**⚠️ IMPORTANTE**: 
- `WG_SERVER_HOST` debe ser la IP del servidor donde está instalado WireGuard (puede ser el mismo VPS o otro servidor)
- `WG_SERVER_ENDPOINT` debe ser la IP pública del servidor WireGuard con el puerto

### Paso 2: Verificar que WireGuard esté instalado y corriendo

En el servidor donde está WireGuard (el que configuraste en `WG_SERVER_HOST`):

```bash
# Verificar que WireGuard esté instalado
which wg
# Debe mostrar: /usr/bin/wg o similar

# Verificar que la interfaz esté activa
sudo wg show
# Debe mostrar información de la interfaz y peers

# Verificar que el servicio esté corriendo
sudo systemctl status wg-quick@wg0
# O si usas otro nombre de interfaz:
sudo systemctl status wg-quick@TU_INTERFAZ
```

### Paso 3: Verificar conectividad SSH desde el VPS

Desde el VPS (donde está el backend Django), verifica que puedas conectarte al servidor WireGuard:

```bash
# Reemplaza con tus valores
ssh -p 22 root@WG_SERVER_HOST

# O si usas clave SSH:
ssh -i /ruta/a/clave_privada -p 22 root@WG_SERVER_HOST
```

Si no puedes conectarte, el backend no podrá gestionar WireGuard.

### Paso 4: Verificar que el backend pueda ejecutar comandos

Prueba ejecutando un comando simple desde el backend:

```bash
# Desde el VPS, en el directorio del backend
cd /home/victus/projects/CORE/manu
source env/bin/activate

# Ejecutar script de prueba (si existe)
python manage.py shell
```

Luego en el shell de Django:

```python
from apps.sistema_analitico.services.wireguard_manager import WireGuardManager

try:
    wg = WireGuardManager()
    status = wg.get_server_status()
    print(status)
except Exception as e:
    print(f"Error: {e}")
```

### Paso 5: Verificar logs del backend

Si la sincronización no muestra nada, revisa los logs:

```bash
# Ver logs del backend
sudo journalctl -u backcore.service -n 100 --no-pager | grep -i wireguard
# O
sudo journalctl -u backcore.service -f
```

## Soluciones

### Solución 1: Configurar variables de entorno

Si las variables no están en el `.env`, agrégalas:

```bash
cd /home/victus/projects/CORE/manu

# Editar .env
nano .env

# Agregar las variables de WireGuard (ver Paso 1)
# Guardar y salir (Ctrl+X, Y, Enter)

# Reiniciar el backend
sudo systemctl restart backcore.service
```

### Solución 2: Verificar que WireGuard esté corriendo en el servidor

Si el servidor WireGuard está en el mismo VPS:

```bash
# Verificar que WireGuard esté instalado
sudo apt update
sudo apt install wireguard wireguard-tools -y

# Verificar que el servicio esté corriendo
sudo systemctl status wg-quick@wg0

# Si no está corriendo, iniciarlo
sudo systemctl start wg-quick@wg0
sudo systemctl enable wg-quick@wg0
```

### Solución 3: Verificar permisos SSH

El usuario SSH debe poder ejecutar `sudo wg` sin contraseña:

```bash
# En el servidor WireGuard, editar sudoers
sudo visudo

# Agregar esta línea (reemplaza 'root' con tu usuario):
root ALL=(ALL) NOPASSWD: /usr/bin/wg, /usr/bin/wg-quick

# Guardar y salir
```

### Solución 4: Verificar firewall

El puerto de WireGuard (51820 por defecto) debe estar abierto:

```bash
# En el servidor WireGuard
sudo ufw allow 51820/udp
# O
sudo firewall-cmd --add-port=51820/udp --permanent
sudo firewall-cmd --reload
```

### Solución 5: Verificar configuración de WireGuard

El servidor WireGuard debe tener una configuración básica en `/etc/wireguard/wg0.conf`:

```ini
[Interface]
PrivateKey = CLAVE_PRIVADA_DEL_SERVIDOR
Address = 10.8.0.1/24
ListenPort = 51820

# PostUp y PostDown para habilitar NAT (si es necesario)
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
```

Y la clave pública del servidor debe estar en `/etc/wireguard/public.key`:

```bash
# Generar clave pública del servidor (si no existe)
sudo wg genkey | sudo tee /etc/wireguard/private.key | sudo wg pubkey | sudo tee /etc/wireguard/public.key
sudo chmod 600 /etc/wireguard/private.key
sudo chmod 644 /etc/wireguard/public.key
```

## Verificación Final

Después de aplicar las soluciones:

1. **Reinicia el backend:**
   ```bash
   sudo systemctl restart backcore.service
   ```

2. **Ve al admin panel** (`https://eddeso.com/admin/dashboard` → pestaña VPN)

3. **Haz clic en "Sincronizar"** y verifica que:
   - No muestre errores
   - Muestre peers si hay alguno configurado
   - Muestre el estado del servidor

4. **Verifica el estado del servidor:**
   - Debe mostrar "Activo" si WireGuard está corriendo
   - Debe mostrar información de peers si hay alguno

## Comandos Útiles para Diagnóstico

```bash
# Ver estado de WireGuard en el servidor
sudo wg show

# Ver configuración de la interfaz
sudo wg show wg0 dump

# Verificar que el servicio esté corriendo
sudo systemctl status wg-quick@wg0

# Ver logs del servicio WireGuard
sudo journalctl -u wg-quick@wg0 -n 50

# Probar conexión SSH desde el VPS al servidor WireGuard
ssh -v root@WG_SERVER_HOST

# Verificar que el puerto esté abierto
sudo netstat -ulnp | grep 51820
# O
sudo ss -ulnp | grep 51820
```

## Notas Importantes

1. **El servidor WireGuard puede ser el mismo VPS** donde está el backend, o puede ser otro servidor.

2. **Si el servidor WireGuard es el mismo VPS**, entonces:
   - `WG_SERVER_HOST` puede ser `localhost` o `127.0.0.1`
   - Pero es mejor usar la IP privada del VPS si está en la misma red

3. **La sincronización** lee los peers que ya existen en el servidor WireGuard y los importa a la base de datos.

4. **"Activo" en el panel** solo significa que el registro está marcado como activo en la BD, no necesariamente que el peer esté conectado. Para ver si está conectado, revisa la columna "Conexión" que muestra "Conectado" o "Desconectado" basado en el último handshake.

