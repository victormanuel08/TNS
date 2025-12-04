<template>
  <div class="pagination-container">
    <div class="pagination-info">
      Mostrando {{ start }}-{{ end }} de {{ total }} resultados
    </div>
    <div class="pagination-controls">
      <button
        class="pagination-btn"
        :disabled="currentPage === 1"
        @click="$emit('previous')"
      >
        ← Anterior
      </button>
      <div class="pagination-pages">
        <button
          v-for="page in visiblePages"
          :key="page"
          class="pagination-page"
          :class="{ active: page === currentPage }"
          @click="$emit('go-to', page)"
        >
          {{ page }}
        </button>
      </div>
      <button
        class="pagination-btn"
        :disabled="currentPage === totalPages"
        @click="$emit('next')"
      >
        Siguiente →
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  currentPage: number
  totalPages: number
  total: number
  itemsPerPage: number
}

const props = defineProps<Props>()

const start = computed(() => {
  return (props.currentPage - 1) * props.itemsPerPage + 1
})

const end = computed(() => {
  const endValue = props.currentPage * props.itemsPerPage
  return endValue > props.total ? props.total : endValue
})

const visiblePages = computed(() => {
  const pages: (number | string)[] = []
  const maxVisible = 5
  
  if (props.totalPages <= maxVisible) {
    // Mostrar todas las páginas
    for (let i = 1; i <= props.totalPages; i++) {
      pages.push(i)
    }
  } else {
    // Mostrar páginas con elipsis
    if (props.currentPage <= 3) {
      for (let i = 1; i <= 4; i++) {
        pages.push(i)
      }
      pages.push('...')
      pages.push(props.totalPages)
    } else if (props.currentPage >= props.totalPages - 2) {
      pages.push(1)
      pages.push('...')
      for (let i = props.totalPages - 3; i <= props.totalPages; i++) {
        pages.push(i)
      }
    } else {
      pages.push(1)
      pages.push('...')
      for (let i = props.currentPage - 1; i <= props.currentPage + 1; i++) {
        pages.push(i)
      }
      pages.push('...')
      pages.push(props.totalPages)
    }
  }
  
  return pages
})

defineEmits<{
  'go-to': [page: number]
  next: []
  previous: []
}>()
</script>

<style scoped>
.pagination-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  margin-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.pagination-info {
  font-size: 0.875rem;
  color: #6b7280;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.pagination-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-pages {
  display: flex;
  gap: 0.25rem;
}

.pagination-page {
  min-width: 2.5rem;
  height: 2.5rem;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pagination-page:hover:not(.active):not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}

.pagination-page.active {
  background: #1f2937;
  color: white;
  border-color: #1f2937;
  font-weight: 600;
}

.pagination-page:disabled {
  cursor: default;
  background: transparent;
  border: none;
}
</style>

