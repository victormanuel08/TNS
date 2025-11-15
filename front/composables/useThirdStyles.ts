export const useThirdStyles = () => {
  const { company } = useCompany()

  const applyThirdStyles = () => {
    if (!process.client || !company.value) return

    const root = document.documentElement
    const primary = company.value.primary_color || '#3B82F6'
    const secondary = company.value.secondary_color || '#1E40AF'
    const fontFamily = company.value.font_family || 'Inter, sans-serif'

    root.style.setProperty('--primary-color', primary)
    root.style.setProperty('--secondary-color', secondary)
    root.style.setProperty('--font-family', fontFamily)
  }

  return { applyThirdStyles }
}
