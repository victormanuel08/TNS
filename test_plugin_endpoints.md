# Endpoints del Plugin Chrome - Verificación

## Endpoints que usa el plugin:

1. **Calendario Tributario - Eventos**
   - URL: `https://api.eddeso.com/api/calendario-tributario/eventos/?year=2025&month=1`
   - Método: `GET`
   - Header: `Api-Key: sk_...`
   - Función: Obtener eventos del calendario tributario

2. **NITs Disponibles (Claves)**
   - URL: `https://api.eddeso.com/api/contrasenas-entidades/nits-disponibles/`
   - Método: `GET`
   - Header: `Api-Key: sk_...`
   - Función: Listar NITs disponibles para la API Key

3. **Claves de Entidad**
   - URL: `https://api.eddeso.com/api/contrasenas-entidades/?nit=XXX`
   - Método: `GET`
   - Header: `Api-Key: sk_...`
   - Función: Obtener claves/contraseñas de un NIT específico

## API Key de Prueba (Maestra):
```
sk_Ben0l9No0lzO_VuCBT0xlZnQSDukhSRBiYhOiitdEOO
```

## Headers que el backend espera:
- `HTTP_API_KEY` (Django convierte `Api-Key` header a esto)
- O `HTTP_AUTHORIZATION: Api-Key sk_...`
- O `HTTP_AUTHORIZATION: Bearer sk_...` (si empieza con sk_)

## Problema detectado:
Los endpoints están devolviendo 401 "Las credenciales de autenticación no se proveyeron."

Esto puede deberse a:
1. El header no se está enviando correctamente desde PowerShell
2. La API Key no está activa en la base de datos
3. El endpoint requiere autenticación adicional
4. Hay un middleware que está bloqueando la petición

## Próximos pasos:
1. Verificar que la API Key existe y está activa en la BD
2. Probar los endpoints desde el navegador o Postman
3. Verificar logs del servidor para ver qué headers está recibiendo
4. Confirmar que el plugin está usando el formato correcto de header

