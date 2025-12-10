<template>
  <div class="redirect-container">
    <div class="redirect-content">
      <div class="spinner"></div>
      <h1>Redirigiendo a Asistente DIAN...</h1>
      <p>Serás redirigido automáticamente a BCE</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

onMounted(() => {
  // Redirigir directamente a BCE
  if (process.client) {
    window.location.href = 'https://bancodecontadoresespecializados.com.co/ScrapingDian'
  }
})
</script>

<style scoped>
.redirect-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.redirect-content {
  text-align: center;
  color: white;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

h1 {
  font-size: 24px;
  margin-bottom: 10px;
}

p {
  font-size: 16px;
  opacity: 0.9;
}
</style>

