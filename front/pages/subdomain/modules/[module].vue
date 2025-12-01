<template>
  <div class="modules-page">
    <!-- Header del módulo -->
    <header class="module-header">
      <div class="header-content">
        <div class="header-left">
          <button @click="goBack" class="btn-back">
            <span>←</span> Volver
          </button>
          <div class="module-info">
            <h1>{{ currentModule?.label || 'Módulo' }}</h1>
            <p v-if="selectedTable">{{ selectedTableLabel }}</p>
          </div>
        </div>
        <div class="header-actions">
          <button @click="toggleModuleSelect" class="btn-modules">
            <span>📦</span> Módulos
          </button>
        </div>
      </div>
    </header>

    <!-- Selector de módulos flotante -->
    <Transition name="slide">
      <div v-if="showModuleSelect" class="module-selector-overlay" @click.self="showModuleSelect = false">
        <div class="module-selector">
          <h3>Seleccionar Módulo</h3>
          <div class="modules-grid">
            <button
              v-for="module in modules"
              :key="module.value"
              class="module-card"
              :class="{ active: currentModuleValue === module.value }"
              @click="selectModule(module.value)"
            >
              <span class="module-icon">{{ getModuleIcon(module.value) }}</span>
              <span class="module-name">{{ module.label }}</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Selector de tabla -->
    <div v-if="currentModule && currentModuleTables.length > 0" class="table-selector">
      <select v-model="selectedTable" @change="handleTableChange" class="table-select">
        <option v-for="table in currentModuleTables" :key="table.value" :value="table.value">
          {{ table.label }}
        </option>
      </select>
    </div>

    <!-- Filtros rápidos -->
    <div v-if="currentFilters.length > 0" class="filters-bar">
      <span class="filters-label">Filtros:</span>
      <button
        v-for="filter in currentFilters"
        :key="`${filter.field}-${filter.value}`"
        class="filter-btn"
        :class="{ active: isQuickFilterActive(filter) }"
        @click="toggleQuickFilter(filter)"
      >
        {{ filter.label }}
      </button>
      <button v-if="activeQuickFilters.length > 0" class="filter-btn clear" @click="clearAllQuickFilters">
        ✕ Limpiar todos
      </button>
    </div>

    <!-- Barra de búsqueda -->
    <div class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        :placeholder="config?.searchPlaceholder || 'Buscar...'"
        class="search-input"
        @input="handleSearch"
      />
      <button v-if="searchQuery" @click="clearSearch" class="btn-clear-search">✕</button>
    </div>

    <!-- Contenido principal -->
    <div class="table-container">
      <!-- Loading -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Cargando registros...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
        <button @click="loadData" class="btn-retry">Reintentar</button>
      </div>

      <!-- Tabla -->
      <div v-else-if="items.length > 0" class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th
                v-for="field in visibleFields"
                :key="field.name"
                :class="[field.textAlign || 'left']"
                :style="{ width: field.width || 'auto' }"
              >
                <div class="th-content">
                  <div class="th-label">
                    <span v-if="field.icon" class="field-icon">{{ getFieldIcon(field.icon) }}</span>
                    <span>{{ field.label }}</span>
                  </div>
                  
                  <!-- Contenedor para herramientas (filtros y ordenamiento) -->
                  <div class="th-tools">
                    <!-- Filtro activo -->
                    <div v-if="activeFilters[field.name]" class="filter-badge" @click.stop="openFilterModal(field)">
                      <span class="filter-icon">🔽</span>
                      <span v-if="activeFilters[field.name]?.value" class="filter-value">
                        {{ formatFilterValue(field, activeFilters[field.name]?.value) }}
                      </span>
                      <span class="filter-close" @click.stop="clearColumnFilter(field.name)">✕</span>
                    </div>
                    
                    <!-- Icono para abrir filtro (cuando no hay filtro activo) -->
                    <button
                      v-else
                      class="filter-btn-icon"
                      @click.stop="openFilterModal(field)"
                      title="Filtrar"
                    >
                      🔽
                    </button>

                    <!-- Contenedor para ordenamiento -->
                    <div class="sort-container">
                      <button
                        @click.stop="openSortMenu(field.name)"
                        class="sort-btn"
                        :class="{ active: getSortDirection(field.name) }"
                        title="Ordenar"
                      >
                        <span v-if="getSortDirection(field.name) === 'asc'" class="sort-icon">↑</span>
                        <span v-else-if="getSortDirection(field.name) === 'desc'" class="sort-icon">↓</span>
                        <span v-else class="sort-icon">⇅</span>
                        <span v-if="getSortIndex(field.name) !== -1" class="sort-number">
                          {{ getSortIndex(field.name) + 1 }}
                        </span>
                      </button>

                      <!-- Menú flotante para selección de ordenamiento -->
                      <div
                        v-if="sortMenu.field === field.name && isSortMenuOpen"
                        class="sort-menu"
                        @click.stop
                      >
                        <div class="sort-menu-header">
                          Ordenar por "{{ field.label }}"
                        </div>
                        <button
                          @click.stop="applySort(field.name, 'asc')"
                          class="sort-menu-item"
                          :class="{ active: getSortDirection(field.name) === 'asc' }"
                        >
                          <span>↑</span> Ascendente (A-Z)
                          <span v-if="getSortDirection(field.name) === 'asc'" class="check">✓</span>
                        </button>
                        <button
                          @click.stop="applySort(field.name, 'desc')"
                          class="sort-menu-item"
                          :class="{ active: getSortDirection(field.name) === 'desc' }"
                        >
                          <span>↓</span> Descendente (Z-A)
                          <span v-if="getSortDirection(field.name) === 'desc'" class="check">✓</span>
                        </button>
                        <button
                          v-if="getSortDirection(field.name)"
                          @click.stop="removeSort(field.name)"
                          class="sort-menu-item remove"
                        >
                          <span>✕</span> Eliminar orden
                        </button>
                        <div v-if="sortBy.length > 0" class="sort-menu-footer">
                          <div class="sort-order-title">Orden actual:</div>
                          <div
                            v-for="(sort, index) in sortBy"
                            :key="index"
                            class="sort-order-item"
                          >
                            {{ index + 1 }}. {{ sort.field }} ({{ sort.direction === 'asc' ? 'Asc' : 'Desc' }})
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in items"
              :key="item[config?.primaryKey || 'id']"
              :class="{ selected: selectedRowId === item[config?.primaryKey || 'id'] }"
              @click="selectRow(item)"
            >
              <td
                v-for="field in visibleFields"
                :key="field.name"
                :class="[field.textAlign || 'left']"
              >
                <FieldRenderer :field="field" :value="item[field.name]" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Empty state -->
      <div v-else class="empty-state">
        <p>{{ config?.emptyMessage || 'No se encontraron resultados' }}</p>
      </div>
    </div>

    <!-- Controles de tabla y paginación -->
    <div v-if="!loading && items.length > 0" class="table-controls">
      <div class="controls-left">
        <!-- Toggle Básico/Completo -->
        <button
          @click="basicMode = !basicMode"
          class="btn-basic-complete"
          :class="{ 'basic': basicMode, 'complete': !basicMode }"
        >
          <span class="btn-icon">{{ basicMode ? '📋' : '📊' }}</span>
          <span class="btn-text">{{ basicMode ? 'Básico' : 'Completo' }}</span>
        </button>
        
        <!-- Botón para abrir modal de tablas auxiliares -->
        <button
          v-if="currentModule?.tablesconfig && currentModule.tablesconfig.length > 0"
          @click="openAuxiliaryTable"
          class="btn-auxiliary-tables"
        >
          <span>📋</span> Auxiliares
        </button>
      </div>
      
      <div class="pagination-left">
        <span class="pagination-info">
          Mostrando {{ showingStart }} - {{ showingEnd }} de {{ totalCount }}
        </span>
      </div>
      <div class="pagination-right">
        <button
          @click="goToFirstPage"
          :disabled="currentPage === 1"
          class="btn-pagination"
          title="Primera página"
        >
          ⏮
        </button>
        <button
          @click="previousPage"
          :disabled="currentPage === 1"
          class="btn-pagination"
        >
          ← Anterior
        </button>
        <div class="page-numbers">
          <button
            v-for="page in visiblePages"
            :key="page"
            @click="goToPage(page)"
            class="page-number"
            :class="{ active: currentPage === page }"
          >
            {{ page }}
          </button>
        </div>
        <button
          @click="nextPage"
          :disabled="currentPage >= totalPages"
          class="btn-pagination"
        >
          Siguiente →
        </button>
        <button
          @click="goToLastPage"
          :disabled="currentPage >= totalPages"
          class="btn-pagination"
          title="Última página"
        >
          ⏭
        </button>
      </div>
    </div>

    <!-- Modal de selección de tabla auxiliar -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showAuxiliarySelector" class="filter-modal-overlay auxiliary-selector-overlay" @click.self="showAuxiliarySelector = false">
          <div class="filter-modal-content auxiliary-selector-content">
            <div class="filter-modal-header">
              <h3>Tablas Auxiliares</h3>
              <button @click="showAuxiliarySelector = false" class="close-btn">×</button>
            </div>
            <div class="modal-body">
              <div class="auxiliary-tables-grid">
                <button
                  v-for="table in currentModule?.tablesconfig || []"
                  :key="table.value"
                  class="auxiliary-table-btn"
                  :class="{ active: selectedAuxiliaryTable === table.value }"
                  @click="openAuxiliaryTableModal(table.value)"
                >
                  {{ table.label }}
                </button>
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn-cancel" @click="showAuxiliarySelector = false">Cerrar</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Modal de tabla auxiliar con datos -->
    <AuxiliaryTableModal
      :is-open="showAuxiliaryTableModal"
      :table-value="selectedAuxiliaryTable"
      @close="closeAuxiliaryTableModal"
    />

    <!-- Modal de filtros -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="isFilterModalOpen" class="filter-modal-overlay" @click.self="closeFilterModal">
          <div class="filter-modal-content">
            <div class="filter-modal-header">
              <h3>Filtro para {{ currentFilterField?.label }}</h3>
              <button @click="closeFilterModal" class="close-btn">×</button>
            </div>

            <div class="filter-modal-body">
              <!-- Filtro para currency/number -->
              <div v-if="isCurrencyField(currentFilterField) || isNumberField(currentFilterField)" class="filter-section">
                <div class="filter-operators">
                  <button
                    v-for="op in numericOperators"
                    :key="op.value"
                    class="operator-btn"
                    :class="{ active: numericFilter.operator === op.value }"
                    @click="numericFilter.operator = op.value"
                  >
                    {{ op.label }}
                  </button>
                </div>
                <input
                  v-model.number="numericFilter.value"
                  type="number"
                  :placeholder="`Valor ${currentFilterField?.label}`"
                  class="filter-input"
                />
              </div>

              <!-- Filtro para fechas -->
              <div v-else-if="isDateField(currentFilterField)" class="filter-section">
                <label class="filter-label">Rango de fechas</label>
                <div class="date-range">
                  <input
                    v-model="dateRange.start"
                    type="date"
                    placeholder="Desde"
                    class="filter-input"
                  />
                  <span class="date-separator">a</span>
                  <input
                    v-model="dateRange.end"
                    type="date"
                    placeholder="Hasta"
                    class="filter-input"
                  />
                </div>
              </div>

              <!-- Filtro para texto -->
              <div v-else-if="isTextField(currentFilterField)" class="filter-section">
                <input
                  v-model="textFilter"
                  type="text"
                  :placeholder="`Buscar ${currentFilterField?.label}`"
                  class="filter-input"
                />
                <div class="text-filter-options">
                  <label>
                    <input
                      v-model="textFilterType"
                      type="radio"
                      value="contains"
                    />
                    Contiene
                  </label>
                  <label>
                    <input
                      v-model="textFilterType"
                      type="radio"
                      value="exact"
                    />
                    Exacto
                  </label>
                  <label>
                    <input
                      v-model="textFilterType"
                      type="radio"
                      value="startsWith"
                    />
                    Comienza con
                  </label>
                </div>
              </div>

              <!-- Filtro para booleanos -->
              <div v-else-if="isBooleanField(currentFilterField)" class="filter-section">
                <div class="boolean-filter-options">
                  <label>
                    <input
                      v-model="booleanFilter"
                      type="radio"
                      :value="true"
                    />
                    Sí
                  </label>
                  <label>
                    <input
                      v-model="booleanFilter"
                      type="radio"
                      :value="false"
                    />
                    No
                  </label>
                </div>
              </div>
            </div>

            <div class="filter-modal-footer">
              <button @click="clearCurrentFilter" class="btn-cancel">Limpiar</button>
              <button @click="applyCurrentFilter" class="btn-apply">Aplicar</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { useModuleConfig, type TableConfig, type Module } from '@/composables/useModuleConfig'
