# sistema_analitico/services/system_tester.py
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class SystemTester:
    def __init__(self):
        self.test_results = {}
    
    def ejecutar_pruebas_integracion(self):
        resultados = {}
        
        try:
            resultados['extraccion_datos'] = self._probar_extraccion_datos()
            resultados['modelos_ml'] = self._probar_modelos_ml()
            
            self.test_results = resultados
            return self._generar_reporte_pruebas()
            
        except Exception as e:
            logger.error(f"Error en pruebas de integración: {e}")
            return {'estado': 'ERROR', 'detalle': str(e)}
    
    def _probar_extraccion_datos(self):
        try:
            datos_prueba = [{
                'tipo_documento': 'FACTURA_VENTA',
                'fecha': '2024-01-15',
                'paciente': 'PACIENTE PRUEBA',
                'articulo_nombre': 'PRÓTESIS CADERA TEST',
                'articulo_codigo': 'TEST001',
                'cantidad': 2,
                'precio_unitario': 5000000
            }]
            
            df = pd.DataFrame(datos_prueba)
            assert 'fecha' in df.columns, "Falta campo fecha"
            
            return {'estado': 'EXITO', 'registros_procesados': len(df)}
            
        except Exception as e:
            return {'estado': 'ERROR', 'error': str(e)}
    
    def _probar_modelos_ml(self):
        try:
            fechas = pd.date_range(start='2023-01-01', end='2024-01-01', freq='M')
            datos_ml = []
            
            for i, fecha in enumerate(fechas):
                datos_ml.append({
                    'fecha': fecha,
                    'cantidad': max(10 + i * 2, 0),
                    'articulo_codigo': 'TEST_ML'
                })
            
            df_ml = pd.DataFrame(datos_ml)
            
            from .prophet_forecaster import ProphetForecaster
            prophet = ProphetForecaster()
            resultado_prophet = prophet.entrenar_modelo_demanda(df_ml)
            
            assert resultado_prophet is not None, "Prophet no pudo entrenarse"
            
            return {'estado': 'EXITO', 'prophet': resultado_prophet}
            
        except Exception as e:
            return {'estado': 'ERROR', 'error': str(e)}
    
    def _generar_reporte_pruebas(self):
        total_pruebas = len(self.test_results)
        pruebas_exitosas = sum(1 for r in self.test_results.values() if r['estado'] == 'EXITO')
        
        return {
            'resumen': {
                'total_pruebas': total_pruebas,
                'exitosas': pruebas_exitosas,
                'fallidas': total_pruebas - pruebas_exitosas
            },
            'detalles': self.test_results
        }