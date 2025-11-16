<template>
  <div v-if="session.empresaModalOpen.value" class="empresa-modal">
    <div class="modal-card">
      <header>
        <p class="kicker">Selecciona tu empresa</p>
        <h2>Elige NIT y año fiscal</h2>
        <p class="subtitle">
          Solo podrás continuar cuando confirmes la empresa con la que deseas trabajar.
        </p>
      </header>

      <div class="empresa-list" v-if="groupedEmpresas.length">
        <article
          v-for="group in groupedEmpresas"
          :key="group.nit"
          class="empresa-item"
          :class="{ active: isGroupSelected(group) }"
          @click="selectGroup(group)"
        >
          <div class="empresa-info">
            <strong>{{ group.nombre }}</strong>
            <span>{{ group.nit }}</span>
          </div>
          <div class="years">
            <button
              v-for="item in group.items"
              :key="item.empresaServidorId"
              type="button"
              :class="{
                year: true,
                selected:
                  selectedEntry?.empresaServidorId === item.empresaServidorId
              }"
              @click.stop="selectEntry(item)"
            >
              {{ item.anioFiscal }}
            </button>
          </div>
        </article>
      </div>

      <footer>
        <button
          class="primary"
          :disabled="!selectedEntry"
          @click="confirmSelection"
        >
          Continuar
        </button>
        <button class="ghost" @click="logout">
          Salir
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
const session = useSessionStore()
const groupedEmpresas = session.groupedEmpresas
const selectedEntry = ref<any>(null)

watch(
  () => session.empresaModalOpen.value,
  (open) => {
    if (open) {
      const firstGroup = groupedEmpresas.value[0]
      selectedEntry.value = firstGroup?.items[0] || null
    }
  },
  { immediate: true }
)

watch(
  groupedEmpresas,
  (groups) => {
    if (session.empresaModalOpen.value && groups.length) {
      selectedEntry.value = groups[0].items[0] || null
    }
  },
  { immediate: true }
)

const selectGroup = (group: any) => {
  selectedEntry.value = group.items[0]
}

const selectEntry = (entry: any) => {
  selectedEntry.value = entry
}

const isGroupSelected = (group: any) => {
  if (!selectedEntry.value) return false
  return selectedEntry.value.nit === group.nit
}

const confirmSelection = () => {
  if (selectedEntry.value) {
    session.selectEmpresa(selectedEntry.value)
  }
}

const logout = () => {
  session.logout()
}
</script>

<style scoped>
.empresa-modal {
  position: fixed;
  inset: 0;
  background: rgba(5, 9, 19, 0.85);
  backdrop-filter: blur(10px);
  z-index: 2000;
  display: grid;
  place-items: center;
  padding: 1rem;
}

.modal-card {
  width: min(720px, 96vw);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 28px;
  padding: 2rem;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.subtitle {
  color: var(--text-secondary);
}

.empresa-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.empresa-item {
  border: 1px solid var(--border-color);
  border-radius: 18px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  cursor: pointer;
}

.empresa-item.active {
  border-color: var(--primary-color);
  background: rgba(37, 99, 235, 0.08);
}

.empresa-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.years {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.year {
  border-radius: 999px;
  border: 1px solid var(--border-color);
  padding: 0.35rem 0.9rem;
  background: transparent;
  color: var(--text-primary);
}

.year.selected {
  background: var(--primary-color);
  color: #fff;
  border-color: transparent;
}

footer {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

button.primary {
  background: var(--primary-color);
  color: #fff;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: var(--border-radius);
}

button.ghost {
  border: 1px solid var(--border-color);
  background: transparent;
  color: var(--text-primary);
  padding: 0.6rem 1.2rem;
  border-radius: var(--border-radius);
}
</style>
