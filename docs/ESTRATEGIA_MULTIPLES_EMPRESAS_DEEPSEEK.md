# 🏢 ESTRATEGIA: MÚLTIPLES EMPRESAS CON DEEPSEEK

## 📊 TU ESCENARIO

- **40-100 empresas** gestionadas
- **Cada empresa**: ~150 facturas cada 15 días
- **Volumen estimado**: 
  - 40 empresas × 150 facturas / 15 días = **400 facturas/día promedio**
  - 100 empresas × 150 facturas / 15 días = **1,000 facturas/día promedio**
- **Actual**: 5 API keys en la misma cuenta DeepSeek

---

## 🔑 RESPUESTA CLAVE: ¿COMPARTEN RATE LIMIT?

### ⚠️ **SÍ, las API keys en la misma cuenta COMPARTEN el rate limit**

Según la documentación de DeepSeek:
- **Rate limits son POR CUENTA**, no por API key individual
- Todas las API keys de la misma cuenta comparten el mismo límite dinámico
- El límite se ajusta según:
  - Presión de tráfico en tiempo real
  - Historial de uso a corto plazo de la cuenta

### ✅ **Ventajas de múltiples keys en la misma cuenta:**
1. **Distribución de carga**: Round-robin distribuye peticiones
2. **Redundancia**: Si una key tiene problemas técnicos, otras funcionan
3. **Tracking individual**: Puedes ver uso por key en los CSVs
4. **Mismo saldo**: Todas comparten el mismo plan/facturación
5. **Gestión simple**: Una sola cuenta para recargar

### ❌ **NO aumenta el rate limit:**
- 5 keys en la misma cuenta = mismo rate limit que 1 key
- Las keys solo ayudan con distribución y redundancia, NO con límites

---

## 💰 ¿CUENTA SEPARADA POR EMPRESA O CUENTA PRINCIPAL?

### ✅ **RECOMENDACIÓN: CUENTA PRINCIPAL CON 5-7 API KEYS**

**Razones:**

#### 1. **Costeo ya está perfecto** ✅
- Tu sistema ya trackea costos por API key
- Los CSVs de DeepSeek muestran uso totalizado por key
- Puedes calcular costos por empresa desde tu BD
- **NO necesitas cuentas separadas para costeo**

#### 2. **Gestión simplificada**
- **Una cuenta**: Recargas una vez, todas las empresas usan
- **Múltiples cuentas**: Debes recargar 40-100 cuentas, complicado
- **Facturación**: Una sola factura vs 40-100 facturas

#### 3. **Rate limits compartidos de todas formas**
- Si creas 100 cuentas, cada una tendría su propio rate limit
- Pero tendrías que gestionar 100 cuentas, recargar 100 veces, etc.
- **No vale la pena** para tu volumen

#### 4. **Tu volumen es manejable**
- 400-1,000 facturas/día = **16-42 facturas/hora promedio**
- Con 5-7 keys rotando, cada key procesa ~3-8 facturas/hora
- **Muy por debajo de cualquier límite razonable**

#### 5. **Cumplimiento TOS**
- DeepSeek NO recomienda múltiples cuentas para evadir límites
- Una cuenta principal con 5-7 keys es uso legítimo
- 100 cuentas podría verse como evasión

---

## 🔄 ¿EL SISTEMA ESPERA Y REINTENTA?

### ✅ **SÍ, ya está implementado**

Tu sistema tiene **exponential backoff** completo:

```python
max_retries = 3
retry_delay = 1  # Segundos iniciales

for intento in range(max_retries):
    # Obtener siguiente API key (rotación automática)
    api_key_obj = AIAnalyticsAPIKey.obtener_siguiente_api_key()
    
    try:
        response = requests.post(...)
        # Éxito: salir del loop
        break
    except HTTPError as e:
        es_rate_limit = (e.response.status_code == 429)
        
        if es_rate_limit:
            if intento < max_retries - 1:
                # Backoff exponencial: 1s, 2s, 4s
                wait_time = retry_delay * (2 ** intento)
                time.sleep(wait_time)
                continue  # Reintentar con otra key
```

### 📊 **Cómo funciona:**

1. **Intento 1**: Usa Key-1 → Si falla (429), espera 1 segundo
2. **Intento 2**: Usa Key-2 → Si falla (429), espera 2 segundos
3. **Intento 3**: Usa Key-3 → Si falla (429), espera 4 segundos
4. **Si todos fallan**: Lanza error (muy raro)

### ✅ **Ventajas:**
- **Rotación automática**: Si Key-1 tiene rate limit, prueba Key-2
- **Backoff exponencial**: Espera progresivamente más tiempo
- **Tracking**: Registra qué key tuvo problemas
- **Resiliente**: Maneja errores temporales automáticamente

---

## 📈 ESTRATEGIA RECOMENDADA PARA 40-100 EMPRESAS

### 🎯 **Configuración Óptima:**

#### **1. Cuenta Principal DeepSeek**
- Una sola cuenta para todas las empresas
- Plan según volumen total estimado

#### **2. API Keys (5-7 keys)**
```
DeepSeek-Prod-1 (activa)
DeepSeek-Prod-2 (activa)
DeepSeek-Prod-3 (activa)
DeepSeek-Prod-4 (activa)
DeepSeek-Prod-5 (activa)
DeepSeek-Prod-6 (activa) - Opcional si volumen > 800 facturas/día
DeepSeek-Prod-7 (activa) - Opcional si volumen > 1,000 facturas/día
```

