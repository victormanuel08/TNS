<template>
  <div v-if="isDev" class="dev-selector">
    <label>Modo Desarrollo:</label>
    <select @change="changeMode($event.target.value)" :value="currentSubdomain">
      <option value="app">Profesional (app)</option>
      <option value="restaurant">Restaurante</option>
      <option value="retail">Retail/Autopago</option>
      <option value="empresa1">Empresa Ejemplo 1</option>
      <option value="empresa2">Empresa Ejemplo 2</option>
    </select>
  </div>
</template>

<script setup>
const { getSubdomain, setDevSubdomain } = useSubdomain()
const isDev = process.dev
const currentSubdomain = getSubdomain()

const changeMode = (mode) => {
  setDevSubdomain(mode)
}
</script>

<style scoped>
.dev-selector {
  position: fixed;
  top: 10px;
  right: 10px;
  background: #f0f0f0;
  padding: 10px;
  border: 1px solid #ccc;
  z-index: 9999;
  border-radius: 5px;
}

.dev-selector label {
  margin-right: 10px;
  font-weight: bold;
}

.dev-selector select {
  padding: 5px;
  border-radius: 3px;
  border: 1px solid #999;
}
</style>