import type { CompanyInfo } from './useSubdomain'

export const useCompany = () => {
  const company = useState<CompanyInfo | null>('current-company', () => null)
  const manualLoading = useState('company-manual-loading', () => false)

  const { getCompanyInfo } = useSubdomain()

  const { data, pending, refresh } = useAsyncData(
    'company',
    () => getCompanyInfo(),
    {
      lazy: false,
      server: true,
      default: () => company.value
    }
  )

  watch(
    data,
    (value) => {
      if (value) {
        company.value = value
      }
    },
    { immediate: true }
  )

  const loadCompany = async () => {
    manualLoading.value = true
    try {
      await refresh()
      return company.value
    } catch (error) {
      console.error('Error loading company:', error)
      return null
    } finally {
      manualLoading.value = false
    }
  }

  const loading = computed(() => pending.value || manualLoading.value)

  const currentMode = computed(() => {
    return company.value?.mode || 'ecommerce'
  })

  const companyName = computed(() => {
    return company.value?.name || 'Empresa'
  })

  const companyImage = computed(() => {
    return company.value?.imageUrl || null
  })

  const isCompanyActive = computed(() => {
    return company.value?.is_active ?? true
  })

  return {
    company: readonly(company),
    loading,
    currentMode,
    companyName,
    companyImage,
    isCompanyActive,
    loadCompany
  }
}
