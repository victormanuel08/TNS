<template>
  <!-- MODAL DE CARGA -->
  <div v-if="loadingPage" class="loading-page-overlay">
    <div class="loading-page-content">
      <img
        v-if="companyLogo"
        :src="companyLogo"
        alt="Logo"
        class="loading-logo"
      />
      <div v-else class="loading-logo-placeholder">
        <h1>{{ loadingSubdomain }}</h1>
      </div>
      <div class="loading-spinner-large"></div>
      <p class="loading-text">Cargando...</p>
    </div>
  </div>

  <div v-else class="ecommerce-container" :style="{ ...containerStyles, ...themeStyles }">
    <!-- HEADER -->
    <header class="ecommerce-header" :style="headerStyles">
      <div class="header-left">
        <div class="logo-block">
          <img
            v-if="ecommerceConfig.logo_url || companyLogo"
            :src="ecommerceConfig.logo_url || companyLogo"
            alt="Logo de la empresa"
            class="company-logo"
            @click="handleLogoClick"
            @dblclick="handleLogoDoubleClick"
            style="cursor: pointer;"
          />
          <h1 
            v-else
            class="company-name"
            @click="handleLogoClick"
            @dblclick="handleLogoDoubleClick"
            style="cursor: pointer;"
          >
            {{ companyName }}
          </h1>
          <h1 v-if="companyLogo" class="company-name">{{ companyName }}</h1>
        </div>
        <p class="company-tagline" v-if="heroSubtitle">
          {{ heroSubtitle }}
        </p>
      </div>

      <div v-if="ecommerceConfig.mostrar_menu" class="header-center">
        <nav class="main-nav">
          <template v-if="ecommerceConfig.menu_items && ecommerceConfig.menu_items.length > 0">
            <button
              v-for="(item, index) in ecommerceConfig.menu_items"
              :key="index"
              class="nav-link"
              @click="handleMenuClick(item)"
            >
              <span v-if="item.icono" class="nav-link-icon">{{ item.icono }}</span>
              {{ item.texto }}
            </button>
          </template>
          <template v-else>
            <button class="nav-link" @click="scrollToSection('hero')">Inicio</button>
            <button class="nav-link" @click="scrollToSection('about')">Nosotros</button>
            <button class="nav-link" @click="scrollToSection('products')">Productos</button>
            <button class="nav-link" @click="scrollToSection('contact')">Contáctanos</button>
          </template>
        </nav>
      </div>

      <div class="header-right">
        <button v-if="isAdmin" class="admin-button active" @click="showAdminPanel = true" title="Panel de Administración">
          ⚙️ Admin
        </button>
        <button class="cart-button" @click="showCart = true">
          <span class="cart-icon">🛒</span>
          <span class="cart-text">Carrito</span>
          <span v-if="cartTotalItems > 0" class="cart-badge-ecom">{{ cartTotalItems }}</span>
        </button>
      </div>
    </header>

    <!-- CONTENIDO PRINCIPAL -->
    <div class="main-content">

    <!-- MÁS BUSCADOS -->
    <section id="featured" class="featured-section" v-if="highlightedProducts.length">
      <div class="section-header">
        <h3>Más buscados</h3>
      </div>
      <div class="product-grid featured-grid">
        <div
          v-for="product in highlightedProducts"
          :key="product.id"
          class="product-card-ecom product-card-featured"
          @click="openProductModal(product)"
        >
          <h4 class="product-name-featured">{{ product.name }}</h4>
          <div class="product-image-ecom">
            <img
              v-if="product.imagen_url"
              :src="product.imagen_url"
              :alt="product.name"
            />
            <div v-else class="product-placeholder">
              {{ product.emoji }}
            </div>
          </div>
          <div class="product-footer-featured">
            <span class="product-price-ecom">
              ${{ formatPrice(product.price) }}
            </span>
            <button class="add-btn-ecom" @click.stop="addToCart(product)">
              Agregar
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- CATÁLOGO -->
    <section id="products" class="catalog-section">
      <div class="section-header">
        <h3>Catálogo</h3>
      </div>

      <div class="catalog-layout">
        <aside class="categories-sidebar" v-if="categories.length">
          <!-- Buscador en el banner de categorías -->
          <div class="search-bar-categories">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="🔍 Buscar productos..."
              class="search-input-categories"
            />
          </div>
          
          <!-- Botón Todos -->
          <button
            class="category-pill"
            :class="{ active: !selectedCategoryId && !searchQuery.trim() }"
            @click="selectedCategoryId = null; searchQuery = ''"
          >
            Todos
          </button>
          
          <!-- Categorías -->
          <button
            v-for="cat in categories"
            :key="cat.id"
            class="category-pill"
            :class="{ active: selectedCategoryId === cat.id }"
            @click="selectedCategoryId = cat.id; searchQuery = ''"
          >
            <span class="category-emoji">{{ cat.icon }}</span>
            <span class="category-label">{{ cat.name }}</span>
          </button>
        </aside>

        <div class="catalog-products" @scroll="handleScroll">
          <div v-if="loadingProducts" class="loading-state">
            <div class="spinner"></div>
            <p>Cargando productos...</p>
          </div>
          <div v-else-if="productsError" class="error-state">
            <p>{{ productsError }}</p>
          </div>
          <div v-else-if="filteredProductsAll.length === 0" class="empty-state">
            <p>No encontramos productos para tu búsqueda.</p>
          </div>
          <div v-else class="product-grid">
            <div
              v-for="product in filteredProducts"
              :key="product.id"
              class="product-card-ecom"
              @click="openProductModal(product)"
            >
              <div class="product-image-ecom">
                <img
                  v-if="product.imagen_url"
                  :src="product.imagen_url"
                  :alt="product.name"
                />
                <div v-else class="product-placeholder">
                  {{ product.emoji }}
                </div>
              </div>
              <div class="product-body">
                <h4 class="product-name-ecom">{{ product.name }}</h4>
                <p class="product-category" v-if="product.categoryName">
                  {{ product.categoryName }}
                </p>
                <div class="product-footer-ecom">
                  <span class="product-price-ecom">
                    ${{ formatPrice(product.price) }}
                  </span>
                  <button class="add-btn-ecom" @click.stop="addToCart(product)">
                    Agregar
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div v-if="isLoadingMore" class="loading-more">
            <div class="spinner"></div>
            <p>Cargando más productos...</p>
          </div>
          <div v-else-if="hasMoreProducts && filteredProducts.length > 0" class="load-more-hint">
            <p>Desplázate para ver más productos</p>
          </div>
        </div>
      </div>
    </section>

    </div>
    <!-- FOOTER -->
    <footer v-if="ecommerceConfig.mostrar_footer" class="ecommerce-footer">
      <div class="footer-content">
        <!-- Secciones del Footer desde Config -->
        <template v-for="(section, sectionIndex) in ecommerceConfig.footer_sections" :key="sectionIndex">
          <div v-if="section && section.titulo" class="footer-section">
            <h4>{{ section.titulo }}</h4>
            <template v-if="section.links && section.links.length > 0">
              <template v-for="(link, linkIndex) in section.links" :key="linkIndex">
                <a
                  v-if="link.tipo === 'external'"
                  :href="link.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="footer-link"
                >
                  <span v-if="link.icono" class="footer-link-icon">{{ link.icono }}</span>
                  {{ link.titulo }}
                </a>
                <button
                  v-else-if="link.tipo === 'modal'"
                  @click="handleFooterLink(link)"
                  class="footer-link"
                >
                  <span v-if="link.icono" class="footer-link-icon">{{ link.icono }}</span>
                  {{ link.titulo }}
                </button>
                <a
                  v-else-if="link.tipo === 'file'"
                  :href="link.url"
                  :download="link.titulo"
                  class="footer-link"
                >
                  <span v-if="link.icono" class="footer-link-icon">{{ link.icono }}</span>
                  {{ link.titulo }}
                </a>
              </template>
            </template>
          </div>
        </template>
        
        <!-- Secciones por defecto si no hay configuradas -->
        <div v-if="!ecommerceConfig.footer_sections || ecommerceConfig.footer_sections.length === 0" class="footer-section">
          <h4>Sobre nosotros</h4>
          <button class="footer-link" @click="showAboutModal = true">
            Conoce más
          </button>
        </div>
        <div v-if="!ecommerceConfig.footer_sections || ecommerceConfig.footer_sections.length === 0" class="footer-section">
          <h4>Contáctanos</h4>
          <a
            v-if="whatsappLink"
            :href="whatsappLink"
            target="_blank"
            rel="noopener noreferrer"
            class="footer-link"
          >
            💬 WhatsApp
          </a>
          <button v-else class="footer-link" @click="showContactModal = true">
            Ver información
          </button>
        </div>
        
        <!-- Footer Links (legacy) - Mostrar siempre si existen -->
        <template v-if="ecommerceConfig.footer_links && ecommerceConfig.footer_links.length > 0">
          <div class="footer-section">
            <h4>Enlaces</h4>
            <template v-for="(link, index) in ecommerceConfig.footer_links" :key="index">
              <a
                v-if="link.tipo === 'external'"
                :href="link.url"
                target="_blank"
                rel="noopener noreferrer"
                class="footer-link"
              >
                <span v-if="link.icono" class="footer-link-icon">{{ link.icono }}</span>
                {{ link.titulo }}
              </a>
              <button
                v-else-if="link.tipo === 'modal'"
                class="footer-link"
                @click="handleFooterLink(link)"
              >
                <span v-if="link.icono" class="footer-link-icon">{{ link.icono }}</span>
                {{ link.titulo }}
              </button>
              <a
                v-else-if="link.tipo === 'file'"
                :href="link.url"
                :download="link.titulo"
                class="footer-link"
              >
                <span v-if="link.icono" class="footer-link-icon">{{ link.icono }}</span>
                {{ link.titulo }}
              </a>
            </template>
          </div>
        </template>
      </div>
      <div v-if="ecommerceConfig.footer_texto_logo" class="footer-logo-text">
        {{ ecommerceConfig.footer_texto_logo }}
      </div>
    </footer>

    <!-- MODAL DETALLE PRODUCTO -->
    <div v-if="selectedProduct" class="modal-overlay" @click.self="selectedProduct = null">
      <div class="modal-content product-modal">
        <button class="modal-close" @click="selectedProduct = null">✕</button>
        <div class="product-modal-body">
          <div class="product-modal-image-wrapper">
            <div class="product-modal-image" :class="{ 'has-image': selectedProduct.imagen_url }">
              <img
                v-if="selectedProduct.imagen_url"
                :src="selectedProduct.imagen_url"
                :alt="selectedProduct.name"
                class="product-modal-img-3d"
                @error="handleImageError"
              />
              <div v-else class="product-placeholder product-modal-emoji">
                {{ selectedProduct.emoji }}
              </div>
              <p class="product-modal-price-overlay">
                ${{ formatPrice(selectedProduct.price) }}
              </p>
            </div>
          </div>
          <div class="product-modal-info">
            <h3>{{ selectedProduct.name }}</h3>
            <p v-if="selectedProduct.categoryName" class="product-category">
              {{ selectedProduct.categoryName }}
            </p>
            <div v-if="selectedProduct.descripcion && selectedProduct.descripcion !== selectedProduct.name" class="product-description-scroll">
              <p class="product-description">{{ selectedProduct.descripcion }}</p>
            </div>
            <div v-if="selectedProduct.pdf_url" class="product-pdf-link">
              <a :href="selectedProduct.pdf_url" target="_blank" rel="noopener noreferrer" class="pdf-download-btn">
                📄 Descargar PDF
              </a>
            </div>
            <div class="product-modal-actions">
              <button class="primary-btn full-width" @click="addToCart(selectedProduct)">
                Agregar al carrito
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL CARRITO -->
    <div v-if="showCart" class="modal-overlay" @click.self="showCart = false">
      <div class="modal-content cart-modal">
        <div class="cart-header">
          <h3>Carrito de Compras</h3>
          <button class="modal-close" @click="showCart = false">✕</button>
        </div>
        <div v-if="cart.length === 0" class="empty-cart">
          <div class="empty-cart-icon">🛒</div>
          <p>Tu carrito está vacío</p>
          <button class="primary-btn" @click="showCart = false">Seguir comprando</button>
        </div>
        <div v-else class="cart-body">
          <div class="cart-items-scroll">
            <div
              v-for="(item, index) in cart"
              :key="item.id + '-' + index"
              class="cart-item-card"
            >
              <div class="cart-item-main">
                <div class="cart-item-details">
                  <h4 class="cart-item-name">{{ item.name }}</h4>
                  <p class="cart-item-unit-price">${{ formatPrice(item.price) }} c/u</p>
                </div>
                <div class="cart-item-total">
                  <strong>${{ formatPrice(item.price * item.quantity) }}</strong>
                </div>
              </div>
              <div class="cart-item-controls">
                <button 
                  class="cart-btn-qty" 
                  @click="updateQuantity(index, item.quantity - 1)"
                  :disabled="item.quantity <= 1"
                >
                  −
                </button>
                <span class="cart-qty-display">{{ item.quantity }}</span>
                <button 
                  class="cart-btn-qty" 
                  @click="updateQuantity(index, item.quantity + 1)"
                >
                  +
                </button>
                <button 
                  class="cart-btn-remove" 
                  @click="updateQuantity(index, 0)"
                  title="Eliminar"
                >
                  🗑️
                </button>
              </div>
            </div>
          </div>
          <div class="cart-summary">
            <div class="cart-summary-line">
              <span>Subtotal:</span>
              <span>${{ formatPrice(cartTotal) }}</span>
            </div>
            <div class="cart-total-line">
              <span>Total:</span>
              <strong>${{ formatPrice(cartTotal) }}</strong>
            </div>
            <button class="primary-btn full-width cart-checkout-btn" @click="proceedToCheckout">
              Finalizar pedido
            </button>
            <button class="secondary-btn full-width" @click="showCart = false">
              Seguir comprando
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL CONTACTO -->
    <div v-if="showContactModal" class="modal-overlay" @click.self="showContactModal = false">
      <div class="modal-content contact-modal">
        <button class="modal-close" @click="showContactModal = false">✕</button>
        <h3>Información de contacto</h3>
        <p>{{ contactText }}</p>
        <a
          v-if="whatsappLink"
          :href="whatsappLink"
          target="_blank"
          rel="noopener noreferrer"
          class="whatsapp-btn"
        >
          💬 Escríbenos por WhatsApp
        </a>
      </div>
    </div>

    <!-- MODAL HERO/INICIO -->
    <div v-if="showHeroModal" class="modal-overlay" @click.self="showHeroModal = false">
      <div class="modal-content hero-modal">
        <button class="modal-close" @click="showHeroModal = false">✕</button>
        <h2 class="modal-title">{{ heroTitle }}</h2>
        <p v-if="heroSubtitle" class="modal-subtitle">{{ heroSubtitle }}</p>
        <p v-if="heroDescription" class="modal-description">{{ heroDescription }}</p>
        <div class="modal-actions">
          <button class="primary-btn" @click="scrollToSection('products'); showHeroModal = false">Ver Productos</button>
        </div>
      </div>
    </div>

    <!-- MODAL CONTACTO -->
    <div v-if="showContactModal" class="modal-overlay" @click.self="showContactModal = false">
      <div class="modal-content contact-modal">
        <button class="modal-close" @click="showContactModal = false">✕</button>
        <h2 class="modal-title">{{ ecommerceConfig.contact_titulo || 'Contáctanos' }}</h2>
        <p class="modal-description">{{ contactText }}</p>
        <div v-if="whatsappLink" class="modal-actions">
          <a :href="whatsappLink" target="_blank" rel="noopener noreferrer" class="primary-btn">
            💬 Contactar por WhatsApp
          </a>
        </div>
      </div>
    </div>

    <!-- MODAL SOBRE NOSOTROS -->
    <div v-if="showAboutModal" class="modal-overlay" @click.self="showAboutModal = false">
      <div class="modal-content about-modal">
        <button class="modal-close" @click="showAboutModal = false">✕</button>
        <h2 class="modal-title">{{ ecommerceConfig.about_titulo || 'Sobre nosotros' }}</h2>
        <p class="modal-description">{{ aboutText }}</p>
      </div>
    </div>

    <!-- MODAL GENÉRICO -->
    <div v-if="showGenericModal" class="modal-overlay" @click.self="showGenericModal = false">
      <div class="modal-content generic-modal">
        <button class="modal-close" @click="showGenericModal = false">✕</button>
        <div class="modal-description" v-html="currentModalContent"></div>
      </div>
    </div>

    <!-- MODAL CÉDULA/NIT -->
    <div v-if="showCedulaModal" class="modal-overlay" @click.self="showCedulaModal = false">
      <div class="modal-content cedula-modal">
        <button class="modal-close" @click="showCedulaModal = false">✕</button>
        <h3>Datos del Cliente</h3>
        <form @submit.prevent="validateDocument" class="cedula-form">
          <div class="form-group">
            <label>Tipo de Documento *</label>
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" v-model="checkoutData.docType" value="cedula" />
                Cédula
              </label>
              <label class="radio-label">
                <input type="radio" v-model="checkoutData.docType" value="nit" />
                NIT
              </label>
            </div>
          </div>
          <div class="form-group">
            <label v-if="checkoutData.docType === 'cedula'">Número de Cédula *</label>
            <label v-else>Número de NIT *</label>
            <input
              v-model="checkoutData.cedula"
              type="text"
              class="form-input"
              :placeholder="checkoutData.docType === 'cedula' ? 'Ej: 1234567890' : 'Ej: 900123456-1'"
              required
              autofocus
              @keyup.enter="validateDocument"
            />
            <small class="form-help">Presiona Enter para buscar en TNS</small>
          </div>
          <div v-if="isValidatingDocument" class="loading-message">
            🔍 Buscando información...
          </div>
          <div v-if="validatedData.name" class="info-message">
            ✅ Datos encontrados: {{ validatedData.name }}
          </div>
          <div class="button-group">
            <button type="button" class="secondary-btn" @click="showCedulaModal = false">Cancelar</button>
            <button 
              type="button" 
              class="primary-btn" 
              @click="validateDocument"
              :disabled="!checkoutData.cedula || checkoutData.cedula.length < 7 || isValidatingDocument"
            >
              Buscar
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- MODAL DATOS COMPLETOS (después de validar documento) -->
    <div v-if="showDatosCompletosModal" class="modal-overlay" @click.self="showDatosCompletosModal = false">
      <div class="modal-content datos-completos-modal">
        <button class="modal-close" @click="showDatosCompletosModal = false">✕</button>
        <h3>Completar Datos</h3>
        <form @submit.prevent="confirmDatosCompletos" class="datos-completos-form">
          <div class="form-group">
            <label>Tipo de Persona *</label>
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" v-model="checkoutData.nature" value="natural" />
                Natural
              </label>
              <label class="radio-label">
                <input type="radio" v-model="checkoutData.nature" value="juridica" />
                Jurídica
              </label>
            </div>
          </div>
          <div class="form-group">
            <label v-if="checkoutData.nature === 'natural'">Nombre Completo *</label>
            <label v-else>Razón Social *</label>
            <input
              v-model="checkoutData.nombre"
              type="text"
              class="form-input"
              :placeholder="checkoutData.nature === 'natural' ? 'Nombre y Apellidos' : 'Razón Social de la Empresa'"
              required
            />
          </div>
          <div class="form-group">
            <label>Email</label>
            <input
              v-model="checkoutData.email"
              type="email"
              class="form-input"
              placeholder="email@ejemplo.com"
            />
          </div>
          <div class="form-group">
            <label>Teléfono</label>
            <input
              v-model="checkoutData.telefono"
              type="text"
              class="form-input"
              placeholder="3001234567"
            />
          </div>
          <div class="button-group">
            <button type="button" class="secondary-btn" @click="goBackToCedulaModal">Volver</button>
            <button type="submit" class="primary-btn">Continuar</button>
          </div>
        </form>
      </div>
    </div>

    <!-- MODAL DIRECCIÓN DE ENVÍO -->
    <div v-if="showDireccionModal" class="modal-overlay" @click.self="showDireccionModal = false">
      <div class="modal-content direccion-modal">
        <button class="modal-close" @click="showDireccionModal = false">✕</button>
        <h3>Dirección de Envío</h3>
        <form @submit.prevent="confirmDireccion" class="direccion-form">
          <div class="form-group">
            <label>Dirección completa *</label>
            <textarea
              v-model="checkoutData.direccion"
              class="form-input form-textarea"
              placeholder="Calle, número, barrio, ciudad..."
              required
              rows="4"
            ></textarea>
          </div>
          <div class="button-group">
            <button type="button" class="secondary-btn" @click="showDireccionModal = false">Cancelar</button>
            <button type="submit" class="primary-btn" :disabled="processingPayment">
              <span v-if="processingPayment">Procesando...</span>
              <span v-else>Finalizar Pedido</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- MODAL SELECCIÓN DE FORMA DE PAGO -->
    <div v-if="showFormaPagoModal" class="modal-overlay" @click.self="showFormaPagoModal = false">
      <div class="modal-content forma-pago-modal">
        <button class="modal-close" @click="showFormaPagoModal = false">✕</button>
        <h3>Selecciona la Forma de Pago</h3>
        <div class="forma-pago-form">
          <div v-if="loadingFormasPago" class="loading-message">
            🔍 Cargando formas de pago...
          </div>
          <div v-else-if="formasPago.length === 0" class="form-group">
            <p class="error-message">No hay formas de pago disponibles</p>
          </div>
          <div v-else class="form-group">
            <div class="payment-options">
              <button
                v-for="fp in formasPago"
                :key="fp.codigo"
                class="payment-option-btn"
                :class="{ active: formaPagoSeleccionada === fp.codigo }"
                @click="formaPagoSeleccionada = fp.codigo"
              >
                <span class="payment-icon">{{ getPaymentIcon(fp.codigo) }}</span>
                <span class="payment-label">{{ fp.descripcion }}</span>
              </button>
            </div>
          </div>
          <div class="button-group">
            <button 
              class="primary-btn" 
              @click="confirmFormaPago"
              :disabled="!formaPagoSeleccionada || loadingFormasPago"
            >
              Continuar
            </button>
            <button class="secondary-btn" @click="cancelFormaPago">Atrás</button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL SELECCIÓN DE PASARELA -->
    <div v-if="showPasarelaModal" class="modal-overlay" @click.self="showPasarelaModal = false">
      <div class="modal-content pasarela-modal">
        <button class="modal-close" @click="cancelPasarela">✕</button>
        <h3>Selecciona la Pasarela de Pago</h3>
        <div class="pasarela-form">
          <div v-if="loadingPasarelas" class="loading-message">
            🔍 Cargando pasarelas...
          </div>
          <div v-else-if="pasarelasDisponibles.length === 0" class="form-group">
            <p class="error-message">No hay pasarelas disponibles</p>
          </div>
          <div v-else class="form-group">
            <div class="payment-options">
              <button
                v-for="pasarela in pasarelasDisponibles"
                :key="pasarela.id"
                class="payment-option-btn"
                :class="{ active: pasarelaSeleccionada === pasarela.codigo }"
                @click="pasarelaSeleccionada = pasarela.codigo"
              >
                <span class="payment-icon">💳</span>
                <span class="payment-label">{{ pasarela.nombre }}</span>
              </button>
            </div>
          </div>
          <div class="button-group">
            <button 
              class="primary-btn" 
              @click="confirmPasarela"
              :disabled="!pasarelaSeleccionada || loadingPasarelas"
            >
              Continuar
            </button>
            <button class="secondary-btn" @click="cancelPasarela">Atrás</button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL DATOS DE TARJETA -->
    <div v-if="showTarjetaModal" class="modal-overlay" @click.self="showTarjetaModal = false">
      <div class="modal-content tarjeta-modal">
        <button class="modal-close" @click="cancelTarjeta">✕</button>
        <h3>Datos de la Tarjeta</h3>
        <form @submit.prevent="confirmTarjeta" class="tarjeta-form">
          <div class="form-group">
            <label>Nombre del Titular *</label>
            <input
              v-model="tarjetaData.nombre_titular"
              type="text"
              class="form-input"
              placeholder="Nombre completo"
              required
            />
          </div>
          <div class="form-group">
            <label>Cédula del Titular *</label>
            <input
              v-model="tarjetaData.cedula_titular"
              type="text"
              class="form-input"
              placeholder="1234567890"
              required
            />
          </div>
          <div class="form-group">
            <label>Número de Tarjeta *</label>
            <input
              v-model="tarjetaData.numero_tarjeta"
              type="text"
              class="form-input"
              placeholder="1234 5678 9012 3456"
              @input="formatCardNumber"
              maxlength="19"
              required
            />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Mes de Vencimiento *</label>
              <input
                v-model="tarjetaData.mes_vencimiento"
                type="text"
                class="form-input"
                placeholder="MM"
                maxlength="2"
                required
              />
            </div>
            <div class="form-group">
              <label>Año de Vencimiento *</label>
              <input
                v-model="tarjetaData.anio_vencimiento"
                type="text"
                class="form-input"
                placeholder="YYYY"
                maxlength="4"
                required
              />
            </div>
            <div class="form-group">
              <label>CVV *</label>
              <input
                v-model="tarjetaData.cvv"
                type="text"
                class="form-input"
                placeholder="123"
                maxlength="4"
                required
              />
            </div>
          </div>
          <div class="button-group">
            <button type="button" class="secondary-btn" @click="cancelTarjeta">Atrás</button>
            <button 
              type="submit" 
              class="primary-btn" 
              :disabled="processingPayment"
            >
              <span v-if="processingPayment">Procesando...</span>
              <span v-else>Pagar</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- NOTIFICACIÓN TOAST -->
    <Transition name="toast">
      <div v-if="showToast && toastMessage" class="toast-notification">
        <div class="toast-content">
          <span class="toast-icon">✓</span>
          <span class="toast-message">{{ toastMessage }}</span>
        </div>
      </div>
    </Transition>

    <!-- MODAL LOGIN ADMIN -->
    <div v-if="showAdminLogin" class="modal-overlay" @click.self="showAdminLogin = false">
      <div class="modal-content admin-login-modal">
        <button class="modal-close" @click="showAdminLogin = false">✕</button>
        <h3>Acceso de Administrador</h3>
        <form @submit.prevent="handleAdminLogin" class="admin-login-form">
          <div class="form-group">
            <label>Contraseña</label>
            <input
              v-model="adminLoginForm.password"
              type="password"
              class="form-input"
              placeholder="Ingresa la contraseña de admin"
              required
              autofocus
            />
          </div>
          <div v-if="adminLoginError" class="error-message">
            {{ adminLoginError }}
          </div>
          <div class="button-group">
            <button type="submit" class="primary-btn" :disabled="loggingIn">
              <span v-if="loggingIn">Verificando...</span>
              <span v-else>Ingresar</span>
            </button>
            <button type="button" class="secondary-btn" @click="showAdminLogin = false" :disabled="loggingIn">
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- MODAL CONTRASEÑA PARA GUARDAR -->
    <div v-if="showPasswordModal" class="modal-overlay" @click.self="showPasswordModal = false">
      <div class="modal-content admin-login-modal">
        <button class="modal-close" @click="showPasswordModal = false">✕</button>
        <h3>Confirmar Contraseña</h3>
        <form @submit.prevent="confirmSaveWithPassword" class="admin-login-form">
          <div class="form-group">
            <label>Contraseña de ADMIN</label>
            <input
              v-model="savePasswordForm.password"
              type="password"
              class="form-input"
              placeholder="Ingresa la contraseña de admin"
              required
              autofocus
            />
          </div>
          <div v-if="savePasswordError" class="error-message">
            {{ savePasswordError }}
          </div>
          <div class="button-group">
            <button type="submit" class="primary-btn" :disabled="savingConfig">
              <span v-if="savingConfig">Guardando...</span>
              <span v-else>Guardar</span>
            </button>
            <button type="button" class="secondary-btn" @click="showPasswordModal = false" :disabled="savingConfig">
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- PANEL DE ADMINISTRACIÓN -->
    <div v-if="showAdminPanel && isAdmin" class="admin-panel-overlay" @click.self="showAdminPanel = false">
      <div class="admin-panel">
        <div class="admin-panel-header">
          <h2>Panel de Administración</h2>
          <button class="admin-close-btn" @click="showAdminPanel = false">✕</button>
        </div>
        
        <div class="admin-tabs-wrapper">
          <div class="admin-tabs">
            <button
              v-for="tab in adminTabs"
              :key="tab.id"
              class="admin-tab"
              :class="{ active: activeAdminTab === tab.id }"
              @click="activeAdminTab = tab.id"
            >
              <span class="admin-tab-icon" v-if="tab.icon">{{ tab.icon }}</span>
              <span class="admin-tab-label">{{ tab.label }}</span>
            </button>
          </div>
        </div>

        <div class="admin-content">
          <!-- TAB: Configuración General -->
          <div v-if="activeAdminTab === 'general'" class="admin-tab-content">
            <h3>Configuración General</h3>
            
            <div class="admin-section">
              <h4>Colores</h4>
              <div class="form-grid">
                <div class="form-group">
                  <label>Color Primario</label>
                  <input v-model="ecommerceConfig.color_primario" type="color" class="color-input" @input="handleColorChange('primario')" />
                  <input v-model="ecommerceConfig.color_primario" type="text" class="form-input" @input="handleColorChange('primario')" />
                </div>
                <div class="form-group">
                  <label>Color Secundario</label>
                  <input v-model="ecommerceConfig.color_secundario" type="color" class="color-input" @input="handleColorChange('secundario')" />
                  <input v-model="ecommerceConfig.color_secundario" type="text" class="form-input" @input="handleColorChange('secundario')" />
                </div>
                <div class="form-group">
                  <label>Color de Fondo</label>
                  <input v-model="ecommerceConfig.color_fondo" type="color" class="color-input" @input="handleColorChange('fondo')" />
                  <input v-model="ecommerceConfig.color_fondo" type="text" class="form-input" @input="handleColorChange('fondo')" />
                </div>
              </div>
            </div>

            <div class="admin-section">
              <h4>Degradado</h4>
              <div class="form-group">
                <label>
                  <input v-model="ecommerceConfig.usar_degradado" type="checkbox" />
                  Usar degradado
                </label>
              </div>
              <div v-if="ecommerceConfig.usar_degradado" class="form-grid">
                <div class="form-group">
                  <label>Color Inicio</label>
                  <input v-model="ecommerceConfig.color_degradado_inicio" type="color" class="color-input" @input="handleColorChange('degradado_inicio')" />
                  <input v-model="ecommerceConfig.color_degradado_inicio" type="text" class="form-input" @input="handleColorChange('degradado_inicio')" />
                </div>
                <div class="form-group">
                  <label>Color Fin</label>
                  <input v-model="ecommerceConfig.color_degradado_fin" type="color" class="color-input" @input="handleColorChange('degradado_fin')" />
                  <input v-model="ecommerceConfig.color_degradado_fin" type="text" class="form-input" @input="handleColorChange('degradado_fin')" />
                </div>
                <div class="form-group">
                  <label>Dirección</label>
                  <select v-model="ecommerceConfig.direccion_degradado" class="form-input">
                    <option value="to right">Izquierda a Derecha</option>
                    <option value="to bottom">Arriba a Abajo</option>
                    <option value="to bottom right">Diagonal</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="admin-section">
              <h4>Logo Principal</h4>
              <div class="form-group">
                <label>Logo (PNG transparente recomendado)</label>
                <input
                  ref="logoInput"
                  type="file"
                  accept="image/png,image/jpeg,image/jpg,image/webp"
                  @change="handleLogoUpload"
                  class="file-input"
                />
                <button @click="logoInput?.click()" class="secondary-btn" type="button">
                  {{ ecommerceConfig.logo_url ? 'Cambiar Logo' : 'Cargar Logo' }}
                </button>
                <div v-if="ecommerceConfig.logo_url || companyLogo" class="logo-preview">
                  <img :src="ecommerceConfig.logo_url || companyLogo" alt="Logo preview" class="logo-preview-img" />
                  <button @click="ecommerceConfig.logo_url = ''; companyLogo = ''" class="danger-btn small">Eliminar</button>
                </div>
                <small class="admin-help-text">El logo se guardará automáticamente al guardar la configuración.</small>
              </div>
            </div>

            <div class="admin-section">
              <h4>Estilo</h4>
              <div class="form-group">
                <label>Tema</label>
                <select v-model="ecommerceConfig.estilo_tema" class="form-input">
                  <option value="balanceado">Balanceado (Recomendado)</option>
                  <option value="moderno">Moderno</option>
                  <option value="minimalista">Minimalista</option>
                  <option value="colorido">Colorido</option>
                  <option value="elegante">Elegante</option>
                </select>
              </div>
            </div>

            <div class="admin-section">
              <h4>Textos - Hero Section</h4>
              <div class="form-group">
                <label>Título</label>
                <input v-model="ecommerceConfig.hero_titulo" type="text" class="form-input" />
              </div>
              <div class="form-group">
                <label>Subtítulo</label>
                <input v-model="ecommerceConfig.hero_subtitulo" type="text" class="form-input" />
              </div>
              <div class="form-group">
                <label>Descripción</label>
                <textarea v-model="ecommerceConfig.hero_descripcion" class="form-input" rows="3"></textarea>
              </div>
            </div>

            <div class="admin-section">
              <h4>Textos - Sobre Nosotros</h4>
              <div class="form-group">
                <label>Título</label>
                <input v-model="ecommerceConfig.about_titulo" type="text" class="form-input" />
              </div>
              <div class="form-group">
                <label>Texto</label>
                <textarea v-model="ecommerceConfig.about_texto" class="form-input" rows="4"></textarea>
              </div>
            </div>

            <div class="admin-section">
              <h4>Textos - Contacto</h4>
              <div class="form-group">
                <label>Título</label>
                <input v-model="ecommerceConfig.contact_titulo" type="text" class="form-input" />
              </div>
              <div class="form-group">
                <label>Texto</label>
                <textarea v-model="ecommerceConfig.contact_texto" class="form-input" rows="4"></textarea>
              </div>
              <div class="form-group">
                <label>WhatsApp (solo números)</label>
                <input v-model="ecommerceConfig.whatsapp_numero" type="text" class="form-input" placeholder="573001234567" />
              </div>
            </div>

            <div class="admin-section">
              <h4>Secciones</h4>
              <div class="form-group">
                <label>
                  <input v-model="ecommerceConfig.mostrar_menu" type="checkbox" />
                  Mostrar Menú Principal
                </label>
              </div>
              <div class="form-group">
                <label>
                  <input v-model="ecommerceConfig.mostrar_hero" type="checkbox" />
                  Mostrar Hero
                </label>
              </div>
              <div class="form-group">
                <label>
                  <input v-model="ecommerceConfig.mostrar_about" type="checkbox" />
                  Mostrar Sobre Nosotros
                </label>
              </div>
              <div class="form-group">
                <label>
                  <input v-model="ecommerceConfig.mostrar_contact" type="checkbox" />
                  Mostrar Contacto
                </label>
              </div>
              <div class="form-group">
                <label>
                  <input v-model="ecommerceConfig.mostrar_footer" type="checkbox" />
                  Mostrar Footer
                </label>
              </div>
              <div class="form-group">
                <label>
                  <input v-model="ecommerceConfig.mostrar_categorias_footer" type="checkbox" />
                  Mostrar Categorías en Footer
                </label>
              </div>
            </div>

            <div class="admin-actions">
              <button @click="saveEcommerceConfig" class="primary-btn" :disabled="savingConfig">
                <span v-if="savingConfig">Guardando...</span>
                <span v-else>Guardar Configuración</span>
              </button>
            </div>
          </div>

          <!-- TAB: Productos -->
          <div v-if="activeAdminTab === 'products'" class="admin-tab-content">
            <h3>Gestión de Productos</h3>
            <div class="admin-search">
              <input
                v-model="adminProductSearch"
                type="text"
                placeholder="Buscar producto..."
                class="form-input"
              />
            </div>
            <div class="admin-products-list">
              <div
                v-for="product in filteredAdminProducts"
                :key="product.id"
                class="admin-product-item"
              >
                <div class="admin-product-info">
                  <h4>{{ product.name }}</h4>
                  <p class="admin-product-code">{{ product.codigo }}</p>
                </div>
                <button @click="openProductEditor(product)" class="edit-btn">Editar</button>
              </div>
            </div>
          </div>

          <!-- TAB: Pasarela de Pago -->
          <div v-if="activeAdminTab === 'payment'" class="admin-tab-content">
            <h3>Configuración de Pasarela de Pago</h3>
            
            <div class="admin-section">
              <h4>Credenciales TNS para Facturación</h4>
              <p class="admin-help-text">
                Estas credenciales se usan para insertar facturas en TNS cuando se procesa un pago.
                El password se almacena de forma encriptada y nunca se expone en el frontend.
              </p>
              
              <div class="form-grid">
                <div class="form-group">
                  <label>Usuario TNS *</label>
                  <input
                    v-model="ecommerceConfig.usuario_tns"
                    type="text"
                    class="form-input"
                    placeholder="Ej: ADMIN"
                    required
                  />
                  <small class="form-help">Usuario TNS que se usará para insertar facturas</small>
                </div>
                
                <div class="form-group">
                  <label>Contraseña TNS *</label>
                  <input
                    v-model="ecommerceConfig.password_tns"
                    type="password"
                    class="form-input"
                    placeholder="Ingresa la contraseña TNS"
                    required
                  />
                  <small class="form-help">La contraseña se almacena de forma encriptada</small>
                </div>
              </div>
            </div>

            <div class="admin-section">
              <h4>Configuración de Pasarela</h4>
              
              <div class="form-group">
                <label>Pasarela de Pago</label>
                <select v-model="ecommerceConfig.payment_provider" class="form-input">
                  <option value="">Seleccionar pasarela...</option>
                  <option
                    v-for="pasarela in pasarelasDisponibles"
                    :key="pasarela.id"
                    :value="pasarela.codigo"
                  >
                    {{ pasarela.nombre }}
                  </option>
                </select>
                <small class="form-help">Selecciona la pasarela de pago que usarás (ej: credibanco)</small>
              </div>
              
              <div class="form-group">
                <label>Modo</label>
                <select v-model="ecommerceConfig.payment_mode" class="form-input">
                  <option value="test">Prueba (Mock)</option>
                  <option value="live">Producción (Real)</option>
                </select>
                <small class="form-help">En modo Prueba se simula el pago. En Producción se usa la pasarela real.</small>
              </div>
              
              <div class="form-group">
                <label>Cómo abrir la pasarela</label>
                <select v-model="ecommerceConfig.payment_window_type" class="form-input">
                  <option value="new_window">Nueva Ventana/Pestaña</option>
                  <option value="modal">Modal (iframe)</option>
                  <option value="same_window">Misma Ventana</option>
                </select>
                <small class="form-help">Cómo se abrirá la página de pago de la pasarela</small>
              </div>
            </div>

            <div class="admin-section">
              <h4>Credenciales de Pasarela (Credibanco)</h4>
              <p class="admin-help-text">
                Credenciales para conectarse a la API de la pasarela (ej: Credibanco).
                Estas credenciales las proporciona la pasarela.
              </p>
              
              <div class="form-grid">
                <div class="form-group">
                  <label>Usuario API (userName)</label>
                  <input
                    v-model="ecommerceConfig.payment_public_key"
                    type="text"
                    class="form-input"
                    placeholder="Ej: DEPOSITO_HABITARE-api"
                  />
                  <small class="form-help">Usuario proporcionado por Credibanco</small>
                </div>
                
                <div class="form-group">
                  <label>Contraseña API (password)</label>
                  <input
                    v-model="ecommerceConfig.payment_secret_key"
                    type="password"
                    class="form-input"
                    placeholder="Ingresa la contraseña de la API"
                  />
                  <small class="form-help">Contraseña proporcionada por Credibanco</small>
                </div>
              </div>
            </div>

            <div class="admin-section">
              <h4>Pasarelas Disponibles</h4>
              <p class="admin-help-text">
                Las pasarelas disponibles se cargan automáticamente desde el servidor.
              </p>
              
              <div v-if="loadingPasarelas" class="loading-text">Cargando pasarelas...</div>
              <div v-else-if="pasarelasDisponibles.length === 0" class="info-text">
                No hay pasarelas disponibles. Contacta al administrador del sistema.
              </div>
              <div v-else class="pasarelas-list">
                <div
                  v-for="pasarela in pasarelasDisponibles"
                  :key="pasarela.id"
                  class="pasarela-item"
                >
                  <div class="pasarela-info">
                    <strong>{{ pasarela.nombre }}</strong>
                    <span class="pasarela-codigo">({{ pasarela.codigo }})</span>
                  </div>
                  <span v-if="pasarela.activa" class="badge-active">Activa</span>
                  <span v-else class="badge-inactive">Inactiva</span>
                </div>
              </div>
            </div>

            <div class="admin-actions">
              <button @click="saveEcommerceConfig" class="primary-btn" :disabled="savingConfig">
                <span v-if="savingConfig">Guardando...</span>
                <span v-else>Guardar Configuración</span>
              </button>
            </div>
          </div>

          <!-- TAB: Menú -->
          <div v-if="activeAdminTab === 'menu'" class="admin-tab-content">
            <h3>Configuración del Menú</h3>
            
            <div class="admin-section">
              <h4>Links del Menú Principal</h4>
              <p class="admin-help-text">Configura los links que aparecen en el menú superior del sitio.</p>
              
              <div v-for="(menuItem, index) in ecommerceConfig.menu_items" :key="index" class="footer-link-item">
                <div class="form-grid">
                  <div class="form-group">
                    <label>Icono (emoji)</label>
                    <input v-model="menuItem.icono" type="text" class="form-input" placeholder="Ej: 🏠" />
                  </div>
                  <div class="form-group">
                    <label>Texto del Link</label>
                    <input v-model="menuItem.texto" type="text" class="form-input" placeholder="Ej: Inicio" />
                  </div>
                  <div class="form-group">
                    <label>Tipo</label>
                    <select v-model="menuItem.tipo" class="form-input">
                      <option value="scroll">Desplazar a Sección</option>
                      <option value="modal">Abrir Modal</option>
                      <option value="external">Enlace Externo</option>
                      <option value="file">Archivo para Descargar</option>
                      <option value="content">Cargar en Área de Trabajo</option>
                    </select>
                  </div>
                  <div class="form-group">
                    <label>Destino/URL/ID Sección</label>
                    <input v-model="menuItem.destino" type="text" class="form-input" placeholder="Ej: hero, about, products, contact o URL" />
                  </div>
                  <div class="form-group">
                    <label>Contenido (si es modal o content)</label>
                    <textarea v-model="menuItem.contenido" class="form-input" rows="3" placeholder="Contenido HTML o texto para modal/content"></textarea>
                  </div>
                  <div class="form-group">
                    <button @click="removeMenuItem(index)" class="danger-btn small">Eliminar</button>
                  </div>
                </div>
              </div>
              
              <button @click="addMenuItem" class="secondary-btn">+ Agregar Item al Menú</button>
            </div>

            <div class="admin-actions">
              <button @click="saveEcommerceConfig" class="primary-btn" :disabled="savingConfig">
                <span v-if="savingConfig">Guardando...</span>
                <span v-else>Guardar Menú</span>
              </button>
            </div>
          </div>

          <!-- TAB: Footer -->
          <div v-if="activeAdminTab === 'footer'" class="admin-tab-content">
            <h3>Configuración del Footer</h3>
            
            <div class="admin-section">
              <h4>Texto debajo del Logo</h4>
              <div class="form-group">
                <textarea v-model="ecommerceConfig.footer_texto_logo" class="form-input" rows="3" placeholder="Texto que aparece debajo del logo..."></textarea>
              </div>
            </div>

            <div class="admin-section">
              <h4>Secciones del Footer</h4>
              <div v-for="(section, sectionIndex) in ecommerceConfig.footer_sections" :key="sectionIndex" class="footer-section-item">
                <div class="footer-section-header">
                  <h5>Sección {{ sectionIndex + 1 }}</h5>
                  <button @click="removeFooterSection(sectionIndex)" class="danger-btn small">Eliminar Sección</button>
                </div>
                <div class="form-group">
                  <label>Título de la Sección</label>
                  <input v-model="section.titulo" type="text" class="form-input" placeholder="Ej: Enlaces Rápidos" />
                </div>
                <div class="form-group">
                  <label>Links de esta Sección</label>
                  <div v-for="(link, linkIndex) in section.links" :key="linkIndex" class="footer-link-item">
                    <div class="form-grid">
                      <div class="form-group">
                        <label>Título</label>
                        <input v-model="link.titulo" type="text" class="form-input" />
                      </div>
                      <div class="form-group">
                        <label>URL</label>
                        <input v-model="link.url" type="text" class="form-input" />
                      </div>
                      <div class="form-group">
                        <label>Tipo</label>
                        <select v-model="link.tipo" class="form-input">
                          <option value="modal">Modal</option>
                          <option value="external">Enlace Externo</option>
                          <option value="file">Archivo para Descargar</option>
                        </select>
                      </div>
                      <div class="form-group">
                        <button @click="removeFooterLinkFromSection(sectionIndex, linkIndex)" class="danger-btn small">Eliminar</button>
                      </div>
                    </div>
                  </div>
                  <button @click="addFooterLinkToSection(sectionIndex)" class="secondary-btn small">+ Agregar Link</button>
                </div>
              </div>
              <button @click="addFooterSection" class="primary-btn">+ Agregar Nueva Sección</button>
            </div>

            <div class="admin-section">
              <h4>Links del Footer (Legacy - se mantiene para compatibilidad)</h4>
              <div v-for="(link, index) in ecommerceConfig.footer_links" :key="index" class="footer-link-item">
                <div class="form-grid">
                  <div class="form-group">
                    <label>Título</label>
                    <input v-model="link.titulo" type="text" class="form-input" />
                  </div>
                  <div class="form-group">
                    <label>URL</label>
                    <input v-model="link.url" type="text" class="form-input" />
                  </div>
                  <div class="form-group">
                    <label>Tipo</label>
                    <select v-model="link.tipo" class="form-input">
                      <option value="modal">Modal</option>
                      <option value="external">Enlace Externo</option>
                      <option value="file">Archivo para Descargar</option>
                    </select>
                  </div>
                  <div class="form-group">
                    <button @click="removeFooterLink(index)" class="danger-btn">Eliminar</button>
                  </div>
                </div>
              </div>
              <button @click="addFooterLink" class="secondary-btn">+ Agregar Link</button>
            </div>

            <div class="admin-actions">
              <button @click="saveEcommerceConfig" class="primary-btn" :disabled="savingConfig">
                <span v-if="savingConfig">Guardando...</span>
                <span v-else>Guardar Footer</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL EDITOR DE PRODUCTO -->
    <div v-if="editingProduct" class="modal-overlay product-editor-overlay" @click.self="editingProduct = null">
      <div class="modal-content product-editor-modal">
        <button class="modal-close" @click="editingProduct = null">✕</button>
        <h3>Editar Producto: {{ editingProduct.name }}</h3>
        
        <div class="admin-section">
          <h4>Imagen</h4>
          <div class="product-image-upload">
            <img v-if="editingProduct.imagen_url" :src="editingProduct.imagen_url" alt="Preview" class="product-image-preview" />
            <div v-else class="product-image-placeholder">Sin imagen</div>
            <input
              ref="productImageInput"
              type="file"
              accept="image/*"
              @change="handleProductImageUpload"
              class="file-input"
            />
            <button @click="() => productImageInput?.click()" class="secondary-btn">Seleccionar Imagen</button>
          </div>
        </div>

        <div class="admin-section">
          <h4>Descripción</h4>
          <div class="form-group">
            <textarea v-model="editingProduct.descripcion" class="form-input" rows="5" placeholder="Descripción del producto..."></textarea>
          </div>
        </div>

        <div class="admin-section">
          <h4>PDF</h4>
          <div class="form-group">
            <input
              ref="productPdfInput"
              type="file"
              accept="application/pdf"
              @change="handleProductPdfUpload"
              class="file-input"
            />
            <button @click="() => productPdfInput?.click()" class="secondary-btn">Seleccionar PDF</button>
            <span v-if="editingProduct.pdf_url" class="pdf-link">
              <a :href="editingProduct.pdf_url" target="_blank">Ver PDF actual</a>
            </span>
          </div>
        </div>

        <div class="admin-actions">
          <button @click="saveProductChanges" class="primary-btn" :disabled="savingProduct">
            <span v-if="savingProduct">Guardando...</span>
            <span v-else>Guardar Cambios</span>
          </button>
          <button @click="editingProduct = null" class="secondary-btn">Cancelar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onUnmounted, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const { fetchRecords } = useTNSRecords()
