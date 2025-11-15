# sistema_analitico/services/natural_response_orchestrator.py
import logging
from datetime import datetime
import re

from .deepseek_integrator import DeepSeekIntegrator

logger = logging.getLogger(__name__)

class NaturalResponseOrchestrator:
    def __init__(self):
        self.deepseek = DeepSeekIntegrator()
    
    def generar_respuesta_hibrida(self, resultados_tecnicos, tipo_consulta, consulta_original):
        try:
            # ✅ PRIMERO: Verificar si hay datos o no
            if self._no_hay_datos(resultados_tecnicos):
                return self._generar_respuesta_sin_datos(resultados_tecnicos, consulta_original)
            
            # ✅ SEGUNDO: Si hay datos, usar DeepSeek normalmente
            contexto_tecnico = self._formatear_contexto_tecnico(resultados_tecnicos, tipo_consulta)
            
            explicacion_niño = self.deepseek.generar_respuesta_niño_inteligente(
                contexto_tecnico, tipo_consulta
            )
            
            return {
                "consulta_original": consulta_original,
                "explicacion_niño_inteligente": explicacion_niño,
                "datos_tecnicos_completos": resultados_tecnicos
            }
            
        except Exception as e:
            logger.error(f"Error generando respuesta híbrida: {e}")
            return self._generar_respuesta_error(consulta_original, resultados_tecnicos, e)
    
    def _no_hay_datos(self, resultados_tecnicos):
        """Verifica si no hay datos en los resultados"""
        if resultados_tecnicos.get('error'):
            return True
            
        if 'resultados' in resultados_tecnicos:
            if (resultados_tecnicos.get('resultados') == [] and 
                resultados_tecnicos.get('total_articulos', 0) == 0):
                return True
                
        if resultados_tecnicos.get('total_articulos', 0) == 0:
            return True
            
        return False
    
    def _generar_respuesta_sin_datos(self, resultados_tecnicos, consulta_original):
        """Genera respuesta profesional cuando no hay datos"""
        
        # Extraer información del período de la consulta
        periodo_info = self._analizar_periodo_consulta(consulta_original)
        
        # Construir mensaje profesional según el contexto
        if periodo_info['es_futuro']:
            explicacion = (
                f"🔍 **Análisis completado**: No se encontraron ventas registradas "
                f"para el período {periodo_info['descripcion']}. "
                f"\n\n📅 **Nota**: El período consultado es futuro. "
                f"Puedes consultar datos históricos o utilizar nuestras "
                f"herramientas de predicción para estimar ventas futuras."
            )
        else:
            explicacion = (
                f"🔍 **Análisis completado**: No se encontraron ventas registradas "
                f"para el período {periodo_info['descripcion']}. "
                f"\n\n💡 **Sugerencia**: Esto puede deberse a:"
                f"\n• No hay datos para las empresas consultadas en ese período"
                f"\n• Las empresas no tuvieron ventas en esas fechas"
                f"\n• Prueba con un período diferente o verifica la configuración"
            )
        
        # Asegurarnos de que los datos técnicos tengan la estructura correcta
        datos_tecnicos = resultados_tecnicos.copy()
        if 'periodo_consulta' not in datos_tecnicos:
            datos_tecnicos['periodo_consulta'] = periodo_info
        
        return {
            "consulta_original": consulta_original,
            "explicacion_niño_inteligente": explicacion,  # ✅ Ahora es profesional
            "datos_tecnicos_completos": datos_tecnicos
        }
    
    def _generar_respuesta_error(self, consulta_original, resultados_tecnicos, error):
        """Genera respuesta profesional para errores"""
        explicacion = (
            f"⚠️ **Error en el análisis**: No pude procesar completamente tu consulta. "
            f"\n\n🔧 **Detalles técnicos**: {str(error)}"
            f"\n\n💡 **Solución**: Por favor intenta nuevamente o reformula tu pregunta."
        )
        
        return {
            "consulta_original": consulta_original,
            "explicacion_niño_inteligente": explicacion,
            "datos_tecnicos_completos": resultados_tecnicos
        }
    
    def _analizar_periodo_consulta(self, consulta):
        """Analiza el período de la consulta para mensajes más precisos"""
        consulta_lower = consulta.lower()
        ahora = datetime.now()
        
        # Detectar primer semestre 2025
        if 'primer semestre de 2025' in consulta_lower or 'primer semestre 2025' in consulta_lower:
            return {
                'fecha_inicio': '2025-01-01',
                'fecha_fin': '2025-06-30',
                'descripcion': 'primer semestre de 2025',
                'es_futuro': True
            }
        
        # Detectar años futuros
        anios = re.findall(r'20\d{2}', consulta_lower)
        if anios:
            anio = int(anios[0])
            if anio > ahora.year:
                return {
                    'fecha_inicio': f'{anio}-01-01',
                    'fecha_fin': f'{anio}-12-31',
                    'descripcion': f'año {anio}',
                    'es_futuro': True
                }
        
        # Por defecto, asumir período histórico
        return {
            'fecha_inicio': 'Período histórico',
            'fecha_fin': 'Actual',
            'descripcion': 'el período consultado',
            'es_futuro': False
        }
    
    def _formatear_contexto_tecnico(self, resultados_tecnicos, tipo_consulta):
        """Formatea el contexto técnico (mantén tu código existente)"""
        if tipo_consulta == 'recomendaciones_compras':
            return f"""
            RECOMENDACIONES DE COMPRAS:
            - Total artículos: {resultados_tecnicos.get('total_articulos', 0)}
            - Inversión estimada: ${resultados_tecnicos.get('inversion_estimada', 0):,}
            """

        elif 'historico' in str(tipo_consulta):
           
            if 'venta_mas_grande' in str(resultados_tecnicos.get('tipo_consulta', '')):
                venta = resultados_tecnicos.get('venta_mas_grande', {})
                return f"""
                VENTA MÁS GRANDE:
                - Artículo: {venta.get('articulo', 'N/A')}
                - Valor: ${venta.get('valor_total', 0):,}
                - Cantidad: {venta.get('cantidad', 0)}
                - Fecha: {venta.get('fecha', 'N/A')}
                - Clínica: {venta.get('clinica', 'N/A')}
                """

            elif 'articulos_mas_vendidos' in str(resultados_tecnicos.get('tipo_consulta', '')):
                resultados = resultados_tecnicos.get('resultados', [])
                if resultados:
                    top_articulo = resultados[0]
                    return f"""
                    ARTÍCULOS MÁS VENDIDOS:
                    - Artículo más vendido: {top_articulo.get('articulo_nombre', 'N/A')}
                    - Total vendido: {top_articulo.get('total_vendido', 0)} unidades
                    - Valor total: ${top_articulo.get('total_valor', 0):,}
                    """

            elif 'general' in str(resultados_tecnicos.get('tipo_consulta', '')):
                stats = resultados_tecnicos.get('estadisticas', {})
                return f"""
                ESTADÍSTICAS GENERALES:
                - Total registros: {stats.get('total_registros', 0)}
                - Artículos únicos: {stats.get('articulos_unicos', 0)}
                - Valor total: ${stats.get('valor_total', 0):,}
                - Venta máxima: ${stats.get('venta_maxima', 0):,}
                """

        return str(resultados_tecnicos)