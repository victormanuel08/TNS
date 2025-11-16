<template>
  <SectionCard
    title="Modelos de Machine Learning"
    kicker="Analítica"
    description="Entrena y consulta predicciones directamente desde el panel."
    icon="🤖"
  >
    <div class="panels">
      <form class="form-card" @submit.prevent="trainModels">
        <h3>Entrenar modelos</h3>
        <label>
          Empresa servidor ID
          <input
            v-model="trainPayload.empresa_servidor_id"
            type="number"
            min="1"
            required
          />
        </label>
        <div class="grid-2">
          <label>
            Fecha inicio
            <input v-model="trainPayload.fecha_inicio" type="date" required />
          </label>
          <label>
            Fecha fin
            <input v-model="trainPayload.fecha_fin" type="date" required />
          </label>
        </div>
        <button type="submit" :disabled="training">
          {{ training ? 'Entrenando...' : 'Entrenar' }}
        </button>
      </form>

      <form class="form-card" @submit.prevent="predictDemand">
        <h3>Predecir demanda</h3>
        <label>
          Modelo ID
          <input v-model="predictPayload.modelo_id" required />
        </label>
        <label>
          Meses
          <input
            v-model.number="predictPayload.meses"
            type="number"
            min="1"
            max="24"
          />
        </label>
        <button type="submit" :disabled="predicting">
          {{ predicting ? 'Calculando...' : 'Predecir' }}
        </button>
      </form>
    </div>

    <div v-if="resultMessage" class="result-banner">
      {{ resultMessage }}
    </div>

    <template #footer>
      <div class="footer-actions">
        <span>Historial rápido</span>
        <ul>
          <li v-for="log in lastLogs" :key="log">{{ log }}</li>
        </ul>
      </div>
    </template>
  </SectionCard>
</template>

<script setup lang="ts">
const api = useApiClient()
const config = useRuntimeConfig()

const trainPayload = reactive({
  empresa_servidor_id: 1,
  fecha_inicio: new Date().toISOString().substring(0, 10),
  fecha_fin: new Date().toISOString().substring(0, 10)
})

const predictPayload = reactive({
  modelo_id: 'empresa_900123456',
  meses: 6
})

const training = ref(false)
const predicting = ref(false)
const resultMessage = ref('')
const lastLogs = ref<string[]>([
  'Modelo empresa_900123456 entrenado 12/02',
  'Recomendación generada 11/30'
])

const backendEnabled = computed(() => config.public.enableBackend)

const trainModels = async () => {
  training.value = true
  resultMessage.value = ''
  try {
    if (!backendEnabled.value) {
      resultMessage.value = 'Modo demo: entrenamiento simulado'
      return
    }
    const response = await api.post<{ estado?: string }>(
      '/assistant/api/ml/entrenar_modelos/',
      trainPayload
    )
    resultMessage.value = response?.estado
      ? `ML: ${response.estado}`
      : 'Entrenamiento completado'
  } catch (error: any) {
    resultMessage.value =
      error?.data?.detail || 'Error entrenando los modelos'
  } finally {
    training.value = false
  }
}

const predictDemand = async () => {
  predicting.value = true
  resultMessage.value = ''
  try {
    if (!backendEnabled.value) {
      resultMessage.value = 'Modo demo: predicción simulada'
      return
    }
    const response = await api.post<{ forecast?: any }>(
      '/assistant/api/ml/predecir_demanda/',
      predictPayload
    )
    resultMessage.value = response?.forecast
      ? 'Predicciones generadas correctamente'
      : 'Proceso completado'
  } catch (error: any) {
    resultMessage.value =
      error?.data?.detail || 'Error solicitando predicción'
  } finally {
    predicting.value = false
  }
}
</script>

<style scoped>
.panels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
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
button {
  border-radius: var(--border-radius);
  border: 1px solid var(--border-color);
  padding: 0.5rem 0.75rem;
}

button {
  background: var(--primary-color);
  color: #fff;
  border: none;
  cursor: pointer;
}

.grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
}

.result-banner {
  padding: 0.75rem;
  border-radius: var(--border-radius);
  background: var(--bg-secondary);
}

.footer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

ul {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
}
</style>
