# Script PowerShell para recrear el archivo .env en UTF-8 (Windows)

Write-Host "🔄 Recreando archivo .env en UTF-8..." -ForegroundColor Yellow

# 1. Hacer backup del .env actual si existe
if (Test-Path .env) {
    $backupName = ".env.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Write-Host "📦 Haciendo backup del .env actual a: $backupName" -ForegroundColor Yellow
    Copy-Item .env $backupName
    Write-Host "✅ Backup creado: $backupName" -ForegroundColor Green
} else {
    Write-Host "⚠️  No existe archivo .env, se creará uno nuevo" -ForegroundColor Yellow
}

# 2. Borrar el .env actual
if (Test-Path .env) {
    Remove-Item .env -Force
    Write-Host "✅ Archivo .env borrado" -ForegroundColor Green
}

# 3. Crear nuevo .env vacío en UTF-8
Write-Host "📝 Creando nuevo archivo .env en UTF-8..." -ForegroundColor Yellow

# Crear contenido inicial
$content = @"
# Archivo de configuración de entorno
# Codificación: UTF-8

"@

# Guardar en UTF-8 sin BOM
[System.IO.File]::WriteAllText(
    (Resolve-Path .).Path + "\.env",
    $content,
    [System.Text.UTF8Encoding]::new($false)  # Sin BOM
)

# Verificar que se creó correctamente
if (Test-Path .env) {
    Write-Host "✅ Archivo .env creado exitosamente" -ForegroundColor Green
    
    # Verificar codificación
    $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path .).Path + "\.env")
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Write-Host "📋 Codificación: UTF-8 con BOM" -ForegroundColor Yellow
    } else {
        Write-Host "📋 Codificación: UTF-8 sin BOM" -ForegroundColor Green
    }
    
    Write-Host "⚠️  Recuerda agregar tus variables de entorno al archivo .env" -ForegroundColor Yellow
} else {
    Write-Host "❌ Error al crear el archivo .env" -ForegroundColor Red
    exit 1
}

Write-Host "✨ Proceso completado" -ForegroundColor Green

