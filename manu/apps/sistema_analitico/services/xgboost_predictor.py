import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import logging
import joblib

logger = logging.getLogger(__name__)

class XGBoostPredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_names_ = []  # ← GUARDAR NOMBRES DE CARACTERÍSTICAS
    
    def preparar_features(self, df):
        """Método IDÉNTICO al original"""
        df_features = df.copy()

        # Características temporales básicas
        if 'fecha' in df_features.columns:
            df_features['fecha'] = pd.to_datetime(df_features['fecha'])
            df_features['mes'] = df_features['fecha'].dt.month
            df_features['trimestre'] = df_features['fecha'].dt.quarter
            df_features['dia_semana'] = df_features['fecha'].dt.dayofweek

        # Columnas a excluir
        columnas_a_excluir = ['articulo_codigo', 'articulo_nombre', 'fecha', 'valor_total']
        for col in columnas_a_excluir:
            if col in df_features.columns:
                df_features = df_features.drop(col, axis=1)

        # Codificar categóricas
        categorical_features = ['clinica', 'medico', 'tipo_bodega', 'sistema_bodega', 'ciudad']
        categorical_features = [col for col in categorical_features if col in df_features.columns]

        for feature in categorical_features:
            df_features[feature] = df_features[feature].fillna('DESCONOCIDO')
            df_features[feature] = df_features[feature].astype(str)
            
            unique_values = df_features[feature].unique()
            if len(unique_values) > 100:  
                logger.warning(f"Característica {feature} tiene {len(unique_values)} valores únicos, excluyendo")
                df_features = df_features.drop(feature, axis=1)
                continue
            
            le = LabelEncoder()
            try:
                df_features[feature] = le.fit_transform(df_features[feature])
                self.label_encoders[feature] = le
            except Exception as e:
                logger.warning(f"No se pudo codificar {feature}: {e}")
                df_features = df_features.drop(feature, axis=1)

        return df_features
    
    def entrenar_modelo_demanda(self, df, target_col='cantidad', test_size=0.2):
        """Método IDÉNTICO pero GUARDA feature_names"""
        try:
            if target_col not in df.columns:
                logger.error(f"DataFrame no tiene columna '{target_col}'")
                return None

            df_features = self.preparar_features(df)
            
            if df_features.empty:
                logger.error("No hay features disponibles después del preprocesamiento")
                return None

            numeric_columns = df_features.select_dtypes(include=[np.number]).columns.tolist()
            feature_cols = [col for col in numeric_columns if col != target_col]

            if not feature_cols:
                logger.error("No hay columnas numéricas para entrenar")
                return None

            # ✅ GUARDAR NOMBRES DE CARACTERÍSTICAS
            self.feature_names_ = feature_cols.copy()
            logger.info(f"🔧 Características guardadas: {self.feature_names_}")

            X = df_features[feature_cols]
            y = df_features[target_col]

            if X.isnull().any().any() or y.isnull().any():
                logger.warning("Hay valores NaN, llenando con 0")
                X = X.fillna(0)
                y = y.fillna(0)

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            self.model = XGBRegressor(n_estimators=100, random_state=42)
            self.model.fit(X_train_scaled, y_train)

            # ✅ FORZAR feature_names en el modelo
            self.model.get_booster().feature_names = self.feature_names_

            y_pred = self.model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)

            return {
                'mae': mae,
                'datos_entrenamiento': len(X_train),
                'datos_prueba': len(X_test),
                'caracteristicas_usadas': self.feature_names_
            }

        except Exception as e:
            logger.error(f"Error entrenando XGBoost: {e}")
            return None
    
    def predecir_demanda(self, df_futuro):
        """Método SIMPLIFICADO y ROBUSTO"""
        try:
            if not self.model:
                logger.error("❌ Modelo no entrenado")
                return []

            if df_futuro is None or df_futuro.empty:
                logger.error("❌ Datos futuros vacíos")
                return []

            logger.info(f"📊 Iniciando predicción con {len(df_futuro)} filas")

            # ✅ OBTENER CARACTERÍSTICAS DE FORMA DIRECTA
            if hasattr(self, 'feature_names_') and self.feature_names_:
                feature_cols = self.feature_names_
                logger.info(f"✅ Usando características guardadas: {feature_cols}")
            else:
                # Intentar del modelo
                try:
                    feature_cols = self.model.get_booster().feature_names
                    logger.info(f"✅ Usando características del modelo: {feature_cols}")
                except:
                    # Características básicas por defecto
                    feature_cols = ['mes', 'año', 'trimestre', 'dia_semana']
                    logger.warning(f"⚠️ Usando características por defecto: {feature_cols}")

            # ✅ PREPARAR DATOS con características específicas
            df_features = pd.DataFrame()
            
            # Características temporales básicas
            if 'fecha' in df_futuro.columns:
                df_features['mes'] = df_futuro['fecha'].dt.month
                df_features['año'] = df_futuro['fecha'].dt.year
                df_features['trimestre'] = (df_features['mes'] - 1) // 3 + 1
                df_features['dia_semana'] = df_futuro['fecha'].dt.dayofweek
            else:
                # Valores por defecto
                df_features['mes'] = 1
                df_features['año'] = 2025
                df_features['trimestre'] = 1
                df_features['dia_semana'] = 0

            # ✅ COMPLETAR CARACTERÍSTICAS FALTANTES
            for col in feature_cols:
                if col not in df_features.columns:
                    if col in ['total_transacciones', 'ventas_mes', 'compras_mes', 'bodegas_unicas']:
                        df_features[col] = 1
                    elif col in ['es_implante', 'es_instrumental', 'es_equipo_poder']:
                        df_features[col] = 0
                    else:
                        df_features[col] = 0  # Valor por defecto

            logger.info(f"🎯 Características finales: {df_features.columns.tolist()}")

            # ✅ ESCALAR Y PREDECIR
            X = df_features[feature_cols]
            
            # Verificar escalador
            if not hasattr(self.scaler, 'mean_'):
                logger.warning("🔄 Inicializando escalador básico")
                from sklearn.preprocessing import StandardScaler
                self.scaler = StandardScaler()
                self.scaler.fit(X)
            
            X_scaled = self.scaler.transform(X)
            predicciones = self.model.predict(X_scaled)

            # ✅ FORMATEAR RESULTADOS
            resultados = []
            for i, (idx, row) in enumerate(df_futuro.iterrows()):
                resultados.append({
                    'fecha': row['fecha'].strftime('%Y-%m-%d') if hasattr(row['fecha'], 'strftime') else str(row['fecha']),
                    'articulo_codigo': row['articulo_codigo'],
                    'articulo_nombre': row['articulo_nombre'],
                    'prediccion': max(float(predicciones[i]), 0)  # No negativos
                })

            logger.info(f"✅ XGBoost generó {len(resultados)} predicciones")
            return resultados

        except Exception as e:
            logger.error(f"❌ Error en XGBoost: {e}")
            return []