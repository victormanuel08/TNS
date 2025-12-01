/**
 * Configuración de módulos dinámicos para TNS
 * Copiado EXACTAMENTE de BCE - NO CAMBIAR NOMBRES
 */

export interface TableField {
  name: string
  label: string
  icon?: string
  primaryKey?: boolean
  primaryId?: string
  textAlign?: 'left' | 'center' | 'right'
  format?: 'currency' | 'date' | 'time' | 'badge' | 'number' | 'foreignkey'
  format2?: string
  badgeColor?: string
  badgeVariant?: string
  width?: string
  typetable?: 'basic' | 'detail'
  hidden?: boolean
}

export interface ForeignKey {
  table: string
  localField: string
  foreignField: string
  joinFrom?: string  // Tabla/FK desde la cual hacer el JOIN (para JOINs encadenados)
  joinType?: 'INNER' | 'LEFT' | 'RIGHT' | 'FULL'  // Tipo de JOIN (default: LEFT)
  columns: Array<{
    name: string
    as: string
    label?: string
  }>
}

export interface TableConfig {
  tableTitle: string
  tableName: string
  primaryKey: string
  searchPlaceholder: string
  emptyMessage: string
  apiEndpoint: string  // Siempre /api/tns/records/
  fields: TableField[]
  foreignKeys?: ForeignKey[]
  searchFields: string[]
  filters?: Array<{
    table: string
    field: string
    value: string
    label: string
    formnew?: {
      fields: Record<string, any>
    }
  }>
}

export interface Module {
  value: string
  label: string
  icon?: string
  tables: Array<{ value: string; label: string }>
  tablesconfig?: Array<{ value: string; label: string }>
  filters?: Array<{
    table: string
    field: string
    value: string
    label: string
    formnew?: {
      fields: Record<string, any>
    }
  }>
}