const { getConfig } = useModuleConfig()
const session = useSessionStore()
const api = useApiClient()
const route = useRoute()
const router = useRouter()

const companyName = computed(() => session.selectedEmpresa.value?.nombreComercial || 'Mi Empresa')
const companyLogo = ref<string | null>(null)
const loadingPage = ref(true)

// Extraer subdominio del dominio para el loading
const loadingSubdomain = computed(() => {
  if (typeof window === 'undefined') return 'CARGANDO'
  const host = window.location.host
  // Extraer subdominio (ej: "pepito" de "pepito.ecommerce.localhost:3001")
  const parts = host.split('.')
  if (parts.length > 0) {
    const subdomain = parts[0]
    return subdomain.toUpperCase()
  }
  return 'CARGANDO'
})

// Admin State
const isAdmin = ref(false)
const showAdminLogin = ref(false)
const showAdminPanel = ref(false)
const loggingIn = ref(false)
const adminLoginError = ref<string | null>(null)
const adminLoginForm = ref({ password: '' })
const adminPassword = ref<string | null>(null) // Guardar contraseña después de login exitoso
const activeAdminTab = ref('general')
const adminTabs = [
  { id: 'general', label: 'General', icon: '⚙️' },
  { id: 'products', label: 'Productos', icon: '📦' },
  { id: 'menu', label: 'Menú', icon: '📋' },
  { id: 'footer', label: 'Footer', icon: '🔗' },
  { id: 'payment', label: 'Pasarela de Pago', icon: '💳' },
]

