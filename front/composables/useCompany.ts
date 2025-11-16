import type { Ref } from 'vue'
import type { CompanyInfo } from './useSubdomain'

type CompanyRef = Ref<CompanyInfo | null>

export const useCompany = () => {
  const tenant = useTenantStore()

  const { pending, refresh } = useAsyncData(
    'tenant-company',
    () => tenant.ensureTenantLoaded(),
    {
      lazy: false,
      server: true,
      default: () => tenant.company.value
    }
  )

  const loading = computed(() => pending.value || tenant.loading.value)

  const company = computed<CompanyRef['value']>(() => tenant.company.value)

  const companyImage = computed(() => tenant.company.value?.imageUrl || null)

  const isCompanyActive = computed(() => tenant.company.value?.is_active ?? true)

  return {
    company,
    loading,
    currentMode: tenant.currentMode,
    companyName: tenant.companyName,
    companyImage,
    isCompanyActive,
    loadCompany: refresh
  }
}
