<template>
  <div class="table-container" style="margin-top: 16px;">
    <table class="data-table">
      <thead>
        <tr>
          <th>CODIGO</th>
          <th>NOMBRE</th>
          <th>NIT</th>
          <th>REPRES</th>
          <th>ANOFIS</th>
          <th>ARCHIVO</th>
          <th>Último Backup</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="empresas.length === 0">
          <td colspan="8" class="text-center">
            No hay empresas en este servidor.
          </td>
        </tr>
        <tr v-for="empresa in empresas" :key="empresa.id">
          <td>{{ empresa.codigo }}</td>
          <td>{{ empresa.nombre }}</td>
          <td>{{ empresa.nit || empresa.nit_normalizado }}</td>
          <td>{{ empresa.representante_legal || '-' }}</td>
          <td>{{ empresa.anio_fiscal }}</td>
          <td>
            <code style="font-size: 11px;">{{ empresa.ruta_base ? empresa.ruta_base.split('/').pop() || empresa.ruta_base.split('\\').pop() : '-' }}</code>
          </td>
          <td>
            <div v-if="empresa.ultimo_backup" class="ultimo-backup-cell">
              <div 
                class="backup-info-clickable" 
                @click.stop="$emit('backup-click', empresa)"
                :title="`Último backup: ${formatDate(empresa.ultimo_backup.fecha_backup)}`"
              >
                <span class="backup-date">{{ formatDate(empresa.ultimo_backup.fecha_backup) }}</span>
                <span class="backup-size">{{ formatFileSize(empresa.ultimo_backup.tamano_bytes) }}</span>
                <span class="backup-status" :class="`status-${empresa.ultimo_backup.estado}`">
                  {{ empresa.ultimo_backup.estado === 'completado' ? '✓' : empresa.ultimo_backup.estado === 'error' ? '✗' : '⏳' }}
                </span>
              </div>
              <div 
                v-if="backupMenuOpen === empresa.id" 
                class="dropdown-menu backup-menu"
                @click.stop
              >
                <DropdownItem @click="$emit('download-fbk', empresa.ultimo_backup.id)">
                  📥 Descargar FBK
                </DropdownItem>
                <DropdownItem @click="$emit('request-gdb', empresa.ultimo_backup.id, empresa)">
                  📧 Solicitar GDB por Email
                </DropdownItem>
                <DropdownDivider />
                <DropdownItem @click="$emit('close-backup-menu')">
                  Cancelar
                </DropdownItem>
              </div>
            </div>
            <span v-else class="text-muted">Sin backup</span>
          </td>
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
              <DropdownItem @click="$emit('create-backup', empresa.id)">
                📦 Crear Backup
              </DropdownItem>
              <DropdownItem 
                v-if="empresa.ultimo_backup"
                @click="$emit('download-fbk', empresa.ultimo_backup.id)"
              >
                ⬇️ Descargar Último Backup (FBK)
              </DropdownItem>
              <DropdownItem 
                v-if="empresa.ultimo_backup"
                @click="$emit('request-gdb', empresa.ultimo_backup.id, empresa)"
              >
                📧 Solicitar GDB por Email
              </DropdownItem>
              <DropdownDivider />
              <DropdownItem @click="$emit('edit', empresa)">
                ✏️ Editar
              </DropdownItem>
            </DropdownMenu>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { EmpresaServidor } from '../types'
import DropdownMenu from './DropdownMenu.vue'
import DropdownItem from './DropdownItem.vue'
import DropdownDivider from './DropdownDivider.vue'
import { formatDate, formatFileSize } from '../utils/formatters'

interface Props {
  empresas: (EmpresaServidor & { ultimo_backup?: any })[]
  backupMenuOpen?: number | null
}

withDefaults(defineProps<Props>(), {
  backupMenuOpen: null
})

defineEmits<{
  'backup-click': [empresa: any]
  'create-backup': [empresaId: number]
  'download-fbk': [backupId: number]
  'request-gdb': [backupId: number, empresa: any]
  'edit': [empresa: any]
  'close-backup-menu': []
}>()
</script>

<style scoped>
.ultimo-backup-cell {
  position: relative;
}

.backup-info-clickable {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.5rem;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.backup-info-clickable:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.backup-date {
  font-size: 0.75rem;
  color: #6b7280;
  font-weight: 500;
}

.backup-size {
  font-size: 0.7rem;
  color: #9ca3af;
}

.backup-status {
  display: inline-block;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  text-align: center;
  line-height: 18px;
  font-size: 0.7rem;
}

.backup-status.status-completado {
  background: #d1fae5;
  color: #10b981;
}

.backup-status.status-error {
  background: #fee2e2;
  color: #dc2626;
}

.backup-status.status-pendiente,
.backup-status.status-procesando {
  background: #fef3c7;
  color: #f59e0b;
}

.backup-menu {
  min-width: 200px;
  z-index: 1001;
}

.text-muted {
  color: #9ca3af;
  font-style: italic;
}

.text-center {
  text-align: center;
  padding: 2rem;
  color: #6b7280;
}
</style>

