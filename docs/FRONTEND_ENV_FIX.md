# Solución: Frontend usando localhost en lugar de api.eddeso.com

## Problema

El frontend en producción está intentando conectarse a `http://localhost:8000` en lugar de `https://api.eddeso.com`, causando errores de conexión.

## Causa

En Nuxt 3, las variables de entorno se leen durante el **build time**. Si el archivo `.env` no existe o no tiene la variable `DJANGO_API_URL` cuando se construye el frontend, Nuxt usa el valor por defecto (`http://localhost:8000`).

## Solución

### Paso 1: Crear el archivo `.env` en el VPS

Ejecuta estos comandos en el servidor:

```bash
cd /home/victus/projects/CORE/front

# Crear el archivo .env
cat > .env <<EOF
DJANGO_API_URL=https://api.eddeso.com
ENABLE_BACKEND=true
EOF

# Verificar que se creó correctamente
cat .env
```

### Paso 2: Reconstruir el frontend

Como las variables de entorno se leen durante el build, **debes reconstruir el frontend**:

```bash
cd /home/victus/projects/CORE/front

# Asegúrate de estar en el Node.js correcto
nvm use 20.19.0

# Reconstruir el frontend
npm run build
```

### Paso 3: Reiniciar PM2

Después de reconstruir, reinicia el proceso PM2:

```bash
pm2 restart Eddeso
```

### Paso 4: Verificar

Abre `https://eddeso.com/admin/login` y verifica que:
1. La página carga correctamente
2. Al intentar hacer login, la petición va a `https://api.eddeso.com/api/auth/login/` (puedes verificar en la consola del navegador, pestaña Network)

## Script Automatizado

También puedes usar el script `docs/scripts/fix_frontend_env.sh`:

```bash
# Copiar el script al servidor (desde tu máquina local)
# Luego ejecutarlo en el servidor:
chmod +x /home/victus/projects/CORE/docs/scripts/fix_frontend_env.sh
/home/victus/projects/CORE/docs/scripts/fix_frontend_env.sh

# Después, reconstruir y reiniciar:
cd /home/victus/projects/CORE/front
nvm use 20.19.0
npm run build
pm2 restart Eddeso
```

## Notas Importantes

1. **El `.env` debe estar en la raíz de `front/`**, no en otra ubicación.
2. **Después de modificar `.env`, SIEMPRE debes reconstruir** el frontend (`npm run build`).
3. **Las variables de entorno en Nuxt 3 se leen en build time**, no en runtime (excepto las que tienen prefijo `NUXT_PUBLIC_`, pero en este caso usamos `process.env` directamente en `nuxt.config.ts`).

## Verificación Adicional

Si después de estos pasos sigue sin funcionar, verifica:

1. **Que el archivo `.env` existe y tiene el contenido correcto:**
   ```bash
   cat /home/victus/projects/CORE/front/.env
   ```

2. **Que el build se hizo correctamente:**
   ```bash
   ls -la /home/victus/projects/CORE/front/.output/
   ```

3. **Que PM2 está usando el build correcto:**
   ```bash
   pm2 info Eddeso
   ```

4. **Revisar los logs de PM2:**
   ```bash
   pm2 logs Eddeso --lines 50
   ```

