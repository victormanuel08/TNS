<template>
  <footer class="ecommerce-footer">
    <div class="container">
      <div class="footer-content">
        <div class="footer-section">
          <div class="logo-area">
            <div class="footer-logo">
              <img v-if="company?.imageUrl" :src="company.imageUrl" :alt="companyName" />
              <span v-else>{{ companyName }}</span>
            </div>
            <p class="footer-description">
              Tu tienda en línea de confianza. Encuentra los mejores productos al mejor precio.
            </p>
          </div>
        </div>

        <div class="footer-section">
          <h4>Enlaces Rápidos</h4>
          <ul class="footer-links">
            <li><a href="#">Inicio</a></li>
            <li><a href="#">Productos</a></li>
            <li><a href="#">Categorías</a></li>
            <li><a href="#">Ofertas</a></li>
            <li><a href="#">Contacto</a></li>
          </ul>
        </div>

        <div class="footer-section">
          <h4>Categorías</h4>
          <ul class="footer-links">
            <li><a href="#">Electrónicos</a></li>
            <li><a href="#">Hogar</a></li>
            <li><a href="#">Moda</a></li>
            <li><a href="#">Deportes</a></li>
            <li><a href="#">Juguetes</a></li>
          </ul>
        </div>

        <div class="footer-section">
          <h4>Contacto</h4>
          <div class="contact-info">
            <div class="contact-item">
              <span class="contact-icon">📧</span>
              <span>info@{{ company?.subdomain }}.com</span>
            </div>
            <div class="contact-item">
              <span class="contact-icon">📞</span>
              <span>+1 234 567 890</span>
            </div>
            <div class="contact-item">
              <span class="contact-icon">📍</span>
              <span>Tu Ciudad, País</span>
            </div>
          </div>
          
          <div class="social-links">
            <a href="#" class="social-link">📘</a>
            <a href="#" class="social-link">📷</a>
            <a href="#" class="social-link">🐦</a>
            <a href="#" class="social-link">💼</a>
          </div>
        </div>
      </div>

      <div class="footer-bottom">
        <div class="footer-bottom-content">
          <p>&copy; {{ currentYear }} {{ companyName }}. Todos los derechos reservados.</p>
          <div class="footer-bottom-links">
            <a href="#">Términos de servicio</a>
            <a href="#">Política de privacidad</a>
            <a href="#">Cookies</a>
          </div>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
const { company, companyName } = useCompany()
const currentYear = new Date().getFullYear()
</script>

<style scoped>
.ecommerce-footer {
  background-color: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  color: var(--text-primary);
  margin-top: auto;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.footer-content {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1.5fr;
  gap: 2rem;
  padding: 3rem 0 2rem;
}

.footer-section h4 {
  color: var(--text-primary);
  margin-bottom: 1rem;
  font-size: 1.1rem;
  font-weight: 600;
}

.footer-logo {
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--primary-color);
  margin-bottom: 1rem;
}

.footer-logo img {
  height: 40px;
  width: auto;
}

.footer-description {
  color: var(--text-secondary);
  line-height: 1.6;
  max-width: 300px;
}

.footer-links {
  list-style: none;
}

.footer-links li {
  margin-bottom: 0.5rem;
}

.footer-links a {
  color: var(--text-secondary);
  text-decoration: none;
  transition: color 0.2s;
}

.footer-links a:hover {
  color: var(--primary-color);
}

.contact-info {
  margin-bottom: 1.5rem;
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  color: var(--text-secondary);
}

.contact-icon {
  font-size: 1.1rem;
}

.social-links {
  display: flex;
  gap: 0.75rem;
}

.social-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: var(--primary-color);
  color: white;
  border-radius: var(--border-radius);
  text-decoration: none;
  font-size: 1.2rem;
  transition: background-color 0.2s;
}

.social-link:hover {
  background: var(--secondary-color);
}

.footer-bottom {
  border-top: 1px solid var(--border-color);
  padding: 1.5rem 0;
}

.footer-bottom-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.footer-bottom-links {
  display: flex;
  gap: 1.5rem;
}

.footer-bottom-links a {
  color: var(--text-secondary);
  text-decoration: none;
  transition: color 0.2s;
}

.footer-bottom-links a:hover {
  color: var(--primary-color);
}

@media (max-width: 768px) {
  .footer-content {
    grid-template-columns: 1fr;
    gap: 2rem;
    text-align: center;
  }

  .footer-description {
    max-width: none;
  }

  .footer-bottom-content {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }

  .footer-bottom-links {
    flex-direction: column;
    gap: 0.5rem;
  }
}

@media (max-width: 480px) {
  .footer-content {
    padding: 2rem 0 1rem;
  }

  .social-links {
    justify-content: center;
  }
}
</style>