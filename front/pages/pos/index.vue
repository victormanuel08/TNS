<template>
  <section class="pos-grid">
    <div class="tables">
      <h2>Mesas activas</h2>
      <div class="table-list">
        <article v-for="table in tables" :key="table.name" class="table-card">
          <strong>{{ table.name }}</strong>
          <p>{{ table.status }}</p>
          <span>{{ table.total }}</span>
        </article>
      </div>
    </div>

    <div class="commands">
      <h2>Acciones</h2>
      <div class="command-buttons">
        <button v-for="action in actions" :key="action" class="command-btn">
          {{ action }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
definePageMeta({
  layout: 'pos'
})

const tables = [
  { name: 'Mesa 1', status: 'Orden enviada', total: '$45.20' },
  { name: 'Mesa 2', status: 'Consumo', total: '$30.00' },
  { name: 'Mesa 5', status: 'Listo para cobrar', total: '$58.90' }
]

const actions = ['Nueva comanda', 'Ver cocina', 'Corte de caja']
</script>

<style scoped>
.pos-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
  color: #f8fafc;
}

.tables,
.commands {
  background: rgba(15, 23, 42, 0.6);
  border-radius: 12px;
  padding: 1.5rem;
}

.table-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
}

.table-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  padding: 1rem;
}

.commands {
  background: rgba(15, 23, 42, 0.9);
}

.command-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}

.command-btn {
  background: var(--primary-color);
  border: none;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  color: white;
  cursor: pointer;
}

@media (max-width: 900px) {
  .pos-grid {
    grid-template-columns: 1fr;
  }
}
</style>
