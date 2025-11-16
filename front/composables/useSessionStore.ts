import { watch, computed } from 'vue'

type UserEmpresaResponse = {
  empresa_servidor_id: number
  nombre: string
  nit: string
  anio_fiscal: number
  codigo?: string
  preferred_template?: string
  servidor?: string
}

type LoginResponse = {
  access: string
  refresh: string
  user: {
    id: number
    username: string
    email?: string
    is_superuser?: boolean
    puede_gestionar_api_keys?: boolean
    empresas?: UserEmpresaResponse[]
    default_template?: string
    default_empresa_id?: number | null
  }
}

type AdminEmpresaRecord = {
  CODIGO: string
  NOMBRE: string
  NIT: string
  ANOFIS: number
  REPRES?: string | null
  ARCHIVO?: string | null
}

type AdminEmpresasResponse = {
  count: number
  nit_buscado: string
  empresas: AdminEmpresaRecord[]
}

type NormalizedEmpresa = {
  empresaServidorId: number | null
  nombre: string
  nit: string
  anioFiscal: number | null
  codigo?: string | null
  archivo?: string | null
  preferredTemplate?: string | null
  source: 'login' | 'admin'
  raw?: any
}

type TNSUserValidationPayload = {
  VALIDATE: Record<string, string>
  MODULOS: Record<string, any>
}

type AdminEmpresaQuery = {
  empresaServidorId?: number
  nit?: string
  anioFiscal?: number
  searchNit: string
}

export const useSessionStore = () => {
  const user = useState<LoginResponse['user'] | null>(
    'session-user',
    () => null
  )
  const empresas = useState<NormalizedEmpresa[]>(
    'session-empresas',
    () => []
  )
  const adminEmpresas = useState<NormalizedEmpresa[]>(
    'session-admin-empresas',
    () => []
  )
  const selectedEmpresa = useState<NormalizedEmpresa | null>(
    'session-selected-empresa',
    () => null
  )
  const validation = useState<TNSUserValidationPayload | null>(
    'session-tns-validation',
    () => null
  )
  const loading = useState('session-loading', () => false)
  const lastError = useState<string | null>('session-last-error', () => null)

  const { accessToken, refreshToken, apiKey } = useAuthState()
  const tenant = useTenantStore()
  const api = useApiClient()

  const accessCookie = useCookie<string | null>('tns-access-token', {
    sameSite: 'lax',
    secure: false
  })
  const refreshCookie = useCookie<string | null>('tns-refresh-token', {
    sameSite: 'lax',
    secure: false
  })

  if (accessCookie.value && !accessToken.value) {
    accessToken.value = accessCookie.value
  }
  if (refreshCookie.value && !refreshToken.value) {
    refreshToken.value = refreshCookie.value
  }

  watch(accessToken, (value) => {
    accessCookie.value = value || null
  })

  watch(refreshToken, (value) => {
    refreshCookie.value = value || null
  })

  const setTokens = (access: string | null, refresh?: string | null) => {
    accessToken.value = access
    if (refresh !== undefined) {
      refreshToken.value = refresh
    }
  }

  const normalizeUserEmpresa = (
    empresa: UserEmpresaResponse
  ): NormalizedEmpresa => ({
    empresaServidorId: empresa.empresa_servidor_id,
    nombre: empresa.nombre,
    nit: empresa.nit,
    anioFiscal: empresa.anio_fiscal,
    codigo: empresa.codigo || null,
    preferredTemplate: empresa.preferred_template || null,
    source: 'login',
    raw: empresa
  })

  const normalizeAdminEmpresa = (
    empresa: AdminEmpresaRecord
  ): NormalizedEmpresa => ({
    empresaServidorId: null,
    nombre: empresa.NOMBRE,
    nit: empresa.NIT,
    anioFiscal: empresa.ANOFIS || null,
    codigo: empresa.CODIGO || null,
    archivo: empresa.ARCHIVO || null,
    preferredTemplate: selectedEmpresa.value?.preferredTemplate || null,
    source: 'admin',
    raw: empresa
  })

  const applyPreferredTemplate = (template?: string | null) => {
    if (template) {
      tenant.setTemplate(template as any)
    }
  }

  const login = async (credentials: {
    username: string
    password: string
  }) => {
    loading.value = true
    lastError.value = null
    try {
      const response = await api.post<LoginResponse>(
        '/api/auth/login/',
        credentials
      )
      setTokens(response.access, response.refresh)
      user.value = response.user

      const userEmpresas = response.user?.empresas || []
      empresas.value = userEmpresas.map(normalizeUserEmpresa)
      adminEmpresas.value = []
      selectedEmpresa.value = null
      empresaModalOpen.value = empresas.value.length > 0
      applyPreferredTemplate(
        response.user?.preferred_template || response.user?.default_template
      )

      return response
    } catch (error: any) {
      lastError.value = error?.data?.detail || 'No fue posible iniciar sesión'
      throw error
    } finally {
      loading.value = false
    }
  }

  const logout = () => {
    setTokens(null, null)
    user.value = null
    empresas.value = []
    adminEmpresas.value = []
    selectedEmpresa.value = null
    validation.value = null
    lastError.value = null
  }

  const setApiKey = (key: string | null) => {
    apiKey.value = key
  }

  const fetchEmpresas = async (params: AdminEmpresaQuery) => {
    loading.value = true
    lastError.value = null
    try {
      const query: Record<string, string | number> = {
        search_nit: params.searchNit
      }
      if (params.empresaServidorId) {
        query['empresa_servidor_id'] = params.empresaServidorId
      }
      if (params.nit) {
        query['nit'] = params.nit
      }
      if (params.anioFiscal) {
        query['anio_fiscal'] = params.anioFiscal
      }

      const response = await api.get<AdminEmpresasResponse>(
        '/assistant/api/tns/admin_empresas/',
        query
      )
      adminEmpresas.value = response.empresas.map(normalizeAdminEmpresa)

      if (
        adminEmpresas.value.length === 1 &&
        !selectedEmpresa.value
      ) {
        selectedEmpresa.value = adminEmpresas.value[0]
      }

      return response
    } catch (error: any) {
      lastError.value =
        error?.data?.message || 'No se pudo consultar la base ADMIN.gdb'
      throw error
    } finally {
      loading.value = false
    }
  }

  const validateTNSUser = async (payload: {
    empresa_servidor_id?: number
    nit?: string
    anio_fiscal?: number
    username: string
    password: string
  }) => {
    loading.value = true
    lastError.value = null
    try {
      const response = await api.post<TNSUserValidationPayload>(
        '/assistant/api/tns/validate_user/',
        payload
      )
      validation.value = response
      return response
    } catch (error: any) {
      lastError.value =
        error?.data?.message ||
        error?.data?.detail ||
        'No fue posible validar al usuario en TNS'
      throw error
    } finally {
      loading.value = false
    }
  }

  const selectEmpresa = (record: NormalizedEmpresa) => {
    selectedEmpresa.value = record
    applyPreferredTemplate(record.preferredTemplate)
  }

  const isAuthenticated = computed(
    () => !!(accessToken.value && user.value?.id)
  )

  return {
    user: readonly(user),
    empresas: readonly(empresas),
    adminEmpresas: readonly(adminEmpresas),
    selectedEmpresa,
    validation: readonly(validation),
    loading: readonly(loading),
    lastError: readonly(lastError),
    isAuthenticated,
    accessToken,
    apiKey,
    login,
    logout,
    setApiKey,
    fetchEmpresas,
    validateTNSUser,
    selectEmpresa
  }
}
