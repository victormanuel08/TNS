<template>
  <div>
    <div v-if="currentMode === 'profesional'">
      <h2>Dashboard Profesional</h2>
      <p>Bienvenido al modo contador/administrador</p>
      <div class="dashboard-grid">
        <div class="card">Tesorería</div>
        <div class="card">Facturación</div>
        <div class="card">Inventario</div>
        <div class="card">Nómina</div>
      </div>
    </div>
    
    <div v-else-if="currentMode === 'pos'">
      <h2>POS Restaurante</h2>
      <div class="pos-grid">
        <button class="pos-button">🍽️ Nueva Comanda</button>
        <button class="pos-button">📋 Ver Mesas</button>
        <button class="pos-button">💰 Caja</button>
        <button class="pos-button">📊 Reportes</button>
      </div>
    </div>
    
    <div v-else-if="currentMode === 'autopago'">
      <h2>Autoservicio</h2>
      <div class="kiosk-grid">
        <button class="kiosk-button">🛒 Comprar Productos</button>
        <button class="kiosk-button">💳 Pagar Servicios</button>
        <button class="kiosk-button">📱 Recargar Celular</button>
      </div>
    </div>
    
    <div v-else>
      <h2>Bienvenido {{ companyName }}</h2>
      <p>Modo empresa específica - {{ subdomain }}</p>
      <div class="enterprise-grid">
        <div class="card">Facturación</div>
        <div class="card">Clientes</div>
        <div class="card">Productos</div>
      </div>
    </div>
  </div>
</template>

<script setup>
const { getSubdomain } = useSubdomain()
const subdomain = getSubdomain()

const currentMode = computed(() => {
  const modeMap = {
    'app': 'profesional',
    'restaurant': 'pos',
    'retail': 'autopago'
  }
  return modeMap[subdomain] || 'empresa'
})

const companyName = computed(() => {
  const names = {
    'app': 'Modo Profesional',
    'restaurant': 'Restaurante POS', 
    'retail': 'Autoservicio',
    'empresa1': 'Empresa Ejemplo 1',
    'empresa2': 'Empresa Ejemplo 2'
  }
  return names[subdomain] || `Empresa: ${subdomain}`
})
</script>

<style scoped>
.dashboard-grid, .enterprise-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 2rem;
}

.card {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  text-align: center;
  cursor: pointer;
}

.pos-grid, .kiosk-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-top: 2rem;
}

.pos-button, .kiosk-button {
  padding: 2rem;
  font-size: 1.2em;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.pos-button {
  background: #4CAF50;
  color: white;
}

.kiosk-button {
  background: #2196F3;
  color: white;
  font-size: 1.4em;
  padding: 3rem 2rem;
}
</style>