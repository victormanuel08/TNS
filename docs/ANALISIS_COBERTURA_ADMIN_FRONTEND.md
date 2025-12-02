# Análisis de Cobertura: Admin Frontend vs Backend

## 📊 Resumen Ejecutivo

Este documento compara los endpoints/ViewSets disponibles en el backend con las secciones implementadas en el frontend admin.

---

## ✅ ViewSets/Endpoints en Backend

### 1. **Servidores** (`ServidorViewSet`)
- ✅ **Frontend**: Implementado
- Endpoint: `/api/servidores/`
- Funcionalidades: Crear, listar, editar, eliminar servidores

### 2. **Empresas Servidor** (`EmpresaServidorViewSet`)
- ✅ **Frontend**: Implementado (parcial)
- Endpoint: `/api/empresas-servidor/`
- Funcionalidades: 
  - ✅ Listar empresas
  - ✅ Ver detalles
  - ✅ Extraer datos
  - ✅ Editar consulta_sql
  - ✅ Editar configuracion (JSON)
  - ❌ Crear empresa (solo desde escaneo)
  - ❌ Editar empresa completa
  - ❌ Eliminar empresa

### 3. **Movimientos Inventario** (`MovimientoInventarioViewSet`)
- ❌ **Frontend**: NO implementado
- Endpoint: `/api/movimientos/`
- Funcionalidades: CRUD completo de movimientos

### 4. **Permisos Usuarios** (`UsuarioEmpresaViewSet`)
- ✅ **Frontend**: Implementado
- Endpoint: `/api/permisos-usuarios/`
- Funcionalidades: CRUD completo

### 5. **Tenant Profiles** (`UserTenantProfileViewSet`)
- ✅ **Frontend**: Implementado
- Endpoint: `/api/tenant-profiles/`
- Funcionalidades: CRUD completo

### 6. **Sistema** (`SistemaViewSet`)
- ✅ **Frontend**: Implementado (parcial)
- Endpoint: `/api/sistema/`
- Funcionalidades:
  - ✅ Descubrir empresas (escaneo)
  - ✅ Estado de descubrimiento
  - ✅ Extraer datos
  - ❌ Inicializar sistema
  - ❌ Otros endpoints del ViewSet

### 7. **ML** (`MLViewSet`)
- ✅ **Frontend**: Implementado (parcial)
- Endpoint: `/api/ml/`
- Funcionalidades:
  - ✅ Ver modelos
  - ✅ Ver estadísticas
  - ❌ Entrenar modelos
  - ❌ Predecir demanda
  - ❌ Recomendaciones de compras

### 8. **Consulta Natural** (`ConsultaNaturalViewSet`)
- ❌ **Frontend**: NO implementado
- Endpoint: `/api/consulta-natural/`
- Funcionalidades: Consultas en lenguaje natural

### 9. **Testing** (`TestingViewSet`)
- ❌ **Frontend**: NO implementado
- Endpoint: `/api/testing/`
- Funcionalidades: Pruebas del sistema

### 10. **API Keys** (`APIKeyManagementViewSet`)
- ✅ **Frontend**: Implementado
- Endpoint: `/api/api-keys/`
- Funcionalidades:
  - ✅ Listar API keys
  - ✅ Generar API key
  - ✅ Ver API key (una vez)
  - ✅ Activar/desactivar
  - ❌ Editar API key
  - ❌ Eliminar API key

### 11. **TNS** (`TNSViewSet`)
- ❌ **Frontend**: NO implementado
- Endpoint: `/api/tns/`
- Funcionalidades: Operaciones TNS (Visual TNS)

### 12. **Branding** (`BrandingViewSet`)
- ❌ **Frontend**: NO implementado
- Endpoint: `/api/branding/`
- Funcionalidades: Personalización de empresas

### 13. **E-commerce Config** (`EcommerceConfigViewSet`)
- ❌ **Frontend**: NO implementado
- Endpoint: `/api/ecommerce-config/`
- Funcionalidades: Configuración de e-commerce

### 14. **Cajas Autopago** (`CajaAutopagoViewSet`)
- ❌ **Frontend**: NO implementado
- Endpoint: `/api/cajas-autopago/`
- Funcionalidades: Gestión de cajas autopago

