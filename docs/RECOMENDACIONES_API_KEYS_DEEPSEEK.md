# 🔑 RECOMENDACIONES: API KEYS DEEPSEEK

## 📋 Información Oficial de DeepSeek

Según la documentación oficial de DeepSeek:

### Rate Limits
- **NO hay límites fijos** de rate limit por API key
- Durante **períodos de alta demanda**, pueden haber:
  - Delays en las respuestas
  - Errores **429 (Too Many Requests)** si se envían solicitudes demasiado rápido
- Los límites son **dinámicos** y se ajustan según la carga del sistema

### Política de Múltiples Cuentas
⚠️ **IMPORTANTE**: DeepSeek **NO recomienda** usar múltiples cuentas para evadir límites:
- Puede **violar los términos de servicio**
- Puede resultar en **suspensión de cuentas**
- Complica el seguimiento de uso y facturación

---

## ✅ MEJORES PRÁCTICAS (Según DeepSeek)

### 1. **Implementar Exponential Backoff**
Si recibes error 429:
- Esperar 1 segundo antes del primer reintento
- Esperar 2 segundos antes del segundo
- Esperar 4 segundos antes del tercero
- Y así sucesivamente (exponencial)

### 2. **Usar Cache y Procesamiento por Lotes**
- Cachear respuestas frecuentes
- Agrupar múltiples solicitudes cuando sea posible
- Reducir llamadas redundantes

### 3. **Monitorear y Gestionar Uso**
- Realizar seguimiento de patrones de uso
- Identificar solicitudes que se acercan a límites dinámicos
- Ajustar según sea necesario

---

## 🎯 RECOMENDACIONES PARA TU SISTEMA

### 📊 Número Recomendado de API Keys

Basado en tu volumen actual y mejores prácticas:

| Volumen Diario | API Keys Recomendadas | Razón |
|----------------|----------------------|-------|
| **< 1,000 facturas/día** | **2-3 keys** | Distribución básica, redundancia |
| **1,000 - 5,000 facturas/día** | **3-5 keys** | Mejor distribución, evitar saturaciones |
| **5,000 - 10,000 facturas/día** | **5-7 keys** | Distribución óptima, alta disponibilidad |
| **> 10,000 facturas/día** | **7-10 keys** | Máxima distribución, evitar cualquier limitación |

### 💡 Recomendación Específica para Tu Caso

**Basado en tu análisis actual (97 clasificaciones/día, ~$0.10 USD/día):**

#### ✅ **Recomendación: 3-5 API Keys**

**Razones:**
1. **Volumen moderado**: No necesitas muchas keys
2. **Redundancia**: Si una key tiene problemas, otras siguen funcionando
3. **Distribución de carga**: Round-robin distribuye equitativamente
4. **Cumplimiento TOS**: No es excesivo, uso legítimo
5. **Costo**: Todas las keys comparten el mismo saldo/plan

#### ⚠️ **NO exceder 10 keys** porque:
- Puede ser visto como evasión de límites
- Complica la gestión
- No es necesario para tu volumen actual

---

## 🔄 Sistema Actual de Rotación

Tu sistema ya implementa:

### Round-Robin Inteligente
```python
def obtener_siguiente_api_key(cls):
    """
    Selecciona la API key con:
    1. Menos uso reciente (ultima_vez_usada)
    2. Menos peticiones totales (total_peticiones)
    """
    api_keys = cls.objects.filter(activa=True).order_by(
        'ultima_vez_usada', 
        'total_peticiones'
    )
    return api_keys.first()
```

### Ventajas del Sistema Actual:
✅ **Distribución equitativa**: Cada key se usa por turnos
✅ **Balanceo automático**: Prioriza keys menos usadas
✅ **Tracking completo**: Registra uso, errores, costos por key
✅ **Retry automático**: Si una key falla, intenta con otra

---

## 📈 Estrategia de Escalamiento

### Fase 1: Volumen Actual (< 1,000 facturas/día)
- **API Keys**: 3
- **Estrategia**: Round-robin simple
- **Monitoreo**: Revisar errores 429 semanalmente

