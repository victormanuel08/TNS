<template>
  <div class="admin-login">
    <div class="login-background">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
    </div>
    <div class="login-container">
      <div class="login-card">
        <div class="login-header">
          <div class="logo-section">
            <div class="logo-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                <line x1="8" y1="21" x2="16" y2="21"/>
                <line x1="12" y1="17" x2="12" y2="21"/>
              </svg>
            </div>
            <h1>EDDESO</h1>
          </div>
          <p class="subtitle">Panel de Administración</p>
        </div>
        <form @submit.prevent="handleLogin" class="login-form">
          <div class="form-group">
            <label>Usuario</label>
            <input 
              v-model="form.username" 
              type="text" 
              placeholder="Ingresa tu usuario"
              required
              autocomplete="username"
            />
          </div>
          <div class="form-group">
            <label>Contraseña</label>
            <input 
              v-model="form.password" 
              type="password" 
              placeholder="Ingresa tu contraseña"
              required
              autocomplete="current-password"
            />
          </div>
          <button type="submit" :disabled="loading" class="btn-submit">
            <span v-if="loading" class="spinner"></span>
            <span v-else>Iniciar Sesión</span>
          </button>
          <p v-if="error" class="error">{{ error }}</p>
        </form>
        <div class="login-footer">
          <NuxtLink to="/" class="back-link">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor">
              <path d="M10 12L6 8l4-4"/>
            </svg>
            Volver al inicio
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: false
})

const session = useSessionStore()
const form = reactive({
  username: '',
  password: ''
})
const loading = ref(false)
const error = ref<string | null>(null)

const handleLogin = async () => {
  error.value = null
  loading.value = true
  try {
    await session.login({
      username: form.username,
      password: form.password
    })
    // Cerrar el modal de empresas si se abrió (solo para admin login)
    session.closeEmpresaModal()
    // Después del login exitoso, redirigir directamente al dashboard
    await nextTick()
    navigateTo('/admin/dashboard')
  } catch (err: any) {
    error.value = err.message || 'Error al iniciar sesión'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.admin-login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  padding: 2rem;
  position: relative;
  overflow: hidden;
}

.login-background {
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
  opacity: 0.4;
  animation: float 20s ease-in-out infinite;
}

.orb-1 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  top: -150px;
  left: -150px;
  animation-delay: 0s;
}

.orb-2 {
  width: 350px;
  height: 350px;
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  bottom: -100px;
  right: -100px;
  animation-delay: 10s;
}

@keyframes float {
  0%, 100% { transform: translateY(0) translateX(0); }
  33% { transform: translateY(-30px) translateX(20px); }
  66% { transform: translateY(-15px) translateX(-20px); }
}

.login-container {
  width: 100%;
  max-width: 440px;
  position: relative;
  z-index: 1;
}

.login-card {
  background: white;
  border-radius: 1.5rem;
  padding: 3rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e7eb;
}

.login-header {
  text-align: center;
  margin-bottom: 2.5rem;
}

.logo-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.logo-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  border-radius: 0.75rem;
  color: #4b5563;
}

.logo-icon svg {
  width: 28px;
  height: 28px;
}

.login-card h1 {
  font-size: 2rem;
  font-weight: 800;
  color: #1f2937;
  margin: 0;
}

.subtitle {
  text-align: center;
  color: #6b7280;
  font-size: 0.95rem;
  margin: 0;
  font-weight: 500;
}

.login-form {
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #374151;
  font-weight: 600;
  font-size: 0.875rem;
}

.form-group input {
  width: 100%;
  padding: 0.875rem 1rem;
  border: 1.5px solid #e5e7eb;
  border-radius: 0.75rem;
  font-size: 1rem;
  transition: all 0.2s;
  background: #ffffff;
  color: #1f2937;
}

.form-group input:focus {
  outline: none;
  border-color: #9ca3af;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.1);
}

.form-group input::placeholder {
  color: #9ca3af;
}

.btn-submit {
  width: 100%;
  padding: 0.875rem 1.5rem;
  background: #1f2937;
  color: white;
  border: none;
  border-radius: 0.75rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.btn-submit:hover:not(:disabled) {
  background: #374151;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.btn-submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error {
  margin-top: 1rem;
  color: #dc2626;
  text-align: center;
  font-size: 0.875rem;
  padding: 0.75rem;
  background: #fef2f2;
  border-radius: 0.5rem;
  border: 1px solid #fecaca;
}

.login-footer {
  text-align: center;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: #6b7280;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: color 0.2s;
}

.back-link:hover {
  color: #1f2937;
}

@media (max-width: 640px) {
  .login-card {
    padding: 2rem;
  }

  .login-card h1 {
    font-size: 1.75rem;
  }
}
</style>
