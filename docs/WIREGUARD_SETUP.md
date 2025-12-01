# Configuración y Pruebas de WireGuard - Guía Segura

Esta guía te ayuda a configurar el gestor de WireGuard desde tu PC Windows local para conectarte al servidor Ubuntu en producción de forma segura.

## ⚠️ IMPORTANTE: Modo Seguro (Solo Lectura Primero)

Antes de hacer cambios, vamos a obtener información del servidor en **modo solo lectura** para no afectar la producción.

## Paso 1: Obtener Información del Servidor Ubuntu

Conéctate por SSH a tu servidor Ubuntu y ejecuta estos comandos **SOLO DE LECTURA**:

### 1.1 Información de la Interfaz WireGuard

```bash
# Ver la interfaz activa (solo lectura)
sudo wg show

# Ver todas las interfaces WireGuard
sudo wg show all

# Ver el nombre de la interfaz (normalmente wg0)
ip link show | grep wg
```

**Anota:**
- Nombre de la interfaz (ej: `wg0`)
- IP del servidor en la VPN (ej: `10.8.0.1`)

### 1.2 Información de la Configuración

```bash
# Ver la configuración del servidor (solo lectura)
sudo cat /etc/wireguard/wg0.conf

# O si tu interfaz tiene otro nombre:
sudo cat /etc/wireguard/*.conf
```

**Anota:**
- `ListenPort` (normalmente `51820`)
- `Address` del servidor (ej: `10.8.0.1/24`)
- `PublicKey` del servidor (la clave pública)

### 1.3 Información de Red y Endpoint Público

```bash
# Ver la IP pública del servidor
curl -4 ifconfig.me

# O
hostname -I | awk '{print $1}'
```

**Anota:**
- IP pública del servidor (para el endpoint)

### 1.4 Verificar Usuario SSH

```bash
# Ver qué usuario eres
whoami

# Verificar si tienes sudo sin password (opcional, más seguro)
sudo -n true && echo "Sudo sin password configurado" || echo "Necesitas password para sudo"
```

**Anota:**
- Usuario SSH (ej: `root`, `ubuntu`, `admin`)
- Si necesitas password o clave SSH

## Paso 2: Crear Usuario de Prueba (Recomendado)

Para no usar root directamente, crea un usuario con permisos sudo limitados:

```bash
# Crear usuario de prueba
sudo adduser wgmanager

# Dar permisos sudo SOLO para comandos wg (muy seguro)
sudo visudo

# Agregar esta línea al final:
wgmanager ALL=(ALL) NOPASSWD: /usr/bin/wg, /usr/bin/wg-quick
```

**Anota:**
- Usuario: `wgmanager`
- Password: (el que configuraste)

## Paso 3: Configurar .env en Windows

Crea o edita `manu/.env` con la información que obtuviste:

```env
# WireGuard VPN Server Configuration
WG_SERVER_HOST=TU_IP_PUBLICA_O_HOSTNAME  # Ej: 45.123.45.67 o servidor.com
WG_SERVER_USER=wgmanager  # O root si prefieres
WG_SERVER_PASSWORD=tu_password_aqui  # Password del usuario
WG_SERVER_SSH_PORT=22  # Puerto SSH (normalmente 22)
# WG_SSH_KEY_PATH=C:/Users/USUARIO/.ssh/id_rsa  # Opcional: usar clave SSH

# WireGuard Network Configuration
WG_INTERFACE=wg0  # Nombre de la interfaz (lo que viste en wg show)
WG_CONFIG_DIR=/etc/wireguard  # Directorio de configuración
WG_SERVER_IP=10.8.0.1  # IP del servidor en la VPN (del Address en wg0.conf)
WG_SERVER_PORT=51820  # Puerto del servidor (del ListenPort en wg0.conf)
WG_SERVER_PUBLIC_KEY_PATH=/etc/wireguard/public.key  # Ruta a clave pública
WG_SERVER_ENDPOINT=TU_IP_PUBLICA:51820  # Ej: 45.123.45.67:51820
```

## Paso 4: Probar Conexión SSH desde Windows

