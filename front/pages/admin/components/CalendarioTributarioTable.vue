<template>
  <div>
    <!-- Filtros -->
    <div class="filters-container">
      <div class="filter-group">
        <label>Impuesto:</label>
        <select v-model="filters.impuesto" class="filter-select" @change="$emit('filter-change', filters)">
          <option value="">Todos</option>
          <option v-for="impuesto in uniqueImpuestos" :key="impuesto" :value="impuesto">
            {{ impuesto }}
          </option>
        </select>
      </div>
      <div class="filter-group">
        <label>Tipo Tercero:</label>
        <select v-model="filters.tipo_tercero" class="filter-select" @change="$emit('filter-change', filters)">
          <option value="">Todos</option>
          <option v-for="tipo in uniqueTiposTercero" :key="tipo" :value="tipo">
            {{ tipo }}
          </option>
        </select>
      </div>
      <div class="filter-group">
        <label>Régimen:</label>
        <select v-model="filters.tipo_regimen" class="filter-select" @change="$emit('filter-change', filters)">
          <option value="">Todos</option>
          <option v-for="regimen in uniqueRegimenes" :key="regimen" :value="regimen">
            {{ regimen }}
          </option>
        </select>
      </div>
      <div class="filter-group">
        <label>Dígitos NIT:</label>
        <input 
          v-model="filters.digitos_nit" 
          type="text" 
          placeholder="Filtrar por dígitos..."
          class="filter-input"
          @input="$emit('filter-change', filters)"
        />
      </div>
      <button class="btn-secondary" @click="resetFilters">
        🔄 Limpiar Filtros
      </button>
    </div>

    <!-- Tabla con ordenamiento -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th 
              class="sortable" 
              @click="$emit('sort', 'impuesto')"
              :class="{ 'sort-asc': sortBy === 'impuesto' && sortOrder === 'asc', 'sort-desc': sortBy === 'impuesto' && sortOrder === 'desc' }"
            >
              Impuesto
              <span class="sort-icon">{{ sortBy === 'impuesto' ? (sortOrder === 'asc' ? '↑' : '↓') : '⇅' }}</span>
            </th>
            <th 
              class="sortable" 
              @click="$emit('sort', 'digitos_nit')"
              :class="{ 'sort-asc': sortBy === 'digitos_nit' && sortOrder === 'asc', 'sort-desc': sortBy === 'digitos_nit' && sortOrder === 'desc' }"
            >
              Dígitos NIT
              <span class="sort-icon">{{ sortBy === 'digitos_nit' ? (sortOrder === 'asc' ? '↑' : '↓') : '⇅' }}</span>
            </th>
            <th 
              class="sortable" 
              @click="$emit('sort', 'tipo_tercero')"
              :class="{ 'sort-asc': sortBy === 'tipo_tercero' && sortOrder === 'asc', 'sort-desc': sortBy === 'tipo_tercero' && sortOrder === 'desc' }"
            >
              Tipo Tercero
              <span class="sort-icon">{{ sortBy === 'tipo_tercero' ? (sortOrder === 'asc' ? '↑' : '↓') : '⇅' }}</span>
            </th>
            <th 
              class="sortable" 
              @click="$emit('sort', 'tipo_regimen')"
              :class="{ 'sort-asc': sortBy === 'tipo_regimen' && sortOrder === 'asc', 'sort-desc': sortBy === 'tipo_regimen' && sortOrder === 'desc' }"
            >
              Régimen
              <span class="sort-icon">{{ sortBy === 'tipo_regimen' ? (sortOrder === 'asc' ? '↑' : '↓') : '⇅' }}</span>
            </th>
            <th 
              class="sortable" 
              @click="$emit('sort', 'fecha_limite')"
              :class="{ 'sort-asc': sortBy === 'fecha_limite' && sortOrder === 'asc', 'sort-desc': sortBy === 'fecha_limite' && sortOrder === 'desc' }"
            >
              Fecha Límite
              <span class="sort-icon">{{ sortBy === 'fecha_limite' ? (sortOrder === 'asc' ? '↑' : '↓') : '⇅' }}</span>
            </th>
            <th>Descripción</th>
            <th 
              class="sortable" 
              @click="$emit('sort', 'fecha_actualizacion')"
              :class="{ 'sort-asc': sortBy === 'fecha_actualizacion' && sortOrder === 'asc', 'sort-desc': sortBy === 'fecha_actualizacion' && sortOrder === 'desc' }"
            >
              Última Actualización
              <span class="sort-icon">{{ sortBy === 'fecha_actualizacion' ? (sortOrder === 'asc' ? '↑' : '↓') : '⇅' }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="vigencia in vigencias" :key="vigencia.id">
            <td><strong>{{ vigencia.impuesto?.codigo }}</strong><br><small>{{ vigencia.impuesto?.nombre }}</small></td>
            <td><code>{{ vigencia.digitos_nit || 'TODOS' }}</code></td>
            <td>{{ vigencia.tipo_tercero?.codigo || 'TODOS' }}</td>
            <td>{{ vigencia.tipo_regimen?.codigo || 'TODOS' }}</td>
            <td><strong>{{ formatDate(vigencia.fecha_limite) }}</strong></td>
            <td>{{ vigencia.descripcion || '-' }}</td>
            <td>{{ formatDate(vigencia.fecha_actualizacion) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { VigenciaTributaria } from '../types'
import { formatDate } from '../utils/formatters'

interface Props {
  vigencias: VigenciaTributaria[]
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  filters?: {
    impuesto: string
    tipo_tercero: string
    tipo_regimen: string
    digitos_nit: string
  }
}

const props = withDefaults(defineProps<Props>(), {
  sortBy: 'fecha_limite',
  sortOrder: 'asc',
  filters: () => ({
    impuesto: '',
    tipo_tercero: '',
    tipo_regimen: '',
    digitos_nit: ''
  })
})

const localFilters = ref({ ...props.filters })

// Sincronizar con props
watch(() => props.filters, (newFilters) => {
  localFilters.value = { ...newFilters }
}, { deep: true })

const uniqueImpuestos = computed(() => {
  const impuestos = new Set<string>()
  props.vigencias.forEach(v => {
    if (v.impuesto?.codigo) impuestos.add(v.impuesto.codigo)
  })
  return Array.from(impuestos).sort()
})

const uniqueTiposTercero = computed(() => {
  const tipos = new Set<string>()
  props.vigencias.forEach(v => {
    const tipo = v.tipo_tercero?.codigo || 'TODOS'
    tipos.add(tipo)
  })
  return Array.from(tipos).sort()
})

const uniqueRegimenes = computed(() => {
  const regimenes = new Set<string>()
  props.vigencias.forEach(v => {
    const regimen = v.tipo_regimen?.codigo || 'TODOS'
    regimenes.add(regimen)
  })
  return Array.from(regimenes).sort()
})

const resetFilters = () => {
  localFilters.value = {
    impuesto: '',
    tipo_tercero: '',
    tipo_regimen: '',
    digitos_nit: ''
  }
  emit('filter-change', localFilters.value)
}

const emit = defineEmits<{
  'sort': [column: string]
  'filter-change': [filters: typeof localFilters.value]
}>()
</script>

<style scoped>
.filters-container {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 0.5rem;
  margin-bottom: 1.5rem;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.filter-group label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
}

.filter-select,
.filter-input {
  padding: 0.5rem 0.75rem;
  border: 1.5px solid #d1d5db;
  border-radius: 0.5rem;
  background: white;
  color: #1f2937;
  font-size: 0.875rem;
  min-width: 150px;
  transition: all 0.2s;
}

.filter-select:focus,
.filter-input:focus {
  outline: none;
  border-color: #4b5563;
  box-shadow: 0 0 0 3px rgba(75, 85, 99, 0.1);
}

.sortable {
  cursor: pointer;
  user-select: none;
  position: relative;
  padding-right: 1.5rem;
}

.sortable:hover {
  background: #f9fafb;
}

.sort-icon {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.75rem;
  color: #9ca3af;
}

.sortable.sort-asc .sort-icon,
.sortable.sort-desc .sort-icon {
  color: #1f2937;
  font-weight: bold;
}
</style>

