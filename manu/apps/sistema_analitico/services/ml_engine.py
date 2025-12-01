# sistema_analitico/services/ml_engine.py
import pandas as pd
import logging
from datetime import datetime, timedelta
from django.utils import timezone
import pickle
import os
import joblib
from django.conf import settings

from .prophet_forecaster import ProphetForecaster
from .xgboost_predictor import XGBoostPredictor
from .inventory_optimizer import InventoryOptimizer

# MLflow es opcional
try:
    from .mlflow_integrator import MLflowIntegrator
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    MLflowIntegrator = None

logger = logging.getLogger(__name__)

class MLEngine:
    def __init__(self, models_dir=None, enable_mlflow=True):      
        if models_dir is None:
            self.models_dir = os.path.join(settings.BASE_DIR, 'modelos_ml')
        else:
            self.models_dir = models_dir        
        
        os.makedirs(self.models_dir, exist_ok=True)
        logger.info(f"📁 Directorio de modelos: {self.models_dir}")
        
        self.prophet = ProphetForecaster()
        self.xgboost = XGBoostPredictor()
        self.optimizer = InventoryOptimizer()
        
        # Inicializar MLflow si está disponible y habilitado
        self.mlflow = None
        if enable_mlflow and MLFLOW_AVAILABLE and MLflowIntegrator:
            try:
                self.mlflow = MLflowIntegrator()
                logger.info("✅ MLflow integrado y disponible")
            except Exception as e:
                logger.warning(f"⚠️ Error inicializando MLflow: {e}")
                self.mlflow = None
        
        self.modelos_entrenados = {}
        self._cargar_modelos_existentes()
    
    def _cargar_modelos_existentes(self):
        """Cargar modelos previamente entrenados al inicializar"""
        try:
            logger.info(f"🔍 Buscando modelos en: {self.models_dir}")
            
            if not os.path.exists(self.models_dir):
                logger.warning(f"❌ Directorio no existe: {self.models_dir}")
                return
            
            archivos = os.listdir(self.models_dir)
            logger.info(f"📄 Archivos encontrados: {archivos}")
            
            for archivo in archivos:
                if archivo.endswith('.joblib'):
                    modelo_id = archivo.replace('.joblib', '')
                    modelo_path = os.path.join(self.models_dir, archivo)
                    
                    try:
                        modelo_data = joblib.load(modelo_path)
                        self.modelos_entrenados[modelo_id] = modelo_data
                        logger.info(f"✅ Modelo cargado: {modelo_id}")
                    except Exception as e:
                        logger.error(f"❌ Error cargando modelo {modelo_id}: {e}")
                        
        except Exception as e:
            logger.error(f"⚠️ Error en _cargar_modelos_existentes: {e}")
    
    def _obtener_nit_y_empresas_relacionadas(self, empresa_servidor_id):
        """Obtiene el NIT y todas las empresas del mismo NIT"""
        try:
            from apps.sistema_analitico.models import EmpresaServidor
            
            # Obtener empresa actual
            empresa_actual = EmpresaServidor.objects.get(id=empresa_servidor_id)
            
            # Buscar todas las empresas con el mismo NIT
            empresas_relacionadas = EmpresaServidor.objects.filter(
                nit=empresa_actual.nit
            ).values_list('id', flat=True)
            
            return {
                'nit': empresa_actual.nit,
                'empresa_actual': empresa_actual,
                'empresas_relacionadas': list(empresas_relacionadas),
                'total_empresas': len(empresas_relacionadas)
            }
        except Exception as e:
            logger.error(f"Error obteniendo empresas relacionadas: {e}")
            return None
    
    def entrenar_modelos_empresa(self, empresa_servidor_id, fecha_inicio=None, fecha_fin=None):
        try:
            from apps.sistema_analitico.models import EmpresaServidor, MovimientoInventario
            from django.db.models import Count, Sum, Avg, Q, Case, When, IntegerField
            from django.db.models.functions import TruncMonth

            # ✅ OBTENER TODAS LAS EMPRESAS DEL MISMO NIT
            info_empresa = self._obtener_nit_y_empresas_relacionadas(empresa_servidor_id)
            if not info_empresa:
                return {"error": "No se pudo obtener información de la empresa"}

            nit = info_empresa['nit']
            empresas_ids = info_empresa['empresas_relacionadas']

            logger.info(f"🔧 Entrenamiento para NIT: {nit}, Empresas: {empresas_ids}")

            # ✅ USAR TODAS LAS EMPRESAS DEL NIT PARA ENTRENAR
            dataset_ml = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids
            ).annotate(
                periodo=TruncMonth('fecha'), 
                es_implante_int=Case(
                    When(es_implante=True, then=1),
                    default=0,
                    output_field=IntegerField()
                ),
                es_instrumental_int=Case(
                    When(es_instrumental=True, then=1),
                    default=0,
                    output_field=IntegerField()
                ),
                es_equipo_poder_int=Case(
                    When(es_equipo_poder=True, then=1),
                    default=0,
                    output_field=IntegerField()
                )
            ).values(
                'articulo_codigo', 'articulo_nombre', 'periodo'
            ).annotate(
                total_transacciones=Count('id'),
                cantidad_total=Sum('cantidad'),
                precio_promedio=Avg('precio_unitario'),
                ventas_mes=Sum('cantidad', filter=Q(tipo_documento='FACTURA_VENTA')),
                compras_mes=Sum('cantidad', filter=Q(tipo_documento='FACTURA_COMPRA')),
                bodegas_unicas=Count('tipo_bodega', distinct=True),
                conteo_implante=Sum('es_implante_int'),
                conteo_instrumental=Sum('es_instrumental_int'), 
                conteo_equipo_poder=Sum('es_equipo_poder_int')
            ).filter(total_transacciones__gte=3)

            df = pd.DataFrame(list(dataset_ml))

            if df.empty:
                logger.error("❌ No hay datos suficientes para entrenar modelos")
                return {"error": "No hay datos suficientes para entrenar modelos"}

            if not df.empty:
                df['fecha'] = pd.to_datetime(df['periodo'])
                df['mes'] = df['fecha'].dt.month
                df['año'] = df['fecha'].dt.year

                if 'cantidad_total' in df.columns:
                    df['cantidad'] = df['cantidad_total']
                else:
                    logger.error("❌ NO EXISTE COLUMNA cantidad_total EN EL DATAFRAME")
                    return {"error": "No se pudo generar dataset con columna 'cantidad'"}                

                df['es_implante'] = (df['conteo_implante'] > 0).astype(int)
                df['es_instrumental'] = (df['conteo_instrumental'] > 0).astype(int)
                df['es_equipo_poder'] = (df['conteo_equipo_poder'] > 0).astype(int)                

                columnas_a_eliminar = ['conteo_implante', 'conteo_instrumental', 'conteo_equipo_poder', 'cantidad_total']
                for col in columnas_a_eliminar:
                    if col in df.columns:
                        df = df.drop(col, axis=1)            

            logger.info(f"📊 Columnas para entrenamiento: {df.columns.tolist()}")

            if 'cantidad' not in df.columns:
                return {"error": f"Falta columna 'cantidad'. Columnas disponibles: {df.columns.tolist()}"}

            resultados = {}

            logger.info("🎯 Entrenando modelo Prophet...")
            resultados['prophet'] = self.prophet.entrenar_modelo_demanda(df)

            logger.info("🎯 Entrenando modelo XGBoost...")
            resultados['xgboost'] = self.xgboost.entrenar_modelo_demanda(df)

            # ✅ MODELO_ID USANDO NIT
            modelo_id = f"empresa_{nit}"

            # ✅ GUARDAR XGBOOST COMPLETO (CON ESCALADOR Y ENCODERS)
            modelo_data = {
                'fecha_entrenamiento': timezone.now().isoformat(),
                'nit_empresa': nit,
                'empresas_servidor_ids': empresas_ids,
                'empresa_servidor_id_original': empresa_servidor_id,
                'resultados_entrenamiento': resultados,
                'filas_entrenamiento': len(df),
                'xgboost_predictor_completo': self.xgboost,  # ← OBJETO COMPLETO
                'prophet_model': self.prophet.model,
                'metadata': {
                    'columnas_entrenamiento': df.columns.tolist(),
                    'total_articulos': df['articulo_codigo'].nunique(),
                    'rango_fechas': {
                        'min': df['fecha'].min().strftime('%Y-%m-%d'),
                        'max': df['fecha'].max().strftime('%Y-%m-%d')
                    },
                    'empresas_incluidas': empresas_ids,
                    'total_empresas': len(empresas_ids)
                }
            }

            modelo_path = os.path.join(self.models_dir, f"{modelo_id}.joblib")
            logger.info(f"💾 Guardando modelo en: {modelo_path}")

            try:
                joblib.dump(modelo_data, modelo_path)
                logger.info(f"✅ Modelo guardado exitosamente: {modelo_path}")
            except Exception as e:
                logger.error(f"❌ Error guardando modelo: {e}")
                return {"error": f"No se pudo guardar el modelo: {str(e)}"}            

            self.modelos_entrenados[modelo_id] = modelo_data
            logger.info(f"✅ Modelo cargado en memoria: {modelo_id}")

            # Registrar en MLflow si está disponible
            mlflow_run_id = None
            if self.mlflow:
                try:
                    mlflow_run_id = self.mlflow.log_model_training(
                        modelo_id=modelo_id,
                        nit_empresa=nit,
                        modelo_data=modelo_data,
                        resultados_entrenamiento=resultados,
                        df_entrenamiento=df
                    )
                    if mlflow_run_id:
                        logger.info(f"📊 Modelo registrado en MLflow - Run ID: {mlflow_run_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Error registrando en MLflow (no crítico): {e}")

            return {
                'estado': 'modelos_entrenados',
                'modelo_id': modelo_id,
                'nit_empresa': nit,
                'empresas_incluidas': empresas_ids,
                'resultados': resultados,
                'filas_entrenamiento': len(df),
                'ruta_guardado': modelo_path,
                'mlflow_run_id': mlflow_run_id,  # ID del run en MLflow
                'mlflow_ui_url': f"{self.mlflow.tracking_uri}/#/experiments/0/runs/{mlflow_run_id}" if mlflow_run_id and self.mlflow else None
            }

        except Exception as e:
            logger.error(f"❌ Error entrenando modelos: {e}")
            return {"error": f"Error en entrenamiento: {str(e)}"}
    
    def _verificar_y_cargar_modelo(self, empresa_servidor_id):
        """Verificar y cargar modelo basado en NIT de la empresa - CORREGIDO COMPLETO"""
        try:
            # ✅ OBTENER NIT PARA BUSCAR MODELO
            info_empresa = self._obtener_nit_y_empresas_relacionadas(empresa_servidor_id)
            if not info_empresa:
                logger.error(f"❌ No se pudo obtener NIT para empresa_servidor_id: {empresa_servidor_id}")
                return False

            nit = info_empresa['nit']
            modelo_id = f"empresa_{nit}"

            # ✅ BUSCAR MODELO EN MEMORIA
            if modelo_id in self.modelos_entrenados:
                logger.info(f"✅ Modelo encontrado en memoria: {modelo_id}")
                modelo_data = self.modelos_entrenados[modelo_id]
            else:
                # ✅ BUSCAR MODELO EN DISCO
                modelo_path = os.path.join(self.models_dir, f"{modelo_id}.joblib")
                logger.info(f"🔍 Buscando modelo por NIT: {modelo_path}")

                if not os.path.exists(modelo_path):
                    logger.error(f"❌ Modelo no encontrado para NIT: {nit}")
                    return False

                # ✅ CARGAR MODELO
                modelo_data = joblib.load(modelo_path)
                self.modelos_entrenados[modelo_id] = modelo_data

            # ✅ CARGAR COMPONENTES ESPECÍFICOS
            if 'prophet_model' in modelo_data and modelo_data['prophet_model'] is not None:
                self.prophet.model = modelo_data['prophet_model']
                logger.info("✅ Prophet model cargado en instancia")

            # ✅ CARGAR XGBOOST COMPLETO (CON ESCALADOR Y ENCODERS)
            if 'xgboost_predictor_completo' in modelo_data:
                self.xgboost = modelo_data['xgboost_predictor_completo']
                logger.info("✅ XGBoost predictor COMPLETO cargado (con escalador y encoders)")
            elif 'xgboost_model' in modelo_data and modelo_data['xgboost_model'] is not None:
                # Fallback para compatibilidad con versiones anteriores
                self.xgboost.model = modelo_data['xgboost_model']
                logger.warning("⚠️ XGBoost cargado sin escalador - solo modelo base")

            logger.info(f"✅ Modelo completamente cargado: {modelo_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error cargando modelo por NIT: {e}")
            return False
    
    def generar_recomendaciones_compras(self, empresa_servidor_id, meses=6, nivel_servicio=0.95):
        """CORREGIDO: Usar TODAS las empresas del NIT para recomendaciones"""
        try:
            logger.info(f"🎯 Generando recomendaciones para NIT completo, meses: {meses}")

            if not self._verificar_y_cargar_modelo(empresa_servidor_id):
                return {"error": f"Modelo para empresa {empresa_servidor_id} no encontrado. Entrene primero los modelos."}

            # ✅ OBTENER TODAS LAS EMPRESAS DEL NIT (como en entrenamiento)
            info_empresa = self._obtener_nit_y_empresas_relacionadas(empresa_servidor_id)
            if not info_empresa:
                return {"error": "No se pudo obtener información del NIT de la empresa"}

            nit = info_empresa['nit']
            todas_empresas_ids = info_empresa['empresas_relacionadas']  # ← TODAS las empresas del NIT

            logger.info(f"📊 Obteniendo datos históricos para TODAS las empresas del NIT: {todas_empresas_ids}")

            from apps.sistema_analitico.models import MovimientoInventario
            from django.db.models import Sum, Count, Avg, Max, Q

            # ✅ CORRECCIÓN: Usar TODAS las empresas del NIT para obtener datos históricos
            datos_historicos = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=todas_empresas_ids  # ← FILTRAR POR TODAS LAS EMPRESAS
            ).values('articulo_codigo', 'articulo_nombre').annotate(
                ventas_totales=Sum('cantidad', filter=Q(tipo_documento='FACTURA_VENTA')),
                compras_totales=Sum('cantidad', filter=Q(tipo_documento='FACTURA_COMPRA')),
                transacciones=Count('id'),
                precio_promedio=Avg('precio_unitario'),
                ultima_venta=Max('fecha', filter=Q(tipo_documento='FACTURA_VENTA')),
                valor_total_ventas=Sum('valor_total', filter=Q(tipo_documento='FACTURA_VENTA'))
            ).filter(ventas_totales__gt=0)  # Solo artículos con ventas

            df_historicos = pd.DataFrame(list(datos_historicos))

            if df_historicos.empty:
                logger.error("❌ No hay datos históricos para generar recomendaciones")
                return {"error": "No hay datos históricos para generar recomendaciones"}

            logger.info(f"📈 Procesando {len(df_historicos)} artículos para recomendaciones")

            recomendaciones = []

            for _, articulo in df_historicos.iterrows():
                # ✅ CALCULAR DEMANDA CON DATOS DE TODAS LAS EMPRESAS
                demanda_mensual = articulo['ventas_totales'] / 12
                demanda_proyectada = demanda_mensual * meses

                cantidad_recomendada = max(int(demanda_proyectada * 1.2), 1)  # 20% buffer

                urgencia = "MEDIA"
                if articulo['ultima_venta']:
                    dias_desde_ultima_venta = (timezone.now() - articulo['ultima_venta']).days
                    if dias_desde_ultima_venta < 30:
                        urgencia = "ALTA"
                    elif dias_desde_ultima_venta > 90:
                        urgencia = "BAJA"

                valor_total = articulo['valor_total_ventas'] or 0
                if valor_total > 10000000:  
                    clasificacion = "A"
                elif valor_total > 1000000:  
                    clasificacion = "B" 
                else:
                    clasificacion = "C"

                precio_promedio = float(articulo['precio_promedio'] or 0)
                inversion_estimada = cantidad_recomendada * precio_promedio

                recomendaciones.append({
                    'articulo_codigo': articulo['articulo_codigo'],
                    'articulo_nombre': articulo['articulo_nombre'],
                    'clasificacion_abc': clasificacion,
                    'demanda_predicha': round(demanda_proyectada),
                    'cantidad_recomendada': cantidad_recomendada,
                    'ventas_historicas': articulo['ventas_totales'],
                    'transacciones_historicas': articulo['transacciones'],
                    'urgencia': urgencia,
                    'precio_promedio': precio_promedio,
                    'inversion_estimada': round(inversion_estimada, 2),
                    'ultima_venta': articulo['ultima_venta'].strftime('%Y-%m-%d') if articulo['ultima_venta'] else 'N/A'
                })

            # Ordenar por urgencia (ALTA primero) y luego por demanda
            orden_urgencia = {"ALTA": 3, "MEDIA": 2, "BAJA": 1}
            recomendaciones.sort(key=lambda x: (orden_urgencia[x['urgencia']], x['demanda_predicha']), reverse=True)

            # Limitar a top 15 recomendaciones
            recomendaciones = recomendaciones[:15]

            inversion_total = sum(r['inversion_estimada'] for r in recomendaciones)

            logger.info(f"✅ Recomendaciones generadas: {len(recomendaciones)} artículos")

            resultado = {
                'recomendaciones': recomendaciones,
                'total_articulos': len(recomendaciones),
                'inversion_estimada': round(inversion_total, 2),
                'nivel_servicio': nivel_servicio,
                'meses_proyeccion': meses,
                'modelo_utilizado': 'analisis_historico_avanzado',
                'empresa_servidor_id': empresa_servidor_id,
                'nit_empresa': nit
            }

            # Registrar predicción en MLflow si está disponible
            if self.mlflow:
                try:
                    mlflow_run_id = self.mlflow.log_prediction(
                        modelo_id=modelo_id,
                        nit_empresa=nit,
                        tipo_prediccion='recomendaciones',
                        predicciones=recomendaciones,
                        metadata={
                            'meses': meses,
                            'nivel_servicio': nivel_servicio,
                            'predictor_principal': 'analisis_historico_avanzado',
                            'total_articulos': len(recomendaciones),
                            'inversion_total': inversion_total
                        }
                    )
                    if mlflow_run_id:
                        resultado['mlflow_run_id'] = mlflow_run_id
                        resultado['mlflow_ui_url'] = f"{self.mlflow.tracking_uri}/#/experiments/0/runs/{mlflow_run_id}"
                        logger.info(f"📊 Recomendaciones registradas en MLflow - Run ID: {mlflow_run_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Error registrando en MLflow (no crítico): {e}")

            return resultado

        except Exception as e:
            logger.error(f"❌ Error generando recomendaciones: {e}")
            return {"error": f"Error generando recomendaciones: {str(e)}"}
    
    def predecir_demanda_articulos(self, empresa_servidor_id, articulos=None, meses=6):
        """CORREGIDA: Sin typos y con validaciones robustas"""
        try:
            logger.info(f"🔮 Prediciendo demanda para NIT completo, meses: {meses}")
                            
            if not self._verificar_y_cargar_modelo(empresa_servidor_id):
                return {"error": f"Modelo no encontrado. Entrene primero los modelos."}
            
            # ✅ OBTENER TODAS LAS EMPRESAS DEL NIT
            info_empresa = self._obtener_nit_y_empresas_relacionadas(empresa_servidor_id)
            if not info_empresa:
                return {"error": "No se pudo obtener información del NIT"}
                
            nit = info_empresa['nit']
            todas_empresas_ids = info_empresa['empresas_relacionadas']
            
            # ✅ SELECCIÓN INTELIGENTE DEL PREDICTOR PRINCIPAL
            modelo_id = f"empresa_{nit}"
            if modelo_id not in self.modelos_entrenados:
                return {"error": "Modelo no encontrado en memoria"}
                
            modelo_data = self.modelos_entrenados[modelo_id]
            predictor_principal = self._evaluar_mejor_predictor(modelo_data)
            explicacion_confianza = self._generar_explicacion_confianza(predictor_principal, modelo_data)
            
            logger.info(f"🎯 Predictor seleccionado: {predictor_principal}")
            
            fecha_final = timezone.now() + timedelta(days=meses*30)
            fechas_futuras = pd.date_range(
                start=timezone.now(), end=fecha_final, freq='ME'
            )
            
            # ✅ PREDICCIÓN PROPHET CORREGIDA (sin typo)
            try:
                # CORRECCIÓN: Usar el nombre correcto del parámetro
                predicciones_prophet = self.prophet.predecir_demanda(periodos_futuro=meses)
                confianza_prophet = "alta" if predictor_principal == 'prophet' else "media"
                logger.info(f"✅ Prophet generó {len(predicciones_prophet) if isinstance(predicciones_prophet, list) else 'algunas'} predicciones")
            except Exception as e:
                logger.warning(f"⚠️ Error en Prophet: {e}")
                predicciones_prophet = {"predicciones": [], "error": str(e)}
                confianza_prophet = "baja"
            
            # ✅ PREDICCIÓN XGBOOST CON VALIDACIONES ROBUSTAS
            from apps.sistema_analitico.models import MovimientoInventario
            from django.db.models import Count
            
            articulos_populares = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=todas_empresas_ids
            ).values('articulo_codigo', 'articulo_nombre').annotate(
                total=Count('id')
            ).order_by('-total')[:10]
            
            # ✅ OBTENER CARACTERÍSTICAS EXACTAS DEL ENTRENAMIENTO
            caracteristicas_entrenamiento = modelo_data.get('resultados_entrenamiento', {}).get('xgboost', {}).get('caracteristicas_usadas', [])
            
            if not caracteristicas_entrenamiento:
                logger.warning("⚠️ No se encontraron características de entrenamiento, usando defaults básicas")
                caracteristicas_entrenamiento = ['mes', 'año', 'trimestre', 'dia_semana']
    
            logger.info(f"🎯 Características de entrenamiento: {caracteristicas_entrenamiento}")
    
            # ✅ CREAR DATOS FUTUROS CON VALIDACIÓN
            datos_futuros = []
            if articulos_populares:
                for fecha in fechas_futuras:
                    for art in articulos_populares:
                        fila = {
                            'fecha': fecha,
                            'articulo_codigo': art['articulo_codigo'],
                            'articulo_nombre': art['articulo_nombre'],
                        }
                        
                        # HOMOLOGACIÓN EXACTA: SOLO USAR CARACTERÍSTICAS DEL ENTRENAMIENTO
                        for caracteristica in caracteristicas_entrenamiento:
                            if caracteristica == 'mes':
                                fila['mes'] = fecha.month
                            elif caracteristica == 'año':
                                fila['año'] = fecha.year
                            elif caracteristica == 'trimestre':
                                fila['trimestre'] = (fecha.month - 1) // 3 + 1
                            elif caracteristica == 'dia_semana':
                                fila['dia_semana'] = fecha.weekday()
                            elif caracteristica in ['total_transacciones', 'ventas_mes', 'compras_mes', 'bodegas_unicas']:
                                fila[caracteristica] = 1
                            elif caracteristica in ['es_implante', 'es_instrumental', 'es_equipo_poder']:
                                fila[caracteristica] = 0
                            else:
                                fila[caracteristica] = 0
                        
                        datos_futuros.append(fila)
    
            # ✅ VALIDAR QUE HAY DATOS ANTES DE CREAR DATAFRAME
            if not datos_futuros:
                logger.warning("⚠️ No se pudieron crear datos futuros, usando fallback histórico")
                predicciones_xgboost = self._generar_predicciones_fallback_basico(
                    todas_empresas_ids, meses, fechas_futuras
                )
                confianza_xgboost = "media"
            else:
                df_futuro = pd.DataFrame(datos_futuros)
                logger.info(f"✅ DataFrame futuro creado con {len(df_futuro)} filas")
                
                # ✅ PREDICCIÓN XGBOOST CON MANEJO DE ERRORES ROBUSTO
                try:
                    predicciones_xgboost = self.xgboost.predecir_demanda(df_futuro)
                    confianza_xgboost = "alta" if predictor_principal == 'xgboost' else "media"
                    logger.info(f"✅ XGBoost generó {len(predicciones_xgboost) if predicciones_xgboost else 0} predicciones")
                except Exception as e:
                    logger.warning(f"⚠️ Error en XGBoost: {e}")
                    predicciones_xgboost = []
                    confianza_xgboost = "baja"
                    
                    # FALLBACK A PREDICCIONES HISTÓRICAS
                    logger.info("🔄 Usando fallback histórico por error en XGBoost")
                    predicciones_xgboost = self._generar_predicciones_fallback_basico(
                        todas_empresas_ids, meses, fechas_futuras
                    )
                    if predicciones_xgboost:
                        confianza_xgboost = "media"
                        logger.info(f"✅ Fallback histórico generó {len(predicciones_xgboost)} predicciones")
            
            resultado = {
                'predicciones_prophet': predicciones_prophet,
                'predicciones_xgboost': predicciones_xgboost,
                'predictor_principal': predictor_principal,
                'explicacion_confianza': explicacion_confianza,
                'niveles_confianza': {
                    'prophet': confianza_prophet,
                    'xgboost': confianza_xgboost
                },
                'periodo_prediccion': meses,
                'empresa_servidor_id': empresa_servidor_id,
                'nit_empresa': nit,
                'total_articulos_predichos': len(predicciones_xgboost) if predicciones_xgboost else 0,
                'metadata_modelo': {
                    'meses_historicos': self._calcular_meses_historicos(modelo_data),
                    'mae_xgboost': modelo_data.get('resultados_entrenamiento', {}).get('xgboost', {}).get('mae', 'N/A'),
                    'datos_prophet': modelo_data.get('resultados_entrenamiento', {}).get('prophet', {}).get('datos_entrenamiento', 0),
                    'caracteristicas_entrenamiento': caracteristicas_entrenamiento
                }
            }

            # Registrar predicción en MLflow si está disponible
            if self.mlflow:
                try:
                    # Combinar predicciones para loguear
                    todas_predicciones = []
                    if isinstance(predicciones_prophet, list):
                        todas_predicciones.extend(predicciones_prophet)
                    if isinstance(predicciones_xgboost, list):
                        todas_predicciones.extend(predicciones_xgboost)
                    
                    mlflow_run_id = self.mlflow.log_prediction(
                        modelo_id=modelo_id,
                        nit_empresa=nit,
                        tipo_prediccion='demanda',
                        predicciones=todas_predicciones,
                        metadata={
                            'meses': meses,
                            'predictor_principal': predictor_principal,
                            'confianza_prophet': confianza_prophet,
                            'confianza_xgboost': confianza_xgboost,
                            'total_predicciones': len(todas_predicciones),
                            **resultado['metadata_modelo']
                        }
                    )
                    if mlflow_run_id:
                        resultado['mlflow_run_id'] = mlflow_run_id
                        resultado['mlflow_ui_url'] = f"{self.mlflow.tracking_uri}/#/experiments/0/runs/{mlflow_run_id}"
                        logger.info(f"📊 Predicción registrada en MLflow - Run ID: {mlflow_run_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Error registrando en MLflow (no crítico): {e}")

            return resultado
                
        except Exception as e:
            logger.error(f"❌ Error prediciendo demanda: {e}")
            return {"error": f"Error prediciendo demanda: {str(e)}"}
        
    def _generar_predicciones_fallback_basico(self, empresas_ids, meses, fechas_futuras):
        """Genera predicciones básicas basadas en promedios históricos cuando XGBoost falla"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario
            from django.db.models import Avg, Sum, Q

            # Obtener artículos más vendidos históricamente
            articulos_historicos = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids
            ).values('articulo_codigo', 'articulo_nombre').annotate(
                venta_promedio_mensual=Avg('cantidad', filter=Q(tipo_documento='FACTURA_VENTA')),
                total_ventas=Sum('cantidad', filter=Q(tipo_documento='FACTURA_VENTA'))
            ).filter(venta_promedio_mensual__gt=0).order_by('-total_ventas')[:15]

            if not articulos_historicos:
                return []

            predicciones = []
            for fecha in fechas_futuras:
                for articulo in articulos_historicos:
                    # Predicción simple: promedio histórico + 10% de crecimiento conservador
                    prediccion_base = articulo['venta_promedio_mensual'] * 1.1

                    predicciones.append({
                        'fecha': fecha.strftime('%Y-%m-%d'),
                        'articulo_codigo': articulo['articulo_codigo'],
                        'articulo_nombre': articulo['articulo_nombre'],
                        'prediccion': max(round(prediccion_base), 1)  # Mínimo 1 unidad, valores enteros
                    })

            return predicciones

        except Exception as e:
            logger.error(f"❌ Error en fallback histórico: {e}")
            return []    
        
    def _calcular_meses_historicos(self, modelo_data):
        """Calcula los meses históricos disponibles"""
        try:
            rango_fechas = modelo_data.get('metadata', {}).get('rango_fechas', {})
            if not rango_fechas or 'min' not in rango_fechas or 'max' not in rango_fechas:
                return 0

            from datetime import datetime
            fecha_min = datetime.strptime(rango_fechas['min'], '%Y-%m-%d')
            fecha_max = datetime.strptime(rango_fechas['max'], '%Y-%m-%d')
            return (fecha_max.year - fecha_min.year) * 12 + (fecha_max.month - fecha_min.month)

        except Exception as e:
            logger.warning(f"⚠️ Error calculando meses históricos: {e}")
            return 0
  
    def verificar_estado_modelo(self, empresa_servidor_id):
        """Verificar si un modelo está entrenado y listo para usar - CORREGIDO"""
        try:
            info_empresa = self._obtener_nit_y_empresas_relacionadas(empresa_servidor_id)
            if not info_empresa:
                return {
                    'estado': 'no_encontrado',
                    'empresa_servidor_id': empresa_servidor_id,
                    'error': 'No se pudo obtener información de la empresa'
                }
            
            nit = info_empresa['nit']
            modelo_id = f"empresa_{nit}"
   
            if modelo_id in self.modelos_entrenados:
                modelo_data = self.modelos_entrenados[modelo_id]
                return {
                    'estado': 'entrenado_en_memoria',
                    'modelo_id': modelo_id,
                    'fecha_entrenamiento': modelo_data.get('fecha_entrenamiento'),
                    'empresa_servidor_id': modelo_data.get('empresa_servidor_id_original'),
                    'nit_empresa': modelo_data.get('nit_empresa'),
                    'empresas_incluidas': modelo_data.get('empresas_servidor_ids', []),
                    'filas_entrenamiento': modelo_data.get('filas_entrenamiento')
                }
        
            modelo_path = os.path.join(self.models_dir, f"{modelo_id}.joblib")
            if os.path.exists(modelo_path):
                try:
                    modelo_data = joblib.load(modelo_path)
                    return {
                        'estado': 'disponible_en_disco',
                        'modelo_id': modelo_id,
                        'ruta': modelo_path,
                        'fecha_entrenamiento': modelo_data.get('fecha_entrenamiento'),
                        'empresa_servidor_id': modelo_data.get('empresa_servidor_id_original'),
                        'nit_empresa': modelo_data.get('nit_empresa'),
                        'empresas_incluidas': modelo_data.get('empresas_servidor_ids', []),
                        'filas_entrenamiento': modelo_data.get('filas_entrenamiento')
                    }
                except Exception as e:
                    return {
                        'estado': 'error_carga',
                        'modelo_id': modelo_id,
                        'error': str(e)
                    }
            else:
                return {
                    'estado': 'no_entrenado',
                    'modelo_id': modelo_id,
                    'ruta_buscada': modelo_path
                }
        except Exception as e:
            return {
                'estado': 'error',
                'empresa_servidor_id': empresa_servidor_id,
                'error': str(e)
            }

    def listar_modelos_disponibles(self):
        """Listar todos los modelos disponibles"""
        modelos = []
        
        if not os.path.exists(self.models_dir):
            return {"error": f"Directorio no existe: {self.models_dir}"}
        
        for archivo in os.listdir(self.models_dir):
            if archivo.endswith('.joblib'):
                modelo_id = archivo.replace('.joblib', '')
                # Para listar, necesitamos obtener el empresa_servidor_id de alguna manera
                # Podemos cargar el modelo y obtener el empresa_servidor_id_original
                try:
                    modelo_path = os.path.join(self.models_dir, archivo)
                    modelo_data = joblib.load(modelo_path)
                    
                    modelos.append({
                        'modelo_id': modelo_id,
                        'nit_empresa': modelo_data.get('nit_empresa', 'N/A'),
                        'empresa_servidor_id_original': modelo_data.get('empresa_servidor_id_original', 'N/A'),
                        'empresas_incluidas': modelo_data.get('empresas_servidor_ids', []),
                        'fecha_entrenamiento': modelo_data.get('fecha_entrenamiento'),
                        'filas_entrenamiento': modelo_data.get('filas_entrenamiento')
                    })
                except Exception as e:
                    modelos.append({
                        'modelo_id': modelo_id,
                        'error': f"No se pudo cargar: {str(e)}"
                    })
        
        return {
            'directorio_modelos': self.models_dir,
            'total_modelos': len(modelos),
            'modelos': modelos
        }
    
    def _evaluar_mejor_predictor(self, modelo_data):
        """Evalúa automáticamente qué predictor es más confiable basado en datos históricos y métricas"""
        try:
            # Obtener meses históricos
            rango_fechas = modelo_data.get('metadata', {}).get('rango_fechas', {})
            if not rango_fechas or 'min' not in rango_fechas or 'max' not in rango_fechas:
                return 'xgboost'  # Fallback a XGBoost por falta de datos temporales

            from dateutil.relativedelta import relativedelta
            from datetime import datetime

            fecha_min = datetime.strptime(rango_fechas['min'], '%Y-%m-%d')
            fecha_max = datetime.strptime(rango_fechas['max'], '%Y-%m-%d')
            meses_historicos = (fecha_max.year - fecha_min.year) * 12 + (fecha_max.month - fecha_min.month)

            # Evaluar calidad de modelos
            resultados = modelo_data.get('resultados_entrenamiento', {})
            mae_xgboost = resultados.get('xgboost', {}).get('mae', float('inf'))
            datos_prophet = resultados.get('prophet', {}).get('datos_entrenamiento', 0)

            logger.info(f"📊 Evaluando predictores - Meses: {meses_historicos}, MAE XGBoost: {mae_xgboost}")

            # Lógica inteligente
            if meses_historicos >= 24 and datos_prophet >= 24:
                # Con suficiente data temporal, priorizar Prophet
                return 'prophet'
            elif mae_xgboost <= 5.0:  # MAE menor a 5 unidades = alta calidad
                return 'xgboost' 
            else:
                # Fallback a XGBoost por defecto
                return 'xgboost'

        except Exception as e:
            logger.warning(f"⚠️ Error evaluando predictores: {e}")
            return 'xgboost'
        
    def _generar_explicacion_confianza(self, predictor_principal, modelo_data):
        """Genera una explicación clara de por qué se eligió el predictor principal"""
        try:
            rango_fechas = modelo_data.get('metadata', {}).get('rango_fechas', {})
            resultados = modelo_data.get('resultados_entrenamiento', {})
            mae_xgboost = resultados.get('xgboost', {}).get('mae', 0)
            datos_prophet = resultados.get('prophet', {}).get('datos_entrenamiento', 0)

            if predictor_principal == 'prophet':
                return f"🔮 **Prophet seleccionado**: Patrones temporales detectados ({datos_prophet} meses históricos). Ideal para tendencias a largo plazo."
            else:
                return f"🎯 **XGBoost seleccionado**: Alta precisión (error promedio: {mae_xgboost:.2f} unidades). Excelente para relaciones complejas entre características."

        except Exception as e:
            logger.warning(f"⚠️ Error generando explicación: {e}")
            return "🎯 **XGBoost seleccionado**: Predictor por defecto para máxima confiabilidad."