import { useTNSRecords, type TNSRecordsFilters, type TNSRecordsOrder } from '@/composables/useTNSRecords'
import FieldRenderer from '@/components/common/FieldRenderer.vue'
import AuxiliaryTableModal from '@/components/common/AuxiliaryTableModal.vue'


definePageMeta({
  layout: false,
  middleware: 'auth'
})

const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const { modules, getModule, getConfig, getModuleTables, getModuleFilters } = useModuleConfig()
const { fetchRecords, searchRecords } = useTNSRecords()

// Estado
const currentModuleValue = ref<string>(route.params.module as string || 'facturacion')
const selectedTable = ref<string>('')
const showModuleSelect = ref(false)
const showAuxiliarySelector = ref(false) // Selector de tablas auxiliares
const showAuxiliaryTableModal = ref(false) // Modal con datos de tabla auxiliar
const selectedAuxiliaryTable = ref<string>('') // Tabla auxiliar seleccionada
const searchQuery = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const items = ref<any[]>([])
const selectedRowId = ref<any>(null)
const activeQuickFilters = ref<any[]>([]) // Múltiples filtros rápidos activos
const currentPage = ref(1)
const pageSize = ref(10) // Como BCE
const totalCount = ref(0)
const totalPages = ref(0)
const basicMode = ref(true) // Toggle básico/completo

