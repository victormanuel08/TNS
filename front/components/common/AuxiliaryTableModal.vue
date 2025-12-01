<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="auxiliary-modal-overlay" @click.self="close">
        <div class="auxiliary-modal-content">
          <div class="auxiliary-modal-header">
            <h3>{{ config?.tableTitle || 'Tabla Auxiliar' }}</h3>
            <button @click="close" class="close-btn">×</button>
          </div>
          
          <!-- Barra de búsqueda -->
          <div class="auxiliary-search-bar">
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="config?.searchPlaceholder || 'Buscar...'"
              class="auxiliary-search-input"
              @input="handleSearch"
            />
            <button v-if="searchQuery" @click="clearSearch" class="btn-clear-search">✕</button>
          </div>
          
          <!-- Contenido con scroll -->
          <div class="auxiliary-modal-body">
            <!-- Loading -->
            <div v-if="loading" class="auxiliary-loading-state">
              <div class="spinner"></div>
              <p>Cargando registros...</p>
            </div>
            
            <!-- Error -->
            <div v-else-if="error" class="auxiliary-error-state">
              <p>{{ error }}</p>
              <button @click="loadData" class="btn-retry">Reintentar</button>
            </div>
            
            <!-- Tabla con scroll -->
            <div v-else-if="items.length > 0" class="auxiliary-table-wrapper">
              <table class="auxiliary-data-table">
                <thead>
                  <tr>
                    <th
                      v-for="field in visibleFields"
                      :key="field.name"
                      :class="[field.textAlign || 'left']"
                      :style="{ width: field.width || 'auto' }"
                    >
                      <div class="th-content">
                        <span v-if="field.icon" class="field-icon">{{ getFieldIcon(field.icon) }}</span>
                        <span>{{ field.label }}</span>
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
            <div v-else class="auxiliary-empty-state">
              <p>{{ config?.emptyMessage || 'No se encontraron resultados' }}</p>
            </div>
          </div>
          
          <!-- Controles de tabla y paginación -->
          <div v-if="!loading && items.length > 0" class="auxiliary-modal-footer">
            <div class="auxiliary-controls-left">
              <!-- Toggle Básico/Completo -->
              <button
                @click="basicMode = !basicMode"
                class="btn-basic-complete"
                :class="{ 'basic': basicMode, 'complete': !basicMode }"
              >
                <span class="btn-icon">{{ basicMode ? '📋' : '📊' }}</span>
                <span class="btn-text">{{ basicMode ? 'Básico' : 'Completo' }}</span>
              </button>
            </div>
            
            <div class="auxiliary-pagination-left">
              <span class="auxiliary-pagination-info">
                Mostrando {{ showingStart }} - {{ showingEnd }} de {{ totalCount }}
              </span>
            </div>
            <div class="auxiliary-pagination-right">
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
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useModuleConfig, type TableConfig } from '@/composables/useModuleConfig'
import { useTNSRecords, type TNSRecordsFilters, type TNSRecordsOrder } from '@/composables/useTNSRecords'
import { useSessionStore } from '@/composables/useSessionStore'
import FieldRenderer from '@/components/common/FieldRenderer.vue'

interface Props {
  isOpen: boolean
  tableValue: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
}>()

const { getConfig } = useModuleConfig()
const { fetchRecords, searchRecords } = useTNSRecords()
const session = useSessionStore()

// Estado
const searchQuery = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const items = ref<any[]>([])
const selectedRowId = ref<any>(null)
const currentPage = ref(1)
const pageSize = ref(10)
const totalCount = ref(0)
const totalPages = ref(0)
const basicMode = ref(true)

// Computed
const config = computed<TableConfig | undefined>(() => {
  return getConfig(props.tableValue)
})

const visibleFields = computed(() => {
  if (!config.value) return []
  return config.value.fields.filter(f => {
    // Ocultar campos marcados como hidden
    if (f.hidden) return false
    // Si basicMode es true (modo básico), mostrar solo campos con typetable === 'basic'
    // Si basicMode es false (modo completo), mostrar todos los campos (excepto hidden)
    if (basicMode.value) {
      return f.typetable === 'basic'
    } else {
      return true
    }
  })
})

const showingStart = computed(() => (currentPage.value - 1) * pageSize.value + 1)
const showingEnd = computed(() => Math.min(currentPage.value * pageSize.value, totalCount.value))

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

// Funciones
const close = () => {
  emit('close')
}

const getFieldIcon = (iconName: string) => {
  return iconName
}

