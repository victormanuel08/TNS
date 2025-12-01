# Configuración de Red WireGuard - EDDESO

## Arquitectura de Red

### Objetivo
- ✅ **Servidor puede acceder a los locales**: El servidor puede iniciar conexiones a cualquier cliente
- ❌ **Locales NO pueden acceder al servidor**: Los clientes no pueden iniciar conexiones al servidor
- ❌ **Locales NO pueden ver otros locales**: Los clientes no pueden comunicarse entre sí

### Configuración Actual

#### En el Servidor (wg-main)
```ini
[Interface]
Address = 10.8.3.1/24
ListenPort = 46587

[Peer]
# Cliente 1
PublicKey = NF7X9XclWLO865H6ylmnN699ZLa1BzaVPx/z21j1NyY=
AllowedIPs = 10.8.3.10/32  # Servidor puede acceder a este cliente

[Peer]
# Cliente 2
PublicKey = APStRrDn74tFdsCNywG8yfsgjdVWRfdIz4AeUV3FtQA=
AllowedIPs = 10.8.3.100/32  # Servidor puede acceder a este cliente
```

#### En el Cliente (archivo .conf generado)
```ini
[Interface]
PrivateKey = <clave_privada_cliente>
Address = 10.8.3.X/24
DNS = 8.8.8.8

[Peer]
PublicKey = <clave_publica_servidor>
Endpoint = 198.7.113.197:46587
AllowedIPs = 10.8.3.X/32  # Solo su propia IP - NO puede acceder al servidor ni otros clientes
PersistentKeepalive = 25
```

## ¿Cómo Funciona?

### 1. Servidor → Cliente (✅ Permitido)
- El servidor tiene `AllowedIPs = 10.8.3.10/32` para el cliente
- El servidor puede iniciar conexiones TCP/UDP al cliente
- El cliente puede responder (porque WireGuard es bidireccional para conexiones establecidas)

### 2. Cliente → Servidor (❌ Bloqueado)
- El cliente tiene `AllowedIPs = 10.8.3.X/32` (solo su IP)
- El cliente NO puede iniciar conexiones al servidor (10.8.3.1)
- El cliente NO puede acceder a otros clientes (10.8.3.10, 10.8.3.100, etc.)

### 3. Cliente → Cliente (❌ Bloqueado)
- Cada cliente solo tiene `AllowedIPs = su_IP/32`
- No pueden acceder a otras IPs de la red VPN
- No pueden comunicarse entre sí

## Ejemplo de Uso

### Caso de Uso: Datafono Local
```
Servidor (Nube) → Cliente Local (10.8.3.10)
  - Servidor puede llamar a API del datafono: http://10.8.3.10:8080
  - Cliente puede responder a esas peticiones
  - Cliente NO puede iniciar conexiones al servidor
  - Cliente NO puede acceder a otros clientes
```

## Verificación

### Desde el Servidor
```bash
# Ver configuración del servidor
sudo wg show wg-main

# Probar conexión a un cliente
ping 10.8.3.10  # Debe funcionar
curl http://10.8.3.10:8080  # Debe funcionar
```

### Desde el Cliente
```bash
# Ver configuración del cliente
sudo wg show

# Intentar acceder al servidor (NO debe funcionar)
ping 10.8.3.1  # NO debe funcionar
curl http://10.8.3.1  # NO debe funcionar

# Intentar acceder a otro cliente (NO debe funcionar)
ping 10.8.3.100  # NO debe funcionar
```

## Notas Importantes

1. **WireGuard es bidireccional para conexiones establecidas**: Si el servidor inicia una conexión, el cliente puede responder. Pero el cliente NO puede iniciar conexiones.

2. **AllowedIPs controla el enrutamiento**: Solo el tráfico destinado a las IPs en AllowedIPs se enruta por el túnel VPN.

3. **Firewall adicional**: Si necesitas más control, puedes usar iptables en el servidor para bloquear conexiones entrantes desde los clientes.

4. **Cambios en la configuración**: Si cambias AllowedIPs en un cliente, necesitas reiniciar la interfaz WireGuard:
   ```bash
   sudo wg-quick down wg0
   sudo wg-quick up wg0
   ```

