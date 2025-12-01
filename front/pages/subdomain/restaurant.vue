<template>
  <div class="restaurant-template">
    <header class="restaurant-header">
      <h1>Restaurante</h1>
      <TemplateSwitcher />
    </header>

    <main class="restaurant-main">
      <div class="categories">
        <button 
          v-for="cat in categories" 
          :key="cat.id"
          class="category-btn"
          :class="{ active: selectedCategory === cat.id }"
          @click="selectedCategory = cat.id"
        >
          {{ cat.name }}
        </button>
      </div>

      <div class="menu-grid">
        <div 
          v-for="item in filteredMenu" 
          :key="item.id"
          class="menu-item"
          @click="addToOrder(item)"
        >
          <div class="menu-item-image">{{ item.emoji }}</div>
          <h3>{{ item.name }}</h3>
          <p class="menu-price">${{ item.price }}</p>
        </div>
      </div>
    </main>

    <aside class="order-panel" v-if="order.length > 0">
      <h2>Pedido Actual</h2>
      <div class="order-items">
        <div v-for="(item, index) in order" :key="index" class="order-item">
          <span>{{ item.name }}</span>
          <span>${{ item.price }}</span>
        </div>
      </div>
      <div class="order-total">
        <strong>Total: ${{ orderTotal }}</strong>
      </div>
      <button class="btn-confirm-order">Confirmar Pedido</button>
    </aside>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: false
})

const categories = [
  { id: 'all', name: 'Todos' },
  { id: 'food', name: 'Comida' },
  { id: 'drinks', name: 'Bebidas' },
  { id: 'desserts', name: 'Postres' },
]

const menu = [
  { id: 1, name: 'Hamburguesa', price: 12.99, category: 'food', emoji: '🍔' },
  { id: 2, name: 'Pizza', price: 15.50, category: 'food', emoji: '🍕' },
  { id: 3, name: 'Coca Cola', price: 2.50, category: 'drinks', emoji: '🥤' },
  { id: 4, name: 'Torta', price: 8.99, category: 'desserts', emoji: '🍰' },
]

const selectedCategory = ref('all')
const order = ref<any[]>([])

const filteredMenu = computed(() => {
  if (selectedCategory.value === 'all') return menu
  return menu.filter(item => item.category === selectedCategory.value)
})

const orderTotal = computed(() => {
  return order.value.reduce((sum, item) => sum + item.price, 0).toFixed(2)
})

const addToOrder = (item: any) => {
  order.value.push(item)
}

</script>

<style scoped>
.restaurant-template {
  min-height: 100vh;
  background: #fafafa;
  padding: 2rem;
}

.restaurant-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  background: white;
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.restaurant-header h1 {
  font-size: 2rem;
  color: #1f2937;
  margin: 0;
}

.template-switcher {
  padding: 0.75rem 1.5rem;
  background: #f97316;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 600;
}

.categories {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.category-btn {
  padding: 0.75rem 1.5rem;
  border: 2px solid #e5e7eb;
  background: white;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.category-btn:hover {
  border-color: #f97316;
}

.category-btn.active {
  background: #f97316;
  color: white;
  border-color: #f97316;
}

.menu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1.5rem;
}

.menu-item {
  background: white;
  border-radius: 1rem;
  padding: 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: transform 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.menu-item:hover {
  transform: scale(1.05);
}

.menu-item-image {
  font-size: 3.5rem;
  margin-bottom: 1rem;
}

.menu-item h3 {
  font-size: 1.125rem;
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.menu-price {
  font-size: 1.25rem;
  font-weight: 700;
  color: #f97316;
}

.order-panel {
  position: fixed;
  right: 0;
  top: 0;
  width: 320px;
  height: 100vh;
  background: white;
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.1);
  padding: 2rem;
  overflow-y: auto;
}

.order-panel h2 {
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
  color: #1f2937;
}

.order-items {
  margin-bottom: 2rem;
}

.order-item {
  display: flex;
  justify-content: space-between;
  padding: 1rem 0;
  border-bottom: 1px solid #e5e7eb;
}

.order-total {
  padding: 1rem 0;
  border-top: 2px solid #f97316;
  font-size: 1.25rem;
  color: #1f2937;
  margin-bottom: 1rem;
}

.btn-confirm-order {
  width: 100%;
  padding: 1rem;
  background: #f97316;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  font-size: 1.125rem;
}
</style>