// Modal de contraseña para guardar
const showPasswordModal = ref(false)
const savePasswordForm = ref({ password: '' })
const savePasswordError = ref<string | null>(null)

// Logo click sequence para admin (igual que autopago: doble click, click, doble click)
const LOGO_SEQUENCE_PATTERN = [0, 1, 0] // 0=doble click, 1=click simple
const LOGO_SEQUENCE_TIMEOUT = 1500 // ms entre acciones
const logoClickSequence = ref<number[]>([])
let logoClickTimer: ReturnType<typeof setTimeout> | null = null
let pendingSingleClick: ReturnType<typeof setTimeout> | null = null

const handleLogoClick = () => {
  if (isAdmin.value) return // Si ya es admin, no hacer nada
  
  // Si hay un clic simple pendiente, cancelarlo (es un doble clic)
  if (pendingSingleClick) {
    clearTimeout(pendingSingleClick)
    pendingSingleClick = null
    return // El doble clic se manejará en handleLogoDoubleClick
  }
  
  // Programar clic simple después de un delay
  pendingSingleClick = setTimeout(() => {
    logoClickSequence.value.push(1) // 1 = clic simple
    console.log('[ecommerce] Clic simple detectado, secuencia:', logoClickSequence.value)
    
    // Limpiar timer anterior
    if (logoClickTimer) {
      clearTimeout(logoClickTimer)
    }
    
    // Verificar secuencia después de un timeout
    logoClickTimer = setTimeout(() => {
      checkLogoSequence()
    }, LOGO_SEQUENCE_TIMEOUT)
    
    pendingSingleClick = null
  }, 250) // Delay para detectar si es doble clic
}

const handleLogoDoubleClick = () => {
  if (isAdmin.value) return // Si ya es admin, no hacer nada
  
  // Cancelar el clic simple pendiente
  if (pendingSingleClick) {
    clearTimeout(pendingSingleClick)
    pendingSingleClick = null
  }
  
  // Registrar doble clic
  logoClickSequence.value.push(0) // 0 = doble clic
  console.log('[ecommerce] Doble clic detectado, secuencia:', logoClickSequence.value)
  
  // Limpiar timer anterior
  if (logoClickTimer) {
    clearTimeout(logoClickTimer)
  }
  
  // Verificar secuencia después de un timeout
  logoClickTimer = setTimeout(() => {
    checkLogoSequence()
  }, LOGO_SEQUENCE_TIMEOUT)
}

const checkLogoSequence = () => {
  if (logoClickSequence.value.length < LOGO_SEQUENCE_PATTERN.length) {
    // Secuencia incompleta, limpiar si es muy antigua
    if (logoClickSequence.value.length > 0) {
      console.log('[ecommerce] Secuencia incompleta, reseteando')
      logoClickSequence.value = []
    }
    return
  }
  
  // Verificar los últimos N elementos
  const recentSequence = logoClickSequence.value.slice(-LOGO_SEQUENCE_PATTERN.length)
  
  // Comparar con el patrón: [0, 1, 0] = doble clic, clic, doble clic
  const matches = recentSequence.every((click, index) => {
    return click === LOGO_SEQUENCE_PATTERN[index]
  })
  
  if (matches) {
    console.log('[ecommerce] ✅ Secuencia de logo detectada, abriendo modal de login')
    showAdminLogin.value = true
    logoClickSequence.value = [] // Limpiar secuencia
  } else {
    // No coincide, limpiar secuencia si es muy larga
    if (logoClickSequence.value.length > LOGO_SEQUENCE_PATTERN.length * 2) {
      console.log('[ecommerce] Secuencia no coincide, reseteando')
      logoClickSequence.value = []
    }
  }
  
  // Limpiar timer
  if (logoClickTimer) {
    clearTimeout(logoClickTimer)
    logoClickTimer = null
  }
}

