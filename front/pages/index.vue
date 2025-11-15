<template>
  <div class="home">
    <section v-if="currentMode === 'pro'" class="panel-grid">
      <article v-for="panel in proPanels" :key="panel.title" class="panel-card">
        <div class="panel-icon">{{ panel.icon }}</div>
        <div>
          <h3>{{ panel.title }}</h3>
          <p>{{ panel.description }}</p>
        </div>
      </article>
    </section>

    <section v-else-if="currentMode === 'pos'" class="pos-actions">
      <button v-for="action in posActions" :key="action" class="pos-button">
        {{ action }}
      </button>
    </section>

    <section v-else-if="currentMode === 'autopago'" class="kiosk-options">
      <button v-for="option in kioskOptions" :key="option" class="kiosk-button">
        {{ option }}
      </button>
    </section>

    <section v-else class="enterprise-grid">
      <article v-for="card in enterpriseCards" :key="card.title" class="panel-card">
        <h3>{{ card.title }}</h3>
        <p>{{ card.description }}</p>
      </article>
    </section>
  </div>
</template>

<script setup>
definePageMeta({
  layout: 'default'
})

const { currentMode, companyName } = useCompany()

const proPanels = [
  { title: 'Tesoreria', description: 'Flujo de caja diario y conciliaciones', icon: '$$' },
  { title: 'Facturacion', description: 'CFDI y facturas electronicas', icon: 'FA' },
  { title: 'Inventario', description: 'Costos promedio y lotes', icon: 'INV' },
  { title: 'Nomina', description: 'Calculo automatico y timbrado', icon: 'PAY' }
]

const posActions = ['Nueva comanda', 'Mesas abiertas', 'Caja del dia', 'Reportes rapidos']

const kioskOptions = ['Comprar productos', 'Recargar servicios', 'Pagar facturas']

const enterpriseCards = computed(() => [
  { title: 'Facturacion', description: `Ventas y clientes de ${companyName.value}` },
  { title: 'Clientes', description: 'Segmentacion y fidelizacion' },
  { title: 'Productos', description: 'Catalogo actualizado' }
])
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.5rem;
}

.panel-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 1.5rem;
  box-shadow: var(--shadow);
}

.panel-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.pos-actions,
.kiosk-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.pos-button,
.kiosk-button {
  padding: 1.5rem;
  border-radius: var(--border-radius);
  border: none;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  color: white;
}

.pos-button {
  background: var(--primary-color);
}

.kiosk-button {
  background: #0ea5e9;
}

.enterprise-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}
</style>
