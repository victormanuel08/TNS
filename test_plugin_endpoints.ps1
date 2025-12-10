# Script de prueba para endpoints del plugin Chrome
# Usa una API Key maestra (permite_scraping_total = True)

$apiKey = "sk_Ben0l9No0lzO_VuCBT0xlZnQSDukhSRBiYhOiitdEOO"
$baseUrl = "https://api.eddeso.com/api"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "PRUEBA DE ENDPOINTS DEL PLUGIN CHROME" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Probar endpoint de Calendario Tributario
Write-Host "1. PROBANDO: Calendario Tributario - Eventos" -ForegroundColor Yellow
Write-Host "   URL: $baseUrl/calendario-tributario/eventos/?year=2025&month=1" -ForegroundColor Gray
try {
    $headers = @{
        "Api-Key" = $apiKey
        "Content-Type" = "application/json"
    }
    $response = Invoke-WebRequest -Uri "$baseUrl/calendario-tributario/eventos/?year=2025&month=1" -Method GET -Headers $headers -ErrorAction Stop
    Write-Host "   OK Status: $($response.StatusCode)" -ForegroundColor Green
    $data = $response.Content | ConvertFrom-Json
    Write-Host "   Eventos encontrados: $($data.Count)" -ForegroundColor Green
    if ($data.Count -gt 0) {
        Write-Host "   Primer evento: $($data[0].titulo)" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ERROR: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $errorBody = $reader.ReadToEnd()
        Write-Host "   Respuesta: $errorBody" -ForegroundColor Red
    }
}
Write-Host ""

# 2. Probar endpoint de NITs Disponibles (Claves)
Write-Host "2. PROBANDO: NITs Disponibles para Claves" -ForegroundColor Yellow
Write-Host "   URL: $baseUrl/contrasenas-entidades/nits-disponibles/" -ForegroundColor Gray
$testNit = $null
try {
    $headers = @{
        "Api-Key" = $apiKey
        "Content-Type" = "application/json"
    }
    $response = Invoke-WebRequest -Uri "$baseUrl/contrasenas-entidades/nits-disponibles/" -Method GET -Headers $headers -ErrorAction Stop
    Write-Host "   OK Status: $($response.StatusCode)" -ForegroundColor Green
    $data = $response.Content | ConvertFrom-Json
    Write-Host "   Total NITs: $($data.total)" -ForegroundColor Green
    Write-Host "   Es API Key Maestra: $($data.es_api_key_maestra)" -ForegroundColor Green
    if ($data.nits.Count -gt 0) {
        Write-Host "   Primeros 3 NITs:" -ForegroundColor Gray
        $maxIndex = [Math]::Min(2, $data.nits.Count - 1)
        for ($i = 0; $i -le $maxIndex; $i++) {
            Write-Host "      - $($data.nits[$i].nit) - $($data.nits[$i].razon_social)" -ForegroundColor Gray
        }
        $testNit = $data.nits[0].nit_normalizado
        Write-Host "   NIT para prueba de claves: $testNit" -ForegroundColor Cyan
    } else {
        Write-Host "   No hay NITs disponibles" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ERROR: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $errorBody = $reader.ReadToEnd()
        Write-Host "   Respuesta: $errorBody" -ForegroundColor Red
    }
}
Write-Host ""

# 3. Probar endpoint de Claves de Entidad (si hay NIT disponible)
if ($testNit) {
    Write-Host "3. PROBANDO: Claves de Entidad para NIT seleccionado" -ForegroundColor Yellow
    Write-Host "   URL: $baseUrl/contrasenas-entidades/?nit=$testNit" -ForegroundColor Gray
    try {
        $headers = @{
            "Api-Key" = $apiKey
            "Content-Type" = "application/json"
        }
        $response = Invoke-WebRequest -Uri "$baseUrl/contrasenas-entidades/?nit=$testNit" -Method GET -Headers $headers -ErrorAction Stop
        Write-Host "   OK Status: $($response.StatusCode)" -ForegroundColor Green
        $data = $response.Content | ConvertFrom-Json
        
        # Manejar diferentes formatos de respuesta
        $claves = @()
        if ($data -is [array]) {
            $claves = $data
        } elseif ($data.results) {
            $claves = $data.results
        } elseif ($data.eventos) {
            $claves = $data.eventos
        } else {
            $claves = @($data)
        }
        
        Write-Host "   Total claves encontradas: $($claves.Count)" -ForegroundColor Green
        if ($claves.Count -gt 0) {
            Write-Host "   Primeras 3 claves:" -ForegroundColor Gray
            $maxIndex = [Math]::Min(2, $claves.Count - 1)
            for ($i = 0; $i -le $maxIndex; $i++) {
                $nombre = $claves[$i].nombre_servicio
                if (-not $nombre) { $nombre = $claves[$i].servicio }
                if (-not $nombre) { $nombre = $claves[$i].nombre }
                if (-not $nombre) { $nombre = "N/A" }
                Write-Host "      - $nombre" -ForegroundColor Gray
            }
        } else {
            Write-Host "   No hay claves para este NIT" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "   ERROR: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $errorBody = $reader.ReadToEnd()
            Write-Host "   Respuesta: $errorBody" -ForegroundColor Red
        }
    }
} else {
    Write-Host "3. Omitido: No hay NIT disponible para probar claves" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "PRUEBA COMPLETADA" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
