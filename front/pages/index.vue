<template>
  <div class="public-home">
    <!-- Header -->
    <header class="header">
      <nav class="nav">
        <div class="nav-brand">
          <div class="logo-container">
            <div class="logo-icon">💻</div>
            <h1>EDDESO</h1>
          </div>
        </div>
        <div class="nav-links">
          <a href="#inicio" class="nav-link">Inicio</a>
          <a href="#servicios" class="nav-link">Servicios</a>
          <a href="#acerca" class="nav-link">Acerca de</a>
          <NuxtLink to="/admin/login" class="btn-login">Iniciar Sesión</NuxtLink>
        </div>
        <button class="mobile-menu-btn" @click="toggleMobileMenu">
          <span></span>
          <span></span>
          <span></span>
        </button>
      </nav>
      <div v-if="showMobileMenu" class="mobile-menu">
        <a href="#inicio" class="mobile-link" @click="closeMobileMenu">Inicio</a>
        <a href="#servicios" class="mobile-link" @click="closeMobileMenu">Servicios</a>
        <a href="#acerca" class="mobile-link" @click="closeMobileMenu">Acerca de</a>
        <NuxtLink to="/admin/login" class="mobile-link" @click="closeMobileMenu">Iniciar Sesión</NuxtLink>
      </div>
    </header>

    <!-- Hero Section -->
    <section id="inicio" class="hero">
      <div class="hero-background">
        <div class="gradient-orb orb-1"></div>
        <div class="gradient-orb orb-2"></div>
        <div class="gradient-orb orb-3"></div>
      </div>
      <div class="hero-content">
        <div class="hero-text">
          <div class="hero-badge">
            <span class="badge-icon">✨</span>
            <span>Diseño, Desarrollo Software Inteligente</span>
          </div>
          <h1 class="hero-title">
            Soluciones Digitales
            <span class="gradient-text">Inteligentes</span>
          </h1>
          <p class="hero-subtitle">
            Transformamos ideas en software de alto rendimiento. 
            Diseño innovador, desarrollo ágil y soluciones tecnológicas a medida.
          </p>
          <div class="hero-actions">
            <NuxtLink to="/admin/login" class="btn-primary">
              <span>Comenzar Ahora</span>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M7.5 15L12.5 10L7.5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </NuxtLink>
            <a href="#servicios" class="btn-secondary">
              <span>Conocer más</span>
            </a>
          </div>
          <div class="hero-stats">
            <div class="stat-item">
              <div class="stat-number">100%</div>
              <div class="stat-label">Automatizado</div>
            </div>
            <div class="stat-item">
              <div class="stat-number">24/7</div>
              <div class="stat-label">Disponible</div>
            </div>
            <div class="stat-item">
              <div class="stat-number">IA</div>
              <div class="stat-label">Asistida</div>
            </div>
          </div>
        </div>
        <div class="hero-visual">
          <div class="feature-card card-1">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <div class="card-content">
              <h3>Diseño</h3>
              <p>Interfaces modernas</p>
            </div>
          </div>
          <div class="feature-card card-2">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                <line x1="8" y1="21" x2="16" y2="21"/>
                <line x1="12" y1="17" x2="12" y2="21"/>
              </svg>
            </div>
            <div class="card-content">
              <h3>Desarrollo</h3>
              <p>Software a medida</p>
            </div>
          </div>
          <div class="feature-card card-3">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>
                <circle cx="12" cy="12" r="2"/>
              </svg>
            </div>
            <div class="card-content">
              <h3>Inteligencia</h3>
              <p>IA integrada</p>
            </div>
          </div>
          <div class="feature-card card-4">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
              </svg>
            </div>
            <div class="card-content">
              <h3>Innovación</h3>
              <p>Tecnología avanzada</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Servicios Section -->
    <section id="servicios" class="services">
      <div class="container">
        <div class="section-header">
          <div class="section-badge">Nuestros Servicios</div>
          <h2 class="section-title">Soluciones Completas para tu Negocio</h2>
          <p class="section-description">
            Herramientas potentes diseñadas para impulsar tu negocio con tecnología de vanguardia
          </p>
        </div>
        <div class="services-grid">
          <div class="service-card">
            <div class="service-card-header">
              <div class="service-icon-wrapper">
                <div class="service-icon">🎨</div>
              </div>
              <div class="service-number">01</div>
            </div>
            <h3>Diseño de Software</h3>
            <p>Interfaces intuitivas y experiencias de usuario excepcionales. Diseñamos soluciones que tus usuarios amarán usar.</p>
            <div class="service-features">
              <span class="feature-tag">UX/UI</span>
              <span class="feature-tag">Responsive</span>
              <span class="feature-tag">Moderno</span>
            </div>
          </div>
          <div class="service-card">
            <div class="service-card-header">
              <div class="service-icon-wrapper">
                <div class="service-icon">💻</div>
              </div>
              <div class="service-number">02</div>
            </div>
            <h3>Desarrollo de Software</h3>
            <p>Desarrollo ágil con las últimas tecnologías. Aplicaciones web, móviles y de escritorio a medida para tu negocio.</p>
            <div class="service-features">
              <span class="feature-tag">Full Stack</span>
              <span class="feature-tag">Escalable</span>
              <span class="feature-tag">Rápido</span>
            </div>
          </div>
          <div class="service-card">
            <div class="service-card-header">
              <div class="service-icon-wrapper">
                <div class="service-icon">🤖</div>
              </div>
              <div class="service-number">03</div>
            </div>
            <h3>Software Inteligente</h3>
            <p>Integración de Inteligencia Artificial y automatización para optimizar procesos y tomar decisiones inteligentes.</p>
            <div class="service-features">
              <span class="feature-tag">IA/ML</span>
              <span class="feature-tag">Automatización</span>
              <span class="feature-tag">Inteligente</span>
            </div>
          </div>
          <div class="service-card">
            <div class="service-card-header">
              <div class="service-icon-wrapper">
                <div class="service-icon">⚡</div>
              </div>
              <div class="service-number">04</div>
            </div>
            <h3>Consultoría Tecnológica</h3>
            <p>Asesoría especializada para transformar tu negocio digitalmente. Estrategias tecnológicas que generan resultados.</p>
            <div class="service-features">
              <span class="feature-tag">Estrategia</span>
              <span class="feature-tag">Optimización</span>
              <span class="feature-tag">Resultados</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Acerca de Section -->
    <section id="acerca" class="about">
      <div class="container">
        <div class="about-content">
          <div class="about-text">
            <div class="section-badge">Acerca de Nosotros</div>
            <h2 class="section-title">Tu Socio en Diseño y Desarrollo de Software</h2>
            <p class="about-description">
              EDDESO es una empresa especializada en diseño y desarrollo de software inteligente. 
              Combinamos creatividad, tecnología de vanguardia e inteligencia artificial para 
              crear soluciones digitales que transforman negocios.
            </p>
            <p class="about-description">
              Nos adaptamos a diferentes tipos de proyectos: desde aplicaciones web y móviles 
              hasta sistemas empresariales complejos, ofreciendo soluciones personalizadas 
              diseñadas para cada necesidad específica.
            </p>
            <div class="about-features">
              <div class="about-feature">
                <div class="feature-check">✓</div>
                <span>Diseño de interfaces modernas y funcionales</span>
              </div>
              <div class="about-feature">
                <div class="feature-check">✓</div>
                <span>Desarrollo con tecnologías de última generación</span>
              </div>
              <div class="about-feature">
                <div class="feature-check">✓</div>
                <span>Integración de Inteligencia Artificial</span>
              </div>
              <div class="about-feature">
                <div class="feature-check">✓</div>
                <span>Soporte y mantenimiento continuo</span>
              </div>
            </div>
          </div>
          <div class="about-visual">
            <div class="visual-card">
              <div class="visual-icon">🚀</div>
              <h3>Innovación</h3>
            </div>
            <div class="visual-card">
              <div class="visual-icon">🔒</div>
              <h3>Seguridad</h3>
            </div>
            <div class="visual-card">
              <div class="visual-icon">⚡</div>
              <h3>Rapidez</h3>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="container">
        <div class="footer-content">
          <div class="footer-brand">
            <h3>EDDESO</h3>
            <p>Diseño, Desarrollo Software Inteligente</p>
          </div>
          <div class="footer-links">
            <div class="footer-column">
              <h4>Plataforma</h4>
              <a href="#inicio">Inicio</a>
              <a href="#servicios">Servicios</a>
              <a href="#acerca">Acerca de</a>
            </div>
            <div class="footer-column">
              <h4>Legal</h4>
              <a href="#">Términos de Servicio</a>
              <a href="#">Política de Privacidad</a>
            </div>
          </div>
        </div>
        <div class="footer-bottom">
          <p>&copy; 2025 EDDESO. Todos los derechos reservados.</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

