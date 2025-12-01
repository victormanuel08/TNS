<template>
  <div class="autopago-container">
    <!-- Modal: Para llevar o comer aquí -->
    <div v-if="showOrderTypeModal" class="modal-overlay">
      <div class="modal-content">
        <h2 class="modal-title">¿Cómo deseas tu pedido?</h2>
        <div class="modal-options">
          <button class="option-btn" @click="selectOrderType('takeaway')">
            <span class="option-icon">🥡</span>
            <span class="option-label">Para Llevar</span>
          </button>
          <button class="option-btn" @click="selectOrderType('dinein')">
            <span class="option-icon">🍽️</span>
            <span class="option-label">Para Comer Aquí</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 1: Tipo documento y número (PRIMER PASO) -->
    <div v-if="showDocumentModal" class="modal-overlay">
      <div class="modal-content invoice-modal">
        <h2 class="modal-title">Ingresa tu Documento</h2>
        
        <div class="invoice-form">
          <div class="form-group">
            <label>Tipo de Documento:</label>
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" v-model="invoiceData.docType" value="cedula" />
                Cédula
              </label>
              <label class="radio-label">
                <input type="radio" v-model="invoiceData.docType" value="nit" />
                NIT
              </label>
            </div>
          </div>

          <div class="form-group">
            <label v-if="invoiceData.docType === 'cedula'">Número de Cédula:</label>
            <label v-else>NIT:</label>
            <input 
              v-model="invoiceData.document" 
              type="text" 
              :placeholder="invoiceData.docType === 'cedula' ? 'Ej: 1234567890' : 'Ej: 900123456-1'"
              class="form-input"
              @keyup.enter="validateDocument"
            />
          </div>

          <div v-if="isValidatingDocument" class="validating-message">
            <div class="spinner-small"></div>
            <p>Validando documento...</p>
          </div>

          <button 
            class="continue-btn" 
            @click="validateDocument"
            :disabled="!invoiceData.document || invoiceData.document.length < 7 || isValidatingDocument"
          >
            {{ isValidatingDocument ? 'Validando...' : 'Validar y Continuar' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 2: ¿Deseas factura electrónica a nombre propio? (DESPUÉS DE VALIDAR) -->
    <div v-if="showInvoiceModal" class="modal-overlay">
      <div class="modal-content">
        <h2 class="modal-title">¿Deseas factura electrónica a nombre propio?</h2>
        
        <div class="modal-options">
          <button 
            class="option-btn" 
            :class="{ active: wantsInvoice === true }"
            @click="wantsInvoice = true"
          >
            <span class="option-icon">✅</span>
            <span class="option-label">Sí, quiero factura</span>
          </button>
          <button 
            class="option-btn" 
            :class="{ active: wantsInvoice === false }"
            @click="wantsInvoice = false; proceedToPayment()"
          >
            <span class="option-icon">❌</span>
            <span class="option-label">No, gracias</span>
          </button>
        </div>

        <!-- Formulario de factura (si quiere factura) -->
        <div v-if="wantsInvoice === true" class="invoice-form">
          <div v-if="validatedData.name" class="info-message">
            ✅ Datos encontrados: {{ validatedData.name }}
          </div>

          <div class="form-group">
            <label>Naturaleza:</label>
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" v-model="invoiceData.nature" value="natural" />
                Natural
              </label>
              <label class="radio-label">
                <input type="radio" v-model="invoiceData.nature" value="juridica" />
                Jurídica
              </label>
            </div>
          </div>

          <div class="form-group">
            <label v-if="invoiceData.nature === 'natural'">Nombre Completo: <span class="required">*</span></label>
            <label v-else>Razón Social: <span class="required">*</span></label>
            <input 
              v-model="invoiceData.name" 
              type="text" 
              :placeholder="invoiceData.nature === 'natural' ? 'Nombre y Apellidos' : 'Razón Social de la Empresa'"
              class="form-input"
              required
            />
          </div>

          <div class="form-group">
            <label>Email: <span class="required">*</span></label>
            <input 
              v-model="invoiceData.email" 
              type="email" 
              placeholder="correo@ejemplo.com"
              class="form-input"
              required
            />
          </div>

          <div class="form-group">
            <label>Teléfono: <span class="required">*</span></label>
            <input 
              v-model="invoiceData.phone" 
              type="tel" 
              placeholder="Ej: 3001234567"
              class="form-input"
              required
            />
          </div>

          <button 
            class="continue-btn" 
            @click="proceedToPayment"
            :disabled="!isInvoiceFormValid"
          >
            Continuar al Pago
          </button>
        </div>
      </div>
    </div>

    <!-- Modal 3: Continúa en el datafono -->
    <div v-if="showPaymentModal" class="modal-overlay">
      <div class="modal-content payment-modal">
        <div class="payment-icon">💳</div>
        <h2 class="modal-title">Continúa en el Datafono</h2>
        <p class="payment-message">
          Por favor, completa el pago en el datafono físico.
        </p>
        <div class="payment-amount">
          <span class="amount-label">Total a pagar:</span>
          <span class="amount-value">${{ formatPrice(cartTotal) }}</span>
        </div>
        <div class="payment-loading">
          <div class="spinner"></div>
          <p>Esperando confirmación del pago...</p>
        </div>
        <button class="cancel-payment-btn" @click="cancelPayment">
          Cancelar Pago
        </button>
      </div>
    </div>

    <!-- Header -->
    <header class="autopago-header">
      <div class="logo-section">
        <h1 class="logo">🍔 FAST FOOD</h1>
        <p class="subtitle">Caja Autopago</p>
        <p v-if="orderType" class="order-type-badge">
          {{ orderType === 'takeaway' ? '🥡 Para Llevar' : '🍽️ Para Comer Aquí' }}
        </p>
      </div>
      <div class="cart-badge" v-if="cartTotalItems > 0" @click="showCart = true">
        <span class="badge-count">{{ cartTotalItems }}</span>
        🛒
      </div>
    </header>

    <!-- Búsqueda -->
    <div class="search-section">
      <input 
        v-model="searchQuery" 
        type="text" 
        placeholder="🔍 Buscar productos..." 
        class="search-input"
      />
    </div>

    <!-- Categorías -->
    <div class="categories-section">
      <button
        v-for="category in categories"
        :key="category.id"
        :class="['category-btn', { active: selectedCategory === category.id }]"
        @click="selectedCategory = category.id"
      >
        <span class="category-icon">{{ category.icon }}</span>
        <span class="category-name">{{ category.name }}</span>
      </button>
    </div>

    <!-- Productos -->
    <div class="products-section">
      <div 
        v-for="product in filteredProducts" 
        :key="product.id"
        class="product-card"
        @click="addToCart(product)"
      >
        <div class="product-image">
          <span class="product-emoji">{{ product.emoji }}</span>
        </div>
        <div class="product-info">
          <h3 class="product-name">{{ product.name }}</h3>
          <p class="product-description">{{ product.description }}</p>
          <div class="product-footer">
            <span class="product-price">${{ formatPrice(product.price) }}</span>
            <button class="add-btn">+ Agregar</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Carrito Sidebar -->
    <div v-if="showCart" class="cart-overlay" @click="showCart = false">
      <div class="cart-sidebar" @click.stop>
        <div class="cart-header">
          <h2>Tu Pedido</h2>
          <button class="close-btn" @click="showCart = false">✕</button>
        </div>

        <div class="cart-items" v-if="cart.length > 0">
          <div v-for="(item, index) in cart" :key="index" class="cart-item">
            <div class="cart-item-info">
              <span class="cart-item-emoji">{{ item.emoji }}</span>
              <div class="cart-item-details">
                <h4>{{ item.name }}</h4>
                <p class="cart-item-price">${{ formatPrice(item.price) }}</p>
              </div>
            </div>
            <div class="cart-item-controls">
              <button @click="decreaseQuantity(index)" class="qty-btn">-</button>
              <span class="qty-value">{{ item.quantity }}</span>
              <button @click="increaseQuantity(index)" class="qty-btn">+</button>
              <button @click="removeFromCart(index)" class="remove-btn">🗑️</button>
            </div>
          </div>
        </div>

        <div v-else class="empty-cart">
          <p>Tu carrito está vacío</p>
          <span class="empty-emoji">🛒</span>
        </div>

        <div v-if="cart.length > 0" class="cart-footer">
          <div class="cart-totals">
            <div class="total-line">
              <span>Subtotal:</span>
              <span>${{ formatPrice(cartSubtotal) }}</span>
            </div>
            <div class="total-line">
              <span>IVA (19%):</span>
              <span>${{ formatPrice(cartTax) }}</span>
            </div>
            <div class="total-line total-final">
              <span>Total:</span>
              <span>${{ formatPrice(cartTotal) }}</span>
            </div>
          </div>
          <button class="checkout-btn" @click="proceedToCheckout">
            Continuar al Pago
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'autopago'
})

