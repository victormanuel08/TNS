<template>
  <SectionCard
    title="Puente TNS"
    kicker="Integración"
    description="Lanza consultas SQL o procedimientos almacenados directamente desde el navegador."
    icon="🛰️"
  >
    <div class="panels">
      <form class="form-card" @submit.prevent="runQuery">
        <h3>Consulta rápida</h3>
        <label>
          Empresa servidor ID
          <input v-model.number="queryPayload.empresa_servidor_id" type="number" min="1" />
        </label>
        <label>
          SQL
          <textarea v-model="queryPayload.sql" rows="4" placeholder="SELECT FIRST 5 * FROM CLIENTES"></textarea>
        </label>
        <label>
          Parámetros (JSON opcional)
          <textarea v-model="queryPayload.paramsText" rows="2" placeholder='["900123456"]'></textarea>
        </label>
        <button type="submit" :disabled="runningQuery">
          {{ runningQuery ? 'Ejecutando...' : 'Ejecutar' }}
        </button>
      </form>

      <form class="form-card" @submit.prevent="runProcedure">
        <h3>Procedimiento almacenado</h3>
        <label>
          Empresa servidor ID
          <input v-model.number="procedurePayload.empresa_servidor_id" type="number" min="1" />
        </label>
        <label>
          Nombre del procedimiento
          <input v-model="procedurePayload.procedure" placeholder="TNS_SP_CLIENTE" />
        </label>
        <label>
          Parámetros (JSON)
          <textarea v-model="procedurePayload.paramsText" rows="4" placeholder='{ "NIT": "900123456" }'></textarea>
        </label>
        <button type="submit" :disabled="runningProcedure">
          {{ runningProcedure ? 'Procesando...' : 'Invocar' }}
        </button>
      </form>
    </div>

    <div v-if="resultRows.length" class="result-table">
      <h4>Resultado</h4>
      <pre>{{ resultRows }}</pre>
    </div>

    <div v-if="panelError" class="error-banner">
      {{ panelError }}
    </div>

    <template #footer>
      <div class="footer-actions">
        <div>
          <p class="muted">Empresa seleccionada</p>
          <strong>{{ selectedEmpresa?.nombre || 'Sin seleccionar' }}</strong>
        </div>
        <NuxtLink to="/auth" class="primary-link">Validar usuario TNS →</NuxtLink>
      </div>
    </template>
  </SectionCard>
</template>

<script setup lang="ts">
const api = useApiClient()
const session = useSessionStore()
const config = useRuntimeConfig()

const backendEnabled = computed(() => config.public.enableBackend)

const queryPayload = reactive({
  empresa_servidor_id: 1,
  sql: '',
  paramsText: ''
})

const procedurePayload = reactive({
  empresa_servidor_id: 1,
  procedure: '',
  paramsText: ''
})

const runningQuery = ref(false)
const runningProcedure = ref(false)
const panelError = ref<string | null>(null)
const resultRows = ref<any>(null)

const selectedEmpresa = computed(() => session.selectedEmpresa.value)

watch(
  () => selectedEmpresa.value?.empresaServidorId,
  (empresaId) => {
    if (empresaId) {
      queryPayload.empresa_servidor_id = empresaId
      procedurePayload.empresa_servidor_id = empresaId
    }
  },
  { immediate: true }
)

const safeParse = (text: string, fallback: any) => {
  if (!text) return fallback
  try {
    return JSON.parse(text)
  } catch {
    return fallback
  }
}

const runQuery = async () => {
  runningQuery.value = true
  panelError.value = null
  resultRows.value = null
  try {
    if (!backendEnabled.value) {
      resultRows.value = [{ mensaje: 'Modo demo, sin conexión real' }]
      return
    }
    const empresaId =
      queryPayload.empresa_servidor_id ||
      selectedEmpresa.value?.empresaServidorId
    if (!empresaId) {
      panelError.value = 'Selecciona una empresa antes de ejecutar consultas'
      return
    }
    const payload = {
      empresa_servidor_id: empresaId,
      sql: queryPayload.sql,
      params: safeParse(queryPayload.paramsText, [])
    }
    resultRows.value = await api.post('/assistant/api/tns/query/', payload)
  } catch (error: any) {
    panelError.value =
      error?.data?.detail || 'No se pudo ejecutar la consulta SQL'
  } finally {
    runningQuery.value = false
  }
}

const runProcedure = async () => {
  runningProcedure.value = true
  panelError.value = null
  resultRows.value = null
  try {
    if (!backendEnabled.value) {
      resultRows.value = [{ mensaje: 'Modo demo, procedimiento simulado' }]
      return
    }
    const empresaId =
      procedurePayload.empresa_servidor_id ||
      selectedEmpresa.value?.empresaServidorId
    if (!empresaId) {
      panelError.value =
        'Selecciona una empresa antes de ejecutar procedimientos'
      return
    }
    const payload = {
      empresa_servidor_id: empresaId,
      procedure: procedurePayload.procedure,
      params: safeParse(procedurePayload.paramsText, {})
    }
    resultRows.value = await api.post(
      '/assistant/api/tns/procedure/',
      payload
    )
  } catch (error: any) {
    panelError.value =
      error?.data?.detail || 'No se pudo ejecutar el procedimiento'
  } finally {
    runningProcedure.value = false
  }
}
</script>

<style scoped>
.panels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.form-card {
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

label {
  font-size: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

input,
textarea {
  border-radius: var(--border-radius);
  border: 1px solid var(--border-color);
  padding: 0.5rem 0.75rem;
  font-family: var(--font-family, 'Inter', sans-serif);
}

textarea {
  resize: vertical;
}

button {
  border-radius: var(--border-radius);
  border: none;
  padding: 0.6rem 1rem;
  background: var(--primary-color);
  color: #fff;
  cursor: pointer;
}

.result-table {
  border: 1px dashed var(--border-color);
  border-radius: var(--border-radius);
  padding: 1rem;
}

pre {
  margin-top: 0.5rem;
  white-space: pre-wrap;
}

.error-banner {
  padding: 0.75rem;
  background: #fee2e2;
  border-radius: var(--border-radius);
  color: #991b1b;
}

.footer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.muted {
  font-size: 0.8rem;
  color: var(--text-secondary);
}
</style>
