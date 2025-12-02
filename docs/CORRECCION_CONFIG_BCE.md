# Corrección del Config BCE

## Config Descargado (INCORRECTO - Versión Antigua)

```ini
[Interface]
PrivateKey = TU_CLAVE_PRIVADA_AQUI
Address = 10.8.3.10/24
DNS = 8.8.8.8  # ❌ Incorrecto

[Peer]
PublicKey = UPgAgldMaBpK9/cAGh3C5+HXkX+n4NtHqAbQjkfL3h0=
Endpoint = 198.7.113.197:46587
AllowedIPs = 10.8.3.10/32  # ❌ Incorrecto (solo su propia IP)
PersistentKeepalive = 25
```

**Problemas:**
- ❌ `AllowedIPs = 10.8.3.10/32` (solo su propia IP, no puede acceder al servidor)
- ❌ `DNS = 8.8.8.8` (debería ser 1.1.1.1)
- ❌ Falta `ListenPort = 51830`
- ❌ Falta `MTU = 1420`

## Config Corregido (CORRECTO)

```ini
[Interface]
PrivateKey = TU_CLAVE_PRIVADA_AQUI
ListenPort = 51830
Address = 10.8.3.10/24
DNS = 1.1.1.1
MTU = 1420

[Peer]
PublicKey = UPgAgldMaBpK9/cAGh3C5+HXkX+n4NtHqAbQjkfL3h0=
AllowedIPs = 10.8.3.1/32
Endpoint = 198.7.113.197:46587
PersistentKeepalive = 25
```

**Correcciones:**
- ✅ `AllowedIPs = 10.8.3.1/32` (puede acceder al servidor)
- ✅ `DNS = 1.1.1.1` (Cloudflare, más rápido)
- ✅ `ListenPort = 51830` (agregado)
- ✅ `MTU = 1420` (agregado)

## Cómo Usar

1. **Copia el config corregido** (arriba)
2. **Reemplaza `TU_CLAVE_PRIVADA_AQUI`** con tu clave privada real
3. **Guarda como** `BCE.conf`
4. **Importa en WireGuard**

## Nota

Si vuelves a descargar el config desde la pestaña VPN, ahora saldrá **automáticamente corregido** porque el código ya está actualizado.

## Verificación

Después de importar:

```powershell
# ✅ Debe funcionar - puede acceder al servidor
ping 10.8.3.1

# ❌ NO debe funcionar - NO puede acceder a otros clientes
ping 10.8.3.100
```

