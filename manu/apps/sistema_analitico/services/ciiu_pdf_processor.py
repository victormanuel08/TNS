"""
Servicio para procesar el PDF de CIIU usando DeepSeek y extraer información estructurada.
Optimizado para procesar en lotes y minimizar costos de API.
"""
import pdfplumber
import re
import json
import logging
import time
from typing import Dict, List, Optional, Any
from django.conf import settings
import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


class CIIUPDFProcessor:
    """Procesa el PDF de CIIU usando DeepSeek para extraer información estructurada"""
    
    def __init__(self, pdf_path: str = 'CIIU.pdf'):
        self.pdf_path = pdf_path
        self.base_url = "https://api.deepseek.com/chat/completions"
        
        # API Key: Usar rotación como el clasificador (fallback a settings)
        self.api_key_obj = None
        self.api_key = None
        self._obtener_api_key()
        
        if not self.api_key:
            raise ValueError("No hay API keys disponibles (ni en BD ni en settings)")
    
    def _obtener_api_key(self):
        """
        Obtener API key usando rotación automática desde el modelo (como el clasificador).
        Si no hay API keys en el modelo, usar la de settings como fallback.
        """
        try:
            from apps.sistema_analitico.models import AIAnalyticsAPIKey
            api_key_obj = AIAnalyticsAPIKey.obtener_siguiente_api_key()
            if api_key_obj:
                self.api_key_obj = api_key_obj
                self.api_key = api_key_obj.api_key
                logger.info(f"🔑 [API_KEY] Usando API key: {api_key_obj.nombre} (Total peticiones: {api_key_obj.total_peticiones})")
            else:
                # Fallback a settings si no hay API keys en BD
                self.api_key = getattr(settings, 'AIANALYTICS_API_KEY', None) or getattr(settings, 'DEEPSEEK_API_KEY', None)
                if self.api_key:
                    logger.warning(f"⚠️ [API_KEY] No hay API keys en BD, usando API key de settings")
        except Exception as e:
            logger.warning(f"⚠️ [API_KEY] Error obteniendo API key del modelo: {e}, usando settings")
            self.api_key = getattr(settings, 'AIANALYTICS_API_KEY', None) or getattr(settings, 'DEEPSEEK_API_KEY', None)
    
    def extraer_codigos_ciuu_del_pdf(self, target_codigo: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extrae códigos CIUU del PDF con su contexto completo.
        Retorna lista de diccionarios con información de cada código.
        
        Args:
            target_codigo: Si se especifica, solo extrae ese código específico.
                          Si es None, extrae todos los códigos.
        """
        codigos_encontrados = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            total_paginas = len(pdf.pages)
            logger.info(f"Procesando PDF con {total_paginas} páginas")
            
            # IMPORTANTE: Empezar desde la página 136 (índice 135)
            # Las páginas anteriores no tienen información útil
            pagina_inicio = 135  # Índice 0-based (página 136)
            
            if pagina_inicio >= total_paginas:
                logger.warning(f"⚠️  La página 136 no existe en el PDF (solo tiene {total_paginas} páginas). Procesando desde el inicio.")
                pagina_inicio = 0
            else:
                logger.info(f"📄 Procesando desde la página 136 (índice {pagina_inicio}) hasta el final")
            
            # Extraer texto solo desde la página 136 en adelante
            texto_completo = ""
            for i in range(pagina_inicio, total_paginas):
                page = pdf.pages[i]
                texto_pagina = page.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina + "\n"
            
            # Buscar códigos CIUU de 4 dígitos
            # Patrón mejorado: código de 4 dígitos seguido de descripción
            # Buscamos patrones como "0111 Cultivo de..." o "2620 Fabricación de..."
            patron_codigo = re.compile(
                r'(\d{4})\s+([A-ZÁÉÍÓÚÑ][^\n]{10,200})',
                re.MULTILINE
            )
            
            matches = list(patron_codigo.finditer(texto_completo))
            logger.info(f"Encontrados {len(matches)} posibles códigos CIUU")
            
            # Para cada código, extraer su sección completa (incluyendo "Esta clase incluye:" y "Esta clase excluye:")
            for i, match in enumerate(matches):
                codigo = match.group(1)
                
                # Si se especificó un código objetivo, solo procesar ese
                if target_codigo and codigo != target_codigo:
                    continue
                
                descripcion_inicial = match.group(2).strip()
                
                # Encontrar el inicio de la sección (inicio del código)
                inicio_seccion = match.start()
                
                # El fin es el inicio del siguiente código de 4 dígitos, o el final del texto
                if i + 1 < len(matches):
                    fin_seccion = matches[i + 1].start()
                else:
                    fin_seccion = len(texto_completo)
                
                # Extraer texto completo de la sección (esto incluye TODO: descripción, "Esta clase incluye:", "Esta clase excluye:")
                texto_seccion = texto_completo[inicio_seccion:fin_seccion].strip()
                
                # Limpiar descripción (tomar solo la primera línea después del código)
                lineas = texto_seccion.split('\n')
                descripcion_final = descripcion_inicial
                
                # Verificar que el texto completo incluya las secciones importantes
                tiene_incluye = 'Esta clase incluye:' in texto_seccion or 'incluye:' in texto_seccion.lower()
                tiene_excluye = 'Esta clase excluye:' in texto_seccion or 'excluye:' in texto_seccion.lower()
                
                if not tiene_incluye and not tiene_excluye:
                    logger.warning(f"Código {codigo} no tiene secciones 'incluye' o 'excluye' claras")
                
                codigos_encontrados.append({
                    'codigo': codigo,
                    'descripcion': descripcion_final,
                    'texto_completo': texto_seccion,  # Incluye TODO: descripción, "Esta clase incluye:", "Esta clase excluye:"
                    'incluye_raw': '',  # Se extraerá con DeepSeek
                    'excluye_raw': ''   # Se extraerá con DeepSeek
                })
                
                # Si se especificó un código objetivo y ya lo encontramos, salir
                if target_codigo and codigo == target_codigo:
                    break
        
        logger.info(f"Extraídos {len(codigos_encontrados)} códigos CIUU del PDF")
        return codigos_encontrados
    
    def _intentar_reparar_json_truncado(self, contenido: str) -> str:
        """
        Intenta reparar un JSON truncado cerrando objetos/arrays abiertos.
        """
        contenido = contenido.strip()
        
        # Si termina abruptamente en medio de una cadena, intentar cerrarla
        if contenido.count('"') % 2 != 0:
            # Hay comillas sin cerrar, buscar la última comilla abierta
            ultima_comilla = contenido.rfind('"')
            if ultima_comilla > 0:
                # Verificar si está dentro de una cadena (no escapada)
                antes_comilla = contenido[:ultima_comilla]
                if antes_comilla.count('\\"') % 2 == 0:  # Número par de comillas escapadas antes
                    contenido = contenido + '"'
        
        # Cerrar objetos/arrays abiertos
        abrir_obj = contenido.count('{')
        cerrar_obj = contenido.count('}')
        abrir_arr = contenido.count('[')
        cerrar_arr = contenido.count(']')
        
        # Agregar cierres faltantes
        contenido += '}' * (abrir_obj - cerrar_obj)
        contenido += ']' * (abrir_arr - cerrar_arr)
        
        return contenido
    
    def _guardar_respuesta_cruda(self, contenido: str, error: Exception, intento: int):
        """
        Guarda la respuesta cruda en un archivo para debugging.
        """
        import os
        from django.conf import settings
        
        try:
            logs_dir = os.path.join(settings.BASE_DIR, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(logs_dir, f'deepseek_error_response_{timestamp}_intento{intento}.txt')
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Error: {error}\n")
                if hasattr(error, 'lineno'):
                    f.write(f"Posición: línea {error.lineno}, columna {error.colno}\n")
                if hasattr(error, 'pos'):
                    f.write(f"Posición (char): {error.pos}\n")
                f.write(f"Longitud: {len(contenido)} caracteres\n")
                f.write("\n" + "="*80 + "\n")
                f.write("RESPUESTA CRUDA:\n")
                f.write("="*80 + "\n")
                f.write(contenido)
            
            logger.warning(f"   💾 Respuesta cruda guardada en: {filename}")
        except Exception as e:
            logger.error(f"   ❌ Error guardando respuesta cruda: {e}")
    
    def procesar_lote_con_deepseek(self, codigos_lote: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Procesa un lote de códigos CIUU con DeepSeek.
        Retorna lista de diccionarios con información estructurada.
        """
        # Construir prompt con todos los códigos del lote
        prompt_codigos = ""
        for codigo_info in codigos_lote:
            # Asegurar que enviamos TODO el texto completo, incluyendo "Esta clase incluye:" y "Esta clase excluye:"
            texto_completo = codigo_info['texto_completo']
            
            # Truncamiento inteligente: NO cortar en medio de secciones importantes
            # Límite más generoso: 5000 chars por código (vs 3000 anterior)
            # Priorizar mantener las secciones "incluye" y "excluye" COMPLETAS
            if len(texto_completo) > 5000:
                # Buscar "Esta clase excluye:" para asegurar que esté completo
                idx_excluye = texto_completo.find('Esta clase excluye:')
                if idx_excluye > 0:
                    # Buscar el final de la sección excluye (hasta el siguiente código de 4 dígitos o fin)
                    siguiente_codigo = re.search(r'\n(\d{4})\s+', texto_completo[idx_excluye + 100:])
                    if siguiente_codigo:
                        # Cortar justo antes del siguiente código
                        fin_excluye = idx_excluye + 100 + siguiente_codigo.start()
                        texto_completo = texto_completo[:fin_excluye]
                    else:
                        # Si no hay siguiente código, tomar hasta 2000 chars después de "excluye:"
                        texto_completo = texto_completo[:idx_excluye + 2000]
                else:
                    # Si no tiene "excluye:", buscar "incluye:" y tomar hasta 4000 chars después
                    idx_incluye = texto_completo.find('Esta clase incluye:')
                    if idx_incluye > 0:
                        texto_completo = texto_completo[:idx_incluye + 4000]
                    else:
                        # Fallback: truncar a 5000 chars
                        texto_completo = texto_completo[:5000]
            
            prompt_codigos += f"""
CÓDIGO CIUU: {codigo_info['codigo']}
DESCRIPCIÓN: {codigo_info['descripcion']}
TEXTO COMPLETO (incluye secciones "Esta clase incluye:" y "Esta clase excluye:"):
{texto_completo}

---
"""
        
        system_prompt = """Eres un experto en clasificación de actividades económicas CIIU.
Tu tarea es extraer información estructurada de códigos CIUU del PDF.

Para CADA código CIUU, debes extraer:
1. Código CIUU (4 dígitos)
2. Descripción/Título (la primera línea después del código)
3. División (primeros 2 dígitos del código)
4. Grupo (primeros 3 dígitos del código)
5. Lista de actividades que INCLUYE (de la sección "Esta clase incluye:")
6. Lista de actividades que EXCLUYE (de la sección "Esta clase excluye:")

INSTRUCCIONES CRÍTICAS:
- El texto completo que recibes incluye las secciones "Esta clase incluye:" y "Esta clase excluye:"
- Cada viñeta (•) en "Esta clase incluye:" es una actividad que INCLUYE
- Cada viñeta (•) en "Esta clase excluye:" es una actividad que EXCLUYE
- El formato de "incluye" y "excluye" debe ser EXACTAMENTE igual al de la API:
  [{"actId": 162, "actIncluye": "S", "actDescripcion": "El cultivo de cereales, como: trigo, maíz..."}]
- actId debe ser un número secuencial único por código (empezar en 1 para cada código)
- actIncluye debe ser "S" para incluye, "N" para excluye
- actDescripcion debe ser el texto COMPLETO de la viñeta (incluyendo todo el texto después del •)

EJEMPLO del formato esperado:
Si el texto tiene:
  "Esta clase incluye:
  • El cultivo de cereales, como: trigo, maíz, sorgo...
  • El cultivo de legumbres, como: frijoles, habas..."

Debes extraer:
  "incluye": [
    {"actId": 1, "actIncluye": "S", "actDescripcion": "El cultivo de cereales, como: trigo, maíz, sorgo..."},
    {"actId": 2, "actIncluye": "S", "actDescripcion": "El cultivo de legumbres, como: frijoles, habas..."}
  ]

Responde SOLO con JSON válido, un objeto por código CIUU:
{
  "codigo": "0111",
  "cseDescripcion": "Cultivo de cereales (excepto arroz), legumbres y semillas oleaginosas",
  "cseTitulo": "Cultivo de cereales (excepto arroz), legumbres y semillas oleaginosas",
  "division": "01",
  "grupo": "011",
  "incluye": [
    {"actId": 1, "actIncluye": "S", "actDescripcion": "El cultivo de cereales, como: trigo, maíz, sorgo, cebada, centeno, avena, mijo y otros cereales n.c.p."},
    {"actId": 2, "actIncluye": "S", "actDescripcion": "El cultivo de legumbres, como: frijoles, habas, garbanzos, caupíes, lentejas, arvejas, guandúes y otras leguminosas n.c.p."}
  ],
  "excluye": [
    {"actId": 3, "actIncluye": "N", "actDescripcion": "El cultivo de arroz. Se incluye en la clase 0112, «Cultivo de arroz»."}
  ]
}

Si hay múltiples códigos, retorna un array de objetos JSON."""

        user_prompt = f"""Extrae la información estructurada de estos códigos CIUU:

{prompt_codigos}

Responde SOLO con JSON válido (array de objetos, uno por código)."""

        # Intentar llamada con retry y rotación de API keys (como el clasificador)
        max_retries = 3
        retry_delay = 1  # Segundos iniciales
        last_error = None
        api_key_usada = None
        
        for intento in range(max_retries):
            # Obtener siguiente API key (rotación automática) en cada intento
            try:
                from apps.sistema_analitico.models import AIAnalyticsAPIKey
                api_key_obj = AIAnalyticsAPIKey.obtener_siguiente_api_key()
                if api_key_obj:
                    api_key_usada = api_key_obj
                    current_api_key = api_key_obj.api_key
                    logger.info(f"🔑 [API_KEY] Intento {intento + 1}: Usando API key '{api_key_obj.nombre}'")
                else:
                    # Fallback a settings
                    current_api_key = getattr(settings, 'AIANALYTICS_API_KEY', None) or getattr(settings, 'DEEPSEEK_API_KEY', '')
                    if not current_api_key:
                        raise ValueError("No hay API keys disponibles ni en BD ni en settings")
            except Exception as e:
                logger.warning(f"⚠️ [API_KEY] Error obteniendo API key del modelo: {e}, usando settings")
                current_api_key = getattr(settings, 'AIANALYTICS_API_KEY', None) or getattr(settings, 'DEEPSEEK_API_KEY', '')
                if not current_api_key:
                    raise ValueError("No hay API keys disponibles")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {current_api_key}"
            }
            
            payload = {
                "model": "deepseek-chat",  # Modelo más económico
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,  # Baja temperatura para respuestas más consistentes
                "max_tokens": 8192  # Máximo permitido por DeepSeek (rango válido: [1, 8192])
            }
            
            try:
                # Log del payload antes de enviar (solo tamaño y estructura, no el contenido completo)
                logger.info(f"📤 Enviando petición a DeepSeek (intento {intento + 1}/{max_retries})")
                logger.info(f"   - Modelo: {payload.get('model')}")
                logger.info(f"   - Max tokens: {payload.get('max_tokens')}")
                logger.info(f"   - Tamaño del system prompt: {len(payload['messages'][0]['content'])} caracteres")
                logger.info(f"   - Tamaño del user prompt: {len(payload['messages'][1]['content'])} caracteres")
                
                response = requests.post(self.base_url, json=payload, headers=headers, timeout=90)
                
                # Si hay error, capturar y mostrar el mensaje de DeepSeek
                if response.status_code != 200:
                    error_msg = f"Status {response.status_code}: {response.text[:500]}"
                    logger.error(f"❌ Error en respuesta de DeepSeek: {error_msg}")
                    try:
                        error_json = response.json()
                        if 'error' in error_json:
                            error_detail = error_json['error']
                            logger.error(f"   Detalle del error: {error_detail}")
                    except:
                        pass
                
                response.raise_for_status()
                
                # Éxito: trackear petición exitosa (como el clasificador)
                if api_key_usada:
                    api_key_usada.incrementar_peticion(exitosa=True, es_rate_limit=False)
                
                # Si llegamos aquí, la petición fue exitosa
                respuesta_json = response.json()
                usage = respuesta_json.get('usage', {})
                
                # Calcular costos (como el clasificador)
                from apps.sistema_analitico.services.clasificador_contable_service import calcular_costo_tokens
                
                input_tokens = usage.get('prompt_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0)
                cache_hit_tokens = usage.get('prompt_cache_hit_tokens')
                cache_miss_tokens = usage.get('prompt_cache_miss_tokens')
                
                costo_info = calcular_costo_tokens(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_hit_tokens=cache_hit_tokens,
                    cache_miss_tokens=cache_miss_tokens
                )
                
                # Trackear costo en la API key usada (como el clasificador)
                if api_key_usada:
                    api_key_usada.agregar_costo(
                        costo_usd=costo_info['costo_usd'],
                        tokens_input=input_tokens,
                        tokens_output=output_tokens,
                        tokens_cache_hit=cache_hit_tokens or 0,
                        tokens_cache_miss=cache_miss_tokens or 0
                    )
                    logger.info(f"💰 [API_KEY] Costo agregado a '{api_key_usada.nombre}': ${costo_info['costo_usd']:.6f} USD (Total acumulado: ${api_key_usada.costo_total_usd:.6f} USD)")
                
                # Procesar respuesta exitosa
                contenido = respuesta_json['choices'][0]['message']['content']
                
                # Log de tokens y costos usados (con prints visibles)
                print("=" * 80)
                print("💰 DETALLE COMPLETO DE COSTOS (PROCESADOR PDF CIUU):")
                print("=" * 80)
                print(f"📊 TOKENS UTILIZADOS:")
                print(f"   - Input tokens (total):     {costo_info['tokens_input']}")
                print(f"   - Output tokens:            {costo_info['tokens_output']}")
                print(f"   - Cache HIT tokens:         {costo_info['tokens_cache_hit']}")
                print(f"   - Cache MISS tokens:        {costo_info['tokens_cache_miss']}")
                print(f"\n💰 COSTOS:")
                print(f"   - Input (cache hit):        ${costo_info['costo_input_usd']:.10f} USD")
                print(f"   - Output:                   ${costo_info['costo_output_usd']:.10f} USD")
                print(f"   - TOTAL:                    ${costo_info['costo_usd']:.10f} USD")
                from django.conf import settings as django_settings
                print(f"   - TOTAL (COP):              ${costo_info['costo_cop']:,.2f} COP (tasa: {getattr(django_settings, 'TASA_CAMBIO_COP_USD', 4000)} COP/USD)")
                print("=" * 80)
                
                logger.info(f"📊 Tokens usados: input={input_tokens}, output={output_tokens}")
                logger.info(f"💰 Costo: ${costo_info['costo_usd']:.6f} USD (${costo_info['costo_cop']:,.2f} COP)")
                
                # Limpiar respuesta (puede tener markdown code blocks)
                contenido_original = contenido
                contenido = contenido.strip()
                if contenido.startswith('```json'):
                    contenido = contenido[7:]
                if contenido.startswith('```'):
                    contenido = contenido[3:]
                if contenido.endswith('```'):
                    contenido = contenido[:-3]
                contenido = contenido.strip()
                
                # Intentar parsear JSON con manejo mejorado de errores
                try:
                    datos_estructurados = json.loads(contenido)
                except json.JSONDecodeError as json_err:
                    # Log detallado del error
                    logger.error(f"❌ Error parseando JSON (intento {intento + 1}/{max_retries}): {json_err}")
                    logger.error(f"   Posición del error: línea {json_err.lineno}, columna {json_err.colno}")
                    logger.error(f"   Longitud del contenido: {len(contenido)} caracteres")
                    
                    # Mostrar contexto alrededor del error
                    if json_err.pos:
                        inicio = max(0, json_err.pos - 100)
                        fin = min(len(contenido), json_err.pos + 100)
                        contexto = contenido[inicio:fin]
                        logger.error(f"   Contexto del error (pos {json_err.pos}): ...{contexto}...")
                    
                    # Intentar reparar JSON truncado (si termina abruptamente)
                    contenido_reparado = self._intentar_reparar_json_truncado(contenido)
                    if contenido_reparado != contenido:
                        logger.warning("   🔧 Intentando reparar JSON truncado...")
                        try:
                            datos_estructurados = json.loads(contenido_reparado)
                            logger.info("   ✅ JSON reparado exitosamente")
                        except json.JSONDecodeError as err2:
                            logger.error(f"   ❌ No se pudo reparar: {err2}")
                            # Guardar respuesta cruda para debugging
                            self._guardar_respuesta_cruda(contenido_original, json_err, intento)
                            raise json_err  # Re-lanzar el error original
                    else:
                        # Guardar respuesta cruda para debugging
                        self._guardar_respuesta_cruda(contenido_original, json_err, intento)
                        raise json_err
                
                # Si es un solo objeto, convertirlo a lista
                if isinstance(datos_estructurados, dict):
                    datos_estructurados = [datos_estructurados]
                
                logger.info(f"✅ Procesados {len(datos_estructurados)} códigos con DeepSeek")
                return datos_estructurados  # Retornar aquí si fue exitoso
                
            except json.JSONDecodeError as e:
                last_error = e
                logger.error(f"Error parseando JSON de DeepSeek: {e}")
                if intento < max_retries - 1:
                    wait_time = retry_delay * (2 ** intento)
                    time.sleep(wait_time)
                else:
                    logger.error(f"Error parseando JSON después de {max_retries} intentos")
                    if api_key_usada:
                        api_key_usada.incrementar_peticion(exitosa=False, es_rate_limit=False)
                    return []
                
            except requests.exceptions.HTTPError as e:
                last_error = e
                status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
                es_rate_limit = (status_code == 429)
                
                # Capturar mensaje de error de DeepSeek
                error_detail = ""
                if hasattr(e, 'response') and e.response:
                    try:
                        error_json = e.response.json()
                        if 'error' in error_json:
                            error_obj = error_json['error']
                            if isinstance(error_obj, dict):
                                error_detail = f" - {error_obj.get('message', error_obj.get('type', str(error_obj)))}"
                            else:
                                error_detail = f" - {error_obj}"
                        else:
                            error_detail = f" - {e.response.text[:300]}"
                    except:
                        error_detail = f" - {str(e)}"
                
                # Trackear petición fallida (como el clasificador)
                if api_key_usada:
                    api_key_usada.incrementar_peticion(exitosa=False, es_rate_limit=es_rate_limit)
                
                # Si es rate limit (429), esperar más tiempo
                if es_rate_limit:
                    if intento < max_retries - 1:
                        wait_time = retry_delay * (2 ** intento)  # Backoff exponencial
                        logger.warning(f"⏳ [RATE_LIMIT] Intento {intento + 1}/{max_retries}: Esperando {wait_time}s antes de reintentar...")
                        time.sleep(wait_time)
                        continue
                elif status_code == 400:
                    # Error 400: Bad Request - probablemente el payload es muy grande o inválido
                    logger.error(f"❌ [HTTP_ERROR] Error 400 Bad Request{error_detail}")
                    logger.error(f"   Esto generalmente indica que el payload es demasiado grande o tiene formato inválido")
                    logger.error(f"   Tamaño del user prompt: {len(payload['messages'][1]['content'])} caracteres")
                    logger.error(f"   Considera reducir el tamaño del lote (actualmente: {len(codigos_lote)} códigos)")
                    
                    # No reintentar con el mismo payload si es 400
                    if api_key_usada:
                        api_key_usada.incrementar_peticion(exitosa=False, es_rate_limit=False)
                    raise ValueError(f"Error 400 Bad Request de DeepSeek{error_detail}. El payload puede ser demasiado grande. Intenta procesar menos códigos por lote.")
                else:
                    # Otro error HTTP, no reintentar
                    logger.error(f"❌ [HTTP_ERROR] Error {status_code}{error_detail}")
                    raise
                    
            except requests.exceptions.RequestException as e:
                last_error = e
                # Trackear petición fallida (como el clasificador)
                if api_key_usada:
                    api_key_usada.incrementar_peticion(exitosa=False, es_rate_limit=False)
                
                if intento < max_retries - 1:
                    wait_time = retry_delay * (2 ** intento)
                    logger.warning(f"⚠️ [ERROR] Intento {intento + 1}/{max_retries}: {e}. Esperando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                last_error = e
                raise
            except Exception as e:
                last_error = e
                # Trackear petición fallida (como el clasificador)
                if api_key_usada:
                    api_key_usada.incrementar_peticion(exitosa=False, es_rate_limit=False)
                
                logger.warning(f"⚠️ [ERROR] Intento {intento + 1}/{max_retries}: {e}")
                if intento < max_retries - 1:
                    wait_time = retry_delay * (2 ** intento)
                    time.sleep(wait_time)
                else:
                    raise
        
        # Si llegamos aquí, todos los intentos fallaron
        logger.error(f"❌ Todos los intentos fallaron. Último error: {last_error}")
        return []
    
    def procesar_pdf_completo(self, tamanio_lote: int = 10) -> List[Dict[str, Any]]:
        """
        Procesa el PDF completo en lotes para optimizar costos.
        
        Args:
            tamanio_lote: Número de códigos a procesar por llamada (default: 10)
        
        Returns:
            Lista de diccionarios con información estructurada de todos los códigos
        """
        # Paso 1: Extraer códigos del PDF
        logger.info("Paso 1: Extrayendo códigos CIUU del PDF...")
        codigos_extraidos = self.extraer_codigos_ciuu_del_pdf()
        
        if not codigos_extraidos:
            logger.warning("No se encontraron códigos CIUU en el PDF")
            return []
        
        logger.info(f"Encontrados {len(codigos_extraidos)} códigos CIUU")
        
        # Paso 2: Procesar en lotes
        logger.info(f"Paso 2: Procesando {len(codigos_extraidos)} códigos en lotes de {tamanio_lote}...")
        
        todos_los_resultados = []
        
        for i in range(0, len(codigos_extraidos), tamanio_lote):
            lote = codigos_extraidos[i:i + tamanio_lote]
            logger.info(f"Procesando lote {i//tamanio_lote + 1}/{(len(codigos_extraidos) + tamanio_lote - 1)//tamanio_lote} ({len(lote)} códigos)...")
            
            resultados_lote = self.procesar_lote_con_deepseek(lote)
            todos_los_resultados.extend(resultados_lote)
            
            # Pequeña pausa para evitar rate limiting
            import time
            time.sleep(1)
        
        logger.info(f"✅ Procesamiento completo: {len(todos_los_resultados)} códigos estructurados")
        return todos_los_resultados
    
    def guardar_ciiu_en_bd(self, datos: Dict[str, Any]):
        """
        Guarda un solo código CIUU en el modelo ActividadEconomica.
        
        Args:
            datos: Diccionario con información del código CIUU
            
        Returns:
            Instancia de ActividadEconomica guardada, o None si falla
        """
        from apps.sistema_analitico.models import ActividadEconomica
        
        codigo = datos.get('codigo')
        if not codigo:
            logger.error("No se puede guardar CIUU sin código")
            return None
        
        # Preparar datos
        actividad_data = {
            'codigo': codigo,
            'descripcion': datos.get('cseDescripcion') or datos.get('descripcion', ''),
            'titulo': datos.get('cseTitulo') or datos.get('titulo', ''),
            'division': datos.get('division', codigo[:2] if len(codigo) >= 2 else ''),
            'grupo': datos.get('grupo', codigo[:3] if len(codigo) >= 3 else ''),
            'incluye': datos.get('incluye', []),
            'excluye': datos.get('excluye', []),
            'fecha_ultima_consulta_api': timezone.now()
        }
        
        try:
            # Crear o actualizar
            actividad, creada = ActividadEconomica.objects.update_or_create(
                codigo=codigo,
                defaults=actividad_data
            )
            
            if creada:
                logger.info(f"✅ Creada actividad {codigo}")
            else:
                logger.info(f"🔄 Actualizada actividad {codigo}")
            
            return actividad
        except Exception as e:
            logger.error(f"❌ Error al guardar CIUU {codigo}: {e}", exc_info=True)
            return None
    
    def guardar_en_bd(self, datos_estructurados: List[Dict[str, Any]]) -> int:
        """
        Guarda los datos estructurados en el modelo ActividadEconomica.
        
        Returns:
            Número de códigos guardados/actualizados
        """
        contador = 0
        
        for datos in datos_estructurados:
            actividad = self.guardar_ciiu_en_bd(datos)
            if actividad:
                contador += 1
        
        return contador

