<template>
  <div class="server-card">
    <div class="server-header">
      <h3>{{ server.nombre }}</h3>
      <span class="server-badge" :class="`badge-${server.tipo_servidor?.toLowerCase()}`">
        {{ server.tipo_servidor }}
      </span>
    </div>
    <div class="server-info">
      <p class="info-item">
        <span class="info-label">Host:</span>
        <span class="info-value">{{ server.host }}</span>
      </p>
      <p class="info-item" v-if="server.puerto">
        <span class="info-label">Puerto:</span>
        <span class="info-value">{{ server.puerto }}</span>
      </p>
      <p class="info-item">
        <span class="info-label">Usuario:</span>
        <span class="info-value">{{ server.usuario }}</span>
      </p>
    </div>
    <div class="server-actions">
      <DropdownMenu trigger-class="btn-menu-icon">
        <template #trigger>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="1"/>
            <circle cx="12" cy="5" r="1"/>
            <circle cx="12" cy="19" r="1"/>
          </svg>
        </template>
        <DropdownItem @click="$emit('scan', server.id)">
          <svg v-if="scanning" class="spinner-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
          </svg>
          <svg v-else-if="hasActiveTask" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="m21 21-4.35-4.35"/>
          </svg>
          {{ hasActiveTask ? 'Ver Progreso' : 'Escanear Empresas' }}
        </DropdownItem>
        <DropdownItem @click="$emit('view-empresas', server.id)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
          Ver Empresas
        </DropdownItem>
        <DropdownItem @click="$emit('edit', server)">
          ✏️ Editar
        </DropdownItem>
        <DropdownItem @click="$emit('details', server.id)">
          ℹ️ Detalles
        </DropdownItem>
        <DropdownDivider />
        <DropdownItem danger @click="$emit('delete', server.id)">
          🗑️ Eliminar
        </DropdownItem>
      </DropdownMenu>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Servidor } from '~/types/admin'
import DropdownMenu from './DropdownMenu.vue'
import DropdownItem from './DropdownItem.vue'
import DropdownDivider from './DropdownDivider.vue'

interface Props {
  server: Servidor
  scanning?: boolean
  hasActiveTask?: boolean
}

defineProps<Props>()

defineEmits<{
  scan: [serverId: number]
  'view-empresas': [serverId: number]
  edit: [server: Servidor]
  details: [serverId: number]
  delete: [serverId: number]
}>()
</script>

<style scoped>
.server-card {
  background: white;
  border-radius: 1rem;
  padding: 1.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: all 0.2s;
  border: 1px solid #e5e7eb;
}

.server-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.server-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.server-card h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.server-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.badge-firebird {
  background: #f3f4f6;
  color: #4b5563;
}

.badge-postgresql {
  background: #dbeafe;
  color: #1e40af;
}

.badge-sqlserver {
  background: #fef3c7;
  color: #92400e;
}

.badge-mysql {
  background: #d1fae5;
  color: #065f46;
}

.server-info {
  margin-bottom: 1rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f3f4f6;
  font-size: 0.875rem;
}

.info-item:last-child {
  border-bottom: none;
}

.info-label {
  color: #6b7280;
  font-weight: 500;
}

.info-value {
  color: #1f2937;
  font-weight: 600;
}

.server-actions {
  margin-top: 1rem;
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

:deep(.btn-menu-icon) {
  padding: 0.5rem;
  min-width: auto;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  color: #4b5563;
  transition: all 0.2s;
}

:deep(.btn-menu-icon:hover) {
  background: #e5e7eb;
  border-color: #d1d5db;
  color: #1f2937;
}

:deep(.btn-menu-icon.active) {
  background: #1f2937;
  border-color: #1f2937;
  color: white;
}

.spinner-icon {
  animation: spin 1s linear infinite;
  width: 16px;
  height: 16px;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>

