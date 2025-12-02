# Configuración de Firebird en Windows para Acceso desde VPS

## Problema

El VPS (10.8.3.1) no puede conectarse al servidor Firebird en Windows (10.8.3.10) en el puerto 3050.

## Solución Completa

### Paso 1: Verificar que Firebird esté corriendo

En Windows, abre PowerShell como **Administrador** y ejecuta:

```powershell
# Verificar servicio Firebird
Get-Service -Name "*Firebird*"

# Si no está corriendo, iniciarlo:
Start-Service -Name "FirebirdServerDefaultInstance"
# O el nombre exacto del servicio que aparezca
```

### Paso 2: Configurar Firebird para escuchar en todas las interfaces

Firebird por defecto puede estar escuchando solo en `localhost` (127.0.0.1). Necesitas configurarlo para que escuche en todas las interfaces (0.0.0.0).

1. **Encontrar el archivo de configuración:**
   ```powershell
   # Generalmente está en:
   C:\Program Files\Firebird\Firebird_3_0\firebird.conf
   # O
   C:\Program Files (x86)\Firebird\Firebird_3_0\firebird.conf
   ```

2. **Editar firebird.conf:**
   - Abre el archivo como Administrador
   - Busca la línea `#RemoteBindAddress = localhost`
   - Cámbiala a: `RemoteBindAddress = 0.0.0.0`
   - Guarda el archivo

3. **Reiniciar Firebird:**
   ```powershell
   Restart-Service -Name "FirebirdServerDefaultInstance"
   ```

### Paso 3: Configurar Firewall de Windows

Necesitas permitir conexiones entrantes en el puerto 3050 **solo desde la IP del VPS (10.8.3.1)**.

#### Opción A: Usando PowerShell (Recomendado)

Ejecuta como **Administrador**:

```powershell
# Crear regla para permitir conexiones desde 10.8.3.1
New-NetFirewallRule -DisplayName "Firebird - Permitir desde VPS 10.8.3.1" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 3050 `
    -RemoteAddress 10.8.3.1 `
    -Action Allow `
    -Enabled True `
    -Profile Any
```

#### Opción B: Usando Interfaz Gráfica

1. Abre **Firewall de Windows Defender con seguridad avanzada**
   - Presiona `Win + R`
   - Escribe: `wf.msc`
   - Presiona Enter

2. Crea una nueva regla entrante:
   - Clic derecho en "Reglas de entrada" → "Nueva regla..."
   - Tipo: **Puerto**
   - Protocolo: **TCP**
   - Puertos específicos: **3050**
   - Acción: **Permitir la conexión**
   - Perfiles: Marca todos (Dominio, Privada, Pública)
   - Nombre: "Firebird - Permitir desde VPS 10.8.3.1"

3. **IMPORTANTE**: Después de crear la regla:
   - Haz doble clic en la regla recién creada
   - Ve a la pestaña **Ámbito**
   - En "Direcciones IP remotas", selecciona "Estas direcciones IP"
   - Agrega: **10.8.3.1**
   - Acepta

### Paso 4: Verificar WireGuard

Asegúrate de que WireGuard esté activo y conectado en Windows:

```powershell
# Verificar que WireGuard esté activo
Get-NetAdapter | Where-Object { $_.Name -like "*WireGuard*" }

# Verificar IP asignada
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like "10.8.3.*" }
```

Deberías ver que tienes la IP **10.8.3.10** asignada.

### Paso 5: Verificar desde el VPS

En el VPS, ejecuta:

```bash
# Verificar que puedes hacer ping al servidor Windows
ping -c 4 10.8.3.10

# Verificar que el puerto 3050 esté abierto
telnet 10.8.3.10 3050
# O
nc -zv 10.8.3.10 3050
```

Si ambos comandos funcionan, la conectividad está correcta.

## Script Automatizado

He creado un script PowerShell que verifica todo automáticamente:

```powershell
# Ejecutar como Administrador
cd C:\ruta\al\proyecto\docs\scripts
.\check_windows_firewall.ps1
```

O descarga y ejecuta el script desde el repositorio.

## Verificación de Reglas para 10.8.1.1

Si también necesitas verificar reglas para otra IP (10.8.1.1), puedes usar:

```powershell
# Ver todas las reglas que mencionan 10.8.1.1
Get-NetFirewallRule | Where-Object { 
    $_.DisplayName -like "*10.8.1.1*" 
} | Format-Table DisplayName, Enabled, Direction

# Ver reglas con direcciones remotas específicas
Get-NetFirewallAddressFilter | Where-Object { 
    $_.RemoteAddress -like "*10.8.1.1*" 
} | Get-NetFirewallRule | Format-Table DisplayName, Enabled
```

## Troubleshooting

### Firebird no responde

1. **Verificar que Firebird esté escuchando:**
   ```powershell
   netstat -an | findstr "3050"
   ```
   Debe mostrar algo como: `TCP    0.0.0.0:3050    0.0.0.0:0    LISTENING`
   Si muestra `127.0.0.1:3050`, Firebird solo está escuchando en localhost.

2. **Verificar logs de Firebird:**
   - Revisa `C:\Program Files\Firebird\Firebird_3_0\firebird.log`
   - Busca errores de conexión

### Firewall bloquea la conexión

1. **Verificar reglas activas:**
   ```powershell
   Get-NetFirewallRule -DisplayName "*Firebird*" | Format-Table DisplayName, Enabled, Direction
   ```

2. **Probar deshabilitando temporalmente el firewall:**
   ```powershell
   # Solo para pruebas, NO en producción
   Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
   # Probar conexión
   # Luego volver a habilitar:
   Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
   ```

### WireGuard no está conectado

1. **Verificar estado de WireGuard:**
   - Abre la aplicación WireGuard
   - Verifica que el túnel esté "Activo"
   - Verifica que la IP asignada sea **10.8.3.10**

2. **Verificar configuración del túnel:**
   - El archivo `.conf` debe tener `AllowedIPs = 10.8.3.10/32`
   - NO debe tener `AllowedIPs = 10.8.3.1/32` (eso permitiría acceso al servidor)

## Resumen de Comandos Rápidos

### En Windows (PowerShell como Administrador):

```powershell
# 1. Verificar Firebird
Get-Service "*Firebird*"

# 2. Crear regla de firewall
New-NetFirewallRule -DisplayName "Firebird - Permitir desde VPS 10.8.3.1" -Direction Inbound -Protocol TCP -LocalPort 3050 -RemoteAddress 10.8.3.1 -Action Allow -Enabled True

# 3. Verificar IP VPN
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like "10.8.3.*" }

# 4. Verificar que Firebird escucha en todas las interfaces
netstat -an | findstr "3050"
```

### En el VPS (Linux):

```bash
# 1. Verificar conectividad
ping -c 4 10.8.3.10

# 2. Verificar puerto
nc -zv 10.8.3.10 3050

# 3. Verificar WireGuard
sudo wg show
```

