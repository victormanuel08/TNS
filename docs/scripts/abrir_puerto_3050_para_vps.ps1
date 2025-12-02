# Script para abrir puerto 3050 (Firebird) para acceso desde VPS 10.8.3.1
# Ejecutar como Administrador

Write-Host "Abriendo puerto 3050 para acceso desde 10.8.3.1..." -ForegroundColor Green

# Verificar si la regla ya existe
$reglaExistente = Get-NetFirewallRule -DisplayName "Firebird 3050 - VPS 10.8.3.1" -ErrorAction SilentlyContinue

if ($reglaExistente) {
    Write-Host "La regla ya existe. Eliminando para recrearla..." -ForegroundColor Yellow
    Remove-NetFirewallRule -DisplayName "Firebird 3050 - VPS 10.8.3.1"
}

# Crear regla de firewall para permitir acceso desde 10.8.3.1
New-NetFirewallRule -DisplayName "Firebird 3050 - VPS 10.8.3.1" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 3050 `
    -RemoteAddress 10.8.3.1 `
    -Action Allow `
    -Profile Any

Write-Host "`nRegla de firewall creada exitosamente!" -ForegroundColor Green
Write-Host "Puerto 3050 ahora acepta conexiones desde 10.8.3.1" -ForegroundColor Green

# Verificar que Firebird está escuchando
Write-Host "`nVerificando que Firebird está escuchando en el puerto 3050..." -ForegroundColor Cyan
$firebirdListening = Get-NetTCPConnection -LocalPort 3050 -State Listen -ErrorAction SilentlyContinue

if ($firebirdListening) {
    Write-Host "Firebird está escuchando en el puerto 3050" -ForegroundColor Green
    Write-Host "Dirección: $($firebirdListening.LocalAddress)" -ForegroundColor Cyan
} else {
    Write-Host "ADVERTENCIA: Firebird NO está escuchando en el puerto 3050" -ForegroundColor Yellow
    Write-Host "Verifica que el servicio Firebird esté ejecutándose" -ForegroundColor Yellow
}

Write-Host "`nListo! El VPS (10.8.3.1) ahora puede conectarse al puerto 3050" -ForegroundColor Green

