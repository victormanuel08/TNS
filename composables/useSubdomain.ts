// composables/useSubdomain.ts
export const useSubdomain = () => {
  const getSubdomain = (): string | null => {
    // En desarrollo local, simulamos subdominios
    if (process.dev) {
      const route = useRoute()
      const querySubdomain = route.query.subdomain as string
      if (querySubdomain) return querySubdomain
      
      if (process.client) {
        return localStorage.getItem('dev-subdomain') || 'app'
      }
    }
    
    // En producción, detectar del host real
    if (process.server) {
      const event = useRequestEvent()
      const host = event.node.req.headers['x-forwarded-host'] as string || 
                   event.node.req.headers.host as string
      return extractCompanyFromHost(host)
    } else {
      const host = window.location.hostname
      return extractCompanyFromHost(host)
    }
  }
  
  const extractCompanyFromHost = (host: string): string | null => {
    if (!host) return null
    
    const parts = host.split('.')
    
    // Lista de modos reconocidos
    const modeKeywords = ['ecommerce', 'autopago', 'pro', 'pos', 'app']
    
    // Si el primer segmento es un modo, ignorarlo y tomar el siguiente
    if (modeKeywords.includes(parts[0]) && parts.length > 2) {
      return parts[1] // ej: "elpalustre" de "pos.elpalustre.eddeso.com"
    }
    
    // Si no hay modo específico, tomar el primer segmento
    return parts[0] // ej: "elpalustre" de "elpalustre.eddeso.com"
  }
  
  const setDevSubdomain = (subdomain: string) => {
    if (process.dev && process.client) {
      localStorage.setItem('dev-subdomain', subdomain)
      window.location.reload()
    }
  }
  
  // ✅ MEJORA: Tipado más específico y mejor manejo de errores
  const getCompanyInfo = async (): Promise<{
    id: number;
    name: string;
    subdomain: string;
    custom_domain?: string;
    mode: string;
    imageUrl?: string;
    is_active: boolean;
  } | null> => {
    const subdomain = getSubdomain()
    if (!subdomain) {
      console.warn('No subdomain found')
      return null
    }
    
    try {
      const config = useRuntimeConfig()
      const response = await $fetch(
        `${config.public.djangoApiUrl}/api/companies/by-subdomain/${subdomain}/`
      )
      
      // ✅ Validar que la respuesta tenga la estructura esperada
      if (response && response.id) {
        return response
      } else {
        console.error('Invalid company response:', response)
        return null
      }
    } catch (error: any) {
      console.error('Error fetching company info:', error)
      
      // ✅ Manejo específico de errores HTTP
      if (error?.status === 404) {
        console.warn(`Company not found for subdomain: ${subdomain}`)
      } else if (error?.status === 500) {
        console.error('Server error when fetching company info')
      }
      
      return null
    }
  }
  
  return { 
    getSubdomain, 
    setDevSubdomain,
    getCompanyInfo,
    extractCompanyFromHost 
  }
}