// composables/useCompany.ts
export const useCompany = () => {
  const company = useState<{
    id: number;
    name: string;
    subdomain: string;
    custom_domain?: string;
    mode: string;
    imageUrl?: string;
    is_active: boolean;
  } | null>('current-company', () => null)
  
  const loading = useState('company-loading', () => false)
  
  const { getCompanyInfo } = useSubdomain()
  
  const loadCompany = async () => {
    loading.value = true
    try {
      const companyInfo = await getCompanyInfo()
      company.value = companyInfo
      return companyInfo
    } catch (error) {
      console.error('Error loading company:', error)
      return null
    } finally {
      loading.value = false
    }
  }
  
  const currentMode = computed(() => {
    return company.value?.mode || 'profesional'
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
  
  // Cargar automáticamente al iniciar
  onMounted(async () => {
    if (!company.value) {
      await loadCompany()
    }
  })
  
  return {
    company: readonly(company),
    loading: readonly(loading),
    currentMode,
    companyName,
    companyImage,
    isCompanyActive,
    loadCompany
  }
}