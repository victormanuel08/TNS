<template>
  <div :class="layoutClasses" class="pos-layout">
    <header class="pos-header">
      <h1>{{ companyName }}</h1>
      <div class="header-actions">
        <button class="accent">Nueva venta</button>
        <button>Sincronizar</button>
      </div>
    </header>

    <div class="pos-body">
      <aside class="pos-panel">
        <h2>Accesos rapidos</h2>
        <ul>
          <li v-for="item in quickActions" :key="item">{{ item }}</li>
        </ul>
      </aside>

      <main class="pos-main">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
const quickActions = [
  'Cobrar comanda',
  'Abrir caja',
  'Reportes de turno',
  'Entregas pendientes'
]

const { company, companyName } = useCompany()
const { applyThirdStyles } = useThirdStyles()

onMounted(() => {
  applyThirdStyles()
})

const layoutClasses = computed(() => {
  const classes = ['mode-pos']
  if (company.value) {
    classes.push(`company-${company.value.id}`)
  }
  return classes
})
</script>

<style scoped>
.pos-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #111827;
  color: #f8fafc;
}

.pos-header {
  padding: 1.5rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #0f172a;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.header-actions button {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  color: inherit;
  padding: 0.5rem 1.25rem;
  margin-left: 0.75rem;
  cursor: pointer;
}

.header-actions .accent {
  background: var(--primary-color);
  border-color: var(--primary-color);
}

.pos-body {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr;
}

.pos-panel {
  background: #0f172a;
  padding: 2rem 1.5rem;
}

.pos-panel h2 {
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 1rem;
}

.pos-panel ul {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  color: #cbd5f5;
}

.pos-main {
  padding: 2rem;
  background: #1f2937;
}

@media (max-width: 900px) {
  .pos-body {
    grid-template-columns: 1fr;
  }

  .pos-panel {
    order: 2;
  }
}
</style>