definePageMeta({
  layout: false,
  middleware: 'subdomain' // Usar el middleware para manejar subdominios
})

const showMobileMenu = ref(false)

const toggleMobileMenu = () => {
  showMobileMenu.value = !showMobileMenu.value
}

const closeMobileMenu = () => {
  showMobileMenu.value = false
}

// Smooth scroll para los enlaces
onMounted(() => {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault()
      const target = document.querySelector(this.getAttribute('href') || '')
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        })
        closeMobileMenu()
      }
    })
  })
})
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.public-home {
  min-height: 100vh;
  background: #ffffff;
  overflow-x: hidden;
}

/* Header */
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  z-index: 1000;
  transition: all 0.3s ease;
}

.nav {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.25rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-brand {
  display: flex;
  align-items: center;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.logo-icon {
  font-size: 2rem;
  color: #4b5563;
}

.nav-brand h1 {
  font-size: 1.75rem;
  font-weight: 800;
  color: #1f2937;
  margin: 0;
}

.nav-links {
  display: flex;
  gap: 2.5rem;
  align-items: center;
}

.nav-link {
  text-decoration: none;
  color: #4b5563;
  font-weight: 500;
  font-size: 0.95rem;
  transition: all 0.2s;
  position: relative;
}

.nav-link::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  width: 0;
  height: 2px;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  transition: width 0.3s ease;
}

.nav-link:hover {
  color: #1f2937;
}

.nav-link:hover::after {
  width: 100%;
}

.btn-login {
  background: #1f2937;
  color: white;
  padding: 0.625rem 1.5rem;
  border-radius: 0.5rem;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.btn-login:hover {
  background: #374151;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.mobile-menu-btn {
  display: none;
  flex-direction: column;
  gap: 4px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
}

.mobile-menu-btn span {
  width: 24px;
  height: 2px;
  background: #4b5563;
  border-radius: 2px;
  transition: all 0.3s;
}

.mobile-menu {
  display: none;
  flex-direction: column;
  gap: 1rem;
  padding: 1.5rem 2rem;
  background: white;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.mobile-link {
  text-decoration: none;
  color: #4b5563;
  font-weight: 500;
  padding: 0.5rem 0;
}

/* Hero Section */
.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  padding: 8rem 2rem 4rem;
  max-width: 1400px;
  margin: 0 auto;
  overflow: hidden;
}

.hero-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 0;
  overflow: hidden;
}

.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.6;
  animation: float 20s ease-in-out infinite;
}