Antes de probar el código, verifica que puedes conectarte:

```powershell
# En PowerShell de Windows
ssh wgmanager@TU_IP_PUBLICA

# O con password
ssh -p 22 wgmanager@TU_IP_PUBLICA
```

Si funciona, puedes salir con `exit`.

## Paso 5: Probar el Sistema (Modo Seguro)

### 5.1 Primera Prueba: Solo Lectura

El sistema tiene un endpoint para ver el estado sin hacer cambios:

```bash
# Desde tu PC Windows, en el proyecto Django
python manage.py runserver

# Luego en el navegador o Postman:
GET http://localhost:8000/api/vpn/configs/server-status/
```

Esto solo lee el estado, **NO hace cambios**.

### 5.2 Segunda Prueba: Crear Túnel de Prueba

1. Ve al dashboard: `http://localhost:3001/admin/dashboard`
2. Pestaña "VPN"
3. Clic en "Crear Túnel"
4. Usa un nombre de prueba: `TEST_PC_WINDOWS`
5. **NO actives inmediatamente** - primero descarga el .conf

### 5.3 Verificar en el Servidor (Solo Lectura)

Después de crear el túnel, verifica en el servidor Ubuntu:

```bash
# Ver si se agregó el peer (solo lectura)
sudo wg show wg0

# Ver la configuración completa (solo lectura)
sudo cat /etc/wireguard/wg0.conf
```

**Si ves el nuevo peer**, el sistema funciona correctamente.

## Paso 6: Limpiar Pruebas (Opcional)

Si quieres eliminar el túnel de prueba:

1. En el dashboard, elimina el túnel de prueba
2. O manualmente en el servidor (si es necesario):

```bash
# Ver la clave pública del peer de prueba
sudo wg show wg0

# Remover el peer (solo si es necesario)
sudo wg set wg0 peer CLAVE_PUBLICA_DE_PRUEBA remove
```

## Comandos Útiles para Diagnóstico

### En el Servidor Ubuntu:

```bash
# Ver estado actual (solo lectura)
sudo wg show wg0

# Ver peers conectados
sudo wg show wg0 peers

# Ver estadísticas de tráfico
sudo wg show wg0 dump

# Ver logs del sistema
sudo journalctl -u wg-quick@wg0 -n 50
```

### En Windows (Django):

```python
# Probar conexión SSH manualmente
from manu.apps.sistema_analitico.services.wireguard_manager import WireGuardManager

try:
    wg = WireGuardManager()
    status = wg.get_server_status()
    print(status)
except Exception as e:
    print(f"Error: {e}")
```

## Checklist de Seguridad

- [ ] Usuario SSH creado (no root directamente)
- [ ] Permisos sudo limitados solo a `wg` y `wg-quick`
- [ ] Password seguro o clave SSH configurada
- [ ] Primera prueba en modo solo lectura (server-status)
- [ ] Túnel de prueba creado y verificado
- [ ] Túnel de prueba eliminado después de verificar

## Solución de Problemas

### Error: "paramiko no está instalado"
```bash
pip install paramiko
```

### Error: "Permission denied"
- Verifica que el usuario tenga permisos sudo para `wg`
- Prueba: `sudo wg show` en el servidor

### Error: "Connection refused"
- Verifica que el puerto SSH (22) esté abierto
- Verifica firewall: `sudo ufw status`

### Error: "WG_SERVER_HOST no está configurado"
- Verifica que todas las variables estén en `.env`
- Reinicia el servidor Django después de cambiar `.env`

## Notas Importantes

1. **Nunca uses root directamente** - Crea un usuario dedicado
2. **Prueba primero en modo lectura** - Usa `server-status` antes de crear túneles
3. **Backup de configuración** - Antes de cambios grandes:
   ```bash
   sudo cp /etc/wireguard/wg0.conf /etc/wireguard/wg0.conf.backup
   ```
4. **Monitorea los logs** - Revisa `journalctl` si algo falla
5. **Un túnel a la vez** - Prueba crear/eliminar un túnel antes de hacer cambios masivos

