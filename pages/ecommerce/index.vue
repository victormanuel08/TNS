<template>
  <div class="ecommerce-home">
    <!-- Hero Section -->
    <section class="hero-section">
      <div class="hero-background">
        <div class="container">
          <div class="hero-content">
            <h1 class="hero-title">Bienvenido a {{ companyName }}</h1>
            <p class="hero-subtitle">Descubre productos increíbles con ofertas exclusivas</p>
            <div class="hero-actions">
              <button class="btn btn-primary">Comprar Ahora</button>
              <button class="btn btn-secondary">Ver Ofertas</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Featured Categories -->
    <section class="categories-section">
      <div class="container">
        <h2 class="section-title">Categorías Populares</h2>
        <div class="categories-grid">
          <div 
            v-for="category in categories" 
            :key="category.id" 
            class="category-card"
          >
            <div class="category-icon">{{ category.icon }}</div>
            <h3 class="category-name">{{ category.name }}</h3>
            <p class="category-count">{{ category.count }} productos</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Featured Products -->
    <section class="products-section">
      <div class="container">
        <div class="section-header">
          <h2 class="section-title">Productos Destacados</h2>
          <button class="view-all-btn">Ver Todos</button>
        </div>
        <div class="products-grid">
          <div 
            v-for="product in featuredProducts" 
            :key="product.id" 
            class="product-card"
          >
            <div class="product-image">
              <div class="image-placeholder">🛍️</div>
              <div class="product-badge" v-if="product.badge">{{ product.badge }}</div>
            </div>
            <div class="product-info">
              <h3 class="product-name">{{ product.name }}</h3>
              <p class="product-description">{{ product.description }}</p>
              <div class="product-price-section">
                <span class="product-price">${{ product.price }}</span>
                <span class="product-old-price" v-if="product.oldPrice">${{ product.oldPrice }}</span>
              </div>
              <div class="product-rating">
                <span class="stars">★★★★★</span>
                <span class="rating-count">({{ product.rating }})</span>
              </div>
              <button class="add-to-cart-btn">Añadir al Carrito</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Promotional Banner -->
    <section class="promo-section">
      <div class="container">
        <div class="promo-banner">
          <div class="promo-content">
            <h3 class="promo-title">Oferta Especial</h3>
            <p class="promo-text">Hasta 50% de descuento en productos seleccionados</p>
            <button class="btn btn-promo">Aprovechar Oferta</button>
          </div>
          <div class="promo-image">
            <div class="promo-placeholder">🎁</div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
definePageMeta({
  layout: 'ecommerce'
})

const { company, companyName } = useCompany()

// Datos de ejemplo - luego vendrán de la API
const categories = ref([
  { id: 1, name: 'Electrónicos', count: 156, icon: '📱' },
  { id: 2, name: 'Moda', count: 89, icon: '👕' },
  { id: 3, name: 'Hogar', count: 203, icon: '🏠' },
  { id: 4, name: 'Deportes', count: 67, icon: '⚽' },
  { id: 5, name: 'Juguetes', count: 124, icon: '🧸' },
  { id: 6, name: 'Belleza', count: 98, icon: '💄' }
])

const featuredProducts = ref([
  {
    id: 1,
    name: 'Smartphone Premium',
    description: 'Último modelo con características avanzadas',
    price: 299.99,
    oldPrice: 399.99,
    rating: 4.5,
    badge: 'Oferta'
  },
  {
    id: 2,
    name: 'Auriculares Inalámbricos',
    description: 'Sonido de alta calidad con cancelación de ruido',
    price: 89.99,
    rating: 4.8,
    badge: 'Nuevo'
  },
  {
    id: 3,
    name: 'Tablet Pro',
    description: 'Perfecta para trabajo y entretenimiento',
    price: 199.99,
    oldPrice: 249.99,
    rating: 4.3
  },
  {
    id: 4,
    name: 'Smart Watch',
    description: 'Monitoriza tu salud y actividad física',
    price: 149.99,
    rating: 4.6,
    badge: 'Popular'
  },
  {
    id: 5,
    name: 'Cámara Digital',
    description: 'Captura momentos especiales con alta resolución',
    price: 349.99,
    oldPrice: 449.99,
    rating: 4.7
  },
  {
    id: 6,
    name: 'Portátil Ultraligero',
    description: 'Ideal para trabajo remoto y estudios',
    price: 599.99,
    rating: 4.4,
    badge: 'Destacado'
  }
])
</script>

