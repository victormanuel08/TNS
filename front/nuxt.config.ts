// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  css: ['@/assets/css/main.css'],
  runtimeConfig: {
    public: {
      djangoApiUrl: process.env.DJANGO_API_URL || 'http://localhost:8000',
      enableBackend: process.env.ENABLE_BACKEND === 'true'
    }
  }
})
