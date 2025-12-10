# Compilar Admin Firebird a .exe

## Requisitos

1. Python 3.8+
2. PyInstaller: `pip install pyinstaller`
3. requests: `pip install requests`

## Compilar

```bash
# Opción 1: Con ventana de consola (para ver errores)
pyinstaller --onefile admin_firebird.py

# Opción 2: Sin ventana (solo MessageBox)
pyinstaller --onefile --windowed admin_firebird.py

# Opción 3: Con icono personalizado
pyinstaller --onefile --windowed --icon=icono.ico admin_firebird.py
```

## Configuración

1. Copia `admin_config.json.example` a `admin_config.json`
2. Edita `admin_config.json` con tu API URL y API Key:

```json
{
  "api_base_url": "http://tu-servidor:8000/api",
  "api_key": "tu-api-key-aqui"
}
```

## Uso

1. Ejecuta `admin_firebird.exe`
2. Si no hay `admin_config.json`, te pedirá la API Key
3. Ingresa el ID de la empresa
4. Selecciona la opción del menú

## Endpoints Disponibles

- `GET /api/firebird-admin/resoluciones/?empresa_servidor_id=1`
- `PUT /api/firebird-admin/resoluciones/actualizar/`
- `GET /api/firebird-admin/configuraciones/?empresa_servidor_id=1`
- `PUT /api/firebird-admin/configuraciones/actualizar/`
- `GET /api/firebird-admin/info/?empresa_servidor_id=1`

## Seguridad

- Todos los endpoints requieren API Key
- Las conexiones a Firebird usan TNSBridge (pool seguro)
- Los tokens sensibles se ocultan en la visualización

