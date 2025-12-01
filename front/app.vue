<template>
  <div class="app-wrapper">
    <ClientOnly v-if="!isAdminDashboard">
      <EmpresaSelectorModal />
    </ClientOnly>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>

<script setup>
import EmpresaSelectorModal from '@/components/common/EmpresaSelectorModal.vue'

const route = useRoute()
const isAdminDashboard = computed(() => route.path.startsWith('/admin/dashboard'))
</script>

<style>
.app-wrapper {
  min-height: 100vh;
  margin: 0;
  padding: 0;
  width: 100%;
  max-width: 100%;
}

/* Para modo ecommerce, eliminar cualquier margen */
.app-wrapper .default-layout.mode-ecommerce,
.app-wrapper .ecommerce-layout {
  margin: 0 !important;
  padding: 0 !important;
  width: 100vw !important;
  max-width: 100vw !important;
}
</style>
