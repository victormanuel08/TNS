// Composable para manejar llamadas API
import { useRuntimeConfig } from '#app'
import { useAuthState } from '~/composables/useAuthState'

export const useApi = () => {
  const config = useRuntimeConfig()
  const { accessToken, apiKey } = useAuthState()

  const getHeaders = () => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }

    if (accessToken.value) {
      headers['Authorization'] = `Bearer ${accessToken.value}`
    }

    if (apiKey.value) {
      headers['Api-Key'] = apiKey.value
    }

    return headers
  }

  const api = {
    get: async <T = any>(url: string, options?: any): Promise<T> => {
      const response = await $fetch<T>(`${config.public.djangoApiUrl}${url}`, {
        method: 'GET',
        headers: getHeaders(),
        ...options
      })
      return response
    },

    post: async <T = any>(url: string, data?: any, options?: any): Promise<T> => {
      const response = await $fetch<T>(`${config.public.djangoApiUrl}${url}`, {
        method: 'POST',
        headers: getHeaders(),
        body: data,
        ...options
      })
      return response
    },

    put: async <T = any>(url: string, data?: any, options?: any): Promise<T> => {
      const response = await $fetch<T>(`${config.public.djangoApiUrl}${url}`, {
        method: 'PUT',
        headers: getHeaders(),
        body: data,
        ...options
      })
      return response
    },

    patch: async <T = any>(url: string, data?: any, options?: any): Promise<T> => {
      const response = await $fetch<T>(`${config.public.djangoApiUrl}${url}`, {
        method: 'PATCH',
        headers: getHeaders(),
        body: data,
        ...options
      })
      return response
    },

    delete: async <T = any>(url: string, options?: any): Promise<T> => {
      const response = await $fetch<T>(`${config.public.djangoApiUrl}${url}`, {
        method: 'DELETE',
        headers: getHeaders(),
        ...options
      })
      return response
    }
  }

  return { api, getHeaders }
}