// E-commerce Config
const ecommerceConfig = ref({
  empresa_servidor_id: null as number | null,
  color_primario: '#DC2626',
  color_secundario: '#FBBF24',
  color_fondo: '#FFFFFF',
  usar_degradado: false,
  color_degradado_inicio: '#DC2626',
  color_degradado_fin: '#FBBF24',
  direccion_degradado: 'to right',
  hero_titulo: 'Bienvenido a nuestra tienda en línea',
  hero_subtitulo: 'Pedidos rápidos, sencillos y sin filas',
  hero_descripcion: 'Explora nuestro menú y realiza tu pedido en pocos clics.',
  about_titulo: 'Sobre nosotros',
  about_texto: 'Somos una marca enfocada en ofrecer la mejor experiencia gastronómica, con ingredientes frescos y recetas únicas.',
  contact_titulo: 'Contáctanos',
  contact_texto: 'Para más información sobre pedidos corporativos, eventos o alianzas, contáctanos a través de nuestros canales oficiales.',
  whatsapp_numero: null as string | null,
  footer_texto_logo: null as string | null,
  footer_links: [] as Array<{ titulo: string; url: string; tipo: 'modal' | 'external' | 'file'; icono?: string }>,
  footer_sections: [] as Array<{ titulo: string; links: Array<{ icono?: string; titulo: string; url: string; tipo: 'modal' | 'external' | 'file' }> }>,
  menu_items: [] as Array<{ icono?: string; texto: string; tipo: 'scroll' | 'modal' | 'external' | 'file' | 'content'; destino: string; contenido?: string }>,
  payment_provider: '' as string,
  payment_public_key: '' as string,
  payment_secret_key: '' as string,
  payment_access_token: '' as string,
  payment_enabled: false,
  payment_mode: 'test' as 'test' | 'live',
  payment_window_type: 'new_window' as 'new_window' | 'modal' | 'same_window',
  usuario_tns: null as string | null,
  password_tns: null as string | null,
  logo_url: null as string | null,
  mostrar_menu: true,
  mostrar_hero: true,
  mostrar_about: true,
  mostrar_contact: true,
  mostrar_footer: true,
  mostrar_categorias_footer: true,
  estilo_tema: 'balanceado',
})
const savingConfig = ref(false)

// Pasarelas disponibles
const pasarelasDisponibles = ref<any[]>([])
const loadingPasarelas = ref(false)

const loadPasarelasDisponibles = async () => {
  console.log('[ecommerce] loadPasarelasDisponibles iniciado')
  loadingPasarelas.value = true
  try {
    const response = await api.get('/api/pasarelas-disponibles/') as any
    console.log('[ecommerce] Respuesta de pasarelas:', response)
    if (response && response.pasarelas) {
      pasarelasDisponibles.value = response.pasarelas
      console.log('[ecommerce] Pasarelas cargadas:', pasarelasDisponibles.value.length, pasarelasDisponibles.value)
    } else {
      console.warn('[ecommerce] No se recibieron pasarelas en la respuesta')
      pasarelasDisponibles.value = []
    }
  } catch (error: any) {
    console.error('[ecommerce] Error cargando pasarelas:', error)
    pasarelasDisponibles.value = []
    showNotification('Error al cargar pasarelas de pago')
  } finally {
    loadingPasarelas.value = false
    console.log('[ecommerce] loadPasarelasDisponibles finalizado')
  }
}

// Logo upload
const logoInput = ref<HTMLInputElement | null>(null)

const handleLogoUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  
  // Validar que sea imagen
  if (!file.type.startsWith('image/')) {
    showNotification('Por favor selecciona un archivo de imagen')
    return
  }
  
  // Crear FormData para subir
  const formData = new FormData()
  formData.append('logo', file)
  formData.append('empresa_servidor_id', String(ecommerceConfig.value.empresa_servidor_id || ''))
  formData.append('username', 'ADMIN')
  formData.append('password', adminPassword.value || savePasswordForm.value.password || '')
  
  try {
    // Subir logo al backend
    const response = await api.put('/api/ecommerce-config/empresa/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    
    const responseData = response as any
    if (responseData && responseData.logo_url) {
      ecommerceConfig.value.logo_url = responseData.logo_url
      companyLogo.value = responseData.logo_url
      showNotification('Logo cargado exitosamente')
    }
  } catch (error: any) {
    console.error('[ecommerce] Error subiendo logo:', error)
    showNotification('Error al cargar el logo. Asegúrate de guardar la configuración primero.')
  }
}

const handleMenuClick = (item: any) => {
  if (item.tipo === 'scroll') {
    scrollToSection(item.destino)
  } else if (item.tipo === 'modal') {
    // Abrir modal con contenido
    console.log('Abrir modal:', item)
    // TODO: Implementar modal dinámico
  } else if (item.tipo === 'external') {
    window.open(item.destino, '_blank')
  } else if (item.tipo === 'file') {
    window.location.href = item.destino
  } else if (item.tipo === 'content') {
    // Cargar contenido en área de trabajo
    console.log('Cargar contenido:', item)
    // TODO: Implementar carga de contenido
  }
}

// Product Editor
const adminProductSearch = ref('')
const editingProduct = ref<EcommerceProduct | null>(null)
const productImageInput = ref<HTMLInputElement | null>(null)
const productPdfInput = ref<HTMLInputElement | null>(null)
const savingProduct = ref(false)

const filteredAdminProducts = computed(() => {
  if (!adminProductSearch.value.trim()) return allProducts.value
  const search = adminProductSearch.value.toLowerCase()
  return allProducts.value.filter(p =>
    p.name.toLowerCase().includes(search) ||
    p.codigo.toLowerCase().includes(search)
  )
})

// Contenido dinámico desde configuración
const heroTitle = computed(() => ecommerceConfig.value.hero_titulo)
const heroSubtitle = computed(() => ecommerceConfig.value.hero_subtitulo)
const heroDescription = computed(() => ecommerceConfig.value.hero_descripcion)
const aboutText = computed(() => ecommerceConfig.value.about_texto)
const contactText = computed(() => ecommerceConfig.value.contact_texto)
const whatsappNumber = computed(() => ecommerceConfig.value.whatsapp_numero)

const whatsappLink = computed(() => {
  if (!whatsappNumber.value) return null
  const clean = whatsappNumber.value.replace(/[^0-9]/g, '')
  if (!clean) return null
  return `https://wa.me/${clean}`
})

// Temas predefinidos con paletas realmente diferentes y atractivas
const themes = {
  balanceado: {
    primary: '#0066cc',
    secondary: '#3399ff',
    accent: '#66b3ff',
    background: '#f0f7ff',
    surface: '#ffffff',
    text: '#1a1a1a',
    textSecondary: '#666666',
    border: '#d0e5ff',
    success: '#00cc66',
    warning: '#ff9900',
    error: '#ff3333'
  },
  moderno: {
    primary: '#1a1a2e',
    secondary: '#16213e',
    accent: '#0f3460',
    background: '#eaeaea',
    surface: '#ffffff',
    text: '#0a0a0a',
    textSecondary: '#4a4a4a',
    border: '#d0d0d0',
    success: '#00a86b',
    warning: '#ff6b35',
    error: '#e63946'
  },
  minimalista: {
    primary: '#2c3e50',
    secondary: '#34495e',
    accent: '#7f8c8d',
    background: '#ffffff',
    surface: '#f8f9fa',
    text: '#212529',
    textSecondary: '#6c757d',
    border: '#dee2e6',
    success: '#28a745',
    warning: '#ffc107',
    error: '#dc3545'
  },
  colorido: {
    primary: '#e91e63',
    secondary: '#f06292',
    accent: '#f8bbd0',
    background: '#fff0f5',
    surface: '#ffffff',
    text: '#1a1a1a',
    textSecondary: '#666666',
    border: '#ffc1cc',
    success: '#4caf50',
    warning: '#ff9800',
    error: '#f44336'
  },
  elegante: {
    primary: '#2d3436',
    secondary: '#636e72',
    accent: '#b2bec3',
    background: '#f5f6fa',
    surface: '#ffffff',
    text: '#2d3436',
    textSecondary: '#636e72',
    border: '#dfe6e9',
    success: '#00b894',
    warning: '#fdcb6e',
    error: '#d63031'
  }
}

// Estilos dinámicos basados en tema
const currentTheme = computed(() => {
  const tema = ecommerceConfig.value.estilo_tema || 'balanceado'
  return themes[tema as keyof typeof themes] || themes.balanceado
})

// Track si los colores han sido personalizados manualmente
const coloresPersonalizados = ref({
  primario: false,
  secundario: false,
  fondo: false,
  degradado_inicio: false,
  degradado_fin: false
})

// Actualizar colores automáticamente cuando cambia el tema
watch(() => ecommerceConfig.value.estilo_tema, (newTema, oldTema) => {
  if (newTema && themes[newTema as keyof typeof themes] && newTema !== oldTema) {
    const theme = themes[newTema as keyof typeof themes]
    console.log('[ecommerce] Cambiando tema a:', newTema, 'Colores del tema:', theme)
    
    // Cuando cambia el tema, SIEMPRE actualizar los colores (a menos que el usuario los haya editado manualmente después del último cambio de tema)
    // Resetear el tracking solo para los colores que no han sido personalizados manualmente por el usuario
    if (!coloresPersonalizados.value.primario) {
      ecommerceConfig.value.color_primario = theme.primary
      console.log('[ecommerce] Actualizado color_primario a:', theme.primary)
    }
    if (!coloresPersonalizados.value.secundario) {
      ecommerceConfig.value.color_secundario = theme.secondary
      console.log('[ecommerce] Actualizado color_secundario a:', theme.secondary)
    }
    if (!coloresPersonalizados.value.fondo) {
      ecommerceConfig.value.color_fondo = theme.background
      console.log('[ecommerce] Actualizado color_fondo a:', theme.background)
    }
    // Actualizar también los colores del degradado si no están personalizados
    if (!coloresPersonalizados.value.degradado_inicio) {
      ecommerceConfig.value.color_degradado_inicio = theme.primary
      console.log('[ecommerce] Actualizado color_degradado_inicio a:', theme.primary)
    }
    if (!coloresPersonalizados.value.degradado_fin) {
      ecommerceConfig.value.color_degradado_fin = theme.secondary
      console.log('[ecommerce] Actualizado color_degradado_fin a:', theme.secondary)
    }
  }
}, { immediate: false })

// Marcar colores como personalizados cuando el usuario los edita manualmente
const handleColorChange = (tipo: 'primario' | 'secundario' | 'fondo' | 'degradado_inicio' | 'degradado_fin') => {
  coloresPersonalizados.value[tipo] = true
  console.log('[ecommerce] Color personalizado manualmente:', tipo)
}

const containerStyles = computed(() => {
  const theme = currentTheme.value
  const config = ecommerceConfig.value
  
  // Usar color del tema si no está personalizado o es el valor por defecto
  const fondoColor = (config.color_fondo && config.color_fondo !== '#FFFFFF' && coloresPersonalizados.value.fondo)
    ? config.color_fondo
    : theme.background
  
  const styles: Record<string, string> = {
    backgroundColor: fondoColor,
    color: theme.text,
  }
  
  if (config.usar_degradado) {
    // Usar colores del tema si no están personalizados
    const inicioColor = (config.color_degradado_inicio && config.color_degradado_inicio !== '#DC2626' && coloresPersonalizados.value.degradado_inicio)
      ? config.color_degradado_inicio
      : theme.primary
    const finColor = (config.color_degradado_fin && config.color_degradado_fin !== '#FBBF24' && coloresPersonalizados.value.degradado_fin)
      ? config.color_degradado_fin
      : theme.secondary
    styles.background = `linear-gradient(${config.direccion_degradado || 'to right'}, ${inicioColor}, ${finColor})`
    console.log('[ecommerce] Aplicando degradado:', {
      usar_degradado: config.usar_degradado,
      inicioColor,
      finColor,
      direccion: config.direccion_degradado || 'to right',
      tema: ecommerceConfig.value.estilo_tema,
      personalizado_inicio: coloresPersonalizados.value.degradado_inicio,
      personalizado_fin: coloresPersonalizados.value.degradado_fin
    })
  }
  
  return styles
})

const headerStyles = computed(() => {
  const theme = currentTheme.value
  const config = ecommerceConfig.value
  
  // Usar color del tema si no está personalizado
  const primaryColor = (config.color_primario && config.color_primario !== '#DC2626' && coloresPersonalizados.value.primario)
    ? config.color_primario 
    : theme.primary
  
  console.log('[ecommerce] Header styles:', {
    primaryColor,
    tema: ecommerceConfig.value.estilo_tema,
    color_primario_config: config.color_primario,
    personalizado: coloresPersonalizados.value.primario
  })
  
  return {
    backgroundColor: primaryColor,
    color: theme.surface,
    borderRadius: '0',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
  }
})

const themeStyles = computed(() => {
  const theme = currentTheme.value
  return {
    '--theme-primary': theme.primary,
    '--theme-secondary': theme.secondary,
    '--theme-accent': theme.accent,
    '--theme-background': theme.background,
    '--theme-surface': theme.surface,
    '--theme-text': theme.text,
    '--theme-text-secondary': theme.textSecondary,
    '--theme-border': theme.border,
    '--theme-success': theme.success,
    '--theme-warning': theme.warning,
    '--theme-error': theme.error,
  } as Record<string, string>
})

// Productos
interface EcommerceProduct {
  id: string
  name: string
  price: number
  emoji: string
  codigo: string
  imagen_url?: string | null
  categoryId?: string | null
  categoryName?: string | null
  descripcion?: string | null
  pdf_url?: string | null
}

const products = ref<EcommerceProduct[]>([])
const allProducts = ref<EcommerceProduct[]>([]) // Todos los productos para búsqueda
const highlightedProducts = ref<EcommerceProduct[]>([])
const loadingProducts = ref(false)
const productsError = ref<string | null>(null)

// Filtros y paginación incremental fluida
const searchQuery = ref('')
const selectedCategoryId = ref<string | null>(null)
const pageSize = 15 // 15 productos por carga
const isLoadingMore = ref(false)
const displayedCount = ref(pageSize) // Cantidad de productos mostrados (incremental)
const maxDisplayed = 90 // Máximo de productos a renderizar para mantener fluidez

// Categorías derivadas de los productos (no pedimos GRUPMAT aparte por ahora)
const categories = computed(() => {
  const map = new Map<string, { id: string; name: string; icon: string }>()
  for (const p of products.value) {
    if (!p.categoryId && !p.categoryName) continue
    const id = p.categoryId || p.categoryName || ''
    if (!id || map.has(id)) continue
    const name = p.categoryName || id
    const lower = name.toLowerCase()
    let icon = '📦'
    if (lower.includes('hamb') || lower.includes('burger')) icon = '🍔'
    else if (lower.includes('bebida') || lower.includes('refresco') || lower.includes('gaseosa')) icon = '🥤'
    else if (lower.includes('papa') || lower.includes('frita')) icon = '🍟'
    else if (lower.includes('postre') || lower.includes('helado')) icon = '🍰'
    else if (lower.includes('pollo') || lower.includes('alita')) icon = '🍗'

    map.set(id, { id, name, icon })
  }
  return Array.from(map.values())
})

// Productos filtrados (sin paginación - todos los que cumplen el filtro)
const filteredProductsAll = computed(() => {
  let data = [...allProducts.value]
  
  // Si hay búsqueda, filtrar por texto
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    data = data.filter(p =>
      p.name.toLowerCase().includes(q) ||
      (p.categoryName && p.categoryName.toLowerCase().includes(q)) ||
      (p.descripcion && p.descripcion.toLowerCase().includes(q))
    )
  }
  
  // Filtrar por categoría si está seleccionada
  if (selectedCategoryId.value) {
    data = data.filter(p => p.categoryId === selectedCategoryId.value || p.categoryName === selectedCategoryId.value)
  }
  
  return data
})

// Productos visibles (paginación incremental fluida)
const filteredProducts = computed(() => {
  const allFiltered = filteredProductsAll.value
  const countToShow = Math.min(displayedCount.value, allFiltered.length, maxDisplayed)
  
  // Retornar los primeros N productos (incremental)
  return allFiltered.slice(0, countToShow)
})

// Verificar si hay más productos para cargar
const hasMoreProducts = computed(() => {
  return displayedCount.value < filteredProductsAll.value.length && displayedCount.value < maxDisplayed
})

// Cargar más productos (incremental y fluido)
const loadMoreProducts = () => {
  if (isLoadingMore.value || !hasMoreProducts.value) return
  
  isLoadingMore.value = true
  
  // Usar requestAnimationFrame para una transición más fluida
  requestAnimationFrame(() => {
    const newCount = Math.min(
      displayedCount.value + pageSize,
      filteredProductsAll.value.length,
      maxDisplayed
    )
    
    displayedCount.value = newCount
    isLoadingMore.value = false
    
    // Si llegamos al máximo, implementar ventana deslizante suave
    if (displayedCount.value >= maxDisplayed && filteredProductsAll.value.length > maxDisplayed) {
      // Mantener solo los últimos maxDisplayed productos
      // Esto se hace automáticamente en el computed filteredProducts
    }
  })
}

// Observar scroll para cargar más productos (incremental fluido)
const handleScroll = (event: Event) => {
  if (isLoadingMore.value || !hasMoreProducts.value) return
  
  const target = event.target as HTMLElement
  if (!target) return
  
  const scrollTop = target.scrollTop
  const scrollHeight = target.scrollHeight
  const clientHeight = target.clientHeight
  
  // Precargar cuando esté a 200px del final para una experiencia más fluida
  if (scrollTop + clientHeight >= scrollHeight - 200) {
    loadMoreProducts()
  }
}

// Resetear paginación cuando cambia la búsqueda o categoría
watch([searchQuery, selectedCategoryId], () => {
  displayedCount.value = pageSize
  // Resetear scroll de productos
  if (typeof document !== 'undefined') {
    const productsContainer = document.querySelector('.catalog-products')
    if (productsContainer) {
      productsContainer.scrollTop = 0
    }
  }
})

// Carrito
const cart = ref<Array<{ id: string; name: string; price: number; quantity: number }>>([])
const showCart = ref(false)

// Clave para localStorage del carrito (específica por empresa)
const getCartStorageKey = () => {
  const empresaId = session.selectedEmpresa.value?.empresaServidorId || 'default'
  return `ecommerce_cart_${empresaId}`
}

