<template>
  <div class="ecommerce-layout">
    <EcommerceHeader />
    <main class="ecommerce-main">
      <slot />
    </main>
    <EcommerceFooter />
  </div>
</template>

<script setup>
// Este layout no requiere autenticación - acceso público
</script>

<style scoped>
.ecommerce-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.ecommerce-main {
  flex: 1;
  padding-top: 0; /* El header manejará su propio espacio */
}
</style>