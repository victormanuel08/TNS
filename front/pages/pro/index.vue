<template>
  <section class="pro-dashboard">
    <div class="stats-grid">
      <article v-for="card in cards" :key="card.title" class="stat-card">
        <p class="label">{{ card.title }}</p>
        <h3>{{ card.value }}</h3>
        <span :class="{ positive: card.trend >= 0 }">
          {{ card.trend >= 0 ? '+' : '' }}{{ card.trend }}%
        </span>
      </article>
    </div>

    <div class="chart-placeholder">
      <p>Grafica de flujo de caja</p>
    </div>
  </section>
</template>

<script setup>
definePageMeta({
  layout: 'pro'
})

const cards = [
  { title: 'Facturacion hoy', value: '$125,640', trend: 12 },
  { title: 'CxC abiertas', value: '$48,300', trend: -3 },
  { title: 'Ordenes', value: '87', trend: 5 },
  { title: 'Utilidad neta', value: '$32,210', trend: 8 }
]
</script>

<style scoped>
.pro-dashboard {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 1.5rem;
  color: white;
}

.stat-card .label {
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  color: #94a3b8;
}

.stat-card span {
  font-size: 0.85rem;
  color: #f87171;
}

.stat-card span.positive {
  color: #4ade80;
}

.chart-placeholder {
  height: 240px;
  border-radius: 12px;
  border: 1px dashed rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
}
</style>
