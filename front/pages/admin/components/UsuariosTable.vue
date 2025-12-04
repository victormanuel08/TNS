<template>
  <div class="table-container">
    <table class="data-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Usuario</th>
          <th>Email</th>
          <th>Nombre</th>
          <th>Superusuario</th>
          <th>Staff</th>
          <th>Activo</th>
          <th>Último Login</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="usr in usuarios" :key="usr.id">
          <td>{{ usr.id }}</td>
          <td><strong>{{ usr.username }}</strong></td>
          <td>{{ usr.email || '-' }}</td>
          <td>{{ (usr.first_name + ' ' + usr.last_name).trim() || '-' }}</td>
          <td>
            <span class="status-badge" :class="usr.is_superuser ? 'status-active' : 'status-inactive'">
              {{ usr.is_superuser_display }}
            </span>
          </td>
          <td>
            <span class="status-badge" :class="usr.is_staff ? 'status-active' : 'status-inactive'">
              {{ usr.is_staff_display }}
            </span>
          </td>
          <td>
            <span class="status-badge" :class="usr.is_active ? 'status-active' : 'status-inactive'">
              {{ usr.is_active ? 'Activo' : 'Inactivo' }}
            </span>
          </td>
          <td>{{ usr.last_login_formatted || 'Nunca' }}</td>
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
              <DropdownItem @click="$emit('edit', usr)">
                ✏️ Editar
              </DropdownItem>
              <DropdownItem @click="$emit('reset-password', usr)">
                🔑 Resetear Contraseña
              </DropdownItem>
              <DropdownItem @click="$emit('view-permisos', usr.id)">
                🔐 Ver Permisos
              </DropdownItem>
              <DropdownItem @click="$emit('view-tenant-profile', usr.id)">
                🏢 Ver Tenant Profile
              </DropdownItem>
              <DropdownDivider />
              <DropdownItem 
                danger 
                :disabled="disabledDelete && usr.id === currentUserId"
                @click="$emit('delete', usr)"
              >
                🗑️ Eliminar
              </DropdownItem>
            </DropdownMenu>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { User } from '~/types/admin'
import DropdownMenu from './DropdownMenu.vue'
import DropdownItem from './DropdownItem.vue'
import DropdownDivider from './DropdownDivider.vue'

interface Props {
  usuarios: User[]
  currentUserId?: number
  disabledDelete?: boolean
}

withDefaults(defineProps<Props>(), {
  currentUserId: undefined,
  disabledDelete: false
})

defineEmits<{
  edit: [user: User]
  'reset-password': [user: User]
  'view-permisos': [userId: number]
  'view-tenant-profile': [userId: number]
  delete: [user: User]
}>()
</script>

<style scoped>
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

