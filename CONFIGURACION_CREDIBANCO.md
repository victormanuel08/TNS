# Configuración de Credibanco según PASARELADEPAGO

## Datos de Configuración Necesarios

### 1. Credenciales API (OBLIGATORIAS)
- **userName**: Usuario API proporcionado por Credibanco
  - Ejemplo: `"DEPOSITO_HABITARE-api"`
  - Se almacena en: `EmpresaEcommerceConfig.payment_public_key` o `PasarelaPago.configuracion.user_name`
  
- **password**: Contraseña API proporcionada por Credibanco
  - Ejemplo: `"Palustre2021."`
  - Se almacena en: `EmpresaEcommerceConfig.payment_secret_key` o `PasarelaPago.configuracion.password`

### 2. URLs y Endpoints (CONFIGURABLES)
- **api_url**: URL base de la API de Credibanco
  - Producción: `"https://eco.credibanco.com/payment/rest/"`
  - Se almacena en: `PasarelaPago.configuracion.api_url`
  
- **register_endpoint**: Endpoint para registrar pago
  - Valor: `"register.do"`
  - Se almacena en: `PasarelaPago.configuracion.register_endpoint`
  
- **status_endpoint**: Endpoint para consultar estado
  - Valor: `"getOrderStatusExtended.do"`
  - Se almacena en: `PasarelaPago.configuracion.status_endpoint`

### 3. Valores de Configuración (OPCIONALES, con valores por defecto)
- **purchaseCurrencyCode**: Código de moneda
  - Valor por defecto: `"170"` (Pesos colombianos)
  - Se almacena en: `PasarelaPago.configuracion.currency_code`
  
- **purchasePlanId**: Identificación del plan de cobranza
  - Valor por defecto: `"01"`
  - Se almacena en: `PasarelaPago.configuracion.plan_id`
  
- **purchaseQuotaId**: Cuotas de tarjeta de crédito
  - Valor por defecto: `"012"` (12 cuotas)
  - Para otras tarjetas usar: `"001"`
  - Se almacena en: `PasarelaPago.configuracion.quota_id`
  
- **language**: Idioma de la interfaz
  - Valor por defecto: `"es"`
  - Se almacena en: `PasarelaPago.configuracion.language`
  
- **billingCountry**: Código de país por defecto
  - Valor por defecto: `"CO"` (Colombia)
  - Se almacena en: `PasarelaPago.configuracion.default_country`
  
- **billingState**: Estado/Departamento por defecto
  - Valor por defecto: `"NDS"` (Norte de Santander)
  - Se almacena en: `PasarelaPago.configuracion.default_state`
  
- **billingPostalCode**: Código postal por defecto
  - Valor por defecto: `"54001"`
  - Se almacena en: `PasarelaPago.configuracion.default_postal_code`
  
- **billingGender**: Género por defecto
  - Valor por defecto: `"M"`
  - Se almacena en: `PasarelaPago.configuracion.default_gender`
  
- **shippingReceptionMethod**: Método de recepción de envío
  - Valor por defecto: `"ba"`
  - Se almacena en: `PasarelaPago.configuracion.shipping_reception_method`

### 4. Valores Dinámicos (NO se configuran, vienen del cliente)
- **amount**: Monto en centavos (se calcula dinámicamente)
- **orderNumber**: Número de orden único (timestamp)
- **returnUrl**: URL de retorno después del pago (se genera dinámicamente)
- **failUrl**: URL de fallo (se genera dinámicamente)
- **jsonParams**: JSON con datos del cliente (se construye dinámicamente)

## Estructura JSON para PasarelaPago.configuracion

```json
{
  "api_url": "https://eco.credibanco.com/payment/rest/",
  "register_endpoint": "register.do",
  "status_endpoint": "getOrderStatusExtended.do",
  "user_name": "DEPOSITO_HABITARE-api",
  "password": "Palustre2021.",
  "currency_code": "170",
  "plan_id": "01",
  "quota_id": "012",
  "language": "es",
  "default_country": "CO",
  "default_state": "NDS",
  "default_postal_code": "54001",
  "default_gender": "M",
  "shipping_reception_method": "ba"
}
```

## Notas Importantes

1. **Credenciales**: Las credenciales `userName` y `password` pueden venir de:
   - `EmpresaEcommerceConfig.payment_public_key` y `payment_secret_key` (prioridad)
   - `PasarelaPago.configuracion.user_name` y `password` (fallback)

2. **Valores por defecto**: Si no se configuran en `PasarelaPago.configuracion`, se usan los valores hardcodeados mostrados arriba.

3. **Valores dinámicos**: Algunos valores como `billingState`, `billingPostalCode`, `payerCity` deberían venir del cliente si están disponibles, pero si no, se usan los valores por defecto.

4. **Seguridad**: Las contraseñas nunca deben exponerse en el frontend. Se almacenan encriptadas en `EmpresaEcommerceConfig.password_tns` (para TNS) y en `EmpresaEcommerceConfig.payment_secret_key` (para Credibanco).

