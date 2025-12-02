# Arquitectura WireGuard - Explicación Completa

## Dos Túneles Diferentes en Windows Server

Windows Server tiene **DOS túneles WireGuard diferentes**:

### Túnel 1: 10.8.1.x (Windows Server es el PRINCIPAL/SERVIDOR)
- **Windows Server IP**: 10.8.1.1
- **Rol**: Servidor principal del túnel
- **Puede ver**: Todos los clientes 10.8.1.x (porque es el servidor)
- **Configuración**: Tiene PostUp/PostDown con ruta a 10.8.1.0/24
- **AllowedIPs**: 10.8.1.250/32 (puede acceder al servidor VPS de ese túnel)

### Túnel 2: 10.8.3.x (Windows Server es CLIENTE)
- **Windows Server IP**: 10.8.3.10
- **Rol**: Cliente del túnel (el VPS 10.8.3.1 es el servidor)
- **Puede ver**: Solo 10.8.3.1 (el servidor VPS)
- **NO puede ver**: Otros clientes 10.8.3.x (10.8.3.100, etc.)
- **Configuración**: NO necesita PostUp/PostDown (es cliente, no servidor)
- **AllowedIPs**: 10.8.3.1/32 (solo el servidor VPS)

## Configuración Correcta para 10.8.3.10

Como Windows Server es **CLIENTE** en el túnel 10.8.3.x, la configuración debe ser **simple**:

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
AllowedIPs = 10.8.3.1/32
PersistentKeepalive = 25
```

**NO necesita PostUp/PostDown** porque:
- No es el servidor principal
- Solo necesita comunicarse con 10.8.3.1
- WireGuard maneja el enrutamiento automáticamente con AllowedIPs

## Verificación

### Desde Windows Server (10.8.3.10):

```powershell
# ✅ Debe funcionar - puede acceder al servidor VPS
ping 10.8.3.1

# ❌ NO debe funcionar - NO puede acceder a otros clientes
ping 10.8.3.100

# ✅ Debe funcionar - puede acceder a todos los 10.8.1.x (es servidor de ese túnel)
ping 10.8.1.1
ping 10.8.1.3
```

### Desde VPS (10.8.3.1):

```bash
# ✅ Debe funcionar - servidor puede acceder al cliente
ping 10.8.3.10

# ✅ Debe funcionar - servidor puede acceder a otros clientes
ping 10.8.3.100
```

## Resumen de la Arquitectura

```
TÚNEL 10.8.1.x:
Windows Server (10.8.1.1) [SERVIDOR PRINCIPAL]
  ├── Puede ver: Todos los 10.8.1.x
  └── Clientes: 10.8.1.3, 10.8.1.50, etc.

TÚNEL 10.8.3.x:
VPS (10.8.3.1) [SERVIDOR PRINCIPAL]
  ├── Puede ver: Todos los 10.8.3.x
  └── Clientes:
      ├── Windows Server (10.8.3.10) [CLIENTE]
      │   └── Solo puede ver: 10.8.3.1
      └── Otros clientes (10.8.3.100, etc.)
          └── Solo pueden ver: 10.8.3.1
```

## Por Qué NO Necesita PostUp/PostDown

En 10.8.1.x, Windows Server necesita PostUp/PostDown porque:
- Es el **servidor principal**
- Necesita enrutar tráfico para todos los clientes
- Tiene responsabilidades de enrutamiento

En 10.8.3.10, Windows Server NO necesita PostUp/PostDown porque:
- Es un **cliente simple**
- Solo necesita comunicarse con el servidor (10.8.3.1)
- WireGuard maneja el enrutamiento automáticamente
- `AllowedIPs = 10.8.3.1/32` es suficiente

## Configuración Final Recomendada

**Configuración SIMPLE sin PostUp/PostDown** (esta debería funcionar sin reiniciarse):

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
AllowedIPs = 10.8.3.1/32
PersistentKeepalive = 25
```

Esta configuración es la correcta para un **cliente** en WireGuard.

