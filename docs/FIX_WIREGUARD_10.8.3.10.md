# Corrección de Configuración WireGuard 10.8.3.10

## Problema Actual

- ❌ El VPS (10.8.3.1) NO puede hacer ping a Windows (10.8.3.10)
- ❌ Windows (10.8.3.10) NO puede hacer ping al VPS (10.8.3.1)
- ✅ La red 10.8.1.x funciona correctamente

## Comparación de Configuraciones

### Red 10.8.1.x (FUNCIONA) ✅
```ini
[Interface]
Address = 10.8.1.1/24
PostUp = netsh interface ip add route 10.8.1.0/24 "WireGuard" 10.8.1.1
PostDown = netsh interface ip delete route 10.8.1.0/24 "WireGuard" 10.8.1.1

[Peer]
AllowedIPs = 10.8.1.250/32  # ✅ Puede acceder al servidor
```

### Red 10.8.3.x (NO FUNCIONA) ❌
```ini
[Interface]
Address = 10.8.3.10/24
# ❌ FALTA PostUp y PostDown

[Peer]
AllowedIPs = 10.8.3.10/32  # ❌ Solo su propia IP, no puede acceder al servidor
```

## Solución

### Objetivo
- ✅ VPS (10.8.3.1) puede acceder completamente a Windows (10.8.3.10)
- ✅ Windows (10.8.3.10) puede acceder al VPS (10.8.3.1)
- ❌ Windows (10.8.3.10) NO puede acceder a otros clientes (10.8.3.x)

### Configuración Correcta para Windows (10.8.3.10)

```ini
[Interface]
PrivateKey = cNTGgpDdZYiWVDgIdxtbnPbzd85IquNSxy5pDZjpu3E=
ListenPort = 51830
Address = 10.8.3.10/24
DNS = 1.1.1.1
MTU = 1420
PostUp = netsh interface ip add route 10.8.3.1/32 "WireGuard" 10.8.3.10
PostDown = netsh interface ip delete route 10.8.3.1/32 "WireGuard" 10.8.3.10

[Peer]
PublicKey = UPgAgldMaBpK9/cAGh3C5+HXkX+n4NtHqAbQjkfL3h0=
AllowedIPs = 10.8.3.1/32, 10.8.3.10/32
PersistentKeepalive = 25
```

**Cambios clave:**
1. ✅ `PostUp` y `PostDown` agregados (como en 10.8.1.x)
2. ✅ `AllowedIPs = 10.8.3.1/32, 10.8.3.10/32` (puede acceder al servidor y a sí mismo)
3. ✅ La ruta es específica para 10.8.3.1/32 (no toda la red 10.8.3.0/24)

### Verificar Configuración del Servidor WireGuard

En el servidor VPS, verifica que el peer esté configurado correctamente:

```bash
# Ver configuración de WireGuard
sudo wg show wg-main
# O el nombre de tu interfaz WireGuard

# Debe mostrar algo como:
# peer: [clave_publica_del_cliente]
#   allowed ips: 10.8.3.10/32
```

Si el servidor NO tiene el peer configurado, necesitas agregarlo:

```bash
# En el servidor VPS
sudo wg set wg-main peer [CLAVE_PUBLICA_DEL_CLIENTE] allowed-ips 10.8.3.10/32

# Guardar la configuración permanentemente
sudo wg-quick save wg-main
```

## Cómo Aplicar los Cambios

### Paso 1: Editar la configuración en Windows

1. Abre WireGuard en Windows
2. Haz clic derecho en el túnel "10.8.3.10" → **Editar**
3. Reemplaza el contenido con la configuración correcta (arriba)
4. Guarda el archivo

### Paso 2: Reiniciar el túnel

1. Desconecta el túnel (si está conectado)
2. Conecta el túnel nuevamente
3. O reinicia WireGuard

### Paso 3: Verificar desde Windows

```powershell
# Debe funcionar ahora
ping 10.8.3.1
```

### Paso 4: Verificar desde el VPS

```bash
# Debe funcionar ahora
ping 10.8.3.10
telnet 10.8.3.10 3050
```

## Diferencia Clave con 10.8.1.x

La configuración de 10.8.1.x tiene:
- `PostUp = netsh interface ip add route 10.8.1.0/24` (toda la red)
- `AllowedIPs = 10.8.1.250/32` (solo el servidor)

La configuración de 10.8.3.10 debe tener:
- `PostUp = netsh interface ip add route 10.8.3.1/32` (solo el servidor, más específico)
- `AllowedIPs = 10.8.3.1/32, 10.8.3.10/32` (servidor + sí mismo)

Esto permite:
- ✅ Comunicación bidireccional entre 10.8.3.1 y 10.8.3.10
- ❌ NO permite acceso a otros clientes (10.8.3.x)