// Guardar carrito en localStorage
const saveCartToStorage = () => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const storageKey = getCartStorageKey()
      localStorage.setItem(storageKey, JSON.stringify(cart.value))
    }
  } catch (error) {
    console.error('[ecommerce] Error guardando carrito en localStorage:', error)
  }
}

// Cargar carrito desde localStorage
const loadCartFromStorage = () => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const storageKey = getCartStorageKey()
      const savedCart = localStorage.getItem(storageKey)
      if (savedCart) {
        const parsed = JSON.parse(savedCart)
        if (Array.isArray(parsed) && parsed.length > 0) {
          cart.value = parsed
          console.log(`[ecommerce] Carrito cargado desde localStorage: ${parsed.length} items`)
        }
      }
    }
  } catch (error) {
    console.error('[ecommerce] Error cargando carrito desde localStorage:', error)
  }
}

// Limpiar carrito del localStorage
const clearCartFromStorage = () => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const storageKey = getCartStorageKey()
      localStorage.removeItem(storageKey)
    }
  } catch (error) {
    console.error('[ecommerce] Error limpiando carrito de localStorage:', error)
  }
}

const cartTotalItems = computed(() =>
  cart.value.reduce((sum, item) => sum + item.quantity, 0)
)

const cartTotal = computed(() =>
  cart.value.reduce((sum, item) => sum + item.price * item.quantity, 0)
)

// Watch para guardar carrito automáticamente cuando cambia
watch(cart, () => {
  saveCartToStorage()
}, { deep: true })

// Notificación toast
const toastMessage = ref<string | null>(null)
const showToast = ref(false)

const showNotification = (message: string) => {
  toastMessage.value = message
  showToast.value = true
  setTimeout(() => {
    showToast.value = false
    setTimeout(() => {
      toastMessage.value = null
    }, 300)
  }, 3000)
}

const addToCart = (product: EcommerceProduct) => {
  const existing = cart.value.find(i => i.id === product.id)
  if (existing) {
    existing.quantity += 1
    showNotification(`${product.name} agregado al carrito (${existing.quantity})`)
  } else {
    cart.value.push({
      id: product.id,
      name: product.name,
      price: product.price,
      quantity: 1
    })
    showNotification(`${product.name} agregado al carrito`)
  }
  // saveCartToStorage() se llama automáticamente por el watch
}

const updateQuantity = (index: number, newQty: number) => {
  if (newQty <= 0) {
    cart.value.splice(index, 1)
  } else {
    cart.value[index].quantity = newQty
  }
}

// Modal producto
const selectedProduct = ref<EcommerceProduct | null>(null)
const openProductModal = (product: EcommerceProduct) => {
  selectedProduct.value = product
}

// Manejar error de carga de imagen
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  if (img) {
    img.style.display = 'none'
    const placeholder = img.parentElement?.querySelector('.product-placeholder')
    if (placeholder) {
      (placeholder as HTMLElement).style.display = 'flex'
    }
  }
}

// Checkout y pago
const showCedulaModal = ref(false)
const showDatosCompletosModal = ref(false)
const showDireccionModal = ref(false)
const processingPayment = ref(false)
const isValidatingDocument = ref(false)
const validatedData = ref<any>({})
const checkoutData = ref({
  docType: 'cedula' as 'cedula' | 'nit',
  cedula: '',
  nature: 'natural' as 'natural' | 'juridica',
  nombre: '',
  telefono: '',
  email: '',
  direccion: ''
})

const proceedToCheckout = () => {
  if (cart.value.length === 0) {
    showNotification('El carrito está vacío')
    return
  }
  showCart.value = false
  showCedulaModal.value = true
  // Resetear datos
  checkoutData.value = {
    docType: 'cedula',
    cedula: '',
    nature: 'natural',
    nombre: '',
    telefono: '',
    email: '',
    direccion: ''
  }
  validatedData.value = {}
}

const validateDocument = async () => {
  if (!checkoutData.value.cedula || checkoutData.value.cedula.length < 7) {
    showNotification('El documento debe tener al menos 7 caracteres')
    return
  }

  if (!session.selectedEmpresa.value) {
    showNotification('No hay empresa seleccionada')
    return
  }

  isValidatingDocument.value = true

  try {
    const empresaId = session.selectedEmpresa.value.empresaServidorId
    
    // Llamar API de validación de tercero
    const response = await api.post('/api/tns/validar-tercero/', {
      empresa_servidor_id: empresaId,
      document_type: checkoutData.value.docType, // 'cedula' o 'nit'
      document_number: checkoutData.value.cedula
    }) as any

    // Si se encontró en TNS o DIAN, prellenar datos
    if (response.encontrado_en_tns || response.encontrado_en_dian) {
      validatedData.value = {
        name: response.nombre || '',
        email: response.email || '',
        telefono: response.telefono || '',
        nit: response.nit || checkoutData.value.cedula
      }
      
      // Prellenar campos del formulario
      if (response.nombre) {
        checkoutData.value.nombre = response.nombre
      }
      if (response.email) {
        checkoutData.value.email = response.email
      }
      if (response.telefono) {
        checkoutData.value.telefono = response.telefono
      }
      
      // Determinar naturaleza según tipo de documento
      if (checkoutData.value.docType === 'nit') {
        checkoutData.value.nature = 'juridica'
      } else {
        checkoutData.value.nature = 'natural'
      }
      
      // Cerrar modal de cédula y abrir modal de datos completos
      showCedulaModal.value = false
      showDatosCompletosModal.value = true
    } else {
      // No se encontró en ningún lado, permitir llenar manualmente
      showNotification('Documento no encontrado. Por favor, completa los datos manualmente.')
      
      // Determinar naturaleza según tipo de documento
      if (checkoutData.value.docType === 'nit') {
        checkoutData.value.nature = 'juridica'
      } else {
        checkoutData.value.nature = 'natural'
      }
      
      // Abrir modal de datos completos para llenar manualmente
      showCedulaModal.value = false
      showDatosCompletosModal.value = true
    }
  } catch (error: any) {
    console.error('[ecommerce] Error validando documento:', error)
    const errorMsg = error?.data?.error || error?.message || 'Error al validar documento'
    showNotification(errorMsg)
    
    // Aún así, permitir continuar manualmente
    if (checkoutData.value.docType === 'nit') {
      checkoutData.value.nature = 'juridica'
    } else {
      checkoutData.value.nature = 'natural'
    }
    showCedulaModal.value = false
    showDatosCompletosModal.value = true
  } finally {
    isValidatingDocument.value = false
  }
}

const goBackToCedulaModal = () => {
  showDatosCompletosModal.value = false
  showCedulaModal.value = true
  // Limpiar datos validados pero mantener el documento
  validatedData.value = {}
}

const confirmDatosCompletos = async () => {
  if (!checkoutData.value.nombre) {
    showNotification('El nombre es requerido')
    return
  }
  
  // Si el tercero no existe en TNS pero tenemos datos, crearlo
  if (!validatedData.value.encontrado_en_tns && checkoutData.value.cedula) {
    try {
      const empresaId = session.selectedEmpresa.value?.empresaServidorId
      if (empresaId) {
        // Crear tercero en TNS
        await api.post('/api/tns/crear-tercero/', {
          empresa_servidor_id: empresaId,
          document_type: checkoutData.value.docType,
          document_number: checkoutData.value.cedula,
          nombre: checkoutData.value.nombre,
          email: checkoutData.value.email || '',
          telefono: checkoutData.value.telefono || '',
          nature: checkoutData.value.nature
        })
        console.log('[ecommerce] Tercero creado en TNS')
      }
    } catch (error: any) {
      console.error('[ecommerce] Error creando tercero:', error)
      // Continuar aunque falle la creación
    }
  }
  
  showDatosCompletosModal.value = false
  showDireccionModal.value = true
}

const confirmDireccion = async () => {
  if (!checkoutData.value.direccion) {
    showNotification('La dirección de envío es requerida')
    return
  }
  
  // Cerrar modal de dirección
  showDireccionModal.value = false
  
  // Cargar formas de pago y luego mostrar modal
  const cargado = await loadFormasPago()
  if (cargado && formasPago.value.length > 0) {
    // Esperar un tick para que Vue actualice el DOM
    await nextTick()
    showFormaPagoModal.value = true
    console.log('[ecommerce] Modal de forma de pago abierta')
  } else if (cargado && formasPago.value.length === 0) {
    showNotification('No hay formas de pago disponibles')
    showDireccionModal.value = true // Volver a mostrar modal de dirección
  }
}

// Modales de pago
const showFormaPagoModal = ref(false)
const showPasarelaModal = ref(false)
const showTarjetaModal = ref(false)
const formasPago = ref<any[]>([])
const loadingFormasPago = ref(false)
const formaPagoSeleccionada = ref<string | null>(null)
const pasarelaSeleccionada = ref<string | null>(null)
const tarjetaData = ref({
  nombre_titular: '',
  cedula_titular: '',
  numero_tarjeta: '',
  mes_vencimiento: '',
  anio_vencimiento: '',
  cvv: ''
})

const loadFormasPago = async () => {
  if (!session.selectedEmpresa.value) {
    showNotification('No hay empresa seleccionada')
    return false
  }
  
  loadingFormasPago.value = true
  try {
    const empresaId = session.selectedEmpresa.value.empresaServidorId
    
    const response = await api.get('/api/formas-pago-ecommerce/', {
      empresa_servidor_id: empresaId
    }) as any
    
    console.log('[ecommerce] Respuesta de formas de pago:', response)
    
    formasPago.value = response.formas_pago || []
    formaPagoSeleccionada.value = null
    
    console.log('[ecommerce] Formas de pago cargadas:', formasPago.value.map(fp => ({ codigo: fp.codigo, descripcion: fp.descripcion })))
    
    console.log(`[ecommerce] Formas de pago cargadas: ${formasPago.value.length} opciones`)
    return true
  } catch (error: any) {
    console.error('[ecommerce] Error cargando formas de pago:', error)
    showNotification(error?.data?.error || error?.message || 'Error al cargar formas de pago')
    formasPago.value = []
    return false
  } finally {
    loadingFormasPago.value = false
  }
}

const getPaymentIcon = (codigo: string): string => {
  const codigoUpper = codigo.toUpperCase()
  if (codigoUpper.includes('EFECTIVO') || codigoUpper.includes('CASH') || codigoUpper === 'EF') {
    return '💵'
  }
  if (codigoUpper.includes('TARJETA') || codigoUpper.includes('CARD') || codigoUpper === 'TC' || codigoUpper === 'TD') {
    return '💳'
  }
  if (codigoUpper.includes('TRANSFERENCIA') || codigoUpper.includes('TRANSFER')) {
    return '🏦'
  }
  if (codigoUpper.includes('NEQUI') || codigoUpper.includes('DAVIPLATA')) {
    return '📱'
  }
  return '💰'
}

const confirmFormaPago = async () => {
  console.log('[ecommerce] confirmFormaPago llamado, formaPagoSeleccionada:', formaPagoSeleccionada.value)
  
  if (!formaPagoSeleccionada.value) {
    showNotification('Por favor selecciona una forma de pago')
    return
  }
  
  // Verificar si es tarjeta (TC o TD generalmente)
  // Los códigos de TNS pueden ser: 'TC', 'TD', 'TCGC', 'TDCG', 'TARJETA CREDITO', 'TARJETA DEBITO', etc.
  const codigoUpper = String(formaPagoSeleccionada.value || '').toUpperCase().trim()
  
  // Detectar si es tarjeta:
  // - Empieza con 'TC' o 'TD' (ej: TC, TD, TCGC, TDCG, etc.)
  // - O contiene palabras clave de tarjeta
  const esTarjeta = codigoUpper.startsWith('TC') || 
                    codigoUpper.startsWith('TD') || 
                    codigoUpper === 'TC' || 
                    codigoUpper === 'TD' || 
                    codigoUpper.includes('TARJETA') || 
                    codigoUpper.includes('CARD') ||
                    codigoUpper.includes('CREDITO') ||
                    codigoUpper.includes('DEBITO')
  
  console.log('[ecommerce] Código forma de pago:', codigoUpper, 'esTarjeta:', esTarjeta)
  console.log('[ecommerce] formaPagoSeleccionada.value completo:', formaPagoSeleccionada.value)
  
  if (esTarjeta) {
    // Si es tarjeta, mostrar modal de pasarela primero
    console.log('[ecommerce] Es tarjeta, cerrando modal forma de pago y cargando pasarelas...')
    showFormaPagoModal.value = false
    
    // Esperar un tick para que Vue actualice el DOM
    await nextTick()
    
    console.log('[ecommerce] Cargando pasarelas disponibles...')
    await loadPasarelasDisponibles()
    
    console.log('[ecommerce] Pasarelas cargadas:', pasarelasDisponibles.value.length)
    console.log('[ecommerce] Abriendo modal de pasarela...')
    
    // Esperar otro tick antes de abrir el modal
    await nextTick()
    showPasarelaModal.value = true
    
    console.log('[ecommerce] Modal de pasarela abierto, showPasarelaModal:', showPasarelaModal.value)
  } else {
    // Si no es tarjeta (efectivo, transferencia, etc.), procesar directamente
    console.log('[ecommerce] No es tarjeta, procesando pago directo...')
    await procesarPagoDirecto()
  }
}

const cancelFormaPago = () => {
  showFormaPagoModal.value = false
  showDireccionModal.value = true
}

const confirmPasarela = async () => {
  console.log('[ecommerce] confirmPasarela llamado, pasarelaSeleccionada:', pasarelaSeleccionada.value)
  
  if (!pasarelaSeleccionada.value) {
    showNotification('Por favor selecciona una pasarela de pago')
    return
  }
  
  console.log('[ecommerce] Cerrando modal de pasarela y abriendo modal de tarjeta...')
  showPasarelaModal.value = false
  
  // Esperar un tick para que Vue actualice el DOM
  await nextTick()
  
  // Resetear datos de tarjeta
  tarjetaData.value = {
    nombre_titular: checkoutData.value.nombre || '',
    cedula_titular: checkoutData.value.cedula || '',
    numero_tarjeta: '',
    mes_vencimiento: '',
    anio_vencimiento: '',
    cvv: ''
  }
  
  showTarjetaModal.value = true
  console.log('[ecommerce] Modal de tarjeta abierto, showTarjetaModal:', showTarjetaModal.value)
}

const cancelPasarela = () => {
  showPasarelaModal.value = false
  showFormaPagoModal.value = true
}

const procesarPagoDirecto = async () => {
  // Para formas de pago que no son tarjeta (efectivo, transferencia, etc.)
  processingPayment.value = true
  showFormaPagoModal.value = false
  
  try {
    const empresaId = session.selectedEmpresa.value?.empresaServidorId
    if (!empresaId) {
      throw new Error('No hay empresa seleccionada')
    }
    
    const cartItems = cart.value.map(item => ({
      id: item.id,
      name: item.name,
      price: item.price,
      quantity: item.quantity
    }))
    
    const response = await api.post('/api/procesar-pago-ecommerce/', {
      empresa_servidor_id: empresaId,
      mock: true,
      tipo_pasarela: null, // No hay pasarela para efectivo/transferencia
      forma_pago_codigo: formaPagoSeleccionada.value,
      cart_items: cartItems,
      monto_total: cartTotal.value,
      doc_type: checkoutData.value.docType,
      document_number: checkoutData.value.cedula,
      nature: checkoutData.value.nature,
      direccion_envio: checkoutData.value.direccion,
      nombre_cliente: checkoutData.value.nombre || undefined,
      telefono_cliente: checkoutData.value.telefono || undefined,
      email_cliente: checkoutData.value.email || undefined
    }) as any
    
    if (response && (response as any).success) {
      showNotification('¡Pedido realizado exitosamente!')
      resetearCheckout()
    } else {
      throw new Error('Error al procesar el pago')
    }
  } catch (error: any) {
    console.error('[ecommerce] Error procesando pago:', error)
    showNotification(error?.data?.detail || error?.message || 'Error al procesar el pago. Por favor intenta nuevamente.')
    showFormaPagoModal.value = true
  } finally {
    processingPayment.value = false
  }
}

const resetearCheckout = () => {
  cart.value = []
  clearCartFromStorage() // Limpiar también del localStorage
  showCart.value = false
  checkoutData.value = {
    docType: 'cedula',
    cedula: '',
    nature: 'natural',
    nombre: '',
    telefono: '',
    email: '',
    direccion: ''
  }
  tarjetaData.value = {
    nombre_titular: '',
    cedula_titular: '',
    numero_tarjeta: '',
    mes_vencimiento: '',
    anio_vencimiento: '',
    cvv: ''
  }
  validatedData.value = {}
  formaPagoSeleccionada.value = null
  pasarelaSeleccionada.value = null
}

