# Script para verificar configuración del puerto 3050
# Ejecutar como Administrador

Write-Host "=== Verificación Puerto 3050 (Firebird) ===" -ForegroundColor Cyan

# Verificar reglas de firewall
Write-Host "`n1. Reglas de Firewall para puerto 3050:" -ForegroundColor Yellow
$reglas = Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*3050*" -or $_.DisplayName -like "*Firebird*" }
if ($reglas) {
    $reglas | ForEach-Object {
        Write-Host "  - $($_.DisplayName): $($_.Enabled) - $($_.Direction) - $($_.Action)" -ForegroundColor Green
        $addressFilter = Get-NetFirewallAddressFilter -AssociatedNetFirewallRule $_
        if ($addressFilter.RemoteAddress) {
            Write-Host "    RemoteAddress: $($addressFilter.RemoteAddress)" -ForegroundColor Cyan
        }
    }
} else {
    Write-Host "  No se encontraron reglas específicas para 3050" -ForegroundColor Yellow
}

# Verificar conexiones activas
Write-Host "`n2. Conexiones en puerto 3050:" -ForegroundColor Yellow
$conexiones = Get-NetTCPConnection -LocalPort 3050 -ErrorAction SilentlyContinue
if ($conexiones) {
    $conexiones | ForEach-Object {
        Write-Host "  - Estado: $($_.State) | Local: $($_.LocalAddress):$($_.LocalPort) | Remote: $($_.RemoteAddress):$($_.RemotePort)" -ForegroundColor Green
    }
} else {
    Write-Host "  No hay conexiones activas en el puerto 3050" -ForegroundColor Yellow
}

# Verificar si Firebird está escuchando
Write-Host "`n3. Firebird escuchando:" -ForegroundColor Yellow
$listening = Get-NetTCPConnection -LocalPort 3050 -State Listen -ErrorAction SilentlyContinue
if ($listening) {
    Write-Host "  Firebird está escuchando en:" -ForegroundColor Green
    $listening | ForEach-Object {
        Write-Host "    - $($_.LocalAddress):$($_.LocalPort)" -ForegroundColor Cyan
    }
} else {
    Write-Host "  Firebird NO está escuchando en el puerto 3050" -ForegroundColor Red
    Write-Host "  Verifica que el servicio Firebird esté ejecutándose" -ForegroundColor Yellow
}

# Verificar servicios Firebird
Write-Host "`n4. Servicios Firebird:" -ForegroundColor Yellow
$servicios = Get-Service | Where-Object { $_.DisplayName -like "*Firebird*" }
if ($servicios) {
    $servicios | ForEach-Object {
        $status = if ($_.Status -eq "Running") { "Running" } else { "Stopped" }
        $color = if ($_.Status -eq "Running") { "Green" } else { "Red" }
        Write-Host "  - $($_.DisplayName): $status" -ForegroundColor $color
    }
} else {
    Write-Host "  No se encontraron servicios Firebird" -ForegroundColor Yellow
}

Write-Host "`n=== Fin de verificación ===" -ForegroundColor Cyan

