<template>
  <div class="table-container">
    <table class="data-table">
      <thead>
        <tr>
          <th style="width: 120px;">NIT</th>
          <th style="min-width: 200px;">Cliente</th>
          <th style="width: 120px;">Servidor</th>
          <th style="min-width: 250px;">API Key</th>
          <th style="width: 140px;">Empresas</th>
          <th style="width: 100px;">Estado</th>
          <th style="width: 130px;">Fecha Creación</th>
          <th style="width: 130px;">Fecha Caducidad</th>
          <th style="width: 90px;">Peticiones</th>
          <th style="width: 60px;">Acciones</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="key in apiKeys" :key="key.id">
          <td><code>{{ key.nit }}</code></td>
          <td><strong>{{ key.nombre_cliente }}</strong></td>
          <td>
            <span v-if="key.servidor_nombre" class="badge">{{ key.servidor_nombre }}</span>
            <span v-else class="text-muted">Todos</span>
          </td>
          <td>
            <div class="api-key-cell">
              <code v-if="!key.showKey" class="api-key-masked">{{ key.api_key_masked || '••••••••' }}</code>
              <code v-else class="api-key-visible">{{ key.api_key }}</code>
              <button 
                class="btn-tiny btn-secondary" 
                @click="$emit('toggle-visibility', key.id)"
                :title="key.showKey ? 'Ocultar' : 'Mostrar'"
              >
                {{ key.showKey ? '👁️' : '👁️‍🗨️' }}
              </button>
              <button 
                class="btn-tiny btn-info" 
                @click="$emit('copy', key.api_key)"
                title="Copiar"
              >
                📋
              </button>
            </div>
          </td>
          <td>
            <span class="badge">{{ key.empresas_asociadas_count || 0 }}</span>
            <button 
              v-if="key.empresas_asociadas_count > 0"
              class="btn-tiny btn-info" 
              @click="$emit('view-empresas', key.id)"
              title="Ver empresas"
            >
              👁️
            </button>
          </td>
          <td>
            <span class="status-badge" :class="key.activa && !key.expirada ? 'status-active' : 'status-inactive'">
              {{ key.activa && !key.expirada ? 'Activa' : (key.expirada ? 'Expirada' : 'Inactiva') }}
            </span>
          </td>
          <td>{{ formatDate(key.fecha_creacion) }}</td>
          <td>
            <span :class="key.expirada ? 'text-danger' : ''">
              {{ formatDate(key.fecha_caducidad) }}
            </span>
          </td>
          <td>{{ key.contador_peticiones || 0 }}</td>
          <td>
            <DropdownMenu trigger-class="btn-menu-icon">
              <template #trigger>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="1"/>
                  <circle cx="12" cy="5" r="1"/>
                  <circle cx="12" cy="19" r="1"/>
                </svg>
              </template>
              <DropdownItem @click="$emit('regenerate', key.id)">
                🔄 Regenerar
              </DropdownItem>
              <DropdownItem @click="$emit('toggle-status', key.id, !key.activa)">
                {{ key.activa ? '⏸️ Desactivar' : '▶️ Activar' }}
              </DropdownItem>
              <DropdownDivider />
              <DropdownItem @click="$emit('manage-calendario-nits', key.id)">
                📅 Gestionar NITs Calendario
              </DropdownItem>
              <DropdownDivider />
              <DropdownItem danger @click="$emit('revoke', key.id)">
                🗑️ Revocar
              </DropdownItem>
            </DropdownMenu>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { APIKey } from '~/types/admin'
import { formatDate } from '../utils/formatters'
import DropdownMenu from './DropdownMenu.vue'
import DropdownItem from './DropdownItem.vue'
import DropdownDivider from './DropdownDivider.vue'

interface Props {
  apiKeys: APIKey[]
}

defineProps<Props>()

defineEmits<{
  'toggle-visibility': [keyId: number]
  copy: [apiKey: string]
  'view-empresas': [keyId: number]
  regenerate: [keyId: number]
  'toggle-status': [keyId: number, newStatus: boolean]
  'manage-calendario-nits': [keyId: number]
  revoke: [keyId: number]
}>()
</script>

<style scoped>
.api-key-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.api-key-masked {
  font-family: 'Courier New', monospace;
  background: #f3f4f6;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.api-key-visible {
  font-family: 'Courier New', monospace;
  background: #f3f4f6;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  word-break: break-all;
  max-width: 300px;
}

.btn-tiny {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-tiny.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-tiny.btn-secondary:hover {
  background: #e5e7eb;
}

.btn-tiny.btn-info {
  background: #dbeafe;
  color: #1e40af;
}

.btn-tiny.btn-info:hover {
  background: #bfdbfe;
}

.badge {
  padding: 0.25rem 0.75rem;
  background: #f3f4f6;
  color: #4b5563;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.text-muted {
  color: #9ca3af;
  font-style: italic;
}

.text-danger {
  color: #dc2626;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-active {
  background: #d1fae5;
  color: #065f46;
}

.status-inactive {
  background: #fee2e2;
  color: #991b1b;
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
  cursor: pointer;
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

.data-table {
  table-layout: auto;
  width: 100%;
}

.data-table td {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 0;
}

.data-table td:nth-child(2) {
  white-space: normal;
  max-width: 200px;
}

.data-table td:nth-child(4) {
  white-space: normal;
  max-width: 300px;
}

.data-table td:last-child {
  position: relative;
  overflow: visible;
}
</style>

