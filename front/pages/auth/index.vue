<template>
  <div class="auth-page">
    <SectionCard
      title="Iniciar sesión"
      kicker="Autenticación"
      description="Combina credenciales JWT y API keys para controlar el acceso."
      icon="🔐"
    >
      <form class="form-grid" @submit.prevent="handleLogin">
        <label>
          Usuario
          <input v-model="loginForm.username" placeholder="admin" required />
        </label>
        <label>
          Contraseña
          <input
            v-model="loginForm.password"
            type="password"
            placeholder="********"
            required
          />
        </label>
        <label>
          API Key (opcional)
          <input
            v-model="loginForm.apiKey"
            placeholder="tns_xxx..."
            autocomplete="off"
          />
        </label>
        <button type="submit" :disabled="session.loading.value">
          {{ session.loading.value ? 'Validando...' : 'Ingresar' }}
        </button>
      </form>

      <p v-if="session.lastError.value" class="error-banner">
        {{ session.lastError.value }}
      </p>
      <p v-else-if="loginFinished" class="success-banner">
        Sesión iniciada. Ahora puedes elegir tu empresa o ir al
        <NuxtLink to="/">dashboard</NuxtLink>.
      </p>

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
    </SectionCard>

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
            :disabled="session.loading.value"
          >
            {{ session.loading.value ? 'Validando...' : 'Usar API Key guardada' }}
          </button>
          <hr />
          <p class="or-text">O ingresa una nueva:</p>
        </div>
        <form @submit.prevent="() => handleApiKeyLogin()">
          <label>
            API Key
            <input
              v-model="apiKeyForm.apiKey"
              type="password"
              placeholder="sk_..."
              required
            />
          </label>
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
              :disabled="session.loading.value"
            >
              {{ session.loading.value ? 'Validando...' : 'Ingresar' }}
            </button>
          </div>
        </form>
        <p v-if="session.lastError.value" class="error-text">
          {{ session.lastError.value }}
        </p>
      </div>
    </div>

    <SectionCard
      title="Empresas disponibles"
      kicker="Discovery"
      description="Selecciona la empresa preferida o consulta la base ADMIN.gdb."
      icon="🏢"
    >
      <div class="empresa-block">
        <div class="empresa-header">
          <h3>Asignadas al usuario</h3>
          <p v-if="!session.empresas.value.length" class="muted">
            Inicia sesión para cargar tus empresas asociadas.
          </p>
        </div>

        <div v-if="session.empresas.value.length" class="empresa-list">
          <button
            v-for="empresa in session.empresas.value"
            :key="empresa.empresaServidorId"
            class="empresa-item"
            @click="session.selectEmpresa(empresa)"
          >
            <div>
              <strong>{{ empresa.nombre }}</strong>
              <p>{{ empresa.nit }} · Año {{ empresa.anioFiscal || 'N/A' }}</p>
              <small v-if="empresa.preferredTemplate">
                Plantilla: {{ empresa.preferredTemplate }}
              </small>
            </div>
            <span
              v-if="
                session.selectedEmpresa.value?.empresaServidorId ===
                empresa.empresaServidorId
              "
            >
              ✓
            </span>
          </button>
        </div>
      </div>

      <hr />

      <form class="form-grid" @submit.prevent="handleAdminLookup">
        <label>
          Empresa servidor ID
          <input
            v-model.number="adminForm.empresaServidorId"
            type="number"
            min="1"
          />
        </label>
        <label>
          NIT servidor (opcional)
          <input v-model="adminForm.nit" placeholder="900123456" />
        </label>
        <label>
          Año fiscal (opcional)
          <input
            v-model.number="adminForm.anioFiscal"
            type="number"
            min="2000"
          />
        </label>
        <label>
          NIT a buscar
          <input v-model="adminForm.searchNit" placeholder="900123456" />
        </label>
        <button type="submit" :disabled="session.loading.value">
          {{ session.loading.value ? 'Buscando...' : 'Consultar ADMIN' }}
        </button>
      </form>

      <div v-if="session.adminEmpresas.value.length" class="empresa-block">
        <div class="empresa-header">
          <h3>Resultados ADMIN.gdb</h3>
          <p class="muted">Selecciona uno para usarlo en los paneles.</p>
        </div>
        <div class="empresa-list">
          <div
            v-for="empresa in session.adminEmpresas.value"
            :key="`${empresa.CODIGO}-${empresa.NIT}`"
            class="empresa-item readonly"
          >
            <div>
              <strong>{{ empresa.NOMBRE }}</strong>
              <p>{{ empresa.NIT }} · Año {{ empresa.ANOFIS || 'N/A' }}</p>
              <small v-if="empresa.CODIGO">Código: {{ empresa.CODIGO }}</small>
            </div>
            <span class="muted">Referencia</span>
          </div>
        </div>
      </div>
    </SectionCard>

    <SectionCard
      title="Validar usuario en TNS"
      kicker="Control de acceso"
      description="Ejecuta el procedimiento TNS_WS_VERIFICAR_USUARIO y revisa permisos."
      icon="🧪"
    >
      <form class="form-grid" @submit.prevent="handleValidation">
        <label>
          Empresa servidor ID
          <input
            v-model.number="validationForm.empresa_servidor_id"
            type="number"
            min="1"
          />
        </label>
        <label>
          Usuario TNS
          <input v-model="validationForm.username" required />
        </label>
        <label>
          Contraseña TNS
          <input
            v-model="validationForm.password"
            type="password"
            required
          />
        </label>
        <button type="submit" :disabled="session.loading.value">
          {{ session.loading.value ? 'Consultando...' : 'Validar' }}
        </button>
      </form>

      <div v-if="session.validation.value" class="validation-result">
        <h4>Resultado</h4>
        <pre>{{ session.validation.value.VALIDATE || session.validation.value.validation || session.validation.value }}</pre>
      </div>
    </SectionCard>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'default'
})

