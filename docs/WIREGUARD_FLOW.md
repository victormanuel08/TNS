# Flujo de Creación de Túnel VPN (WireGuard)

## ¿Qué pasa cuando creas un nuevo túnel VPN?

### Paso 1: Crear el Túnel (Frontend → Backend)

Cuando haces clic en "Crear Túnel" en el admin panel:

1. **Frontend envía**:
   ```json
   {
     "nombre": "DEPO",
     "ip_address": "10.8.3.11",  // Opcional, si no se envía se asigna automáticamente
     "activo": true,
     "notas": ""
   }
   ```

### Paso 2: Backend Procesa la Solicitud

El backend (`VpnConfigViewSet.create`) ejecuta:

#### 2.1. Genera las Claves (en el servidor WireGuard vía SSH)
```python
# Se conecta al servidor WireGuard vía SSH
# Ejecuta: wg genkey
private_key = "clave_privada_generada_en_el_servidor"

# Ejecuta: echo "clave_privada" | wg pubkey
public_key = "clave_publica_generada_desde_la_privada"
```

**⚠️ IMPORTANTE**: Las claves se generan **en el servidor WireGuard**, no en el backend Django.

#### 2.2. Asigna IP
- Si enviaste `ip_address`: usa esa IP
- Si no enviaste IP: busca la siguiente IP disponible en el rango (ej: `10.8.3.11`)

#### 2.3. Genera el Archivo .conf
```python
config_content = """
[Interface]
PrivateKey = clave_privada_generada
Address = 10.8.3.11/24
DNS = 8.8.8.8

[Peer]
PublicKey = clave_publica_del_servidor
Endpoint = IP_PUBLICA:51820
AllowedIPs = 10.8.3.11/32
PersistentKeepalive = 25
"""
```

#### 2.4. Guarda el Archivo .conf
- Guarda en: `/tmp/wireguard_configs/depo.conf` (en el servidor donde está Django)
- Guarda la ruta en la base de datos

#### 2.5. Agrega el Peer al Servidor WireGuard
```bash
# Ejecuta vía SSH en el servidor WireGuard:
sudo wg set wg-main peer "clave_publica_del_cliente" allowed-ips 10.8.3.11/32
```

**✅ En este momento, el peer ya está configurado en el servidor WireGuard.**

#### 2.6. Guarda en la Base de Datos
```python
VpnConfig.objects.create(
    nombre="DEPO",
    ip_address="10.8.3.11",
    public_key="clave_publica_del_cliente",
    private_key="clave_privada_del_cliente",  # Encriptada
    config_file_path="/tmp/wireguard_configs/depo.conf",
    activo=True
)
```

### Paso 3: Estado "Inactivo" vs "Activo"

**⚠️ CONFUSIÓN ACTUAL**:

- **`activo` en la BD**: Solo indica si el registro está marcado como activo en la base de datos
- **Peer en el servidor**: El peer **YA ESTÁ AGREGADO** al servidor WireGuard cuando se crea
- **Conexión real**: Depende de que el cliente:
  1. Descargue el archivo `.conf`
  2. Lo instale en su dispositivo
  3. Se conecte a la VPN

**El estado "Inactivo" en la tabla NO significa que el peer no esté en el servidor.**

### Paso 4: Descargar el Archivo .conf

Cuando haces clic en "Descargar":

1. **Si el archivo existe**: Lo lee y lo descarga
2. **Si el archivo no existe**: Lo regenera desde los datos de la BD
3. **Si no hay `private_key`** (peer sincronizado): Genera un template con placeholder

### Paso 5: Instalar en el Cliente

El cliente debe:

1. **Descargar** el archivo `.conf`
2. **Instalar** WireGuard en su dispositivo
3. **Importar** el archivo `.conf` en WireGuard
4. **Activar** la conexión VPN

**Solo entonces**:
- El peer se conecta al servidor
- Aparece en `wg show wg-main`
- Aparece como "Conectado" en el admin panel

## Resumen del Flujo

```
1. Usuario crea túnel "DEPO" con IP 10.8.3.11
   ↓
2. Backend genera claves en servidor WireGuard (vía SSH)
   ↓
3. Backend asigna IP 10.8.3.11
   ↓
4. Backend genera archivo .conf con configuración completa
   ↓
5. Backend agrega peer al servidor: wg set wg-main peer ... allowed-ips 10.8.3.11/32
   ✅ Peer YA ESTÁ EN EL SERVIDOR (aunque aparezca "Inactivo")
   ↓
6. Backend guarda todo en BD (claves, IP, ruta del .conf)
   ↓
7. Usuario descarga .conf
   ↓
8. Cliente instala .conf en su dispositivo
   ↓
9. Cliente se conecta a la VPN
   ↓
10. Aparece como "Conectado" en el admin panel
```

## Preguntas Frecuentes

### ¿Por qué aparece "Inactivo" si el peer ya está en el servidor?

El campo `activo` en la BD solo indica si el registro está marcado como activo. **No indica si el cliente está conectado**.

Para saber si está conectado, revisa la columna **"Conexión"** que muestra:
- **"Conectado"**: El cliente está conectado (último handshake < 3 minutos)
- **"Desconectado"**: El cliente no está conectado (último handshake > 3 minutos o nunca)

### ¿Qué pasa si el archivo .conf se borra?

No pasa nada. El archivo se regenera automáticamente cuando lo descargas, usando los datos de la BD.

### ¿Puedo cambiar la IP después de crear el túnel?

Sí, pero necesitarías:
1. Actualizar la IP en la BD
2. Actualizar el peer en el servidor WireGuard
3. Regenerar el archivo .conf

**⚠️ Esto no está implementado actualmente en la UI.**

### ¿Qué pasa si el cliente nunca descarga el .conf?

El peer sigue estando configurado en el servidor, pero nunca se conectará porque el cliente no tiene la configuración.

## Mejoras Sugeridas

1. **Cambiar "Estado" por "Registro"**: Mostrar "Activo/Inactivo" solo para el registro en BD
2. **Separar "Conexión"**: Ya está implementado, muestra si está conectado o no
3. **Indicador visual**: Mostrar un badge diferente si el peer está en el servidor pero nunca se conectó

