<template>
  <div class="template-switcher">
    <button class="switcher-btn" @click="showMenu = !showMenu">
      <span>{{ currentTemplateName }}</span>
      <span class="arrow">▼</span>
    </button>
    
    <Transition name="dropdown">
      <div v-if="showMenu" class="template-menu">
        <button
          v-for="(template, key) in templates"
          :key="key"
          class="template-option"
          :class="{ active: currentTemplate === key }"
          @click="switchTemplate(key as TemplateType)"
        >
          <div class="template-info">
            <strong>{{ template.name }}</strong>
            <span class="template-desc">{{ template.description }}</span>
          </div>
        </button>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import type { TemplateType } from '~/composables/useTemplate'

const { currentTemplate, templates, setTemplate } = useTemplate()
const showMenu = ref(false)

const currentTemplateName = computed(() => {
  return templates[currentTemplate.value]?.name || 'Seleccionar Vista'
})

const switchTemplate = (template: TemplateType) => {
  setTemplate(template)
  showMenu.value = false
}

// Cerrar menú al hacer click fuera
onMounted(() => {
  const handleClickOutside = (e: MouseEvent) => {
    const target = e.target as HTMLElement
    if (!target.closest('.template-switcher')) {
      showMenu.value = false
    }
  }
  document.addEventListener('click', handleClickOutside)
  onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside)
  })
})
</script>

<style scoped>
.template-switcher {
  position: relative;
}

.switcher-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.switcher-btn:hover {
  border-color: #2563eb;
  color: #2563eb;
}

.arrow {
  font-size: 0.75rem;
  transition: transform 0.2s;
}

.switcher-btn:hover .arrow {
  transform: rotate(180deg);
}

.template-menu {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  min-width: 250px;
  z-index: 100;
  overflow: hidden;
}

.template-option {
  width: 100%;
  padding: 1rem;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid #f3f4f6;
}

.template-option:last-child {
  border-bottom: none;
}

.template-option:hover {
  background: #f9fafb;
}

.template-option.active {
  background: #eff6ff;
}

.template-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.template-info strong {
  color: #1f2937;
  font-size: 0.875rem;
}

.template-desc {
  color: #6b7280;
  font-size: 0.75rem;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>