const confirmTarjeta = async () => {
  console.log('[ecommerce] confirmTarjeta llamado')
  console.log('[ecommerce] Datos de tarjeta:', {
    nombre: tarjetaData.value.nombre_titular,
    cedula: tarjetaData.value.cedula_titular,
    numero: tarjetaData.value.numero_tarjeta ? '***' + tarjetaData.value.numero_tarjeta.slice(-4) : 'vacío',
    pasarela: pasarelaSeleccionada.value,
    formaPago: formaPagoSeleccionada.value
  })
  
  // Validar datos de tarjeta
  if (!tarjetaData.value.nombre_titular) {
    showNotification('El nombre del titular es requerido')
    return
  }
  if (!tarjetaData.value.numero_tarjeta || tarjetaData.value.numero_tarjeta.length < 13) {
    showNotification('El número de tarjeta debe tener al menos 13 dígitos')
    return
  }
  if (!tarjetaData.value.mes_vencimiento || !tarjetaData.value.anio_vencimiento) {
    showNotification('La fecha de vencimiento es requerida')
    return
  }
  if (!tarjetaData.value.cvv || tarjetaData.value.cvv.length < 3) {
    showNotification('El CVV es requerido (mínimo 3 dígitos)')
    return
  }
  
  // Procesar pago
  processingPayment.value = true
  showTarjetaModal.value = false
  
  try {
    const empresaId = session.selectedEmpresa.value?.empresaServidorId
    if (!empresaId) {
      throw new Error('No hay empresa seleccionada')
    }
    
    // Preparar datos del pago
    const cartItems = cart.value.map(item => ({
      id: item.id,
      name: item.name,
      price: item.price,
      quantity: item.quantity
    }))
    
    // NO enviar mock desde el frontend
    // El backend decidirá automáticamente según la configuración de la pasarela
    // Si payment_mode es 'test', el backend puede usar mock según su configuración
    // Si payment_mode es 'live', el backend usará la pasarela real
    
    const response = await api.post('/api/procesar-pago-ecommerce/', {
      empresa_servidor_id: empresaId,
      // NO enviar mock: el backend lo decide según la pasarela configurada
      cart_items: cartItems,
      monto_total: cartTotal.value,
      doc_type: checkoutData.value.docType,
      document_number: checkoutData.value.cedula,
      nature: checkoutData.value.nature,
      direccion_envio: checkoutData.value.direccion,
      nombre_cliente: checkoutData.value.nombre || undefined,
      telefono_cliente: checkoutData.value.telefono || undefined,
      email_cliente: checkoutData.value.email || undefined,
      // Datos de tarjeta
      forma_pago_codigo: formaPagoSeleccionada.value,
      tarjeta: {
        nombre_titular: tarjetaData.value.nombre_titular,
        cedula_titular: tarjetaData.value.cedula_titular,
        numero: tarjetaData.value.numero_tarjeta.replace(/\s/g, ''),
        mes_vencimiento: tarjetaData.value.mes_vencimiento,
        anio_vencimiento: tarjetaData.value.anio_vencimiento,
        cvv: tarjetaData.value.cvv
      }
    }) as any
    
    console.log('[ecommerce] Respuesta del backend:', response)
    
    if (response && (response as any).success) {
      // Si es mock, el pago ya está procesado
      if ((response as any).mock) {
        showNotification('¡Pedido realizado exitosamente!')
        resetearCheckout()
      } else {
        // Si es pasarela real, recibimos formUrl
        const formUrl = (response as any).formUrl
        console.log('[ecommerce] formUrl recibido:', formUrl)
        
        if (formUrl) {
          // Abrir formUrl según configuración
          const windowType = ecommerceConfig.value.payment_window_type || 'new_window'
          console.log('[ecommerce] Tipo de ventana configurado:', windowType)
          
          if (windowType === 'modal') {
            // Abrir en modal/iframe (futuro)
            showNotification('Redirigiendo a la pasarela de pago...')
            window.open(formUrl, '_blank', 'width=800,height=600')
          } else if (windowType === 'same_window') {
            // Redirigir en la misma ventana
            console.log('[ecommerce] Redirigiendo a:', formUrl)
            window.location.href = formUrl
          } else {
            // new_window (por defecto) - Nueva ventana/pestaña
            console.log('[ecommerce] Abriendo nueva ventana con:', formUrl)
            const newWindow = window.open(formUrl, '_blank')
            if (newWindow) {
              showNotification('Completa el pago en la ventana que se abrió')
            } else {
              // Si el popup fue bloqueado, redirigir en la misma ventana
              showNotification('Popup bloqueado. Redirigiendo...')
              window.location.href = formUrl
            }
          }
        } else {
          console.error('[ecommerce] No se recibió formUrl en la respuesta:', response)
          throw new Error('No se recibió formUrl de la pasarela')
        }
      }
    } else {
      console.error('[ecommerce] Respuesta sin success:', response)
      throw new Error('Error al procesar el pago')
    }
  } catch (error: any) {
    console.error('[ecommerce] Error procesando pago:', error)
    console.error('[ecommerce] Detalles del error:', {
      message: error?.message,
      data: error?.data,
      response: error?.response
    })
    
    const errorMessage = error?.data?.detail || error?.response?.data?.detail || error?.message || 'Error al procesar el pago. Por favor intenta nuevamente.'
    showNotification(errorMessage)
    showTarjetaModal.value = true // Volver a mostrar modal de tarjeta en caso de error
  } finally {
    processingPayment.value = false
  }
}

const cancelTarjeta = () => {
  showTarjetaModal.value = false
  showPasarelaModal.value = true
}

const formatCardNumber = (event: Event) => {
  const input = event.target as HTMLInputElement
  let value = input.value.replace(/\s/g, '')
  value = value.replace(/\D/g, '')
  if (value.length > 16) value = value.slice(0, 16)
  // Formatear con espacios cada 4 dígitos
  const formatted = value.match(/.{1,4}/g)?.join(' ') || value
  tarjetaData.value.numero_tarjeta = formatted
}

// Modales
const showContactModal = ref(false)
const showAboutModal = ref(false)
const showHeroModal = ref(false)
const showGenericModal = ref(false)
const currentModalContent = ref('')

// Utilidades
const formatPrice = (value: number) => {
  return new Intl.NumberFormat('es-CO', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value || 0)
}

const scrollToSection = (id: string) => {
  if (typeof document === 'undefined') return
  const el = document.getElementById(id)
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// Admin Functions
const handleAdminLogin = async () => {
  loggingIn.value = true
  adminLoginError.value = null
  
  try {
    const empresaId = session.selectedEmpresa.value?.empresaServidorId
    if (!empresaId) {
      throw new Error('No hay empresa seleccionada')
    }
    
    // Validar usuario TNS (ADMIN)
    await session.validateTNSUser({
      empresa_servidor_id: empresaId,
      username: 'ADMIN',
      password: adminLoginForm.value.password
    })
    
    // Guardar contraseña para usar en guardados posteriores
    adminPassword.value = adminLoginForm.value.password
    
    isAdmin.value = true
    showAdminLogin.value = false
    adminLoginForm.value.password = ''
    showNotification('Sesión de administrador iniciada')
    // Cargar pasarelas cuando se inicia sesión como admin
    loadPasarelasDisponibles()
  } catch (error: any) {
    console.error('[ecommerce] Error en login admin:', error)
    adminLoginError.value = error?.data?.message || error?.data?.detail || 'Contraseña incorrecta'
  } finally {
    loggingIn.value = false
  }
}

const confirmSaveWithPassword = async () => {
  savePasswordError.value = null
  const passwordToUse = savePasswordForm.value.password
  await performSaveConfig(passwordToUse)
  if (!savePasswordError.value) {
    // Guardar contraseña si el guardado fue exitoso
    adminPassword.value = passwordToUse
    showPasswordModal.value = false
    savePasswordForm.value.password = ''
  }
}

const performSaveConfig = async (password: string) => {
  if (!ecommerceConfig.value.empresa_servidor_id) {
    showNotification('No hay empresa seleccionada')
    return
  }
  
  savingConfig.value = true
  try {
    // Preparar datos para enviar (sin password_tns si está vacío/null)
    const dataToSend: any = {
      empresa_servidor_id: ecommerceConfig.value.empresa_servidor_id,
      username: 'ADMIN',
      password: password,
      ...ecommerceConfig.value
    }
    
    // Si password_tns está vacío o null, no enviarlo (para no sobrescribir el existente)
    if (!dataToSend.password_tns || dataToSend.password_tns === '') {
      delete dataToSend.password_tns
    }
    
    await api.put('/api/ecommerce-config/empresa/', dataToSend)
    showNotification('Configuración guardada exitosamente')
    
    // Limpiar password_tns del frontend después de guardar (por seguridad)
    ecommerceConfig.value.password_tns = null
  } catch (error: any) {
    console.error('[ecommerce] Error guardando configuración:', error)
    const errorMsg = error?.response?.data?.detail || 'Error al guardar la configuración'
    savePasswordError.value = errorMsg
    showNotification(errorMsg)
  } finally {
    savingConfig.value = false
  }
}

const loadEcommerceConfig = async (empresaServidorId: number) => {
  try {
    const response = await api.get('/api/ecommerce-config/empresa/', {
      empresa_servidor_id: empresaServidorId
    })
    
    if (response) {
      const configData = response as any
      const tema = configData.estilo_tema || 'balanceado'
      const theme = themes[tema as keyof typeof themes] || themes.balanceado
      
      // Al cargar, NO marcar como personalizados automáticamente
      // Solo se marcarán como personalizados cuando el usuario los edite manualmente
      // Resetear el tracking para permitir que el tema actualice los colores
      coloresPersonalizados.value = {
        primario: false,
        secundario: false,
        fondo: false,
        degradado_inicio: false,
        degradado_fin: false
      }
      
      // Determinar colores según el tema (siempre usar del tema al cargar)
      const colorPrimario = theme.primary
      const colorSecundario = theme.secondary
      const colorFondo = theme.background
      const colorDegradadoInicio = theme.primary
      const colorDegradadoFin = theme.secondary
      
      ecommerceConfig.value = {
        ...ecommerceConfig.value,
        ...configData,
        empresa_servidor_id: empresaServidorId,
        footer_sections: configData.footer_sections || [],
        menu_items: configData.menu_items || [],
        // Aplicar colores del tema si no están personalizados
        color_primario: colorPrimario,
        color_secundario: colorSecundario,
        color_fondo: colorFondo,
        // Actualizar también los colores del degradado si no están personalizados
        color_degradado_inicio: colorDegradadoInicio,
        color_degradado_fin: colorDegradadoFin
      }
      
      console.log('[ecommerce] Colores aplicados del tema:', {
        tema,
        color_primario: colorPrimario,
        color_secundario: colorSecundario,
        color_fondo: colorFondo,
        color_degradado_inicio: colorDegradadoInicio,
        color_degradado_fin: colorDegradadoFin,
        personalizados: coloresPersonalizados.value
      })
      
      // Actualizar logo si existe
      if (configData.logo_url) {
        companyLogo.value = configData.logo_url
      }
      
      // NO cargar password_tns en el frontend por seguridad (solo se puede editar, no ver)
      // Si viene password_tns, no lo asignamos (se mantiene null para que el usuario lo ingrese nuevamente)
      if (configData.password_tns) {
        // No asignar el password al frontend por seguridad
        ecommerceConfig.value.password_tns = null
      }
      
      console.log('[ecommerce] Configuración cargada:', ecommerceConfig.value)
      
      // Cargar pasarelas si es admin
      if (isAdmin.value) {
        loadPasarelasDisponibles()
      }
    }
  } catch (error: any) {
    console.error('[ecommerce] Error cargando configuración:', error)
    // Usar valores por defecto si no existe configuración
    ecommerceConfig.value.empresa_servidor_id = empresaServidorId
  }
}

const saveEcommerceConfig = async () => {
  if (!ecommerceConfig.value.empresa_servidor_id) {
    showNotification('No hay empresa seleccionada')
    return
  }
  
  // Si tenemos la contraseña guardada (de login previo), usarla directamente
  if (adminPassword.value) {
    await performSaveConfig(adminPassword.value)
    return
  }
  
  // Si no, mostrar modal para pedir contraseña
  showPasswordModal.value = true
  savePasswordForm.value.password = ''
  savePasswordError.value = null
}

const openProductEditor = (product: EcommerceProduct) => {
  editingProduct.value = { ...product }
}

const handleProductImageUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file || !editingProduct.value) return
  
  try {
    const formData = new FormData()
    formData.append('imagen', file)
    formData.append('nit_normalizado', session.selectedEmpresa.value?.nit || '')
    formData.append('codigo_material', editingProduct.value.codigo)
    
    const response = await api.post('/api/branding/material/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    if (response?.imagen_url) {
      editingProduct.value.imagen_url = response.imagen_url
      // Actualizar también en allProducts
      const productIndex = allProducts.value.findIndex(p => p.id === editingProduct.value!.id)
      if (productIndex >= 0) {
        allProducts.value[productIndex].imagen_url = response.imagen_url
      }
      showNotification('Imagen actualizada')
    }
  } catch (error: any) {
    console.error('[ecommerce] Error subiendo imagen:', error)
    showNotification('Error al subir la imagen')
  }
}

const handleProductPdfUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file || !editingProduct.value) return
  
  try {
    const formData = new FormData()
    formData.append('pdf', file)
    formData.append('nit_normalizado', session.selectedEmpresa.value?.nit || '')
    formData.append('codigo_material', editingProduct.value.codigo)
    
    // Nota: Necesitarás crear un endpoint para PDFs o usar el mismo de branding
    // Por ahora, asumimos que se puede agregar al endpoint de material
    const response = await api.post('/api/branding/material/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    if (response?.pdf_url) {
      editingProduct.value.pdf_url = response.pdf_url
      const productIndex = allProducts.value.findIndex(p => p.id === editingProduct.value!.id)
      if (productIndex >= 0) {
        allProducts.value[productIndex].pdf_url = response.pdf_url
      }
      showNotification('PDF actualizado')
    }
  } catch (error: any) {
    console.error('[ecommerce] Error subiendo PDF:', error)
    showNotification('Error al subir el PDF')
  }
}