// Mock Data - Categorías
const categories = [
  { id: 'all', name: 'Todo', icon: '🍽️' },
  { id: 'burgers', name: 'Hamburguesas', icon: '🍔' },
  { id: 'drinks', name: 'Bebidas', icon: '🥤' },
  { id: 'fries', name: 'Papas', icon: '🍟' },
  { id: 'desserts', name: 'Postres', icon: '🍰' },
  { id: 'chicken', name: 'Pollo', icon: '🍗' },
  { id: 'salads', name: 'Ensaladas', icon: '🥗' }
]

// Mock Data - Productos
const mockProducts = [
  // Hamburguesas
  { id: 1, name: 'Big Burger', description: 'Carne, queso, lechuga, tomate', price: 15900, emoji: '🍔', category: 'burgers' },
  { id: 2, name: 'Cheese Burger', description: 'Doble carne y queso', price: 18900, emoji: '🍔', category: 'burgers' },
  { id: 3, name: 'Bacon Burger', description: 'Con tocino crujiente', price: 21900, emoji: '🍔', category: 'burgers' },
  { id: 4, name: 'Chicken Burger', description: 'Pollo empanizado', price: 14900, emoji: '🍔', category: 'burgers' },
  { id: 5, name: 'Veggie Burger', description: '100% vegetal', price: 12900, emoji: '🍔', category: 'burgers' },
  
  // Bebidas
  { id: 6, name: 'Coca Cola', description: '500ml', price: 3500, emoji: '🥤', category: 'drinks' },
  { id: 7, name: 'Sprite', description: '500ml', price: 3500, emoji: '🥤', category: 'drinks' },
  { id: 8, name: 'Fanta', description: '500ml', price: 3500, emoji: '🥤', category: 'drinks' },
  { id: 9, name: 'Agua', description: '500ml', price: 2000, emoji: '💧', category: 'drinks' },
  { id: 10, name: 'Jugo de Naranja', description: 'Natural', price: 4500, emoji: '🧃', category: 'drinks' },
  
  // Papas
  { id: 11, name: 'Papas Fritas', description: 'Porción regular', price: 5500, emoji: '🍟', category: 'fries' },
  { id: 12, name: 'Papas Grandes', description: 'Porción grande', price: 7500, emoji: '🍟', category: 'fries' },
  { id: 13, name: 'Papas con Queso', description: 'Con queso derretido', price: 8500, emoji: '🍟', category: 'fries' },
  
  // Postres
  { id: 14, name: 'Helado de Vainilla', description: '2 bolas', price: 4500, emoji: '🍦', category: 'desserts' },
  { id: 15, name: 'Brownie', description: 'Con helado', price: 6500, emoji: '🍰', category: 'desserts' },
  { id: 16, name: 'Torta de Chocolate', description: 'Porción', price: 5500, emoji: '🎂', category: 'desserts' },
  
  // Pollo
  { id: 17, name: 'Nuggets (6pz)', description: 'Pollo empanizado', price: 8900, emoji: '🍗', category: 'chicken' },
  { id: 18, name: 'Alitas BBQ', description: '6 piezas', price: 12900, emoji: '🍗', category: 'chicken' },
  { id: 19, name: 'Pollo Frito', description: '2 piezas', price: 14900, emoji: '🍗', category: 'chicken' },
  
  // Ensaladas
  { id: 20, name: 'Ensalada César', description: 'Pollo, lechuga, crutones', price: 12900, emoji: '🥗', category: 'salads' },
  { id: 21, name: 'Ensalada Mixta', description: 'Verduras frescas', price: 9900, emoji: '🥗', category: 'salads' }
]

