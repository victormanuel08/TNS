type CompanyMode = 'ecommerce' | 'pos' | 'pro' | 'autopago'

export type CompanyInfo = {
  id: number
  name: string
  subdomain: string
  custom_domain?: string
  mode: CompanyMode
  imageUrl?: string
  is_active: boolean
  primary_color?: string
  secondary_color?: string
  font_family?: string
  tagline?: string
}

const fallbackCompanies: Record<string, CompanyInfo> = {
  app: {
    id: 1,
    name: 'Contalink Pro',
    subdomain: 'app',
    mode: 'pro',
    is_active: true,
    tagline: 'Suite contable avanzada',
    primary_color: '#2563EB',
    secondary_color: '#1D4ED8',
    font_family: 'Inter, sans-serif'
  },
  restaurant: {
    id: 2,
    name: 'POS Restaurante Demo',
    subdomain: 'restaurant',
    mode: 'pos',
    is_active: true,
    tagline: 'Punto de venta agil para restaurantes',
    primary_color: '#F97316',
    secondary_color: '#EA580C',
    font_family: 'Poppins, sans-serif'
  },
  retail: {
    id: 3,
    name: 'Autoservicio Retail',
    subdomain: 'retail',
    mode: 'autopago',
    is_active: true,
    tagline: 'Terminal de autopago para tus clientes',
    primary_color: '#0EA5E9',
    secondary_color: '#0284C7',
    font_family: 'Outfit, sans-serif'
  }
}

export const useSubdomain = () => {
  const extractCompanyFromHost = (host?: string | null): string | null => {
    if (!host) return null

    const parts = host.split('.')
    const modeKeywords = ['ecommerce', 'autopago', 'pro', 'pos', 'app']

    if (modeKeywords.includes(parts[0]) && parts.length > 2) {
      return parts[1]
    }

    return parts[0] || null
  }

  const getSubdomain = (): string => {
    if (process.dev) {
      const route = useRoute()
      const querySubdomain = route.query.subdomain as string
      if (querySubdomain) return querySubdomain

      if (process.client) {
        return localStorage.getItem('dev-subdomain') || 'app'
      }

      return 'app'
    }

    if (process.server) {
      const event = useRequestEvent()
      const host =
        (event.node.req.headers['x-forwarded-host'] as string) ||
        (event.node.req.headers.host as string)
      return extractCompanyFromHost(host) || 'app'
    }

    const host =
      typeof window !== 'undefined' && window.location
        ? window.location.hostname
        : null
    return extractCompanyFromHost(host) || 'app'
  }

  const setDevSubdomain = (subdomain: string) => {
    if (process.dev && process.client) {
      localStorage.setItem('dev-subdomain', subdomain)
      window.location.reload()
    }
  }

  const getFallbackCompany = (subdomain: string): CompanyInfo => {
    return (
      fallbackCompanies[subdomain] || {
        id: Date.now(),
        name: `Demo ${subdomain}`,
        subdomain,
        mode: 'ecommerce',
        is_active: true,
        primary_color: '#3B82F6',
        secondary_color: '#1E40AF',
        font_family: 'Inter, sans-serif',
        tagline: 'Empresa demostrativa'
      }
    )
  }

  const getCompanyInfo = async (): Promise<CompanyInfo> => {
    const subdomain = getSubdomain()
    const config = useRuntimeConfig()

    if (!config.public.enableBackend) {
      return getFallbackCompany(subdomain)
    }

    try {
      const response = await $fetch<CompanyInfo>(
        `${config.public.djangoApiUrl}/api/companies/by-subdomain/${subdomain}/`
      )

      if (response && response.id) {
        return response
      }

      console.error('Invalid company response:', response)
      return getFallbackCompany(subdomain)
    } catch (error: any) {
      console.warn('Error fetching company info, using fallback:', error)

      if (error?.status === 404) {
        console.warn(`Company not found for subdomain: ${subdomain}`)
      }

      return getFallbackCompany(subdomain)
    }
  }

  return {
    getSubdomain,
    setDevSubdomain,
    getCompanyInfo,
    extractCompanyFromHost
  }
}
