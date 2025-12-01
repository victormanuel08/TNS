"""
Integrador MLflow para sistema_analitico
Permite registrar modelos, loguear métricas y visualizar predicciones en MLflow UI
Sin romper la funcionalidad existente - funciona como wrapper opcional
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import pandas as pd

logger = logging.getLogger(__name__)

# MLflow es opcional - si no está instalado, el sistema funciona sin él
try:
    import mlflow
    import mlflow.sklearn
    import mlflow.xgboost
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logger.warning("⚠️ MLflow no está instalado. El sistema funcionará sin tracking de MLflow.")


class MLflowIntegrator:
    """
    Integrador MLflow que envuelve MLEngine sin romper funcionalidad existente.
    Si MLflow no está disponible, todas las operaciones son no-ops (no fallan).
    """
    
    def __init__(self, tracking_uri: Optional[str] = None, experiment_name: str = "tnsfull_ml"):
        """
        Inicializa el integrador MLflow
        
        Args:
            tracking_uri: URI del servidor MLflow. Si no se proporciona, se lee de la variable
                         de entorno MLFLOW_TRACKING_URI (default: http://localhost:5000)
            experiment_name: Nombre del experimento en MLflow
        """
        self.mlflow_available = MLFLOW_AVAILABLE
        # Lee dinámicamente desde variable de entorno o usa default
        self.tracking_uri = tracking_uri or os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
        self.experiment_name = experiment_name
        
        if not self.mlflow_available:
            logger.info("📊 MLflow no disponible - operaciones serán no-ops")
            return
        
        try:
            # Configurar tracking URI
            mlflow.set_tracking_uri(self.tracking_uri)
            
            # Crear o obtener experimento
            try:
                experiment = mlflow.get_experiment_by_name(experiment_name)
                if experiment is None:
                    experiment_id = mlflow.create_experiment(experiment_name)
                    logger.info(f"✅ Experimento creado: {experiment_name} (ID: {experiment_id})")
                else:
                    logger.info(f"✅ Experimento encontrado: {experiment_name} (ID: {experiment.experiment_id})")
            except Exception as e:
                logger.warning(f"⚠️ Error configurando experimento MLflow: {e}")
                self.mlflow_available = False
                
        except Exception as e:
            logger.warning(f"⚠️ Error inicializando MLflow: {e}")
            self.mlflow_available = False
    
    def log_model_training(
        self,
        modelo_id: str,
        nit_empresa: str,
        modelo_data: Dict[str, Any],
        resultados_entrenamiento: Dict[str, Any],
        df_entrenamiento: pd.DataFrame
    ) -> Optional[str]:
        """
        Registra el entrenamiento de un modelo en MLflow
        
        Returns:
            run_id del experimento o None si MLflow no está disponible
        """
        if not self.mlflow_available:
            return None
        
        try:
            mlflow.set_experiment(self.experiment_name)
            
            with mlflow.start_run(run_name=f"entrenamiento_{modelo_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                # Log parámetros
                mlflow.log_param("modelo_id", modelo_id)
                mlflow.log_param("nit_empresa", nit_empresa)
                mlflow.log_param("fecha_entrenamiento", modelo_data.get('fecha_entrenamiento', ''))
                mlflow.log_param("filas_entrenamiento", modelo_data.get('filas_entrenamiento', 0))
                mlflow.log_param("total_articulos", modelo_data.get('metadata', {}).get('total_articulos', 0))
                
                # Log métricas de Prophet
                if 'prophet' in resultados_entrenamiento:
                    prophet_metrics = resultados_entrenamiento['prophet']
                    mlflow.log_metric("prophet_datos_entrenamiento", prophet_metrics.get('datos_entrenamiento', 0))
                
                # Log métricas de XGBoost
                if 'xgboost' in resultados_entrenamiento:
                    xgboost_metrics = resultados_entrenamiento['xgboost']
                    mlflow.log_metric("xgboost_mae", xgboost_metrics.get('mae', 0))
                    mlflow.log_metric("xgboost_r2", xgboost_metrics.get('r2_score', 0))
                    mlflow.log_metric("xgboost_rmse", xgboost_metrics.get('rmse', 0))
                
                # Log modelos
                if 'prophet_model' in modelo_data and modelo_data['prophet_model'] is not None:
                    try:
                        # Prophet no es directamente compatible con mlflow, guardamos metadata
                        mlflow.log_dict({
                            'prophet_trained': True,
                            'prophet_info': modelo_data.get('resultados_entrenamiento', {}).get('prophet', {})
                        }, "prophet_model_info.json")
                    except Exception as e:
                        logger.warning(f"⚠️ Error logueando Prophet: {e}")
                
                if 'xgboost_predictor_completo' in modelo_data:
                    try:
                        xgboost_predictor = modelo_data['xgboost_predictor_completo']
                        if hasattr(xgboost_predictor, 'model') and xgboost_predictor.model is not None:
                            mlflow.xgboost.log_model(
                                xgboost_predictor.model,
                                "xgboost_model",
                                registered_model_name=f"xgboost_{nit_empresa}"
                            )
                    except Exception as e:
                        logger.warning(f"⚠️ Error logueando XGBoost: {e}")
                
                # Log dataset de entrenamiento (sample)
                if df_entrenamiento is not None and not df_entrenamiento.empty:
                    try:
                        sample_df = df_entrenamiento.head(1000)  # Sample para no sobrecargar
                        # Guardar como artefacto CSV
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
                            sample_df.to_csv(tmp.name, index=False)
                            mlflow.log_artifact(tmp.name, "training_data_sample.csv")
                            os.unlink(tmp.name)  # Limpiar archivo temporal
                    except Exception as e:
                        logger.warning(f"⚠️ Error logueando dataset: {e}")
                
                run_id = mlflow.active_run().info.run_id
                logger.info(f"✅ Modelo registrado en MLflow - Run ID: {run_id}")
                return run_id
                
        except Exception as e:
            logger.error(f"❌ Error registrando modelo en MLflow: {e}")
            return None
    
    def log_prediction(
        self,
        modelo_id: str,
        nit_empresa: str,
        tipo_prediccion: str,
        predicciones: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> Optional[str]:
        """
        Registra una predicción en MLflow para visualización
        
        Args:
            modelo_id: ID del modelo usado
            nit_empresa: NIT de la empresa
            tipo_prediccion: 'demanda' o 'recomendaciones'
            predicciones: Lista de predicciones realizadas
            metadata: Metadata adicional (meses, predictor usado, etc.)
        
        Returns:
            run_id del experimento o None
        """
        if not self.mlflow_available:
            return None
        
        try:
            mlflow.set_experiment(self.experiment_name)
            
            run_name = f"prediccion_{tipo_prediccion}_{nit_empresa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            with mlflow.start_run(run_name=run_name):
                # Log parámetros
                mlflow.log_param("modelo_id", modelo_id)
                mlflow.log_param("nit_empresa", nit_empresa)
                mlflow.log_param("tipo_prediccion", tipo_prediccion)
                mlflow.log_param("predictor_principal", metadata.get('predictor_principal', 'unknown'))
                mlflow.log_param("meses_proyeccion", metadata.get('meses', 6))
                mlflow.log_param("total_predicciones", len(predicciones))
                
                # Log métricas agregadas
                if predicciones:
                    if tipo_prediccion == 'demanda':
                        demandas = [p.get('prediccion', 0) for p in predicciones if isinstance(p, dict)]
                        if demandas:
                            mlflow.log_metric("demanda_total_predicha", sum(demandas))
                            mlflow.log_metric("demanda_promedio", sum(demandas) / len(demandas))
                            mlflow.log_metric("demanda_maxima", max(demandas))
                            mlflow.log_metric("demanda_minima", min(demandas))
                    
                    elif tipo_prediccion == 'recomendaciones':
                        cantidades = [r.get('cantidad_recomendada', 0) for r in predicciones if isinstance(r, dict)]
                        inversiones = [r.get('inversion_estimada', 0) for r in predicciones if isinstance(r, dict)]
                        if cantidades:
                            mlflow.log_metric("total_articulos_recomendados", len(predicciones))
                            mlflow.log_metric("cantidad_total_recomendada", sum(cantidades))
                        if inversiones:
                            mlflow.log_metric("inversion_total_estimada", sum(inversiones))
                
                # Log predicciones como tabla
                try:
                    if predicciones:
                        df_predicciones = pd.DataFrame(predicciones)
                        # Guardar como artefacto CSV
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
                            df_predicciones.to_csv(tmp.name, index=False)
                            mlflow.log_artifact(tmp.name, f"{tipo_prediccion}_results.csv")
                            os.unlink(tmp.name)  # Limpiar archivo temporal
                except Exception as e:
                    logger.warning(f"⚠️ Error logueando tabla de predicciones: {e}")
                
                # Log metadata completa
                mlflow.log_dict(metadata, "prediction_metadata.json")
                
                run_id = mlflow.active_run().info.run_id
                logger.info(f"✅ Predicción registrada en MLflow - Run ID: {run_id}")
                logger.info(f"📊 Ver en MLflow UI: {self.tracking_uri}/#/experiments/0/runs/{run_id}")
                return run_id
                
        except Exception as e:
            logger.error(f"❌ Error registrando predicción en MLflow: {e}")
            return None
    
    def get_experiment_runs(self, nit_empresa: Optional[str] = None, limit: int = 100):
        """
        Obtiene los runs del experimento (para consultas desde el frontend)
        
        Returns:
            Lista de runs o None si MLflow no está disponible
        """
        if not self.mlflow_available:
            return None
        
        try:
            client = MlflowClient(tracking_uri=self.tracking_uri)
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            
            if experiment is None:
                return []
            
            runs = client.search_runs(
                experiment_ids=[experiment.experiment_id],
                max_results=limit,
                order_by=["start_time DESC"]
            )
            
            runs_data = []
            for run in runs:
                run_data = {
                    'run_id': run.info.run_id,
                    'run_name': run.data.tags.get('mlflow.runName', ''),
                    'start_time': run.info.start_time,
                    'status': run.info.status,
                    'params': run.data.params,
                    'metrics': run.data.metrics,
                    'tags': run.data.tags
                }
                
                # Filtrar por NIT si se especifica
                if nit_empresa and run_data['params'].get('nit_empresa') != nit_empresa:
                    continue
                
                runs_data.append(run_data)
            
            return runs_data
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo runs de MLflow: {e}")
            return None

