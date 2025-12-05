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

const storageKey = 'dev-subdomain'

export const useSubdomain = () => {
  const normalize = (value?: string | null) => {
    if (!value) return null
    const cleaned = value.trim().toLowerCase()
    return cleaned.length ? cleaned : null
  }

  /**
   * Lista de TLDs comunes de 2 partes (país + genérico)
   * Estos deben tratarse como un solo TLD, no como subdominio
   */
  const TWO_PART_TLDS = [
    'com.co', 'com.mx', 'com.ar', 'com.br', 'com.pe', 'com.cl', 'com.uy',
    'co.uk', 'com.au', 'com.sg', 'com.hk', 'com.tw', 'com.my', 'com.ph',
    'com.ve', 'com.ec', 'com.bo', 'com.py', 'com.cr', 'com.pa', 'com.gt',
    'com.sv', 'com.hn', 'com.ni', 'com.do', 'com.cu', 'com.pr', 'com.jm',
    'com.za', 'com.ng', 'com.eg', 'com.ae', 'com.sa', 'com.il', 'com.tr',
    'com.in', 'com.pk', 'com.bd', 'com.lk', 'com.np', 'com.kh', 'com.vn',
    'com.th', 'com.id', 'com.kr', 'com.jp', 'com.cn', 'com.ru', 'com.ua',
    'com.pl', 'com.cz', 'com.sk', 'com.hu', 'com.ro', 'com.bg', 'com.gr',
    'com.pt', 'com.es', 'com.it', 'com.fr', 'com.de', 'com.nl', 'com.be',
    'com.ch', 'com.at', 'com.se', 'com.no', 'com.dk', 'com.fi', 'com.ie',
    'com.nz', 'com.ca', 'com.us', 'org.co', 'net.co', 'edu.co', 'gov.co',
    'mil.co', 'info.co', 'biz.co', 'name.co'
  ]

  /**
   * Detecta si un dominio tiene un TLD de 2 partes
   */
  const hasTwoPartTLD = (host: string): boolean => {
    const lowerHost = host.toLowerCase()
    return TWO_PART_TLDS.some(tld => lowerHost.endsWith('.' + tld) || lowerHost === tld)
  }

  /**
   * Extrae el dominio completo y el subdominio (si existe) del host
   * Retorna: { domain: string, subdomain: string | null }
   */
  const parseDomain = (host: string): { domain: string; subdomain: string | null } => {
    const segments = host.split('.').filter(Boolean)
    if (segments.length < 2) {
      return { domain: host, subdomain: null }
    }

    // Para localhost, permitir subdominios (ej: pepito.localhost)
    if (segments[segments.length - 1] === 'localhost') {
      if (segments.length > 2) {
        // Hay subdominio: pepito.localhost → subdomain: pepito, domain: localhost
        return {
          subdomain: segments.slice(0, segments.length - 1).join('.') || null,
          domain: 'localhost'
        }
      }
      return { domain: 'localhost', subdomain: null }
    }

    // Verificar si tiene TLD de 2 partes
    if (hasTwoPartTLD(host)) {
      // empresanueva.com.co → domain: empresanueva.com.co, subdomain: null
      // shop.empresanueva.com.co → domain: empresanueva.com.co, subdomain: shop
      if (segments.length > 3) {
        // Hay subdominio: shop.empresanueva.com.co
        const tld = segments.slice(-2).join('.') // com.co
        const domain = segments.slice(-3, -1).join('.') + '.' + tld // empresanueva.com.co
        const subdomain = segments.slice(0, -3).join('.') // shop
        return { domain, subdomain }
      } else if (segments.length === 3) {
        // No hay subdominio: empresanueva.com.co
        return { domain: host, subdomain: null }
      }
    }

    // TLD de 1 parte (com, org, net, etc.)
    // empresanueva.com → domain: empresanueva.com, subdomain: null
    // shop.empresanueva.com → domain: empresanueva.com, subdomain: shop
    if (segments.length > 2) {
      // Hay subdominio: shop.empresanueva.com
      const tld = segments[segments.length - 1] // com
      const domain = segments.slice(-2).join('.') // empresanueva.com
      const subdomain = segments.slice(0, -2).join('.') // shop
      return { domain, subdomain }
    }

    // Dominio base sin subdominio
    return { domain: host, subdomain: null }
  }

  const extractCompanyFromHost = (host?: string | null): string | null => {
    host = normalize(host)
    if (!host) return null

    const parsed = parseDomain(host)
    
    // Si hay subdominio, retornarlo (para compatibilidad con código existente)
    if (parsed.subdomain) {
      return parsed.subdomain
    }

    // Si no hay subdominio, retornar null (el código que llama debe usar el dominio completo)
    return null
  }

  const getStoredSubdomain = () => {
    if (process.client) {
      const stored = localStorage.getItem(storageKey)
      return normalize(stored)
    }
    return null
  }

  const setStoredSubdomain = (subdomain: string) => {
    if (process.client) {
      localStorage.setItem(storageKey, subdomain)
    }
  }

  const getSubdomain = (): string | null => {
    let resolved: string | null = null

    if (process.server) {
      const event = useRequestEvent()
      const host =
        (event?.node?.req?.headers['x-forwarded-host'] as string) ||
        (event?.node?.req?.headers.host as string)
      resolved = extractCompanyFromHost(host)
      return resolved
    }

    if (process.client) {
      resolved = extractCompanyFromHost(window.location.hostname)
      if (resolved) {
        return resolved
      }

      const route = useRoute()
      const querySubdomain = normalize(route.query.subdomain as string)
      if (querySubdomain) {
        setStoredSubdomain(querySubdomain)
        return querySubdomain
      }

      return getStoredSubdomain()
    }

    return null
  }

  const setDevSubdomain = (subdomain: string) => {
    const normalized = normalize(subdomain)
    if (normalized && process.client) {
      setStoredSubdomain(normalized)
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

  /**
   * Obtiene el dominio completo del host actual
   */
  const getFullDomain = (): string | null => {
    if (process.server) {
      const event = useRequestEvent()
      const host =
        (event?.node?.req?.headers['x-forwarded-host'] as string) ||
        (event?.node?.req?.headers.host as string)
      if (host) {
        const parsed = parseDomain(normalize(host) || '')
        return parsed.domain
      }
      return null
    }

    if (process.client) {
      const parsed = parseDomain(normalize(window.location.hostname) || '')
      return parsed.domain
    }

    return null
  }

  const getCompanyInfo = async (
    providedSubdomain?: string | null
  ): Promise<CompanyInfo | null> => {
    const config = useRuntimeConfig()

    // Obtener subdominio y dominio completo
    const subdomain = normalize(providedSubdomain) ?? getSubdomain()
    const fullDomain = getFullDomain()

    // Si no hay subdominio ni dominio completo, retornar null
    if (!subdomain && !fullDomain) {
      return null
    }

    if (!config.public.enableBackend) {
      return subdomain ? getFallbackCompany(subdomain) : null
    }

    try {
      // Estrategia 1: Si hay subdominio, buscar por subdominio primero
      if (subdomain) {
        try {
          const response = await $fetch<CompanyInfo>(
            `${config.public.djangoApiUrl}/api/companies/by-subdomain/${subdomain}/`
          )

          if (response && response.id) {
            return response
          }
        } catch (subdomainError: any) {
          // Si falla por subdominio, continuar con dominio completo
          console.warn(`Subdomain search failed for '${subdomain}', trying full domain...`)
        }
      }

      // Estrategia 2: Buscar por dominio completo
      if (fullDomain) {
        try {
          const response = await $fetch<CompanyInfo>(
            `${config.public.djangoApiUrl}/api/companies/by-domain/${fullDomain}/`
          )

          if (response && response.id) {
            return response
          }
        } catch (domainError: any) {
          console.warn(`Domain search failed for '${fullDomain}'`)
        }
      }

      // Si ambas búsquedas fallan, usar fallback solo si hay subdominio
      if (subdomain) {
        console.warn('Both subdomain and domain searches failed, using fallback')
        return getFallbackCompany(subdomain)
      }

      return null
    } catch (error: any) {
      console.warn('Error fetching company info:', error)

      if (error?.status === 404) {
        console.warn(`Company not found for subdomain: ${subdomain || 'N/A'} or domain: ${fullDomain || 'N/A'}`)
      }

      // Solo usar fallback si hay subdominio
      return subdomain ? getFallbackCompany(subdomain) : null
    }
  }

  return {
    getSubdomain,
    setDevSubdomain,
    getCompanyInfo,
    extractCompanyFromHost,
    getFullDomain,
    parseDomain
  }
}
