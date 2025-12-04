<template>
  <div class="search-bar-container">
    <input
      :value="modelValue"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      type="text"
      :placeholder="placeholder"
      class="search-input"
    />
    <button 
      v-if="modelValue"
      class="search-clear"
      @click="$emit('update:modelValue', '')"
      title="Limpiar búsqueda"
    >
      ×
    </button>
  </div>
</template>

<script setup lang="ts">
interface Props {
  modelValue: string
  placeholder?: string
}

withDefaults(defineProps<Props>(), {
  placeholder: 'Buscar...'
})

defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<style scoped>
.search-bar-container {
  position: relative;
  display: flex;
  align-items: center;
}

.search-input {
  padding: 0.625rem 1rem;
  padding-right: 2.5rem;
  border: 1.5px solid #e5e7eb;
  border-radius: 0.5rem;
  font-size: 0.95rem;
  min-width: 300px;
  transition: all 0.2s;
  background: white;
}

.search-input:focus {
  outline: none;
  border-color: #9ca3af;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.1);
}

.search-clear {
  position: absolute;
  right: 0.5rem;
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #9ca3af;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
}

.search-clear:hover {
  color: #374151;
}
</style>

