# 📋 ENDPOINTS COMPLETOS - SISTEMA ANALÍTICO

## 🔐 AUTENTICACIÓN JWT

### Login
POST /api/auth/login/
Content-Type: application/json

{
    "username": "admin",
    "password": "password"
}

Respuesta:
{
    "access": "...",
    "refresh": "...",
    "user": {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "is_superuser": true,
        "puede_gestionar_api_keys": true
    }
}

### Refresh Token
POST /api/auth/refresh/
Content-Type: application/json

{
    "refresh": "..."
}

Respuesta:
{
    "access": "..."
}

### Logout
POST /api/auth/logout/
Content-Type: application/json
Authorization: Bearer <token_acceso>

{
    "refresh_token": "..."
}

Respuesta:
{
    "message": "Logout exitoso"
}

## 🔑 GESTIÓN API KEYS

### Generar API Key
POST /api/api-keys/generar_api_key/
Authorization: Bearer <token_acceso>
Content-Type: application/json

{
    "nit": "123456789",
    "nombre_cliente": "Cliente Externo SA",
    "dias_validez": 365
}

Respuesta:
{
    "nit": "123456789",
    "nombre_cliente": "Cliente Externo SA",
    "api_key": "sk_TuKeyGeneradaAqui123456789",
    "fecha_creacion": "2024-01-15T10:30:00Z",
    "fecha_caducidad": "2025-01-15T10:30:00Z",
    "empresas_asociadas": 3,
    "accion": "Creada",
    "mensaje": "API Key generada exitosamente - GUARDA ESTA KEY"
}

### Listar API Keys
GET /api/api-keys/listar_api_keys/
Authorization: Bearer <token_acceso>

Respuesta:
{
    "total_api_keys": 2,
    "api_keys": [ ... ]
}

### Revocar API Key
POST /api/api-keys/revocar_api_key/
Authorization: Bearer <token_acceso>
Content-Type: application/json

{
    "api_key_id": 1
}

Respuesta:
{
    "mensaje": "API Key revocada exitosamente"
}

### Renovar API Key
POST /api/api-keys/renovar_api_key/
Authorization: Bearer <token_acceso>
Content-Type: application/json

{
    "api_key_id": 1,
    "dias": 180
}

Respuesta:
{
    "mensaje": "API Key renovada por 180 días",
    "nueva_fecha_caducidad": "2024-07-15T10:30:00Z"
}

### Estadísticas API Keys
GET /api/api-keys/estadisticas_api_keys/
Authorization: Bearer <token_acceso>

Respuesta:
{
    "total_api_keys": 5,
    "api_keys_activas": 3,
    "api_keys_expiradas": 2,
    "total_peticiones": 245,
    "api_key_mas_usada": "Cliente Externo SA"
}

## 🧠 CONSULTAS NATURALES

### Pregunta Inteligente (con API Key)
POST /api/consulta-natural/pregunta_inteligente/
API-Key: sk_TuKeyGeneradaAqui123456789
Content-Type: application/json

{
    "consulta": "¿Qué artículos debo comprar para los próximos 6 meses?"
}

### Pregunta Inteligente (con JWT)
POST /api/consulta-natural/pregunta_inteligente/
Authorization: Bearer <token_acceso>
Content-Type: application/json

{
    "consulta": "¿Cuánto vendí en enero 2024?",
    "empresa_servidor_id": 1
}

### Tipos de Consulta Soportados
GET /api/consulta-natural/tipos_consulta_soportados/

Respuesta:
{
    "total_tipos_consulta": 25,
    "tipos_consulta_soportados": [
        "recomendaciones_compras",
        "prediccion_demanda", 
        "ventas_por_mes",
        "ventas_por_anio",
        "comparar_anios",
        "articulos_mas_vendidos",
        "consulta_por_nit",
        "consulta_por_medico"
    ]
}

## ⚙️ SISTEMA

### Inicializar Sistema
POST /api/sistema/inicializar_sistema/
Authorization: Bearer <token_acceso>

### Descubrir Empresas
POST /api/sistema/descubrir_empresas/
Authorization: Bearer <token_acceso>
Content-Type: application/json

{
    "servidor_id": 1
}

### Extraer Datos
POST /api/sistema/extraer_datos/
Authorization: Bearer <token_acceso>
Content-Type: application/json

{
    "empresa_servidor_id": 1,
    "fecha_inicio": "2024-01-01",
    "fecha_fin": "2024-01-31",
    "forzar_reextraccion": false
}

## 🤖 MACHINE LEARNING

### Entrenar Modelos
POST /api/ml/entrenar_modelos/
Authorization: Bearer <token_acceso>
Content-Type: application/json

{
    "empresa_servidor_id": 1,
    "fecha_inicio": "2023-01-01",
    "fecha_fin": "2023-12-31"
}

### Predecir Demanda
POST /api/ml/predecir_demanda/
Authorization: Bearer <token_acceso>
Content-Type: application/json

{
    "modelo_id": "empresa_123456789",
    "meses": 6
}

### Recomendaciones Compras
POST /api/ml/recomendaciones_compras/
Authorization: Bearer <token_acceso>
Content-Type: application/json

{
    "modelo_id": "empresa_123456789",
    "meses": 6,
    "nivel_servicio": 0.95
}

## 🧪 TESTING

### Ejecutar Pruebas Completas
POST /api/testing/ejecutar_pruebas_completas/
Authorization: Bearer <token_acceso>

## 📊 CRUD BÁSICO

### Servidores
GET    /api/servidores/
POST   /api/servidores/
GET    /api/servidores/{id}/
PUT    /api/servidores/{id}/
DELETE /api/servidores/{id}/

### Empresas Servidor
GET    /api/empresas-servidor/
POST   /api/empresas-servidor/
GET    /api/empresas-servidor/{id}/
PUT    /api/empresas-servidor/{id}/
DELETE /api/empresas-servidor/{id}/

### Movimientos Inventario
GET    /api/movimientos/
POST   /api/movimientos/
GET    /api/movimientos/{id}/
PUT    /api/movimientos/{id}/
DELETE /api/movimientos/{id}/

### Permisos Usuarios
GET    /api/permisos-usuarios/
POST   /api/permisos-usuarios/
GET    /api/permisos-usuarios/{id}/
PUT    /api/permisos-usuarios/{id}/
DELETE /api/permisos-usuarios/{id}/

## 🚀 FLUJO COMPLETO DE USO

### Usuario Interno (Admin/Staff)
POST /api/auth/login/
POST /api/api-keys/generar_api_key/
POST /api/sistema/descubrir_empresas/
POST /api/ml/entrenar_modelos/
POST /api/consulta-natural/pregunta_inteligente/

### Cliente Externo
POST /api/consulta-natural/pregunta_inteligente/
API-Key: sk_TuKeyGeneradaAqui123456789

### Refresh Token
POST /api/auth/refresh/
{
    "refresh": "token_refresh_recibido_en_login"
}

## 📝 NOTAS IMPORTANTES

JWT: Para usuarios internos - acceso completo al sistema  
API Keys: Para clientes externos - solo consultas inteligentes  
Auto-detection: Las API Keys acceden automáticamente a TODAS las empresas del NIT  
Seguridad: Las API Keys tienen caducidad y contador de uso  
Compatibilidad: Tu código existente sigue funcionando igual