const saveProductChanges = async () => {
  if (!editingProduct.value) return
  
  savingProduct.value = true
  try {
    const nit_normalizado = session.selectedEmpresa.value?.nit || ''
    
    // Guardar descripción/características
    const formData = new FormData()
    formData.append('nit_normalizado', nit_normalizado)
    formData.append('codigo_material', editingProduct.value.codigo)
    formData.append('caracteristicas', editingProduct.value.descripcion || '')
    
    await api.put('/api/branding/material/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    // Actualizar en allProducts
    const productIndex = allProducts.value.findIndex(p => p.id === editingProduct.value!.id)
    if (productIndex >= 0) {
      allProducts.value[productIndex].descripcion = editingProduct.value.descripcion
    }
    
    editingProduct.value = null
    showNotification('Producto actualizado exitosamente')
  } catch (error: any) {
    console.error('[ecommerce] Error guardando producto:', error)
    showNotification('Error al guardar el producto')
  } finally {
    savingProduct.value = false
  }
}

const addFooterLink = () => {
  ecommerceConfig.value.footer_links.push({
    titulo: '',
    url: '',
    tipo: 'modal'
  })
}

const removeFooterLink = (index: number) => {
  ecommerceConfig.value.footer_links.splice(index, 1)
}

const addFooterSection = () => {
  if (!ecommerceConfig.value.footer_sections) {
    ecommerceConfig.value.footer_sections = []
  }
  ecommerceConfig.value.footer_sections.push({
    titulo: '',
    links: []
  })
}

const removeFooterSection = (index: number) => {
  if (ecommerceConfig.value.footer_sections) {
    ecommerceConfig.value.footer_sections.splice(index, 1)
  }
}

const addFooterLinkToSection = (sectionIndex: number) => {
  if (ecommerceConfig.value.footer_sections && ecommerceConfig.value.footer_sections[sectionIndex]) {
    ecommerceConfig.value.footer_sections[sectionIndex].links.push({
      icono: '',
      titulo: '',
      url: '',
      tipo: 'modal'
    })
  }
}

const addMenuItem = () => {
  if (!ecommerceConfig.value.menu_items) {
    ecommerceConfig.value.menu_items = []
  }
  ecommerceConfig.value.menu_items.push({
    icono: '',
    texto: '',
    tipo: 'scroll',
    destino: '',
    contenido: ''
  })
}

const removeMenuItem = (index: number) => {
  if (ecommerceConfig.value.menu_items) {
    ecommerceConfig.value.menu_items.splice(index, 1)
  }
}

const removeFooterLinkFromSection = (sectionIndex: number, linkIndex: number) => {
  if (ecommerceConfig.value.footer_sections && ecommerceConfig.value.footer_sections[sectionIndex]) {
    ecommerceConfig.value.footer_sections[sectionIndex].links.splice(linkIndex, 1)
  }
}

const handleFooterLink = (link: any) => {
  if (link.tipo === 'modal') {
    // Determinar qué modal abrir según el destino
    if (link.destino === 'hero' || link.destino === 'inicio') {
      showHeroModal.value = true
    } else if (link.destino === 'about' || link.destino === 'nosotros') {
      showAboutModal.value = true
    } else if (link.destino === 'contact' || link.destino === 'contacto') {
      showContactModal.value = true
    } else {
      // Modal genérico con contenido personalizado
      currentModalContent.value = link.contenido || link.destino
      showGenericModal.value = true
    }
  } else if (link.tipo === 'scroll') {
    scrollToSection(link.destino)
  } else if (link.tipo === 'external') {
    window.open(link.url || link.destino, '_blank')
  } else if (link.tipo === 'file') {
    window.location.href = link.url || link.destino
  }
}

// Cargar empresa desde dominio
const loadEmpresaFromDomain = async () => {
  if (typeof window === 'undefined') return false
  
  try {
    const dominio = window.location.host
    console.log('[ecommerce] Cargando empresa desde dominio:', dominio)
    
    // Usar el endpoint público de catálogo (más seguro, SQL queries predefinidos)
    const response = await api.get('/api/public-catalog/', {
      dominio
    })
    
    console.log('[ecommerce] Respuesta del endpoint:', response)
    console.log('[ecommerce] Tipo de respuesta:', typeof response)
    
    // useApiClient.get() retorna los datos directamente
    const data = response
    
    console.log('[ecommerce] Datos procesados:', data)
    console.log('[ecommerce] Estructura de respuesta:', {
      tiene_empresa: !!data?.empresa,
      tiene_productos: !!data?.productos,
      tiene_categorias: !!data?.categorias,
      tiene_mas_vendidos: !!data?.mas_vendidos
    })
    
    if (data && data.empresa && data.empresa.empresa_servidor_id) {
        const empresaData = data.empresa
        
        // Establecer empresa en la sesión
        const empresaSessionData = {
          empresaServidorId: empresaData.empresa_servidor_id,
          nombre: empresaData.nombre,
          nombreComercial: empresaData.nombre_comercial || empresaData.nombre,
          nit: empresaData.nit || '',
          anioFiscal: empresaData.anio_fiscal,
          codigo: '',
          preferredTemplate: 'ecommerce',
          source: 'admin' as const
        }
        
        console.log('[ecommerce] Datos de empresa a establecer:', empresaSessionData)
        session.selectEmpresa(empresaSessionData)
        
        // Esperar un tick para que la reactividad se actualice
        await nextTick()
        
        console.log('[ecommerce] Empresa establecida en sesión:', session.selectedEmpresa.value)
        console.log('[ecommerce] Empresa ID en sesión:', session.selectedEmpresa.value?.empresaServidorId)
        
        // Guardar logo si existe
        if (empresaData.logo_url) {
          companyLogo.value = empresaData.logo_url
          console.log('[ecommerce] Logo cargado:', empresaData.logo_url)
        } else {
          console.log('[ecommerce] No hay logo disponible')
        }
        
        console.log('[ecommerce] ✅ Empresa cargada exitosamente:', empresaData.nombre_comercial || empresaData.nombre)
        
        // Cargar configuración del e-commerce
        await loadEcommerceConfig(empresaData.empresa_servidor_id)
        
        // Procesar productos, categorías y más vendidos
        if (data.productos && Array.isArray(data.productos) && data.productos.length > 0) {
          console.log('[ecommerce] Procesando productos de la respuesta:', data.productos.length)
          processProductsFromResponse(data.productos, data.mas_vendidos || [])
          return true
        } else {
          console.warn('[ecommerce] ⚠️  No hay productos en la respuesta')
          return true
        }
      } else {
        console.error('[ecommerce] ❌ Respuesta sin empresa_servidor_id:', data)
        productsError.value = 'La respuesta del servidor no contiene información de empresa válida.'
        return false
      }
  } catch (error: any) {
    console.error('[ecommerce] ❌ Error cargando empresa desde dominio:', error)
    console.error('[ecommerce] Detalles del error:', {
      message: error.message,
      response: error.response,
      status: error.response?.status,
      data: error.response?.data
    })
    
    if (error.response?.status === 404) {
      productsError.value = `Dominio no encontrado: ${window.location.host}. Por favor, verifica la URL.`
    } else {
      productsError.value = `Error al cargar información de la empresa: ${error.message || 'Error desconocido'}`
    }
    return false
  }
}

// Procesar productos desde la respuesta del endpoint
const processProductsFromResponse = (productosData: any[], masVendidosData: any[] = []) => {
  console.log('[ecommerce] Procesando productos desde respuesta:', productosData.length)
  
  const productsMap = new Map<string, EcommerceProduct>()
  
  for (const row of productosData) {
    const codigo = row.CODIGO || row.codigo
    if (!codigo) continue
    
    const basePrice = parseFloat(row.PRECIO1 || row.precio1 || 0) || 0
    const name = row.DESCRIP || row.descrip || codigo
    const gmDescrip = row.GM_DESCRIP || row.gm_descrip || null
    const gmCodigo = row.GM_CODIGO || row.gm_codigo || null
    
    // Obtener imagen_url y caracteristicas del backend
    const imagenUrl = row.imagen_url || null
    const caracteristicas = row.caracteristicas || null
    
    if (!productsMap.has(codigo)) {
      let emoji = '📦'
      const lower = (gmDescrip || '').toLowerCase()
      if (lower.includes('hamb') || lower.includes('burger')) emoji = '🍔'
      else if (lower.includes('bebida') || lower.includes('refresco') || lower.includes('gaseosa')) emoji = '🥤'
      else if (lower.includes('papa') || lower.includes('frita')) emoji = '🍟'
      else if (lower.includes('postre') || lower.includes('helado')) emoji = '🍰'
      else if (lower.includes('pollo') || lower.includes('alita')) emoji = '🍗'
      
        // Obtener pdf_url del backend
        const pdfUrl = row.pdf_url || null
        
        productsMap.set(codigo, {
          id: codigo,
          name,
          price: basePrice,
          emoji,
          codigo,
          imagen_url: imagenUrl,
          categoryId: gmCodigo,
          categoryName: gmDescrip,
          descripcion: caracteristicas || name,
          pdf_url: pdfUrl
        })
    }
  }
  
  products.value = Array.from(productsMap.values())
  allProducts.value = [...products.value] // Guardar todos para búsqueda
  console.log('[ecommerce] ✅ Productos procesados:', products.value.length)
  console.log('[ecommerce] Productos con imagen:', products.value.filter(p => p.imagen_url).length)
  
  // Procesar más vendidos (ya vienen limitados a 5 desde el backend)
  if (masVendidosData.length > 0) {
    const masVendidosMap = new Map<string, EcommerceProduct>()
    for (const row of masVendidosData) {
      const codigo = row.CODIGO || row.codigo
      if (!codigo) continue
      
      const basePrice = parseFloat(row.PRECIO1 || row.precio1 || 0) || 0
      const name = row.DESCRIP || row.descrip || codigo
      const gmDescrip = row.GM_DESCRIP || row.gm_descrip || null
      
      if (!masVendidosMap.has(codigo)) {
        let emoji = '📦'
        const lower = (gmDescrip || '').toLowerCase()
        if (lower.includes('hamb') || lower.includes('burger')) emoji = '🍔'
        else if (lower.includes('bebida') || lower.includes('refresco') || lower.includes('gaseosa')) emoji = '🥤'
        else if (lower.includes('papa') || lower.includes('frita')) emoji = '🍟'
        else if (lower.includes('postre') || lower.includes('helado')) emoji = '🍰'
        else if (lower.includes('pollo') || lower.includes('alita')) emoji = '🍗'
        
        // Obtener imagen_url y caracteristicas del backend
        const imagenUrl = row.imagen_url || null
        const caracteristicas = row.caracteristicas || null
        
        // Obtener pdf_url del backend
        const pdfUrl = row.pdf_url || null
        
        masVendidosMap.set(codigo, {
          id: codigo,
          name,
          price: basePrice,
          emoji,
          codigo,
          imagen_url: imagenUrl,
          categoryId: row.GM_CODIGO || row.gm_codigo || null,
          categoryName: gmDescrip,
          descripcion: caracteristicas || name,
          pdf_url: pdfUrl
        })
      }
    }
    
    highlightedProducts.value = Array.from(masVendidosMap.values())
    console.log('[ecommerce] ✅ Más vendidos procesados:', highlightedProducts.value.length)
  } else {
    // Si no hay más vendidos, usar los de mayor precio (máximo 5)
    highlightedProducts.value = [...products.value]
      .sort((a, b) => b.price - a.price)
      .slice(0, 5)
  }
}

// Carga de productos desde TNS (sin requerir login de usuario final, solo empresa seleccionada)
const loadProducts = async () => {
  console.log('[ecommerce] Iniciando carga de productos...')
  console.log('[ecommerce] Empresa seleccionada:', session.selectedEmpresa.value)
  
  const empresaId = session.selectedEmpresa.value?.empresaServidorId
  if (!empresaId) {
    console.warn('[ecommerce] ❌ No hay empresa seleccionada, no se pueden cargar productos')
    productsError.value = 'No hay empresa seleccionada. No se pueden cargar productos.'
    return
  }

  console.log('[ecommerce] Empresa ID:', empresaId)

  const config = getConfig('materialprecio')
  if (!config) {
    console.error('[ecommerce] ❌ Configuración de materiales no encontrada')
    productsError.value = 'Configuración no encontrada'
    return
  }

  console.log('[ecommerce] Configuración encontrada:', config)

  loadingProducts.value = true
  productsError.value = null

  try {
    console.log('[ecommerce] Haciendo petición a fetchRecords...')
    const response = await fetchRecords(config, {
      empresa_servidor_id: empresaId,
      page: 1,
      page_size: 200,
      order_by: [{ field: 'CODIGO', direction: 'ASC' }],
      filters: {
        PRECIO1: { operator: '>', value: 0 }
      }
    })

    const productsMap = new Map<string, EcommerceProduct>()

    for (const row of response.data) {
      const codigo = row.CODIGO || row.codigo
      if (!codigo) continue

      const basePrice = parseFloat(row.PRECIO1 || row.precio1 || 0) || 0
      const name = row.DESCRIP || row.descrip || codigo
      const gmDescrip = row.GM_DESCRIP || row.gm_descrip || null
      const gmCodigo = row.GM_CODIGO || row.gm_codigo || null

      if (productsMap.has(codigo)) {
        const existing = productsMap.get(codigo)!
        if (row.imagen_url && !existing.imagen_url) existing.imagen_url = row.imagen_url
        const newPrice = basePrice
        if (newPrice > existing.price) existing.price = newPrice
      } else {
        let emoji = '📦'
        const lower = (gmDescrip || '').toLowerCase()
        if (lower.includes('hamb') || lower.includes('burger')) emoji = '🍔'
        else if (lower.includes('bebida') || lower.includes('refresco') || lower.includes('gaseosa')) emoji = '🥤'
        else if (lower.includes('papa') || lower.includes('frita')) emoji = '🍟'
        else if (lower.includes('postre') || lower.includes('helado')) emoji = '🍰'
        else if (lower.includes('pollo') || lower.includes('alita')) emoji = '🍗'

        // Obtener imagen_url y caracteristicas del backend
        const imagenUrl = row.imagen_url || null
        const caracteristicas = row.caracteristicas || null
        
        // Obtener pdf_url del backend
        const pdfUrl = row.pdf_url || null
        
        productsMap.set(codigo, {
          id: codigo,
          name,
          price: basePrice,
          emoji,
          codigo,
          imagen_url: imagenUrl,
          categoryId: gmCodigo,
          categoryName: gmDescrip,
          descripcion: caracteristicas || name,
          pdf_url: pdfUrl
        })
      }
    }

    products.value = Array.from(productsMap.values())
    allProducts.value = [...products.value] // Guardar todos para búsqueda
    console.log('[ecommerce] ✅ Productos cargados:', products.value.length)

    // “Más buscados”: por ahora usamos los de mayor precio como proxy simple (máximo 5)
    highlightedProducts.value = [...products.value]
      .sort((a, b) => b.price - a.price)
      .slice(0, 5)
    console.log('[ecommerce] ✅ Productos destacados:', highlightedProducts.value.length)
  } catch (error: any) {
    console.error('[ecommerce] ❌ Error cargando productos:', error)
    console.error('[ecommerce] Detalles del error:', {
      message: error.message,
      response: error.response,
      data: error.response?.data
    })
    productsError.value = error?.message || 'Error al cargar productos'
  } finally {
    loadingProducts.value = false
    console.log('[ecommerce] Carga de productos finalizada')
  }
}

// Manejar query params al volver del callback de pago
const handlePaymentCallback = () => {
  const query = route.query
  if (query.payment_success === 'true') {
    const orderNumber = query.order_number as string
    const factura = query.factura as string
    showNotification(`¡Pago exitoso! Factura: ${factura || orderNumber}`)
    resetearCheckout()
    // Limpiar query params
    router.replace({ query: {} })
  } else if (query.payment_error) {
    const error = query.payment_error as string
    const orderNumber = query.order_number as string
    let errorMessage = 'Error en el pago'
    if (error === 'rechazado') {
      errorMessage = 'El pago fue rechazado. Por favor intenta con otro método de pago.'
    } else if (error === 'factura_error') {
      errorMessage = 'El pago fue exitoso pero hubo un error al crear la factura. Por favor contacta al soporte.'
    } else if (error === 'transaccion_no_encontrada') {
      errorMessage = 'No se encontró la transacción. Por favor contacta al soporte.'
    } else if (error === 'consulta_error') {
      errorMessage = 'Error al consultar el estado del pago. Por favor contacta al soporte.'
    }
    showNotification(errorMessage)
    // Limpiar query params
    router.replace({ query: {} })
  }
}

onMounted(async () => {
  // Cargar carrito desde localStorage
  loadCartFromStorage()
  
  // Manejar callback de pago si viene en query params
  handlePaymentCallback()
  
  // Mostrar loading mientras se cargan los datos
  loadingPage.value = true
  
  try {
    // Primero cargar empresa desde dominio (incluye productos si include_products=true)
    const empresaCargada = await loadEmpresaFromDomain()
    if (empresaCargada) {
      // Solo cargar productos adicionales si no vinieron en la respuesta del endpoint
      if (products.value.length === 0) {
        console.log('[ecommerce] No hay productos en respuesta, cargando desde TNS...')
        await loadProducts()
      } else {
        console.log('[ecommerce] Productos ya cargados desde respuesta del endpoint')
      }
    }
  } finally {
    // Ocultar loading después de cargar todo
    loadingPage.value = false
  }
})
</script>

<style>
/* Resetear márgenes globales para e-commerce - SIN SCOPED para que funcione */
body,
html {
  margin: 0 !important;
  padding: 0 !important;
  width: 100% !important;
  max-width: 100% !important;
  overflow-x: hidden !important;
  box-sizing: border-box !important;
}

#__nuxt,
#__nuxt > div {
  margin: 0 !important;
  padding: 0 !important;
  width: 100% !important;
  max-width: 100% !important;
}

/* Eliminar padding del layout default cuando es ecommerce */
.default-layout.mode-ecommerce,
.default-layout.mode-ecommerce .default-main {
  padding: 0 !important;
  margin: 0 !important;
}
</style>

