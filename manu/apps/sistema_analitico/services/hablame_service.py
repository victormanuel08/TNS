"""
Servicio para envío de SMS y llamadas usando la API de Hablame
Sistema completo y organizado para comunicación telefónica
"""
import requests
import time
import logging
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class HablameService:
    """
    Servicio para envío de SMS y llamadas usando la API de Hablame.
    Proporciona métodos para comunicación telefónica de forma organizada.
    """
    
    def __init__(self):
        """Inicializa el servicio con configuración desde settings"""
        self.account = getattr(settings, 'HABLAME_ACCOUNT', '')
        self.api_key = getattr(settings, 'HABLAME_APIKEY', '')
        self.token = getattr(settings, 'HABLAME_TOKEN', '')
        self.sms_url = getattr(settings, 'HABLAME_SMS_URL', 'https://api103.hablame.co/api/sms/v3/send/priority')
        self.sms_report_url = getattr(settings, 'HABLAME_SMS_REPORT_URL', 'https://api103.hablame.co/api/sms/v3/report/')
        self.tts_url = getattr(settings, 'HABLAME_TTS_URL', 'https://api103.hablame.co/api/callblasting/v1/callblasting/tts_text')
        self.tts_status_url = getattr(settings, 'HABLAME_TTS_STATUS_URL', 'https://api103.hablame.co/api/callblasting/v1/callblasting/status/')
        self.sms_service_code = getattr(settings, 'HABLAME_SMS_SERVICE_CODE', '890202')
        self.tts_voice = getattr(settings, 'HABLAME_TTS_VOICE', 'es-US-natural-3')
        self.max_intentos = getattr(settings, 'HABLAME_MAX_INTENTOS', 3)
        self.tiempo_espera = getattr(settings, 'HABLAME_TIEMPO_ESPERA', 5)
        
        # Headers base para todas las peticiones
        self.headers = {
            "Content-Type": "application/json",
            "account": self.account,
            "apiKey": self.api_key,
            "token": self.token
        }
        
        # Validar que las credenciales estén configuradas
        if not all([self.account, self.api_key, self.token]):
            logger.warning("⚠️ [HABLAME] Credenciales no configuradas completamente")
    
    def _formatear_telefono(self, telefono: str) -> str:
        """
        Formatea el teléfono al formato requerido (57XXXXXXXXXX)
        
        Args:
            telefono: Número de teléfono (10 dígitos o con código país)
            
        Returns:
            Teléfono formateado
        """
        # Limpiar caracteres no numéricos
        telefono_limpio = ''.join(filter(str.isdigit, telefono))
        
        # Si tiene 10 dígitos, agregar código de país
        if len(telefono_limpio) == 10:
            return f"57{telefono_limpio}"
        
        # Si ya tiene código de país, retornar tal cual
        if telefono_limpio.startswith('57') and len(telefono_limpio) == 12:
            return telefono_limpio
        
        # Si no cumple formato, retornar con 57
        return f"57{telefono_limpio[-10:]}" if len(telefono_limpio) >= 10 else f"57{telefono_limpio}"
    
    def enviar_sms(
        self, 
        telefono: str, 
        mensaje: str, 
        flash: bool = False,
        prioridad: bool = True
    ) -> Dict[str, Any]:
        """
        Envía un SMS a través de la API de Hablame
        
        Args:
            telefono: Número de teléfono (10 dígitos, sin indicativo)
            mensaje: Mensaje a enviar
            flash: Si es True, el SMS aparece directamente en pantalla
            prioridad: Si es True, envía con prioridad alta
            
        Returns:
            Dict con información del envío:
            {
                "success": bool,
                "sms_id": str,
                "costo": int,
                "estado": str,
                "telefono": str,
                "mensaje": str,
                "error": str (si hay error)
            }
        """
        telefono_formateado = self._formatear_telefono(telefono)
        
        payload = {
            "toNumber": telefono_formateado,
            "sms": mensaje,
            "flash": "1" if flash else "0",
            "sc": self.sms_service_code,
            "request_dlvr_rcpt": "0",
            "isPriority": 1 if prioridad else 0
        }
        
        logger.info(f"📱 [SMS] Enviando SMS a {telefono_formateado}")
        logger.debug(f"📱 [SMS] Mensaje: {mensaje[:50]}...")
        
        try:
            response = requests.post(
                self.sms_url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            respuesta = response.json()
            
            if "smsId" in respuesta:
                sms_id = respuesta["smsId"]
                logger.info(f"✅ [SMS] SMS enviado exitosamente. ID: {sms_id}")
                
                # Verificar estado del SMS
                estado = self.verificar_estado_sms(sms_id)
                costo = int(estado.get("price", 0)) if estado and "price" in estado else 0
                
                return {
                    "success": True,
                    "sms_id": sms_id,
                    "costo": costo,
                    "estado": "entregado" if costo > 0 else "pendiente",
                    "telefono": telefono_formateado,
                    "mensaje": mensaje,
                    "data": respuesta
                }
            else:
                error_msg = respuesta.get("error", "Error desconocido")
                logger.error(f"❌ [SMS] Error en respuesta: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "telefono": telefono_formateado,
                    "mensaje": mensaje,
                    "data": respuesta
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [SMS] Error de conexión: {str(e)}")
            return {
                "success": False,
                "error": f"Error de conexión: {str(e)}",
                "telefono": telefono_formateado,
                "mensaje": mensaje
            }
        except Exception as e:
            logger.error(f"❌ [SMS] Error inesperado: {str(e)}")
            return {
                "success": False,
                "error": f"Error inesperado: {str(e)}",
                "telefono": telefono_formateado,
                "mensaje": mensaje
            }
    
    def enviar_llamada(
        self, 
        telefono: str, 
        mensaje: str,
        duplicar_mensaje: bool = True
    ) -> Dict[str, Any]:
        """
        Envía una llamada TTS (Text-to-Speech) a través de la API de Hablame
        
        Args:
            telefono: Número de teléfono (10 dígitos, sin indicativo)
            mensaje: Mensaje a convertir a voz
            duplicar_mensaje: Si es True, duplica el mensaje para mejor comprensión
            
        Returns:
            Dict con información de la llamada:
            {
                "success": bool,
                "call_id": str,
                "costo": int,
                "estado": str ("contestada" | "no_contestada"),
                "duracion": str,
                "telefono": str,
                "mensaje": str,
                "error": str (si hay error)
            }
        """
        telefono_formateado = self._formatear_telefono(telefono)
        
        # Duplicar mensaje para mejor comprensión en llamada
        mensaje_final = f"{mensaje}. {mensaje}" if duplicar_mensaje else mensaje
        
        payload = {
            "toNumber": telefono_formateado,
            "text": mensaje_final,
            "voice_name": self.tts_voice,
            "attempts": self.max_intentos,
            "attempts_delay": self.tiempo_espera,
        }
        
        logger.info(f"📞 [LLAMADA] Enviando llamada a {telefono_formateado}")
        logger.debug(f"📞 [LLAMADA] Mensaje: {mensaje[:50]}...")
        
        try:
            response = requests.post(
                self.tts_url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            respuesta = response.json()
            
            if "callblastingId" in respuesta:
                call_id = respuesta["callblastingId"]
                logger.info(f"✅ [LLAMADA] Llamada iniciada. ID: {call_id}")
                
                # Monitorear estado de la llamada
                estado_final = self._monitorear_llamada(call_id)
                
                if estado_final.get("contestada"):
                    logger.info(f"✅ [LLAMADA] Llamada contestada. Costo: {estado_final.get('costo', 0)}")
                    return {
                        "success": True,
                        "call_id": call_id,
                        "costo": estado_final.get("costo", 0),
                        "estado": "contestada",
                        "duracion": estado_final.get("duracion", "0"),
                        "telefono": telefono_formateado,
                        "mensaje": mensaje,
                        "data": respuesta
                    }
                else:
                    logger.warning(f"⚠️ [LLAMADA] Llamada no contestada")
                    return {
                        "success": False,
                        "call_id": call_id,
                        "costo": 0,
                        "estado": "no_contestada",
                        "telefono": telefono_formateado,
                        "mensaje": mensaje,
                        "error": "Llamada no contestada",
                        "data": respuesta
                    }
            else:
                error_msg = respuesta.get("error", "Error desconocido")
                logger.error(f"❌ [LLAMADA] Error en respuesta: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "telefono": telefono_formateado,
                    "mensaje": mensaje,
                    "data": respuesta
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [LLAMADA] Error de conexión: {str(e)}")
            return {
                "success": False,
                "error": f"Error de conexión: {str(e)}",
                "telefono": telefono_formateado,
                "mensaje": mensaje
            }
        except Exception as e:
            logger.error(f"❌ [LLAMADA] Error inesperado: {str(e)}")
            return {
                "success": False,
                "error": f"Error inesperado: {str(e)}",
                "telefono": telefono_formateado,
                "mensaje": mensaje
            }
    
    def enviar_mixto(
        self, 
        telefono: str, 
        mensaje: str
    ) -> Dict[str, Any]:
        """
        Envía primero una llamada y si no contesta, envía un SMS de respaldo.
        Estrategia de comunicación mixta para mayor efectividad.
        
        Args:
            telefono: Número de teléfono (10 dígitos, sin indicativo)
            mensaje: Mensaje a enviar
            
        Returns:
            Dict con información de ambos envíos:
            {
                "success": bool,
                "tipo": "mixto",
                "metodo_efectivo": str ("llamada" | "sms"),
                "llamada": dict,
                "sms": dict,
                "costo_total": int
            }
        """
        logger.info(f"📞📱 [MIXTO] Iniciando envío mixto a {telefono}")
        
        resultado = {
            "success": False,
            "tipo": "mixto",
            "metodo_efectivo": None,
            "llamada": None,
            "sms": None,
            "costo_total": 0
        }
        
        # Primero intentar llamada
        llamada_result = self.enviar_llamada(telefono, mensaje)
        resultado["llamada"] = llamada_result
        
        if llamada_result.get("success") and llamada_result.get("estado") == "contestada":
            resultado["success"] = True
            resultado["costo_total"] = llamada_result.get("costo", 0)
            resultado["metodo_efectivo"] = "llamada"
            logger.info(f"✅ [MIXTO] Llamada exitosa, no se envía SMS")
            return resultado
        
        # Si la llamada no fue contestada, enviar SMS de respaldo
        logger.info(f"📱 [MIXTO] Llamada no contestada, enviando SMS de respaldo")
        sms_result = self.enviar_sms(telefono, f"AVISO: {mensaje}")
        resultado["sms"] = sms_result
        
        if sms_result.get("success"):
            resultado["success"] = True
            resultado["costo_total"] = sms_result.get("costo", 0)
            resultado["metodo_efectivo"] = "sms"
            logger.info(f"✅ [MIXTO] SMS enviado exitosamente")
        else:
            logger.error(f"❌ [MIXTO] Ambos métodos fallaron")
        
        return resultado
    
    def verificar_estado_sms(self, sms_id: str) -> Dict[str, Any]:
        """
        Verifica el estado de un SMS enviado
        
        Args:
            sms_id: ID del SMS
            
        Returns:
            Dict con el estado del SMS
        """
        url = f"{self.sms_report_url}{sms_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ [SMS] Error verificando estado: {str(e)}")
            return {"error": str(e)}
    
    def verificar_estado_llamada(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Verifica el estado de una llamada TTS
        
        Args:
            call_id: ID de la llamada
            
        Returns:
            Dict con el estado de la llamada o None si hay error
        """
        url = f"{self.tts_status_url}{call_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"❌ [LLAMADA] Error verificando estado: {str(e)}")
            return None
    
    def _monitorear_llamada(
        self, 
        call_id: str, 
        max_reintentos: int = 3
    ) -> Dict[str, Any]:
        """
        Monitorea el estado de una llamada hasta que se resuelva
        
        Args:
            call_id: ID de la llamada
            max_reintentos: Número máximo de reintentos
            
        Returns:
            Dict con el resultado del monitoreo:
            {
                "contestada": bool,
                "costo": int,
                "duracion": str,
                "intento": int
            }
        """
        for intento in range(max_reintentos + 1):
            tiempo_espera = 5 + (intento * 5)  # Espera progresiva
            time.sleep(tiempo_espera)
            
            estado = self.verificar_estado_llamada(call_id)
            if estado and "call_records" in estado and estado["call_records"]:
                call_record = estado["call_records"][0]
                status = call_record.get("status", "UNKNOWN")
                
                if status == "ANSWERED":
                    return {
                        "contestada": True,
                        "costo": int(float(call_record.get("cost", 0))),
                        "duracion": call_record.get("duration", "0"),
                        "intento": intento + 1
                    }
                elif status != "UNKNOWN":
                    break  # Estado definitivo (FAILED, NO ANSWER)
        
        return {
            "contestada": False,
            "costo": 0,
            "duracion": "0",
            "intento": max_reintentos
        }


# Instancia global para fácil importación
hablame_service = HablameService()

