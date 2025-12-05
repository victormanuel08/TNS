export default defineNuxtRouteMiddleware((to, from) => {
  const { getSubdomain, extractCompanyFromHost } = useSubdomain()
  
  // Obtener subdominio del host actual (no del localStorage)
  let subdomain: string | null = null
  
  if (process.server) {
    const event = useRequestEvent()
    const host =
      (event?.node?.req?.headers['x-forwarded-host'] as string) ||
      (event?.node?.req?.headers.host as string)
    subdomain = extractCompanyFromHost(host)
  } else if (process.client) {
    subdomain = extractCompanyFromHost(window.location.hostname)
  }
  
  // Solo redirigir si hay un subdominio REAL en el hostname (no del localStorage)
  // Y estamos en la ruta raíz
  if (subdomain && to.path === '/') {
    return navigateTo('/subdomain/login')
  }
  
  // Si no hay subdominio en el hostname y estamos en rutas de subdominio, redirigir a home
  if (!subdomain && to.path.startsWith('/subdomain')) {
    return navigateTo('/')
  }
})

