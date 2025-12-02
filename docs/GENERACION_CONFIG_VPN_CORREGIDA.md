# Generación de Configuración VPN Corregida

## Problema Identificado

El sistema generaba configuraciones VPN incorrectas:
- ❌ `AllowedIPs = {client_ip}/32` (cliente solo podía acceder a sí mismo)
- ❌ Faltaba `ListenPort`
- ❌ Faltaba `MTU = 1420`
- ❌ Usaba `DNS = 8.8.8.8` en lugar de `1.1.1.1`

## Solución Implementada

Ahora el sistema genera configuraciones basadas en el **modelo funcional de 10.8.3.10**:

### Configuración Correcta para Clientes 10.8.3.x

```ini
[Interface]
PrivateKey = {client_private_key}
ListenPort = 51830
Address = {client_ip}/24
DNS = 1.1.1.1
MTU = 1420

[Peer]
PublicKey = {server_public_key}
AllowedIPs = 10.8.3.1/32
Endpoint = {server_endpoint}
PersistentKeepalive = 25
```

### Cambios Clave

1. **AllowedIPs**: Ahora es `{server_ip}/32` (servidor) en lugar de `{client_ip}/32` (cliente)
   - ✅ Cliente puede acceder al servidor (10.8.3.1)
   - ❌ Cliente NO puede acceder a otros clientes (10.8.3.x)

2. **ListenPort**: Agregado automáticamente
   - Para 10.8.3.x: `51830`
   - Para otras redes: Usa el puerto del servidor

3. **MTU**: Agregado `1420` (estándar para WireGuard)

4. **DNS**: Cambiado a `1.1.1.1` (Cloudflare, más rápido)

5. **NO PostUp/PostDown**: Clientes simples no necesitan rutas manuales

## Archivos Modificados

### 1. `manu/apps/sistema_analitico/services/wireguard_manager.py`

**Método `create_client_config`**:
- Detecta la red base (ej: "10.8.3" desde "10.8.3.1")
- Genera `AllowedIPs = {server_ip}/32` (servidor, no cliente)
- Agrega `ListenPort`, `MTU`, `DNS` correctos
- NO incluye PostUp/PostDown (es cliente, no servidor)

### 2. `manu/apps/sistema_analitico/views.py`

**Métodos actualizados**:
- `download_config`: Genera configs correctos incluso para peers importados
- `read_config`: Muestra configs correctos en la pestaña VPN

## Comportamiento Actual

### Al Crear un Nuevo Túnel VPN

1. El sistema genera automáticamente:
   - Claves privada/pública
   - IP disponible en la red del servidor
   - Configuración `.conf` completa y funcional

2. El usuario solo necesita:
   - Descargar el `.conf`
   - Importarlo en WireGuard
   - ✅ **Ya funciona inmediatamente** (sin editar nada)

### Ejemplo de Configuración Generada

Para un cliente nuevo en 10.8.3.x:

```ini
[Interface]
PrivateKey = abc123...xyz789
ListenPort = 51830
Address = 10.8.3.11/24
DNS = 1.1.1.1
MTU = 1420

[Peer]
PublicKey = UPgAgldMaBpK9/cAGh3C5+HXkX+n4NtHqAbQjkfL3h0=
AllowedIPs = 10.8.3.1/32
Endpoint = 198.7.113.197:46587
PersistentKeepalive = 25
```

## Verificación

Después de importar la configuración:

```powershell
# ✅ Debe funcionar - puede acceder al servidor
ping 10.8.3.1

# ❌ NO debe funcionar - NO puede acceder a otros clientes
ping 10.8.3.10
ping 10.8.3.100
```

## Compatibilidad

- ✅ Funciona para redes 10.8.3.x (puerto 51830)
- ✅ Funciona para otras redes (usa puerto del servidor)
- ✅ Detecta automáticamente la red base del servidor
- ✅ Genera configs listos para usar sin edición manual

## Notas Importantes

1. **No se requiere PostUp/PostDown** porque:
   - El cliente es simple (no servidor)
   - WireGuard maneja el enrutamiento automáticamente
   - `AllowedIPs` es suficiente para controlar el acceso

2. **El servidor puede acceder a todos los clientes** porque:
   - Es el servidor principal del túnel
   - Tiene `AllowedIPs = {client_ip}/32` en su configuración
   - Puede ver todos los peers conectados

3. **Los clientes solo pueden acceder al servidor** porque:
   - `AllowedIPs = {server_ip}/32` limita el acceso
   - No tienen rutas a otros clientes
   - Están aislados entre sí

