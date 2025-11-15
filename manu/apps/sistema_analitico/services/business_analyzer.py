import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class BusinessAnalyzer:
    def __init__(self):
        self.reglas_negocio = {
            'implantes_criticos': {
                'categorias': ['IMPLANTE', 'PRÓTESIS', 'CADERA', 'RODILLA'],
                'stock_minimo': 5
            }
        }
    
    def analizar_rentabilidad_procedimientos(self, df):
        try:
            rentabilidad = df.groupby('procedimientos').agg({
                'valor_total': ['sum', 'mean', 'count'],
                'cantidad': 'sum'
            }).reset_index()
            
            rentabilidad.columns = ['procedimiento', 'ingreso_total', 'ingreso_promedio', 
                                  'total_procedimientos', 'total_insumos']
            
            rentabilidad['rentabilidad_por_procedimiento'] = (
                rentabilidad['ingreso_promedio'] / rentabilidad['total_insumos']
            )
            
            return rentabilidad.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error analizando rentabilidad: {e}")
            return []
    
    def identificar_medicos_estrategicos(self, df):
        try:
            analisis_medicos = df.groupby('medico').agg({
                'valor_total': 'sum',
                'cantidad': 'sum',
                'fecha': 'count'
            }).reset_index()
            
            analisis_medicos.columns = ['medico', 'ingreso_total', 'total_insumos', 'total_movimientos']
            
            analisis_medicos['categoria_medico'] = np.where(
                analisis_medicos['ingreso_total'] > analisis_medicos['ingreso_total'].quantile(0.8),
                'ESTRATÉGICO', 'REGULAR'
            )
            
            return analisis_medicos.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error analizando médicos: {e}")
            return []