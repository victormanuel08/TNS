export default defineNuxtRouteMiddleware((to, from) => {
  const { getSubdomain } = useSubdomain()
  const subdomain = getSubdomain()
  
  // Si hay subdominio, redirigir a la página de login del subdominio
  if (subdomain && to.path === '/') {
    return navigateTo('/subdomain/login')
  }
  
  // Si no hay subdominio y estamos en rutas de subdominio, redirigir a home
  if (!subdomain && to.path.startsWith('/subdomain')) {
    return navigateTo('/')
  }
})

