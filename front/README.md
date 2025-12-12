# Nuxt Minimal Starter

Look at the [Nuxt documentation](https://nuxt.com/docs/getting-started/introduction) to learn more.

## Setup

Make sure to install dependencies:

```bash
# npm
npm install

# pnpm
pnpm install

# yarn
yarn install

# bun
bun install
```

## Development Server

Start the development server on `http://localhost:3000`:

```bash
# npm
npm run dev

# pnpm
pnpm dev

# yarn
yarn dev

# bun
bun run dev
```

## Production

Build the application for production:

```bash
# npm
npm run build

# pnpm
pnpm build

# yarn
yarn build

# bun
bun run build
```

Locally preview production build:

```bash
# npm
npm run preview

# pnpm
pnpm preview

# yarn
yarn preview

# bun
bun run preview
```

Check out the [deployment documentation](https://nuxt.com/docs/getting-started/deployment) for more information.

## Backend-aware runtime

The dashboard consume los endpoints de Django mediante las siguientes variables de entorno:

```bash
DJANGO_API_URL=http://localhost:8000
ENABLE_BACKEND=true
```

- Con `ENABLE_BACKEND=true` se llaman a los endpoints reales (`/assistant/api/tns/*`, `/dian/api/sessions/`, `/assistant/api/ml/*`).
- Si la bandera está en `false`, se usan datos de demostración y no se realizan requests.

Para probar el flujo TNS:
1. Ingresa a `/auth` y autentícate (JWT + API key opcional).
2. Usa la sección “Empresas en ADMIN.gdb” para consultar `admin_empresas`.
3. Ejecuta “Validar usuario en TNS” y revisa el detalle del procedimiento.

## Simular subdominios en local

Durante el desarrollo puedes emular `subdominio.dominio.com` de tres formas:

1. **Query param**: en modo dev `http://localhost:3000/?subdomain=restaurant` fuerza el subdominio (se guarda en `localStorage`).
2. **Archivo hosts**: añade `127.0.0.1 app.localhost` (u otro) y abre `http://app.localhost:3000`.
3. **Proxy local**: si prefieres Traefik/Caddy, enruta `*.test.local` al puerto 3000 y el store detectará el subdominio automáticamente.

PS C:\Users\USUARIO\repos\TNSFULL> cd .\manu\                
PS C:\Users\USUARIO\repos\TNSFULL\manu> .\env\Scripts\activate
(env) PS C:\Users\USUARIO\repos\TNSFULL\manu> celery -A config worker -l info -P solo
PS C:\Redis> .\redis-server.exe --port 6380
PS C:\Users\USUARIO\repos\TNSFULL\front> npx nuxt dev --port 3001 --host

ssh victus@198.7.113.197