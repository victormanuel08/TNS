import pandas as pd
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)

class InventoryOptimizer:
    def __init__(self, nivel_servicio=0.95):
        self.nivel_servicio = nivel_servicio
    
    def clasificar_abc_xyz(self, df):
        try:
            articulos_agg = df.groupby(['articulo_codigo', 'articulo_nombre']).agg({
                'valor_total': 'sum',
                'cantidad': ['sum', 'std'],
                'fecha': 'count'
            }).reset_index()
            
            articulos_agg.columns = ['articulo_codigo', 'articulo_nombre', 'valor_total', 
                                   'cantidad_total', 'std_cantidad', 'frecuencia']
            
            articulos_agg = articulos_agg.sort_values('valor_total', ascending=False)
            articulos_agg['valor_acumulado'] = articulos_agg['valor_total'].cumsum()
            articulos_agg['porcentaje_acumulado'] = articulos_agg['valor_acumulado'] / articulos_agg['valor_total'].sum()
            
            articulos_agg['clase_abc'] = np.where(
                articulos_agg['porcentaje_acumulado'] <= 0.8, 'A',
                np.where(articulos_agg['porcentaje_acumulado'] <= 0.95, 'B', 'C')
            )
            
            articulos_agg['cv'] = articulos_agg['std_cantidad'] / articulos_agg['cantidad_total']
            articulos_agg['clase_xyz'] = np.where(
                articulos_agg['cv'] <= 0.5, 'X',
                np.where(articulos_agg['cv'] <= 1.0, 'Y', 'Z')
            )
            
            articulos_agg['clase_abc_xyz'] = articulos_agg['clase_abc'] + articulos_agg['clase_xyz']
            
            return articulos_agg.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error en clasificación ABC/XYZ: {e}")
            return []
    
    def calcular_stock_optimo(self, df, lead_time_dias=30):
        try:
            resultados = []
            
            for articulo in df['articulo_codigo'].unique():
                df_articulo = df[df['articulo_codigo'] == articulo].copy()
                
                if len(df_articulo) < 10:
                    continue
                
                demanda_diaria = df_articulo.groupby('fecha')['cantidad'].sum()
                demanda_promedio = demanda_diaria.mean()
                desviacion_demanda = demanda_diaria.std()
                
                demanda_lead_time = demanda_promedio * lead_time_dias
                desviacion_lead_time = desviacion_demanda * np.sqrt(lead_time_dias)
                
                z_score = stats.norm.ppf(self.nivel_servicio)
                punto_reorden = demanda_lead_time + z_score * desviacion_lead_time
                stock_seguridad = z_score * desviacion_lead_time
                
                resultados.append({
                    'articulo_codigo': articulo,
                    'articulo_nombre': df_articulo['articulo_nombre'].iloc[0],
                    'demanda_promedio_diaria': round(demanda_promedio, 2),
                    'punto_reorden': round(punto_reorden),
                    'stock_seguridad': round(stock_seguridad)
                })
            
            return resultados
            
        except Exception as e:
            logger.error(f"Error calculando stock óptimo: {e}")
            return []