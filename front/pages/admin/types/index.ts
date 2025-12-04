// Tipos TypeScript para el Admin Dashboard

export interface User {
  id: number
  username: string
  email?: string
  first_name?: string
  last_name?: string
  is_superuser: boolean
  is_staff: boolean
  is_active: boolean
  last_login?: string
  is_superuser_display?: string
  is_staff_display?: string
  last_login_formatted?: string
}

export interface Servidor {
  id: number
  nombre: string
  host: string
  usuario: string
  tipo_servidor: 'FIREBIRD' | 'POSTGRESQL' | 'SQLSERVER' | 'MYSQL'
  ruta_maestra?: string
  puerto?: number
  activo: boolean
  fecha_creacion: string
}

export interface EmpresaServidor {
  id: number
  codigo: string
  nombre: string
  nit?: string
  nit_normalizado: string
  representante_legal?: string
  anio_fiscal: number
  ruta_base?: string
  estado?: string
  servidor?: number
  servidor_nombre?: string
}

export interface BackupS3 {
  id: number
  empresa_servidor: number
  nombre_archivo: string
  ruta_s3: string
  tamano_bytes: number
  fecha_backup: string
  estado: 'pendiente' | 'procesando' | 'completado' | 'error'
  anio_fiscal: number
}

export interface APIKey {
  id: number
  nit: string
  nombre_cliente: string
  servidor?: number
  servidor_nombre?: string
  api_key: string
  api_key_masked?: string
  showKey?: boolean
  empresas_asociadas_count?: number
  activa: boolean
  expirada: boolean
  fecha_creacion: string
  fecha_caducidad: string
  contador_peticiones?: number
}

export interface EmpresaDominio {
  id: number
  dominio: string
  nit?: string
  servidor?: number
  servidor_nombre?: string
  empresa_servidor?: number
  empresa_servidor_nombre?: string
  anio_fiscal?: number
  modo: 'ecommerce' | 'autopago' | 'pro'
  activo: boolean
}

export interface VigenciaTributaria {
  id: number
  impuesto?: {
    codigo: string
    nombre: string
  }
  digitos_nit?: string
  tipo_tercero?: {
    codigo: string
  }
  tipo_regimen?: {
    codigo: string
  }
  fecha_limite: string
  descripcion?: string
  fecha_actualizacion?: string
}

export interface Section {
  id: string
  name: string
  icon: string
}

export interface ToastNotification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration?: number
}

