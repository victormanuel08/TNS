<template>
  <div :class="layoutClasses" class="ecommerce-layout">
    <EcommerceHeader />
    <main class="ecommerce-main">
      <slot />
    </main>
    <EcommerceFooter />
  </div>
</template>

<script setup>
const { company, currentMode } = useCompany()
const { applyThirdStyles } = useThirdStyles()

onMounted(() => {
  applyThirdStyles()
})

const layoutClasses = computed(() => {
  const classes = ['mode-ecommerce']
  if (company.value) {
    classes.push(`company-${company.value.id}`)
  }
  if (currentMode.value !== 'ecommerce') {
    classes.push(`mode-${currentMode.value}`)
  }
  return classes
})
</script>

<style>
/* Resetear márgenes globales - SIN SCOPED para que funcione */
body,
html {
  margin: 0 !important;
  padding: 0 !important;
  width: 100% !important;
  max-width: 100% !important;
  overflow-x: hidden !important;
  box-sizing: border-box !important;
}

#__nuxt,
#__nuxt > div {
  margin: 0 !important;
  padding: 0 !important;
  width: 100% !important;
  max-width: 100% !important;
}
</style>

<style scoped>
.ecommerce-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  width: 100vw;
  max-width: 100vw;
  overflow-x: hidden;
  margin: 0;
  padding: 0;
  position: relative;
  left: 0;
  top: 0;
}

.ecommerce-main {
  flex: 1;
  padding: 0;
  width: 100%;
  max-width: 100%;
  margin: 0;
  overflow-x: hidden;
}
</style>
