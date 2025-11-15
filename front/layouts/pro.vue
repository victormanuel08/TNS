<template>
  <div :class="layoutClasses" class="pro-layout">
    <aside class="pro-sidebar">
      <div class="brand">
        <span class="brand-label">TNS</span>
        <p>{{ companyName }}</p>
      </div>
      <nav class="sidebar-menu">
        <a v-for="item in menuItems" :key="item" href="#">
          {{ item }}
        </a>
      </nav>
    </aside>

    <div class="pro-content">
      <header class="pro-header">
        <div>
          <p class="label">Modo profesional</p>
          <h2>Panel contable</h2>
        </div>
        <div class="chips">
          <span v-for="chip in chips" :key="chip">{{ chip }}</span>
        </div>
      </header>

      <main class="pro-main">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
const menuItems = [
  'Tablero',
  'Facturacion',
  'Tesoreria',
  'Inventarios',
  'Nomina',
  'Reportes'
]
const chips = ['En linea', 'Multiempresa', 'Auditoria']

const { company, companyName, currentMode } = useCompany()
const { applyThirdStyles } = useThirdStyles()

onMounted(() => {
  applyThirdStyles()
})

const layoutClasses = computed(() => {
  const classes = ['mode-pro']
  if (company.value) {
    classes.push(`company-${company.value.id}`)
  }
  if (currentMode.value !== 'pro') {
    classes.push(`mode-${currentMode.value}`)
  }
  return classes
})
</script>

<style scoped>
.pro-layout {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 280px 1fr;
  background: #0f172a;
  color: white;
}

.pro-sidebar {
  background: #020617;
  padding: 2rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.brand {
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 0.85rem;
  color: #94a3b8;
}

.brand-label {
  display: block;
  font-size: 1.25rem;
  font-weight: 700;
}

.sidebar-menu {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.sidebar-menu a {
  color: #cbd5f5;
  text-decoration: none;
  font-weight: 500;
}

.pro-content {
  background: #0f172a;
  display: flex;
  flex-direction: column;
}

.pro-header {
  padding: 2rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.label {
  color: #94a3b8;
  font-size: 0.9rem;
  letter-spacing: 0.08em;
}

.chips {
  display: flex;
  gap: 0.5rem;
}

.chips span {
  border: 1px solid rgba(255, 255, 255, 0.2);
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.8rem;
}

.pro-main {
  flex: 1;
  padding: 2rem;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.9) 0%, #020617 100%);
}

@media (max-width: 960px) {
  .pro-layout {
    grid-template-columns: 1fr;
  }

  .pro-sidebar {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
}
</style>
