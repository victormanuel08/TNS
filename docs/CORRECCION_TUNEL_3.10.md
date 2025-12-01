# Corrección de Configuración - Túnel 10.8.3.10

## Configuración Actual (INCORRECTA)

```ini
[Interface]
PrivateKey = cNTGgpDdZYiWVDgIdxtbnPbzd85IquNSxy5pDZjpu3E=
ListenPort = 51830
Address = 10.8.3.10/24
DNS = 1.1.1.1
MTU = 1420
PostUp = netsh interface ip add route 10.8.3.0/24 "WireGuard" 10.8.3.10
PostDown = netsh interface ip delete route 10.8.3.0/24 "WireGuard" 10.8.3.10

[Peer]
PublicKey = UPgAgldMaBpK9/cAGh3C5+HXkX+n4NtHqAbQjkfL3h0=
AllowedIPs = 10.8.3.1/32  # ❌ Permite acceso al servidor
PersistentKeepalive = 25
```

**Problemas:**
1. `AllowedIPs = 10.8.3.1/32` → Cliente puede acceder al servidor ❌
2. `PostUp` con ruta `10.8.3.0/24` → Cliente puede acceder a toda la red (otros clientes) ❌

## Configuración Correcta

```ini
[Interface]
PrivateKey = cNTGgpDdZYiWVDgIdxtbnPbzd85IquNSxy5pDZjpu3E=
ListenPort = 51830
Address = 10.8.3.10/24
DNS = 1.1.1.1
MTU = 1420
# PostUp y PostDown eliminados - no necesarios

[Peer]
PublicKey = UPgAgldMaBpK9/cAGh3C5+HXkX+n4NtHqAbQjkfL3h0=
AllowedIPs = 10.8.3.10/32  # ✅ Solo su propia IP
PersistentKeepalive = 25
```

**Cambios:**
1. `AllowedIPs = 10.8.3.10/32` → Cliente solo puede acceder a su propia IP ✅
2. Eliminados `PostUp` y `PostDown` → No hay rutas adicionales ✅

## Resultado

- ✅ **Servidor puede acceder al cliente**: El servidor tiene `AllowedIPs = 10.8.3.10/32` en su configuración
- ❌ **Cliente NO puede acceder al servidor**: Cliente solo tiene `10.8.3.10/32` en AllowedIPs
- ❌ **Cliente NO puede acceder a otros clientes**: No hay rutas para otras IPs

## Cómo Aplicar el Cambio

### Opción 1: Editar Manualmente el Archivo .conf
1. Edita el archivo `.conf` del cliente
2. Cambia `AllowedIPs = 10.8.3.1/32` a `AllowedIPs = 10.8.3.10/32`
3. Elimina las líneas `PostUp` y `PostDown`
4. Guarda el archivo
5. Reinicia WireGuard en el cliente:
   ```powershell
   # Windows
   wg-quick down "WireGuard"
   wg-quick up "WireGuard"
   ```

### Opción 2: Regenerar desde el Dashboard
1. Ve al dashboard → VPN
2. Elimina el túnel 10.8.3.10
3. Crea un nuevo túnel con el mismo nombre
4. Descarga el nuevo archivo .conf (ya tendrá la configuración correcta)
5. Reemplaza el archivo en el cliente y reinicia WireGuard