// Estado
const selectedCategory = ref('all')
const searchQuery = ref('')
const showCart = ref(false)
const cart = ref<Array<{ id: number, name: string, price: number, emoji: string, quantity: number }>>([])

// Flujo de pedido
const showOrderTypeModal = ref(true) // Mostrar al inicio
const orderType = ref<'takeaway' | 'dinein' | null>(null)

// Factura electrónica - Flujo en 3 pasos
const showDocumentModal = ref(false) // Paso 1: Tipo documento y número
const showInvoiceModal = ref(false) // Paso 2: ¿Quiere factura? (después de validar)
const showPaymentModal = ref(false) // Paso 3: Continúa en datafono
const wantsInvoice = ref<boolean | null>(null)
const isValidatingDocument = ref(false)
const validatedData = ref<any>({}) // Datos obtenidos de la API de validación
const invoiceData = ref({
  docType: 'cedula' as 'cedula' | 'nit',
  nature: 'natural' as 'natural' | 'juridica',
  document: '',
  name: '',
  email: '',
  phone: ''
})

// Computed
const filteredProducts = computed(() => {
  let products = mockProducts

  // Filtrar por categoría
  if (selectedCategory.value !== 'all') {
    products = products.filter(p => p.category === selectedCategory.value)
  }

  // Filtrar por búsqueda
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    products = products.filter(p => 
      p.name.toLowerCase().includes(query) || 
      p.description.toLowerCase().includes(query)
    )
  }

  return products
})

