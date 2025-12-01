<template>
  <div class="pro-template">
    <header class="pro-header">
      <div class="header-left">
        <h1>Software Contable</h1>
        <p class="subtitle">Gestión profesional completa</p>
      </div>
      <div class="header-right">
        <!-- Selector de año fiscal -->
        <div v-if="fiscalYears.length > 0" class="fiscal-year-selector">
          <select
            v-model="selectedFiscalYear"
            @change="handleFiscalYearChange"
            class="year-select"
          >
            <option v-for="year in fiscalYears" :key="year.anioFiscal" :value="year">
              {{ year.anioFiscal }}
            </option>
          </select>
        </div>
        <TemplateSwitcher />
      </div>
    </header>

    <nav class="pro-nav">
        <button 
        v-for="tab in tabs" 
        :key="tab.id"
        class="nav-tab"
        :class="{ active: activeTab === tab.id }"
        @click="handleTabClick(tab)"
      >
        {{ tab.name }}
      </button>
    </nav>

    <main class="pro-main">
      <div class="dashboard-grid">
        <div class="stat-card">
          <h3>Facturas</h3>
          <p class="stat-value">1,234</p>
        </div>
        <div class="stat-card">
          <h3>Clientes</h3>
          <p class="stat-value">456</p>
        </div>
        <div class="stat-card">
          <h3>Ingresos</h3>
          <p class="stat-value">$125,000</p>
        </div>
        <div class="stat-card">
          <h3>Gastos</h3>
          <p class="stat-value">$45,000</p>
        </div>
      </div>

      <div class="content-section">
        <h2>Últimas Transacciones</h2>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Descripción</th>
                <th>Monto</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="transaction in mockTransactions" :key="transaction.id">
                <td>{{ transaction.date }}</td>
                <td>{{ transaction.description }}</td>
                <td>${{ transaction.amount }}</td>
                <td>
                  <span class="status-badge" :class="transaction.status">
                    {{ transaction.status }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: false
})

const tabs = [
  { id: 'dashboard', name: 'Dashboard' },
  { id: 'facturas', name: 'Facturas', route: '/subdomain/modules/facturacion' },
  { id: 'tesoreria', name: 'Tesorería', route: '/subdomain/modules/tesoreria' },
  { id: 'cartera', name: 'Cartera', route: '/subdomain/modules/cartera' },
  { id: 'inventario', name: 'Inventario', route: '/subdomain/modules/inventario' },
  { id: 'contabilidad', name: 'Contabilidad', route: '/subdomain/modules/contabilidad' },
  { id: 'dian', name: 'DIAN', route: '/subdomain/modules/dian' },
  { id: 'archivos', name: 'Archivos', route: '/subdomain/modules/archivos' },
  { id: 'calendario', name: 'Calendario', route: '/subdomain/modules/calendario' },
  { id: 'reportes', name: 'Reportes' },
]

const router = useRouter()
const session = useSessionStore()
const activeTab = ref('dashboard')

const fiscalYears = computed(() => {
  if (!session.selectedEmpresa.value) return []
  const grouped = session.groupedEmpresas.value
  const group = grouped.find(g => g.nit === session.selectedEmpresa.value?.nit)
  return group?.items || []
})

const selectedFiscalYear = computed({
  get: () => session.selectedEmpresa.value || null,
  set: (value) => {
    if (value) {
      handleSelectFiscalYear(value)
    }
  }
})

const handleSelectFiscalYear = async (year: any) => {
  // Verificar si es el mismo NIT (no pedir TNS password)
  const currentNit = session.selectedEmpresa.value?.nit
  const newNit = year.nit
  
  if (currentNit === newNit) {
    // Mismo NIT: heredar permisos del login inicial, no pedir TNS password
    session.selectEmpresa(year)
    // Recargar la página para actualizar datos
    router.go(0)
  } else {
    // Diferente NIT: necesitamos validación TNS
    session.selectEmpresa(year)
    // Mostrar modal de validación TNS
    session.empresaModalOpen.value = true
  }
}

const handleFiscalYearChange = () => {
  if (selectedFiscalYear.value) {
    handleSelectFiscalYear(selectedFiscalYear.value)
  }
}

const handleTabClick = (tab: any) => {
  if (tab.route) {
    router.push(tab.route)
  } else {
    activeTab.value = tab.id
  }
}

const mockTransactions = [
  { id: 1, date: '2025-01-15', description: 'Factura #001', amount: 1500, status: 'pagado' },
  { id: 2, date: '2025-01-14', description: 'Factura #002', amount: 2300, status: 'pendiente' },
  { id: 3, date: '2025-01-13', description: 'Factura #003', amount: 980, status: 'pagado' },
]

</script>

<style scoped>
.pro-template {
  min-height: 100vh;
  background: #f9fafb;
}

.pro-header {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 1.5rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left h1 {
  font-size: 1.75rem;
  color: #1f2937;
  margin: 0 0 0.25rem 0;
}

.subtitle {
  color: #6b7280;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.fiscal-year-selector {
  display: flex;
  align-items: center;
}

.year-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  background: white;
  color: #1f2937;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  min-width: 100px;
}

.year-select:hover {
  border-color: #94a3b8;
}

.template-switcher {
  padding: 0.75rem 1.5rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 600;
}

.pro-nav {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 2rem;
  display: flex;
  gap: 0.5rem;
}

.nav-tab {
  padding: 1rem 1.5rem;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  font-weight: 500;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.nav-tab:hover {
  color: #2563eb;
}

.nav-tab.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}

.pro-main {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  border-radius: 0.75rem;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.stat-card h3 {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0 0 0.5rem 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.content-section {
  background: white;
  border-radius: 0.75rem;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.content-section h2 {
  font-size: 1.5rem;
  color: #1f2937;
  margin: 0 0 1.5rem 0;
}

.table-container {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  text-align: left;
  padding: 0.75rem;
  border-bottom: 2px solid #e5e7eb;
  color: #6b7280;
  font-weight: 600;
  font-size: 0.875rem;
  text-transform: uppercase;
}

.data-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #e5e7eb;
  color: #1f2937;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-badge.pagado {
  background: #d1fae5;
  color: #065f46;
}

.status-badge.pendiente {
  background: #fef3c7;
  color: #92400e;
}
</style>