export const useModuleConfig = () => {
  const modules: Module[] = [
    {
      value: 'facturacion',
      label: 'Facturación',
      icon: 'i-heroicons-document-text',
      tables: [
        { value: 'facturacion', label: 'Facturación' },
        { value: 'defacturacion', label: 'Facturación Detallada' }
      ],
      tablesconfig: [
        { value: 'area', label: 'Áreas' },
        { value: 'banco', label: 'Bancos' },
        { value: 'bodega', label: 'Bodegas' },
        { value: 'centros', label: 'Centros' },
        { value: 'clasificacion', label: 'Clasificación' },
        { value: 'concepto', label: 'Concepto' }
      ],
      filters: [
        {
          table: 'KARDEX',
          field: 'CODCOMP',
          value: 'FV',
          label: 'Factura de Venta',
          formnew: {
            fields: {
              CODCOMP: 'FV',
              CODPREFIJO: '',
              NUMERO: '',
              FECHA: '',
              CLIENTE_CODIGO: '',
              CLIENTE_NOMBRE: '',
              USUARIO: '',
              FORMAPAGO: '',
              OBSERV: '',
              TOTAL: 0
            }
          }
        },
        { table: 'KARDEX', field: 'CODCOMP', value: 'DV', label: 'Devolución de Venta' },
        { table: 'KARDEX', field: 'CODCOMP', value: 'RS', label: 'Remisión de Salida' },
        { table: 'KARDEX', field: 'CODCOMP', value: 'CT', label: 'Cotización' },
        { table: 'KARDEX', field: 'CODCOMP', value: 'PV', label: 'Pedido de Venta' }
      ]
    },
    {
      value: 'tesoreria',
      label: 'Tesorería',
      icon: 'i-heroicons-banknotes',
      tables: [
        { value: 'tesoreria', label: 'Tesorería Documentos' },
        { value: 'detesoreria', label: 'Tesorería Documentos Detallada' },
        { value: 'recibos', label: 'Recibos' },
        { value: 'derecibos', label: 'Recibos Detalladas' }
      ],
      filters: [
        { table: 'DOCUMENTO', field: 'CODCOMP', value: 'FC', label: 'Factura de Compra' },
        { table: 'DOCUMENTO', field: 'CODCOMP', value: 'ND', label: 'Nota de Débito' },
        { table: 'RECIBO', field: 'CODCOMP', value: 'CE', label: 'Comprobante de Egreso' }
      ]
    },
    {
      value: 'cartera',
      label: 'Cartera',
      icon: 'i-heroicons-credit-card',
      tables: [
        { value: 'cartera', label: 'Cartera Documentos' },
        { value: 'decartera', label: 'Cartera Documentos Detallada' },
        { value: 'recibos', label: 'Cartera Recibos' },
        { value: 'derecibos', label: 'Cartera Recibos Detallados' }
      ],
      filters: [
        { table: 'DOCUMENTO', field: 'CODCOMP', value: 'FV', label: 'Factura de Venta' },
        { table: 'DOCUMENTO', field: 'CODCOMP', value: 'ND', label: 'Nota de Débito' },
        { table: 'DOCUMENTO', field: 'CODCOMP', value: 'NE', label: 'Nota de Intereses' },
        { table: 'RECIBO', field: 'CODCOMP', value: 'RC', label: 'Recibo de Caja' }
      ]
    },
    {
      value: 'inventario',
      label: 'Inventario',
      icon: 'i-heroicons-cube',
      tables: [
        { value: 'facturacion', label: 'Inventario' },
        { value: 'defacturacion', label: 'Inventario Detallado' }
      ],
      filters: [
        { table: 'KARDEX', field: 'CODCOMP', value: 'CO', label: 'Consumo' },
        { table: 'KARDEX', field: 'CODCOMP', value: 'FC', label: 'Factura de Compra' },
        { table: 'KARDEX', field: 'CODCOMP', value: 'DC', label: 'Devolución de Compra' },
        { table: 'KARDEX', field: 'CODCOMP', value: 'RE', label: 'Remisión de Entrada' },
        { table: 'KARDEX', field: 'CODCOMP', value: 'IN', label: 'Nota de Inventario' }
      ]
    },
    {
      value: 'contabilidad',
      label: 'Contabilidad',
      icon: 'i-heroicons-calculator',
      tables: [
        { value: 'contabilidad', label: 'Contabilidad' },
        { value: 'decontabilidad', label: 'Contabilidad Detallada' }
      ]
    },
    {
      value: 'nomina',
      label: 'Nómina',
      icon: 'i-heroicons-users',
      tables: []
    },
    {
      value: 'dian',
      label: 'DIAN',
      icon: 'i-heroicons-document-check',
      tables: []
    },
    {
      value: 'archivos',
      label: 'Archivos',
      icon: 'i-heroicons-folder',
      tables: []
    },
    {
      value: 'calendario',
      label: 'Calendario',
      icon: 'i-heroicons-calendar-days',
      tables: []
    }
  ]

  const configs: Record<string, TableConfig> = {
    facturacion: {
      tableTitle: 'Facturación',
      tableName: 'KARDEX',
      primaryKey: 'KARDEXID',
      searchPlaceholder: 'Buscar por código o descripción...',
      emptyMessage: 'No se encontraron resultados',
      apiEndpoint: '/api/tns/records/',
      fields: [
        {
          name: 'CODCOMP',
          label: 'Tipo',
          icon: 'i-heroicons-document-text',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'CODPREFIJO',
          label: 'Prefijo',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'NUMERO',
          label: 'Número',
          icon: 'i-heroicons-identification',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'FECHA',
          label: 'Fecha',
          icon: 'i-heroicons-calendar',
          textAlign: 'center',
          format: 'date'
        },
        {
          name: 'CLIENTE_CODIGO',
          label: 'Código',
          primaryKey: true,
          primaryId: 'CLIENTE',
          icon: 'i-heroicons-barcode',
          textAlign: 'center',
          typetable: 'basic',
          format: 'foreignkey'
        },
        {
          name: 'CLIENTE_NOMBRE',
          label: 'Cliente',
          primaryKey: true,
          primaryId: 'CLIENTE',
          icon: 'i-heroicons-user-circle',
          textAlign: 'left',
          typetable: 'basic',
          format: 'foreignkey'
        },
        {
          name: 'USUARIO',
          label: 'Usuario',
          icon: 'i-heroicons-user',
          textAlign: 'left'
        },
        {
          name: 'FECASENTAD',
          label: 'Asentada',
          icon: 'i-heroicons-check-circle',
          textAlign: 'center',
          format: 'badge',
          format2: 'date',
          badgeColor: 'blue',
          typetable: 'basic'
        },
        {
          name: 'HORAASEN',
          label: 'Hora',
          icon: 'i-heroicons-clock',
          textAlign: 'center',
          format: 'time'
        },
        {
          name: 'IMPRESA',
          label: 'Impresa',
          icon: 'i-heroicons-printer',
          textAlign: 'center'
        },
        {
          name: 'NOMVENDEDOR',
          label: 'Vendedor',
          icon: 'i-heroicons-user',
          textAlign: 'left',
          typetable: 'basic'
        },
        {
          name: 'FORMAPAGO',
          label: 'Pago',
          icon: 'i-heroicons-credit-card',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'OBSERV',
          label: 'Observaciones',
          icon: 'i-heroicons-information-circle',
          textAlign: 'left',
          typetable: 'basic'
        },
        {
          name: 'VRBASE',
          label: 'Vr. Base',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'VRIVA',
          label: 'Vr. IVA',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'TOTAL',
          label: 'Total',
          icon: 'i-heroicons-credit-card',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'FPCONTADO',
          label: 'Pago Contado',
          icon: 'i-heroicons-credit-card',
          textAlign: 'center',
          format: 'badge',
          format2: 'currency'
        },
        {
          name: 'FPCREDITO',
          label: 'Pago Crédito',
          icon: 'i-heroicons-credit-card',
          textAlign: 'center',
          format: 'badge',
          format2: 'currency'
        },
        {
          name: 'PERIODO',
          label: 'Periodo',
          icon: 'i-heroicons-calendar-days',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'CUFE',
          label: 'DIAN',
          icon: 'i-heroicons-document-check',
          textAlign: 'left',
          typetable: 'basic'
        }
      ],
      foreignKeys: [
        {
          table: 'TERCEROS',
          localField: 'CLIENTE',
          foreignField: 'TERID',
          columns: [
            { name: 'NOMBRE', as: 'CLIENTE_NOMBRE', label: 'Tercero' },
            { name: 'NIT', as: 'CLIENTE_CODIGO', label: 'Nit' }
          ]
        },
        {
          table: 'CENTROS',
          localField: 'CENID',
          foreignField: 'CENID',
          columns: [
            { name: 'DESCRIP', as: 'CENTRO_DESCRIP', label: 'Centro' },
            { name: 'NRO', as: 'CENTRO_CODIGO', label: 'Num Centro' }
          ]
        },
        {
          table: 'AREAD',
          localField: 'AREADID',
          foreignField: 'AREADID',
          columns: [
            { name: 'CODAREAD', as: 'AREA_CODIGO', label: 'Cod Área' },
            { name: 'NOMAREAD', as: 'AREA_NOMBRE', label: 'Área' }
          ]
        },
        {
          table: 'SUCURSAL',
          localField: 'SUCID',
          foreignField: 'SUCID',
          columns: [
            { name: 'DESCRIP', as: 'SUCURSAL_DESCRIP', label: 'Sucursal' },
            { name: 'NRO', as: 'SUCURSAL_CODIGO', label: 'Cód Sucursal' }
          ]
        },
        {
          table: 'BANCO',
          localField: 'BCOID',
          foreignField: 'BCOID',
          columns: [
            { name: 'NOMBRE', as: 'BANCO_NOMBRE', label: 'Banco' },
            { name: 'CODIGO', as: 'BANCO_CODIGO', label: 'Cód Banco' }
          ]
        },
        {
          table: 'CONCEPTO',
          localField: 'CONCEPTO',
          foreignField: 'CONCID',
          columns: [
            { name: 'DESCRIP', as: 'CONCEPTO_DESCRIP', label: 'Concepto' },
            { name: 'NRO', as: 'CONCEPTO_CODIGO', label: 'Cód Concepto' }
          ]
        },
        {
          table: 'DOCUMENTO',
          localField: 'DOCUID',
          foreignField: 'DOCUID',
          columns: [
            { name: 'NUMERO', as: 'NUMERO_DOCUMENTO', label: 'Número Doc' },
            { name: 'DETALLE', as: 'DETALLE_DOCUMENTO', label: 'Detalle Doc' }
          ]
        },
        {
          table: 'DOCUMENTO',
          localField: 'DOCUID2',
          foreignField: 'DOCUID',
          columns: [
            { name: 'DESCRIP', as: 'DOCUMENTO_DESCRIP', label: 'Descripción' },
            { name: 'NRO', as: 'DOCUMENTO_CODIGO', label: 'Código' }
          ]
        }
      ],
      searchFields: ['CLIENTE_CODIGO', 'CLIENTE_NOMBRE', 'NUMERO', 'CODPREFIJO', 'CODCOMP']
    },
    defacturacion: {
      tableTitle: 'Facturación Detallada',
      tableName: 'DEKARDEX',
      primaryKey: 'DEKARDEXID',
      searchPlaceholder: 'Buscar por código o descripción...',
      emptyMessage: 'No se encontraron resultados',
      apiEndpoint: '/api/tns/records/',
      fields: [
        {
          name: 'KARDEX_CODCOMP',
          label: 'Tipo',
          icon: 'i-heroicons-document-text',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'KARDEXID',
          typetable: 'basic'
        },
        {
          name: 'KARDEX_CODPREFIJO',
          label: 'Prefijo',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'KARDEXID',
          typetable: 'basic'
        },
        {
          name: 'KARDEX_NUMERO',
          label: 'Número',
          icon: 'i-heroicons-identification',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'KARDEXID',
          typetable: 'basic'
        },
        {
          name: 'KARDEX_FECHA',
          label: 'Fecha',
          icon: 'i-heroicons-calendar',
          textAlign: 'center',
          format: 'foreignkey',
          format2: 'date',
          primaryKey: true,
          primaryId: 'KARDEXID'
        },
        {
          name: 'KARDEX_ASENTADA',
          label: 'Asentada',
          icon: 'i-heroicons-check-circle',
          textAlign: 'center',
          format: 'foreignkey',
          format2: 'badge',
          badgeColor: 'blue',
          primaryKey: true,
          primaryId: 'KARDEXID',
          typetable: 'basic'
        },
        {
          name: 'MAT_CODIGO',
          label: 'Código',
          icon: 'i-heroicons-barcode',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'MATID'
        },
        {
          name: 'MAT_DESCRIP',
          label: 'Material',
          icon: 'i-heroicons-document-text',
          textAlign: 'left',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'MATID',
          typetable: 'basic'
        },
        {
          name: 'BOD_CODIGO',
          label: 'Código Bodega',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'BODID'
        },
        {
          name: 'TIPUND',
          label: 'Unidad',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center'
        },
        {
          name: 'PORCIVA',
          label: '% IVA',
          icon: 'i-heroicons-percent',
          textAlign: 'center'
        },
        {
          name: 'DESCUENTO',
          label: 'Descuento',
          icon: 'i-heroicons-tag',
          textAlign: 'center'
        },
        {
          name: 'CANMAT',
          label: 'Cantidad',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'PRECIOVTA',
          label: 'Precio Venta',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'PRECIOBASE',
          label: 'Precio Base',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'center'
        },
        {
          name: 'PRECIOIVA',
          label: 'Precio IVA',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'center'
        },
        {
          name: 'PRECIOICONSUMO',
          label: 'Precio I. Consumo',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'center'
        },
        {
          name: 'PRECIONETO',
          label: 'Precio Neto',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'center'
        },
        {
          name: 'PARCVTA',
          label: 'Parcial Venta',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'center'
        },
        {
          name: 'PARCOSTO',
          label: 'Parcial Costo',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'center'
        }
      ],
      foreignKeys: [
        {
          table: 'KARDEX',
          localField: 'KARDEXID',
          foreignField: 'KARDEXID',
          columns: [
            { name: 'CODCOMP', as: 'KARDEX_CODCOMP', label: 'Tipo' },
            { name: 'CODPREFIJO', as: 'KARDEX_CODPREFIJO', label: 'Prefijo' },
            { name: 'NUMERO', as: 'KARDEX_NUMERO', label: 'Número' },
            { name: 'FECHA', as: 'KARDEX_FECHA', label: 'Fecha' },
            { name: 'FECASENTAD', as: 'KARDEX_ASENTADA', label: 'Asentada' }
          ]
        },
        {
          table: 'MATERIAL',
          localField: 'MATID',
          foreignField: 'MATID',
          columns: [
            { name: 'CODIGO', as: 'MAT_CODIGO', label: 'Código' },
            { name: 'DESCRIP', as: 'MAT_DESCRIP', label: 'Descripción' }
          ]
        },
        {
          table: 'BODEGA',
          localField: 'BODID',
          foreignField: 'BODID',
          columns: [
            { name: 'CODIGO', as: 'BOD_CODIGO', label: 'Código' },
            { name: 'DESCRIP', as: 'BOD_DESCRIP', label: 'Descripción' }
          ]
        }
      ],
      searchFields: ['KARDEX_CODCOMP', 'KARDEX_CODPREFIJO', 'KARDEX_NUMERO', 'KARDEX_CLIENTE_CODIGO', 'KARDEX_CLIENTE_NOMBRE', 'MAT_CODIGO', 'MAT_DESCRIP', 'BOD_CODIGO', 'BOD_DESCRIP']
    },
    contabilidad: {
      tableTitle: 'Contabilidad',
      tableName: 'MOVI',
      primaryKey: 'MOVID',
      searchPlaceholder: 'Buscar por código o descripción...',
      emptyMessage: 'No se encontraron registros',
      apiEndpoint: '/api/tns/records/',
      fields: [
        {
          name: 'MOVID',
          label: 'ID',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center'
        },
        {
          name: 'CODCOMP',
          label: 'Tipo',
          icon: 'i-heroicons-document-text',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'CODPREFIJO',
          label: 'Prefijo',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'NUMERO',
          label: 'Número',
          icon: 'i-heroicons-identification',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'FECHA',
          label: 'Fecha',
          icon: 'i-heroicons-calendar',
          textAlign: 'center',
          format: 'date',
          typetable: 'basic'
        },
        {
          name: 'TOTDB',
          label: 'Total Débito',
          icon: 'i-heroicons-arrow-down-circle',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'TOTCR',
          label: 'Total Crédito',
          icon: 'i-heroicons-arrow-up-circle',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'TOTDBNIIF',
          label: 'Total Débito',
          icon: 'i-heroicons-arrow-down-circle',
          textAlign: 'right',
          format: 'currency'
        },
        {
          name: 'TOTCRNIIF',
          label: 'Total Crédito',
          icon: 'i-heroicons-arrow-up-circle',
          textAlign: 'right',
          format: 'currency'
        },
        {
          name: 'FECASENT',
          label: 'Asentada',
          icon: 'i-heroicons-check-circle',
          textAlign: 'center',
          format: 'badge',
          format2: 'date',
          badgeColor: 'blue',
          typetable: 'basic'
        },
        {
          name: 'PERIODO',
          label: 'Periodo',
          icon: 'i-heroicons-calendar-days',
          textAlign: 'center'
        },
        {
          name: 'IMPORTADO',
          label: 'Importado',
          icon: 'i-heroicons-world',
          textAlign: 'center'
        },
        {
          name: 'AREA_NOMBRE',
          label: 'Area',
          icon: 'i-heroicons-building-office-2',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'AREADID'
        }
      ],
      foreignKeys: [
        {
          table: 'AREAD',
          localField: 'AREADID',
          foreignField: 'AREADID',
          columns: [
            { name: 'CODAREAD', as: 'AREA_CODIGO', label: 'Código' },
            { name: 'NOMAREAD', as: 'AREA_NOMBRE', label: 'Nombre' }
          ]
        }
      ],
      searchFields: ['CLIENTE_CODIGO', 'CLIENTE_NOMBRE', 'NUMERO', 'CODPREFIJO', 'CODCOMP']
    },
    decontabilidad: {
      tableTitle: 'Contabilidad Detallada',
      tableName: 'DEMOVI',
      primaryKey: 'DMVID',
      searchPlaceholder: 'Buscar...',
      emptyMessage: 'No se encontraron registros',
      apiEndpoint: '/api/tns/records/',
      fields: [
        {
          name: 'DMVID',
          label: 'ID',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center'
        },
        {
          name: 'MOVI_FECHA',
          label: 'Fecha',
          icon: 'i-heroicons-calendar',
          textAlign: 'center',
          format: 'foreignkey',
          format2: 'date',
          primaryKey: true,
          primaryId: 'MOVID'
        },
        {
          name: 'MOVI_PERIODO',
          label: 'Periodo',
          icon: 'i-heroicons-calendar-days',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'MOVID'
        },
        {
          name: 'MOVI_CODCOMP',
          label: 'Código Comprobante',
          icon: 'i-heroicons-document-text',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'MOVID'
        },
        {
          name: 'MOVI_CODPREFIJO',
          label: 'Prefijo',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'MOVID'
        },
        {
          name: 'MOVI_NUMERO',
          label: 'Número Comprobante',
          icon: 'i-heroicons-identification',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'MOVID'
        },
        {
          name: 'VALORTRA',
          label: 'Valor',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'TIPOCD',
          label: 'Tipo',
          icon: 'i-heroicons-tag',
          textAlign: 'center',
          format: 'badge',
          format2: 'type',
          badgeColor: 'blue',
          badgeVariant: 'solid',
          typetable: 'basic'
        },
        {
          name: 'MOVI_OBS',
          label: 'Observaciones',
          icon: 'i-heroicons-information-circle',
          textAlign: 'left',
          format: 'foreignkey',
          typetable: 'basic',
          primaryKey: true,
          primaryId: 'MOVID'
        },
        {
          name: 'MOVI_TOTDB',
          label: 'Total Débito',
          icon: 'i-heroicons-arrow-down-circle',
          textAlign: 'right',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'MOVID',
          format2: 'currency',
          typetable: 'basic'
        },
        {
          name: 'MOVI_TOTCR',
          label: 'Total Crédito',
          icon: 'i-heroicons-arrow-up-circle',
          textAlign: 'right',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'MOVID',
          format2: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PUC_NOMBRE',
          label: 'Cuenta PUC',
          icon: 'i-heroicons-document',
          textAlign: 'left',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'PUCID',
          typetable: 'basic'
        },
        {
          name: 'PUC_CODIGO',
          label: 'Código PUC',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'PUCID',
          typetable: 'basic'
        },
        {
          name: 'TIPDOCUM',
          label: 'Tipo Documento',
          icon: 'i-heroicons-document-text',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'NRODOCUM',
          label: 'Número Documento',
          icon: 'i-heroicons-identification',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'AREA_CODIGO',
          label: 'Código Área',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'AREADID'
        },
        {
          name: 'AREA_NOMBRE',
          label: 'Nombre Área',
          icon: 'i-heroicons-building-office-2',
          textAlign: 'left',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'AREADID'
        },
        {
          name: 'CENTRO_DESCRIP',
          label: 'Centro Descripción',
          icon: 'i-heroicons-information-circle',
          textAlign: 'left',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'CENID'
        },
        {
          name: 'CENTRO_CODIGO',
          label: 'Centro Código',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'CENID'
        },
        {
          name: 'OBSTRA',
          label: 'Observaciones',
          icon: 'i-heroicons-information-circle',
          textAlign: 'left',
          typetable: 'basic'
        },
        {
          name: 'TERCERO_NOMBRE',
          label: 'Tercero Nombre',
          icon: 'i-heroicons-user-circle',
          textAlign: 'left',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'TERID',
          typetable: 'basic'
        },
        {
          name: 'TERCERO_NITTRI',
          label: 'Tercero NIT',
          icon: 'i-heroicons-barcode',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'TERID',
          typetable: 'basic'
        },
        {
          name: 'TERCERO_NIT',
          label: 'Tercero NIT',
          icon: 'i-heroicons-barcode',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'TERID'
        }
      ],
      foreignKeys: [
        {
          table: 'MOVI',
          localField: 'MOVID',
          foreignField: 'MOVID',
          columns: [
            { name: 'FECHA', as: 'MOVI_FECHA', label: 'Fecha' },
            { name: 'PERIODO', as: 'MOVI_PERIODO', label: 'Periodo' },
            { name: 'CODCOMP', as: 'MOVI_CODCOMP', label: 'Comprobante' },
            { name: 'CODPREFIJO', as: 'MOVI_CODPREFIJO', label: 'Prefijo' },
            { name: 'NUMERO', as: 'MOVI_NUMERO', label: 'Número' },
            { name: 'OBS', as: 'MOVI_OBS', label: 'Observaciones' },
            { name: 'TOTDB', as: 'MOVI_TOTDB', label: 'Total Debito' },
            { name: 'TOTCR', as: 'MOVI_TOTCR', label: 'Total Credito' }
          ]
        },
        {
          table: 'AREAD',
          localField: 'AREADID',
          foreignField: 'AREADID',
          columns: [
            { name: 'CODAREAD', as: 'AREA_CODIGO', label: 'Código' },
            { name: 'NOMAREAD', as: 'AREA_NOMBRE', label: 'Nombre' }
          ]
        },
        {
          table: 'PLANCUENTAS',
          localField: 'PUCID',
          foreignField: 'PUCID',
          columns: [
            { name: 'NOMBRE', as: 'PUC_NOMBRE', label: 'Nombre' },
            { name: 'CODIGO', as: 'PUC_CODIGO', label: 'Código' }
          ]
        },
        {
          table: 'TERCEROS',
          localField: 'TERID',
          foreignField: 'TERID',
          columns: [
            { name: 'NOMBRE', as: 'TERCERO_NOMBRE', label: 'Nombre' },
            { name: 'NIT', as: 'TERCERO_NIT', label: 'NIT' },
            { name: 'NITTRI', as: 'TERCERO_NITTRI', label: 'NITTRI' }
          ]
        },
        {
          table: 'CENTROS',
          localField: 'CENID',
          foreignField: 'CENID',
          columns: [
            { name: 'DESCRIP', as: 'CENTRO_DESCRIP', label: 'Descripción' },
            { name: 'NRO', as: 'CENTRO_CODIGO', label: 'Código' }
          ]
        }
      ],
      searchFields: ['CLIENTE_CODIGO', 'CLIENTE_NOMBRE', 'NUMERO', 'CODPREFIJO', 'CODCOMP']
    },
    tesoreria: {
      tableTitle: 'Tesorería',
      tableName: 'DOCUMENTO',
      primaryKey: 'DOCUID',
      searchPlaceholder: 'Buscar movimientos...',
      emptyMessage: 'No se encontraron movimientos',
      apiEndpoint: '/api/tns/records/',
      fields: [
        { name: 'TIPOIE', label: 'Tipo', icon: 'i-heroicons-document-text', textAlign: 'center', typetable: 'basic' },
        { name: 'CODCOMP', label: 'Comprobante', icon: 'i-heroicons-tag', textAlign: 'center', typetable: 'basic' },
        { name: 'CODPREFIJO', label: 'Prefijo', icon: 'i-heroicons-hashtag', textAlign: 'center', typetable: 'basic' },
        { name: 'NUMERO', label: 'Número', icon: 'i-heroicons-hashtag', textAlign: 'center', typetable: 'basic' },
        { name: 'FECHA', label: 'Fecha', icon: 'i-heroicons-calendar', textAlign: 'center', format: 'date' },
        {
          name: 'TERCERO_NOMBRE',
          label: 'Tercero',
          icon: 'i-heroicons-user-circle',
          textAlign: 'left',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'TERID',
          typetable: 'basic'
        },
        {
          name: 'TERCERO_NIT',
          label: 'Tercero NIT',
          icon: 'i-heroicons-barcode',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'TERID',
          typetable: 'basic'
        },
        { name: 'DETALLE', label: 'Detalle', icon: 'i-heroicons-information-circle', textAlign: 'left', typetable: 'basic' },
        { name: 'VALOR', label: 'Valor', icon: 'i-heroicons-currency-dollar', textAlign: 'right', format: 'currency', typetable: 'basic' },
        { name: 'DESCUENTO', label: 'Descuento', icon: 'i-heroicons-currency-dollar', textAlign: 'right', format: 'currency' },
        { name: 'NETO', label: 'Neto', icon: 'i-heroicons-banknotes', textAlign: 'right', format: 'currency' },
        { name: 'SALDO', label: 'Saldo', icon: 'i-heroicons-scale', textAlign: 'right', format: 'currency', typetable: 'basic' },
        { name: 'PERIODO', label: 'Periodo', icon: 'i-heroicons-calendar-days', textAlign: 'center', typetable: 'basic' },
        {
          name: 'SUCURSAL_CODIGO',
          label: 'Cod. Sucursal',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'SUCID'
        },
        {
          name: 'SUCURSAL_DESCRIP',
          label: 'Sucursal',
          icon: 'i-heroicons-building-office-2',
          textAlign: 'left',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'SUCID'
        },
        {
          name: 'FECASENT',
          label: 'Asentada',
          icon: 'i-heroicons-check-circle',
          textAlign: 'center',
          format: 'badge',
          format2: 'date',
          badgeColor: 'blue',
          badgeVariant: 'solid',
          typetable: 'basic'
        },
        { name: 'IMPORTADO', label: 'Importado', icon: 'i-heroicons-globe-alt', textAlign: 'center', typetable: 'basic' },
        {
          name: 'AREA_CODIGO',
          label: 'Cod. Área',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'AREADID',
          typetable: 'basic'
        },
        {
          name: 'AREA_NOMBRE',
          label: 'Área',
          icon: 'i-heroicons-building-office-2',
          textAlign: 'left',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'AREADID'
        },
        {
          name: 'CENTRO_CODIGO',
          label: 'Cod. Centro',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'CENID',
          typetable: 'basic'
        },
        {
          name: 'CENTRO_DESCRIP',
          label: 'Centro costo',
          icon: 'i-heroicons-rectangle-group',
          textAlign: 'left',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'CENID'
        },
        { name: 'FECVENCE', label: 'Fecha vence', icon: 'i-heroicons-calendar', textAlign: 'center', format: 'date' },
        { name: 'FECSERV', label: 'Fecha servicio', icon: 'i-heroicons-calendar', textAlign: 'center', format: 'date' },
        {
          name: 'VENDEDOR_NOMBRE',
          label: 'Vendedor',
          icon: 'i-heroicons-user',
          textAlign: 'left',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'VENDEDOR',
          typetable: 'basic'
        },
        {
          name: 'VENDEDOR_NIT',
          label: 'NIT vendedor',
          icon: 'i-heroicons-barcode',
          textAlign: 'center',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'VENDEDOR'
        },
        { name: 'VRBASE', label: 'Vr Base', icon: 'i-heroicons-currency-dollar', textAlign: 'right', format: 'currency' },
        { name: 'VRINICIAL', label: 'Vr Inicial', icon: 'i-heroicons-currency-dollar', textAlign: 'right', format: 'currency' },
        { name: 'FECULTPAGO', label: 'Último pago', icon: 'i-heroicons-calendar', textAlign: 'center', format: 'date', typetable: 'basic' },
        { name: 'SALDOBASE', label: 'Saldo Base', icon: 'i-heroicons-banknotes', textAlign: 'right', format: 'currency' },
        {
          name: 'PUC_CODIGO',
          label: 'Cuenta PUC',
          icon: 'i-heroicons-clipboard-document-list',
          textAlign: 'left',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'PUCID',
          typetable: 'basic'
        },
        {
          name: 'PUC_NOMBRE',
          label: 'Nombre cuenta',
          icon: 'i-heroicons-document-text',
          textAlign: 'left',
          format: 'foreignkey',
          primaryKey: true,
          primaryId: 'PUCID'
        }
      ],
      foreignKeys: [
        {
          table: 'TERCEROS',
          localField: 'TERID',
          foreignField: 'TERID',
          columns: [
            { name: 'NOMBRE', as: 'TERCERO_NOMBRE', label: 'Tercero' },
            { name: 'NIT', as: 'TERCERO_NIT', label: 'NIT' }
          ]
        },
        {
          table: 'TERCEROS',
          localField: 'VENDEDOR',
          foreignField: 'TERID',
          columns: [
            { name: 'NOMBRE', as: 'VENDEDOR_NOMBRE', label: 'Vendedor' },
            { name: 'NIT', as: 'VENDEDOR_NIT', label: 'NIT' }
          ]
        },
        {
          table: 'PLANCUENTAS',
          localField: 'PUCID',
          foreignField: 'PUCID',
          columns: [
            { name: 'NOMBRE', as: 'PUC_NOMBRE', label: 'Cuenta' },
            { name: 'CODIGO', as: 'PUC_CODIGO', label: 'Código' }
          ]
        },
        {
          table: 'AREAD',
          localField: 'AREADID',
          foreignField: 'AREADID',
          columns: [
            { name: 'CODAREAD', as: 'AREA_CODIGO', label: 'Cod. Área' },
            { name: 'NOMAREAD', as: 'AREA_NOMBRE', label: 'Área' }
          ]
        },
        {
          table: 'CENTROS',
          localField: 'CENID',
          foreignField: 'CENID',
          columns: [
            { name: 'DESCRIP', as: 'CENTRO_DESCRIP', label: 'Centro' },
            { name: 'NRO', as: 'CENTRO_CODIGO', label: 'Código' }
          ]
        },
        {
          table: 'SUCURSAL',
          localField: 'SUCID',
          foreignField: 'SUCID',
          columns: [
            { name: 'NOMSUC', as: 'SUCURSAL_DESCRIP', label: 'Sucursal' },
            { name: 'CODSUC', as: 'SUCURSAL_CODIGO', label: 'Código' }
          ]
        }
      ],
      searchFields: ['NUMERO', 'CODCOMP', 'TERCERO_NOMBRE', 'DETALLE']
    },
    detesoreria: {
      tableTitle: 'Tesorería Detallada',
      tableName: 'DEDOCUM',
      primaryKey: 'DEDOCUMID',
      searchPlaceholder: 'Buscar...',
      emptyMessage: 'No se encontraron registros',
      apiEndpoint: '/api/tns/records/',
      fields: [
        { name: 'DOCUMENTO_TIPOIE', label: 'Tipo', icon: 'i-heroicons-document-text', textAlign: 'center', typetable: 'basic' },
        { name: 'DOCUMENTO_CODCOMP', label: 'Comprobante', icon: 'i-heroicons-tag', textAlign: 'center', typetable: 'basic' },
        { name: 'DOCUMENTO_CODPREFIJO', label: 'Prefijo', icon: 'i-heroicons-hashtag', textAlign: 'center', typetable: 'basic' },
        { name: 'DOCUMENTO_NUMERO', label: 'Número', icon: 'i-heroicons-hashtag', textAlign: 'center', typetable: 'basic' },
        { name: 'DOCUMENTO_FECHA', label: 'Fecha', icon: 'i-heroicons-calendar', textAlign: 'center', format: 'date' },
        { name: 'ITEM', label: 'Ítem', icon: 'i-heroicons-hashtag', textAlign: 'center', typetable: 'basic' },
        { name: 'FECVENCE', label: 'Fecha vence', icon: 'i-heroicons-calendar', textAlign: 'center', format: 'date', typetable: 'basic' },
        { name: 'VALOR', label: 'Valor', icon: 'i-heroicons-currency-dollar', textAlign: 'right', format: 'currency', typetable: 'basic' },
        { name: 'INTERES', label: 'Interés', icon: 'i-heroicons-currency-dollar', textAlign: 'right', format: 'currency', typetable: 'basic' },
        { name: 'SALVAL', label: 'Saldo Valor', icon: 'i-heroicons-banknotes', textAlign: 'right', format: 'currency' },
        { name: 'FECULPAGO', label: 'Fecha último pago', icon: 'i-heroicons-calendar', textAlign: 'center', format: 'date', typetable: 'basic' },
        { name: 'VALORINI', label: 'Valor Inicial', icon: 'i-heroicons-currency-dollar', textAlign: 'right', format: 'currency' },
        { name: 'DOCULTPAGO', label: 'Doc. Último pago', icon: 'i-heroicons-document-text', textAlign: 'center', typetable: 'basic' },
        { name: 'VRBASE', label: 'Vr Base', icon: 'i-heroicons-currency-dollar', textAlign: 'right', format: 'currency' },
        { name: 'CONCEPTO_CODIGO', label: 'Código Conc.', icon: 'i-heroicons-hashtag', textAlign: 'center', typetable: 'basic' },
        { name: 'CONCEPTO_DESCRIP', label: 'Descripción Conc.', icon: 'i-heroicons-information-circle', textAlign: 'left', typetable: 'basic' }
      ],
      foreignKeys: [
        {
          table: 'DOCUMENTO',
          localField: 'DOCUID',
          foreignField: 'DOCUID',
          columns: [
            { name: 'TIPOIE', as: 'DOCUMENTO_TIPOIE', label: 'Tipo' },
            { name: 'CODCOMP', as: 'DOCUMENTO_CODCOMP', label: 'Código' },
            { name: 'CODPREFIJO', as: 'DOCUMENTO_CODPREFIJO', label: 'Prefijo' },
            { name: 'NUMERO', as: 'DOCUMENTO_NUMERO', label: 'Número' },
            { name: 'FECHA', as: 'DOCUMENTO_FECHA', label: 'Fecha' }
          ]
        },
        {
          table: 'CONCEPTO',
          localField: 'CONCID',
          foreignField: 'CONCID',
          columns: [
            { name: 'CODIGO', as: 'CONCEPTO_CODIGO', label: 'Código Conc.' },
            { name: 'DESCRIP', as: 'CONCEPTO_DESCRIP', label: 'Descripción Conc.' }
          ]
        }
      ],
      searchFields: ['DOCUMENTO_CODPREFIJO', 'DOCUMENTO_NUMERO', 'CONCEPTO_CODIGO', 'CONCEPTO_DESCRIP']
    },
    recibos: {
      tableTitle: 'Cartera',
      tableName: 'RECIBO',
      primaryKey: 'RECIBOID',
      searchPlaceholder: 'Buscar en cartera...',
      emptyMessage: 'No se encontraron registros',
      apiEndpoint: '/api/tns/records/',
      fields: [
        { name: 'TIPOIE', label: 'Tipo', icon: 'i-heroicons-document-text', textAlign: 'center', typetable: 'basic' },
        { name: 'CODCOMP', label: 'Comprobante', icon: 'i-heroicons-tag', textAlign: 'center', typetable: 'basic' },
        { name: 'CODPREFIJO', label: 'Prefijo', icon: 'i-heroicons-hashtag', textAlign: 'center', typetable: 'basic' },
        { name: 'NUMERO', label: 'Número', icon: 'i-heroicons-hashtag', textAlign: 'center', typetable: 'basic' },
        { name: 'FECHA', label: 'Fecha', icon: 'i-heroicons-calendar', textAlign: 'center', format: 'date' },
        { name: 'CLIENTE_NOMBRE', label: 'Tercero', icon: 'i-heroicons-user-circle', textAlign: 'left', typetable: 'basic' },
        { name: 'CLIENTE_NIT', label: 'NIT Tercero', icon: 'i-heroicons-barcode', textAlign: 'center', typetable: 'basic' },
        { name: 'DETALLE', label: 'Detalle', icon: 'i-heroicons-information-circle', textAlign: 'left', typetable: 'basic' },
        { name: 'TOTAL', label: 'Total', icon: 'i-heroicons-currency-dollar', textAlign: 'right', format: 'currency', typetable: 'basic' },
        { name: 'TOTDESC', label: 'Total Descuento', icon: 'i-heroicons-currency-dollar', textAlign: 'right', format: 'currency' },
        { name: 'NETO', label: 'Neto', icon: 'i-heroicons-banknotes', textAlign: 'right', format: 'currency' },
        { name: 'SUCURSAL_CODIGO', label: 'Cod. Sucursal', icon: 'i-heroicons-hashtag', textAlign: 'center', typetable: 'basic' },
        { name: 'SUCURSAL_DESCRIP', label: 'Sucursal', icon: 'i-heroicons-building-office-2', textAlign: 'left', typetable: 'basic' },
        { name: 'FECASENT', label: 'Asentada', icon: 'i-heroicons-check-circle', textAlign: 'center', format: 'badge', format2: 'date', badgeColor: 'blue', badgeVariant: 'solid', typetable: 'basic' },
        { name: 'PERIODO', label: 'Periodo', icon: 'i-heroicons-calendar-days', textAlign: 'center', typetable: 'basic' },
        { name: 'IMPORTADO', label: 'Importado', icon: 'i-heroicons-globe-alt', textAlign: 'center', typetable: 'basic' },
        { name: 'AREA_CODIGO', label: 'Cod. Área', icon: 'i-heroicons-hashtag', textAlign: 'center', format: 'foreignkey', primaryKey: true, primaryId: 'AREADID', typetable: 'basic' },
        { name: 'AREA_NOMBRE', label: 'Área', icon: 'i-heroicons-building-office-2', textAlign: 'left', format: 'foreignkey', primaryKey: true, primaryId: 'AREADID' },
        { name: 'CENTRO_CODIGO', label: 'Cod. Centro', icon: 'i-heroicons-hashtag', textAlign: 'center', format: 'foreignkey', primaryKey: true, primaryId: 'CENID', typetable: 'basic' },
        { name: 'CENTRO_DESCRIP', label: 'Centro costo', icon: 'i-heroicons-rectangle-group', textAlign: 'left', format: 'foreignkey', primaryKey: true, primaryId: 'CENID' },
        { name: 'TOTALFP', label: 'Total Forma Pago', icon: 'i-heroicons-currency-dollar', textAlign: 'right', format: 'currency', typetable: 'basic' },
        { name: 'COBRADOR_NOMBRE', label: 'Cobrador', icon: 'i-heroicons-user', textAlign: 'left', format: 'foreignkey', primaryKey: true, primaryId: 'COBRADOR', typetable: 'basic' },
        { name: 'COBRADOR_NIT', label: 'NIT Cobrador', icon: 'i-heroicons-barcode', textAlign: 'center', format: 'foreignkey', primaryKey: true, primaryId: 'COBRADOR' },
        { name: 'USUARIO', label: 'Usuario', icon: 'i-heroicons-user-circle', textAlign: 'left', typetable: 'basic' },
        { name: 'HORA', label: 'Hora', icon: 'i-heroicons-clock', textAlign: 'center', typetable: 'basic' },
        { name: 'MOV_CODCOMP', label: 'Comprobante Mov.', icon: 'i-heroicons-tag', textAlign: 'center', typetable: 'basic' },
        { name: 'MOV_CODPREFIJO', label: 'Prefijo Mov.', icon: 'i-heroicons-hashtag', textAlign: 'center', typetable: 'basic' },
        { name: 'MOV_NUMERO', label: 'Número Mov.', icon: 'i-heroicons-hashtag', textAlign: 'center', typetable: 'basic' }
      ],
      foreignKeys: [
        {
          table: 'TERCEROS',
          localField: 'TERID',
          foreignField: 'TERID',
          columns: [
            { name: 'NOMBRE', as: 'CLIENTE_NOMBRE', label: 'Tercero' },
            { name: 'NIT', as: 'CLIENTE_NIT', label: 'NIT' }
          ]
        },
        {
          table: 'SUCURSAL',
          localField: 'SUCID',
          foreignField: 'SUCID',
          columns: [
            { name: 'NOMSUC', as: 'SUCURSAL_DESCRIP', label: 'Sucursal' },
            { name: 'CODSUC', as: 'SUCURSAL_CODIGO', label: 'Código' }
          ]
        },
        {
          table: 'TERCEROS',
          localField: 'COBRADOR',
          foreignField: 'TERID',
          columns: [
            { name: 'NOMBRE', as: 'COBRADOR_NOMBRE', label: 'Cobrador' },
            { name: 'NIT', as: 'COBRADOR_NIT', label: 'NIT' }
          ]
        },
        {
          table: 'AREAD',
          localField: 'AREADID',
          foreignField: 'AREADID',
          columns: [
            { name: 'CODAREAD', as: 'AREA_CODIGO', label: 'Cod. Área' },
            { name: 'NOMAREAD', as: 'AREA_NOMBRE', label: 'Área' }
          ]
        },
        {
          table: 'CENTROS',
          localField: 'CENID',
          foreignField: 'CENID',
          columns: [
            { name: 'DESCRIP', as: 'CENTRO_DESCRIP', label: 'Centro' },
            { name: 'NRO', as: 'CENTRO_CODIGO', label: 'Código' }
          ]
        }
      ],
      searchFields: ['NUMERO', 'CODCOMP', 'CLIENTE_NOMBRE', 'DETALLE', 'USUARIO']
    },
    derecibos: {
      tableTitle: 'Cartera Detallada',
      tableName: 'DERECIBO',
      primaryKey: 'DRECIBOID',
      searchPlaceholder: 'Buscar en cartera detallada...',
      emptyMessage: 'No se encontraron registros',
      apiEndpoint: '/api/tns/records/',
      searchFields: ['NUMERO', 'CODCOMP', 'CLIENTE_NOMBRE', 'DETALLE', 'USUARIO'],
      fields: [
        { name: 'RECIBO_CODCOMP', label: 'Comprobante', icon: 'i-heroicons-tag', textAlign: 'center', typetable: 'basic' },
        { name: 'RECIBO_CODPREFIJO', label: 'Prefijo', icon: 'i-heroicons-hashtag', textAlign: 'center', typetable: 'basic' },
        { name: 'RECIBO_NUMERO', label: 'Número', icon: 'i-heroicons-hashtag', textAlign: 'center', typetable: 'basic' },
        { name: 'RECIBO_TIPOIE', label: 'Tipo Doc.', icon: 'i-heroicons-document-text', textAlign: 'center', typetable: 'basic' }
      ]
    },
    area: {
      tableTitle: 'Áreas',
      tableName: 'AREAD',
      primaryKey: 'AREADID',
      searchPlaceholder: 'Buscar área...',
      emptyMessage: 'No se encontraron áreas',
      apiEndpoint: '/api/tns/records/',
      fields: [
        {
          name: 'CODAREAD',
          label: 'Código',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'NOMAREAD',
          label: 'Nombre',
          icon: 'i-heroicons-document',
          textAlign: 'left',
          typetable: 'basic'
        },
        {
          name: 'CODPREFIJO',
          label: 'Prefijo',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center'
        }
      ],
      searchFields: ['CODAREAD', 'NOMAREAD', 'CODPREFIJO']
    },
    banco: {
      tableTitle: 'Bancos',
      tableName: 'BANCO',
      primaryKey: 'BCOID',
      searchPlaceholder: 'Buscar banco...',
      emptyMessage: 'No se encontraron bancos',
      apiEndpoint: '/api/tns/records/',
      foreignKeys: [
        {
          table: 'PLANCUENTAS',
          localField: 'PUCID',
          foreignField: 'PUCID',
          columns: [
            { name: 'NOMBRE', as: 'PUC_NOMBRE' },
            { name: 'CODIGO', as: 'PUC_CODIGO' }
          ]
        }
      ],
      fields: [
        {
          name: 'CODIGO',
          label: 'Código',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'NOMBRE',
          label: 'Nombre',
          icon: 'i-heroicons-document',
          textAlign: 'left',
          typetable: 'basic'
        },
        {
          name: 'NROCTABCO',
          label: 'Número Cuenta Banco',
          icon: 'i-heroicons-banknotes',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'PUC_NOMBRE',
          label: 'Cuenta PUC',
          icon: 'i-heroicons-document',
          textAlign: 'left',
          primaryKey: true,
          primaryId: 'PUCID',
          format: 'foreignkey'
        },
        {
          name: 'PUC_CODIGO',
          label: 'Código PUC',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic',
          primaryKey: true,
          primaryId: 'PUCID',
          format: 'foreignkey'
        }
      ],
      searchFields: ['CODIGO', 'NOMBRE', 'PUCID']
    },
    materiales:
    {
      tableTitle: 'Materiales',
      tableName: 'MATERIAL',
      primaryKey: 'MATID',
      searchPlaceholder: 'Buscar material...',
      emptyMessage: 'No se encontraron materiales',
      apiEndpoint: '/api/tns/records/',
      fields: [
        // Campos de MATERIAL (tabla principal)
        {
          name: 'CODIGO',
          label: 'Código',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'CODBARRA',
          label: 'Código Barra',
          icon: 'i-heroicons-barcode',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'DESCRIP',
          label: 'Descripción',
          icon: 'i-heroicons-information-circle',
          textAlign: 'left',
          typetable: 'basic'
        },
        {
          name: 'PESO',
          label: 'Peso',
          icon: 'i-heroicons-scale',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        {
          name: 'UNIDAD',
          label: 'Unidad',
          icon: 'i-heroicons-cube',
          textAlign: 'center',
          typetable: 'basic'
        },
        
        // Campos de GRUPMAT
        {
          name: 'GM_CODIGO',
          label: 'Código Grupo',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'GM_DESCRIP',
          label: 'Descripción Grupo',
          icon: 'i-heroicons-folder',
          textAlign: 'left',
          typetable: 'basic'
        },
        
        // Campos de GCMAT
        {
          name: 'GC_CODIGO',
          label: 'Código Clasificación',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'GC_DESCRIP',
          label: 'Descripción Clasificación',
          icon: 'i-heroicons-tag',
          textAlign: 'left',
          typetable: 'basic'
        },
        
        // Campos de MATERIALSUC
        {
          name: 'COSTO',
          label: 'Costo',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO1',
          label: 'Precio 1',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO2',
          label: 'Precio 2',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO3',
          label: 'Precio 3',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO4',
          label: 'Precio 4',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO5',
          label: 'Precio 5',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'DESCUENTO1',
          label: 'Descuento 1',
          icon: 'i-heroicons-percent-badge',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        {
          name: 'DESCUENTO2',
          label: 'Descuento 2',
          icon: 'i-heroicons-percent-badge',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        {
          name: 'DESCUENTO3',
          label: 'Descuento 3',
          icon: 'i-heroicons-percent-badge',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        {
          name: 'DESCUENTO4',
          label: 'Descuento 4',
          icon: 'i-heroicons-percent-badge',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        {
          name: 'DESCUENTO5',
          label: 'Descuento 5',
          icon: 'i-heroicons-percent-badge',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        
        // Campos de SALMATERIAL
        {
          name: 'EXISTENC',
          label: 'Existencia',
          icon: 'i-heroicons-cube',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        
        // Campos de BODEGA (encadenado desde SALMATERIAL)
        {
          name: 'BOD_CODIGO',
          label: 'Código Bodega',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'BOD_NOMBRE',
          label: 'Nombre Bodega',
          icon: 'i-heroicons-building-storefront',
          textAlign: 'left',
          typetable: 'basic'
        },
        
        // Campos de SERIAL
        {
          name: 'NROSERIAL',
          label: 'Nro Serial',
          icon: 'i-heroicons-qr-code',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'FECHA',
          label: 'Fecha',
          icon: 'i-heroicons-calendar',
          textAlign: 'center',
          format: 'date',
          typetable: 'basic'
        },
        {
          name: 'SALDO',
          label: 'Saldo',
          icon: 'i-heroicons-calculator',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        }
      ],
      
      foreignKeys: [
        // JOIN 1: MATERIAL → MATERIALSUC (directo)
        {
          table: 'MATERIALSUC',
          localField: 'MATID',
          foreignField: 'MATID',
          joinType: 'LEFT',
          columns: [
            { name: 'COSTO', as: 'COSTO' },
            { name: 'PRECIO1', as: 'PRECIO1' },
            { name: 'PRECIO2', as: 'PRECIO2' },
            { name: 'PRECIO3', as: 'PRECIO3' },
            { name: 'PRECIO4', as: 'PRECIO4' },
            { name: 'PRECIO5', as: 'PRECIO5' },
            { name: 'DESCUENTO1', as: 'DESCUENTO1' },
            { name: 'DESCUENTO2', as: 'DESCUENTO2' },
            { name: 'DESCUENTO3', as: 'DESCUENTO3' },
            { name: 'DESCUENTO4', as: 'DESCUENTO4' },
            { name: 'DESCUENTO5', as: 'DESCUENTO5' }
          ]
        },
        
        // JOIN 2: MATERIAL → GRUPMAT (directo)
        {
          table: 'GRUPMAT',
          localField: 'GRUPMATID',
          foreignField: 'GRUPMATID',
          joinType: 'LEFT',
          columns: [
            { name: 'CODIGO', as: 'GM_CODIGO' },
            { name: 'DESCRIP', as: 'GM_DESCRIP' }
          ]
        },
        
        // JOIN 3: MATERIAL → GCMAT (directo)
        {
          table: 'GCMAT',
          localField: 'GCMATID',
          foreignField: 'GCMATID',
          joinType: 'LEFT',
          columns: [
            { name: 'CODIGO', as: 'GC_CODIGO' },
            { name: 'DESCRIP', as: 'GC_DESCRIP' }
          ]
        },
        
        // JOIN 4: MATERIAL → SALMATERIAL (directo)
        {
          table: 'SALMATERIAL',
          localField: 'MATID',
          foreignField: 'MATID',
          joinType: 'LEFT',
          columns: [
            { name: 'EXISTENC', as: 'EXISTENC' }
          ]
        },
        
        // JOIN 5: SALMATERIAL → BODEGA (ENCADENADO)
        {
          table: 'BODEGA',
          localField: 'BODID',
          foreignField: 'BODID',
          joinFrom: 'SALMATERIAL',  // ← JOIN encadenado desde SALMATERIAL
          joinType: 'LEFT',
          columns: [
            { name: 'CODIGO', as: 'BOD_CODIGO' },
            { name: 'NOMBRE', as: 'BOD_NOMBRE' }
          ]
        },
        
        // JOIN 6: MATERIAL → SERIAL (directo)
        {
          table: 'SERIAL',
          localField: 'MATID',
          foreignField: 'MATID',
          joinType: 'LEFT',
          columns: [
            { name: 'NROSERIAL', as: 'NROSERIAL' },
            { name: 'FECHA', as: 'FECHA' },
            { name: 'SALDO', as: 'SALDO' }
          ]
        }
      ],
      
      searchFields: [
        'CODIGO', 
        'CODBARRA', 
        'DESCRIP', 
        'GM_CODIGO', 
        'GM_DESCRIP', 
        'GC_CODIGO', 
        'GC_DESCRIP',
        'BOD_CODIGO',
        'BOD_NOMBRE',
        'NROSERIAL'
      ]
    },
    
    // ========== CONFIGURACIONES ESPECÍFICAS PARA AUTOPAGO ==========
    // 
    // Estas configuraciones son optimizadas para diferentes casos de uso
    // sin afectar la configuración original 'materiales' (retrocompatible).
    // 
    // CUÁNDO USAR CADA UNA:
    // 
    // 1. materialprecio:
    //    - ✅ Lista inicial del catálogo de autopago (más rápida)
    //    - ✅ Solo necesitas: código, descripción, precios, categorías
    //    - ✅ NO incluye: stock, bodegas, seriales
    //    - ⚡ MÁS RÁPIDA: Menos JOINs = mejor performance
    //    - 📦 Sin duplicados: Un producto = una fila
    // 
    // 2. materialpreciosaldo:
    //    - ✅ Cuando necesitas filtrar por bodega específica
    //    - ✅ Cuando necesitas stock agregado por bodega
    //    - ✅ Consultas de inventario por ubicación
    //    - ⚠️ Puede generar duplicados (un producto por bodega)
    //    - 💡 Usa filters: { 'BOD_CODIGO': { operator: '=', value: 'BOD001' } }
    // 
    // 3. materialprecioserial:
    //    - ✅ Casos especiales que requieren información de seriales
    //    - ✅ Trazabilidad completa de productos
    //    - ⚠️ MÁS LENTA: Muchos JOINs = más tiempo de consulta
    //    - ⚠️ Puede generar muchos duplicados (un producto por serial)
    //    - 💡 Usar solo cuando realmente necesites seriales
    // 
    // 4. materiales (original):
    //    - ✅ Mantener para retrocompatibilidad
    //    - ✅ Módulos existentes que ya la usan
    //    - ⚠️ NO modificar: puede romper funcionalidad existente
    //
    materialprecio: {
      tableTitle: 'Materiales con Precio',
      tableName: 'MATERIAL',
      primaryKey: 'MATID',
      searchPlaceholder: 'Buscar material...',
      emptyMessage: 'No se encontraron materiales',
      apiEndpoint: '/api/tns/records/',
      fields: [
        // Campos de MATERIAL (tabla principal)
        {
          name: 'CODIGO',
          label: 'Código',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'CODBARRA',
          label: 'Código Barra',
          icon: 'i-heroicons-barcode',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'DESCRIP',
          label: 'Descripción',
          icon: 'i-heroicons-information-circle',
          textAlign: 'left',
          typetable: 'basic'
        },
        {
          name: 'PESO',
          label: 'Peso',
          icon: 'i-heroicons-scale',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        {
          name: 'UNIDAD',
          label: 'Unidad',
          icon: 'i-heroicons-cube',
          textAlign: 'center',
          typetable: 'basic'
        },
        
        // Campos de GRUPMAT (categorías)
        {
          name: 'GM_CODIGO',
          label: 'Código Grupo',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'GM_DESCRIP',
          label: 'Descripción Grupo',
          icon: 'i-heroicons-folder',
          textAlign: 'left',
          typetable: 'basic'
        },
        
        // Campos de GCMAT
        {
          name: 'GC_CODIGO',
          label: 'Código Clasificación',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'GC_DESCRIP',
          label: 'Descripción Clasificación',
          icon: 'i-heroicons-tag',
          textAlign: 'left',
          typetable: 'basic'
        },
        
        // Campos de MATERIALSUC (precios)
        {
          name: 'COSTO',
          label: 'Costo',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO1',
          label: 'Precio 1',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO2',
          label: 'Precio 2',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO3',
          label: 'Precio 3',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO4',
          label: 'Precio 4',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO5',
          label: 'Precio 5',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'DESCUENTO1',
          label: 'Descuento 1',
          icon: 'i-heroicons-percent-badge',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        {
          name: 'DESCUENTO2',
          label: 'Descuento 2',
          icon: 'i-heroicons-percent-badge',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        {
          name: 'DESCUENTO3',
          label: 'Descuento 3',
          icon: 'i-heroicons-percent-badge',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        {
          name: 'DESCUENTO4',
          label: 'Descuento 4',
          icon: 'i-heroicons-percent-badge',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        {
          name: 'DESCUENTO5',
          label: 'Descuento 5',
          icon: 'i-heroicons-percent-badge',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        }
      ],
      
      foreignKeys: [
        // JOIN 1: MATERIAL → MATERIALSUC (precios)
        {
          table: 'MATERIALSUC',
          localField: 'MATID',
          foreignField: 'MATID',
          joinType: 'LEFT',
          columns: [
            { name: 'COSTO', as: 'COSTO' },
            { name: 'PRECIO1', as: 'PRECIO1' },
            { name: 'PRECIO2', as: 'PRECIO2' },
            { name: 'PRECIO3', as: 'PRECIO3' },
            { name: 'PRECIO4', as: 'PRECIO4' },
            { name: 'PRECIO5', as: 'PRECIO5' },
            { name: 'DESCUENTO1', as: 'DESCUENTO1' },
            { name: 'DESCUENTO2', as: 'DESCUENTO2' },
            { name: 'DESCUENTO3', as: 'DESCUENTO3' },
            { name: 'DESCUENTO4', as: 'DESCUENTO4' },
            { name: 'DESCUENTO5', as: 'DESCUENTO5' }
          ]
        },
        
        // JOIN 2: MATERIAL → GRUPMAT (categorías)
        {
          table: 'GRUPMAT',
          localField: 'GRUPMATID',
          foreignField: 'GRUPMATID',
          joinType: 'LEFT',
          columns: [
            { name: 'CODIGO', as: 'GM_CODIGO' },
            { name: 'DESCRIP', as: 'GM_DESCRIP' }
          ]
        },
        
        // JOIN 3: MATERIAL → GCMAT
        {
          table: 'GCMAT',
          localField: 'GCMATID',
          foreignField: 'GCMATID',
          joinType: 'LEFT',
          columns: [
            { name: 'CODIGO', as: 'GC_CODIGO' },
            { name: 'DESCRIP', as: 'GC_DESCRIP' }
          ]
        }
      ],
      
      searchFields: [
        'CODIGO', 
        'CODBARRA', 
        'DESCRIP', 
        'GM_CODIGO', 
        'GM_DESCRIP', 
        'GC_CODIGO', 
        'GC_DESCRIP'
      ]
    },
    
    // materialpreciosaldo: Con stock agregado (para consultas por bodega)
    // 
    // USO RECOMENDADO:
    // - Filtrar productos de una bodega específica
    // - Ver stock disponible por ubicación
    // - Reportes de inventario por bodega
    // 
    // EJEMPLO DE USO:
    // const config = getConfig('materialpreciosaldo')
    // const response = await fetchRecords(config, {
    //   filters: { 'BOD_CODIGO': { operator: '=', value: 'BOD001' } }
    // })
    //
    materialpreciosaldo: {
      tableTitle: 'Materiales con Precio y Stock',
      tableName: 'MATERIAL',
      primaryKey: 'MATID',
      searchPlaceholder: 'Buscar material...',
      emptyMessage: 'No se encontraron materiales',
      apiEndpoint: '/api/tns/records/',
      fields: [
        // Campos de MATERIAL (tabla principal)
        {
          name: 'CODIGO',
          label: 'Código',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'CODBARRA',
          label: 'Código Barra',
          icon: 'i-heroicons-barcode',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'DESCRIP',
          label: 'Descripción',
          icon: 'i-heroicons-information-circle',
          textAlign: 'left',
          typetable: 'basic'
        },
        {
          name: 'PESO',
          label: 'Peso',
          icon: 'i-heroicons-scale',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        {
          name: 'UNIDAD',
          label: 'Unidad',
          icon: 'i-heroicons-cube',
          textAlign: 'center',
          typetable: 'basic'
        },
        
        // Campos de GRUPMAT
        {
          name: 'GM_CODIGO',
          label: 'Código Grupo',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'GM_DESCRIP',
          label: 'Descripción Grupo',
          icon: 'i-heroicons-folder',
          textAlign: 'left',
          typetable: 'basic'
        },
        
        // Campos de GCMAT
        {
          name: 'GC_CODIGO',
          label: 'Código Clasificación',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'GC_DESCRIP',
          label: 'Descripción Clasificación',
          icon: 'i-heroicons-tag',
          textAlign: 'left',
          typetable: 'basic'
        },
        
        // Campos de MATERIALSUC
        {
          name: 'COSTO',
          label: 'Costo',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO1',
          label: 'Precio 1',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO2',
          label: 'Precio 2',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO3',
          label: 'Precio 3',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO4',
          label: 'Precio 4',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO5',
          label: 'Precio 5',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        
        // Campos de SALMATERIAL (stock)
        {
          name: 'EXISTENC',
          label: 'Existencia',
          icon: 'i-heroicons-cube',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        
        // Campos de BODEGA (encadenado desde SALMATERIAL)
        {
          name: 'BOD_CODIGO',
          label: 'Código Bodega',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'BOD_NOMBRE',
          label: 'Nombre Bodega',
          icon: 'i-heroicons-building-storefront',
          textAlign: 'left',
          typetable: 'basic'
        }
      ],
      
      foreignKeys: [
        // JOIN 1: MATERIAL → MATERIALSUC
        {
          table: 'MATERIALSUC',
          localField: 'MATID',
          foreignField: 'MATID',
          joinType: 'LEFT',
          columns: [
            { name: 'COSTO', as: 'COSTO' },
            { name: 'PRECIO1', as: 'PRECIO1' },
            { name: 'PRECIO2', as: 'PRECIO2' },
            { name: 'PRECIO3', as: 'PRECIO3' },
            { name: 'PRECIO4', as: 'PRECIO4' },
            { name: 'PRECIO5', as: 'PRECIO5' }
          ]
        },
        
        // JOIN 2: MATERIAL → GRUPMAT
        {
          table: 'GRUPMAT',
          localField: 'GRUPMATID',
          foreignField: 'GRUPMATID',
          joinType: 'LEFT',
          columns: [
            { name: 'CODIGO', as: 'GM_CODIGO' },
            { name: 'DESCRIP', as: 'GM_DESCRIP' }
          ]
        },
        
        // JOIN 3: MATERIAL → GCMAT
        {
          table: 'GCMAT',
          localField: 'GCMATID',
          foreignField: 'GCMATID',
          joinType: 'LEFT',
          columns: [
            { name: 'CODIGO', as: 'GC_CODIGO' },
            { name: 'DESCRIP', as: 'GC_DESCRIP' }
          ]
        },
        
        // JOIN 4: MATERIAL → SALMATERIAL
        {
          table: 'SALMATERIAL',
          localField: 'MATID',
          foreignField: 'MATID',
          joinType: 'LEFT',
          columns: [
            { name: 'EXISTENC', as: 'EXISTENC' }
          ]
        },
        
        // JOIN 5: SALMATERIAL → BODEGA (ENCADENADO)
        {
          table: 'BODEGA',
          localField: 'BODID',
          foreignField: 'BODID',
          joinFrom: 'SALMATERIAL',
          joinType: 'LEFT',
          columns: [
            { name: 'CODIGO', as: 'BOD_CODIGO' },
            { name: 'NOMBRE', as: 'BOD_NOMBRE' }
          ]
        }
      ],
      
      searchFields: [
        'CODIGO', 
        'CODBARRA', 
        'DESCRIP', 
        'GM_CODIGO', 
        'GM_DESCRIP', 
        'GC_CODIGO', 
        'GC_DESCRIP',
        'BOD_CODIGO',
        'BOD_NOMBRE'
      ]
    },
    
    // materialprecioserial: Con todo (igual a materiales original, para casos especiales)
    // 
    // USO RECOMENDADO:
    // - Solo cuando necesites información de seriales
    // - Trazabilidad completa de productos
    // - Consultas de auditoría o control de calidad
    // 
    // ⚠️ ADVERTENCIA: Esta consulta es la más pesada y puede ser lenta
    // con grandes volúmenes de datos. Usar solo cuando sea necesario.
    //
    materialprecioserial: {
      tableTitle: 'Materiales Completo',
      tableName: 'MATERIAL',
      primaryKey: 'MATID',
      searchPlaceholder: 'Buscar material...',
      emptyMessage: 'No se encontraron materiales',
      apiEndpoint: '/api/tns/records/',
      fields: [
        // Campos de MATERIAL (tabla principal)
        {
          name: 'CODIGO',
          label: 'Código',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'CODBARRA',
          label: 'Código Barra',
          icon: 'i-heroicons-barcode',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'DESCRIP',
          label: 'Descripción',
          icon: 'i-heroicons-information-circle',
          textAlign: 'left',
          typetable: 'basic'
        },
        {
          name: 'PESO',
          label: 'Peso',
          icon: 'i-heroicons-scale',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        {
          name: 'UNIDAD',
          label: 'Unidad',
          icon: 'i-heroicons-cube',
          textAlign: 'center',
          typetable: 'basic'
        },
        
        // Campos de GRUPMAT
        {
          name: 'GM_CODIGO',
          label: 'Código Grupo',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'GM_DESCRIP',
          label: 'Descripción Grupo',
          icon: 'i-heroicons-folder',
          textAlign: 'left',
          typetable: 'basic'
        },
        
        // Campos de GCMAT
        {
          name: 'GC_CODIGO',
          label: 'Código Clasificación',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'GC_DESCRIP',
          label: 'Descripción Clasificación',
          icon: 'i-heroicons-tag',
          textAlign: 'left',
          typetable: 'basic'
        },
        
        // Campos de MATERIALSUC
        {
          name: 'COSTO',
          label: 'Costo',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO1',
          label: 'Precio 1',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO2',
          label: 'Precio 2',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO3',
          label: 'Precio 3',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO4',
          label: 'Precio 4',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        {
          name: 'PRECIO5',
          label: 'Precio 5',
          icon: 'i-heroicons-currency-dollar',
          textAlign: 'right',
          format: 'currency',
          typetable: 'basic'
        },
        
        // Campos de SALMATERIAL
        {
          name: 'EXISTENC',
          label: 'Existencia',
          icon: 'i-heroicons-cube',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        },
        
        // Campos de BODEGA (encadenado desde SALMATERIAL)
        {
          name: 'BOD_CODIGO',
          label: 'Código Bodega',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'BOD_NOMBRE',
          label: 'Nombre Bodega',
          icon: 'i-heroicons-building-storefront',
          textAlign: 'left',
          typetable: 'basic'
        },
        
        // Campos de SERIAL
        {
          name: 'NROSERIAL',
          label: 'Nro Serial',
          icon: 'i-heroicons-qr-code',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'FECHA',
          label: 'Fecha',
          icon: 'i-heroicons-calendar',
          textAlign: 'center',
          format: 'date',
          typetable: 'basic'
        },
        {
          name: 'SALDO',
          label: 'Saldo',
          icon: 'i-heroicons-calculator',
          textAlign: 'right',
          format: 'number',
          typetable: 'basic'
        }
      ],
      
      foreignKeys: [
        // JOIN 1: MATERIAL → MATERIALSUC
        {
          table: 'MATERIALSUC',
          localField: 'MATID',
          foreignField: 'MATID',
          joinType: 'LEFT',
          columns: [
            { name: 'COSTO', as: 'COSTO' },
            { name: 'PRECIO1', as: 'PRECIO1' },
            { name: 'PRECIO2', as: 'PRECIO2' },
            { name: 'PRECIO3', as: 'PRECIO3' },
            { name: 'PRECIO4', as: 'PRECIO4' },
            { name: 'PRECIO5', as: 'PRECIO5' },
            { name: 'DESCUENTO1', as: 'DESCUENTO1' },
            { name: 'DESCUENTO2', as: 'DESCUENTO2' },
            { name: 'DESCUENTO3', as: 'DESCUENTO3' },
            { name: 'DESCUENTO4', as: 'DESCUENTO4' },
            { name: 'DESCUENTO5', as: 'DESCUENTO5' }
          ]
        },
        
        // JOIN 2: MATERIAL → GRUPMAT
        {
          table: 'GRUPMAT',
          localField: 'GRUPMATID',
          foreignField: 'GRUPMATID',
          joinType: 'LEFT',
          columns: [
            { name: 'CODIGO', as: 'GM_CODIGO' },
            { name: 'DESCRIP', as: 'GM_DESCRIP' }
          ]
        },
        
        // JOIN 3: MATERIAL → GCMAT
        {
          table: 'GCMAT',
          localField: 'GCMATID',
          foreignField: 'GCMATID',
          joinType: 'LEFT',
          columns: [
            { name: 'CODIGO', as: 'GC_CODIGO' },
            { name: 'DESCRIP', as: 'GC_DESCRIP' }
          ]
        },
        
        // JOIN 4: MATERIAL → SALMATERIAL
        {
          table: 'SALMATERIAL',
          localField: 'MATID',
          foreignField: 'MATID',
          joinType: 'LEFT',
          columns: [
            { name: 'EXISTENC', as: 'EXISTENC' }
          ]
        },
        
        // JOIN 5: SALMATERIAL → BODEGA (ENCADENADO)
        {
          table: 'BODEGA',
          localField: 'BODID',
          foreignField: 'BODID',
          joinFrom: 'SALMATERIAL',
          joinType: 'LEFT',
          columns: [
            { name: 'CODIGO', as: 'BOD_CODIGO' },
            { name: 'NOMBRE', as: 'BOD_NOMBRE' }
          ]
        },
        
        // JOIN 6: MATERIAL → SERIAL
        {
          table: 'SERIAL',
          localField: 'MATID',
          foreignField: 'MATID',
          joinType: 'LEFT',
          columns: [
            { name: 'NROSERIAL', as: 'NROSERIAL' },
            { name: 'FECHA', as: 'FECHA' },
            { name: 'SALDO', as: 'SALDO' }
          ]
        }
      ],
      
      searchFields: [
        'CODIGO', 
        'CODBARRA', 
        'DESCRIP', 
        'GM_CODIGO', 
        'GM_DESCRIP', 
        'GC_CODIGO', 
        'GC_DESCRIP',
        'BOD_CODIGO',
        'BOD_NOMBRE',
        'NROSERIAL'
      ]
    },
    
    bodega: {
      tableTitle: 'Bodegas',
      tableName: 'BODEGA',
      primaryKey: 'BODID',
      searchPlaceholder: 'Buscar bodega...',
      emptyMessage: 'No se encontraron bodegas',
      apiEndpoint: '/api/tns/records/',
      foreignKeys: [
        {
          table: 'SUCURSAL',
          localField: 'SUCID',
          foreignField: 'SUCID',
          columns: [
            { name: 'NOMSUC', as: 'SUC_NOMBRE' },
            { name: 'CODSUC', as: 'SUC_CODIGO' },
            { name: 'DIRECCION', as: 'SUC_DIRECCION' },
            { name: 'TELEFONO', as: 'SUC_TELEFONO' },
            { name: 'CIUDAD', as: 'SUC_CIUDAD' }
          ]
        }
      ],
      fields: [
        {
          name: 'CODIGO',
          label: 'Código',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'NOMBRE',
          label: 'Nombre',
          icon: 'i-heroicons-document',
          textAlign: 'left',
          typetable: 'basic'
        },
        {
          name: 'PUERTO',
          label: 'Ruta',
          icon: 'i-heroicons-map-pin',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'ACT',
          label: 'Activo',
          icon: 'i-heroicons-check-circle',
          textAlign: 'center',
          format: 'badge',
          format2: 'boolean',
          badgeColor: 'green',
          badgeVariant: 'solid',
          typetable: 'basic'
        },
        {
          name: 'SUC_NOMBRE',
          label: 'Sucursal',
          icon: 'i-heroicons-building-office-2',
          textAlign: 'left',
          primaryKey: true,
          primaryId: 'SUCID',
          format: 'foreignkey'
        },
        {
          name: 'SUC_CODIGO',
          label: 'Código Sucursal',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          primaryKey: true,
          primaryId: 'SUCID',
          format: 'foreignkey'
        },
        {
          name: 'SUC_DIRECCION',
          label: 'Dirección Sucursal',
          icon: 'i-heroicons-map-pin',
          textAlign: 'left',
          primaryKey: true,
          primaryId: 'SUCID',
          format: 'foreignkey'
        },
        {
          name: 'SUC_TELEFONO',
          label: 'Teléfono Sucursal',
          icon: 'i-heroicons-phone',
          textAlign: 'center',
          primaryKey: true,
          primaryId: 'SUCID',
          format: 'foreignkey'
        },
        {
          name: 'SUC_CIUDAD',
          label: 'Ciudad Sucursal',
          icon: 'i-heroicons-map-pin',
          textAlign: 'left',
          primaryKey: true,
          primaryId: 'SUCID',
          format: 'foreignkey'
        }
      ],
      searchFields: ['CODBOD', 'NOMBOD', 'CODPREFIJO', 'CIUDAD']
    },
    centros: {
      tableTitle: 'Centros de Costo',
      tableName: 'CENTROS',
      primaryKey: 'CENID',
      searchPlaceholder: 'Buscar centro de costo...',
      emptyMessage: 'No se encontraron centros de costo',
      apiEndpoint: '/api/tns/records/',
      fields: [
        {
          name: 'NRO',
          label: 'Código',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'DESCRIP',
          label: 'Descripción',
          icon: 'i-heroicons-information-circle',
          textAlign: 'left',
          typetable: 'basic'
        }
      ],
      searchFields: ['NRO', 'DESCRIP']
    },
    clasificacion: {
      tableTitle: 'Clasificación de Terceros',
      tableName: 'CLASIFICA',
      primaryKey: 'CLASIFICAID',
      searchPlaceholder: 'Buscar clasificación...',
      emptyMessage: 'No se encontraron clasificaciones',
      apiEndpoint: '/api/tns/records/',
      fields: [
        {
          name: 'CODIGO',
          label: 'Código',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'NOMBRE',
          label: 'Nombre',
          icon: 'i-heroicons-document',
          textAlign: 'left',
          typetable: 'basic'
        }
      ],
      searchFields: ['CODIGO', 'NOMBRE']
    },
    concepto: {
      tableTitle: 'Conceptos',
      tableName: 'CONCEPTO',
      primaryKey: 'CONCID',
      searchPlaceholder: 'Buscar concepto...',
      emptyMessage: 'No se encontraron conceptos',
      apiEndpoint: '/api/tns/records/',
      foreignKeys: [
        {
          table: 'PLANCUENTAS',
          localField: 'CTAVAL',
          foreignField: 'PUCID',
          columns: [
            { name: 'NOMBRE', as: 'CTAVAL_NOMBRE' },
            { name: 'CODIGO', as: 'CTAVAL_CODIGO' }
          ]
        },
        {
          table: 'PLANCUENTAS',
          localField: 'CTAORDEN',
          foreignField: 'PUCID',
          columns: [
            { name: 'NOMBRE', as: 'CTAORDEN_NOMBRE' },
            { name: 'CODIGO', as: 'CTAORDEN_CODIGO' }
          ]
        },
        {
          table: 'PLANCUENTAS',
          localField: 'CTAAUXNIIF',
          foreignField: 'PUCID',
          columns: [
            { name: 'NOMBRE', as: 'CTAAUXNIIF_NOMBRE' },
            { name: 'CODIGO', as: 'CTAAUXNIIF_CODIGO' }
          ]
        },
        {
          table: 'PLANCUENTAS',
          localField: 'CTAACREE',
          foreignField: 'PUCID',
          columns: [
            { name: 'NOMBRE', as: 'CTAACREE_NOMBRE' },
            { name: 'CODIGO', as: 'CTAACREE_CODIGO' }
          ]
        },
        {
          table: 'PLANCUENTAS',
          localField: 'CTACARTERA',
          foreignField: 'PUCID',
          columns: [
            { name: 'NOMBRE', as: 'CTACARTERA_NOMBRE' },
            { name: 'CODIGO', as: 'CTACARTERA_CODIGO' }
          ]
        },
        {
          table: 'TIPOIVA',
          localField: 'IVA',
          foreignField: 'TIPOIVAID',
          columns: [
            { name: 'PORCIVA', as: 'TIPOIVA_PORCIVA' },
            { name: 'CODIGO', as: 'TIPOIVA_CODIGO' }
          ]
        },
        {
          table: 'TIPOFUENTE',
          localField: 'TIPOFUENTEID',
          foreignField: 'TIPOFUENTEID',
          columns: [
            { name: 'DESCRIPCION', as: 'TIPOFUENTE_DESCRIP' },
            { name: 'CODIGO', as: 'TIPOFUENTE_CODIGO' }
          ]
        },
        {
          table: 'GRUPOCONCEPTO',
          localField: 'GRUPOCONCEPTOID',
          foreignField: 'GRUPOCONCEPTOID',
          columns: [
            { name: 'DESCRIP', as: 'GRUPOCONCEPTO_DESCRIP' },
            { name: 'CODIGO', as: 'GRUPOCONCEPTO_CODIGO' }
          ]
        }
      ],
      fields: [
        {
          name: 'CODIGO',
          label: 'Código',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'TIPOIE',
          label: 'Tipo',
          icon: 'i-heroicons-tag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'DESCRIP',
          label: 'Descripción',
          icon: 'i-heroicons-information-circle',
          textAlign: 'left',
          typetable: 'basic'
        },
        {
          name: 'CTAVAL_NOMBRE',
          label: 'Cuenta Valor',
          icon: 'i-heroicons-document',
          textAlign: 'left',
          format: 'foreignkey'
        },
        {
          name: 'CTAVAL_CODIGO',
          label: 'Código Cuenta Valor',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey'
        },
        {
          name: 'CTAORDEN_NOMBRE',
          label: 'Cuenta Orden',
          icon: 'i-heroicons-document',
          textAlign: 'left',
          format: 'foreignkey'
        },
        {
          name: 'CTAORDEN_CODIGO',
          label: 'Código Cuenta Orden',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey'
        },
        {
          name: 'CTAAUXNIIF_NOMBRE',
          label: 'Cuenta Auxiliar NIIF',
          icon: 'i-heroicons-document',
          textAlign: 'left',
          format: 'foreignkey'
        },
        {
          name: 'CTAAUXNIIF_CODIGO',
          label: 'Código Cuenta Auxiliar NIIF',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey'
        },
        {
          name: 'CTAACREE_NOMBRE',
          label: 'Cuenta Creación Cartera',
          icon: 'i-heroicons-document',
          textAlign: 'left',
          format: 'foreignkey'
        },
        {
          name: 'CTAACREE_CODIGO',
          label: 'Código Cuenta Creación Cartera',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey'
        },
        {
          name: 'CTACARTERA_NOMBRE',
          label: 'Cuenta Cartera Creada por Concepto de Cartera ',
          icon: 'i-heroicons-document',
          textAlign: 'left',
          format: 'foreignkey'
        },
        {
          name: 'CTACARTERA_CODIGO',
          label: 'Código Cuenta Cartera Creada por Concepto de Cartera',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey'
        },
        {
          name: 'TIPOIVA_PORCIVA',
          label: 'Porcentaje IVA',
          icon: 'i-heroicons-percent',
          textAlign: 'center',
          format: 'foreignkey'
        },
        {
          name: 'TIPOIVA_CODIGO',
          label: 'Código IVA',
          icon: 'i-heroicons-percent',
          textAlign: 'center',
          format: 'foreignkey'
        },
        {
          name: 'TIPOFUENTE_DESCRIP',
          label: 'Tipo Fuente',
          icon: 'i-heroicons-tag',
          textAlign: 'center',
          format: 'foreignkey'
        },
        {
          name: 'TIPOFUENTE_CODIGO',
          label: 'Código Tipo Fuente',
          icon: 'i-heroicons-tag',
          textAlign: 'center',
          format: 'foreignkey'
        },
        {
          name: 'GRUPOCONCEPTO_DESCRIP',
          label: 'Grupo Concepto Descripción',
          icon: 'i-heroicons-information-circle',
          textAlign: 'left',
          format: 'foreignkey'
        },
        {
          name: 'GRUPOCONCEPTO_CODIGO',
          label: 'Código Grupo Concepto',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          format: 'foreignkey'
        },
        {
          name: 'CONVACT',
          label: 'Consecutivo Tesoreria',
          icon: 'i-heroicons-tag',
          textAlign: 'center'
        },
        {
          name: 'CONVANT',
          label: 'Consecutivo Anteriores',
          icon: 'i-heroicons-tag',
          textAlign: 'center'
        },
        {
          name: 'CONDIFCOBRO',
          label: 'Consecutivo Dificil Recaudo',
          icon: 'i-heroicons-tag',
          textAlign: 'center'
        },
        {
          name: 'RUBRO',
          label: 'Rubro Presupuestal',
          icon: 'i-heroicons-tag',
          textAlign: 'center'
        }
      ],
      searchFields: ['CODIGO', 'DESCRIP', 'TIPOIE']
    },
    
    // Configuración para GRUPMAT (grupos de materiales)
    grupmat: {
      tableTitle: 'Grupos de Materiales',
      tableName: 'GRUPMAT',
      primaryKey: 'GRUPMATID',
      searchPlaceholder: 'Buscar grupo...',
      emptyMessage: 'No se encontraron grupos',
      apiEndpoint: '/api/tns/records/',
      fields: [
        {
          name: 'GRUPMATID',
          label: 'ID',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic',
          primaryKey: true
        },
        {
          name: 'CODIGO',
          label: 'Código',
          icon: 'i-heroicons-hashtag',
          textAlign: 'center',
          typetable: 'basic'
        },
        {
          name: 'DESCRIP',
          label: 'Descripción',
          icon: 'i-heroicons-information-circle',
          textAlign: 'left',
          typetable: 'basic'
        }
      ],
      foreignKeys: [],
      searchFields: ['CODIGO', 'DESCRIP']
    }
  }

  const getModule = (value: string): Module | undefined => {
    return modules.find(m => m.value === value)
  }

  const getConfig = (tableValue: string): TableConfig | undefined => {
    return configs[tableValue]
  }

  const getModuleTables = (moduleValue: string): Array<{ value: string; label: string }> => {
    const module = getModule(moduleValue)
    return module?.tables || []
  }

  const getModuleFilters = (moduleValue: string): Array<any> => {
    const module = getModule(moduleValue)
    return module?.filters || []
  }

  return {
    modules,
    configs,
    getModule,
    getConfig,
    getModuleTables,
    getModuleFilters
  }
}
