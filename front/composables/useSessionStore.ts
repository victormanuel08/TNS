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
  const adminEmpresas = useState<AdminEmpresaRecord[]>(
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
  // Guardar username del TNS por separado para fácil acceso
  const tnsUsername = useState<string | null>(
    'session-tns-username',
    () => null
  )
  // Computed para saber si el usuario TNS es ADMIN
  const isTNSAdmin = computed(() => {
    // Buscar username en varios lugares
    const username = tnsUsername.value || 
                     validation.value?.username ||
                     validation.value?.VALIDATE?.OUSERNAME || 
                     validation.value?.validation?.OUSERNAME
    if (!username) {
      console.log('[session] isTNSAdmin: No hay username', {
        tnsUsername: tnsUsername.value,
        validation: validation.value
      })
      return false
    }
    const isAdmin = String(username).toUpperCase() === 'ADMIN'
    console.log('[session] isTNSAdmin check:', { username, isAdmin })
    return isAdmin
  })
  const loading = useState('session-loading', () => false)
  const lastError = useState<string | null>('session-last-error', () => null)
  const empresaModalOpen = useState('session-empresa-modal', () => false)
  const nombreCliente = useState<string | null>('session-nombre-cliente', () => null)

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

  const groupedEmpresas = computed(() => {
    const map = new Map<
      string,
      { nit: string; nombre: string; items: NormalizedEmpresa[] }
    >()

    for (const empresa of empresas.value) {
      if (!map.has(empresa.nit)) {
        map.set(empresa.nit, {
          nit: empresa.nit,
          nombre: empresa.nombre,
          items: []
        })
      }
      map.get(empresa.nit)!.items.push(empresa)
    }

    return Array.from(map.values()).map((group) => {
      group.items.sort(
        (a, b) => (b.anioFiscal || 0) - (a.anioFiscal || 0)
      )
      return group
    })
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
    subdomain?: string
  }) => {
    loading.value = true
    lastError.value = null
    try {
      console.log('[session] Enviando login', credentials.username)
      // Si hay subdominio, validar que el usuario pertenezca a ese subdominio
      const headers: Record<string, string> = {}
      if (credentials.subdomain) {
        headers['X-Subdomain'] = credentials.subdomain
      }
      
      const response = await api.post<LoginResponse>(
        '/api/auth/login/',
        credentials,
        { headers }
      )
      console.log('[session] Login OK', {
        empresas: response.user?.empresas?.length || 0,
        default_empresa_id: response.user?.default_empresa_id
      })
      setTokens(response.access, response.refresh)
      user.value = response.user

      const userEmpresas = response.user?.empresas || []
      empresas.value = userEmpresas.map(normalizeUserEmpresa)
      adminEmpresas.value = []
      selectedEmpresa.value = null
      empresaModalOpen.value = empresas.value.length > 0
      console.log('[session] Empresas normalizadas', {
        empresas: empresas.value,
        modalOpen: empresaModalOpen.value
      })
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
    tnsUsername.value = null
    lastError.value = null
    empresaModalOpen.value = false
    nombreCliente.value = null
  }

  const setApiKey = (key: string | null) => {
    apiKey.value = key
    // Guardar en localStorage
    if (key) {
      localStorage.setItem('tns-api-key', key)
    } else {
      localStorage.removeItem('tns-api-key')
    }
  }

  const getStoredApiKey = (): string | null => {
    if (process.client) {
      return localStorage.getItem('tns-api-key')
    }
    return null
  }

  const loginWithApiKey = async (apiKeyValue: string) => {
    loading.value = true
    lastError.value = null
    try {
      console.log('[session] Validando API Key...')

      // Limpiar cualquier validación TNS previa (incluyendo ADMIN)
      validation.value = null
      tnsUsername.value = null
      try {
        if (process.client) {
          // Borrar todas las claves tns_validation_* de sessionStorage
          const keysToRemove: string[] = []
          for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i)
            if (key && key.startsWith('tns_validation_')) {
              keysToRemove.push(key)
            }
          }
          keysToRemove.forEach((k) => sessionStorage.removeItem(k))
          console.log('[session] Limpieza de validaciones TNS en sessionStorage:', keysToRemove)
        }
      } catch (e) {
        console.warn('[session] No fue posible limpiar sessionStorage de TNS:', e)
      }
      
      const response = await api.post<{
        valid: boolean
        nit: string
        nombre_cliente: string
        empresas: UserEmpresaResponse[]
        total_empresas: number
      }>('/api/api-keys/validar_api_key/', {
        api_key: apiKeyValue
      })

      if (!response.valid) {
        throw new Error('API Key inválida')
      }

      // Guardar API Key
      setApiKey(apiKeyValue)

      // Guardar nombre del cliente
      nombreCliente.value = response.nombre_cliente || null

      // Normalizar empresas
      empresas.value = response.empresas.map(normalizeUserEmpresa)
      adminEmpresas.value = []
      selectedEmpresa.value = null
      empresaModalOpen.value = empresas.value.length > 0

      // Aplicar template retail por defecto
      applyPreferredTemplate('retail')

      console.log('[session] API Key validada', {
        empresas: empresas.value.length,
        nit: response.nit,
        nombre_cliente: response.nombre_cliente
      })

      return response
    } catch (error: any) {
      lastError.value = error?.data?.error || 'Error al validar API Key'
      throw error
    } finally {
      loading.value = false
    }
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
        '/api/tns/admin_empresas/',
        query
      )
      adminEmpresas.value = response.empresas

      return response
    } catch (error: any) {
      lastError.value =
        error?.data?.message || 'No se pudo consultar la base ADMIN.gdb'
      throw error
    } finally {
      loading.value = false
    }
  }

  const setTNSValidation = (data: any) => {
    // Siempre actualizar el objeto de validación
    validation.value = data
    // Extraer y guardar el username del TNS
    // Puede venir en varios lugares según cómo se guarde:
    // 1. data.username (directo desde TNSValidationModal)
    // 2. data.VALIDATE.OUSERNAME (formato directo del response)
    // 3. data.validation.OUSERNAME (formato storageData)
    const username =
      data?.username || data?.VALIDATE?.OUSERNAME || data?.validation?.OUSERNAME

    if (username) {
      tnsUsername.value = String(username).toUpperCase()
      console.log('[session] TNS Username guardado:', tnsUsername.value)
    } else {
      // Si no hay username en la nueva validación, asegurarse de salir de modo ADMIN
      console.warn('[session] No se encontró username en nueva validación, limpiando tnsUsername', data)
      tnsUsername.value = null
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

    // Antes de validar un nuevo usuario TNS, limpiar el estado anterior
    // para evitar que se quede en modo ADMIN si la validación falla
    validation.value = null
    tnsUsername.value = null

    try {
      const body = { ...payload }
      if (!body.empresa_servidor_id && selectedEmpresa.value?.empresaServidorId) {
        body.empresa_servidor_id = selectedEmpresa.value.empresaServidorId
      }
      const response = await api.post<TNSUserValidationPayload>(
        '/api/tns/validate_user/',
        body
      )

      // Guardar validación y username usando la función centralizada
      setTNSValidation({
        ...response,
        username: response?.VALIDATE?.OUSERNAME
      })

      return response
    } catch (error: any) {
      // Si falla la validación, asegurarse de que no quede modo ADMIN
      validation.value = null
      tnsUsername.value = null

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
    empresaModalOpen.value = false

    // Si estamos en modo API Key, NO cargar validaciones TNS antiguas desde sessionStorage.
    // Siempre forzamos a una validación fresca de usuario TNS.
    if (apiKey.value) {
      console.log('[session] selectEmpresa en modo API Key: limpiando validación TNS previa')
      validation.value = null
      tnsUsername.value = null
      return
    }

    // Si hay validación TNS guardada para esta empresa, asegurarse de que esté disponible
    if (record.empresaServidorId && process.client) {
      // Buscar validación guardada - puede tener user.id o undefined al final
      const userId = user.value?.id || 'undefined'
      const storageKey = `tns_validation_${record.empresaServidorId}_${userId}`
      let stored = sessionStorage.getItem(storageKey)
      
      // Si no se encuentra con user.id, buscar con undefined (para API Key logins)
      if (!stored && !user.value?.id) {
        const storageKeyUndefined = `tns_validation_${record.empresaServidorId}_undefined`
        stored = sessionStorage.getItem(storageKeyUndefined)
      }
      
      // También buscar cualquier clave que empiece con tns_validation_{empresaServidorId}_
      if (!stored) {
        const prefix = `tns_validation_${record.empresaServidorId}_`
        for (let i = 0; i < sessionStorage.length; i++) {
          const key = sessionStorage.key(i)
          if (key && key.startsWith(prefix)) {
            stored = sessionStorage.getItem(key)
            console.log('[session] Validación encontrada con clave:', key)
            break
          }
        }
      }
      
      if (stored) {
        try {
          const data = JSON.parse(stored)
          console.log('[session] Cargando validación desde sessionStorage:', data)
          
          // Verificar que la validación fue exitosa
          const oSuccess = data.validation?.OSUCCESS
          const isSuccess = oSuccess === "1" || oSuccess === 1 || 
                            String(oSuccess).toLowerCase() === "true" ||
                            String(oSuccess).toLowerCase() === "si" ||
                            String(oSuccess).toLowerCase() === "yes"
          
          if (!isSuccess) {
            // Si la validación guardada falló, no cargarla
            console.warn('Validación guardada falló anteriormente, no se carga')
            return
          }
          
          // Verificar que no sea muy antigua (menos de 24 horas)
          const timestamp = new Date(data.timestamp)
          const now = new Date()
          const hoursDiff = (now.getTime() - timestamp.getTime()) / (1000 * 60 * 60)
          
          if (hoursDiff < 24) {
            // Cargar validación guardada
            setTNSValidation(data)
            console.log('[session] Validación TNS cargada desde sessionStorage')
          } else {
            console.log('[session] Validación TNS muy antigua, no se carga')
          }
        } catch (e) {
          console.error('Error cargando validación TNS:', e)
        }
      } else {
        console.log('[session] No se encontró validación TNS guardada para empresa:', record.empresaServidorId)
      }
    }
  }

  const isAuthenticated = computed(
    () => !!(accessToken.value && user.value?.id)
  )

  const openEmpresaModal = () => {
    console.log('[session] openEmpresaModal', {
      empresas: empresas.value.length,
      modalOpen: empresaModalOpen.value
    })
    if (empresas.value.length) {
      empresaModalOpen.value = true
    }
  }

  const closeEmpresaModal = () => {
    empresaModalOpen.value = false
  }

  return {
    user: readonly(user),
    empresas: readonly(empresas),
    adminEmpresas: readonly(adminEmpresas),
    groupedEmpresas,
    selectedEmpresa,
    validation: readonly(validation),
    tnsUsername: readonly(tnsUsername),
    loading: readonly(loading),
    lastError: readonly(lastError),
    empresaModalOpen,
    nombreCliente,
    isAuthenticated,
    accessToken,
    apiKey,
    isTNSAdmin,
    login,
    logout,
    setApiKey,
    getStoredApiKey,
    loginWithApiKey,
    fetchEmpresas,
    validateTNSUser,
    setTNSValidation,
    selectEmpresa,
    openEmpresaModal,
    closeEmpresaModal
  }
}
