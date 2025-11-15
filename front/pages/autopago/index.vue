<template>
  <section class="kiosk">
    <div class="kiosk-card" v-for="option in kioskOptions" :key="option.label">
      <h3>{{ option.label }}</h3>
      <p>{{ option.description }}</p>
      <button>Iniciar</button>
    </div>
  </section>
</template>

<script setup>
definePageMeta({
  layout: 'autopago'
})

const kioskOptions = [
  { label: 'Pagar servicios', description: 'Luz, agua, internet y mas' },
  { label: 'Recargar celular', description: 'Compatible con todos los operadores' },
  { label: 'Comprar productos', description: 'Catalogo rapido y seguro' }
]
</script>

<style scoped>
.kiosk {
  width: 100%;
  max-width: 900px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.5rem;
}

.kiosk-card {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 18px;
  padding: 2rem 1.5rem;
  text-align: center;
  color: white;
}

.kiosk-card button {
  margin-top: 1rem;
  background: white;
  color: #312e81;
  border: none;
  border-radius: 999px;
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  cursor: pointer;
}
</style>
