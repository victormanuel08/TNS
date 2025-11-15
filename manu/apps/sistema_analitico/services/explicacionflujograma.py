# views.py - ConsultaNaturalViewSet
#1. ENTRADA DEL USUARIO
@action(methods=['post'])
def pregunta_inteligente(self, request):
    """
    🎯 ENTRADA PRINCIPAL: Recibe consultas en lenguaje natural
    """
    consulta = request.data.get('consulta')  # Ej: "¿Qué comprar para 6 meses?"
    return self._procesar_consulta_completa(consulta)


#2. INTERPRETACIÓN DE CONSULTA
def _interpretar_consulta_natural(self, consulta):
    """
    🧠 DETECTA QUÉ ANÁLISIS EJECUTAR:
    - "comprar" → Recomendaciones compras
    - "predecir" → Predicción demanda  
    - "analizar" → Análisis inventario
    """
    
#3. EXTRACCIÓN DE DATOS
# services/data_manager.py
def cargar_datos_empresa(self, nit, fecha_inicio, fecha_fin):
    """
    📊 CONECTA Y EXTRAE DATOS:
    1. Conecta a Firebird/PostgreSQL con credenciales
    2. Ejecuta tu consulta SQL específica
    3. Convierte a DataFrame pandas
    4. Preprocesa (fechas, cálculos, clasificaciones)    
    """
    
#4. MODELOS ML - PROPAGACIÓN
# services/ml_engine.py
def entrenar_modelos_empresa(self, empresa_servidor_id):
    """
    🤖 ORQUESTA MODELOS ML:
    """
    # Prophet → Tendencias temporales
    resultados['prophet'] = self.prophet.entrenar_modelo_demanda(df)
    
    # XGBoost → Relaciones complejas
    resultados['xgboost'] = self.xgboost.entrenar_modelo_demanda(df)
    
    # Random Forest → Clasificación
    articulos_abc = self.optimizer.clasificar_abc_xyz(df)
    
#5. BUSINESS ANALYZER
# services/business_analyzer.py  
def analizar_rentabilidad_procedimientos(self, df):
    """
    💰 ANÁLISIS DE NEGOCIO:
    - Rentabilidad por procedimiento
    - Médicos más estratégicos
    - Alertas de negocio
    """
#6. GENERACIÓN DE RESPUESTA
# services/natural_response_orchestrator.py
def generar_respuesta_hibrida(self, resultados_tecnicos, tipo_consulta):
    """
    🎨 COMBINA PRECISIÓN + NATURALIDAD:
    1. Toma resultados técnicos de todos los modelos
    2. Los envía a DeepSeek para "traducción infantil"
    3. Estructura respuesta final
    """