# Configuración de Gestión de Servicios del Servidor

Esta guía explica cómo configurar la gestión de servicios del sistema (systemd) y PM2 desde el dashboard.

## Requisitos

- Servidor VPS Linux (Ubuntu/Debian recomendado) con SSH habilitado
- Usuario con permisos sudo (o root)
- PM2 instalado (opcional, solo si usas PM2)

## Paso 1: Obtener información del servidor

En tu servidor VPS, ejecuta:

```bash
# IP pública del servidor
curl -4 ifconfig.me

# Verificar que SSH está activo
sudo systemctl status ssh

# Verificar usuario actual
whoami
```

## Paso 2: Crear usuario con permisos sudo (RECOMENDADO)

**No es necesario usar root.** Es más seguro usar un usuario específico con permisos sudo limitados:

```bash
# Crear usuario
sudo adduser servicemanager

# Agregar a grupo sudo
sudo usermod -aG sudo servicemanager

# Configurar sudo sin password SOLO para comandos específicos (más seguro)
sudo visudo
# Agregar estas líneas al final del archivo:
# servicemanager ALL=(ALL) NOPASSWD: /usr/bin/systemctl, /usr/bin/journalctl, /usr/bin/pm2
```

**O si prefieres usar root** (menos seguro pero más simple):
- Simplemente usa `root` como `SERVER_SSH_USER` en el `.env`
- No necesitas crear usuario adicional

## Paso 3: Configurar variables de entorno

En el archivo `.env` del proyecto Django, agrega:

```env
# Configuración SSH para gestión de servicios del servidor VPS
SERVER_SSH_HOST=tu_servidor_vps.com
# O la IP pública:
# SERVER_SSH_HOST=198.7.113.197

SERVER_SSH_USER=servicemanager
# RECOMENDADO: Usar un usuario con sudo (más seguro)
# O si prefieres usar root (menos seguro):
# SERVER_SSH_USER=root

SERVER_SSH_PASSWORD=tu_password_aqui
# O si prefieres usar clave SSH:
# SERVER_SSH_KEY_PATH=/ruta/a/tu/clave_privada

SERVER_SSH_PORT=22
# Puerto SSH (por defecto 22)
```

### Opción: Usar clave SSH (más seguro)

Si prefieres usar clave SSH en lugar de password:

```bash
# En tu máquina local, generar clave SSH (si no tienes)
ssh-keygen -t rsa -b 4096 -C "servicemanager@servidor"

# Copiar clave pública al servidor
ssh-copy-id servicemanager@tu_servidor_vps.com

# En .env, usar:
SERVER_SSH_KEY_PATH=C:/Users/USUARIO/.ssh/id_rsa
# O la ruta donde guardaste tu clave privada
```

## Paso 4: Verificar conexión

Puedes probar la conexión desde Python:

```python
# test_ssh_connection.py
import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('SERVER_SSH_HOST')
user = os.getenv('SERVER_SSH_USER')
password = os.getenv('SERVER_SSH_PASSWORD')
port = int(os.getenv('SERVER_SSH_PORT', 22))

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, port=port, username=user, password=password, timeout=10)
    print("✅ Conexión SSH exitosa")
    
    # Probar comando systemctl
    stdin, stdout, stderr = client.exec_command('sudo systemctl list-units --type=service --no-pager | head -5')
    print("✅ Comando systemctl ejecutado:")
    print(stdout.read().decode())
    
    # Probar PM2 (si está instalado)
    stdin, stdout, stderr = client.exec_command('pm2 jlist')
    pm2_output = stdout.read().decode()
    if pm2_output:
        print("✅ PM2 está instalado y funcionando")
    else:
        print("⚠️ PM2 no está instalado o no hay procesos")
    
    client.close()
except Exception as e:
    print(f"❌ Error: {e}")
```

## Paso 5: Verificar permisos

El usuario debe poder ejecutar:

```bash
# systemctl (con sudo)
sudo systemctl status ssh

# journalctl (con sudo)
sudo journalctl -u ssh -n 10

# PM2 (sin sudo, pero debe estar en el PATH)
pm2 list
```

## Notas importantes

1. **Seguridad**: 
   - No uses root si es posible
   - Usa claves SSH en lugar de passwords
   - Limita los comandos sudo solo a los necesarios

2. **Firewall**: 
   - Asegúrate de que el puerto SSH (22) esté abierto
   - Considera cambiar el puerto SSH por seguridad

3. **PM2**: 
   - PM2 debe estar instalado globalmente: `npm install -g pm2`
   - O en el PATH del usuario

4. **Diferencias con WireGuard**:
   - Esta configuración es **independiente** de WireGuard
   - Puedes usar el mismo servidor o uno diferente
   - Las variables son `SERVER_SSH_*` en lugar de `WG_SERVER_*`

## Solución de problemas

### Error: "SSH_HOST no está configurado"
- Verifica que `SERVER_SSH_HOST` esté en el `.env`
- Reinicia el servidor Django después de cambiar `.env`

### Error: "Connection refused"
- Verifica que SSH esté corriendo: `sudo systemctl status ssh`
- Verifica que el puerto sea correcto
- Verifica el firewall

### Error: "Permission denied"
- Verifica que el usuario tenga permisos sudo
- Verifica que la clave SSH tenga permisos correctos: `chmod 600 ~/.ssh/id_rsa`

### Error: "sudo: a password is required"
- **Opción 1 (Recomendada)**: Configura sudo sin password solo para comandos específicos (ver Paso 2)
- **Opción 2**: Usa root como usuario (menos seguro pero más simple)
- **Opción 3**: Usa una clave SSH configurada para sudo sin password