// Estado para filtros y ordenamiento
const activeFilters = ref<Record<string, { value: any; type: string }>>({})
const sortBy = ref<Array<{ field: string; direction: 'asc' | 'desc' }>>([])
const isFilterModalOpen = ref(false)
const currentFilterField = ref<any>(null)
const isSortMenuOpen = ref(false)
const sortMenu = ref<{ field: string | null }>({ field: null })

// Estado para filtros en modal
const dateRange = ref({ start: '', end: '' })
const textFilter = ref('')
const textFilterType = ref('contains')
const booleanFilter = ref<boolean | null>(null)
const numericFilter = ref({ operator: '=', value: null as number | null })

const numericOperators = [
  { value: '=', label: '=' },
  { value: '<', label: '<' },
  { value: '<=', label: '<=' },
  { value: '>', label: '>' },
  { value: '>=', label: '>=' }
]

// Computed
const currentModule = computed<Module | undefined>(() => getModule(currentModuleValue.value))
const currentModuleTables = computed(() => getModuleTables(currentModuleValue.value))
const currentFilters = computed(() => getModuleFilters(currentModuleValue.value))
const config = computed<TableConfig | undefined>(() => {
  if (!selectedTable.value) return undefined
  return getConfig(selectedTable.value)
})
// Campos visibles filtrados por modo básico/completo (como BCE)
// El toggle alterna entre básico (solo typetable: 'basic') y completo (todos los campos)
const visibleFields = computed(() => {
  if (!config.value) return []
  return config.value.fields.filter(f => {
    // Ocultar campos marcados como hidden
    if (f.hidden) return false
    // Si basicMode es true (modo básico), mostrar solo campos con typetable === 'basic'
    // Si basicMode es false (modo completo), mostrar todos los campos (sin filtrar por typetable)
    if (basicMode.value) {
      // Modo básico: solo campos marcados con typetable: 'basic'
      return f.typetable === 'basic'
    } else {
      // Modo completo: todos los campos (excepto hidden)
      return true
    }
  })
})
const selectedTableLabel = computed(() => {
  // Si hay una tabla auxiliar seleccionada, no mostrar label (se muestra en modal)
  if (showAuxiliaryTableModal.value) return ''
  const table = currentModuleTables.value.find(t => t.value === selectedTable.value)
  return table?.label || ''
})

const showingStart = computed(() => (currentPage.value - 1) * pageSize.value + 1)
const showingEnd = computed(() => Math.min(currentPage.value * pageSize.value, totalCount.value))

// Watch para recargar datos cuando cambia el modo básico/completo
watch(basicMode, () => {
  // No recargar datos, solo actualizar campos visibles (ya es un computed)
  // Los datos ya están cargados, solo cambiamos qué campos mostrar
})

