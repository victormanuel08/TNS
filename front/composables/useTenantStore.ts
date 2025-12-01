import type { CompanyInfo } from './useSubdomain'

type TenantTemplate = CompanyInfo['mode']

type TenantPreferences = {
  primaryColor: string
  secondaryColor: string
  fontFamily: string
  tagline?: string
}

const defaultPreferences: TenantPreferences = {
  primaryColor: '#2563EB',
  secondaryColor: '#1D4ED8',
  fontFamily: 'Inter, sans-serif',
  tagline: 'Portal empresarial'
}

export const useTenantStore = () => {
  const subdomainUtils = useSubdomain()
  const { getSubdomain } = subdomainUtils
  const company = useState<CompanyInfo | null>(
    'tenant-company',
    () => null
  )
  const template = useState<TenantTemplate>(
    'tenant-template',
    () => 'ecommerce'
  )
  const preferences = useState<TenantPreferences>(
    'tenant-preferences',
    () => ({ ...defaultPreferences })
  )
  const loading = useState('tenant-loading', () => false)
  const lastLoaded = useState<number | null>('tenant-last-loaded', () => null)
  const currentSubdomain = useState('tenant-current-subdomain', () => getSubdomain())

  const { getCompanyInfo } = subdomainUtils

  const ensureTenantLoaded = async (force = false) => {
    const subdomain = getSubdomain()
    currentSubdomain.value = subdomain

    if (!subdomain) {
      company.value = null
      return null
    }

    if (
      !force &&
      company.value &&
      company.value.subdomain === subdomain
    ) {
      return company.value
    }

    loading.value = true
    try {
      const info = await getCompanyInfo(subdomain)
      if (!info) {
        company.value = null
        return null
      }
      company.value = info
      template.value = info.mode
      preferences.value = {
        primaryColor: info.primary_color || defaultPreferences.primaryColor,
        secondaryColor:
          info.secondary_color || defaultPreferences.secondaryColor,
        fontFamily: info.font_family || defaultPreferences.fontFamily,
        tagline: info.tagline || defaultPreferences.tagline
      }
      lastLoaded.value = Date.now()
      return info
    } catch (error) {
      console.error('Error loading tenant data', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const setTemplate = (mode: TenantTemplate) => {
    template.value = mode
  }

  const currentMode = computed<TenantTemplate>(() => {
    return company.value?.mode || template.value
  })

  const companyName = computed(() => {
    return company.value?.name || 'Empresa'
  })

  const theme = computed(() => ({
    primary: preferences.value.primaryColor,
    secondary: preferences.value.secondaryColor,
    font: preferences.value.fontFamily
  }))

  return {
    company: readonly(company),
    loading: readonly(loading),
    lastLoaded: readonly(lastLoaded),
    currentMode,
    companyName,
    template,
    preferences,
    currentSubdomain: readonly(currentSubdomain),
    ensureTenantLoaded,
    setTemplate,
    theme
  }
}
