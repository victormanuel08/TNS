<template>
  <div class="app-wrapper">
    <ClientOnly v-if="showDevSelector">
      <DevModeSelector />
    </ClientOnly>
    <ClientOnly>
      <EmpresaSelectorModal />
    </ClientOnly>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>

<script setup>
const showDevSelector = process.dev
</script>

<style>
.app-wrapper {
  min-height: 100vh;
}
</style>