### 15. **DIAN Processor** (`DianProcessorViewSet`)
- ❌ **Frontend**: NO implementado
- Endpoint: `/api/dian-processor/`
- Funcionalidades: Procesamiento de documentos DIAN

### 16. **VPN Configs** (`VpnConfigViewSet`)
- ✅ **Frontend**: Implementado
- Endpoint: `/api/vpn/configs/`
- Funcionalidades:
  - ✅ Listar configs
  - ✅ Ver detalles
  - ✅ Descargar config
  - ✅ Ver stats
  - ❌ Crear config
  - ❌ Editar config
  - ❌ Eliminar config
  - ❌ Sincronizar peers

### 17. **Server Management** (`ServerManagementViewSet`)
- ✅ **Frontend**: Implementado
- Endpoint: `/api/server/`
- Funcionalidades:
  - ✅ Ver servicios systemd
  - ✅ Ver procesos PM2
  - ✅ Ver logs (Celery, PM2, servicios)
  - ✅ Ver tareas Celery en tiempo real
  - ✅ Ejecutar comandos terminal
  - ❌ Iniciar/detener servicios
  - ❌ Reiniciar servicios

### 18. **Notas Rápidas** (`NotaRapidaViewSet`)
- ❌ **Frontend**: NO implementado
- Endpoint: `/api/notas-rapidas/`
- Funcionalidades: CRUD de notas rápidas

### 19. **Usuarios** (`UserManagementViewSet`)
- ✅ **Frontend**: Implementado
- Endpoint: `/api/usuarios/`
- Funcionalidades: CRUD completo + reset password

### 20. **Empresa Dominios** (`EmpresaDominioViewSet`)
- ✅ **Frontend**: Implementado
- Endpoint: `/api/empresa-dominios/`
- Funcionalidades: CRUD completo

### 21. **Pasarelas de Pago** (`PasarelaPagoViewSet`)
- ✅ **Frontend**: Implementado
- Endpoint: `/api/pasarelas-pago/`
- Funcionalidades: CRUD completo

---

## 📈 Estadísticas de Cobertura

- **Total ViewSets/Endpoints**: 21
- **Totalmente Implementados**: 8 (38%)
- **Parcialmente Implementados**: 5 (24%)
- **No Implementados**: 8 (38%)

---

## 🎯 Endpoints Públicos (No Requieren Admin)

Estos endpoints no necesitan estar en el admin frontend:

- `/api/resolve-domain/` - Resolver dominio
- `/api/public-catalog/` - Catálogo público
- `/api/public-catalog/images/` - Imágenes públicas
- `/api/formas-pago-ecommerce/` - Formas de pago
- `/api/pasarelas-disponibles/` - Pasarelas disponibles
- `/api/procesar-pago-ecommerce/` - Procesar pago
- `/api/pasarela-response/` - Respuesta de pasarela

---

## 🔴 Funcionalidades Faltantes Críticas

### Alta Prioridad:
1. **Movimientos Inventario** - CRUD completo
2. **Branding** - Personalización visual de empresas
3. **E-commerce Config** - Configuración de tiendas
4. **Cajas Autopago** - Gestión de cajas
5. **Notas Rápidas** - Sistema de notas

### Media Prioridad:
1. **TNS ViewSet** - Operaciones con Visual TNS
2. **DIAN Processor** - Procesamiento de documentos
3. **Consulta Natural** - Interfaz de consultas
4. **Testing** - Herramientas de prueba

### Baja Prioridad:
1. **Completar funcionalidades parciales**:
   - Crear/editar empresas manualmente
   - Gestión completa de VPN configs
   - Control de servicios (start/stop/restart)
   - Entrenar modelos ML desde frontend

---

## ✅ Recomendaciones

1. **Implementar funcionalidades faltantes críticas** (Alta prioridad)
2. **Completar funcionalidades parciales** en secciones existentes
3. **Agregar validaciones y confirmaciones** para operaciones destructivas
4. **Mejorar UX** con loading states y mensajes de error más claros
5. **Agregar permisos granulares** por sección

---

## 📝 Notas

- El análisis se basa en los ViewSets registrados en `urls.py`
- Algunos endpoints pueden tener acciones adicionales (`@action`) no listadas aquí
- Se recomienda revisar cada ViewSet individualmente para funcionalidades específicas

