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

<style scoped>
.ecommerce-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
}

.ecommerce-main {
  flex: 1;
  padding-top: 0;
}
</style>
