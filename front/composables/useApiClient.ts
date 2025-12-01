type QueryRecord = Record<string, string | number | boolean | null | undefined>

type ApiRequestOptions<TBody = any> = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: TBody
  query?: QueryRecord
  headers?: Record<string, string>
}

const buildQueryString = (query?: QueryRecord) => {
  if (!query) return ''
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (
      value === undefined ||
      value === null ||
      (typeof value === 'string' && value.length === 0)
    ) {
      return
    }
    params.append(key, String(value))
  })
  const result = params.toString()
  return result ? `?${result}` : ''
}

export const useApiClient = () => {
  const config = useRuntimeConfig()
  const { accessToken, apiKey } = useAuthState()
  const { getSubdomain } = useSubdomain()

  const baseHeaders = () => {
    const headers: Record<string, string> = {
      Accept: 'application/json'
    }

    if (accessToken.value) {
      headers['Authorization'] = `Bearer ${accessToken.value}`
    }

    if (apiKey.value) {
      headers['Api-Key'] = apiKey.value
    }

    const currentSubdomain = getSubdomain?.()
    if (currentSubdomain) {
      headers['X-Subdomain'] = currentSubdomain
    }

    return headers
  }

  const request = async <T>(
    path: string,
    options: ApiRequestOptions = {}
  ): Promise<T> => {
    const method = options.method || (options.body ? 'POST' : 'GET')
    const headers = {
      ...baseHeaders(),
      ...(options.headers || {})
    }

    const isFormData = options.body instanceof FormData
    // Si es FormData, NO establecer Content-Type - el navegador lo hace automáticamente con el boundary correcto
    if (!isFormData && !headers['Content-Type'] && options.body) {
      headers['Content-Type'] = 'application/json'
    }
    // Si es FormData y se pasó Content-Type en headers, eliminarlo para que el navegador lo establezca
    if (isFormData && headers['Content-Type']) {
      delete headers['Content-Type']
    }

    const queryString = buildQueryString(options.query)

    const payload =
      options.body && !isFormData ? JSON.stringify(options.body) : options.body

    return await $fetch<T>(`${path}${queryString}`, {
      baseURL: config.public.djangoApiUrl,
      method,
      body: payload as any,
      headers
    })
  }

  const get = async <T>(path: string, query?: QueryRecord) =>
    request<T>(path, { method: 'GET', query })

  const post = async <T, TBody = any>(path: string, body?: TBody, options?: { headers?: Record<string, string> }) =>
    request<T>(path, { method: 'POST', body, headers: options?.headers })

  const put = async <T, TBody = any>(path: string, body?: TBody, options?: { headers?: Record<string, string> }) =>
    request<T>(path, { method: 'PUT', body, headers: options?.headers })

  const patch = async <T, TBody = any>(path: string, body?: TBody, options?: { headers?: Record<string, string> }) =>
    request<T>(path, { method: 'PATCH', body, headers: options?.headers })

  const del = async <T>(path: string, query?: QueryRecord) =>
    request<T>(path, { method: 'DELETE', query })

  return {
    request,
    get,
    post,
    put,
    patch,
    delete: del
  }
}
