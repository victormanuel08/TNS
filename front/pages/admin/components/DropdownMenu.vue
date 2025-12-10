<template>
  <div class="dropdown-menu-container" ref="containerRef">
    <button
      class="dropdown-trigger"
      :class="[triggerClass, { active: isOpen }]"
      @click.stop="toggle"
      :disabled="disabled"
    >
      <slot name="trigger">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="1"/>
          <circle cx="12" cy="5" r="1"/>
          <circle cx="12" cy="19" r="1"/>
        </svg>
        Menú
      </slot>
    </button>
    <Transition name="dropdown">
      <div
        v-if="isOpen"
        class="dropdown-menu"
        :class="menuClass"
        @click.stop
      >
        <slot></slot>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface Props {
  triggerClass?: string
  menuClass?: string
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  triggerClass: 'btn-small btn-primary',
  menuClass: '',
  disabled: false
})

const isOpen = ref(false)
const containerRef = ref<HTMLElement | null>(null)

const toggle = () => {
  if (!props.disabled) {
    isOpen.value = !isOpen.value
  }
}

const close = () => {
  isOpen.value = false
}

const handleClickOutside = (event: MouseEvent) => {
  if (containerRef.value && !containerRef.value.contains(event.target as Node)) {
    close()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

defineExpose({ toggle, close, isOpen })
</script>

<style scoped>
.dropdown-menu-container {
  position: relative;
  display: inline-block;
}

.dropdown-trigger {
  position: relative;
}

.dropdown-trigger.active {
  background: #374151;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 0.25rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  min-width: 180px;
  z-index: 9999;
  overflow: hidden;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>

