<template>
  <div :class="layoutClasses" class="kiosk-layout">
    <main class="kiosk-main">
      <slot />
    </main>
  </div>
</template>

<script setup>
const { company, companyName } = useCompany()
const { applyThirdStyles } = useThirdStyles()

onMounted(() => {
  if (process.client) {
    applyThirdStyles()
  }
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
  background: #f5f5f5; /* Fondo neutro tipo fast food */
  color: #333;
}

.kiosk-main {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 1rem;
  width: 100%;
  box-sizing: border-box;
  overflow-x: hidden; /* Evitar desbordamiento horizontal */
}
</style>
