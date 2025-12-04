# Análisis de Seguridad de Endpoints

## 📊 Estado Actual

### 1. **Carga de RUT (subir-pdf)**
- **Autenticación actual:** `IsAuthenticated` + `APIKeyAwareViewSet`
- **Permisos:** Solo superusuarios pueden subir
- **Riesgo si es público:** ⚠️ **ALTO**
  - Cualquiera podría subir RUTs falsos o incorrectos
  - Podría corromper los datos del sistema
  - Afecta el cálculo de PN/PJ para el calendario tributario
  - Podría sobreescribir RUTs válidos

**Recomendación:** ❌ **NO hacerlo público** - Mantener autenticación estricta

---

### 2. **Calendario Tributario - Eventos (GET)**
- **Autenticación actual:** `IsAuthenticated` + `APIKeyAwareViewSet`
- **Permisos:** Solo superusuarios pueden ver (en `get_queryset`)
- **Riesgo si es público:** ✅ **BAJO**
  - Solo lectura de información
  - No modifica datos
  - Información de fechas de vencimiento (pública en teoría)
  - Útil para clientes externos que necesitan consultar sus obligaciones

**Recomendación:** ✅ **Permitir con API Key** - Modificar para que usuarios con API Key válida puedan consultar eventos de sus empresas asociadas

---

### 3. **Calendario Tributario - Carga Excel (subir-excel)**
- **Autenticación actual:** `IsAuthenticated` + `APIKeyAwareViewSet`
- **Permisos:** Solo superusuarios pueden subir
- **Riesgo si es público:** ⚠️ **MUY ALTO**
  - Modifica datos críticos del calendario tributario
  - Podría corromper todas las fechas de vencimiento
  - Afecta a todas las empresas del sistema

**Recomendación:** ❌ **NO hacerlo público** - Mantener solo para superusuarios

---

## 🔒 Propuesta de Seguridad

### Opción 1: Mantener Seguridad Estricta (Recomendada)
- **RUT:** Solo superusuarios autenticados
- **Eventos Calendario:** API Key válida (solo empresas asociadas)
- **Carga Excel:** Solo superusuarios

### Opción 2: Permitir API Key para Eventos
- **RUT:** Solo superusuarios autenticados
- **Eventos Calendario:** API Key válida (público con API Key)
- **Carga Excel:** Solo superusuarios

---

## 💡 Implementación Recomendada

### Modificar `obtener_eventos` para permitir API Key sin ser superusuario:

```python
@action(detail=False, methods=['get'], url_path='eventos')
def obtener_eventos(self, request):
    """
    Obtiene eventos del calendario tributario.
    Permite API Key para consultar eventos de empresas asociadas.
    """
    # Si tiene API Key válida, permitir consultar eventos de sus empresas
    if hasattr(request, 'cliente_api') and request.cliente_api:
        # Usuario con API Key - puede consultar eventos de sus empresas
        empresas_autorizadas = request.empresas_autorizadas
        # Lógica para filtrar por empresas autorizadas
    elif request.user.is_superuser:
        # Superusuario - puede consultar cualquier empresa
        pass
    else:
        # Usuario autenticado sin API Key - solo superusuarios
        return Response(
            {'error': 'Se requiere API Key válida o ser superusuario'},
            status=status.HTTP_403_FORBIDDEN
        )
```

---

## 📝 Resumen de Decisiones

| Endpoint | Actual | Recomendado | Razón |
|----------|--------|-------------|-------|
| **RUT - subir-pdf** | Solo superusuarios | ✅ Mantener | Alto riesgo de corrupción de datos |
| **Calendario - eventos (GET)** | Solo superusuarios | ✅ Permitir API Key | Bajo riesgo, información útil para clientes |
| **Calendario - eventos-multiples (POST)** | Solo superusuarios | ✅ Permitir API Key | Bajo riesgo, información útil para clientes |
| **Calendario - subir-excel** | Solo superusuarios | ✅ Mantener | Muy alto riesgo de corrupción masiva |

---

## 🎯 Conclusión

1. **RUT:** ❌ **NO hacer público** - Es crítico para determinar PN/PJ
2. **Eventos Calendario:** ✅ **Permitir con API Key** - Información útil, bajo riesgo
3. **Carga Excel:** ❌ **NO hacer público** - Muy alto riesgo

La mejor opción es permitir que usuarios con API Key válida puedan consultar eventos del calendario tributario de sus empresas asociadas, pero mantener la carga de RUT y Excel solo para superusuarios.