const cartTotalItems = computed(() => {
  return cart.value.reduce((sum, item) => sum + item.quantity, 0)
})

const cartSubtotal = computed(() => {
  return cart.value.reduce((sum, item) => sum + (item.price * item.quantity), 0)
})

const cartTax = computed(() => {
  return cartSubtotal.value * 0.19
})

const cartTotal = computed(() => {
  return cartSubtotal.value + cartTax.value
})

// Métodos
const formatPrice = (price: number) => {
  return new Intl.NumberFormat('es-CO').format(price)
}

const addToCart = (product: typeof mockProducts[0]) => {
  const existingItem = cart.value.find(item => item.id === product.id)
  
  if (existingItem) {
    existingItem.quantity++
  } else {
    cart.value.push({
      id: product.id,
      name: product.name,
      price: product.price,
      emoji: product.emoji,
      quantity: 1
    })
  }
  
  // Mostrar carrito automáticamente
  showCart.value = true
}

const increaseQuantity = (index: number) => {
  cart.value[index].quantity++
}

const decreaseQuantity = (index: number) => {
  if (cart.value[index].quantity > 1) {
    cart.value[index].quantity--
  } else {
    removeFromCart(index)
  }
}

const removeFromCart = (index: number) => {
  cart.value.splice(index, 1)
  if (cart.value.length === 0) {
    showCart.value = false
  }
}

// Métodos de flujo
const selectOrderType = (type: 'takeaway' | 'dinein') => {
  orderType.value = type
  showOrderTypeModal.value = false
}

const proceedToCheckout = () => {
  // Paso 1: Mostrar modal de documento
  showCart.value = false
  showDocumentModal.value = true
  // Resetear datos
  invoiceData.value = {
    docType: 'cedula',
    nature: 'natural',
    document: '',
    name: '',
    email: '',
    phone: ''
  }
}