<style scoped>
.ecommerce-home {
  min-height: 100vh;
}

/* Hero Section */
.hero-section {
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
  color: white;
  padding: 4rem 0;
}

.hero-content {
  text-align: center;
  max-width: 600px;
  margin: 0 auto;
}

.hero-title {
  font-size: 3rem;
  font-weight: bold;
  margin-bottom: 1rem;
  line-height: 1.2;
}

.hero-subtitle {
  font-size: 1.25rem;
  margin-bottom: 2rem;
  opacity: 0.9;
}

.hero-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

.btn {
  padding: 0.75rem 2rem;
  border: none;
  border-radius: var(--border-radius);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  display: inline-block;
}

.btn-primary {
  background: white;
  color: var(--primary-color);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.btn-secondary {
  background: transparent;
  color: white;
  border: 2px solid white;
}

.btn-secondary:hover {
  background: white;
  color: var(--primary-color);
}

/* Sections Common */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.categories-section,
.products-section,
.promo-section {
  padding: 4rem 0;
}

.section-title {
  font-size: 2.5rem;
  text-align: center;
  margin-bottom: 3rem;
  color: var(--text-primary);
}

/* Categories Grid */
.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.category-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 2rem 1rem;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
}

.category-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow);
  border-color: var(--primary-color);
}

.category-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.category-name {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}

.category-count {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

/* Products Section */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.view-all-btn {
  background: none;
  border: 2px solid var(--primary-color);
  color: var(--primary-color);
  padding: 0.5rem 1.5rem;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.view-all-btn:hover {
  background: var(--primary-color);
  color: white;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 2rem;
}

.product-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  overflow: hidden;
  transition: all 0.3s ease;
}

.product-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow);
}

.product-image {
  position: relative;
  height: 200px;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-placeholder {
  font-size: 4rem;
  opacity: 0.7;
}

.product-badge {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: var(--accent-color);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.product-info {
  padding: 1.5rem;
}

.product-name {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}

.product-description {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 1rem;
  line-height: 1.4;
}

.product-price-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.product-price {
  font-size: 1.25rem;
  font-weight: bold;
  color: var(--primary-color);
}

.product-old-price {
  font-size: 1rem;
  color: var(--text-secondary);
  text-decoration: line-through;
}

.product-rating {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.stars {
  color: #FFD700;
}

.rating-count {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.add-to-cart-btn {
  width: 100%;
  background: var(--primary-color);
  color: white;
  border: none;
  padding: 0.75rem;
  border-radius: var(--border-radius);
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.add-to-cart-btn:hover {
  background: var(--secondary-color);
}

/* Promo Section */
.promo-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.promo-banner {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3rem;
  align-items: center;
}

.promo-content {
  text-align: left;
}

.promo-title {
  font-size: 2.5rem;
  font-weight: bold;
  margin-bottom: 1rem;
}

.promo-text {
  font-size: 1.125rem;
  margin-bottom: 2rem;
  opacity: 0.9;
}

.btn-promo {
  background: white;
  color: var(--primary-color);
  border: none;
  padding: 1rem 2rem;
  font-size: 1.125rem;
  font-weight: 600;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: transform 0.2s;
}

.btn-promo:hover {
  transform: translateY(-2px);
}

.promo-image {
  display: flex;
  justify-content: center;
  align-items: center;
}

.promo-placeholder {
  font-size: 8rem;
  opacity: 0.8;
}

/* Responsive */
@media (max-width: 768px) {
  .hero-title {
    font-size: 2rem;
  }

  .hero-actions {
    flex-direction: column;
    align-items: center;
  }

  .btn {
    width: 200px;
  }

  .section-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }

  .categories-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .promo-banner {
    grid-template-columns: 1fr;
    text-align: center;
    gap: 2rem;
  }

  .promo-content {
    text-align: center;
  }

  .promo-placeholder {
    font-size: 6rem;
  }
}

@media (max-width: 480px) {
  .categories-grid {
    grid-template-columns: 1fr;
  }

  .products-grid {
    grid-template-columns: 1fr;
  }

  .hero-section,
  .categories-section,
  .products-section {
    padding: 2rem 0;
  }
}
</style>