<template>
  <div class="table-container">
    <table class="data-table">
      <thead>
        <tr>
          <th>NIT</th>
          <th>Cliente</th>
          <th>Servidor</th>
          <th>API Key</th>
          <th>Empresas Asociadas</th>
          <th>Estado</th>
          <th>Fecha Creación</th>
          <th>Fecha Caducidad</th>
          <th>Peticiones</th>
          <th>Acciones</th>
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
            <DropdownMenu>
              <template #trigger>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="1"/>
                  <circle cx="12" cy="5" r="1"/>
                  <circle cx="12" cy="19" r="1"/>
                </svg>
                Menú
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
</style>