<style scoped>
.ecommerce-container {
  min-height: 100vh;
  width: 100vw;
  max-width: 100vw;
  padding: 0;
  margin: 0;
  box-sizing: border-box;
  background: var(--theme-background, #f0f7ff);
  color: var(--theme-text, #1a1a1a);
  overflow-x: hidden;
  position: relative;
  left: 0;
  top: 0;
}

.ecommerce-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 1rem;
  align-items: center;
  background: var(--theme-primary, #2563eb);
  color: var(--theme-surface, #ffffff);
  padding: 1rem 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 0;
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
}

.logo-block {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.company-logo {
  width: 52px;
  height: 52px;
  object-fit: contain;
}

.company-name {
  font-size: 1.6rem;
  font-weight: 800;
  margin: 0;
  color: var(--theme-surface, #ffffff);
}

.company-tagline {
  margin: 0.25rem 0 0;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.8);
}

.header-center {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.main-nav {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border: none;
  background: transparent;
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--theme-surface, #ffffff);
  cursor: pointer;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  transition: all 0.2s;
}

.nav-link-icon {
  font-size: 1.1rem;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--theme-surface, #ffffff);
}

.nav-link:hover {
  background: #fee2e2;
  color: #b91c1c;
}

.search-bar-categories {
  width: 100%;
  margin-bottom: 0.75rem;
}

.search-input-categories {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  font-size: 0.9rem;
  background: #f9fafb;
  box-sizing: border-box;
}

.header-right {
  display: flex;
  justify-content: flex-end;
}

.cart-button {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  padding: 0.35rem 0.7rem;
  cursor: pointer;
  font-size: 0.85rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.cart-icon {
  font-size: 1.2rem;
}

.cart-text {
  font-weight: 600;
}

.cart-badge-ecom {
  background: var(--theme-error, #ef4444);
  color: var(--theme-surface, #ffffff);
  border-radius: 12px;
  padding: 0.15rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 700;
  min-width: 20px;
  text-align: center;
}

.hero-section {
  background: var(--theme-surface, #ffffff);
  border-radius: 16px;
  padding: 3rem 2.5rem;
  margin-bottom: 2rem;
  text-align: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid var(--theme-border, #e2e8f0);
}

.hero-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.hero-title {
  font-size: 2rem;
  font-weight: 800;
  margin: 0;
}

.hero-subtitle {
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
  color: var(--theme-text-secondary, #64748b);
  font-weight: 400;
}

.hero-actions {
  margin-top: 0.75rem;
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.primary-btn,
.secondary-btn {
  border-radius: 999px;
  padding: 0.55rem 1.1rem;
  font-size: 0.9rem;
  cursor: pointer;
  border: none;
}

.primary-btn {
  background: var(--theme-primary, #2563eb);
  color: var(--theme-surface, #ffffff);
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.primary-btn:hover {
  background: var(--theme-secondary, #3b82f6);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.secondary-btn {
  background: white;
  color: #111827;
  border: 1px solid #e5e7eb;
}

.hero-media {
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
}

.hero-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.about-section,
.featured-section,
.catalog-section,
.contact-section {
  background: var(--theme-surface, #ffffff);
  border-radius: 16px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid var(--theme-border, #e2e8f0);
}

.section-header h3 {
  margin: 0 0 0.75rem;
  font-size: 1.2rem;
}

.about-text,
.contact-text {
  margin: 0;
  color: #4b5563;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 1rem;
}

.featured-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: space-between;
  align-items: stretch;
}

/* En pantallas grandes, distribuir uniformemente */
@media (min-width: 768px) {
  .featured-grid {
    justify-content: space-around;
  }
  
  .featured-grid .product-card-ecom {
    flex: 1 1 auto;
    min-width: 160px;
    max-width: 200px;
  }
}

/* En pantallas pequeñas, permitir scroll horizontal si es necesario */
@media (max-width: 767px) {
  .featured-grid {
    flex-wrap: nowrap;
    overflow-x: auto;
    justify-content: flex-start;
    scrollbar-width: thin;
    scrollbar-color: var(--theme-primary, #2563eb) transparent;
  }
  
  .featured-grid::-webkit-scrollbar {
    height: 6px;
  }
  
  .featured-grid::-webkit-scrollbar-track {
    background: transparent;
  }
  
  .featured-grid::-webkit-scrollbar-thumb {
    background: var(--theme-primary, #2563eb);
    border-radius: 3px;
  }
  
  .featured-grid .product-card-ecom {
    flex: 0 0 auto;
    min-width: 180px;
    max-width: 180px;
  }
}

.product-card-ecom {
  background: var(--theme-surface, #ffffff);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid var(--theme-border, #e2e8f0);
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
}

.product-card-ecom:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  border-color: var(--theme-primary, #2563eb);
}

.product-card-featured {
  padding: 0.5rem;
  gap: 0.5rem;
}

.product-name-featured {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  text-align: center;
  padding: 0.25rem 0;
  line-height: 1.2;
  max-height: 2.4em;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.product-footer-featured {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0.5rem;
  margin-top: auto;
}

.product-image-ecom {
  width: 100%;
  padding-top: 65%;
  position: relative;
  background: var(--theme-background, #f8fafc);
  border-radius: 8px 8px 0 0;
  overflow: hidden;
}

.product-image-ecom img,
.product-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.product-image-ecom img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.product-placeholder {
  font-size: 2rem;
}

.product-body {
  padding: 0.6rem 0.75rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.product-name-ecom {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.3;
  max-height: 2.6em;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  word-break: break-word;
}

.product-category {
  margin: 0;
  font-size: 0.75rem;
  color: var(--theme-text-secondary, #64748b);
}

.product-footer-ecom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.25rem;
}

.product-price-ecom {
  font-weight: 700;
  color: var(--theme-primary, #2563eb);
  font-size: 1.1rem;
}

.add-btn-ecom {
  border-radius: 8px;
  border: none;
  background: var(--theme-primary, #2563eb);
  color: var(--theme-surface, #ffffff);
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.5rem 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.add-btn-ecom:hover {
  background: var(--theme-secondary, #3b82f6);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.catalog-layout {
  display: flex;
  gap: 1.25rem;
  align-items: flex-start;
  position: relative;
  min-height: 600px;
  max-height: 700px;
}

.categories-sidebar {
  flex: 0 0 240px;
  min-width: 240px;
  align-self: flex-start;
  max-height: 600px;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 0.5rem;
}

.catalog-products {
  flex: 1;
  min-width: 0;
  min-height: 180px;
  width: 100%;
  max-height: 600px;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 0.5rem;
}

.categories-sidebar {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-self: start;
}

.search-bar-categories {
  width: 100%;
  padding-bottom: 0.5rem;
}

.category-pill {
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  padding: 0.3rem 0.7rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
  font-size: 0.85rem;
}

.category-pill.active {
  background: var(--theme-primary, #2563eb);
  border-color: var(--theme-primary, #2563eb);
  color: var(--theme-surface, #ffffff);
  font-weight: 600;
}

.category-pill:hover {
  background: var(--theme-accent, #60a5fa);
  border-color: var(--theme-accent, #60a5fa);
  color: var(--theme-surface, #ffffff);
}

.category-emoji {
  font-size: 1.1rem;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 1.5rem 0.5rem;
  color: #6b7280;
}

.spinner {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 3px solid #e5e7eb;
  border-top-color: #dc2626;
  margin: 0 auto 0.75rem;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.contact-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.contact-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.whatsapp-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  border-radius: 999px;
  padding: 0.45rem 0.9rem;
  background: #16a34a;
  color: white;
  text-decoration: none;
  font-size: 0.9rem;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal-content {
  background: var(--theme-surface, #ffffff);
  border-radius: 16px;
  padding: 2rem;
  max-width: 600px;
  width: 90%;
  max-height: 85vh;
  overflow-y: auto;
  box-sizing: border-box;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  position: relative;
}

.modal-title {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 1rem 0;
  color: var(--theme-text, #1a1a1a);
}

.modal-subtitle {
  font-size: 1.1rem;
  color: var(--theme-text-secondary, #666666);
  margin: 0 0 1rem 0;
}

.modal-description {
  font-size: 1rem;
  line-height: 1.6;
  color: var(--theme-text-secondary, #666666);
  margin: 0 0 1.5rem 0;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 1.5rem;
}

.modal-close {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 1.1rem;
}

.product-modal {
  max-width: 600px;
}

.product-modal-body {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 1.2fr);
  gap: 0.75rem;
  align-items: start;
}

.product-modal-image-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.product-modal-image {
  border-radius: 14px;
  overflow: hidden;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 50%, #fcd34d 100%);
  width: 100%;
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  perspective: 1000px;
}

.product-modal-image.has-image {
  background: white;
}

.product-modal-img-3d {
  max-width: 80%;
  max-height: 80%;
  object-fit: contain;
  animation: rotate3d-ecommerce 20s infinite linear;
  transform-style: preserve-3d;
  filter: drop-shadow(0 20px 40px rgba(0, 0, 0, 0.3));
  mix-blend-mode: normal;
}

.product-modal-emoji {
  font-size: 4rem;
  animation: rotate3d-ecommerce 20s infinite linear;
}

@keyframes rotate3d-ecommerce {
  0% {
    transform: rotateY(0deg) rotateX(5deg);
  }
  25% {
    transform: rotateY(90deg) rotateX(0deg);
  }
  50% {
    transform: rotateY(180deg) rotateX(-5deg);
  }
  75% {
    transform: rotateY(270deg) rotateX(0deg);
  }
  100% {
    transform: rotateY(360deg) rotateX(5deg);
  }
}

.product-modal-price-overlay {
  position: absolute;
  bottom: 0.75rem;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.75);
  color: #fff;
  padding: 0.5rem 1.25rem;
  border-radius: 999px;
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
  margin: 0;
  z-index: 5;
}

.product-modal-info {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  height: 300px;
  max-height: 300px;
  overflow-y: auto;
}

.product-modal-info h3 {
  margin-top: 0;
  margin-bottom: 0;
  font-size: 1.1rem;
  line-height: 1.2;
}

.product-category {
  margin: 0;
  font-size: 0.85rem;
  color: #6b7280;
}

.product-description-scroll {
  max-height: 80px;
  overflow-y: auto;
  margin: 0;
  padding: 0.4rem;
  background: #f9fafb;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.product-description {
  margin: 0;
  color: #4b5563;
  line-height: 1.4;
  font-size: 0.85rem;
  white-space: pre-wrap;
}

.product-pdf-link {
  margin: 0.25rem 0;
}

.pdf-download-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.8rem;
  background: #dc2626;
  color: white;
  text-decoration: none;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  transition: background 0.2s;
}

.pdf-download-btn:hover {
  background: #b91c1c;
}

.product-modal-actions {
  margin-top: auto;
  padding-top: 0.5rem;
  position: sticky;
  bottom: 0;
  background: white;
  z-index: 10;
}

.product-modal-actions .full-width {
  width: 100%;
}

.product-modal-info h3 {
  margin-top: 0;
}

.product-modal-price {
  font-size: 1.2rem;
  font-weight: 700;
  color: #b91c1c;
}

.cart-modal {
  max-width: 520px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.cart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #f1f5f9;
}

.cart-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
}

.empty-cart {
  text-align: center;
  padding: 3rem 1rem;
}

.empty-cart-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-cart p {
  color: #64748b;
  margin-bottom: 1.5rem;
  font-size: 1rem;
}

.cart-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.cart-items-scroll {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 1rem;
  padding-right: 0.5rem;
  max-height: 400px;
}

.cart-item-card {
  background: #f8fafc;
  border-radius: 12px;
  padding: 1rem;
  margin-bottom: 0.75rem;
  border: 1px solid #e2e8f0;
  transition: all 0.2s;
}

.cart-item-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.cart-item-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}

.cart-item-details {
  flex: 1;
}

.cart-item-name {
  font-weight: 600;
  font-size: 1rem;
  margin: 0 0 0.25rem 0;
  color: #1e293b;
}

.cart-item-unit-price {
  font-size: 0.85rem;
  color: #64748b;
  margin: 0;
}

.cart-item-total {
  font-size: 1.1rem;
  color: #1e293b;
}

.cart-item-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: flex-end;
}

.cart-btn-qty {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  background: white;
  cursor: pointer;
  font-size: 1.1rem;
  font-weight: 600;
  color: #475569;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cart-btn-qty:hover:not(:disabled) {
  background: #f1f5f9;
  border-color: #94a3b8;
}

.cart-btn-qty:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.cart-qty-display {
  min-width: 40px;
  text-align: center;
  font-weight: 600;
  font-size: 1rem;
  color: #1e293b;
}

.cart-btn-remove {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  padding: 0.25rem;
  margin-left: 0.5rem;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.cart-btn-remove:hover {
  opacity: 1;
}

.cart-summary {
  border-top: 2px solid #f1f5f9;
  padding-top: 1rem;
  margin-top: auto;
}

.cart-summary-line {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  color: #64748b;
  font-size: 0.9rem;
}

.cart-total-line {
  display: flex;
  justify-content: space-between;
  margin: 0.75rem 0;
  padding-top: 0.75rem;
  border-top: 1px solid #e2e8f0;
  font-size: 1.1rem;
}

.cart-total-line strong {
  font-size: 1.3rem;
  color: #1e293b;
}

.cart-checkout-btn {
  margin-bottom: 0.75rem;
  padding: 0.875rem;
  font-size: 1rem;
  font-weight: 600;
}

.secondary-btn {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 0.75rem 1rem;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  transition: all 0.2s;
}

.secondary-btn:hover {
  background: #e2e8f0;
  border-color: #94a3b8;
}

.full-width {
  width: 100%;
}

.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
  width: 100%;
  box-sizing: border-box;
}

.contact-modal {
  max-width: 480px;
}

.cedula-modal,
.datos-completos-modal,
.direccion-modal,
.forma-pago-modal,
.pasarela-modal,
.tarjeta-modal {
  max-width: 500px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.payment-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin: 1rem 0;
}

.payment-option-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.5rem;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 1rem;
}

.payment-option-btn:hover {
  border-color: var(--theme-primary, #2563eb);
  background: #f0f9ff;
}

.payment-option-btn.active {
  border-color: var(--theme-primary, #2563eb);
  background: var(--theme-primary, #2563eb);
  color: white;
}

.payment-icon {
  font-size: 2rem;
}

.payment-label {
  font-weight: 600;
}

.cedula-form,
.direccion-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--theme-text, #1a1a1a);
}

.form-input {
  padding: 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 1rem;
  transition: all 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: var(--theme-primary, #2563eb);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-textarea {
  resize: vertical;
  min-height: 100px;
  font-family: inherit;
}

.button-group {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.button-group button {
  flex: 1;
}

.pasarelas-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}

.pasarela-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.pasarela-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.pasarela-codigo {
  color: #64748b;
  font-size: 0.9rem;
}

.badge-active {
  background: #10b981;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
}

.badge-inactive {
  background: #ef4444;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
}

.form-help {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.85rem;
  color: #64748b;
}

.loading-text,
.info-text {
  padding: 1rem;
  text-align: center;
  color: #64748b;
}

.ecommerce-footer {
  background: var(--theme-primary, #2563eb);
  color: var(--theme-surface, #ffffff);
  padding: 3rem 2rem;
  margin-top: 4rem;
  width: 100%;
  box-sizing: border-box;
}

.footer-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
}

.footer-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.footer-section h4 {
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--theme-surface, #ffffff);
}

.footer-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: rgba(255, 255, 255, 0.9);
  text-decoration: none;
  font-size: 0.95rem;
  padding: 0.5rem 0;
  transition: all 0.2s;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
}

.footer-link:hover {
  color: var(--theme-surface, #ffffff);
  transform: translateX(4px);
}

.footer-link-icon {
  font-size: 1.1rem;
}

.load-more-hint {
  text-align: center;
  padding: 1rem;
  color: #64748b;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}

.loading-more {
  text-align: center;
  padding: 1.5rem 0.5rem;
  color: #6b7280;
}

.load-more-up {
  text-align: center;
  padding: 1rem 0.5rem;
}

.load-more-btn {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.9rem;
  color: #4b5563;
  transition: background 0.2s;
}

.load-more-btn:hover {
  background: #e5e7eb;
}

.loading-message {
  padding: 0.75rem;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  color: #0369a1;
  text-align: center;
  margin: 0.5rem 0;
}

.info-message {
  padding: 0.75rem;
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 8px;
  color: #166534;
  text-align: center;
  margin: 0.5rem 0;
}

.radio-group {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: 500;
}

.radio-label input[type="radio"] {
  cursor: pointer;
  width: 18px;
  height: 18px;
}

/* Toast Notification */
.toast-notification {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  z-index: 3000;
  min-width: 280px;
  max-width: 400px;
}

.toast-content {
  background: #1e293b;
  color: white;
  padding: 1rem 1.25rem;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  animation: slideInRight 0.3s ease-out;
}

.toast-icon {
  background: #10b981;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  font-weight: 700;
  flex-shrink: 0;
}

.toast-message {
  flex: 1;
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.4;
}

/* Toast Animations */
.toast-enter-active {
  animation: slideInRight 0.3s ease-out;
}

.toast-leave-active {
  animation: slideOutRight 0.3s ease-in;
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slideOutRight {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(100%);
    opacity: 0;
  }
}

/* Admin Styles */
.admin-button {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.9rem;
  color: #475569;
  margin-right: 0.75rem;
  transition: all 0.2s;
}

.admin-button:hover {
  background: #e2e8f0;
  border-color: #94a3b8;
}

.admin-button.active {
  background: #dc2626;
  color: white;
  border-color: #dc2626;
}

.admin-login-modal {
  max-width: 400px;
}

.admin-login-form {
  margin-top: 1rem;
}

.error-message {
  color: #dc2626;
  font-size: 0.9rem;
  margin: 0.5rem 0;
  padding: 0.5rem;
  background: #fee2e2;
  border-radius: 6px;
}

.admin-panel-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
  padding: 1rem;
}

.admin-panel {
  background: white;
  border-radius: 16px;
  width: 100%;
  max-width: 1200px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.admin-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 2px solid #f1f5f9;
}

.admin-panel-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
}

.admin-close-btn {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #64748b;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  transition: all 0.2s;
}

.admin-close-btn:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.admin-tabs-wrapper {
  border-bottom: 2px solid #f1f5f9;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 0 1rem;
  background: white;
  position: sticky;
  top: 0;
  z-index: 10;
}

.admin-tabs {
  display: flex;
  gap: 0;
  padding: 0 1.5rem;
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 transparent;
}

.admin-tabs::-webkit-scrollbar {
  height: 6px;
}

.admin-tabs::-webkit-scrollbar-track {
  background: transparent;
}

.admin-tabs::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.admin-tabs::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.admin-tab {
  background: transparent;
  border: none;
  padding: 1rem 2rem;
  cursor: pointer;
  font-size: 1rem;
  color: #64748b;
  border-bottom: 3px solid transparent;
  transition: all 0.2s;
  white-space: nowrap;
  position: relative;
  flex-shrink: 0;
  min-width: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.admin-tab-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
}

.admin-tab-label {
  font-weight: 500;
}

.admin-tab:hover {
  color: #1e293b;
  background: #f8fafc;
}

.admin-tab.active {
  color: #dc2626;
  background: #fef2f2;
  border-bottom-color: #dc2626;
  font-weight: 600;
  box-shadow: 0 -2px 8px rgba(220, 38, 38, 0.1);
}

.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.admin-tab-content h3 {
  margin: 0 0 1.5rem 0;
  font-size: 1.25rem;
  font-weight: 700;
}

.admin-section {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #f1f5f9;
}

.admin-section:last-child {
  border-bottom: none;
}

.admin-help-text {
  color: #64748b;
  font-size: 0.875rem;
  margin-bottom: 1rem;
  font-style: italic;
}

.admin-section h4 {
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #475569;
  font-size: 0.9rem;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 0.95rem;
  transition: all 0.2s;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #dc2626;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
}

.color-input {
  width: 60px;
  height: 40px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  cursor: pointer;
  margin-right: 0.5rem;
}

.button-group {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}

.admin-actions {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 2px solid #f1f5f9;
}

.admin-search {
  margin-bottom: 1.5rem;
}

.admin-products-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 500px;
  overflow-y: auto;
}

.admin-product-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.admin-product-info h4 {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
  font-weight: 600;
}

.admin-product-code {
  margin: 0;
  font-size: 0.85rem;
  color: #64748b;
}

.edit-btn {
  background: #dc2626;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}

.edit-btn:hover {
  background: #b91c1c;
}

.danger-btn {
  background: #ef4444;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.danger-btn:hover {
  background: #dc2626;
}

.product-editor-overlay {
  z-index: 4000 !important;
}

.product-editor-modal {
  max-width: 500px;
  max-height: 85vh;
  overflow-y: auto;
  z-index: 4001;
}

.product-editor-modal .admin-section {
  margin-bottom: 1rem;
  padding-bottom: 1rem;
}

.product-editor-modal h3 {
  font-size: 1.1rem;
  margin-bottom: 1rem;
}

.product-editor-modal h4 {
  font-size: 0.95rem;
  margin-bottom: 0.5rem;
}

.product-editor-modal .form-group {
  margin-bottom: 0.75rem;
}

.product-editor-modal .form-input {
  padding: 0.5rem;
  font-size: 0.9rem;
}

.product-editor-modal .product-image-preview {
  max-height: 200px;
}

.footer-section-item {
  padding: 1.5rem;
  background: #f8fafc;
  border-radius: 12px;
  margin-bottom: 1.5rem;
  border: 2px solid #e2e8f0;
}

.footer-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #e2e8f0;
}

.footer-section-header h5 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
}

.danger-btn.small,
.secondary-btn.small {
  padding: 0.4rem 0.75rem;
  font-size: 0.85rem;
}

.product-image-upload {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.product-image-preview {
  max-width: 100%;
  max-height: 300px;
  border-radius: 8px;
  object-fit: contain;
}

.product-image-placeholder {
  width: 100%;
  height: 200px;
  background: #f1f5f9;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
}

.file-input {
  display: none;
}

.pdf-link {
  margin-top: 0.5rem;
  display: block;
}

.pdf-link a {
  color: #dc2626;
  text-decoration: none;
  font-size: 0.9rem;
}

.pdf-link a:hover {
  text-decoration: underline;
}

.footer-link-item {
  padding: 1rem;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 1rem;
  border: 1px solid #e2e8f0;
}

/* Loading Page Modal */
.loading-page-overlay {
  position: fixed;
  inset: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.loading-page-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  text-align: center;
}

.loading-logo {
  max-width: 200px;
  max-height: 100px;
  object-fit: contain;
  animation: fadeIn 0.5s ease-in;
}

.loading-logo-placeholder {
  font-size: 2rem;
  font-weight: 700;
  color: #1e293b;
  animation: fadeIn 0.5s ease-in;
}

.loading-spinner-large {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  border: 4px solid #e5e7eb;
  border-top-color: #dc2626;
  animation: spin 0.8s linear infinite;
}

.loading-text {
  font-size: 1.1rem;
  color: #64748b;
  font-weight: 500;
  animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 900px) {
  .ecommerce-header {
    grid-template-columns: 1fr;
  }

  .header-right {
    justify-content: flex-start;
  }

  .hero-section {
    grid-template-columns: 1fr;
  }

  .catalog-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .ecommerce-container {
    padding: 1rem 0.75rem 1.5rem;
  }

  .product-modal-body {
    grid-template-columns: 1fr;
  }
}
</style>


