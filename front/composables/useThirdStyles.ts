import { watch } from 'vue'

export const useThirdStyles = () => {
  const tenant = useTenantStore()

  const applyThirdStyles = () => {
    if (!process.client) return

    const root = document.documentElement
    const primary =
      tenant.company.value?.primary_color || tenant.preferences.value.primaryColor
    const secondary =
      tenant.company.value?.secondary_color ||
      tenant.preferences.value.secondaryColor
    const fontFamily =
      tenant.company.value?.font_family || tenant.preferences.value.fontFamily

    root.style.setProperty('--primary-color', primary)
    root.style.setProperty('--secondary-color', secondary)
    root.style.setProperty('--font-family', fontFamily)
  }

  if (process.client) {
    watch(
      () => [
        tenant.company.value?.primary_color,
        tenant.preferences.value.primaryColor,
        tenant.preferences.value.secondaryColor
      ],
      () => applyThirdStyles(),
      { immediate: true }
    )
  }

  return { applyThirdStyles }
}
