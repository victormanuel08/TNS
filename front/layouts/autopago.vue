<template>
  <div :class="layoutClasses" class="kiosk-layout">
    <header class="kiosk-header">
      <div>
        <p class="subtitle">Terminal de autopago</p>
        <h1>{{ companyName }}</h1>
      </div>
      <div class="status-indicator">Disponible</div>
    </header>

    <main class="kiosk-main">
      <slot />
    </main>
  </div>
</template>

<script setup>
const { company, companyName } = useCompany()
const { applyThirdStyles } = useThirdStyles()

onMounted(() => {
  applyThirdStyles()
})

const layoutClasses = computed(() => {
  const classes = ['mode-autopago']
  if (company.value) {
    classes.push(`company-${company.value.id}`)
  }
  return classes
})
</script>

<style scoped>
.kiosk-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(120deg, #0ea5e9, #312e81);
  color: white;
}

.kiosk-header {
  padding: 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.subtitle {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.85rem;
  opacity: 0.9;
}

.status-indicator {
  background: rgba(255, 255, 255, 0.12);
  padding: 0.75rem 1.5rem;
  border-radius: 999px;
  font-weight: 600;
}

.kiosk-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}
</style>