const visiblePages = computed(() => {
  const pages: number[] = []
  const maxVisible = 5
  let start = Math.max(1, currentPage.value - Math.floor(maxVisible / 2))
  let end = Math.min(totalPages.value, start + maxVisible - 1)
  
  if (end - start < maxVisible - 1) {
    start = Math.max(1, end - maxVisible + 1)
  }
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  return pages
})

// Inicialización
onMounted(() => {
  if (!session.selectedEmpresa.value?.empresaServidorId) {
    router.push('/subdomain')
    return
  }
  initializeModule()
})

watch(() => route.params.module, (newModule) => {
  if (newModule) {
    currentModuleValue.value = newModule as string
    initializeModule()
  }
})

// Cerrar menús al hacer click fuera
onMounted(() => {
  document.addEventListener('click', () => {
    isSortMenuOpen.value = false
  })
})

const initializeModule = () => {
  const module = getModule(currentModuleValue.value)
  if (module && module.tables && module.tables.length > 0 && module.tables[0]) {
    selectedTable.value = module.tables[0].value
    
    // Inicializar filtros rápidos con los filtros por defecto del módulo (como BCE)
    activeQuickFilters.value = []
    if (module.filters && module.filters.length > 0) {
      const config = getConfig(selectedTable.value)
      const currentTable = config?.tableName || ''
      
      // Agregar todos los filtros por defecto que apliquen a la tabla actual o a foreign keys
      module.filters.forEach(defaultFilter => {
        const tableMatches = defaultFilter.table.localeCompare(currentTable, undefined, { sensitivity: 'base' }) === 0
        const isForeignKey = config?.foreignKeys?.some(fk =>
          fk.table.localeCompare(defaultFilter.table, undefined, { sensitivity: 'base' }) === 0
        )
        
        // Aplicar si es la tabla principal o si es una foreign key
        if (tableMatches || isForeignKey) {
          // Verificar que el campo exista (directo o como alias de FK)
          const fieldExists = tableMatches 
            ? config?.fields?.some(f =>
                f.name.localeCompare(defaultFilter.field, undefined, { sensitivity: 'base' }) === 0
              )
            : config?.foreignKeys?.some(fk =>
                fk.table.localeCompare(defaultFilter.table, undefined, { sensitivity: 'base' }) === 0 &&
                fk.columns?.some(col =>
                  col.name.localeCompare(defaultFilter.field, undefined, { sensitivity: 'base' }) === 0 ||
                  col.as.localeCompare(defaultFilter.field, undefined, { sensitivity: 'base' }) === 0
                )
              )
          
          if (fieldExists) {
            activeQuickFilters.value.push({
              ...defaultFilter,
              table: defaultFilter.table,
              field: defaultFilter.field,
              value: defaultFilter.value,
              label: defaultFilter.label
            })
          }
        }
      })
    }
    
    activeFilters.value = {}
    sortBy.value = []
    loadData()
  }
}

// Navegación
const goBack = () => {
  router.push('/subdomain')
}

const toggleModuleSelect = () => {
  showModuleSelect.value = !showModuleSelect.value
}

const selectModule = (moduleValue: string) => {
  currentModuleValue.value = moduleValue
  router.push(`/subdomain/modules/${moduleValue}`)
  showModuleSelect.value = false
  initializeModule()
}

const handleTableChange = () => {
  currentPage.value = 1
  
  // Reinicializar filtros rápidos con los filtros por defecto del módulo para la nueva tabla
  const module = getModule(currentModuleValue.value)
  activeQuickFilters.value = []
  
  if (module?.filters && module.filters.length > 0 && config.value) {
    const currentTable = config.value.tableName || ''
    
    // Agregar todos los filtros por defecto que apliquen a la tabla actual o a foreign keys
    module.filters.forEach(defaultFilter => {
      const tableMatches = defaultFilter.table.localeCompare(currentTable, undefined, { sensitivity: 'base' }) === 0
      const isForeignKey = config.value?.foreignKeys?.some(fk =>
        fk.table.localeCompare(defaultFilter.table, undefined, { sensitivity: 'base' }) === 0
      )
      
      // Aplicar si es la tabla principal o si es una foreign key
      if (tableMatches || isForeignKey) {
        // Verificar que el campo exista (directo o como alias de FK)
        const fieldExists = tableMatches 
          ? config.value?.fields?.some(f =>
              f.name.localeCompare(defaultFilter.field, undefined, { sensitivity: 'base' }) === 0
            )
          : config.value?.foreignKeys?.some(fk =>
              fk.table.localeCompare(defaultFilter.table, undefined, { sensitivity: 'base' }) === 0 &&
              fk.columns?.some(col =>
                col.name.localeCompare(defaultFilter.field, undefined, { sensitivity: 'base' }) === 0 ||
                col.as.localeCompare(defaultFilter.field, undefined, { sensitivity: 'base' }) === 0
              )
            )
        
        if (fieldExists) {
          activeQuickFilters.value.push({
            ...defaultFilter,
            table: defaultFilter.table,
            field: defaultFilter.field,
            value: defaultFilter.value,
            label: defaultFilter.label
          })
        }
      }
    })
  }
  
  activeFilters.value = {}
  sortBy.value = []
  searchQuery.value = ''
  basicMode.value = true
  loadData()
}

const openAuxiliaryTable = () => {
  showAuxiliarySelector.value = true
}

const openAuxiliaryTableModal = (tableValue: string) => {
  selectedAuxiliaryTable.value = tableValue
  showAuxiliarySelector.value = false
  showAuxiliaryTableModal.value = true
}

