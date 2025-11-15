<template>
  <div :class="layoutClasses">
    <component :is="currentLayout">
      <slot />
    </component>
  </div>
</template>

<script setup>
const { company, currentMode } = useCompany()
const { applyThirdStyles } = useThirdStyles()

// Aplicar estilos de la empresa cuando se monta el componente
onMounted(() => {
  applyThirdStyles()
})

// Clases CSS dinámicas
const layoutClasses = computed(() => {
  const classes = [`mode-${currentMode.value}`]
  if (company.value) {
    classes.push(`company-${company.value.id}`)
  }
  return classes
})

// Layout dinámico basado en el modo
const currentLayout = computed(() => {
  const layoutMap = {
    ecommerce: 'LayoutEcommerce',
    pos: 'LayoutPos',
    pro: 'LayoutPro',
    autopago: 'LayoutAutopago'
  }
  return layoutMap[currentMode.value] || 'LayoutEcommerce'
})
</script>

<style>
/* Variables CSS globales */
:root {
  --primary-color: #3B82F6;
  --secondary-color: #1E40AF;
  --accent-color: #F59E0B;
  --text-primary: #1F2937;
  --text-secondary: #6B7280;
  --bg-primary: #FFFFFF;
  --bg-secondary: #F9FAFB;
  --border-color: #E5E7EB;
  --font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  --border-radius: 8px;
  --shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
}

/* Reset y estilos base */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-family);
  color: var(--text-primary);
  background-color: var(--bg-primary);
  line-height: 1.5;
}

/* Clases base por modo */
.mode-ecommerce {
  /* Estilos específicos se aplicarán via useThirdStyles */
}

.mode-pos {
  background-color: #1F2937;
  color: white;
}

.mode-pro {
  background-color: #111827;
  color: white;
}

.mode-autopago {
  background-color: #F3F4F6;
}
</style>