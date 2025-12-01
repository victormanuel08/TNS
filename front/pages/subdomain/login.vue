<template>
  <div class="picasso-login">
    <!-- Panel Visual (izquierda) -->
    <div class="visual-panel">
      <div class="artwork">
        <div class="shape shape-1"></div>
        <div class="shape shape-2"></div>
        <div class="shape shape-3"></div>
        <div class="gradient-overlay"></div>
      </div>
      <div class="visual-content">
        <h1>{{ subdomain }}</h1>
        <p>Bienvenido a tu espacio de trabajo</p>
      </div>
    </div>

    <!-- Panel de Login (derecha) -->
    <div class="login-panel">
      <div class="login-content">
        <h2>Iniciar Sesión</h2>
        <form @submit.prevent="handleLogin">
          <div class="form-group">
            <label>Usuario</label>
            <input 
              v-model="form.username" 
              type="text" 
              placeholder="usuario"
              required
            />
          </div>
          <div class="form-group">
            <label>Contraseña</label>
            <input 
              v-model="form.password" 
              type="password" 
              placeholder="********"
              required
            />
          </div>
          <button type="submit" :disabled="loading">
            {{ loading ? 'Validando...' : 'Entrar' }}
          </button>
          <p v-if="error" class="error">{{ error }}</p>
        </form>

        <!-- Botón discreto para login con API Key -->
        <div class="api-key-link">
          <button 
            type="button" 
            class="api-key-btn"
            @click="showApiKeyModal = true"
          >
            🔑 Login con API Key
          </button>
        </div>
      </div>
    </div>

    <!-- Modal API Key -->
    <div v-if="showApiKeyModal" class="modal-overlay" @click="showApiKeyModal = false">
      <div class="modal-content" @click.stop>
        <h3>Login con API Key</h3>
        <div v-if="storedApiKey" class="stored-key-section">
          <p class="stored-key-label">API Key guardada:</p>
          <div class="stored-key-display">
            <code>{{ maskedApiKey }}</code>
            <button 
              type="button" 
              class="btn-small btn-danger"
              @click="clearStoredApiKey"
            >
              🗑️ Borrar
            </button>
          </div>
          <button 
            type="button" 
            class="btn-primary"
            @click="useStoredApiKey"
            :disabled="loading"
          >
            {{ loading ? 'Validando...' : 'Usar API Key guardada' }}
          </button>
          <hr />
          <p class="or-text">O ingresa una nueva:</p>
        </div>
        <form @submit.prevent="() => handleApiKeyLogin()">
          <div class="form-group">
            <label>API Key</label>
            <input
              v-model="apiKeyForm.apiKey"
              type="password"
              placeholder="sk_..."
              required
            />
          </div>
          <div class="modal-actions">
            <button 
              type="button" 
              class="btn-secondary"
              @click="showApiKeyModal = false"
            >
              Cancelar
            </button>
            <button 
              type="submit" 
              class="btn-primary"
              :disabled="loading"
            >
              {{ loading ? 'Validando...' : 'Ingresar' }}
            </button>
          </div>
        </form>
        <p v-if="error" class="error-text">
          {{ error }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: false,
  middleware: 'subdomain'
})

const { getSubdomain } = useSubdomain()
const session = useSessionStore()
const subdomain = computed(() => getSubdomain() || 'empresa')

const form = reactive({
  username: '',
  password: ''
})
const loading = ref(false)
const error = ref<string | null>(null)
const showApiKeyModal = ref(false)
const storedApiKey = ref<string | null>(null)

// Cargar API Key guardada al montar
onMounted(() => {
  storedApiKey.value = session.getStoredApiKey()
})

const maskedApiKey = computed(() => {
  if (!storedApiKey.value) return ''
  const key = storedApiKey.value
  if (key.length <= 8) return '***'
  return key.substring(0, 4) + '***' + key.substring(key.length - 4)
})

const apiKeyForm = reactive({
  apiKey: ''
})

const clearStoredApiKey = () => {
  session.setApiKey(null)
  storedApiKey.value = null
  apiKeyForm.apiKey = ''
}

const useStoredApiKey = async () => {
  if (!storedApiKey.value) return
  await handleApiKeyLogin(storedApiKey.value)
}

