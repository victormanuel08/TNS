# TNSFULL Backend

Este repositorio contiene el backend Django para scraping DIAN, analítica/ML y el puente TNS. La referencia completa de endpoints vive en [`docs/api_endpoints.md`](../docs/api_endpoints.md); usa ese archivo como fuente única (incluye ejemplos y notas de autenticación).

## Requisitos rápidos
1. Python 3.12+, PostgreSQL y Redis (ver variables en `.env`).
2. Instala dependencias: `pip install -r requirements.txt`.
3. Ejecuta migraciones con `python manage.py migrate` y crea un superusuario si lo necesitas.
4. Levanta el servidor: `python manage.py runserver 0.0.0.0:8000`.
5. Para tareas DIAN/TNS, ejecuta también el worker: `celery -A config worker -l info -P solo`.

## Documentación
- **Guía completa**: [`docs/api_endpoints.md`](../docs/api_endpoints.md) describe autenticación, Scraping DIAN, documentos, Sistema/ML, consulta natural y puente TNS. Cada sección incluye request/response de ejemplo.
- **Colección Postman**: `postman_collection.json` está sincronizada con la guía. Importa la colección y configura las variables `{{base_url}}`, `{{jwt_token}}`, `{{api_key}}` y `{{session_id}}`.

## Buenas prácticas
- Cuando agregues un endpoint o cambies uno existente: actualiza primero `docs/api_endpoints.md` y luego reexporta `postman_collection.json`.
- Mantén los servicios externos (Firebird, Redis) configurados en `Servidor`/`EmpresaServidor` para que el puente TNS funcione.
- Usa JWT para usuarios internos y API keys para clientes externos; ambos mecanismos están documentados en la guía.
