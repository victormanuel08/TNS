import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class DeepSeekIntegrator:
    def __init__(self):
        self.api_key = getattr(settings, 'DEEPSEEK_API_KEY', 'sk-f0ba5a27ac694372aa63ee974237a9b2')
        self.base_url = "https://api.deepseek.com/chat/completions"
        self.tono_niño = """
        Eres un asistente muy inteligente que trabaja en una empresa de insumos médico-quirúrgicos.
        Hablas con la curiosidad de un niño pero con conocimiento del ámbito médico.
        
        CONTEXTO:
        - Trabajas en una empresa que vende insumos para hospitales y clínicas
        - Los artículos son materiales médicos, equipos quirúrgicos, insumos de curación
        - Los clientes son médicos, enfermeras, hospitales y clínicas
        - Entiendes la importancia de estos insumos en procedimientos médicos
        
        CARACTERÍSTICAS:
        - Usas lenguaje simple pero técnicamente correcto
        - Te emocionas cuando descubres patrones en los datos médicos
        - Haces preguntas curiosas sobre por qué ciertos insumos son más utilizados
        - Relacionas las ventas con necesidades médicas reales
        - TODOS los valores son en PESOS COLOMBIANOS (COP)
        - NO uses **negritas** ni formato markdown
        
        EJEMPLO DE TONO:
        "¡Interesante! El campo quirúrgico Pharmadrape es el más utilizado...
        Me pregunto si será porque es muy versátil en diferentes procedimientos..."
        """
    
    def generar_respuesta_niño_inteligente(self, contexto_tecnico, tipo_consulta):
        try:
            prompt = self._construir_prompt_niño(contexto_tecnico, tipo_consulta)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": self.tono_niño},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            respuesta = response.json()['choices'][0]['message']['content']
            return self._limpiar_formato(respuesta)
            
        except Exception as e:
            logger.error(f"Error llamando a DeepSeek: {e}")
            return "¡Hola! Soy tu ayudante del área médica. Hoy tengo problemas para conectar con mis fuentes, pero puedo ayudarte con lo que sé."
    
    def _limpiar_formato(self, texto):
        """Elimina formato markdown y caracteres especiales"""
        import re
        # Eliminar negritas
        texto = re.sub(r'\*\*(.*?)\*\*', r'\1', texto)
        # Eliminar cursivas
        texto = re.sub(r'\*(.*?)\*', r'\1', texto)
        # Eliminar código
        texto = re.sub(r'`(.*?)`', r'\1', texto)
        # Eliminar encabezados markdown
        texto = re.sub(r'^#+\s*', '', texto, flags=re.MULTILINE)
        # Normalizar espacios
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto
    
    def _construir_prompt_niño(self, contexto_tecnico, tipo_consulta):
        
        prompts = {
            'historico_articulos_mas_vendidos': f"""
            DATOS DE VENTAS DE INSUMOS MÉDICOS:
            {contexto_tecnico}
            
            Explícalo como un niño que entiende de materiales médicos:
            - Relaciona los artículos con procedimientos médicos reales
            - Pregúntate por qué ciertos insumos son más demandados
            - Considera que estos productos salvan vidas y ayudan en cirugías
            - Usa ejemplos de uso en hospitales o clínicas
            - Todos los valores en PESOS COLOMBIANOS
            - Sin formato markdown
            
            Ejemplo:
            "¡Vaya! El campo quirúrgico Pharmadrape es el más vendido con 358 unidades...
            Eso significa que en muchos procedimientos están usando este material estéril.
            ¿Será porque es muy confiable para mantener la esterilidad en las cirugías?"
            """,
            
            'prediccion_demanda': f"""
            PREDICCIONES PARA INSUMOS MÉDICOS:
            {contexto_tecnico}
            
            Explícalo considerando:
            - Temporadas de cirugías programadas
            - Necesidades de hospitales y clínicas
            - Eventos de salud pública
            - Renovación de inventarios médicos
            """,
            
            'recomendaciones_compras': f"""
            RECOMENDACIONES DE COMPRA PARA INSUMOS MÉDICOS:
            {contexto_tecnico}
            
            Enfócate en:
            - Insumos críticos para emergencias
            - Materiales que no pueden faltar en quirófano
            - Productos con alta rotación en hospitales
            - Necesidades estacionales del sector salud
            """,
            
            'analisis_ventas': f"""
            ANÁLISIS DE VENTAS DE PRODUCTOS MÉDICOS:
            {contexto_tecnico}
            
            Analiza considerando:
            - Patrones de compra de instituciones de salud
            - Tendencia en uso de materiales médicos
            - Relación con eventos de salud pública
            - Comportamiento de diferentes especialidades médicas
            """
        }
        
        prompt_base = f"""
        DATOS DEL SECTOR SALUD:
        {contexto_tecnico}
        
        Eres un niño muy inteligente que creció en una familia de médicos y entiendes 
        la importancia de los insumos médico-quirúrgicos. Explica estos datos mostrando:
        
        - Curiosidad genuina por los patrones médicos
        - Comprensión de que estos productos ayudan a salvar vidas
        - Preguntas inteligentes sobre el uso en procedimientos
        - Relación con necesidades reales de pacientes y médicos
        
        Contexto: Trabajamos con hospitales, clínicas y profesionales de la salud
        que necesitan materiales confiables para sus procedimientos.
        
        Todos los valores en PESOS COLOMBIANOS.
        Sin formato markdown, texto natural.
        """
        
        return prompts.get(tipo_consulta, prompt_base)


def generar_respuesta_hibrida(consulta, datos_tecnicos, tipo_consulta):
    """
    Función wrapper para mantener compatibilidad
    """
    integrator = DeepSeekIntegrator()
    return integrator.generar_respuesta_niño_inteligente(datos_tecnicos, tipo_consulta)