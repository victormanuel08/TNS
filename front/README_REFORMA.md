# Reforma del Frontend - TNS Full

## Estructura Implementada

### 1. Páginas Públicas (dominio.com)
- **`/`** - Página principal con secciones: Inicio, Servicios, Acerca de
- Diseño moderno con tonos claros (blancos, crema, pasteles)

### 2. Panel de Administración (dominio.com/admin)
- **`/admin/login`** - Login para superusuarios
- **`/admin/dashboard`** - Panel completo de administración con:
  - Gestión de servidores
  - Gestión de empresas
  - Gestión de scrapers (DIAN, FUDO)
  - Gestión de modelos ML

### 3. Sistema de Subdominios (cualquiercosa.dominio.com)
- **`/subdomain/login`** - Login tipo Picasso (mitad visual, mitad formulario)
- **`/subdomain/`** - Redirige al template preferido del usuario
- **`/subdomain/retail`** - Template Retail/Autopago (pantalla táctil)
- **`/subdomain/restaurant`** - Template Restaurante (app de pedidos)
- **`/subdomain/pro`** - Template Profesional (software contable)

### 4. Componentes Clave
- **`TemplateSwitcher`** - Permite cambiar entre templates dinámicamente
- **`EmpresaSelectorModal`** - Modal elegante para seleccionar empresa con:
  - Buscador por nombre o código
  - Selección de años fiscales
  - Diseño moderno y limpio

### 5. Composables
- **`useTemplate`** - Gestión de templates y cambio dinámico
- **`useSubdomain`** - Detección y manejo de subdominios
- **`useSessionStore`** - Actualizado para soportar subdominios en login

## Cambios en Backend

### TEMPLATE_CHOICES Corregidos
- Eliminada duplicación
- Centralizados en una constante
- Solo 3 templates: `retail`, `restaurant`, `pro`
- Cada uno con su descripción clara

## Diseño

### Paleta de Colores
- **Fondo**: Tonos claros (#fafafa, #ffffff)
- **Acentos**: Azules suaves (#2563eb, #3b82f6)
- **Pasteles**: Crema, azul pastel, morado pastel
- **Texto**: Grises suaves (#1f2937, #6b7280)

### Características
- Diseño limpio y moderno
- Animaciones suaves
- Responsive
- Intuitivo sin exagerar

## Próximos Pasos

1. **Completar templates** con los ejemplos Vue/TS que proporciones
2. **Conectar APIs reales** en el panel de administración
3. **Implementar validación de subdominio** en el backend
4. **Añadir más funcionalidades** según necesidades

## Notas

- Los templates están mockeados y listos para ser completados
- El sistema de cambio de template funciona dinámicamente
- El modal de empresa incluye buscador y selección de años fiscales
- El diseño es moderno con tonos claros como solicitaste

