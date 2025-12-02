# Troubleshooting: WireGuard se Reinicia en Windows

## Problema

El servicio de WireGuard se reinicia constantemente después de aplicar la nueva configuración.

## Soluciones

### Solución 1: Configuración Simple (Sin PostUp/PostDown)

Primero prueba con una configuración simple sin PostUp/PostDown:

```ini
[Interface]
PrivateKey = cNTGgpDdZYiWVDgIdxtbnPbzd85IquNSxy5pDZjpu3E=
ListenPort = 51830
Address = 10.8.3.10/24
DNS = 1.1.1.1
MTU = 1420

[Peer]
PublicKey = UPgAgldMaBpK9/cAGh3C5+HXkX+n4NtHqAbQjkfL3h0=
Endpoint = 198.7.113.197:46587
AllowedIPs = 10.8.3.1/32, 10.8.3.10/32
PersistentKeepalive = 25
```

**Prueba esta primero**. Si funciona, luego agregamos PostUp/PostDown.

### Solución 2: Verificar Nombre de la Interfaz

El problema puede ser que el nombre de la interfaz en PostUp/PostDown no coincide. Verifica el nombre real:

```powershell
# Ver todas las interfaces de red
Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object Name, InterfaceDescription

# Buscar específicamente WireGuard
Get-NetAdapter | Where-Object { $_.Name -like "*WireGuard*" -or $_.InterfaceDescription -like "*WireGuard*" }
```

El nombre puede ser:
- `WireGuard`
- `wg0`
- `WireGuard Tunnel`
- O algo diferente

### Solución 3: PostUp/PostDown con PowerShell (Más Confiable)

Si necesitas PostUp/PostDown, usa PowerShell en lugar de netsh:

```ini
[Interface]
PrivateKey = cNTGgpDdZYiWVDgIdxtbnPbzd85IquNSxy5pDZjpu3E=
ListenPort = 51830
Address = 10.8.3.10/24
DNS = 1.1.1.1
MTU = 1420
PostUp = powershell -Command "New-NetRoute -DestinationPrefix 10.8.3.1/32 -InterfaceAlias WireGuard -NextHop 10.8.3.10 -ErrorAction SilentlyContinue"
PostDown = powershell -Command "Remove-NetRoute -DestinationPrefix 10.8.3.1/32 -InterfaceAlias WireGuard -Confirm:$false -ErrorAction SilentlyContinue"

[Peer]
PublicKey = UPgAgldMaBpK9/cAGh3C5+HXkX+n4NtHqAbQjkfL3h0=
Endpoint = 198.7.113.197:46587
AllowedIPs = 10.8.3.1/32, 10.8.3.10/32
PersistentKeepalive = 25
```

**IMPORTANTE**: Reemplaza `WireGuard` con el nombre real de tu interfaz (del paso anterior).

### Solución 4: Agregar Ruta Manualmente (Sin PostUp/PostDown)

Si PostUp/PostDown causa problemas, puedes agregar la ruta manualmente después de conectar:

1. **Conecta WireGuard** (sin PostUp/PostDown en la configuración)
2. **Agrega la ruta manualmente**:

```powershell
# Ver el nombre real de la interfaz
$interface = Get-NetAdapter | Where-Object { $_.InterfaceDescription -like "*WireGuard*" } | Select-Object -First 1 -ExpandProperty Name

# Agregar ruta
New-NetRoute -DestinationPrefix 10.8.3.1/32 -InterfaceAlias $interface -NextHop 10.8.3.10
```

3. **Verificar que funciona**:
```powershell
ping 10.8.3.1
```

### Solución 5: Ver Logs de WireGuard

Para ver qué error está causando el reinicio:

1. Abre **Visor de eventos de Windows** (`eventvwr.msc`)
2. Ve a **Registros de Windows** → **Aplicación**
3. Busca eventos relacionados con WireGuard
4. Revisa los errores

O desde PowerShell:

```powershell
Get-EventLog -LogName Application -Source "*WireGuard*" -Newest 20 | Format-List
```

## Pasos Recomendados

1. **Primero**: Prueba la configuración simple (Solución 1) - sin PostUp/PostDown
2. **Verifica conectividad**: `ping 10.8.3.1` desde Windows
3. **Si funciona**: Prueba agregar la ruta manualmente (Solución 4)
4. **Si necesitas PostUp/PostDown**: Usa PowerShell (Solución 3) con el nombre correcto de la interfaz

## Configuración Mínima que Debe Funcionar

```ini
[Interface]
PrivateKey = cNTGgpDdZYiWVDgIdxtbnPbzd85IquNSxy5pDZjpu3E=
Address = 10.8.3.10/24
DNS = 1.1.1.1

[Peer]
PublicKey = UPgAgldMaBpK9/cAGh3C5+HXkX+n4NtHqAbQjkfL3h0=
Endpoint = 198.7.113.197:46587
AllowedIPs = 10.8.3.1/32, 10.8.3.10/32
PersistentKeepalive = 25
```

Esta configuración mínima debería funcionar sin problemas. Luego puedes agregar PostUp/PostDown si es necesario.

