<template>
  <SectionCard
    title="Scraping DIAN"
    kicker="Automatización"
    description="Monitorea las sesiones recientes y lanza nuevas extracciones cuando lo necesites."
    icon="📄"
  >
    <div class="scraping-grid">
      <div class="stat-card">
        <p class="stat-label">Sesiones registradas</p>
        <strong>{{ sessions.length }}</strong>
      </div>
      <div class="stat-card">
        <p class="stat-label">En curso</p>
        <strong>{{ runningSessions }}</strong>
      </div>
      <div class="stat-card">
        <p class="stat-label">Última ejecución</p>
        <strong>{{ lastExecuted }}</strong>
      </div>
    </div>

    <div class="table-wrapper" v-if="sessions.length">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>NIT</th>
            <th>Tipo</th>
            <th>Estado</th>
            <th>Desde</th>
            <th>Hasta</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="session in sessions" :key="session.id">
            <td>#{{ session.id }}</td>
            <td>{{ session.nit }}</td>
            <td>{{ session.tipo }}</td>
            <td>
              <span :class="['status-pill', session.status]">
                {{ session.status }}
              </span>
            </td>
            <td>{{ formatDate(session.ejecutado_desde) }}</td>
            <td>{{ formatDate(session.ejecutado_hasta) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="error" class="error-banner">
      {{ error }}
    </div>

    <template #footer>
      <div class="footer-actions">
        <button class="ghost" @click="fetchSessions" :disabled="loading">
          {{ loading ? 'Actualizando...' : 'Actualizar' }}
        </button>
        <NuxtLink to="/dian" class="primary-link">
          Crear sesión rápida →
        </NuxtLink>
      </div>
    </template>
  </SectionCard>
</template>

<script setup lang="ts">
type ScrapingSession = {
  id: number
  nit: string
  tipo: string
  status: string
  ejecutado_desde?: string
  ejecutado_hasta?: string
}

const api = useApiClient()
const config = useRuntimeConfig()

const sessions = ref<ScrapingSession[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const backendEnabled = computed(() => config.public.enableBackend)

const fallbackSessions: ScrapingSession[] = [
  {
    id: 101,
    nit: '900123456',
    tipo: 'Sent',
    status: 'completed',
    ejecutado_desde: '2025-01-01',
    ejecutado_hasta: '2025-01-31'
  },
  {
    id: 102,
    nit: '900654321',
    tipo: 'Received',
    status: 'running',
    ejecutado_desde: '2025-02-01',
    ejecutado_hasta: '2025-02-28'
  }
]

const fetchSessions = async () => {
  loading.value = true
  error.value = null
  try {
    if (!backendEnabled.value) {
      sessions.value = fallbackSessions
      return
    }
    const response = await api.get<any>('/dian/api/sessions/', {
      page_size: 5
    })
    if (Array.isArray(response)) {
      sessions.value = response
    } else if (Array.isArray(response?.results)) {
      sessions.value = response.results
    } else {
      sessions.value = fallbackSessions
    }
  } catch (err: any) {
    error.value =
      err?.data?.detail || 'No se pudieron cargar las sesiones recientes'
    console.error('ScrapingSummary error', err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchSessions)

const runningSessions = computed(() => {
  return sessions.value.filter((session) => session.status === 'running').length
})

const lastExecuted = computed(() => {
  if (!sessions.value.length) return 'N/A'
  const [first] = sessions.value
  return formatDate(first.ejecutado_hasta || first.ejecutado_desde)
})

const formatDate = (value?: string) => {
  if (!value) return 'Pendiente'
  try {
    return new Date(value).toLocaleDateString()
  } catch {
    return value
  }
}
</script>

<style scoped>
.scraping-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 1rem;
}

.stat-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: 0.35rem;
}

.table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  text-align: left;
  padding: 0.75rem;
  border-bottom: 1px solid var(--border-color);
}

th {
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.06em;
  color: var(--text-secondary);
}

.status-pill {
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.8rem;
  text-transform: capitalize;
}

.status-pill.completed {
  background: #dcfce7;
  color: #166534;
}

.status-pill.running {
  background: #fef9c3;
  color: #854d0e;
}

.status-pill.error {
  background: #fee2e2;
  color: #991b1b;
}

.error-banner {
  padding: 0.75rem;
  border-radius: var(--border-radius);
  background: #fee2e2;
  color: #991b1b;
}

.footer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.ghost {
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 0.5rem 1rem;
  background: transparent;
  cursor: pointer;
}

.primary-link {
  font-weight: 600;
  color: var(--primary-color);
}
</style>