const validateDocument = async () => {
  if (!invoiceData.value.document || invoiceData.value.document.length < 7) {
    return
  }

  isValidatingDocument.value = true

  // TODO: Llamar API de validación de documento
  // Ejemplo: await $fetch('/api/validate-document/', { method: 'POST', body: { docType, document } })
  // Por ahora mockeado
  try {
    // Simular llamada API
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    // Mock: Respuesta de API de validación
    if (invoiceData.value.docType === 'nit') {
      invoiceData.value.nature = 'juridica'
      validatedData.value = {
        name: 'EMPRESA MOCK S.A.S.',
        nature: 'juridica'
      }
      invoiceData.value.name = 'EMPRESA MOCK S.A.S.' // Prellenar si la API lo trae
    } else {
      invoiceData.value.nature = 'natural'
      validatedData.value = {
        name: 'Juan Pérez',
        nature: 'natural'
      }
      invoiceData.value.name = 'Juan Pérez' // Prellenar si la API lo trae
    }

    // Cerrar modal de documento y abrir modal de factura
    showDocumentModal.value = false
    showInvoiceModal.value = true
    wantsInvoice.value = null
  } catch (error) {
    console.error('Error validando documento:', error)
    alert('Error al validar documento. Intenta nuevamente.')
  } finally {
    isValidatingDocument.value = false
  }
}

const proceedToPayment = () => {
  // Validar formulario si quiere factura
  if (wantsInvoice.value === true && !isInvoiceFormValid.value) {
    return
  }

  // Cerrar modal de factura
  showInvoiceModal.value = false

  // Preparar datos del pedido
  const orderData = {
    orderType: orderType.value,
    cart: cart.value,
    total: cartTotal.value,
    invoice: wantsInvoice.value ? {
      docType: invoiceData.value.docType,
      nature: invoiceData.value.nature,
      document: invoiceData.value.document,
      name: invoiceData.value.name,
      email: invoiceData.value.email,
      phone: invoiceData.value.phone
    } : null
  }

  console.log('Datos del pedido:', orderData)

  // Mostrar modal de pago en datafono
  showPaymentModal.value = true

  // TODO: Integrar con API de pago real
  // Aquí se llamaría al endpoint que comunica con el servidor local
  // Por ahora mockeado
  setTimeout(() => {
    // Simular pago exitoso después de 3 segundos (mock)
    // En producción, esto vendría del servidor local vía WebSocket o polling
    console.log('Pago procesado (mock)')
  }, 3000)
}

const cancelPayment = () => {
  showPaymentModal.value = false
  showCart.value = true
}

// Validación del formulario de factura
const isInvoiceFormValid = computed(() => {
  if (wantsInvoice.value !== true) return true
  
  return !!(
    invoiceData.value.docType &&
    invoiceData.value.nature &&
    invoiceData.value.document &&
    invoiceData.value.document.length >= 7 &&
    invoiceData.value.name &&
    invoiceData.value.name.length >= 3 &&
    invoiceData.value.email &&
    invoiceData.value.email.includes('@') &&
    invoiceData.value.phone &&
    invoiceData.value.phone.length >= 7
  )
})
</script>

<style scoped>
.autopago-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #ff6b6b 0%, #ffa500 100%);
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

/* Header */
.autopago-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 1.5rem 2rem;
  border-radius: 20px;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.logo-section h1 {
  margin: 0;
  font-size: 2.5rem;
  color: #ff6b6b;
  font-weight: 900;
}

.subtitle {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.cart-badge {
  position: relative;
  font-size: 2rem;
  cursor: pointer;
  padding: 0.5rem 1rem;
  background: #ff6b6b;
  border-radius: 50px;
  transition: transform 0.2s;
}

.cart-badge:hover {
  transform: scale(1.1);
}

.badge-count {
  position: absolute;
  top: -8px;
  right: -8px;
  background: #ffa500;
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: bold;
}

/* Búsqueda */
.search-section {
  margin-bottom: 1.5rem;
}

.search-input {
  width: 100%;
  padding: 1rem 1.5rem;
  font-size: 1.1rem;
  border: none;
  border-radius: 50px;
  background: white;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  outline: none;
}

.search-input:focus {
  box-shadow: 0 4px 25px rgba(255, 107, 107, 0.3);
}

/* Categorías */
.categories-section {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  overflow-x: auto;
  padding-bottom: 0.5rem;
  scrollbar-width: none;
}

.categories-section::-webkit-scrollbar {
  display: none;
}

.category-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  border: none;
  border-radius: 15px;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
  min-width: 100px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.category-btn:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.2);
}

