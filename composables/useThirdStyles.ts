export const useThirdStyles = () => {
  const { company } = useCompany()

  const applyThirdStyles = () => {
    if (!company.value) return

    const root = document.documentElement
    
    // Por ahora usamos valores por defecto
    // Estos vendrán del backend después
    root.style.setProperty('--primary-color', company.value.primary_color || '#3B82F6')
    root.style.setProperty('--secondary-color', company.value.secondary_color || '#1E40AF')
    root.style.setProperty('--font-family', company.value.font_family || 'Inter, sans-serif')
    
    console.log('Estilos aplicados para empresa:', company.value.name)
  }

  return { applyThirdStyles }
}