const handleApiKeyLogin = async (apiKeyValue?: string) => {
  // Asegurar que no recibimos un evento
  if (apiKeyValue && typeof apiKeyValue !== 'string') {
    console.warn('handleApiKeyLogin recibió un valor no string:', apiKeyValue)
    apiKeyValue = undefined
  }
  
  const apiKey = apiKeyValue || apiKeyForm.apiKey.trim()
  if (!apiKey) {
    error.value = 'Por favor ingresa una API Key'
    return
  }

  error.value = null
  loading.value = true
  try {
    console.log('[login] Enviando API Key:', apiKey.substring(0, 10) + '...')
    await session.loginWithApiKey(apiKey)
    storedApiKey.value = apiKey
    showApiKeyModal.value = false
    
    // Si hay empresas, el modal se abrirá automáticamente
    if (session.empresas.value.length > 0) {
      await nextTick()
      session.openEmpresaModal()
      
      // Watch para redirigir cuando se seleccione empresa
      const stopWatcher = watch(() => session.selectedEmpresa.value, (empresa) => {
        if (empresa) {
          stopWatcher()
          navigateTo('/subdomain/retail')
        }
      })
    } else {
      // Si no hay empresas, redirigir directamente
      navigateTo('/subdomain/retail')
    }
  } catch (err: any) {
    error.value = err.message || 'Error al validar API Key'
  } finally {
    loading.value = false
  }
}

const handleLogin = async () => {
  error.value = null
  loading.value = true
  try {
    // Validar que el usuario pertenezca al subdominio
    await session.login({
      username: form.username,
      password: form.password,
      subdomain: subdomain.value
    })
    
    // Después del login, abrir modal de selección de empresa
    await nextTick()
    session.openEmpresaModal()
  } catch (err: any) {
    error.value = err.message || 'Usuario o contraseña incorrectos'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.picasso-login {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.visual-panel {
  position: relative;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.artwork {
  position: absolute;
  inset: 0;
}

.shape {
  position: absolute;
  border-radius: 50%;
  opacity: 0.3;
  animation: float 8s ease-in-out infinite;
}

.shape-1 {
  width: 300px;
  height: 300px;
  background: rgba(255, 255, 255, 0.2);
  top: 10%;
  left: 10%;
  animation-delay: 0s;
}

.shape-2 {
  width: 200px;
  height: 200px;
  background: rgba(255, 255, 255, 0.15);
  bottom: 20%;
  right: 15%;
  animation-delay: 2s;
}

.shape-3 {
  width: 150px;
  height: 150px;
  background: rgba(255, 255, 255, 0.1);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: 4s;
}

.gradient-overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 30% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 50%);
}

.visual-content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: white;
}

.visual-content h1 {
  font-size: 3rem;
  font-weight: 700;
  margin-bottom: 1rem;
  text-transform: capitalize;
}

.visual-content p {
  font-size: 1.25rem;
  opacity: 0.9;
}

.login-panel {
  background: #fafafa;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.login-content {
  width: 100%;
  max-width: 400px;
}

.login-content h2 {
  font-size: 2rem;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #374151;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 0.875rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  font-size: 1rem;
  background: white;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

button {
  width: 100%;
  padding: 0.875rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
}

button:hover:not(:disabled) {
  background: #5568d3;
  transform: translateY(-1px);
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  margin-top: 1rem;
  color: #ef4444;
  text-align: center;
  font-size: 0.875rem;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(5deg);
  }
}

.api-key-link {
  margin-top: 1.5rem;
  text-align: center;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.api-key-btn {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #3b82f6;
  font-size: 0.875rem;
  padding: 0.5rem 1rem;
  cursor: pointer;
  border-radius: 0.5rem;
  transition: all 0.2s;
  font-weight: 500;
  width: auto;
  display: inline-block;
}

.api-key-btn:hover {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.5);
  transform: translateY(-1px);
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 0.5rem;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.modal-content h3 {
  margin: 0 0 1.5rem 0;
  font-size: 1.5rem;
  color: #1f2937;
}

.stored-key-section {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 0.5rem;
}

.stored-key-label {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.stored-key-display {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.stored-key-display code {
  flex: 1;
  padding: 0.5rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.375rem;
  font-family: monospace;
  font-size: 0.875rem;
}

.btn-small {
  padding: 0.4rem 0.8rem;
  font-size: 0.875rem;
}

.btn-danger {
  background: #ef4444;
  color: white;
  border: none;
}

.btn-danger:hover {
  background: #dc2626;
}

.btn-primary {
  width: 100%;
  padding: 0.875rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 0.5rem;
}

.btn-primary:hover:not(:disabled) {
  background: #5568d3;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #e5e7eb;
  padding: 0.875rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  margin-top: 1rem;
}

.or-text {
  text-align: center;
  color: #6b7280;
  font-size: 0.875rem;
  margin: 1rem 0;
}

.error-text {
  color: #ef4444;
  font-size: 0.875rem;
  margin-top: 1rem;
  text-align: center;
}

@media (max-width: 768px) {
  .picasso-login {
    grid-template-columns: 1fr;
  }
  
  .visual-panel {
    min-height: 300px;
  }
  
  .visual-content h1 {
    font-size: 2rem;
  }
}
</style>

