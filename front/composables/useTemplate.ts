export type TemplateType = 'retail' | 'restaurant' | 'pro'

export const useTemplate = () => {
  const currentTemplate = useState<TemplateType>('current-template', () => 'pro')
  const session = useSessionStore()

  const templates = {
    retail: {
      name: 'Retail / Autopago',
      description: 'Pantalla táctil tipo McDonald\'s',
      route: '/subdomain/retail',
      color: '#0EA5E9'
    },
    restaurant: {
      name: 'Restaurante',
      description: 'App de pedidos tipo Makos',
      route: '/subdomain/restaurant',
      color: '#F97316'
    },
    pro: {
      name: 'Profesional',
      description: 'Software contable full',
      route: '/subdomain/pro',
      color: '#2563EB'
    }
  }

  const setTemplate = (template: TemplateType) => {
    currentTemplate.value = template
    // Guardar preferencia en backend si hay sesión
    if (session.isAuthenticated.value) {
      // TODO: Llamar API para actualizar preferred_template
    }
    navigateTo(templates[template].route)
  }

  const getTemplateInfo = (template: TemplateType) => {
    return templates[template]
  }

  return {
    currentTemplate: readonly(currentTemplate),
    templates,
    setTemplate,
    getTemplateInfo
  }
}

