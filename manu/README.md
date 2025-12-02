# TNSFULL Backend - EDDESO

Este repositorio contiene el backend Django para scraping DIAN, analítica/ML y el puente TNS. La referencia completa de endpoints vive en [`docs/api_endpoints.md`](../docs/api_endpoints.md); usa ese archivo como fuente única (incluye ejemplos y notas de autenticación).

## Requisitos rápidos
1. Python 3.12+, PostgreSQL y Redis (ver variables en `.env`).
2. Instala dependencias: `pip install -r requirements.txt`.
3. Ejecuta migraciones con `python manage.py migrate` y crea un superusuario si lo necesitas.
4. Levanta el servidor: `python manage.py runserver 0.0.0.0:8000`.
5. Para tareas DIAN/TNS, ejecuta también el worker: 
   - **Linux**: `celery -A config worker -l info -P prefork --concurrency=4 -E`
   - **Windows**: `celery -A config worker -l info -P solo`
   
   **Nota**: En producción Linux, usa el servicio systemd (ver `docs/systemd/celerycore.service`).

## Documentación

### Guías Principales
- **API Endpoints**: [`docs/api_endpoints.md`](../docs/api_endpoints.md) - Referencia completa de todos los endpoints con ejemplos
- **Flujo del Sistema**: [`docs/FLUJO_SISTEMA.md`](../docs/FLUJO_SISTEMA.md) - **NUEVO** - Secuencia completa de pasos y qué hace cada acción
- **MLflow Integration**: [`docs/MLFLOW_INTEGRATION.md`](../docs/MLFLOW_INTEGRATION.md) - Integración opcional con MLflow

### Colección Postman
- `postman_collection.json` está sincronizada con la guía. Importa la colección y configura las variables `{{base_url}}`, `{{jwt_token}}`, `{{api_key}}` y `{{session_id}}`.

## Flujo de Trabajo Rápido

### Configuración Inicial (Una vez)
1. **Crear Servidor**: `POST /assistant/api/servidores/` - Registra un servidor de base de datos (Firebird, PostgreSQL, etc.)
2. **Escanear Empresas**: `POST /assistant/api/sistema/descubrir_empresas/` - Descubre empresas en el servidor
3. **Configurar Consulta SQL**: `PATCH /assistant/api/empresas-servidor/{id}/` - Define la consulta para extraer datos

### Uso Regular
4. **Extraer Datos**: `POST /assistant/api/sistema/extraer_datos/` - Extrae movimientos de inventario
5. **Entrenar ML** (opcional): `POST /assistant/api/ml/entrenar_modelos/` - Entrena modelos de predicción
6. **Consultas Naturales**: `POST /assistant/api/consulta-natural/pregunta_inteligente/` - Preguntas en lenguaje natural

**Ver [`docs/FLUJO_SISTEMA.md`](../docs/FLUJO_SISTEMA.md) para detalles completos de cada paso.**

## Arquitectura del Sistema

### Apps Principales
- **`sistema_analitico`**: Gestión de servidores, empresas, extracción de datos, ML y consultas naturales
- **`dian_scraper`**: Scraping automático de facturas desde DIAN
- **`fudo_scraper`**: Scraping y sincronización con FUDO

### Servicios Clave
- **`DataManager`**: Gestiona conexiones, descubrimiento de empresas y extracción de datos
- **`MLEngine`**: Motor de Machine Learning (XGBoost, Prophet)
- **`NaturalResponseOrchestrator`**: Procesa consultas en lenguaje natural
- **`TNSBridge`**: Puente para interactuar con bases de datos TNS/Firebird

## Buenas prácticas
- Cuando agregues un endpoint o cambies uno existente: actualiza primero `docs/api_endpoints.md` y luego reexporta `postman_collection.json`.
- Mantén los servicios externos (Firebird, Redis) configurados en `Servidor`/`EmpresaServidor` para que el puente TNS funcione.
- Usa JWT para usuarios internos y API keys para clientes externos; ambos mecanismos están documentados en la guía.
- Consulta [`docs/FLUJO_SISTEMA.md`](../docs/FLUJO_SISTEMA.md) para entender el flujo completo antes de hacer cambios.
