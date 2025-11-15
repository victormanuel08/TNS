export const useTheme = () => {
  const theme = useState<'ecommerce' | 'pos' | 'pro' | 'autopago'>(
    'theme',
    () => 'ecommerce'
  )
  const { company, currentMode } = useCompany()

  const setTheme = (newTheme: 'ecommerce' | 'pos' | 'pro' | 'autopago') => {
    theme.value = newTheme

    if (process.client) {
      document.body.className = `theme-${newTheme}`
    }
  }

  watch(
    company,
    (next) => {
      if (next?.mode) {
        setTheme(next.mode)
      }
    },
    { immediate: true }
  )

  watch(currentMode, (next) => {
    if (next) {
      setTheme(next)
    }
  })

  onMounted(() => {
    if (company.value?.mode) {
      setTheme(company.value.mode)
    }
  })

  return {
    theme: readonly(theme),
    setTheme,
    currentTheme: computed(() => theme.value)
  }
}
