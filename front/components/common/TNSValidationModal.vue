<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Validar Usuario TNS</h2>
            <button class="close-btn" @click="close">×</button>
          </div>

          <div class="modal-body">
            <p class="info-text">
              Ingresa tus credenciales de TNS para validar permisos y acceder a los módulos disponibles.
            </p>

            <form @submit.prevent="handleSubmit" class="validation-form">
              <div class="form-group">
                <label for="username">Usuario TNS</label>
                <input
                  id="username"
                  v-model="formData.username"
                  type="text"
                  placeholder="Ej: ADMIN"
                  required
                  class="form-input"
                  :disabled="loading"
                />
              </div>

              <div class="form-group">
                <label for="password">Contraseña</label>
                <input
                  id="password"
                  v-model="formData.password"
                  type="password"
                  placeholder="Ingresa tu contraseña"
                  required
                  class="form-input"
                  :disabled="loading"
                />
              </div>

              <div v-if="error" class="error-message">
                {{ error }}
              </div>

              <div v-if="success && validationData" class="success-section">
                <div class="success-header">
                  <span class="success-icon">✓</span>
                  <h3>Usuario Validado</h3>
                </div>
                <div class="permissions-info">
                  <p><strong>Usuario:</strong> {{ validationData.VALIDATE?.OUSERNAME || formData.username }}</p>
                  <div v-if="validationData.MODULOS && Object.keys(validationData.MODULOS).length > 0">
                    <p class="modules-title">Módulos Disponibles:</p>
                    <div class="modules-list">
                      <span
                        v-for="(value, key) in validationData.MODULOS"
                        :key="key"
                        class="module-badge"
                        :class="{ 'module-enabled': value }"
                      >
                        {{ key }}: {{ value ? '✓' : '✗' }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </form>
          </div>

          <div class="modal-actions">
            <button class="btn-cancel" @click="close" :disabled="loading">
              Cancelar
            </button>
            <button
              class="btn-confirm"
              @click="handleSubmit"
              :disabled="loading || !canSubmit"
            >
              <span v-if="loading" class="spinner"></span>
              <span v-else>{{ success ? 'Continuar' : 'Validar' }}</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
interface Props {
  empresaServidorId: number
  isOpen: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'validated', data: any): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const session = useSessionStore()
const api = useApiClient()

const formData = ref({
  username: '',
  password: ''
})

const loading = ref(false)
const error = ref<string | null>(null)
const success = ref(false)
const validationData = ref<any>(null)

const canSubmit = computed(() => {
  return formData.value.username.trim() !== '' && formData.value.password.trim() !== ''
})

const close = () => {
  emit('close')
  resetForm()
}

const resetForm = () => {
  formData.value = { username: '', password: '' }
  error.value = null
  success.value = false
  validationData.value = null
}

const handleSubmit = async () => {
  if (success.value) {
    // Si ya está validado, continuar
    emit('validated', validationData.value)
    close()
    return
  }

  if (!canSubmit.value) return

  loading.value = true
  error.value = null

  try {
    const response = await api.post('/api/tns/validate_user/', {
      empresa_servidor_id: props.empresaServidorId,
      username: formData.value.username.toUpperCase(),
      password: formData.value.password
    })

    // Verificar OSUCCESS - puede ser "0", "1", "true", "false", etc.
    const oSuccess = response.VALIDATE?.OSUCCESS
    const isSuccess = oSuccess === "1" || oSuccess === 1 || 
                      String(oSuccess).toLowerCase() === "true" ||
                      String(oSuccess).toLowerCase() === "si" ||
                      String(oSuccess).toLowerCase() === "yes"

    if (!isSuccess) {
      // Mostrar error con SweetAlert
      const mensaje = response.VALIDATE?.OMENSAJE || 
                     response.VALIDATE?.MENSAJE || 
                     'Usuario o contraseña no válidos'
      
      // Limpiar validación fallida previa del sessionStorage
      const storageKey = `tns_validation_${props.empresaServidorId}_${session.user?.id}`
      if (process.client) {
        sessionStorage.removeItem(storageKey)
      }
      
      if (process.client) {
        const Swal = (await import('sweetalert2')).default
        await Swal.fire({
          icon: 'error',
          title: 'Error de validación',
          text: mensaje,
          confirmButtonText: 'Aceptar',
          confirmButtonColor: '#2563eb',
          // Asegurar que esté por encima del modal
          customClass: {
            container: 'swal-z-index-fix'
          }
        })
      }
      
      error.value = mensaje
      validationData.value = null
      success.value = false
      // Limpiar validación del session store también
      session.setTNSValidation(null)
      return
    }

    // Si OSUCCESS es "1", guardar la validación
    validationData.value = response
    success.value = true

    // Guardar en storage: empresa_añofiscal_user
    const storageKey = `tns_validation_${props.empresaServidorId}_${session.user?.id}`
    const storageData = {
      empresa_servidor_id: props.empresaServidorId,
      username: formData.value.username.toUpperCase(),
      validation: response.VALIDATE,
      modulos: response.MODULOS,
      // Guardar ruta_base si viene en la validación
      ruta_base: response.VALIDATE?.RUTA_BASE || response.VALIDATE?.ruta_base || null,
      timestamp: new Date().toISOString()
    }
    
    if (process.client) {
      sessionStorage.setItem(storageKey, JSON.stringify(storageData))
    }

    // Guardar en session store
    session.setTNSValidation(storageData)

    // Mostrar SweetAlert de éxito
    if (process.client) {
      const Swal = (await import('sweetalert2')).default
      await Swal.fire({
        icon: 'success',
        title: 'Validación exitosa',
        text: response.VALIDATE?.OMENSAJE?.replace(/'/g, '') || 'Inicio de sesión exitoso',
        confirmButtonText: 'Continuar',
        confirmButtonColor: '#2563eb',
        allowOutsideClick: false,
        allowEscapeKey: false,
        // Asegurar que esté por encima del modal
        customClass: {
          container: 'swal-z-index-fix'
        }
      })
      
      // Cerrar modal y emitir evento de validación exitosa
      emit('validated', storageData)
      close()
    }
  } catch (err: any) {
    // Error de red o del servidor
    const errorMessage = err?.data?.error || err?.data?.detail || 'Error al validar usuario TNS'
    
    if (process.client) {
      const Swal = (await import('sweetalert2')).default
      await Swal.fire({
        icon: 'error',
        title: 'Error de conexión',
        text: errorMessage,
        confirmButtonText: 'Aceptar',
        confirmButtonColor: '#2563eb',
        // Asegurar que esté por encima del modal
        customClass: {
          container: 'swal-z-index-fix'
        }
      })
    }
    
    error.value = errorMessage
    console.error('Error validando usuario TNS:', err)
  } finally {
    loading.value = false
  }
}

// Cargar validación guardada si existe
watch(() => props.isOpen, (open) => {
  if (open) {
    const storageKey = `tns_validation_${props.empresaServidorId}_${session.user?.id}`
    if (process.client) {
      const stored = sessionStorage.getItem(storageKey)
      if (stored) {
        try {
          const data = JSON.parse(stored)
          
          // Verificar que la validación fue exitosa
          const oSuccess = data.validation?.OSUCCESS
          const isSuccess = oSuccess === "1" || oSuccess === 1 || 
                            String(oSuccess).toLowerCase() === "true" ||
                            String(oSuccess).toLowerCase() === "si" ||
                            String(oSuccess).toLowerCase() === "yes"
          
          if (!isSuccess) {
            // Si la validación guardada falló, no cargarla
            console.warn('Validación guardada falló anteriormente, no se carga')
            return
          }
          
          // Verificar que no sea muy antigua (ej: menos de 24 horas)
          const timestamp = new Date(data.timestamp)
          const now = new Date()
          const hoursDiff = (now.getTime() - timestamp.getTime()) / (1000 * 60 * 60)
          
          if (hoursDiff < 24) {
            validationData.value = {
              VALIDATE: data.validation,
              MODULOS: data.modulos
            }
            formData.value.username = data.username
            success.value = true
          }
        } catch (e) {
          console.error('Error cargando validación guardada:', e)
        }
      }
    }
  }
})
</script>

<style scoped>
.modal-overlay {
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

.modal-content {
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

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 2rem;
  color: #6b7280;
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  transition: background 0.2s;
}

.close-btn:hover {
  background: #f3f4f6;
}

.modal-body {
  padding: 1.5rem;
  flex: 1;
  overflow-y: auto;
}

.info-text {
  color: #6b7280;
  font-size: 0.95rem;
  margin-bottom: 1.5rem;
  line-height: 1.6;
}

.validation-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  font-size: 1rem;
  transition: all 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-input:disabled {
  background: #f3f4f6;
  cursor: not-allowed;
}

.error-message {
  padding: 0.75rem;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  color: #991b1b;
  font-size: 0.875rem;
}

.success-section {
  padding: 1rem;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 0.5rem;
  margin-top: 1rem;
}

.success-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.success-icon {
  width: 24px;
  height: 24px;
  background: #10b981;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.875rem;
}

.success-header h3 {
  margin: 0;
  color: #065f46;
  font-size: 1rem;
  font-weight: 600;
}

.permissions-info {
  color: #374151;
  font-size: 0.875rem;
}

.permissions-info p {
  margin: 0.5rem 0;
}

.modules-title {
  font-weight: 600;
  margin-top: 0.75rem !important;
  margin-bottom: 0.5rem !important;
}

.modules-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.module-badge {
  padding: 0.375rem 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  background: #f3f4f6;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

.module-badge.module-enabled {
  background: #dbeafe;
  color: #1e40af;
  border-color: #93c5fd;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  border-top: 1px solid #e5e7eb;
  justify-content: flex-end;
}

.btn-cancel,
.btn-confirm {
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-cancel {
  background: white;
  border: 1px solid #d1d5db;
  color: #374151;
}

.btn-cancel:hover:not(:disabled) {
  background: #f9fafb;
}

.btn-confirm {
  background: #2563eb;
  color: white;
  border: none;
}

.btn-confirm:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-confirm:disabled,
.btn-cancel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
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