### Fase 2: Crecimiento (1,000 - 5,000 facturas/día)
- **API Keys**: 5
- **Estrategia**: Round-robin + exponential backoff mejorado
- **Monitoreo**: Revisar errores 429 diariamente

### Fase 3: Alto Volumen (> 5,000 facturas/día)
- **API Keys**: 7-10
- **Estrategia**: Round-robin + backoff + rate limiting interno
- **Monitoreo**: Dashboard en tiempo real

---

## 🛡️ Protecciones Implementadas

### 1. **Exponential Backoff** (Ya implementado)
```python
max_retries = 3
retry_delay = 1  # Segundos iniciales

for intento in range(max_retries):
    # Si es rate limit, esperar más tiempo
    if es_rate_limit:
        time.sleep(retry_delay * (2 ** intento))
```

### 2. **Rotación Automática** (Ya implementado)
- Cada petición usa la siguiente key disponible
- Si una key falla, automáticamente prueba con otra

### 3. **Tracking de Errores** (Ya implementado)
- `total_errores_rate_limit`: Cuenta errores 429 por key
- Permite identificar keys problemáticas

---

## ⚙️ Configuración Recomendada

### Para 3-5 API Keys:

1. **Nombres sugeridos**:
   - `DeepSeek-Prod-1`
   - `DeepSeek-Prod-2`
   - `DeepSeek-Prod-3`
   - `DeepSeek-Prod-4` (opcional)
   - `DeepSeek-Prod-5` (opcional)

2. **Todas activas**: `activa=True`

3. **Mismo plan/saldo**: Todas las keys deben compartir el mismo plan de facturación

4. **Monitoreo**:
   - Revisar `total_errores_rate_limit` semanalmente
   - Si una key tiene muchos errores 429, desactivarla temporalmente
   - Revisar distribución de peticiones (debe ser equitativa)

---

## 🚨 Señales de Alerta

### ⚠️ Si ves estos patrones, considera agregar más keys:

1. **Errores 429 frecuentes** (> 5% de peticiones)
2. **Delays constantes** (> 10 segundos por petición)
3. **Una key recibe > 50% de las peticiones** (problema en rotación)
4. **Volumen creciendo** (> 20% mes a mes)

### ✅ Si todo está bien:

- Errores 429 < 1%
- Tiempo de respuesta < 5 segundos promedio
- Distribución equitativa entre keys
- Sin quejas de usuarios

---

## 📊 Dashboard de Monitoreo Recomendado

### Métricas a revisar:

1. **Por API Key**:
   - Total peticiones
   - Errores 429
   - Costo acumulado
   - Última vez usada

2. **Global**:
   - Peticiones por hora/día
   - Tasa de éxito/fallo
   - Costo total
   - Tiempo promedio de respuesta

---

## 🎯 CONCLUSIÓN Y RECOMENDACIÓN FINAL

### Para tu volumen actual (97-134 clasificaciones/día):

✅ **Usa 3-5 API Keys**

**Configuración sugerida:**
```
1. DeepSeek-Prod-1 (activa)
2. DeepSeek-Prod-2 (activa)
3. DeepSeek-Prod-3 (activa)
4. DeepSeek-Prod-4 (activa) - Opcional
5. DeepSeek-Prod-5 (activa) - Opcional
```

**Ventajas:**
- ✅ Distribución de carga
- ✅ Redundancia (si una falla, otras funcionan)
- ✅ Cumplimiento TOS (uso legítimo)
- ✅ Fácil gestión
- ✅ Tracking individual por key

**Cuándo escalar a más keys:**
- Cuando volumen > 5,000 facturas/día
- Cuando errores 429 > 5%
- Cuando delays > 10 segundos constantemente

---

## 📝 Checklist de Implementación

- [ ] Crear 3-5 API keys en DeepSeek
- [ ] Agregar todas al modelo `AIAnalyticsAPIKey`
- [ ] Verificar que todas estén `activa=True`
- [ ] Probar rotación (verificar que se usen todas)
- [ ] Configurar monitoreo de errores 429
- [ ] Revisar distribución semanalmente
- [ ] Documentar nombres y propósito de cada key

---

**Última actualización**: Diciembre 2025
**Fuente**: Documentación oficial DeepSeek + Análisis del sistema actual

