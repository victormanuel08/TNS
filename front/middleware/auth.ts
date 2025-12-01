export default defineNuxtRouteMiddleware((to, from) => {
  const session = useSessionStore()
  
  if (!session.isAuthenticated.value) {
    return navigateTo('/admin/login')
  }
})

