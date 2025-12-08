# Configuración de Hablame y Deepseek en MANU

## Variables a agregar en `.env`

Agrega las siguientes variables al archivo `.env` de MANU:

### Configuración Deepseek (Para consultas inteligentes)
```env
# ============================================
# DEEPSEEK API (Para consultas inteligentes)
# ============================================
DEEPSEEK_API_KEY=sk-f0ba5a27ac694372aa63ee974237a9b2
```

### Configuración Hablame (SMS y Llamadas)
```env
# ============================================
# HABLAME API (SMS y Llamadas)
# ============================================
HABLAME_ACCOUNT=10013855
HABLAME_APIKEY=4wnE24MumCFKoAcS89rkT3AiEhBMhK
HABLAME_TOKEN=5a70e03fde3f87b01f4488c7366e6515
HABLAME_SMS_URL=https://api103.hablame.co/api/sms/v3/send/priority
HABLAME_SMS_REPORT_URL=https://api103.hablame.co/api/sms/v3/report/
HABLAME_TTS_URL=https://api103.hablame.co/api/callblasting/v1/callblasting/tts_text
HABLAME_TTS_STATUS_URL=https://api103.hablame.co/api/callblasting/v1/callblasting/status/
HABLAME_SMS_SERVICE_CODE=890202
HABLAME_TTS_VOICE=es-US-natural-3
HABLAME_MAX_INTENTOS=3
HABLAME_TIEMPO_ESPERA=5
```

## Ubicación del archivo `.env`

El archivo `.env` debe estar en la raíz del proyecto MANU:
```
manu/.env
```

## Notas

- **Deepseek**: Ya está configurado en `settings.py`, solo necesitas agregar la variable `DEEPSEEK_API_KEY` al `.env`
- **Hablame**: Todas las variables están configuradas en `settings.py` con valores por defecto, pero debes agregar las credenciales reales (`HABLAME_ACCOUNT`, `HABLAME_APIKEY`, `HABLAME_TOKEN`) al `.env`
- Las URLs y configuraciones opcionales tienen valores por defecto, pero puedes personalizarlas si es necesario

## Script de Actualización Automática

Se ha creado un script para actualizar automáticamente el `.env`:

```bash
python scripts/actualizar_env_hablame_deepseek.py
```

Este script:
- ✅ Lee el `.env` actual
- ✅ Crea un backup (`.env.backup`)
- ✅ Agrega/actualiza las variables de Hablame y Deepseek
- ✅ Mantiene las demás configuraciones intactas

## Verificación

Después de agregar las variables, reinicia el servidor Django para que tome los nuevos valores:

```bash
# En desarrollo
python manage.py runserver

# En producción (con systemd o PM2)
sudo systemctl restart manu
# o
pm2 restart manu
```

## Variables Configuradas

### Deepseek
- `DEEPSEEK_API_KEY`: Clave API de Deepseek para consultas inteligentes

### Hablame
- `HABLAME_ACCOUNT`: Número de cuenta Hablame
- `HABLAME_APIKEY`: Clave API de Hablame
- `HABLAME_TOKEN`: Token de autenticación Hablame
- `HABLAME_SMS_URL`: URL para envío de SMS
- `HABLAME_SMS_REPORT_URL`: URL para reportes de SMS
- `HABLAME_TTS_URL`: URL para llamadas TTS
- `HABLAME_TTS_STATUS_URL`: URL para estado de llamadas
- `HABLAME_SMS_SERVICE_CODE`: Código de servicio SMS
- `HABLAME_TTS_VOICE`: Voz para TTS
- `HABLAME_MAX_INTENTOS`: Máximo de intentos para llamadas
- `HABLAME_TIEMPO_ESPERA`: Tiempo de espera entre intentos

