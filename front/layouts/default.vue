<template>
  <div :class="layoutClasses" class="default-layout">
    <!-- Header eliminado para no mostrar 'Empresa activa / Modo ...' y aprovechar mejor el espacio -->
    <main class="default-main">
      <slot />
    </main>

    <footer v-if="currentMode !== 'ecommerce'" class="default-footer">
      <p>Sistema contable - {{ new Date().getFullYear() }}</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
const { company, companyName, currentMode } = useCompany()
const { applyThirdStyles } = useThirdStyles()

onMounted(() => {
  applyThirdStyles()
})

const currentModeLabel = computed(() => {
  const labels: Record<string, string> = {
    ecommerce: 'E-commerce',
    pos: 'Punto de venta',
    pro: 'Profesional',
    autopago: 'Autopago'
  }

  return labels[currentMode.value] || 'General'
})

const layoutClasses = computed(() => {
  const classes = ['mode-' + currentMode.value]
  if (company.value) {
    classes.push(`company-${company.value.id}`)
  }
  return classes
})
</script>

<style scoped>
.default-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.default-header {
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  padding: 1.5rem 2rem;
  box-shadow: var(--shadow);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.company-label {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
}

.mode-badge {
  padding: 0.75rem 1rem;
  border-radius: var(--border-radius);
  border: 1px solid var(--border-color);
  text-align: right;
  min-width: 160px;
}

.mode-badge span {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.mode-badge strong {
  display: block;
  font-size: 1rem;
  color: var(--primary-color);
}

.default-main {
  flex: 1;
  padding: 2rem;
}

/* Para modo ecommerce, eliminar padding y márgenes */
.default-layout.mode-ecommerce {
  padding: 0 !important;
  margin: 0 !important;
  width: 100vw !important;
  max-width: 100vw !important;
}

.default-layout.mode-ecommerce .default-main {
  padding: 0 !important;
  margin: 0 !important;
  width: 100% !important;
  max-width: 100% !important;
}

.default-footer {
  text-align: center;
  padding: 1rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
  border-top: 1px solid var(--border-color);
}
</style>
