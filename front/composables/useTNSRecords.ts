/**
 * Composable para consultar registros TNS usando el endpoint /api/tns/records/
 * Sin caché - siempre consulta datos frescos
 */

import type { TableConfig, ForeignKey } from './useModuleConfig'

export interface TNSRecordsFilters {
  [field: string]: any | {
    operator?: string
    value?: any
    contains?: string
    startsWith?: string
    between?: [any, any]
    in?: any[]
  }
  OR?: Array<Record<string, any>>
}

export interface TNSRecordsOrder {
  field: string
  direction: 'ASC' | 'DESC'
}

export interface TNSRecordsRequest {
  empresa_servidor_id: number
  table_name: string
  fields?: string[]
  foreign_keys?: ForeignKey[]
  filters?: TNSRecordsFilters
  order_by?: TNSRecordsOrder[]
  page?: number
  page_size?: number
}

export interface TNSRecordsResponse {
  data: any[]  // BCE usa 'data', no 'results'
  pagination: {  // BCE usa 'pagination', no campos separados
    total: number
    page: number
    page_size: number
    total_pages: number
    next: boolean
    previous: boolean
  }
}

export const useTNSRecords = () => {
  const api = useApiClient()
  const session = useSessionStore()

  const fetchRecords = async (
    config: TableConfig,
    options: {
      filters?: TNSRecordsFilters
      order_by?: TNSRecordsOrder[]
      page?: number
      page_size?: number
      empresa_servidor_id?: number
    } = {}
  ): Promise<TNSRecordsResponse> => {
    const empresaId = options.empresa_servidor_id || session.selectedEmpresa.value?.empresaServidorId

    if (!empresaId) {
      throw new Error('No hay empresa seleccionada')
    }

    // Construir campos a consultar (como BCE: todos los nombres de campos, incluyendo FK aliases)
    const fields = config.fields.map(f => f.name)
    
    // Asegurar que el localField de cada foreign key esté incluido (necesario para el JOIN)
    if (config.foreignKeys) {
      for (const fk of config.foreignKeys) {
        // Agregar el localField si no está en los campos (necesario para el JOIN)
        if (!fields.includes(fk.localField)) {
          fields.push(fk.localField)
        }
      }
    }

    // Construir foreign keys si existen (enviar tal cual como BCE)
    const foreignKeys = config.foreignKeys?.map(fk => ({
      table: fk.table,
      localField: fk.localField,
      foreignField: fk.foreignField,
      ...(fk.joinFrom ? { joinFrom: fk.joinFrom } : {}),  // Incluir joinFrom si existe
      ...(fk.joinType ? { joinType: fk.joinType } : {}),  // Incluir joinType si existe
      columns: fk.columns.map(col => ({
        name: col.name,
        as: col.as,
        ...(col.label ? { label: col.label } : {})
      }))
    })) || []
    
    console.debug('TNS Records Request:', {
      table_name: config.tableName,
      fields,
      foreign_keys: foreignKeys
    })

    // Request body
    const requestBody: TNSRecordsRequest = {
      empresa_servidor_id: empresaId,
      table_name: config.tableName,
      fields,
      foreign_keys: foreignKeys.length > 0 ? foreignKeys : undefined,
      filters: options.filters,
      order_by: options.order_by,
      page: options.page || 1,
      page_size: options.page_size || 50
    }

    try {
      const response = await api.post<TNSRecordsResponse>(
        '/api/tns/records/',
        requestBody
      )
      // Retornar formato BCE directamente: { data, pagination }
      return {
        data: response.data || [],
        pagination: response.pagination || {
          total: 0,
          page: options.page || 1,
          page_size: options.page_size || 50,
          total_pages: 0,
          next: false,
          previous: false
        }
      }
    } catch (error: any) {
      console.error('Error fetching TNS records:', error)
      throw new Error(error?.data?.error || 'Error al consultar registros')
    }
  }

  const searchRecords = async (
    config: TableConfig,
    searchQuery: string,
    options: {
      page?: number
      page_size?: number
      empresa_servidor_id?: number
    } = {}
  ): Promise<TNSRecordsResponse> => {
    // Construir filtros de búsqueda
    const filters: TNSRecordsFilters = {
      OR: config.searchFields.map(field => ({
        [field]: {
          contains: searchQuery
        }
      }))
    }

    return fetchRecords(config, {
      ...options,
      filters
    })
  }

  const applyFilter = async (
    config: TableConfig,
    filter: {
      table: string
      field: string
      value: string
    },
    options: {
      page?: number
      page_size?: number
      empresa_servidor_id?: number
    } = {}
  ): Promise<TNSRecordsResponse> => {
    const filters: TNSRecordsFilters = {
      [filter.field]: {
        operator: '=',
        value: filter.value
      }
    }

    return fetchRecords(config, {
      ...options,
      filters
    })
  }

  return {
    fetchRecords,
    searchRecords,
    applyFilter
  }
}

