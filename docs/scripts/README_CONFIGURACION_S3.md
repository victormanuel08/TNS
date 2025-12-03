# Configuración S3 para Backups

Este script permite insertar o actualizar la configuración S3 directamente en la base de datos de MANU.

## Uso del Script PowerShell

### Requisitos

1. Tener el entorno virtual de Python activado en `manu/env`
2. Tener Django y las dependencias instaladas
3. Tener acceso a la base de datos de MANU

### Ejecución

Desde el directorio `docs/scripts/` o desde cualquier lugar con la ruta completa:

```powershell
.\insertar_configuracion_s3.ps1 `
  -BucketName "mi-bucket-backups" `
  -AccessKeyId "AKIAIOSFODNN7EXAMPLE" `
  -SecretAccessKey "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" `
  -Region "us-east-1" `
  -Nombre "Backups Principal" `
  -Activo
```

### Parámetros

#### Requeridos

- **`-BucketName`**: Nombre del bucket S3 (ej: `mi-bucket-backups`)
- **`-AccessKeyId`**: Access Key ID de AWS (ej: `AKIAIOSFODNN7EXAMPLE`)
- **`-SecretAccessKey`**: Secret Access Key de AWS

#### Opcionales

- **`-Region`**: Región de AWS (default: `us-east-1`)
  - Ejemplos: `us-east-1`, `us-west-2`, `eu-west-1`, etc.
- **`-EndpointUrl`**: URL del endpoint S3 (solo para S3-compatible como MinIO)
  - Ejemplo: `https://s3.amazonaws.com` o `http://minio.local:9000`
- **`-Nombre`**: Nombre descriptivo de la configuración (default: `Backups Principal`)
- **`-Activo`**: Marca la configuración como activa (default: `true`)

### Ejemplos

#### Configuración básica AWS S3

```powershell
.\insertar_configuracion_s3.ps1 `
  -BucketName "tns-backups-prod" `
  -AccessKeyId "AKIA..." `
  -SecretAccessKey "tu-secret-key-aqui"
```

#### Configuración con región específica

```powershell
.\insertar_configuracion_s3.ps1 `
  -BucketName "tns-backups-prod" `
  -AccessKeyId "AKIA..." `
  -SecretAccessKey "tu-secret-key-aqui" `
  -Region "us-west-2"
```

#### Configuración para MinIO (S3-compatible)

```powershell
.\insertar_configuracion_s3.ps1 `
  -BucketName "backups" `
  -AccessKeyId "minioadmin" `
  -SecretAccessKey "minioadmin" `
  -Region "us-east-1" `
  -EndpointUrl "http://192.168.1.100:9000"
```

### Verificación

Después de ejecutar el script:

1. Ve al admin frontend → pestaña **"11. Backups S3"**
2. Verifica que la configuración aparece en el formulario
3. Los campos deberían estar prellenados con los valores que insertaste

### Actualización

Si ejecutas el script nuevamente con el mismo `-Nombre`, se **actualizará** la configuración existente en lugar de crear una nueva.

### Notas de Seguridad

⚠️ **IMPORTANTE**: El `SecretAccessKey` se almacena en texto plano en la base de datos. En producción, considera:

1. Usar encriptación a nivel de base de datos
2. Usar un servicio de gestión de secretos (AWS Secrets Manager, HashiCorp Vault, etc.)
3. Implementar rotación de credenciales periódicamente

### Solución de Problemas

#### Error: "No se encontró el directorio manu"
- Asegúrate de ejecutar el script desde `TNSFULL/docs/scripts/` o proporciona la ruta correcta

#### Error: "No se encontró el entorno virtual"
- Ejecuta primero: `python -m venv env` en el directorio `manu/`

#### Error: "ModuleNotFoundError: No module named 'django'"
- Activa el entorno virtual y ejecuta: `pip install -r requirements.txt`

#### Error de conexión a la base de datos
- Verifica que `settings.py` tenga la configuración correcta de `DATABASES`
- Verifica que la base de datos esté corriendo y accesible