const closeAuxiliaryTableModal = () => {
  showAuxiliaryTableModal.value = false
  selectedAuxiliaryTable.value = ''
}


// Funciones de filtros
const isCurrencyField = (field: any) => {
  return field?.format === 'currency' || field?.format2 === 'currency'
}

const isNumberField = (field: any) => {
  return field?.format === 'number'
}

const isDateField = (field: any) => {
  return field?.format === 'date' || field?.format2 === 'date'
}

const isTextField = (field: any) => {
  return field && !isDateField(field) && !isBooleanField(field) && !isCurrencyField(field) && !isNumberField(field)
}

const isBooleanField = (field: any) => {
  return field && ['IMPRESA', 'ASENTADA'].includes(field?.name)
}

const openFilterModal = (field: any) => {
  currentFilterField.value = field
  isFilterModalOpen.value = true
  
  // Cargar valores existentes si hay filtro activo
  if (activeFilters.value[field.name]) {
    const filter = activeFilters.value[field.name]
    if (!filter) return
    
    if (filter.type === 'dateRange') {
      dateRange.value = filter.value
    } else if (filter.type === 'contains' || filter.type === 'startsWith' || filter.type === 'exact') {
      textFilter.value = typeof filter.value === 'string' ? filter.value : (filter.value as any)?.contains || (filter.value as any)?.startsWith || ''
      textFilterType.value = filter.type
    } else if (filter.type === 'boolean') {
      booleanFilter.value = filter.value
    } else if (filter.type === 'numeric') {
      numericFilter.value = filter.value
    }
  } else {
    // Resetear valores
    dateRange.value = { start: '', end: '' }
    textFilter.value = ''
    textFilterType.value = 'contains'
    booleanFilter.value = null
    numericFilter.value = { operator: '=', value: null }
  }
}

const closeFilterModal = () => {
  isFilterModalOpen.value = false
  currentFilterField.value = null
}

const applyCurrentFilter = () => {
  if (!currentFilterField.value) return

  const field = currentFilterField.value
  let filterValue: any = null
  let filterType = 'exact'

  if (isCurrencyField(field) || isNumberField(field)) {
    if (numericFilter.value.value !== null) {
      filterValue = {
        operator: numericFilter.value.operator,
        value: numericFilter.value.value
      }
      filterType = 'numeric'
    }
  } else if (isDateField(field)) {
    if (dateRange.value.start || dateRange.value.end) {
      filterValue = { ...dateRange.value }
      filterType = 'dateRange'
    }
  } else if (isBooleanField(field)) {
    if (booleanFilter.value !== null) {
      filterValue = booleanFilter.value
      filterType = 'boolean'
    }
  } else if (textFilter.value.trim()) {
    if (textFilterType.value === 'contains') {
      filterValue = { contains: textFilter.value.trim() }
      filterType = 'contains'
    } else if (textFilterType.value === 'startsWith') {
      filterValue = { startsWith: textFilter.value.trim() }
      filterType = 'startsWith'
    } else {
      filterValue = textFilter.value.trim()
      filterType = 'exact'
    }
  }

  if (filterValue !== null) {
    activeFilters.value[field.name] = { value: filterValue, type: filterType }
  } else {
    delete activeFilters.value[field.name]
  }

  closeFilterModal()
  currentPage.value = 1
  loadData()
}

const clearCurrentFilter = () => {
  if (currentFilterField.value?.name) {
    delete activeFilters.value[currentFilterField.value.name]
  }
  closeFilterModal()
  currentPage.value = 1
  loadData()
}

const clearColumnFilter = (fieldName: string) => {
  delete activeFilters.value[fieldName]
  currentPage.value = 1
  loadData()
}

const formatFilterValue = (field: any, value: any): string => {
  if (typeof value === 'object') {
    if (value.contains) return `Contiene: ${value.contains}`
    if (value.startsWith) return `Empieza: ${value.startsWith}`
    if (value.start && value.end) return `${value.start} - ${value.end}`
    if (value.operator && value.value !== null) return `${value.operator} ${value.value}`
  }
  if (typeof value === 'boolean') return value ? 'Sí' : 'No'
  return String(value)
}

// Funciones de ordenamiento
const openSortMenu = (fieldName: string) => {
  if (sortMenu.value.field === fieldName && isSortMenuOpen.value) {
    isSortMenuOpen.value = false
    sortMenu.value.field = null
  } else {
    sortMenu.value.field = fieldName
    isSortMenuOpen.value = true
  }
}

const applySort = (field: string, direction: 'asc' | 'desc') => {
  const existingIndex = sortBy.value.findIndex(s => s.field === field)
  
  if (existingIndex !== -1 && sortBy.value[existingIndex]) {
    sortBy.value[existingIndex].direction = direction
  } else {
    sortBy.value.push({ field, direction })
  }
  
  isSortMenuOpen.value = false
  currentPage.value = 1
  loadData()
}

const removeSort = (field: string) => {
  const index = sortBy.value.findIndex(s => s.field === field)
  if (index !== -1) {
    sortBy.value.splice(index, 1)
  }
  isSortMenuOpen.value = false
  currentPage.value = 1
  loadData()
}

const getSortDirection = (fieldName: string): 'asc' | 'desc' | null => {
  const sort = sortBy.value.find(s => s.field === fieldName)
  return sort?.direction || null
}

const getSortIndex = (fieldName: string): number => {
  return sortBy.value.findIndex(s => s.field === fieldName)
}

