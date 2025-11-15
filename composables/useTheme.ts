// composables/useTheme.ts
export const useTheme = () => {
  const theme = useState('theme', () => 'professional')
  const { company, currentMode } = useCompany()
  
  const setTheme = (newTheme: string) => {
    theme.value = newTheme
    
    if (process.client) {
      document.body.className = `theme-${newTheme}`
    }
  }
  
  // Aplicar tema automáticamente basado en la empresa
  watch(company, (newCompany) => {
    if (newCompany) {
      setTheme(newCompany.mode || newCompany.default_mode)
    }
  })
  
  // También observar currentMode por si cambia
  watch(currentMode, (newMode) => {
    setTheme(newMode)
  })
  
  onMounted(() => {
    if (company.value) {
      setTheme(company.value.mode || company.value.default_mode)
    }
  })
  
  return { 
    theme, 
    setTheme,
    currentTheme: computed(() => theme.value)
  }
}