const loadData = async () => {
  if (!config.value) return
  
  if (!session.selectedEmpresa.value?.empresaServidorId) {
    error.value = 'No hay empresa seleccionada'
    return
  }
  
  loading.value = true
  error.value = null
  
  try {
    // Construir filtros
    const filters: TNSRecordsFilters = {}
    
    // Agregar búsqueda global si existe
    if (searchQuery.value.trim()) {
      const searchFields = config.value.searchFields || []
      if (searchFields.length > 0) {
        filters.OR = searchFields.map(field => ({
          [field]: { contains: searchQuery.value.trim() }
        }))
      }
    }
    
    const response = await fetchRecords(config.value, {
      page: currentPage.value,
      page_size: pageSize.value,
      empresa_servidor_id: session.selectedEmpresa.value.empresaServidorId,
      filters: Object.keys(filters).length > 0 ? filters : undefined
    })
    
    items.value = response.data || []
    totalCount.value = response.pagination?.total || 0
    totalPages.value = response.pagination?.total_pages || 0
  } catch (err: any) {
    error.value = err.message || 'Error al cargar datos'
    console.error('Error loading auxiliary data:', err)
    // En caso de error, limpiar datos
    items.value = []
    totalCount.value = 0
    totalPages.value = 0
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

// Paginación
const goToFirstPage = () => {
  currentPage.value = 1
  loadData()
}

const previousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
    loadData()
  }
}

const goToPage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
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
  currentPage.value = totalPages.value
  loadData()
}

const selectRow = (item: any) => {
  selectedRowId.value = item[config.value?.primaryKey || 'id']
}

// Watch para recargar cuando se abre la modal o cambia la tabla
watch(() => props.isOpen, (open) => {
  if (open && props.tableValue) {
    currentPage.value = 1
    searchQuery.value = ''
    basicMode.value = true
    loadData()
  }
})

watch(() => props.tableValue, () => {
  if (props.isOpen) {
    currentPage.value = 1
    searchQuery.value = ''
    basicMode.value = true
    loadData()
  }
})

// Debounce utility
function debounce<T extends (...args: any[]) => any>(func: T, wait: number): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null
  return (...args: Parameters<T>): void => {
    const later = () => {
      if (timeout) clearTimeout(timeout)
      func(...args)
    }
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}
</script>

<style scoped>
.auxiliary-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
  padding: 2rem;
}

.auxiliary-modal-content {
  background: white;
  border-radius: 1rem;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  width: 100%;
  max-width: 95vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.auxiliary-modal-header {
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.auxiliary-modal-header h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #64748b;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.auxiliary-search-bar {
  padding: 1rem 2rem;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.auxiliary-search-input {
  flex: 1;
  padding: 0.625rem 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.auxiliary-search-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.btn-clear-search {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.625rem 0.75rem;
  cursor: pointer;
  color: #64748b;
  transition: all 0.2s;
}

.btn-clear-search:hover {
  background: #e2e8f0;
  color: #1e293b;
}

.auxiliary-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 2rem;
  min-height: 300px;
  max-height: calc(90vh - 300px);
}

.auxiliary-table-wrapper {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
}

.auxiliary-data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.auxiliary-data-table thead {
  background: #f8fafc;
  position: sticky;
  top: 0;
  z-index: 10;
}

.auxiliary-data-table th {
  padding: 0.75rem 1rem;
  text-align: left;
  font-weight: 600;
  color: #475569;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

.auxiliary-data-table th.text-center {
  text-align: center;
}

.auxiliary-data-table th.text-right {
  text-align: right;
}

.auxiliary-data-table td {
  padding: 0.5rem 1rem;
  border-bottom: 1px solid #f1f5f9;
  color: #1e293b;
  font-size: 0.75rem;
}

.auxiliary-data-table td.text-center {
  text-align: center;
}

.auxiliary-data-table td.text-right {
  text-align: right;
}

.auxiliary-data-table tbody tr {
  cursor: pointer;
  transition: background-color 0.15s;
}

.auxiliary-data-table tbody tr:hover {
  background: #f8fafc;
}

.auxiliary-data-table tbody tr.selected {
  background: #dbeafe;
}

.auxiliary-loading-state,
.auxiliary-error-state,
.auxiliary-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #64748b;
  text-align: center;
}

.spinner {
  width: 2rem;
  height: 2rem;
  border: 3px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-retry {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-retry:hover {
  background: #1d4ed8;
}

.auxiliary-modal-footer {
  padding: 1rem 2rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.auxiliary-controls-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
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

.auxiliary-pagination-left {
  display: flex;
  align-items: center;
}

.auxiliary-pagination-info {
  font-size: 0.875rem;
  color: #64748b;
}

.auxiliary-pagination-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-pagination,
.page-number {
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  background: white;
  color: #475569;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
  min-width: 2.5rem;
  text-align: center;
}

.btn-pagination:hover:not(:disabled),
.page-number:hover:not(.active) {
  background: #f1f5f9;
  border-color: #94a3b8;
}

.btn-pagination:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-number.active {
  background: #2563eb;
  color: white;
  border-color: #2563eb;
  font-weight: 600;
}

.page-numbers {
  display: flex;
  gap: 0.25rem;
}

/* Transiciones */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .auxiliary-modal-content,
.modal-leave-active .auxiliary-modal-content {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.modal-enter-from .auxiliary-modal-content,
.modal-leave-to .auxiliary-modal-content {
  transform: scale(0.95);
  opacity: 0;
}
</style>