// Carga de datos
const loadData = async () => {
  if (!config.value) return

  if (!session.selectedEmpresa.value?.empresaServidorId) {
    error.value = 'No hay empresa seleccionada. Por favor selecciona una empresa primero.'
    return
  }

  loading.value = true
  error.value = null

  try {
    if (!config.value) {
      error.value = 'Configuración no encontrada'
      loading.value = false
      return
    }

    // Construir filtros
    const filters: TNSRecordsFilters = {}
    
    // 1. Agrupar filtros rápidos activos por campo (como BCE)
    const groupedQuickFilters: Record<string, any[]> = {}
    
    for (const quickFilter of activeQuickFilters.value) {
      if (quickFilter.field && quickFilter.value !== undefined && quickFilter.value !== null) {
        // Verificar que NO haya un filtro activo del usuario para este campo
        const hasUserFilter = Object.keys(activeFilters.value).some(activeField =>
          activeField.localeCompare(quickFilter.field, undefined, { sensitivity: 'base' }) === 0
        )
        
        // Solo agregar si no hay filtro del usuario
        if (!hasUserFilter) {
          // Si el filtro es para una tabla que es foreign key (no la tabla principal)
          // usar formato TABLA_CAMPO para que el backend lo detecte
          let filterField = quickFilter.field
          if (quickFilter.table && config.value) {
            const currentTable = config.value.tableName || ''
            if (quickFilter.table.localeCompare(currentTable, undefined, { sensitivity: 'base' }) !== 0) {
              // Verificar si la tabla del filtro es una foreign key
              const isForeignKey = config.value?.foreignKeys?.some(fk =>
                fk.table.localeCompare(quickFilter.table, undefined, { sensitivity: 'base' }) === 0
              )
              
              if (isForeignKey) {
                // Formato: TABLA_CAMPO (ej: KARDEX_CODCOMP)
                filterField = `${quickFilter.table}_${quickFilter.field}`
              }
            }
          }
          
          if (!groupedQuickFilters[filterField]) {
            groupedQuickFilters[filterField] = []
          }
          const fieldArray = groupedQuickFilters[filterField]
          if (fieldArray) {
            fieldArray.push(quickFilter.value)
          }
        }
      }
    }
    
    // Aplicar filtros agrupados (como BCE: un valor directo, múltiples valores con "in")
    for (const [field, values] of Object.entries(groupedQuickFilters)) {
      if (values.length === 1) {
        filters[field] = values[0] // Un solo valor
      } else {
        filters[field] = { in: values } // Múltiples valores como array con "in"
      }
    }
    
    // 2. Agregar filtros de columnas (del usuario) - estos tienen prioridad
    for (const [fieldName, filter] of Object.entries(activeFilters.value)) {
      // Los filtros del usuario tienen prioridad, sobrescriben filtros rápidos
      // No verificar si existe, siempre aplicar filtros del usuario
      
      if (filter.type === 'dateRange') {
        if (filter.value.start || filter.value.end) {
          filters[fieldName] = {
            operator: '>=',
            value: filter.value.start || '1900-01-01'
          }
          if (filter.value.end) {
            filters[`${fieldName}_end`] = {
              operator: '<=',
              value: filter.value.end
            }
          }
        }
      } else if (filter.type === 'contains') {
        filters[fieldName] = { contains: filter.value.contains || filter.value }
      } else if (filter.type === 'startsWith') {
        filters[fieldName] = { startsWith: filter.value.startsWith || filter.value }
      } else if (filter.type === 'numeric' || filter.type === 'currency') {
        const numericValue = filter.value?.value ?? filter.value
        filters[fieldName] = {
          operator: filter.value?.operator || '=',
          value: numericValue
        }
      } else if (filter.type === 'boolean') {
        filters[fieldName] = filter.value
      } else if (filter.type === 'exact') {
        filters[fieldName] = filter.value
      } else {
        filters[fieldName] = filter.value
      }
    }

    // 3. Agregar búsqueda global si existe
    if (searchQuery.value.trim()) {
      const searchFields = config.value.searchFields || []
      if (searchFields.length > 0) {
        filters.OR = searchFields.map(field => ({
          [field]: { contains: searchQuery.value.trim() }
        }))
      }
    }

    // Construir ordenamiento
    const orderBy: TNSRecordsOrder[] = sortBy.value.map(sort => ({
      field: sort.field,
      direction: sort.direction.toUpperCase() as 'ASC' | 'DESC'
    }))

    if (!config.value) {
      error.value = 'Configuración no encontrada'
      loading.value = false
      return
    }

    const response = await fetchRecords(config.value, {
      page: currentPage.value,
      page_size: pageSize.value,
      empresa_servidor_id: session.selectedEmpresa.value.empresaServidorId,
      filters: Object.keys(filters).length > 0 ? filters : undefined,
      order_by: orderBy.length > 0 ? orderBy : undefined
    })

    items.value = response.data || []
    totalCount.value = response.pagination?.total || 0
    totalPages.value = response.pagination?.total_pages || 0
  } catch (err: any) {
    error.value = err.message || 'Error al cargar datos'
    console.error('Error loading data:', err)
  } finally {
    loading.value = false
  }
}

// Búsqueda
const handleSearch = debounce(() => {
  currentPage.value = 1
  loadData()
}, 300)

const clearSearch = () => {
  searchQuery.value = ''
  currentPage.value = 1
  loadData()
}

// Filtros rápidos (múltiples)
const isQuickFilterActive = (filter: any) => {
  return activeQuickFilters.value.some(qf =>
    qf.field === filter.field && qf.value === filter.value
  )
}