.orb-1 {
  width: 500px;
  height: 500px;
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  top: -200px;
  left: -200px;
  animation-delay: 0s;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  bottom: -150px;
  right: -150px;
  animation-delay: 7s;
}

.orb-3 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  top: 50%;
  right: 10%;
  animation-delay: 14s;
}

.hero-content {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4rem;
  align-items: center;
  width: 100%;
}

.hero-text {
  animation: fadeInUp 0.8s ease-out;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(107, 114, 128, 0.08);
  border: 1px solid rgba(107, 114, 128, 0.15);
  padding: 0.5rem 1rem;
  border-radius: 2rem;
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 600;
  margin-bottom: 1.5rem;
}

.badge-icon {
  font-size: 1rem;
}

.hero-title {
  font-size: 4rem;
  font-weight: 900;
  color: #1f2937;
  margin-bottom: 1.5rem;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.gradient-text {
  background: linear-gradient(135deg, #4b5563 0%, #6b7280 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 1.25rem;
  color: #6b7280;
  margin-bottom: 2.5rem;
  line-height: 1.7;
  max-width: 540px;
}

.hero-actions {
  display: flex;
  gap: 1rem;
  margin-bottom: 3rem;
  flex-wrap: wrap;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: #1f2937;
  color: white;
  padding: 1rem 2rem;
  border-radius: 0.75rem;
  text-decoration: none;
  font-weight: 600;
  font-size: 1rem;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.btn-primary:hover {
  background: #374151;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  background: white;
  color: #4b5563;
  padding: 1rem 2rem;
  border-radius: 0.75rem;
  text-decoration: none;
  font-weight: 600;
  font-size: 1rem;
  border: 2px solid #e5e7eb;
  transition: all 0.3s ease;
}

.btn-secondary:hover {
  background: #f8fafc;
  transform: translateY(-2px);
}

.hero-stats {
  display: flex;
  gap: 3rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.stat-number {
  font-size: 2rem;
  font-weight: 800;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

.hero-visual {
  position: relative;
  height: 500px;
  animation: fadeInRight 0.8s ease-out 0.2s both;
}

.feature-card {
  position: absolute;
  background: white;
  padding: 1.5rem;
  border-radius: 1.25rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: all 0.3s ease;
  animation: float 6s ease-in-out infinite;
}

.feature-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.card-1 {
  top: 0;
  left: 0;
  animation-delay: 0s;
}

.card-2 {
  top: 120px;
  right: 0;
  animation-delay: 1.5s;
}

.card-3 {
  bottom: 120px;
  left: 0;
  animation-delay: 3s;
}

.card-4 {
  bottom: 0;
  right: 20%;
  animation-delay: 4.5s;
}

.card-icon {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  border-radius: 1rem;
  flex-shrink: 0;
  color: #4b5563;
}

.card-icon svg {
  width: 28px;
  height: 28px;
}

.card-content h3 {
  font-size: 1.125rem;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 0.25rem;
}

.card-content p {
  font-size: 0.875rem;
  color: #6b7280;
}

/* Services Section */
.services {
  padding: 8rem 0;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  position: relative;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
}

.section-header {
  text-align: center;
  margin-bottom: 4rem;
}

.section-badge {
  display: inline-block;
  background: rgba(107, 114, 128, 0.08);
  color: #6b7280;
  padding: 0.5rem 1.25rem;
  border-radius: 2rem;
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 1rem;
}

.section-title {
  font-size: 3rem;
  font-weight: 800;
  color: #1f2937;
  margin-bottom: 1rem;
  line-height: 1.2;
}

.section-description {
  font-size: 1.125rem;
  color: #6b7280;
  max-width: 600px;
  margin: 0 auto;
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}

.service-card {
  background: white;
  padding: 2.5rem;
  border-radius: 1.5rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  border: 1px solid rgba(0, 0, 0, 0.05);
  position: relative;
  overflow: hidden;
}

.service-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: #e5e7eb;
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.service-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
}

.service-card:hover::before {
  transform: scaleX(1);
}

.service-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.service-icon-wrapper {
  width: 64px;
  height: 64px;
  background: #f3f4f6;
  border-radius: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4b5563;
}

.service-icon {
  font-size: 1.75rem;
}

.service-number {
  font-size: 3rem;
  font-weight: 900;
  color: rgba(107, 114, 128, 0.1);
  line-height: 1;
}

.service-card h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 1rem;
}

.service-card p {
  color: #6b7280;
  line-height: 1.7;
  margin-bottom: 1.5rem;
}

.service-features {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.feature-tag {
  background: #f3f4f6;
  color: #4b5563;
  padding: 0.375rem 0.875rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
}

/* About Section */
.about {
  padding: 8rem 0;
  background: white;
}

.about-content {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 4rem;
  align-items: center;
}

.about-text {
  animation: fadeInLeft 0.8s ease-out;
}

.about-description {
  font-size: 1.125rem;
  color: #4b5563;
  line-height: 1.8;
  margin-bottom: 1.5rem;
}

.about-features {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 2rem;
}

.about-feature {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.feature-check {
  width: 32px;
  height: 32px;
  background: #1f2937;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
  font-size: 0.875rem;
}

.about-feature span {
  color: #4b5563;
  font-size: 1rem;
}

.about-visual {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  animation: fadeInRight 0.8s ease-out;
}

.visual-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  padding: 2.5rem;
  border-radius: 1.5rem;
  text-align: center;
  color: #1f2937;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.visual-card:nth-child(3) {
  grid-column: 1 / -1;
  background: #f9fafb;
}

.visual-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
  border-color: #d1d5db;
}

.visual-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.visual-card h3 {
  font-size: 1.5rem;
  font-weight: 700;
}

/* Footer */
.footer {
  background: #1f2937;
  color: #9ca3af;
  padding: 4rem 0 2rem;
}

.footer-content {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 4rem;
  margin-bottom: 3rem;
}

.footer-brand h3 {
  font-size: 1.5rem;
  font-weight: 800;
  color: white;
  margin-bottom: 0.5rem;
}

.footer-brand p {
  color: #9ca3af;
  line-height: 1.6;
}

.footer-links {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 2rem;
}

.footer-column h4 {
  color: white;
  font-weight: 700;
  margin-bottom: 1rem;
  font-size: 1rem;
}

.footer-column a {
  display: block;
  color: #9ca3af;
  text-decoration: none;
  margin-bottom: 0.75rem;
  transition: color 0.2s;
}

.footer-column a:hover {
  color: white;
}

.footer-bottom {
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  text-align: center;
}

/* Animations */
@keyframes float {
  0%, 100% { transform: translateY(0) translateX(0); }
  33% { transform: translateY(-20px) translateX(10px); }
  66% { transform: translateY(-10px) translateX(-10px); }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInRight {
  from {
    opacity: 0;
    transform: translateX(30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes fadeInLeft {
  from {
    opacity: 0;
    transform: translateX(-30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* Responsive */
@media (max-width: 1024px) {
  .hero-content {
    grid-template-columns: 1fr;
    gap: 3rem;
  }

  .hero-visual {
    height: 400px;
  }

  .about-content {
    grid-template-columns: 1fr;
  }

  .footer-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .nav-links {
    display: none;
  }

  .mobile-menu-btn {
    display: flex;
  }

  .mobile-menu {
    display: flex;
  }

  .hero {
    padding: 6rem 1.5rem 3rem;
  }

  .hero-title {
    font-size: 2.5rem;
  }

  .hero-subtitle {
    font-size: 1.125rem;
  }

  .hero-stats {
    gap: 2rem;
  }

  .section-title {
    font-size: 2rem;
  }

  .services-grid {
    grid-template-columns: 1fr;
  }

  .about-visual {
    grid-template-columns: 1fr;
  }

  .visual-card:nth-child(3) {
    grid-column: 1;
  }
}
</style>
