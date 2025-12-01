<template>
  <div class="subdomain-dashboard">
    <!-- Redirigir según template preferido -->
    <div class="loading-screen">
      <div class="spinner"></div>
      <p>Cargando...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: false
})

const session = useSessionStore()
const { currentTemplate } = useTemplate()
const { getSubdomain } = useSubdomain()

onMounted(() => {
  // Obtener template preferido del usuario o empresa seleccionada
  const preferredTemplate = session.selectedEmpresa.value?.preferredTemplate || 'pro'
  
  // Redirigir al template correspondiente
  const templateRoutes: Record<string, string> = {
    retail: '/subdomain/retail',
    restaurant: '/subdomain/restaurant',
    pro: '/subdomain/pro'
  }
  
  navigateTo(templateRoutes[preferredTemplate] || '/subdomain/pro')
})
</script>

<style scoped>
.subdomain-dashboard {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-background);
}

.loading-screen {
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-screen p {
  color: var(--color-text-secondary);
}
</style>

