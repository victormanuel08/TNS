# Integración MLflow - Sistema Analítico

## Resumen

MLflow se ha integrado de forma **opcional y no invasiva** al sistema analítico. Si MLflow no está instalado o no está disponible, el sistema funciona normalmente sin él.

## Características

✅ **No rompe funcionalidad existente**: Si MLflow falla, el sistema continúa funcionando  
✅ **Tracking automático**: Registra entrenamientos y predicciones automáticamente  
✅ **Visualización en UI**: Todas las predicciones se pueden ver en `http://localhost:5000`  
✅ **Integración transparente**: No requiere cambios en el código existente

## Instalación

### 1. Instalar MLflow

```bash
pip install mlflow>=2.8.0
```

O instalar desde requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. Configurar variable de entorno (IMPORTANTE)

En tu archivo `.env` dentro de `manu/`:
```env
MLFLOW_TRACKING_URI=http://localhost:5050
```

**Nota**: El puerto es configurable. Asegúrate de que coincida con el puerto donde inicies el servidor MLflow.

### 3. Iniciar servidor MLflow

En una terminal separada:
```bash
cd manu
mlflow ui --port 5050
```

El servidor estará disponible en: `http://localhost:5050`

**Importante**: El puerto en `MLFLOW_TRACKING_URI` debe coincidir con el puerto donde inicies MLflow.
Si no se configura `MLFLOW_TRACKING_URI`, usa el default: `http://localhost:5000`

## Uso

### Entrenamiento de Modelos

Cuando entrenas un modelo usando `/assistant/api/ml/entrenar_modelos/`, automáticamente se registra en MLflow:

**Request:**
```json
POST /assistant/api/ml/entrenar_modelos/
{
  "empresa_servidor_id": 1,
  "fecha_inicio": "2023-01-01",
  "fecha_fin": "2023-12-31"
}
```

**Response incluye:**
```json
{
  "estado": "modelos_entrenados",
  "modelo_id": "empresa_900123456",
  "mlflow_run_id": "abc123...",
  "mlflow_ui_url": "http://localhost:5000/#/experiments/0/runs/abc123..."
}
```

### Predicciones desde Preguntas Inteligentes

Cuando haces una pregunta predictiva usando `/assistant/api/consulta-natural/pregunta_inteligente/`:

**Request:**
```json
POST /assistant/api/consulta-natural/pregunta_inteligente/
{
  "consulta": "¿Qué artículos debo comprar el próximo mes?",
  "empresa_servidor_id": 1
}
```

**Response incluye:**
```json
{
  "consulta_original": "...",
  "explicacion_nino_inteligente": "...",
  "datos_tecnicos_completos": {
    "recomendaciones": [...],
    "mlflow_run_id": "def456...",
    "mlflow_ui_url": "http://localhost:5000/#/experiments/0/runs/def456..."
  }
}
```

### Ver Resultados en MLflow UI

1. Abre `http://localhost:5000` en tu navegador
2. Busca el experimento `tnsfull_ml`
3. Cada entrenamiento y predicción aparece como un "run"
4. Puedes ver:
   - Métricas (MAE, R², RMSE, etc.)
   - Parámetros del modelo
   - Predicciones completas (CSV descargable)
   - Datos de entrenamiento (sample)

## Qué se Registra en MLflow

### Durante Entrenamiento:
- ✅ Parámetros: modelo_id, nit_empresa, fecha_entrenamiento, filas_entrenamiento
- ✅ Métricas: MAE XGBoost, R², RMSE, datos Prophet
- ✅ Modelos: XGBoost registrado como modelo versionado
- ✅ Artefactos: Sample de datos de entrenamiento (CSV)

### Durante Predicciones:
- ✅ Parámetros: tipo_prediccion, predictor_principal, meses_proyeccion
- ✅ Métricas: demanda_total, demanda_promedio, inversión_total, etc.
- ✅ Artefactos: Predicciones completas (CSV), metadata (JSON)

## Arquitectura

```
┌─────────────────┐
│   MLEngine      │
│  (existente)    │
└────────┬────────┘
         │
         ├───► MLflowIntegrator (nuevo, opcional)
         │     └───► MLflow Server (localhost:5000)
         │
         └───► Funciona sin MLflow si falla
```

## Troubleshooting

### MLflow no está disponible
- El sistema funciona normalmente
- Los logs mostrarán: `⚠️ MLflow no está instalado`
- Las respuestas no incluirán `mlflow_run_id` ni `mlflow_ui_url`

### Error al conectar a MLflow
- Verifica que el servidor esté corriendo: `mlflow ui --port 5050` (o el puerto configurado)
- Verifica la variable `MLFLOW_TRACKING_URI` en `.env` dentro de `manu/`
- **Asegúrate de que el puerto en `MLFLOW_TRACKING_URI` coincida con el puerto donde iniciaste MLflow**
- Los errores son no-críticos: el sistema continúa funcionando

### No veo runs en MLflow
- Verifica que el experimento se haya creado: `tnsfull_ml`
- Revisa los logs del backend para ver si hay errores
- Asegúrate de que MLflow esté instalado: `pip list | grep mlflow`

## Beneficios

1. **Trazabilidad**: Historial completo de todos los entrenamientos y predicciones
2. **Comparación**: Compara diferentes modelos y configuraciones
3. **Reproducibilidad**: Cada run tiene todos los parámetros y datos necesarios
4. **Visualización**: UI intuitiva para explorar resultados
5. **Versionado**: Modelos XGBoost registrados y versionados automáticamente

## Notas Técnicas

- MLflow es **completamente opcional**: Si no está instalado, el sistema funciona sin él
- Los errores de MLflow son **no-críticos**: Se loguean como warnings pero no detienen el proceso
- El tracking URI se puede cambiar en tiempo de ejecución via variable de entorno
- Los modelos Prophet no se registran directamente (limitación de MLflow), pero se guarda su metadata

