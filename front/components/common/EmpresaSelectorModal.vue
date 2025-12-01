<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Seleccionar Empresa</h2>
            <button class="close-btn" @click="close">×</button>
          </div>

          <!-- Buscador -->
          <div class="search-section">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Buscar por nombre o código..."
              class="search-input"
            />
          </div>

          <!-- Lista de empresas -->
          <div class="empresas-list">
            <div
              v-for="empresa in filteredEmpresas"
              :key="empresa.id"
              class="empresa-item"
              :class="{ active: selectedEmpresaId === empresa.id }"
              @click="selectEmpresa(empresa)"
            >
              <div class="empresa-info">
                <h3>{{ empresa.nombre }}</h3>
                <p class="empresa-details">
                  NIT: {{ empresa.nit }} · Código: {{ empresa.codigo }}
                </p>
              </div>
              <div class="empresa-actions">
                <span class="check-icon" v-if="selectedEmpresaId === empresa.id">✓</span>
              </div>
            </div>
          </div>

          <!-- Selección de años fiscales -->
          <div v-if="selectedEmpresa" class="anios-section">
            <h3>Años Fiscales Disponibles</h3>
            <div class="anios-grid">
              <button
                v-for="anio in selectedEmpresa.aniosFiscales"
                :key="anio"
                class="anio-btn"
                :class="{ active: selectedAnio === anio }"
                @click="selectedAnio = anio"
              >
                {{ anio }}
              </button>
            </div>
          </div>

          <!-- Acciones -->
          <div class="modal-actions">
            <button class="btn-cancel" @click="close">Cancelar</button>
            <button 
              class="btn-confirm" 
              :disabled="!canConfirm"
              @click="confirmSelection"
            >
              Confirmar
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Modal de validación TNS -->
    <TNSValidationModal
      :empresa-servidor-id="empresaSeleccionada?.empresaServidorId || 0"
      :is-open="showTNSValidation"
      @close="showTNSValidation = false"
      @validated="handleTNSValidated"
    />
  </Teleport>
</template>

<script setup lang="ts">
import TNSValidationModal from './TNSValidationModal.vue'

const session = useSessionStore()

const isOpen = computed(() => session.empresaModalOpen.value)
const empresas = ref<any[]>([])
const searchQuery = ref('')
const selectedEmpresaId = ref<number | null>(null)
const selectedEmpresa = ref<any | null>(null)
const selectedAnio = ref<number | null>(null)

const filteredEmpresas = computed(() => {
  if (!searchQuery.value) return empresas.value
  
  const query = searchQuery.value.toLowerCase()
  return empresas.value.filter(emp => 
    emp.nombre.toLowerCase().includes(query) ||
    emp.codigo.toLowerCase().includes(query) ||
    emp.nit.toLowerCase().includes(query)
  )
})

const canConfirm = computed(() => {
  return selectedEmpresa.value && selectedAnio.value !== null
})

const close = () => {
  session.empresaModalOpen.value = false
  searchQuery.value = ''
  selectedEmpresaId.value = null
  selectedEmpresa.value = null
  selectedAnio.value = null
}

const selectEmpresa = (empresa: any) => {
  selectedEmpresaId.value = empresa.id
  selectedEmpresa.value = empresa
  
  // Si solo hay un año fiscal, seleccionarlo automáticamente
  if (empresa.aniosFiscales && empresa.aniosFiscales.length === 1) {
    selectedAnio.value = empresa.aniosFiscales[0]
  } else if (empresa.aniosFiscales && empresa.aniosFiscales.length > 1) {
    // Seleccionar el más reciente por defecto
    selectedAnio.value = Math.max(...empresa.aniosFiscales)
  }
}

const showTNSValidation = ref(false)
const empresaSeleccionada = ref<any>(null)

const confirmSelection = () => {
  if (!selectedEmpresa.value || selectedAnio.value === null) return
  
  // Buscar la empresa específica con el año fiscal seleccionado
  const grouped = session.groupedEmpresas.value
  const group = grouped.find(g => g.nit === selectedEmpresa.value.nit)
  if (group) {
    const empresaConAnio = group.items.find(item => item.anioFiscal === selectedAnio.value)
    if (empresaConAnio) {
      empresaSeleccionada.value = empresaConAnio
      // Mostrar modal de validación TNS
      showTNSValidation.value = true
    }
  }
}

const handleTNSValidated = async (validationData: any) => {
  if (empresaSeleccionada.value) {
    session.selectEmpresa(empresaSeleccionada.value)
    close()
    
    // Redirigir al template correspondiente después de validar
    const router = useRouter()
    
    // Si hay API Key activa, siempre redirigir a retail (autopago)
    const hasApiKey = session.apiKey.value && session.apiKey.value.length > 0
    const preferredTemplate = hasApiKey ? 'retail' : (empresaSeleccionada.value.preferredTemplate || 'pro')
    
    const templateRoutes: Record<string, string> = {
      retail: '/subdomain/retail',
      restaurant: '/subdomain/restaurant',
      pro: '/subdomain/pro'
    }
    
    // Pequeño delay para que se cierre el modal antes de redirigir
    setTimeout(() => {
      router.push(templateRoutes[preferredTemplate] || '/subdomain/retail')
    }, 300)
  }
}

// Usar empresas del login (ya vienen en session.empresas)
watch(isOpen, (open) => {
  if (open) {
    // Las empresas ya vienen del login en session.empresas (normalizadas)
    // Usar groupedEmpresas que ya agrupa por NIT
    const grouped = session.groupedEmpresas.value
    
    empresas.value = grouped.map(group => ({
      id: group.items[0].empresaServidorId, // Usar el ID de la primera empresa del grupo
      nombre: group.nombre,
      nit: group.nit,
      codigo: group.items[0].codigo || '',
      aniosFiscales: group.items.map(item => item.anioFiscal || 0).sort((a, b) => b - a)
    }))
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.modal-content {
  background: white;
  border-radius: 1rem;
  width: 100%;
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 2rem;
  color: #6b7280;
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  transition: background 0.2s;
}

.close-btn:hover {
  background: #f3f4f6;
}

.search-section {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.search-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  font-size: 1rem;
  transition: border-color 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: #2563eb;
}

.empresas-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  max-height: 300px;
}

.empresa-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 0.5rem;
}

.empresa-item:hover {
  background: #f9fafb;
}

.empresa-item.active {
  background: #eff6ff;
  border: 2px solid #2563eb;
}

.empresa-info h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.empresa-details {
  font-size: 0.875rem;
  color: #6b7280;
}

.check-icon {
  color: #2563eb;
  font-size: 1.5rem;
  font-weight: bold;
}

.anios-section {
  padding: 1.5rem;
  border-top: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
}

.anios-section h3 {
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 1rem;
}

.anios-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.anio-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db;
  background: white;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
}

.anio-btn:hover {
  border-color: #2563eb;
  color: #2563eb;
}

.anio-btn.active {
  background: #2563eb;
  color: white;
  border-color: #2563eb;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  justify-content: flex-end;
}

.btn-cancel,
.btn-confirm {
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: white;
  border: 1px solid #d1d5db;
  color: #374151;
}

.btn-cancel:hover {
  background: #f9fafb;
}

.btn-confirm {
  background: #2563eb;
  color: white;
  border: none;
}

.btn-confirm:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
