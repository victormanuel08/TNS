<template>
  <button
    class="dropdown-item"
    :class="{ 'dropdown-item-danger': danger, 'dropdown-item-disabled': disabled }"
    :disabled="disabled"
    @click="handleClick"
  >
    <slot></slot>
  </button>
</template>

<script setup lang="ts">
interface Props {
  danger?: boolean
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  danger: false,
  disabled: false
})

const emit = defineEmits<{
  click: []
}>()

const handleClick = () => {
  if (!props.disabled) {
    emit('click')
  }
}
</script>

<style scoped>
.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.625rem 1rem;
  border: none;
  background: none;
  text-align: left;
  font-size: 0.875rem;
  color: #374151;
  cursor: pointer;
  transition: background 0.15s;
}

.dropdown-item:hover:not(:disabled) {
  background: #f3f4f6;
}

.dropdown-item:disabled,
.dropdown-item-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dropdown-item-danger {
  color: #dc2626;
}

.dropdown-item-danger:hover:not(:disabled) {
  background: #fee2e2;
  color: #991b1b;
}
</style>