const toggleQuickFilter = (filter: any) => {
  const existingIndex = activeQuickFilters.value.findIndex(qf =>
    qf.field === filter.field && qf.value === filter.value
  )
  
  if (existingIndex >= 0) {
    // Desactivar filtro
    activeQuickFilters.value.splice(existingIndex, 1)
  } else {
    // Activar filtro
    activeQuickFilters.value.push({
      ...filter,
      table: filter.table || currentModule.value?.filters?.[0]?.table,
      field: filter.field,
      value: filter.value,
      label: filter.label
    })
  }
  
  currentPage.value = 1
  loadData()
}

const clearAllQuickFilters = () => {
  activeQuickFilters.value = []
  currentPage.value = 1
  loadData()
}

// Paginación
const goToFirstPage = () => {
  if (currentPage.value > 1) {
    currentPage.value = 1
    loadData()
  }
}

const previousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
    loadData()
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    loadData()
  }
}

const goToLastPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value = totalPages.value
    loadData()
  }
}

const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadData()
  }
}

// Selección de fila
const selectRow = (item: any) => {
  if (config.value) {
    selectedRowId.value = item[config.value.primaryKey]
  }
}

// Helpers
const getModuleIcon = (moduleValue: string): string => {
  const icons: Record<string, string> = {
    facturacion: '📄',
    tesoreria: '💰',
    cartera: '💳',
    inventario: '📦',
    contabilidad: '🧮',
    nomina: '👥'
  }
  return icons[moduleValue] || '📋'
}

const getFieldIcon = (icon: string): string => {
  const iconMap: Record<string, string> = {
    'i-heroicons-document-text': '📄',
    'i-heroicons-hashtag': '#',
    'i-heroicons-identification': '🆔',
    'i-heroicons-calendar': '📅',
    'i-heroicons-user': '👤',
    'i-heroicons-currency-dollar': '$',
    'i-heroicons-clock': '🕐',
    'i-heroicons-check-circle': '✓'
  }
  return iconMap[icon] || '•'
}

// Debounce helper
function debounce<T extends (...args: any[]) => any>(func: T, wait: number): (...args: Parameters<T>) => void {
  let timeout: number | null = null
  return (...args: Parameters<T>): void => {
    const later = () => {
      if (timeout) clearTimeout(timeout)
      func(...args)
    }
    if (timeout) clearTimeout(timeout)
    timeout = window.setTimeout(later, wait)
  }
}
</script>

<style scoped>
.modules-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
}

