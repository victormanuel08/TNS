# Script PowerShell para verificar y configurar firewall en Windows
# Ejecutar como Administrador

Write-Host "🔍 Verificación de Firewall y Firebird en Windows" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar que Firebird esté corriendo
Write-Host "1️⃣ Verificando servicio Firebird..." -ForegroundColor Yellow
$firebirdService = Get-Service -Name "*Firebird*" -ErrorAction SilentlyContinue
if ($firebirdService) {
    Write-Host "   ✅ Servicio Firebird encontrado: $($firebirdService.Name)" -ForegroundColor Green
    Write-Host "   Estado: $($firebirdService.Status)" -ForegroundColor $(if ($firebirdService.Status -eq 'Running') { 'Green' } else { 'Red' })
} else {
    Write-Host "   ❌ Servicio Firebird NO encontrado" -ForegroundColor Red
}

Write-Host ""

# 2. Verificar reglas de firewall existentes para el puerto 3050
Write-Host "2️⃣ Verificando reglas de firewall para puerto 3050..." -ForegroundColor Yellow
$firewallRules = Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*3050*" -or $_.DisplayName -like "*Firebird*" }
if ($firewallRules) {
    Write-Host "   Reglas encontradas:" -ForegroundColor Green
    foreach ($rule in $firewallRules) {
        Write-Host "   - $($rule.DisplayName) | Estado: $($rule.Enabled) | Dirección: $($rule.Direction)" -ForegroundColor Cyan
    }
} else {
    Write-Host "   ⚠️ No se encontraron reglas específicas para puerto 3050" -ForegroundColor Yellow
}

Write-Host ""

# 3. Verificar reglas para la red VPN (10.8.3.x)
Write-Host "3️⃣ Verificando reglas para red VPN (10.8.3.x)..." -ForegroundColor Yellow
$vpnRules = Get-NetFirewallRule | Where-Object { 
    $_.DisplayName -like "*10.8.3*" -or 
    $_.DisplayName -like "*VPN*" -or 
    $_.DisplayName -like "*WireGuard*" 
}
if ($vpnRules) {
    Write-Host "   Reglas VPN encontradas:" -ForegroundColor Green
    foreach ($rule in $vpnRules) {
        Write-Host "   - $($rule.DisplayName) | Estado: $($rule.Enabled)" -ForegroundColor Cyan
    }
} else {
    Write-Host "   ⚠️ No se encontraron reglas específicas para VPN" -ForegroundColor Yellow
}

Write-Host ""

# 4. Verificar interfaces de red
Write-Host "4️⃣ Verificando interfaces de red..." -ForegroundColor Yellow
$interfaces = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' }
foreach ($interface in $interfaces) {
    $ipConfig = Get-NetIPAddress -InterfaceIndex $interface.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue
    if ($ipConfig) {
        Write-Host "   $($interface.Name): $($ipConfig.IPAddress)" -ForegroundColor Cyan
        if ($ipConfig.IPAddress -like "10.8.3.*") {
            Write-Host "      ✅ Esta es la interfaz VPN (10.8.3.x)" -ForegroundColor Green
        }
    }
}

Write-Host ""

# 5. Crear regla de firewall para permitir conexiones desde 10.8.3.1
Write-Host "5️⃣ ¿Crear regla de firewall para permitir conexiones desde 10.8.3.1?" -ForegroundColor Yellow
Write-Host "   Esta regla permitirá que el servidor VPS (10.8.3.1) se conecte al puerto 3050" -ForegroundColor White
$createRule = Read-Host "   ¿Crear regla? (S/N)"

if ($createRule -eq 'S' -or $createRule -eq 's') {
    try {
        # Eliminar regla existente si existe
        Remove-NetFirewallRule -DisplayName "Firebird - Permitir desde VPS 10.8.3.1" -ErrorAction SilentlyContinue
        
        # Crear nueva regla
        New-NetFirewallRule -DisplayName "Firebird - Permitir desde VPS 10.8.3.1" `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort 3050 `
            -RemoteAddress 10.8.3.1 `
            -Action Allow `
            -Enabled True `
            -Profile Any
        
        Write-Host "   ✅ Regla creada exitosamente" -ForegroundColor Green
        Write-Host "   La regla permite conexiones TCP en puerto 3050 desde 10.8.3.1" -ForegroundColor Cyan
    } catch {
        Write-Host "   ❌ Error creando regla: $_" -ForegroundColor Red
    }
} else {
    Write-Host "   ⏭️ Saltando creación de regla" -ForegroundColor Yellow
}

Write-Host ""

# 6. Verificar configuración de Firebird
Write-Host "6️⃣ Verificando configuración de Firebird..." -ForegroundColor Yellow
$firebirdConfigPath = "C:\Program Files\Firebird\Firebird_3_0\firebird.conf"
if (Test-Path $firebirdConfigPath) {
    Write-Host "   ✅ Archivo de configuración encontrado: $firebirdConfigPath" -ForegroundColor Green
    $configContent = Get-Content $firebirdConfigPath | Select-String -Pattern "RemoteBindAddress|RemoteServicePort" -Context 0,2
    if ($configContent) {
        Write-Host "   Configuración relevante:" -ForegroundColor Cyan
        $configContent | ForEach-Object { Write-Host "   $_" -ForegroundColor White }
    } else {
        Write-Host "   ⚠️ No se encontraron configuraciones de RemoteBindAddress o RemoteServicePort" -ForegroundColor Yellow
        Write-Host "   Firebird puede estar escuchando solo en localhost (127.0.0.1)" -ForegroundColor Yellow
        Write-Host "   Necesitas configurar RemoteBindAddress = 0.0.0.0 en firebird.conf" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ⚠️ Archivo de configuración no encontrado en la ruta estándar" -ForegroundColor Yellow
    Write-Host "   Busca firebird.conf en la instalación de Firebird" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Verificación completada" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Resumen de acciones necesarias:" -ForegroundColor Cyan
Write-Host "   1. Verificar que Firebird esté corriendo" -ForegroundColor White
Write-Host "   2. Verificar que Firebird escuche en 0.0.0.0:3050 (no solo localhost)" -ForegroundColor White
Write-Host "   3. Crear regla de firewall para permitir 10.8.3.1:3050" -ForegroundColor White
Write-Host "   4. Verificar que WireGuard esté activo y conectado" -ForegroundColor White