#### **3. Rotación Automática**
- Round-robin inteligente (ya implementado)
- Distribución equitativa entre keys
- Si una key falla, automáticamente usa otra

#### **4. Costeo por Empresa**
- **NO necesitas cuentas separadas**
- Tu sistema ya trackea:
  - `ClasificacionContable` tiene `session_dian_id` → Empresa
  - `AIAnalyticsAPIKey` tiene `costo_total_usd` → Por key
  - Puedes calcular: Costo total / Empresas = Costo por empresa

#### **5. Monitoreo**
- Revisar errores 429 semanalmente
- Verificar distribución equitativa entre keys
- Monitorear costos totales vs presupuesto

---

## 💡 CÁLCULO DE COSTOS POR EMPRESA

### **Opción 1: Proporcional al uso**
```python
# Costo total del período
costo_total = sum(keys.costo_total_usd for keys in AIAnalyticsAPIKey.objects.all())

# Facturas por empresa
facturas_empresa_A = ClasificacionContable.objects.filter(
    session_dian__empresa=empresa_A
).count()

facturas_totales = ClasificacionContable.objects.count()

# Costo proporcional
costo_empresa_A = (facturas_empresa_A / facturas_totales) * costo_total
```

### **Opción 2: Costo real por factura**
```python
# Costo promedio por factura
costo_promedio = costo_total / facturas_totales

# Costo por empresa
costo_empresa_A = facturas_empresa_A * costo_promedio
```

### **Opción 3: Desde CSVs de DeepSeek**
- Los CSVs muestran uso totalizado por API key
- Puedes dividir proporcionalmente entre empresas
- O usar tu sistema de costeo (más preciso)

---

## 🚨 CUÁNDO CONSIDERAR CUENTAS SEPARADAS

### ⚠️ **Solo si:**

1. **Volumen extremo**: > 10,000 facturas/día
2. **Requisitos de facturación**: Necesitas facturar por empresa a clientes
3. **Aislamiento**: Una empresa no debe afectar a otras
4. **Compliance**: Requisitos legales/contables específicos

### ❌ **NO necesitas cuentas separadas si:**
- Solo quieres costeo (ya lo tienes)
- Solo quieres evitar rate limits (keys rotando lo hacen)
- Solo quieres gestión simple (una cuenta es más simple)

---

## 📊 COMPARACIÓN: UNA CUENTA vs MÚLTIPLES CUENTAS

| Aspecto | 1 Cuenta + 5-7 Keys | 100 Cuentas (1 por empresa) |
|---------|---------------------|----------------------------|
| **Gestión** | ✅ Simple (1 recarga) | ❌ Complejo (100 recargas) |
| **Facturación** | ✅ 1 factura | ❌ 100 facturas |
| **Rate Limits** | ⚠️ Compartido | ✅ Separados |
| **Costeo** | ✅ Perfecto (ya implementado) | ✅ También funciona |
| **Redundancia** | ✅ 5-7 keys rotando | ⚠️ 1 key por cuenta |
| **Cumplimiento TOS** | ✅ Uso legítimo | ⚠️ Puede verse como evasión |
| **Tracking** | ✅ Por key en CSVs | ⚠️ Por cuenta (más difícil) |
| **Costo** | ✅ Mismo plan | ❌ Posiblemente más caro |

---

## 🎯 CONCLUSIÓN Y RECOMENDACIÓN FINAL

### ✅ **MANTÉN: 1 CUENTA PRINCIPAL + 5-7 API KEYS**

**Razones:**
1. ✅ **Costeo perfecto**: Ya está implementado y funciona
2. ✅ **Gestión simple**: Una cuenta, una recarga
3. ✅ **Rate limits**: Con 5-7 keys rotando, no tendrás problemas
4. ✅ **Redundancia**: Si una key falla, otras funcionan
5. ✅ **Tracking**: CSVs muestran uso por key, puedes calcular por empresa
6. ✅ **Cumplimiento**: Uso legítimo, no evasión
7. ✅ **Sistema robusto**: Ya tiene exponential backoff y rotación

### 📋 **Plan de Acción:**

1. **Mantén tu cuenta principal** con 5-7 API keys
2. **Agrega 2 keys más** si volumen > 800 facturas/día
3. **Monitorea errores 429** semanalmente
4. **Usa tu sistema de costeo** para calcular por empresa
5. **Revisa CSVs mensualmente** para validar costos

### ⚠️ **NO hagas:**
- ❌ Crear 100 cuentas (innecesario y complicado)
- ❌ Esperar que múltiples keys aumenten rate limit (no lo hacen)
- ❌ Cambiar el sistema de costeo (ya está perfecto)

---

## 📝 CHECKLIST

- [x] Sistema de costeo implementado ✅
- [x] Rotación automática de keys ✅
- [x] Exponential backoff implementado ✅
- [x] Tracking de errores por key ✅
- [ ] Agregar 2 keys más si volumen crece
- [ ] Configurar monitoreo semanal de errores 429
- [ ] Documentar cálculo de costos por empresa

---

**Última actualización**: Diciembre 2025
**Recomendación**: Mantén 1 cuenta + 5-7 keys rotando