.category-btn.active {
  background: #ff6b6b;
  color: white;
  transform: translateY(-5px);
}

.category-icon {
  font-size: 2rem;
}

.category-name {
  font-size: 0.85rem;
  font-weight: 600;
}

/* Productos */
.products-section {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.product-card {
  background: white;
  border-radius: 20px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.product-card:hover {
  transform: translateY(-10px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
}

.product-image {
  background: linear-gradient(135deg, #ff6b6b, #ffa500);
  padding: 2rem;
  text-align: center;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.product-emoji {
  font-size: 5rem;
}

.product-info {
  padding: 1.5rem;
}

.product-name {
  margin: 0 0 0.5rem 0;
  font-size: 1.3rem;
  color: #333;
  font-weight: 700;
}

.product-description {
  margin: 0 0 1rem 0;
  color: #666;
  font-size: 0.9rem;
}

.product-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.product-price {
  font-size: 1.5rem;
  font-weight: 900;
  color: #ff6b6b;
}

.add-btn {
  background: #ff6b6b;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 50px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.add-btn:hover {
  background: #ff5252;
  transform: scale(1.05);
}

/* Carrito */
.cart-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.cart-sidebar {
  width: 100%;
  max-width: 450px;
  background: white;
  height: 100vh;
  overflow-y: auto;
  animation: slideIn 0.3s;
  display: flex;
  flex-direction: column;
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.cart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem;
  border-bottom: 2px solid #f0f0f0;
}

.cart-header h2 {
  margin: 0;
  font-size: 1.8rem;
  color: #333;
}

.close-btn {
  background: #f0f0f0;
  border: none;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #ff6b6b;
  color: white;
}

.cart-items {
  flex: 1;
  padding: 1rem;
}

.cart-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #f0f0f0;
  gap: 1rem;
}

.cart-item-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

.cart-item-emoji {
  font-size: 2.5rem;
}

.cart-item-details h4 {
  margin: 0 0 0.25rem 0;
  font-size: 1.1rem;
  color: #333;
}

.cart-item-price {
  margin: 0;
  color: #ff6b6b;
  font-weight: 700;
  font-size: 1.1rem;
}

.cart-item-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.qty-btn {
  background: #f0f0f0;
  border: none;
  width: 35px;
  height: 35px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  font-weight: 700;
  transition: all 0.2s;
}

.qty-btn:hover {
  background: #ff6b6b;
  color: white;
}

.qty-value {
  font-size: 1.2rem;
  font-weight: 700;
  min-width: 30px;
  text-align: center;
}

.remove-btn {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
  transition: transform 0.2s;
}

.remove-btn:hover {
  transform: scale(1.2);
}

.empty-cart {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
}

.empty-emoji {
  font-size: 5rem;
  margin-top: 1rem;
}

.cart-footer {
  padding: 1.5rem;
  border-top: 2px solid #f0f0f0;
  background: #f9f9f9;
}

.cart-totals {
  margin-bottom: 1.5rem;
}

.total-line {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  font-size: 1rem;
  color: #666;
}

.total-final {
  font-size: 1.5rem;
  font-weight: 900;
  color: #333;
  border-top: 2px solid #ddd;
  padding-top: 1rem;
  margin-top: 0.5rem;
}

.checkout-btn {
  width: 100%;
  background: #ff6b6b;
  color: white;
  border: none;
  padding: 1.25rem;
  border-radius: 15px;
  font-size: 1.2rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
}

.checkout-btn:hover {
  background: #ff5252;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
}

/* Modales */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.3s;
}

.modal-content {
  background: white;
  border-radius: 25px;
  padding: 3rem;
  max-width: 600px;
  width: 90%;
  text-align: center;
  animation: slideUp 0.3s;
}

@keyframes slideUp {
  from {
    transform: translateY(50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.modal-title {
  font-size: 2rem;
  color: #333;
  margin: 0 0 2rem 0;
  font-weight: 700;
}

.modal-options {
  display: flex;
  gap: 1.5rem;
  justify-content: center;
  flex-wrap: wrap;
}

.option-btn {
  flex: 1;
  min-width: 200px;
  padding: 2rem;
  border: 3px solid #f0f0f0;
  border-radius: 20px;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.option-btn:hover {
  border-color: #ff6b6b;
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(255, 107, 107, 0.2);
}

.option-btn.active {
  border-color: #ff6b6b;
  background: #fff5f5;
}

.option-icon {
  font-size: 4rem;
}

.option-label {
  font-size: 1.3rem;
  font-weight: 700;
  color: #333;
}

/* Formulario de factura */
.invoice-modal {
  max-width: 700px;
  text-align: left;
}

.invoice-form {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 2px solid #f0f0f0;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
  font-size: 1rem;
}

.radio-group {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: 2px solid #f0f0f0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  flex: 1;
}

.radio-label:hover {
  border-color: #ff6b6b;
  background: #fff5f5;
}

.radio-label input[type="radio"] {
  margin: 0;
  cursor: pointer;
}

.radio-label input[type="radio"]:checked + span,
.radio-label:has(input[type="radio"]:checked) {
  border-color: #ff6b6b;
  background: #fff5f5;
}

.form-input {
  width: 100%;
  padding: 1rem;
  border: 2px solid #f0f0f0;
  border-radius: 10px;
  font-size: 1rem;
  transition: all 0.2s;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #ff6b6b;
  box-shadow: 0 0 0 3px rgba(255, 107, 107, 0.1);
}

.continue-btn {
  width: 100%;
  background: #ff6b6b;
  color: white;
  border: none;
  padding: 1.25rem;
  border-radius: 15px;
  font-size: 1.2rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s;
  margin-top: 1.5rem;
  box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
}

.continue-btn:hover:not(:disabled) {
  background: #ff5252;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
}

.continue-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  box-shadow: none;
}

/* Modal de Pago */
.payment-modal {
  text-align: center;
}

.payment-icon {
  font-size: 5rem;
  margin-bottom: 1rem;
}

.payment-message {
  font-size: 1.2rem;
  color: #666;
  margin: 1rem 0 2rem 0;
}

.payment-amount {
  background: #f9f9f9;
  padding: 1.5rem;
  border-radius: 15px;
  margin: 2rem 0;
}

.amount-label {
  display: block;
  font-size: 1rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.amount-value {
  display: block;
  font-size: 2.5rem;
  font-weight: 900;
  color: #ff6b6b;
}

.payment-loading {
  margin: 2rem 0;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f0f0f0;
  border-top-color: #ff6b6b;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.payment-loading p {
  color: #666;
  font-size: 1rem;
}

.cancel-payment-btn {
  margin-top: 1.5rem;
  background: transparent;
  color: #666;
  border: 2px solid #ddd;
  padding: 0.75rem 2rem;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-payment-btn:hover {
  border-color: #ff6b6b;
  color: #ff6b6b;
}

.required {
  color: #ff6b6b;
}

.validating-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  margin: 1rem 0;
  color: #666;
}

.spinner-small {
  width: 30px;
  height: 30px;
  border: 3px solid #f0f0f0;
  border-top-color: #ff6b6b;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.info-message {
  background: #d4edda;
  color: #155724;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.95rem;
  border: 1px solid #c3e6cb;
}

.order-type-badge {
  margin: 0.5rem 0 0 0;
  font-size: 0.85rem;
  color: #666;
  font-weight: 600;
}

/* Responsive */
@media (max-width: 768px) {
  .autopago-container {
    padding: 1rem;
  }

  .products-section {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
  }

  .cart-sidebar {
    max-width: 100%;
  }

  .modal-content {
    padding: 2rem 1.5rem;
  }

  .modal-options {
    flex-direction: column;
  }

  .option-btn {
    min-width: 100%;
  }

  .radio-group {
    flex-direction: column;
  }
}
</style>
