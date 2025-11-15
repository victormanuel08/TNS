import pandas as pd
from prophet import Prophet
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ProphetForecaster:
    def __init__(self):
        self.model = None
        self.model_info = {}
    
    def entrenar_modelo_demanda(self, df, articulo_codigo=None, frecuencia='ME'):
        try:
            if articulo_codigo:
                df_filtrado = df[df['articulo_codigo'] == articulo_codigo].copy()
            else:
                df_filtrado = df.copy()

            if df_filtrado.empty:
                return None

            if 'cantidad' not in df_filtrado.columns:
                logger.error("DataFrame no tiene columna 'cantidad'")
                logger.error(f"Columnas disponibles: {df_filtrado.columns.tolist()}")
                return None

            df_filtrado['fecha'] = pd.to_datetime(df_filtrado['fecha'])
            df_agrupado = df_filtrado.set_index('fecha').resample(frecuencia).agg({
                'cantidad': 'sum'
            }).reset_index()

            df_prophet = df_agrupado[['fecha', 'cantidad']].rename(
                columns={'fecha': 'ds', 'cantidad': 'y'}
            )

   
            df_prophet['ds'] = df_prophet['ds'].dt.tz_localize(None)

            self.model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                changepoint_prior_scale=0.05
            )

            self.model.fit(df_prophet)

            self.model_info = {
                'articulo_codigo': articulo_codigo,
                'frecuencia': frecuencia,
                'fecha_entrenamiento': datetime.now().isoformat(),
                'datos_entrenamiento': len(df_prophet)
            }

            return self.model_info

        except Exception as e:
            logger.error(f"Error entrenando Prophet: {e}")
            return None
    
    def predecir_demanda(self, periodos_futuro=6, frecuencia='ME'): 
        if not self.model:
            raise ValueError("Modelo no entrenado.")
        
        future = self.model.make_future_dataframe(
            periods=periodos_futuro, 
            freq=frecuencia,  
            include_history=False
        )
        
        forecast = self.model.predict(future)
        
        resultados = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].rename(
            columns={'ds': 'fecha', 'yhat': 'prediccion', 'yhat_lower': 'minimo', 'yhat_upper': 'maximo'}
        )
        
        resultados['prediccion'] = resultados['prediccion'].clip(lower=0)
        resultados['minimo'] = resultados['minimo'].clip(lower=0)
        
        return resultados.to_dict('records')