.module-header {
  background: white;
  border-bottom: 1px solid #e2e8f0;
  padding: 1.5rem 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.header-content {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.btn-back {
  padding: 0.5rem 1rem;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 500;
  color: #475569;
  transition: all 0.2s;
}

.btn-back:hover {
  background: #e2e8f0;
  color: #1e293b;
}

.module-info h1 {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 0.25rem 0;
}

.module-info p {
  color: #64748b;
  font-size: 0.95rem;
  margin: 0;
}

.btn-modules {
  padding: 0.625rem 1.25rem;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s;
}

.btn-modules:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
}

.module-selector-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.module-selector {
  background: white;
  border-radius: 1rem;
  padding: 2rem;
  max-width: 800px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.module-selector h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 1.5rem 0;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;
}

.module-card {
  padding: 1.5rem;
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.module-card:hover {
  background: #f1f5f9;
  border-color: #2563eb;
  transform: translateY(-2px);
}

.module-card.active {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  border-color: #2563eb;
  color: white;
}

.module-icon {
  font-size: 2rem;
}

.module-name {
  font-weight: 600;
  font-size: 0.95rem;
}

.table-selector {
  max-width: 1600px;
  margin: 1.5rem auto 0;
  padding: 0 2rem;
}

.table-select {
  padding: 0.625rem 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  font-size: 1rem;
  background: white;
  cursor: pointer;
  min-width: 250px;
}

.filters-bar {
  max-width: 1600px;
  margin: 1rem auto 0;
  padding: 0 2rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.filters-label {
  font-weight: 600;
  color: #475569;
  font-size: 0.875rem;
}

.filter-btn {
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.filter-btn:hover {
  background: #f8fafc;
  border-color: #2563eb;
}

.filter-btn.active {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: white;
  border-color: #2563eb;
}

.filter-btn.clear {
  background: #fee2e2;
  border-color: #fecaca;
  color: #991b1b;
}

.search-bar {
  max-width: 1600px;
  margin: 1rem auto;
  padding: 0 2rem;
  display: flex;
  gap: 0.5rem;
}

.search-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  font-size: 1rem;
  transition: all 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.btn-clear-search {
  padding: 0.75rem 1rem;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  cursor: pointer;
  color: #64748b;
}

.table-container {
  max-width: 1600px;
  margin: 1.5rem auto;
  padding: 0 2rem;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #64748b;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-retry {
  margin-top: 1rem;
  padding: 0.625rem 1.25rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 600;
}

.table-wrapper {
  background: white;
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 100%;
}

.data-table th {
  text-align: left;
  padding: 1rem; /* p-4 como BCE */
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 2px solid #e2e8f0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.data-table th.center {
  text-align: center;
}

.data-table th.right {
  text-align: right;
}

.th-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.th-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
}

.th-tools {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.field-icon {
  font-size: 1rem;
}

.filter-badge {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: #dbeafe;
  border: 1px solid #93c5fd;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  cursor: pointer;
  color: #1e40af;
}

.filter-icon {
  font-size: 0.75rem;
}

.filter-value {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.filter-close {
  cursor: pointer;
  padding: 0.125rem;
  border-radius: 0.125rem;
}

.filter-close:hover {
  background: #93c5fd;
}

.filter-btn-icon {
  padding: 0.25rem;
  background: transparent;
  border: none;
  cursor: pointer;
  color: #64748b;
  font-size: 0.875rem;
  transition: color 0.2s;
  border-radius: 0.25rem;
}

.filter-btn-icon:hover {
  color: #2563eb;
  background: #f1f5f9;
}

.sort-container {
  position: relative;
}

.sort-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem;
  background: transparent;
  border: none;
  cursor: pointer;
  color: #64748b;
  font-size: 0.875rem;
  transition: all 0.2s;
  border-radius: 0.25rem;
}

.sort-btn:hover {
  color: #2563eb;
  background: #f1f5f9;
}

.sort-btn.active {
  color: #2563eb;
}

.sort-icon {
  font-size: 0.875rem;
}

.sort-number {
  font-size: 0.625rem;
  background: #2563eb;
  color: white;
  border-radius: 50%;
  width: 1rem;
  height: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

.sort-menu {
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 0.25rem;
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  border: 1px solid #e2e8f0;
  z-index: 50;
  min-width: 200px;
  overflow: hidden;
}

.sort-menu-header {
  padding: 0.75rem 1rem;
  font-size: 0.75rem;
  color: #64748b;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  font-weight: 600;
}

.sort-menu-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.75rem 1rem;
  background: white;
  border: none;
  text-align: left;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background 0.15s;
}

.sort-menu-item:hover {
  background: #f8fafc;
}

.sort-menu-item.active {
  background: #dbeafe;
  color: #1e40af;
}

.sort-menu-item.remove {
  color: #dc2626;
  border-top: 1px solid #e2e8f0;
}

.sort-menu-item.remove:hover {
  background: #fee2e2;
}

.sort-menu-item .check {
  margin-left: auto;
  color: #2563eb;
  font-weight: 600;
}

.sort-menu-footer {
  padding: 0.75rem 1rem;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
}

.sort-order-title {
  font-size: 0.75rem;
  color: #64748b;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.sort-order-item {
  font-size: 0.75rem;
  color: #475569;
  margin-top: 0.25rem;
}

.data-table td {
  padding: 0.5rem; /* p-2 como BCE (más angosto) */
  border-bottom: 1px solid #f1f5f9;
  color: #1e293b;
  font-size: 0.75rem; /* text-xs como BCE */
}

.data-table td.center {
  text-align: center;
}

.data-table td.right {
  text-align: right;
}

.data-table tbody tr {
  cursor: pointer;
  transition: background 0.15s;
}

.data-table tbody tr:hover {
  background: #f8fafc;
}

.data-table tbody tr.selected {
  background: #dbeafe;
}

.table-controls {
  max-width: 1600px;
  margin: 1.5rem auto;
  padding: 0 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.controls-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.table-select-aux {
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  background: white;
  cursor: pointer;
  min-width: 150px;
}

.pagination-info {
  color: #64748b;
  font-size: 0.95rem;
}

.pagination-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-pagination {
  padding: 0.625rem 1rem;
  background: white;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
  font-size: 0.875rem;
}

.btn-pagination:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #2563eb;
  color: #2563eb;
}

.btn-pagination:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-numbers {
  display: flex;
  gap: 0.25rem;
}

.page-number {
  min-width: 2.5rem;
  height: 2.5rem;
  padding: 0.5rem;
  background: white;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-number:hover {
  background: #f8fafc;
  border-color: #2563eb;
}

.page-number.active {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: white;
  border-color: #2563eb;
}

/* Modal de filtros */
.filter-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 2rem;
}

.modal-body {
  padding: 1.5rem;
}

.auxiliary-tables-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.75rem;
}

.auxiliary-table-btn {
  padding: 0.75rem 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  background: white;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
  text-align: center;
}

.auxiliary-table-btn:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
  transform: translateY(-1px);
}

.auxiliary-table-btn.active {
  background: #dbeafe;
  border-color: #93c5fd;
  color: #2563eb;
  font-weight: 600;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.auxiliary-selector-overlay {
  z-index: 2500 !important; /* Por encima del modal de filtros (2000), pero debajo del modal de datos (3000) */
}

.auxiliary-selector-content {
  z-index: 2501 !important;
}

.btn-auxiliary-tables {
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  background: white;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}

.btn-auxiliary-tables:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.btn-basic-complete {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid;
}

.btn-basic-complete.basic {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1e40af;
}

.btn-basic-complete.complete {
  background: #f0f9ff;
  border-color: #7dd3fc;
  color: #0c4a6e;
}

.btn-basic-complete:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.btn-icon {
  font-size: 1rem;
}

.btn-text {
  font-weight: 600;
}

.filter-modal-content {
  background: white;
  border-radius: 1rem;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.filter-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.filter-modal-header h3 {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.filter-modal-header .close-btn {
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  border: none;
  background: #f1f5f9;
  color: #64748b;
  cursor: pointer;
  font-size: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.filter-modal-header .close-btn:hover {
  background: #e2e8f0;
  color: #1e293b;
}

.filter-modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.filter-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.filter-operators {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.5rem;
}

.operator-btn {
  padding: 0.5rem;
  background: white;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.operator-btn:hover {
  background: #f8fafc;
  border-color: #2563eb;
}

.operator-btn.active {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: white;
  border-color: #2563eb;
}

.filter-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  font-size: 1rem;
  transition: all 0.2s;
}

.filter-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.filter-label {
  font-weight: 600;
  color: #475569;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.date-separator {
  color: #64748b;
  font-weight: 500;
}

.text-filter-options,
.boolean-filter-options {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.text-filter-options label,
.boolean-filter-options label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: #475569;
}

.filter-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
}

.btn-cancel {
  padding: 0.625rem 1.25rem;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 500;
  color: #475569;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: #e2e8f0;
}

.btn-apply {
  padding: 0.625rem 1.25rem;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-apply:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
}

.slide-enter-active,
.slide-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
