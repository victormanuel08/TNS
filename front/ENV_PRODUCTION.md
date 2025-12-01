# Configuración de Variables de Entorno - Producción

## Archivo `.env` del Frontend

Crea un archivo `.env` en la raíz de `front/` con el siguiente contenido:

```bash
# URL del backend Django (API)
# En producción debe ser: https://api.eddeso.com
DJANGO_API_URL=https://api.eddeso.com

# Habilitar conexión al backend
# true = Usa el backend real
# false = Usa datos de demostración (solo para desarrollo)
ENABLE_BACKEND=true
```

## Explicación de Variables

### `DJANGO_API_URL`
- **Qué hace**: Define la URL base del backend Django (API REST)
- **Valor en desarrollo**: `http://localhost:8000`
- **Valor en producción**: `https://api.eddeso.com`
- **Uso**: Todas las peticiones HTTP del frontend a la API usan esta URL como base

### `ENABLE_BACKEND`
- **Qué hace**: Activa o desactiva la conexión al backend real
- **Valores posibles**: `true` o `false` (como string)
- **`true`**: El frontend hace peticiones reales al backend Django
- **`false`**: El frontend usa datos de demostración (mock data) sin conectarse al backend
- **Uso**: Útil para desarrollo sin backend, pero en producción siempre debe ser `true`

## Notas Importantes

1. **Después de crear/modificar `.env`**, debes reconstruir el frontend:
   ```bash
   npm run build
   ```

2. **En Nuxt**, las variables de entorno que empiezan con `NUXT_PUBLIC_` son accesibles en el cliente. En este caso, `DJANGO_API_URL` y `ENABLE_BACKEND` se exponen a través de `runtimeConfig.public` en `nuxt.config.ts`.

3. **Seguridad**: No incluyas credenciales sensibles en el `.env` del frontend, ya que estas variables se exponen al cliente (navegador).

