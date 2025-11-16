<template>
  <div class="dashboard">
    <section class="hero">
      <div class="hero-content">
        <p class="kicker">Bienvenido</p>
        <h1>{{ companyName }}</h1>
        <p class="hero-subtitle">{{ tenant.preferences.value.tagline }}</p>
        <div class="hero-actions">
          <NuxtLink class="primary" to="/auth">Configurar acceso</NuxtLink>
          <NuxtLink class="ghost" to="/assistant">Abrir asistente</NuxtLink>
          <button
            v-if="!hasEmpresa"
            class="outline"
            type="button"
            @click="session.openEmpresaModal()"
          >
            Elegir empresa
          </button>
        </div>
        <p v-if="!hasEmpresa" class="hero-warning">
          Debes seleccionar una empresa y año fiscal antes de continuar.
        </p>
      </div>
      <div class="hero-visual">
        <div class="shape shape-one"></div>
        <div class="shape shape-two"></div>
        <svg viewBox="0 0 200 200" class="hero-svg" aria-hidden="true">
          <path
            d="M52.3,-64.8C66.4,-55.1,77,-38.1,80,-20.1C83, -2.1, 78.6, 17, 68.3, 32.8C58.1, 48.7, 42, 61.5, 23.5, 67.7C5, 73.9, -15.7, 73.4, -33.9, 66.1C-52.1, 58.9, -67.8, 44.9, -74.2, 27.2C-80.6, 9.5, -77.8, -11.9, -69.1, -29.3C-60.3, -46.7, -45.7, -60.1, -29.1, -69.1C-12.4, -78.1, 6.3, -82.7, 23.2, -78.5C40.1, -74.3, 54.2, -61.5, 52.3, -64.8Z"
            fill="url(#heroGradient)"
            transform="translate(100 100)"
          />
          <defs>
            <linearGradient id="heroGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#38bdf8" />
              <stop offset="100%" stop-color="#8b5cf6" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </section>

    <section class="metrics">
      <div class="metric-card">
        <p>Modo activo</p>
        <strong>{{ currentModeLabel }}</strong>
      </div>
      <div class="metric-card">
        <p>Empresa seleccionada</p>
        <strong>{{ selectedEmpresaName }}</strong>
        <button v-if="!hasEmpresa" class="mini-btn" @click="session.openEmpresaModal()">
          Seleccionar
        </button>
      </div>
      <div class="metric-card">
        <p>Autenticado</p>
        <strong>{{ session.isAuthenticated.value ? 'Sí' : 'No' }}</strong>
      </div>
    </section>

    <div class="panels-grid">
      <ScrapingSummary />
      <MachineLearningPanel />
      <TnsBridgePanel />
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'default'
})

const tenant = useTenantStore()
const { companyName, currentMode } = useCompany()
const session = useSessionStore()

const currentModeLabel = computed(() => {
  const labels: Record<string, string> = {
    pro: 'Profesional',
    pos: 'Punto de venta',
    ecommerce: 'E-commerce',
    autopago: 'Autopago'
  }
  return labels[currentMode.value] || 'General'
})

const selectedEmpresaName = computed(() => {
  const empresa = session.selectedEmpresa.value
  if (!empresa) return 'Pendiente'
  return `${empresa.nombre} · ${empresa.anioFiscal}`
})

const hasEmpresa = computed(() => Boolean(session.selectedEmpresa.value))
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.hero {
  position: relative;
  overflow: hidden;
  border-radius: 32px;
  border: 1px solid var(--border-color);
  padding: 2rem;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.35), rgba(15, 23, 42, 0.85));
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 2rem;
}

.hero-content {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.hero-subtitle {
  color: var(--text-secondary);
  font-size: 1rem;
}

.hero-visual {
  position: relative;
  min-height: 220px;
}

.hero-visual .shape {
  position: absolute;
  border-radius: 24px;
  filter: blur(0.5px);
  opacity: 0.7;
}

.shape-one {
  width: 140px;
  height: 140px;
  background: rgba(59, 130, 246, 0.3);
  top: 10%;
  left: 5%;
  transform: rotate(-12deg);
}

.shape-two {
  width: 180px;
  height: 120px;
  background: rgba(147, 51, 234, 0.25);
  bottom: 12%;
  right: 8%;
  transform: rotate(18deg);
}

.hero-svg {
  position: absolute;
  width: 220px;
  height: 220px;
  top: 10%;
  left: 20%;
  opacity: 0.9;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.hero-warning {
  margin-top: 0.5rem;
  color: #fcd34d;
  font-size: 0.9rem;
}

.primary,
.ghost,
.outline {
  padding: 0.6rem 1.2rem;
  border-radius: var(--border-radius);
  font-weight: 600;
}

.primary {
  background: var(--primary-color);
  color: #fff;
}

.ghost {
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.outline {
  border: 1px solid var(--primary-color);
  background: transparent;
  color: var(--primary-color);
}

.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.metric-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 1rem;
}

.metric-card p {
  margin-bottom: 0.25rem;
  color: var(--text-secondary);
}

.panels-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1rem;
}

.mini-btn {
  margin-top: 0.5rem;
  padding: 0.35rem 0.8rem;
  border-radius: 999px;
  border: 1px solid var(--primary-color);
  background: transparent;
  color: var(--primary-color);
  font-size: 0.8rem;
}

@media (max-width: 768px) {
  .hero {
    grid-template-columns: 1fr;
  }
  .hero-visual {
    min-height: 180px;
  }
}
</style>
