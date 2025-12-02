# Eliminar y Regenerar Configuración VPN

## ¿Qué Pasa si Eliminas el Archivo .conf?

### Escenario: Eliminar solo el archivo .conf (NO el registro VPN)

1. **El registro en la BD sigue existiendo**:
   - ✅ `VpnConfig` con `nombre`, `ip_address`, `public_key`, `private_key`
   - ✅ Las claves están **encriptadas** en la BD
   - ❌ Solo se elimina la ruta del archivo (`config_file_path = None`)

2. **Al descargar/regenerar**:
   - ✅ El sistema **SIEMPRE regenera** el archivo .conf
   - ✅ Usa las **MISMAS claves** guardadas en BD
   - ✅ La peer es **LA MISMA** (no cambia)

## Flujo de Regeneración

### Si el registro tiene `private_key` (creado por el sistema):

```python
# El método download_config usa:
vpn_config.private_key  # ← MISMA clave guardada en BD
vpn_config.public_key   # ← MISMA clave guardada en BD
vpn_config.ip_address   # ← MISMA IP asignada

# Regenera el .conf con las MISMAS claves
config_content = wg_manager.create_client_config(
    client_private_key=vpn_config.private_key,  # ← MISMA
    client_public_key=vpn_config.public_key,    # ← MISMA
    client_ip=vpn_config.ip_address            # ← MISMA
)
```

**Resultado:**
- ✅ Archivo .conf nuevo (regenerado)
- ✅ **MISMA peer** (mismas claves)
- ✅ **MISMA IP** (10.8.3.10, etc.)
- ✅ **MISMA configuración** en el servidor WireGuard

### Si el registro NO tiene `private_key` (peer importado):

- Genera un template con `PrivateKey = TU_CLAVE_PRIVADA_AQUI`
- Debes agregar manualmente la clave privada que usaste para generar la `public_key`

## Respuestas a tus Preguntas

### 1. ¿Se crea uno nuevo?

**Sí**, se crea un nuevo archivo .conf, pero con las **MISMAS claves**.

### 2. ¿La peer sería diferente?

**NO**, la peer es **LA MISMA** porque:
- Usa `vpn_config.private_key` guardada en BD
- Usa `vpn_config.public_key` guardada en BD
- El servidor WireGuard tiene registrada la misma `public_key`

### 3. ¿Debería volver a importarla en Windows?

**Sí**, debes:
1. Descargar el nuevo archivo .conf
2. Importarlo en WireGuard (reemplaza el anterior)
3. ✅ Funcionará inmediatamente (misma peer, misma IP)

### 4. ¿Así estarían seguros?

**Sí, completamente seguro** porque:
- ✅ Las claves están **encriptadas** en BD (`EncryptedTextField`)
- ✅ La peer es **LA MISMA** (no cambia)
- ✅ El servidor WireGuard tiene la **MISMA configuración**
- ✅ Solo se regenera el archivo .conf con las mismas claves

## Ejemplo Práctico

### Situación Inicial:
```
BD: VpnConfig
  - nombre: "Windows Server"
  - ip_address: "10.8.3.10"
  - private_key: "abc123...xyz" (encriptada)
  - public_key: "def456...uvw"
  - config_file_path: "/tmp/wireguard_configs/windows_server.conf"
```

### Después de Eliminar el .conf:
```
BD: VpnConfig (SIGUE EXISTIENDO)
  - nombre: "Windows Server"
  - ip_address: "10.8.3.10"
  - private_key: "abc123...xyz" (encriptada) ← SIGUE AQUÍ
  - public_key: "def456...uvw" ← SIGUE AQUÍ
  - config_file_path: None ← Solo esto cambia
```

### Después de Descargar/Regenerar:
```
Archivo: /tmp/wireguard_configs/windows_server.conf (NUEVO)
  - PrivateKey = "abc123...xyz" ← MISMA CLAVE
  - PublicKey = "def456...uvw" ← MISMA CLAVE
  - Address = 10.8.3.10/24 ← MISMA IP
```

## Método Correcto

1. **Eliminar el .conf** (opcional, solo si quieres limpiar archivos)
2. **Descargar/Regenerar** desde la pestaña VPN
3. **Importar en Windows** (reemplaza el anterior)
4. ✅ **Funciona inmediatamente** (misma peer, misma IP)

## Seguridad

- ✅ **Claves encriptadas** en BD
- ✅ **Misma peer** (no se genera nueva)
- ✅ **Misma IP** (no cambia)
- ✅ **Misma configuración** en servidor
- ✅ **Solo se regenera el archivo** .conf

## Nota Importante

Si eliminas el **registro completo** (no solo el archivo):
- ❌ Se pierden las claves
- ❌ Se pierde la peer
- ❌ Debes crear una nueva configuración VPN
- ❌ El servidor WireGuard debe actualizarse

**Por eso es importante**: Solo eliminar el archivo .conf, NO el registro VPN completo.