const session = useSessionStore()
const loginFinished = ref(false)
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
    session.lastError.value = 'Por favor ingresa una API Key'
    return
  }

  try {
    console.log('[login] Enviando API Key:', apiKey.substring(0, 10) + '...')
    await session.loginWithApiKey(apiKey)
    storedApiKey.value = apiKey
    showApiKeyModal.value = false
    
    // Si hay empresas, el modal se abrirá automáticamente
    // Esperar a que se seleccione empresa y luego redirigir
    if (session.empresas.value.length > 0) {
      // Watch para redirigir cuando se seleccione empresa
      const stopWatcher = watch(() => session.selectedEmpresa.value, (empresa) => {
        if (empresa) {
          stopWatcher() // Detener el watcher
          navigateTo('/subdomain/retail')
        }
      })
    } else {
      // Si no hay empresas, redirigir directamente
      navigateTo('/subdomain/retail')
    }
  } catch (error) {
    console.error('Error en login con API Key:', error)
  }
}

const loginForm = reactive({
  username: '',
  password: '',
  apiKey: ''
})

const adminForm = reactive({
  empresaServidorId: 1,
  nit: '',
  anioFiscal: new Date().getFullYear(),
  searchNit: ''
})

const validationForm = reactive({
  empresa_servidor_id: 1,
  username: '',
  password: ''
})

const handleLogin = async () => {
  if (loginForm.apiKey) {
    session.setApiKey(loginForm.apiKey)
  }
  try {
    await session.login({
      username: loginForm.username,
      password: loginForm.password
    })
    loginFinished.value = true
  } catch (error) {
    console.warn('Login failed', error)
  }
}

const handleAdminLookup = async () => {
  if (!adminForm.searchNit) return
  await session.fetchEmpresas({
    empresaServidorId: adminForm.empresaServidorId,
    nit: adminForm.nit,
    anioFiscal: adminForm.anioFiscal,
    searchNit: adminForm.searchNit
  })
}

const handleValidation = async () => {
  const payload = { ...validationForm }
  if (session.selectedEmpresa.value?.empresaServidorId) {
    payload.empresa_servidor_id =
      session.selectedEmpresa.value.empresaServidorId
  }
  await session.validateTNSUser(payload)
}
</script>

<style scoped>
.auth-page {
  display: grid;
  gap: 1.5rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
}

label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.85rem;
}

input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
}

button {
  border: none;
  border-radius: var(--border-radius);
  padding: 0.6rem 1rem;
  background: var(--primary-color);
  color: #fff;
  cursor: pointer;
}

.empresa-block {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.empresa-header {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.muted {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.empresa-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.empresa-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 0.75rem;
  background: var(--bg-secondary);
  cursor: pointer;
}

.empresa-item.readonly {
  cursor: default;
  opacity: 0.85;
}

.error-banner {
  padding: 0.75rem;
  background: rgba(239, 68, 68, 0.15);
  color: #fecaca;
  border-radius: var(--border-radius);
}

.success-banner {
  margin-top: 0.5rem;
  padding: 0.75rem;
  border-radius: var(--border-radius);
  background: rgba(34, 197, 94, 0.15);
  color: #86efac;
}

.validation-result {
  border: 1px dashed var(--border-color);
  border-radius: var(--border-radius);
  padding: 1rem;
}

pre {
  white-space: pre-wrap;
  margin-top: 0.5rem;
}

hr {
  border: none;
  border-top: 1px solid var(--border-color);
  margin: 1.5rem 0;
}

.api-key-link {
  margin-top: 1rem;
  text-align: center;
}

.api-key-link {
  margin-top: 1rem;
  text-align: center;
  padding: 0.5rem;
}

.api-key-btn {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #3b82f6;
  font-size: 0.9rem;
  padding: 0.6rem 1.2rem;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
  font-weight: 500;
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
  background: var(--bg-primary);
  border-radius: var(--border-radius);
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content h3 {
  margin: 0 0 1.5rem 0;
}

.stored-key-section {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border-radius: var(--border-radius);
}

.stored-key-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
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
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9rem;
}

.btn-small {
  padding: 0.4rem 0.8rem;
  font-size: 0.85rem;
}

.btn-danger {
  background: #ef4444;
  color: white;
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  margin-top: 1rem;
}

.or-text {
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin: 1rem 0;
}

.error-text {
  color: #ef4444;
  font-size: 0.85rem;
  margin-top: 1rem;
}
</style>
