# ✅ VPN Gestor - Listo para Usar

## Estado Actual

✅ **Conexión SSH**: Funcionando correctamente  
✅ **Frontend**: Pestaña VPN implementada en el dashboard  
✅ **Backend**: Endpoints configurados y funcionando  
✅ **Configuración**: Variables de entorno configuradas  

## Configuración Actual

```env
WG_SERVER_HOST=198.7.113.197
WG_SERVER_USER=wgmanager
WG_SERVER_PASSWORD=Wg32708
WG_INTERFACE=wg-main
WG_SERVER_IP=10.8.3.1
WG_SERVER_PORT=46587
WG_SERVER_ENDPOINT=198.7.113.197:46587
```

## Pasos para Activar

### 1. Crear Migración (si no existe)

```bash
cd manu
python manage.py makemigrations sistema_analitico
```

### 2. Aplicar Migración

```bash
python manage.py migrate
```

### 3. Iniciar Servidor Django

```bash
python manage.py runserver
```

### 4. Acceder al Dashboard

1. Ve a: `http://localhost:3001/admin/dashboard`
2. Haz clic en la pestaña **"VPN"**
3. Verás la interfaz de gestión de VPN

## Funcionalidades Disponibles

### ✅ Listar Configuraciones VPN
- Muestra todas las configuraciones creadas
- Estado (Activo/Inactivo)
- IP asignada
- Fecha de creación

### ✅ Crear Nuevo Túnel
- Clic en "Crear Túnel"
- Ingresa nombre del cliente/PC
- IP opcional (se asigna automáticamente si no se especifica)
- Opción de activar inmediatamente

### ✅ Descargar Archivo .conf
- Clic en "Descargar" junto a cada configuración
- Descarga el archivo `.conf` listo para instalar en el cliente

### ✅ Activar/Desactivar Túneles
- Toggle para activar o desactivar túneles
- Se actualiza automáticamente en el servidor WireGuard

### ✅ Eliminar Configuraciones
- Botón de eliminar (con confirmación)
- Remueve el peer del servidor automáticamente

## Prueba Rápida

1. **Crear túnel de prueba**:
   - Nombre: `TEST_WINDOWS_PC`
   - IP: (dejar vacío para asignación automática)
   - Activar: No (por ahora)

2. **Verificar en servidor**:
   ```bash
   sudo wg show wg-main
   # Deberías ver el nuevo peer
   ```

3. **Descargar configuración**:
   - Clic en "Descargar"
   - Instalar en un cliente para probar

## Notas Importantes

- ⚠️ La red VPN es `10.8.3.0/24` (no `10.8.0.0/24`)
- ⚠️ La interfaz activa es `wg-main` (no `wg0`)
- ⚠️ El puerto es `46587` (no `51820`)
- ✅ El sistema detecta automáticamente IPs ya asignadas
- ✅ Evita conflictos con peers existentes

## Solución de Problemas

### Error: "No module named 'VpnConfig'"
```bash
python manage.py makemigrations sistema_analitico
python manage.py migrate
```

### Error: "WG_SERVER_HOST no está configurado"
- Verifica que el `.env` tenga todas las variables
- Reinicia el servidor Django después de cambiar `.env`

### Error: "Permission denied"
- Verifica que `wgmanager` tenga permisos sudo:
  ```bash
  sudo visudo
  # Agregar: wgmanager ALL=(ALL) NOPASSWD: /usr/bin/wg, /usr/bin/wg-quick
  ```

### IPs ya asignadas
- El sistema consulta automáticamente las IPs de:
  - Base de datos (VpnConfig)
  - Peers activos en el servidor (wg show)
- Asigna la siguiente IP disponible automáticamente

