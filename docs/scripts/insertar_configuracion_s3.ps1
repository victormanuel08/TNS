# Script para insertar/actualizar configuración S3 en la base de datos MANU
# Ejecutar desde el directorio raíz de TNSFULL/manu

param(
    [string]$BucketName = "",
    [string]$Region = "us-east-1",
    [string]$AccessKeyId = "",
    [string]$SecretAccessKey = "",
    [string]$EndpointUrl = "",
    [string]$Nombre = "Backups Principal",
    [switch]$Activo = $true
)

Write-Host "=== Configuración S3 para Backups ===" -ForegroundColor Cyan
Write-Host ""

# Validar parámetros requeridos
if ([string]::IsNullOrWhiteSpace($BucketName)) {
    Write-Host "❌ Error: Se requiere -BucketName" -ForegroundColor Red
    Write-Host ""
    Write-Host "Uso:" -ForegroundColor Yellow
    Write-Host "  .\insertar_configuracion_s3.ps1 -BucketName 'mi-bucket' -AccessKeyId 'AKIA...' -SecretAccessKey 'tu-secret-key'"
    Write-Host ""
    Write-Host "Parámetros opcionales:" -ForegroundColor Yellow
    Write-Host "  -Region 'us-east-1' (default: us-east-1)"
    Write-Host "  -EndpointUrl 'https://s3.amazonaws.com' (opcional, para MinIO u otro S3-compatible)"
    Write-Host "  -Nombre 'Backups Principal' (default: Backups Principal)"
    Write-Host "  -Activo (default: true)"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($AccessKeyId)) {
    Write-Host "❌ Error: Se requiere -AccessKeyId" -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($SecretAccessKey)) {
    Write-Host "❌ Error: Se requiere -SecretAccessKey" -ForegroundColor Red
    exit 1
}

# Obtener ruta del script actual
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$manuDir = Join-Path $scriptDir "..\..\manu"

if (-not (Test-Path $manuDir)) {
    Write-Host "❌ Error: No se encontró el directorio manu en: $manuDir" -ForegroundColor Red
    exit 1
}

# Cambiar al directorio de manu
Push-Location $manuDir

try {
    # Verificar que existe el entorno virtual
    $venvPath = Join-Path $manuDir "env"
    if (-not (Test-Path $venvPath)) {
        Write-Host "❌ Error: No se encontró el entorno virtual en: $venvPath" -ForegroundColor Red
        Write-Host "   Ejecuta primero: python -m venv env" -ForegroundColor Yellow
        exit 1
    }

    # Activar entorno virtual y ejecutar script Python
    $pythonPath = Join-Path $venvPath "Scripts\python.exe"
    if (-not (Test-Path $pythonPath)) {
        Write-Host "❌ Error: No se encontró Python en: $pythonPath" -ForegroundColor Red
        exit 1
    }

    Write-Host "📦 Insertando configuración S3..." -ForegroundColor Green
    Write-Host "   Bucket: $BucketName" -ForegroundColor Cyan
    Write-Host "   Región: $Region" -ForegroundColor Cyan
    Write-Host "   Access Key: $($AccessKeyId.Substring(0, [Math]::Min(10, $AccessKeyId.Length)))..." -ForegroundColor Cyan
    Write-Host ""

    # Crear script Python temporal
    $pythonScript = @"
import os
import sys
import django

# Configurar Django
sys.path.insert(0, r'$manuDir')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.sistema_analitico.models import ConfiguracionS3

# Parámetros
bucket_name = r'$BucketName'
region = r'$Region'
access_key_id = r'$AccessKeyId'
secret_access_key = r'$SecretAccessKey'
endpoint_url = r'$EndpointUrl' if r'$EndpointUrl' else None
nombre = r'$Nombre'
activo = $($Activo.IsPresent)

# Crear o actualizar configuración
config, created = ConfiguracionS3.objects.update_or_create(
    nombre=nombre,
    defaults={
        'bucket_name': bucket_name,
        'region': region,
        'access_key_id': access_key_id,
        'secret_access_key': secret_access_key,
        'endpoint_url': endpoint_url,
        'activo': activo
    }
)

if created:
    print(f"✅ Configuración S3 creada exitosamente (ID: {config.id})")
else:
    print(f"✅ Configuración S3 actualizada exitosamente (ID: {config.id})")

print(f"   Nombre: {config.nombre}")
print(f"   Bucket: {config.bucket_name}")
print(f"   Región: {config.region}")
print(f"   Activo: {config.activo}")
"@

    # Guardar script temporal
    $tempScript = Join-Path $env:TEMP "insert_s3_config_$(Get-Date -Format 'yyyyMMddHHmmss').py"
    $pythonScript | Out-File -FilePath $tempScript -Encoding UTF8

    try {
        # Ejecutar script Python
        & $pythonPath $tempScript

        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✅ Configuración S3 insertada/actualizada correctamente en la base de datos" -ForegroundColor Green
            Write-Host ""
            Write-Host "💡 Ahora puedes:" -ForegroundColor Cyan
            Write-Host "   1. Ir al admin frontend → pestaña '11. Backups S3'" -ForegroundColor White
            Write-Host "   2. Verificar que la configuración aparece correctamente" -ForegroundColor White
            Write-Host "   3. Crear backups desde el frontend" -ForegroundColor White
        } else {
            Write-Host ""
            Write-Host "❌ Error al insertar configuración S3" -ForegroundColor Red
            exit 1
        }
    } finally {
        # Limpiar script temporal
        if (Test-Path $tempScript) {
            Remove-Item $tempScript -Force
        }
    }

} catch {
    Write-Host ""
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

