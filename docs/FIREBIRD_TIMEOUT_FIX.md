# Solución: Timeout al conectar a servidor Firebird

## Problema

Al intentar descubrir empresas en un servidor Firebird, se obtiene el error:
```
Error conectando al servidor 'BCE': timed out
```

## Causas Posibles

1. **El servidor Firebird no está accesible desde el VPS**
   - El servidor Firebird puede estar en una red privada/VPN
   - El VPS puede no tener acceso a esa red

2. **Configuración incorrecta del servidor**
   - Host/IP incorrecto
   - Puerto incorrecto o bloqueado por firewall
   - Ruta maestra no configurada o incorrecta

3. **Firewall bloqueando la conexión**
   - El puerto 3050 (o el configurado) está bloqueado
   - Reglas de firewall en el servidor Firebird o en el VPS

4. **El servidor Firebird no está corriendo**
   - El servicio de Firebird puede estar detenido

## Diagnóstico

### Paso 1: Verificar la configuración del servidor

En el admin panel, verifica que el servidor 'BCE' tenga:
- **Host/IP**: Debe ser una IP accesible desde el VPS
- **Puerto**: Generalmente 3050 para Firebird
- **Ruta Maestra**: Debe apuntar a la base de datos maestra (ej: `C:\datos\ADMIN.gdb` o `/ruta/al/ADMIN.gdb`)
- **Usuario y Contraseña**: Credenciales válidas de Firebird

### Paso 2: Verificar conectividad desde el VPS

Ejecuta estos comandos en el VPS para verificar la conectividad:

```bash
# Reemplaza HOST_IP con la IP del servidor Firebird
# Reemplaza PUERTO con el puerto configurado (generalmente 3050)

# 1. Verificar si el host es accesible (ping)
ping -c 4 HOST_IP

# 2. Verificar si el puerto está abierto
telnet HOST_IP PUERTO
# O usando nc (netcat):
nc -zv HOST_IP PUERTO

# 3. Si el servidor está en una VPN, verificar que la VPN esté activa
# (depende de cómo esté configurada la VPN)
```

### Paso 3: Verificar logs del backend

Revisa los logs del backend para ver más detalles del error:

```bash
# Ver logs del servicio backcore
sudo journalctl -u backcore.service -n 100 --no-pager

# O si estás usando Gunicorn directamente, verifica los logs de Gunicorn
```

## Soluciones

### Solución 1: Servidor en red privada/VPN

Si el servidor Firebird está en una red privada o VPN:

1. **Verificar que la VPN esté activa en el VPS**
   ```bash
   # Verificar conexiones VPN activas
   ip addr show
   # O
   ifconfig
   ```

2. **Configurar la ruta correcta en el servidor**
   - Si el servidor Firebird está en la misma red, usa la IP privada
   - Si está en otra red, asegúrate de que haya conectividad (VPN, túnel, etc.)

### Solución 2: Verificar configuración del servidor

1. **Accede al admin panel** (`https://eddeso.com/admin/dashboard`)
2. **Ve a la sección de Servidores**
3. **Edita el servidor 'BCE'** y verifica:
   - **Host**: Debe ser una IP accesible (no `localhost` si el Firebird está en otra máquina)
   - **Puerto**: Generalmente `3050` para Firebird
   - **Ruta Maestra**: Debe ser la ruta completa a la base de datos maestra
     - Windows: `C:\datos\ADMIN.gdb` o `\\servidor\datos\ADMIN.gdb`
     - Linux: `/ruta/al/ADMIN.gdb`
   - **Usuario**: Generalmente `SYSDBA` o el usuario configurado
   - **Contraseña**: La contraseña del usuario

### Solución 3: Verificar firewall

Si el puerto está bloqueado:

```bash
# En el servidor donde está Firebird, verificar que el puerto esté abierto
# (Esto debe hacerse en el servidor Firebird, no en el VPS)

# En Windows (servidor Firebird):
# - Abrir "Firewall de Windows Defender"
# - Permitir el puerto 3050 (o el configurado) para conexiones entrantes

# En Linux (servidor Firebird):
sudo ufw allow 3050/tcp
# O
sudo firewall-cmd --add-port=3050/tcp --permanent
sudo firewall-cmd --reload
```

### Solución 4: Verificar que Firebird esté corriendo

En el servidor donde está Firebird:

```bash
# En Windows:
# - Abrir "Servicios" (services.msc)
# - Verificar que "Firebird Server" esté "En ejecución"

# En Linux:
sudo systemctl status firebird
# O
sudo service firebird status
```

### Solución 5: Aumentar timeout (temporal)

Si el servidor está accesible pero es lento, puedes aumentar el timeout temporalmente:

**⚠️ ADVERTENCIA**: Esto solo oculta el problema. Si el servidor no es accesible, aumentar el timeout no ayudará.

Para aumentar el timeout, edita `manu/apps/sistema_analitico/services/database_connectors.py`:

```python
'timeout': 60  # Aumentar de 30 a 60 segundos
```

Luego reconstruye y reinicia el backend.

## Verificación Final

Después de aplicar las soluciones:

1. **Intenta descubrir empresas nuevamente** desde el admin panel
2. **Revisa los logs** si sigue fallando:
   ```bash
   sudo journalctl -u backcore.service -f
   ```
3. **Verifica la conectividad** desde el VPS:
   ```bash
   # Desde el VPS, intenta conectarte al servidor Firebird
   # (Esto requiere tener firebirdsql instalado en el VPS, solo para pruebas)
   ```

## Notas Importantes

- **El timeout actual es de 30 segundos**. Si el servidor no responde en ese tiempo, la conexión falla.
- **La ruta maestra debe ser accesible desde el VPS**. Si la base de datos está en una ruta de red (ej: `\\servidor\datos\ADMIN.gdb`), el VPS debe tener acceso a esa ruta.
- **Si el servidor Firebird está en una red privada**, el VPS debe tener acceso a esa red (VPN, túnel, etc.).

## Comandos Útiles para Diagnóstico

```bash
# Verificar conectividad de red
ping HOST_IP

# Verificar puerto abierto
nc -zv HOST_IP PUERTO

# Ver logs del backend en tiempo real
sudo journalctl -u backcore.service -f

# Verificar configuración del servidor en la base de datos
# (Desde el shell de Django)
python manage.py shell
>>> from apps.sistema_analitico.models import Servidor
>>> servidor = Servidor.objects.get(nombre='BCE')
>>> print(f"Host: {servidor.host}, Puerto: {servidor.puerto}, Ruta: {servidor.ruta_maestra}")
```

