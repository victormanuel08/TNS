# Comparación de Configuraciones WireGuard

## Configuración 10.8.1.x (FUNCIONA) ✅

```ini
[Interface]
Address = 10.8.1.1/24
PostUp = netsh interface ip add route 10.8.1.0/24 "WireGuard" 10.8.1.1
PostDown = netsh interface ip delete route 10.8.1.0/24 "WireGuard" 10.8.1.1

[Peer]
AllowedIPs = 10.8.1.250/32
```

**Resultado:**
- ✅ Puede hacer ping a 10.8.1.1 (servidor)
- ❌ NO puede hacer ping a 10.8.1.3 (otros clientes)

## Configuración 10.8.3.10 (DEBE SER IGUAL)

Para que funcione igual que 10.8.1.x, usa:

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
Endpoint = 198.7.113.197:46587
AllowedIPs = 10.8.3.1/32
PersistentKeepalive = 25
```

**Diferencias clave:**
- `PostUp` con ruta a `10.8.3.0/24` (toda la red, como en 10.8.1.x)
- `AllowedIPs = 10.8.3.1/32` (solo el servidor, como en 10.8.1.x que tiene 10.8.1.250/32)

## Verificación Esperada

Después de aplicar esta configuración:

```powershell
# ✅ Debe funcionar
ping 10.8.3.1

# ❌ NO debe funcionar (como 10.8.1.3)
ping 10.8.3.100
ping 10.8.3.11
```

## Nota sobre PostUp/PostDown

Si el servicio se reinicia con PostUp/PostDown, verifica:

1. **El nombre de la interfaz**: Puede no ser "WireGuard"
   ```powershell
   Get-NetAdapter | Where-Object { $_.InterfaceDescription -like "*WireGuard*" } | Select-Object Name
   ```

2. **Reemplaza "WireGuard"** en PostUp/PostDown con el nombre real de la interfaz

3. **O prueba sin PostUp/PostDown primero** y agrega la ruta manualmente después de conectar

