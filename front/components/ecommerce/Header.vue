<template>
  <header class="ecommerce-header">
    <div class="container">
      <div class="header-content">
        <div class="logo-section">
          <div class="logo">
            <img v-if="company?.imageUrl" :src="company.imageUrl" :alt="companyName" />
            <span v-else>{{ companyName }}</span>
          </div>
        </div>
        
        <nav class="navigation">
          <div class="nav-links">
            <a href="#" class="nav-link">Inicio</a>
            <a href="#" class="nav-link">Categorías</a>
            <a href="#" class="nav-link">Ofertas</a>
            <a href="#" class="nav-link">Contacto</a>
          </div>
        </nav>

        <div class="header-actions">
          <button class="search-btn">
            <i>🔍</i>
          </button>
          <button class="cart-btn" @click="toggleCart">
            <i>🛒</i>
            <span class="cart-count" v-if="cartCount > 0">{{ cartCount }}</span>
          </button>
          <button class="user-btn">
            <i>👤</i>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
const { company, companyName } = useCompany()

const cartCount = ref(0)
const isCartOpen = ref(false)

const toggleCart = () => {
  isCartOpen.value = !isCartOpen.value
  // Aquí se integrará con el carrito después
}
</script>

<style scoped>
.ecommerce-header {
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow);
  position: sticky;
  top: 0;
  z-index: 100;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 70px;
}

.logo-section .logo {
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--primary-color);
}

.logo-section .logo img {
  height: 40px;
  width: auto;
}

.navigation .nav-links {
  display: flex;
  gap: 2rem;
}

.nav-link {
  color: var(--text-primary);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.nav-link:hover {
  color: var(--primary-color);
}

.header-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.search-btn,
.cart-btn,
.user-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: var(--border-radius);
  transition: background-color 0.2s;
}

.search-btn:hover,
.cart-btn:hover,
.user-btn:hover {
  background-color: var(--bg-secondary);
}

.cart-btn {
  position: relative;
}

.cart-count {
  position: absolute;
  top: -5px;
  right: -5px;
  background: var(--accent-color);
  color: white;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 768px) {
  .navigation {
    display: none;
  }
  
  .header-content {
    height: 60px;
  }
}
</style>