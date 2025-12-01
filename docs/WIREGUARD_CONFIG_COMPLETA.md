# Configuración WireGuard - Información Completa

## ✅ Variables Configuradas en .env

Basándome en la información que proporcionaste, he configurado el `.env` con:

```env
WG_SERVER_HOST=198.7.113.197
WG_SERVER_USER=wgmanager
WG_SERVER_PASSWORD=Wg32708
WG_SERVER_SSH_PORT=22
WG_INTERFACE=wg-main
WG_CONFIG_DIR=/etc/wireguard
WG_SERVER_IP=10.8.0.1
WG_SERVER_PORT=46587
WG_SERVER_PUBLIC_KEY_PATH=/etc/wireguard/public.key
WG_SERVER_ENDPOINT=198.7.113.197:46587
```

## ⚠️ IMPORTANTE: Verificar IP del Servidor

Hay una discrepancia que necesitamos verificar:

- **Interfaz activa**: `wg-main` (puerto `46587`)
- **Archivo de configuración**: `wg0.conf` (puerto `51820`, IP `10.8.0.1`)
- **IPs de los peers**: `10.8.3.10` y `10.8.3.100` (sugieren red `10.8.3.0/24`)

### Ejecuta en el servidor Ubuntu:

```bash
# Ver la IP del servidor en wg-main
ip addr show wg-main | grep "inet "

# O verificar si existe archivo de configuración para wg-main
sudo cat /etc/wireguard/wg-main.conf 2>/dev/null || echo "No existe wg-main.conf"

# Ver la configuración completa
sudo wg show wg-main dump
```

**Si la IP del servidor en `wg-main` es diferente a `10.8.0.1`, actualiza `WG_SERVER_IP` en el `.env`**

## Paso 4: Probar Conexión SSH desde Windows

Ahora puedes probar la conexión desde Windows:

```powershell
cd manu
python scripts/test_ssh_connection.py
```

Este script verificará:
- ✅ Conexión SSH al servidor
- ✅ Autenticación con usuario `wgmanager`
- ✅ Permisos para ejecutar `sudo wg show`
- ✅ Estado de WireGuard

## Paso 5: Configurar Permisos Sudo para wgmanager

**IMPORTANTE**: Antes de probar crear túneles, asegúrate de que `wgmanager` tenga permisos sudo:

En el servidor Ubuntu, ejecuta:

```bash
sudo visudo
```

Y agrega esta línea al final:

```
wgmanager ALL=(ALL) NOPASSWD: /usr/bin/wg, /usr/bin/wg-quick
```

Guarda y cierra (Ctrl+X, luego Y, luego Enter).

Verifica que funciona:

```bash
su wgmanager
sudo wg show wg-main
# Debe mostrar la información sin pedir password
exit
```

## Paso 6: Probar el Sistema

### 6.1 Probar solo lectura (no hace cambios)

```bash
# En Windows, iniciar Django
cd manu
python manage.py runserver

# Luego en navegador o Postman:
GET http://localhost:8000/api/vpn/configs/server-status/
```

### 6.2 Crear túnel de prueba

1. Ve a: `http://localhost:3001/admin/dashboard`
2. Pestaña "VPN"
3. Clic en "Crear Túnel"
4. Nombre: `TEST_WINDOWS_PC`
5. **NO actives inmediatamente** - primero descarga el .conf

### 6.3 Verificar en el servidor

```bash
sudo wg show wg-main
# Deberías ver el nuevo peer agregado
```

## Solución de Problemas

### Error: "Permission denied" al ejecutar wg
- Verifica que agregaste la línea en `visudo`
- Prueba: `su wgmanager` y luego `sudo wg show wg-main`

### Error: "WG_SERVER_IP incorrecto"
- Verifica la IP real del servidor: `ip addr show wg-main | grep "inet "`
- Actualiza `WG_SERVER_IP` en el `.env` si es diferente

### Error: "Interface wg-main not found"
- Verifica que la interfaz esté activa: `sudo wg show wg-main`
- Si no existe, puede que necesites usar `wg0` en su lugar

## Notas Importantes

1. **La interfaz activa es `wg-main`**, no `wg0`
2. **El puerto es `46587`**, no `51820`
3. **Verifica la IP del servidor** antes de crear túneles
4. **Configura permisos sudo** para `wgmanager` antes de probar
5. **Prueba primero en modo lectura** con `server-status`

