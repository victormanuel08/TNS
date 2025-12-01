<template>
  <span :class="fieldClass">
    <template v-if="field.format === 'currency' || field.format2 === 'currency'">
      {{ formatCurrency(value) }}
    </template>
    <template v-else-if="field.format === 'date' || field.format2 === 'date'">
      {{ formatDate(value) }}
    </template>
    <template v-else-if="field.format === 'time'">
      {{ formatTime(value) }}
    </template>
    <template v-else-if="field.format === 'badge'">
      <span class="badge" :class="badgeClass">
        {{ formatBadge(value) }}
      </span>
    </template>
    <template v-else-if="field.format === 'number'">
      {{ formatNumber(value) }}
    </template>
    <template v-else>
      {{ value || '-' }}
    </template>
  </span>
</template>

<script setup lang="ts">
import type { TableField } from '@/composables/useModuleConfig'

interface Props {
  field: TableField
  value: any
}

const props = defineProps<Props>()

const fieldClass = computed(() => {
  const classes = []
  if (props.field.textAlign) {
    classes.push(`text-${props.field.textAlign}`)
  }
  return classes.join(' ')
})

const badgeClass = computed(() => {
  const color = props.field.badgeColor || 'blue'
  return `badge-${color}`
})

const formatCurrency = (value: any): string => {
  if (!value && value !== 0) return '-'
  const num = typeof value === 'string' ? parseFloat(value) : value
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0
  }).format(num)
}

const formatDate = (value: any): string => {
  if (!value) return '-'
  try {
    const date = new Date(value)
    return date.toLocaleDateString('es-CO', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  } catch {
    return value
  }
}

const formatTime = (value: any): string => {
  if (!value) return '-'
  try {
    if (typeof value === 'string' && value.includes(':')) {
      return value
    }
    const date = new Date(value)
    return date.toLocaleTimeString('es-CO', {
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return value
  }
}

const formatNumber = (value: any): string => {
  if (!value && value !== 0) return '-'
  const num = typeof value === 'string' ? parseFloat(value) : value
  return new Intl.NumberFormat('es-CO').format(num)
}

const formatBadge = (value: any): string => {
  if (props.field.format2 === 'date') {
    return formatDate(value)
  } else if (props.field.format2 === 'currency') {
    return formatCurrency(value)
  }
  return value || '-'
}
</script>

<style scoped>
.badge {
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 500;
  display: inline-block;
}

.badge-blue {
  background: #dbeafe;
  color: #1e40af;
}

.badge-green {
  background: #d1fae5;
  color: #065f46;
}

.badge-yellow {
  background: #fef3c7;
  color: #92400e;
}

.badge-red {
  background: #fee2e2;
  color: #991b1b;
}
</style>

