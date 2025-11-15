# sistema_analitico/views.py
# 🔹 Librerías estándar
import logging
import pandas as pd
import re
import secrets
from datetime import datetime, timedelta
from decimal import Decimal

# 🔹 Django y DRF
from django.db.models import Count, Sum, Avg, Max, Min, Q, F, Value
from django.db.models.functions import TruncMonth, TruncYear, TruncQuarter, Coalesce
from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# 🔹 Modelos, serializadores y servicios internos
from .models import Servidor, EmpresaServidor, MovimientoInventario, UsuarioEmpresa
from .serializers import *
from .services.data_manager import DataManager
from .services.ml_engine import MLEngine
from .services.natural_response_orchestrator import NaturalResponseOrchestrator
from .services.system_tester import SystemTester
from .services.permisos import TienePermisoEmpresa, HasValidAPIKey

# 🔹 Logger
logger = logging.getLogger(__name__)


class ServidorViewSet(viewsets.ModelViewSet):
    queryset = Servidor.objects.all()
    serializer_class = ServidorSerializer

class EmpresaServidorViewSet(viewsets.ModelViewSet):
    queryset = EmpresaServidor.objects.all()
    serializer_class = EmpresaServidorSerializer
    
class UsuarioEmpresaViewSet(viewsets.ModelViewSet):
    queryset = UsuarioEmpresa.objects.all()
    serializer_class = UsuarioEmpresaSerializer
    permission_classes = [TienePermisoEmpresa]

class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    queryset = MovimientoInventario.objects.all()
    serializer_class = MovimientoInventarioSerializer

class SistemaViewSet(viewsets.ViewSet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data_manager = DataManager()
    
    @action(detail=False, methods=['post'])
    def inicializar_sistema(self, request):
        try:
            maestro = self.data_manager.inicializar_sistema()
            return Response({
                'estado': 'sistema_inicializado',
                'version': maestro['version']
            })
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['post'])
    def descubrir_empresas(self, request):
        serializer = DescubrirEmpresasSerializer(data=request.data)
        if serializer.is_valid():
            try:
                empresas = self.data_manager.descubrir_empresas(
                    serializer.validated_data['servidor_id']
                )
                return Response({
                    'estado': 'empresas_descubiertas',
                    'total_empresas': len(empresas)
                })
            except Exception as e:
                return Response({'error': str(e)}, status=500)
        return Response(serializer.errors, status=400)
    
    @action(detail=False, methods=['post'])
    def extraer_datos(self, request):
        serializer = ExtraerDatosSerializer(data=request.data)
        if serializer.is_valid():
            try:
                resultado = self.data_manager.extraer_datos_empresa(
                    empresa_servidor_id=serializer.validated_data['empresa_servidor_id'],
                    fecha_inicio=serializer.validated_data['fecha_inicio'],
                    fecha_fin=serializer.validated_data['fecha_fin']
                )
                return Response(resultado)
            except Exception as e:
                return Response({'error': str(e)}, status=500)
        return Response(serializer.errors, status=400)

class MLViewSet(viewsets.ViewSet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ml_engine = MLEngine()
    
    @action(detail=False, methods=['post'])
    def entrenar_modelos(self, request):
        serializer = EntrenarModelosSerializer(data=request.data)
        if serializer.is_valid():
            try:
                resultado = self.ml_engine.entrenar_modelos_empresa(
                    empresa_servidor_id=serializer.validated_data['empresa_servidor_id']
                )
                return Response(resultado)
            except Exception as e:
                return Response({'error': str(e)}, status=500)
        return Response(serializer.errors, status=400)
    
    @action(detail=False, methods=['post'])
    def predecir_demanda(self, request):
        serializer = PredecirDemandaSerializer(data=request.data)
        if serializer.is_valid():
            try:
                resultado = self.ml_engine.predecir_demanda_articulos(
                    modelo_id=serializer.validated_data['modelo_id'],
                    meses=serializer.validated_data['meses']
                )
                return Response(resultado)
            except Exception as e:
                return Response({'error': str(e)}, status=500)
        return Response(serializer.errors, status=400)
    
    @action(detail=False, methods=['post'])
    def recomendaciones_compras(self, request):
        serializer = RecomendacionesComprasSerializer(data=request.data)
        if serializer.is_valid():
            try:
                resultado = self.ml_engine.generar_recomendaciones_compras(
                    modelo_id=serializer.validated_data['modelo_id'],
                    meses=serializer.validated_data['meses'],
                    nivel_servicio=serializer.validated_data['nivel_servicio']
                )
                return Response(resultado)
            except Exception as e:
                return Response({'error': str(e)}, status=500)
        return Response(serializer.errors, status=400)

class ConsultaNaturalViewSet(viewsets.ViewSet):
    permission_classes = [HasValidAPIKey, TienePermisoEmpresa]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ml_engine = MLEngine()
        self.response_orchestrator = NaturalResponseOrchestrator()
    
    # En ConsultaNaturalViewSet, agregar este método
    def _obtener_empresas_para_consulta(self, request, empresa_servidor_id):
        """
        Obtiene las empresas para consulta según el contexto (API Key o usuario normal)
        PARA API KEY: SIEMPRE usa TODAS las empresas del NIT, ignora empresa_servidor_id
        """
        try:
            from apps.sistema_analitico.models import EmpresaServidor
    
            print(f"🔑 _obtener_empresas_para_consulta - INICIO")
            print(f"   empresa_servidor_id recibido: {empresa_servidor_id}")
            print(f"   ¿Es API Key?: {hasattr(request, 'cliente_api') and request.cliente_api}")
    
            # ✅ SI ES API KEY - IGNORAR empresa_servidor_id Y USAR TODAS LAS EMPRESAS DEL NIT
            if hasattr(request, 'cliente_api') and request.cliente_api:
                empresas = request.empresas_autorizadas
                print(f"   API Key - NIT: {request.cliente_api.nit}")
                print(f"   Empresas autorizadas: {list(empresas.values_list('id', 'nombre'))}")
    
                if not empresas.exists():
                    print("❌ API Key no tiene empresas asociadas")
                    raise Exception('API Key no tiene empresas asociadas')
    
                # ✅ CORRECCIÓN: IGNORAR empresa_servidor_id Y SIEMPRE USAR TODAS LAS EMPRESAS
                empresas_ids = list(empresas.values_list('id', flat=True))
                print(f"   API Key - Usando TODAS las empresas del NIT: {empresas_ids}")
                return empresas_ids, len(empresas_ids) > 1  # True = consolidado
    
            # ✅ SI ES USUARIO NORMAL (mantener lógica original)
            else:
                print("   Modo usuario normal")
                if not request.user.is_authenticated:
                    raise Exception('Usuario no autenticado')
    
                if empresa_servidor_id:
                    try:
                        empresa = EmpresaServidor.objects.get(id=empresa_servidor_id)
                        if not self._tiene_permiso_empresa(request.user, empresa, 'ver'):
                            raise Exception('No tienes permisos para esta empresa')
                        return [empresa_servidor_id], False
                    except EmpresaServidor.DoesNotExist:
                        raise Exception('Empresa no encontrada')
                else:
                    empresas_permitidas = self._obtener_empresas_permitidas(request.user)
                    if empresas_permitidas.exists():
                        primera_empresa = empresas_permitidas.first().id
                        print(f"   Usando primera empresa permitida: {primera_empresa}")
                        return [primera_empresa], False
                    else:
                        raise Exception('No tienes empresas asignadas')
    
        except Exception as e:
            print(f"❌ Error en _obtener_empresas_para_consulta: {e}")
            raise Exception(f'Error de permisos: {str(e)}')
        
    @action(detail=False, methods=['post'])
    def pregunta_inteligente(self, request):
        consulta = request.data.get('consulta', '').lower()
        empresa_servidor_id = request.data.get('empresa_servidor_id')

        if not consulta:
            return Response({'error': 'No enviaste ninguna pregunta'}, status=400)

        try:
            # ✅ DETECTAR SI ES API KEY O USUARIO NORMAL
            es_api_key = hasattr(request, 'cliente_api') and request.cliente_api

            # ========== LÓGICA PARA API KEYS ==========
            if es_api_key:
                empresas = request.empresas_autorizadas

                # ✅ CORRECCIÓN: VERIFICAR QUÉ EMPRESAS TIENEN MODELOS ENTRENADOS
                if not empresa_servidor_id and empresas.exists():
                    # Buscar empresa que tenga modelo entrenado
                    empresa_con_modelo = None

                    for empresa in empresas:
                        # Verificar si esta empresa tiene modelo entrenado
                        estado_modelo = self.ml_engine.verificar_estado_modelo(empresa.id)
                        if estado_modelo.get('estado') in ['entrenado_en_memoria', 'disponible_en_disco']:
                            empresa_con_modelo = empresa
                            logger.info(f"✅ Encontrada empresa con modelo: {empresa.id} - {empresa.nit}")
                            break
                        
                    # Si no encontramos empresa con modelo, usar la primera disponible
                    if empresa_con_modelo:
                        empresa_servidor_id = empresa_con_modelo.id
                        nit_empresa = empresa_con_modelo.nit
                    else:
                        empresa_servidor_id = empresas.first().id
                        nit_empresa = empresas.first().nit
                        logger.warning(f"⚠️ Ninguna empresa tiene modelo entrenado, usando: {empresa_servidor_id}")

                    logger.info(f"🔑 API Key - Empresa seleccionada: {empresa_servidor_id}, NIT: {nit_empresa}")

                # Verificar que la empresa solicitada esté autorizada
                if empresa_servidor_id and not empresas.filter(id=empresa_servidor_id).exists():
                    return Response({'error': 'API Key no tiene acceso a esta empresa'}, status=403)

                logger.info(f"✅ API Key autorizada para empresa: {empresa_servidor_id}")

            # ========== EL RESTO DE TU CÓDIGO ORIGINAL ==========
            tipo_consulta, parametros = self._interpretar_consulta_natural(consulta)

            logger.info(f"🔍 Consulta detectada: {tipo_consulta}, Parámetros: {parametros}")

            if tipo_consulta in ['recomendaciones_compras', 'prediccion_demanda']:
                # ✅ MÉTODOS PREDICTIVOS - NO TOCAR (ya tienen su propia lógica)
                resultados = self._ejecutar_analisis_predictivo(
                    tipo_consulta, parametros, empresa_servidor_id
                )

                if 'error' in resultados and any(msg in resultados['error'].lower() for msg in ['no encontrado', 'no entrenado']):
                    logger.info("🔄 Fallback a análisis histórico")
                    resultados = self._generar_recomendaciones_historicas_mejoradas(
                        consulta, empresa_servidor_id, parametros.get('meses', 6)
                    )
            else:
                # ✅ MÉTODOS HISTÓRICOS - PASAR EL REQUEST PARA MANEJAR API KEYS
                resultados = self._ejecutar_analisis_historico(
                    tipo_consulta, parametros, empresa_servidor_id, request
                )

            if 'error' in resultados:
                return Response(resultados, status=400)

            respuesta_hibrida = self.response_orchestrator.generar_respuesta_hibrida(
                resultados, tipo_consulta, consulta
            )

            return Response(respuesta_hibrida)

        except Exception as e:
            logger.error(f"❌ Error en pregunta_inteligente: {e}")
            return Response({
                'error': f'¡Ups! Algo salió mal: {str(e)}'
            }, status=500)
    # ========== MÉTODOS AUXILIARES SEGUROS ==========
    
    def _tiene_permiso_empresa(self, user, empresa, permiso):
        """Método seguro para verificar permisos de empresa"""
        if user.is_anonymous:
            return False
        if user.is_superuser:
            return True
        if hasattr(user, 'has_empresa_permission'):
            return user.has_empresa_permission(empresa, permiso)
        return False
    
    def _obtener_empresas_permitidas(self, user):
        """Método seguro para obtener empresas permitidas"""
        if user.is_anonymous:
            from apps.sistema_analitico.models import EmpresaServidor
            return EmpresaServidor.objects.none()
        if hasattr(user, 'empresas_permitidas'):
            return user.empresas_permitidas()
        from apps.sistema_analitico.models import EmpresaServidor
        return EmpresaServidor.objects.none()
    
    def _interpretar_consulta_natural(self, consulta):
        consulta_lower = consulta.lower()

        # ========== CONSULTAS DE COMPARACIÓN ENTRE AÑOS ==========
        if self._detectar_comparacion_anios(consulta):
            # Extraer años específicos si se mencionan
            anios = re.findall(r'20\d{2}', consulta)
            if len(anios) == 2:
                return 'comparar_anios_especificos', {
                    'consulta_original': consulta,
                    'anio_actual': int(anios[0]),
                    'anio_comparar': int(anios[1])
                }
            elif 'anterior' in consulta_lower or 'pasado' in consulta_lower:
                return 'comparar_anio_anterior', {'consulta_original': consulta}
            else:
                return 'comparar_anios_general', {'consulta_original': consulta}
        
        # ========== CONSULTAS PREDICTIVAS ==========
        palabras_recomendaciones = [
            'comprar', 'pedir', 'stock', 'mercancia', 'mercancía', 'inventario', 
            'orden', 'recomiendas', 'recomendación', 'recomendaciones', 'sugerencia',
            'qué comprar', 'que comprar', 'qué pedir', 'que pedir', 'necesito'
        ]
        if any(palabra in consulta_lower for palabra in palabras_recomendaciones):
            meses = self._extraer_meses(consulta_lower) or 6
            return 'recomendaciones_compras', {'meses': meses, 'consulta_original': consulta}
        
        palabras_prediccion = [
            'predecir', 'pronóstico', 'pronostico', 'futuro', 'proyectar', 
            'proyección', 'proyeccion', 'demanda futura', 'qué pasará', 'que pasara',
            'cómo será', 'como sera', 'tendencia futura'
        ]
        if any(palabra in consulta_lower for palabra in palabras_prediccion):
            meses = self._extraer_meses(consulta_lower) or 6
            return 'prediccion_demanda', {'meses': meses, 'consulta_original': consulta}
        
        # ========== CONSULTAS POR FECHAS/PERIODOS ==========
        # ========== CONSULTAS POR MÚLTIPLES MESES ==========        
        
        meses_palabras = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                         'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

        # Detectar si hay múltiples meses mencionados
        meses_en_consulta = [mes for mes in meses_palabras if mes in consulta_lower]   
        if len(meses_en_consulta) >= 2 and any(palabra in consulta_lower for palabra in ['vendí', 'vendio', 'ventas', 'articulos', 'referencias']):
            return 'ventas_por_meses', {'consulta_original': consulta}
        
        # Consultas por mes específico
        if any(mes in consulta_lower for mes in meses_palabras):
            if any(palabra in consulta_lower for palabra in ['vendí', 'vendio', 'ventas', 'articulos', 'cantidad', 'total']):
                return 'ventas_por_mes', {'consulta_original': consulta}
            elif any(palabra in consulta_lower for palabra in ['compré', 'compro', 'compras']):
                return 'compras_por_mes', {'consulta_original': consulta}
        
        # Consultas por año
        if any(palabra in consulta_lower for palabra in ['año', 'ano', 'años', 'anos']) and any(palabra in consulta_lower for palabra in ['ventas', 'compras', 'total']):
            return 'ventas_por_anio', {'consulta_original': consulta}
        
        # Consultas por rango de fechas
        if any(palabra in consulta_lower for palabra in ['desde', 'hasta', 'entre', 'rango', 'periodo']):
            return 'ventas_por_rango_fechas', {'consulta_original': consulta}
        
        # Consultas de últimos días/meses
        if any(palabra in consulta_lower for palabra in ['último', 'ultimo', 'reciente', 'pasado', 'previo']):
            if any(palabra in consulta_lower for palabra in ['días', 'dias', 'mes', 'meses', 'semana', 'semanas']):
                return 'ventas_recientes', {'consulta_original': consulta}
        
        # ========== CONSULTAS POR ARTÍCULOS ==========
        if any(palabra in consulta_lower for palabra in ['artículo más vendido', 'articulo mas vendido', 'mas vendido', 'producto más vendido']):
            return 'historico_articulos_mas_vendidos', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['artículo menos vendido', 'articulo menos vendido', 'menos vendido']):
            return 'historico_articulos_menos_vendidos', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['artículo más caro', 'articulo mas caro', 'producto más caro']):
            return 'historico_articulos_mas_caros', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['buscar artículo', 'buscar articulo', 'información artículo', 'info articulo']):
            return 'buscar_articulo', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['categoría', 'categoria', 'tipo artículo', 'tipo articulo']):
            return 'articulos_por_categoria', {'consulta_original': consulta}
        
        # ========== CONSULTAS POR PERSONAS/ENTIDADES ==========
        if any(palabra in consulta_lower for palabra in ['nit', 'n.it']):
            return 'consulta_por_nit', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['cédula', 'cedula', 'cedula']):
            return 'consulta_por_cedula', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['doctor', 'médico', 'medico', 'dr.', 'dra.']):
            return 'consulta_por_medico', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['paciente', 'pacientes']):
            return 'consulta_por_paciente', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['clínica', 'clinica', 'hospital']):
            return 'consulta_por_clinica', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['pagador', 'eps', 'ars', 'aseguradora']):
            return 'consulta_por_pagador', {'consulta_original': consulta}
        
        # ========== CONSULTAS POR UBICACIONES ==========
        if any(palabra in consulta_lower for palabra in ['ciudad', 'ciudades', 'municipio', 'departamento']):
            return 'ventas_por_ciudad', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['bodega', 'bodegas', 'almacén', 'almacen']):
            return 'ventas_por_bodega', {'consulta_original': consulta}
        
        # ========== CONSULTAS ESPECÍFICAS DE VENTAS ==========
        if any(palabra in consulta_lower for palabra in ['venta más grande', 'venta mas grande', 'mayor venta', 'venta mayor']):
            return 'historico_venta_mas_grande', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['venta más pequeña', 'venta mas pequeña', 'menor venta']):
            return 'historico_venta_menor', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['promedio venta', 'venta promedio', 'valor promedio']):
            return 'estadisticas_ventas_promedio', {'consulta_original': consulta}
        
        # ========== CONSULTAS DE COMPARACIÓN ==========
        if any(palabra in consulta_lower for palabra in ['comparar', 'vs', 'versus', 'comparación']):
            return 'comparar_periodos', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['crecimiento', 'incremento', 'aumento', 'disminución', 'decrecimiento']):
            return 'analisis_crecimiento', {'consulta_original': consulta}
        
        # ========== CONSULTAS ESTADÍSTICAS GENERALES ==========
        if any(palabra in consulta_lower for palabra in [
            'estadística', 'estadisticas', 'resumen', 'resumen general', 
            'totales', 'métricas', 'metricas', 'kpi', 'indicadores'
        ]):
            return 'historico_general', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['cuántos', 'cuantos', 'cuántas', 'cuantas', 'total']):
            return 'conteo_general', {'consulta_original': consulta}
        
        # ========== CONSULTAS DE INVENTARIO ==========
        if any(palabra in consulta_lower for palabra in ['stock', 'inventario', 'existencia', 'nivel stock']):
            return 'estado_inventario', {'consulta_original': consulta}
        
        if any(palabra in consulta_lower for palabra in ['rotación', 'rotacion', 'giro']):
            return 'analisis_rotacion', {'consulta_original': consulta}
        
        # ========== DETECCIÓN POR DEFAULT ==========
        # Si no coincide con nada específico, intentar análisis predictivo primero
        meses = self._extraer_meses(consulta_lower) or 3
        return 'recomendaciones_compras', {'meses': meses, 'consulta_original': consulta}
    
    def _extraer_meses(self, consulta):
        """Extrae el número de meses de la consulta natural"""
        numeros = re.findall(r'\d+', consulta)
        if numeros:
            return min(int(numeros[0]), 24)  # Máximo 24 meses
        return None
    
    def _extraer_anio(self, consulta):
        """Extrae el año de la consulta"""
        anios = re.findall(r'20\d{2}', consulta)
        if anios:
            return int(anios[0])
        return datetime.now().year
    
    def _extraer_mes_nombre(self, consulta):
        """Extrae el nombre del mes de la consulta"""
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        for mes_nombre, mes_num in meses.items():
            if mes_nombre in consulta.lower():
                return mes_num, mes_nombre.capitalize()
        return None, None
    
    def _ejecutar_analisis_predictivo(self, tipo_consulta, parametros, empresa_servidor_id):
        """Ejecuta análisis predictivo usando ML - CORREGIDO"""
        try:
            logger.info(f"🔮 Ejecutando análisis predictivo: {tipo_consulta}")

            if tipo_consulta == 'recomendaciones_compras':
                return self.ml_engine.generar_recomendaciones_compras(
                    empresa_servidor_id=empresa_servidor_id,  # ← CAMBIADO: pasa el entero directamente
                    meses=parametros['meses']
                )

            elif tipo_consulta == 'prediccion_demanda':
                return self.ml_engine.predecir_demanda_articulos(
                    empresa_servidor_id=empresa_servidor_id,  # ← CAMBIADO: pasa el entero directamente
                    meses=parametros['meses']
                )

        except Exception as e:
            logger.error(f"❌ Error en análisis predictivo: {e}")
            return {'error': f"Error en análisis predictivo: {str(e)}"}

    def _ejecutar_analisis_historico(self, tipo_consulta, parametros, empresa_servidor_id, request=None):
        try:
            consulta_original = parametros.get('consulta_original', '')

            # ========== CONSULTAS DE COMPARACIÓN ENTRE AÑOS ==========
            if tipo_consulta == 'comparar_anios_especificos':
                return self._comparar_anios_especificos(
                    consulta_original, empresa_servidor_id,
                    parametros['anio_actual'], parametros['anio_comparar']
                )
            elif tipo_consulta == 'comparar_anio_anterior':
                return self._comparar_anio_anterior(consulta_original, empresa_servidor_id)
            elif tipo_consulta == 'comparar_anios_general':
                return self._comparar_anio_anterior(consulta_original, empresa_servidor_id)

            # ========== CONSULTAS POR FECHAS/PERIODOS ==========
            elif tipo_consulta == 'ventas_por_mes':
                return self._consultar_ventas_por_mes(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'ventas_por_meses':
                return self._consultar_ventas_por_meses(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'compras_por_mes':
                return self._consultar_compras_por_mes(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'ventas_por_anio':
                return self._consultar_ventas_por_anio(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'ventas_por_rango_fechas':
                return self._consultar_ventas_por_rango_fechas(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'ventas_recientes':
                return self._consultar_ventas_recientes(consulta_original, empresa_servidor_id, request)

            # ========== CONSULTAS POR ARTÍCULOS ==========
            elif tipo_consulta == 'historico_articulos_mas_vendidos':
                return self._consultar_articulos_mas_vendidos(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'historico_articulos_menos_vendidos':
                return self._consultar_articulos_menos_vendidos(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'historico_articulos_mas_caros':
                return self._consultar_articulos_mas_caros(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'buscar_articulo':
                return self._buscar_articulo(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'articulos_por_categoria':
                return self._consultar_articulos_por_categoria(empresa_servidor_id, request)

            # ========== CONSULTAS POR PERSONAS/ENTIDADES ==========
            elif tipo_consulta == 'consulta_por_nit':
                return self._consultar_por_nit(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'consulta_por_cedula':
                return self._consultar_por_cedula(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'consulta_por_medico':
                return self._consultar_por_medico(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'consulta_por_paciente':
                return self._consultar_por_paciente(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'consulta_por_clinica':
                return self._consultar_por_clinica(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'consulta_por_pagador':
                return self._consultar_por_pagador(consulta_original, empresa_servidor_id, request)

            # ========== CONSULTAS POR UBICACIONES ==========
            elif tipo_consulta == 'ventas_por_ciudad':
                return self._consultar_ventas_por_ciudad(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'ventas_por_bodega':
                return self._consultar_ventas_por_bodega(consulta_original, empresa_servidor_id, request)

            # ========== CONSULTAS ESPECÍFICAS DE VENTAS ==========
            elif tipo_consulta == 'historico_venta_mas_grande':
                return self._consultar_venta_mas_grande(empresa_servidor_id, request)
            elif tipo_consulta == 'historico_venta_menor':
                return self._consultar_venta_menor(empresa_servidor_id, request)
            elif tipo_consulta == 'estadisticas_ventas_promedio':
                return self._consultar_estadisticas_ventas_promedio(empresa_servidor_id, request)

            # ========== CONSULTAS DE COMPARACIÓN ==========
            elif tipo_consulta == 'comparar_periodos':
                return self._comparar_periodos(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'analisis_crecimiento':
                return self._analizar_crecimiento(consulta_original, empresa_servidor_id, request)

            # ========== CONSULTAS ESTADÍSTICAS GENERALES ==========
            elif tipo_consulta == 'historico_general':
                return self._consultar_estadisticas_generales(empresa_servidor_id, request)
            elif tipo_consulta == 'conteo_general':
                return self._consultar_conteo_general(empresa_servidor_id, request)

            # ========== CONSULTAS DE INVENTARIO ==========
            elif tipo_consulta == 'estado_inventario':
                return self._consultar_estado_inventario(consulta_original, empresa_servidor_id, request)
            elif tipo_consulta == 'analisis_rotacion':
                return self._analizar_rotacion_inventario(consulta_original, empresa_servidor_id, request)

            # ========== DEFAULT ==========
            else:
                return self._consultar_estadisticas_generales(empresa_servidor_id, request)

        except Exception as e:
            logger.error(f"❌ Error en análisis histórico: {e}")
            return {'error': f"Error en análisis histórico: {str(e)}"}
    
    # ========== MÉTODOS DE CONSULTA POR FECHAS/PERIODOS ==========
    def _consultar_ventas_por_mes(self, consulta, empresa_servidor_id):
        """Consulta ventas por mes específico - CORREGIDO PARA MOSTRAR TODAS LAS REFERENCIAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            mes_num, mes_nombre = self._extraer_mes_nombre(consulta)
            anio = self._extraer_anio(consulta)

            if not mes_num:
                return {'error': 'No se pudo identificar el mes en la consulta'}

            # ✅ CORRECCIÓN: Calcular estadísticas sin usar Avg en campos agregados
            ventas_mes = MovimientoInventario.objects.filter(
                empresa_servidor_id=empresa_servidor_id,
                fecha__year=anio,
                fecha__month=mes_num,
                tipo_documento='FACTURA_VENTA'
            ).aggregate(
                total_articulos=Sum('cantidad'),
                total_ventas=Count('id'),
                valor_total=Sum('valor_total')
            )

            # ✅ CORRECCIÓN: Calcular promedio manualmente
            total_ventas_count = ventas_mes['total_ventas'] or 0
            valor_total_ventas = ventas_mes['valor_total'] or 0

            if total_ventas_count > 0:
                venta_promedio = valor_total_ventas / total_ventas_count
            else:
                venta_promedio = 0

            # ✅ CORRECCIÓN CRÍTICA: OBTENER TODOS LOS ARTÍCULOS SIN LÍMITE CUANDO PIDE "TODAS"
            consulta_lower = consulta.lower()
            if any(palabra in consulta_lower for palabra in ['todas', 'todos', 'completo', 'completa', 'todas las', 'todos los']):
                # SIN LÍMITE - TODAS LAS REFERENCIAS
                articulos_mes = MovimientoInventario.objects.filter(
                    empresa_servidor_id=empresa_servidor_id,
                    fecha__year=anio,
                    fecha__month=mes_num,
                    tipo_documento='FACTURA_VENTA'
                ).values('articulo_codigo', 'articulo_nombre').annotate(
                    cantidad_vendida=Sum('cantidad'),
                    valor_total=Sum('valor_total')
                ).order_by('-cantidad_vendida')

                mensaje_articulos = f'TODAS las referencias de artículos vendidos en {mes_nombre} {anio}'
            else:
                # Límite por defecto (5 artículos) para consultas normales
                articulos_mes = MovimientoInventario.objects.filter(
                    empresa_servidor_id=empresa_servidor_id,
                    fecha__year=anio,
                    fecha__month=mes_num,
                    tipo_documento='FACTURA_VENTA'
                ).values('articulo_codigo', 'articulo_nombre').annotate(
                    cantidad_vendida=Sum('cantidad'),
                    valor_total=Sum('valor_total')
                ).order_by('-cantidad_vendida')[:5]

                mensaje_articulos = f'Principales artículos vendidos en {mes_nombre} {anio}'

            # Convertir a lista para serialización
            articulos_lista = list(articulos_mes)

            return {
                'tipo_consulta': 'ventas_por_mes',
                'mes': mes_nombre,
                'anio': anio,
                'total_articulos_vendidos': ventas_mes['total_articulos'] or 0,
                'total_ventas': total_ventas_count,
                'valor_total': float(valor_total_ventas),
                'venta_promedio': float(venta_promedio),
                'articulos': articulos_lista,  # ✅ CAMBIO: ahora se llama 'articulos' no 'articulos_destacados'
                'total_referencias_encontradas': len(articulos_lista),
                'mostrando_todas_referencias': any(palabra in consulta_lower for palabra in ['todas', 'todos', 'completo']),
                'mensaje': mensaje_articulos
            }

        except Exception as e:
            return {'error': f'Error consultando ventas por mes: {str(e)}'}

    def _consultar_compras_por_mes(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta compras por mes específico - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Para consultas por mes, si es consolidado, usar solo la primera empresa
            if es_consolidado and len(empresas_ids) > 1:
                logger.warning("⚠️ Consulta por mes con múltiples empresas, usando solo la primera")
                empresas_ids = [empresas_ids[0]]
                es_consolidado = False

            mes_num, mes_nombre = self._extraer_mes_nombre(consulta)
            anio = self._extraer_anio(consulta)

            if not mes_num:
                return {'error': 'No se pudo identificar el mes en la consulta'}

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                fecha__year=anio,
                fecha__month=mes_num,
                tipo_documento='FACTURA_COMPRA'
            )

            compras_mes = query.aggregate(
                total_articulos=Sum('cantidad'),
                total_compras=Count('id'),
                valor_total=Sum('valor_total')
            )

            # ✅ CORRECCIÓN: Calcular promedio manualmente
            total_compras_count = compras_mes['total_compras'] or 0
            valor_total_compras = compras_mes['valor_total'] or 0

            if total_compras_count > 0:
                compra_promedio = valor_total_compras / total_compras_count
            else:
                compra_promedio = 0

            # ✅ MENSAJE SEGÚN CONTEXTO
            mensaje = f'Compras de {mes_nombre} {anio}'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'compras_por_mes',
                'mes': mes_nombre,
                'anio': anio,
                'total_articulos_comprados': compras_mes['total_articulos'] or 0,
                'total_compras': total_compras_count,
                'valor_total': float(valor_total_compras),
                'compra_promedio': float(compra_promedio),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error consultando compras por mes: {str(e)}'}


    def _consultar_ventas_por_meses(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta ventas por MÚLTIPLES meses específicos - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Para consultas por meses específicos, si es consolidado, usar solo la primera empresa
            if es_consolidado and len(empresas_ids) > 1:
                logger.warning("⚠️ Consulta por meses específicos con múltiples empresas, usando solo la primera")
                empresas_ids = [empresas_ids[0]]
                es_consolidado = False

            # Extraer todos los meses mencionados
            meses_dict = {
                'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
                'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
            }

            consulta_lower = consulta.lower()
            meses_encontrados = []

            for mes_nombre, mes_num in meses_dict.items():
                if mes_nombre in consulta_lower:
                    meses_encontrados.append({'nombre': mes_nombre.capitalize(), 'numero': mes_num})

            if len(meses_encontrados) < 2:
                return {'error': 'No se pudieron identificar al menos 2 meses en la consulta'}

            anio = self._extraer_anio(consulta)

            resultados_meses = []

            for mes_info in meses_encontrados:
                mes_nombre = mes_info['nombre']
                mes_num = mes_info['numero']

                # Consulta base - ADAPTADA
                query = MovimientoInventario.objects.filter(
                    empresa_servidor_id__in=empresas_ids,
                    fecha__year=anio,
                    fecha__month=mes_num,
                    tipo_documento='FACTURA_VENTA'
                )

                # Estadísticas del mes
                ventas_mes = query.aggregate(
                    total_articulos=Sum('cantidad'),
                    total_ventas=Count('id'),
                    valor_total=Sum('valor_total')
                )

                total_ventas_count = ventas_mes['total_ventas'] or 0
                valor_total_ventas = ventas_mes['valor_total'] or 0
                venta_promedio = valor_total_ventas / total_ventas_count if total_ventas_count > 0 else 0

                # ✅ TODOS LOS ARTÍCULOS DEL MES (sin límite)
                articulos_mes = query.values('articulo_codigo', 'articulo_nombre').annotate(
                    cantidad_vendida=Sum('cantidad'),
                    valor_total=Sum('valor_total')
                ).order_by('-cantidad_vendida')

                resultados_meses.append({
                    'mes': mes_nombre,
                    'anio': anio,
                    'total_articulos_vendidos': ventas_mes['total_articulos'] or 0,
                    'total_ventas': total_ventas_count,
                    'valor_total': float(valor_total_ventas),
                    'venta_promedio': float(venta_promedio),
                    'articulos': list(articulos_mes),
                    'total_referencias': len(list(articulos_mes))
                })

            # Calcular totales generales
            total_articulos_general = sum(mes['total_articulos_vendidos'] for mes in resultados_meses)
            total_ventas_general = sum(mes['total_ventas'] for mes in resultados_meses)
            total_valor_general = sum(mes['valor_total'] for mes in resultados_meses)

            nombres_meses = ", ".join(mes['mes'] for mes in resultados_meses)

            # ✅ MENSAJE SEGÚN CONTEXTO
            mensaje = f'TODAS las referencias de {nombres_meses} {anio}'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'ventas_por_meses',
                'meses_analizados': resultados_meses,
                'totales_generales': {
                    'total_articulos_vendidos': total_articulos_general,
                    'total_ventas': total_ventas_general,
                    'valor_total': total_valor_general
                },
                'total_meses_analizados': len(resultados_meses),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error consultando ventas por múltiples meses: {str(e)}'}
    
    # ========== MÉTODOS DE CONSULTA POR FECHAS/PERIODOS (ADAPTADOS) ==========

    def _consultar_ventas_por_mes(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta ventas por mes específico - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Para consultas por mes, si es consolidado, usar solo la primera empresa
            # porque los meses son específicos de cada empresa/año
            if es_consolidado and len(empresas_ids) > 1:
                logger.warning("⚠️ Consulta por mes con múltiples empresas, usando solo la primera")
                empresas_ids = [empresas_ids[0]]
                es_consolidado = False

            mes_num, mes_nombre = self._extraer_mes_nombre(consulta)
            anio = self._extraer_anio(consulta)

            if not mes_num:
                return {'error': 'No se pudo identificar el mes en la consulta'}

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                fecha__year=anio,
                fecha__month=mes_num,
                tipo_documento='FACTURA_VENTA'
            )

            ventas_mes = query.aggregate(
                total_articulos=Sum('cantidad'),
                total_ventas=Count('id'),
                valor_total=Sum('valor_total')
            )

            # ✅ CORRECCIÓN: Calcular promedio manualmente
            total_ventas_count = ventas_mes['total_ventas'] or 0
            valor_total_ventas = ventas_mes['valor_total'] or 0

            if total_ventas_count > 0:
                venta_promedio = valor_total_ventas / total_ventas_count
            else:
                venta_promedio = 0

            # ✅ CORRECCIÓN CRÍTICA: OBTENER TODOS LOS ARTÍCULOS SIN LÍMITE CUANDO PIDE "TODAS"
            consulta_lower = consulta.lower()
            if any(palabra in consulta_lower for palabra in ['todas', 'todos', 'completo', 'completa', 'todas las', 'todos los']):
                # SIN LÍMITE - TODAS LAS REFERENCIAS
                articulos_mes = query.values('articulo_codigo', 'articulo_nombre').annotate(
                    cantidad_vendida=Sum('cantidad'),
                    valor_total=Sum('valor_total')
                ).order_by('-cantidad_vendida')

                mensaje_articulos = f'TODAS las referencias de artículos vendidos en {mes_nombre} {anio}'
            else:
                # Límite por defecto (5 artículos) para consultas normales
                articulos_mes = query.values('articulo_codigo', 'articulo_nombre').annotate(
                    cantidad_vendida=Sum('cantidad'),
                    valor_total=Sum('valor_total')
                ).order_by('-cantidad_vendida')[:5]

                mensaje_articulos = f'Principales artículos vendidos en {mes_nombre} {anio}'

            # Convertir a lista para serialización
            articulos_lista = list(articulos_mes)

            # ✅ MENSAJE SEGÚN CONTEXTO
            if es_consolidado:
                mensaje_articulos += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'ventas_por_mes',
                'mes': mes_nombre,
                'anio': anio,
                'total_articulos_vendidos': ventas_mes['total_articulos'] or 0,
                'total_ventas': total_ventas_count,
                'valor_total': float(valor_total_ventas),
                'venta_promedio': float(venta_promedio),
                'articulos': articulos_lista,
                'total_referencias_encontradas': len(articulos_lista),
                'mostrando_todas_referencias': any(palabra in consulta_lower for palabra in ['todas', 'todos', 'completo']),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje_articulos
            }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error consultando ventas por mes: {str(e)}'}

    def _consultar_ventas_por_anio(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta ventas por año específico - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            anio = self._extraer_anio(consulta)

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                fecha__year=anio,
                tipo_documento='FACTURA_VENTA'
            )

            ventas_anio = query.aggregate(
                total_articulos=Sum('cantidad'),
                total_ventas=Count('id'),
                valor_total=Sum('valor_total')
            )

            # ✅ CORRECCIÓN: Calcular promedio manualmente
            total_ventas_count = ventas_anio['total_ventas'] or 0
            valor_total_ventas = ventas_anio['valor_total'] or 0

            if total_ventas_count > 0:
                venta_promedio = valor_total_ventas / total_ventas_count
            else:
                venta_promedio = 0

            # Ventas por mes del año - ADAPTADA
            ventas_por_mes = query.annotate(
                mes=TruncMonth('fecha')
            ).values('mes').annotate(
                total_ventas=Count('id'),
                valor_total=Sum('valor_total')
            ).order_by('mes')

            # ✅ MENSAJE SEGÚN CONTEXTO
            mensaje = f'Ventas del año {anio}'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'ventas_por_anio',
                'anio': anio,
                'total_articulos_vendidos': ventas_anio['total_articulos'] or 0,
                'total_ventas': total_ventas_count,
                'valor_total': float(valor_total_ventas),
                'venta_promedio': float(venta_promedio),
                'ventas_por_mes': list(ventas_por_mes),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error consultando ventas por año: {str(e)}'}

    def _consultar_ventas_recientes(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta ventas de los últimos días/meses - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            consulta_lower = consulta.lower()

            if 'día' in consulta_lower or 'dia' in consulta_lower:
                dias = 1
            elif 'semana' in consulta_lower:
                dias = 7
            elif 'mes' in consulta_lower:
                dias = 30
            else:
                dias = 30  # Por defecto último mes

            fecha_limite = timezone.now() - timedelta(days=dias)

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                fecha__gte=fecha_limite,
                tipo_documento='FACTURA_VENTA'
            )

            ventas_recientes = query.aggregate(
                total_articulos=Sum('cantidad'),
                total_ventas=Count('id'),
                valor_total=Sum('valor_total')
            )

            # ✅ CORRECCIÓN: Calcular promedio manualmente
            total_ventas_count = ventas_recientes['total_ventas'] or 0
            valor_total_ventas = ventas_recientes['valor_total'] or 0

            if total_ventas_count > 0:
                venta_promedio = valor_total_ventas / total_ventas_count
            else:
                venta_promedio = 0

            # Artículos más vendidos recientemente - ADAPTADO
            articulos_recientes = query.values('articulo_codigo', 'articulo_nombre').annotate(
                cantidad_vendida=Sum('cantidad')
            ).order_by('-cantidad_vendida')[:5]

            # ✅ MENSAJE SEGÚN CONTEXTO
            mensaje = f'Ventas de los últimos {dias} días'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'ventas_recientes',
                'periodo': f'últimos {dias} días',
                'total_articulos_vendidos': ventas_recientes['total_articulos'] or 0,
                'total_ventas': total_ventas_count,
                'valor_total': float(valor_total_ventas),
                'venta_promedio': float(venta_promedio),
                'articulos_populares': list(articulos_recientes),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error consultando ventas recientes: {str(e)}'}


    def _consultar_ventas_por_rango_fechas(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta ventas por rango de fechas específico - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Para consultas por rango de fechas, si es consolidado, usar solo la primera empresa
            if es_consolidado and len(empresas_ids) > 1:
                logger.warning("⚠️ Consulta por rango de fechas con múltiples empresas, usando solo la primera")
                empresas_ids = [empresas_ids[0]]
                es_consolidado = False

            # Extraer fechas de la consulta (esto es simplificado)
            fechas = re.findall(r'\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}', consulta)

            if len(fechas) < 2:
                return {'error': 'No se pudieron identificar las fechas en el formato DD/MM/AAAA o AAAA-MM-DD'}

            fecha_inicio = datetime.strptime(fechas[0], '%d/%m/%Y' if '/' in fechas[0] else '%Y-%m-%d')
            fecha_fin = datetime.strptime(fechas[1], '%d/%m/%Y' if '/' in fechas[1] else '%Y-%m-%d')

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                fecha__range=[fecha_inicio, fecha_fin],
                tipo_documento='FACTURA_VENTA'
            )

            ventas_rango = query.aggregate(
                total_articulos=Sum('cantidad'),
                total_ventas=Count('id'),
                valor_total=Sum('valor_total')
            )

            # ✅ CORRECCIÓN: Calcular promedio manualmente
            total_ventas_count = ventas_rango['total_ventas'] or 0
            valor_total_ventas = ventas_rango['valor_total'] or 0

            if total_ventas_count > 0:
                venta_promedio = valor_total_ventas / total_ventas_count
            else:
                venta_promedio = 0

            # ✅ MENSAJE SEGÚN CONTEXTO
            mensaje = f'Ventas desde {fecha_inicio.strftime("%d/%m/%Y")} hasta {fecha_fin.strftime("%d/%m/%Y")}'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'ventas_por_rango_fechas',
                'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
                'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
                'total_articulos_vendidos': ventas_rango['total_articulos'] or 0,
                'total_ventas': total_ventas_count,
                'valor_total': float(valor_total_ventas),
                'venta_promedio': float(venta_promedio),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error consultando ventas por rango de fechas: {str(e)}'}

    # ========== MÉTODOS DE CONSULTA POR ARTÍCULOS ==========
    def _extraer_periodo_consulta(self, consulta):
        """Extrae el período de la consulta y retorna fechas válidas"""
        from datetime import datetime

        consulta_lower = consulta.lower()
        ahora = datetime.now()

        # ✅ DETECTAR PRIMER SEMESTRE 2025
        if 'primer semestre de 2025' in consulta_lower or 'primer semestre 2025' in consulta_lower:
            return {
                'fecha_inicio': datetime(2025, 1, 1),
                'fecha_fin': datetime(2025, 6, 30),
                'descripcion': 'primer semestre de 2025',
                'es_futuro': True
            }

        # ✅ DETECTAR AÑO COMPLETO
        anios = re.findall(r'20\d{2}', consulta)
        if anios:
            anio = int(anios[0])
            if anio > ahora.year:
                return {
                    'fecha_inicio': datetime(anio, 1, 1),
                    'fecha_fin': datetime(anio, 12, 31),
                    'descripcion': f'año {anio}',
                    'es_futuro': True
                }
            else:
                return {
                    'fecha_inicio': datetime(anio, 1, 1),
                    'fecha_fin': datetime(anio, 12, 31),
                    'descripcion': f'año {anio}',
                    'es_futuro': False
                }

        # ✅ DETECTAR SEMESTRES
        if 'primer semestre' in consulta_lower:
            anio = ahora.year
            return {
                'fecha_inicio': datetime(anio, 1, 1),
                'fecha_fin': datetime(anio, 6, 30),
                'descripcion': 'primer semestre',
                'es_futuro': ahora.month <= 6  # Es futuro si estamos antes de julio
            }

        if 'segundo semestre' in consulta_lower:
            anio = ahora.year
            return {
                'fecha_inicio': datetime(anio, 7, 1),
                'fecha_fin': datetime(anio, 12, 31),
                'descripcion': 'segundo semestre',
                'es_futuro': ahora.month < 7  # Es futuro si estamos antes de julio
            }

        # ✅ POR DEFECTO: ÚLTIMOS 12 MESES
        fecha_inicio_default = datetime(ahora.year - 1, ahora.month, ahora.day)
        return {
            'fecha_inicio': fecha_inicio_default,
            'fecha_fin': ahora,
            'descripcion': 'los últimos 12 meses',
            'es_futuro': False
        }
    
    def _consultar_articulos_mas_vendidos(self, consulta, empresa_servidor_id=None, request=None):
        try:
            from apps.sistema_analitico.models import MovimientoInventario
            from django.db.models import Sum, Count, Avg, Min, Max
            from django.db.models import Q

            print(f"🔍 INICIANDO CONSULTA ARTÍCULOS MÁS VENDIDOS")
            print(f"🔍 Consulta: {consulta}")
            print(f"🔍 Empresa ID recibido: {empresa_servidor_id}")

            # ✅ Obtener TODAS las empresas del NIT (no solo una)
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)
            print(f"🔍 Empresas a consultar: {empresas_ids}")
            print(f"🔍 ¿Es consolidado?: {es_consolidado}")

            # Extraer periodo
            periodo_info = self._extraer_periodo_consulta(consulta)
            print(f"🔍 Periodo extraído: {periodo_info}")

            # ✅ VERIFICAR DATOS EN TODAS LAS EMPRESAS DEL NIT
            print(f"🔍 VERIFICANDO DATOS EN BD PARA TODAS LAS EMPRESAS:")

            for emp_id in empresas_ids:
                total_empresa = MovimientoInventario.objects.filter(
                    empresa_servidor_id=emp_id
                ).count()
                print(f"   - Empresa {emp_id}: {total_empresa} registros")

            # Total en TODAS las empresas
            total_sin_filtros = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids
            ).count()
            print(f"   - TOTAL en todas las empresas: {total_sin_filtros} registros")

            # Total ventas en TODAS las empresas
            total_ventas = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                tipo_documento='FACTURA_VENTA'
            ).count()
            print(f"   - TOTAL ventas en todas las empresas: {total_ventas}")

            # Rango de fechas en TODA la base de datos
            rango_fechas = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids
            ).aggregate(
                min_fecha=Min('fecha'),
                max_fecha=Max('fecha')
            )
            print(f"   - Rango fechas en BD: {rango_fechas}")

            # Registros del periodo específico en TODAS las empresas
            registros_periodo = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                fecha__range=[periodo_info['fecha_inicio'], periodo_info['fecha_fin']]
            ).count()
            print(f"   - Registros en periodo consultado: {registros_periodo}")

            # ✅ CONSULTA REAL EN TODAS LAS EMPRESAS
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,  # ✅ TODAS las empresas del NIT
                cantidad__gt=0,
                tipo_documento='FACTURA_VENTA',
                fecha__range=[periodo_info['fecha_inicio'], periodo_info['fecha_fin']]
            )

            print(f"🔍 EJECUTANDO QUERY CON FILTROS:")
            print(f"   - Empresas: {empresas_ids}")
            print(f"   - Fecha inicio: {periodo_info['fecha_inicio']}")
            print(f"   - Fecha fin: {periodo_info['fecha_fin']}")

            total_query = query.count()
            print(f"🔍 TOTAL REGISTROS EN QUERY: {total_query}")

            # Si no hay resultados, verificar qué hay sin filtros
            if total_query == 0:
                print(f"🔍 BUSCANDO SIN FILTRO DE FECHA:")
                query_sin_fecha = MovimientoInventario.objects.filter(
                    empresa_servidor_id__in=empresas_ids,
                    cantidad__gt=0,
                    tipo_documento='FACTURA_VENTA'
                )
                total_sin_fecha = query_sin_fecha.count()
                print(f"   - Total sin fecha: {total_sin_fecha}")

            # Continuar con la consulta normal
            resultados_query = query.values('articulo_codigo', 'articulo_nombre').annotate(
                total_vendido=Sum('cantidad'),
                total_valor=Sum('valor_total'),
                transacciones=Count('id'),
                precio_promedio=Avg('precio_unitario')
            ).order_by('-total_vendido')

            total_articulos = resultados_query.count()
            print(f"🔍 TOTAL ARTÍCULOS ENCONTRADOS: {total_articulos}")

            limite = self._extraer_limite_consulta(consulta)
            if limite is not None:
                resultados_query = resultados_query[:limite]

            resultados_lista = []
            for item in resultados_query:
                resultados_lista.append({
                    'articulo_codigo': item['articulo_codigo'],
                    'articulo_nombre': item['articulo_nombre'],
                    'total_vendido': float(item['total_vendido'] or 0),
                    'total_valor': float(item['total_valor'] or 0),
                    'transacciones': item['transacciones'],
                    'precio_promedio': float(item['precio_promedio'] or 0)
                })

            print(f"🔍 RESULTADOS FINALES: {len(resultados_lista)} artículos")

            # Mensaje
            if total_articulos == 0:
                mensaje = f"No se encontraron ventas en el período {periodo_info['descripcion']} para las empresas consultadas"
            else:
                mensaje = f"Top {len(resultados_lista)} artículos más vendidos en {periodo_info['descripcion']}"

            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'historico_articulos_mas_vendidos',
                'resultados': resultados_lista,
                'total_articulos': total_articulos,
                'limite_aplicado': limite,
                'mostrando': len(resultados_lista),
                'periodo_consulta': periodo_info,
                'empresas_consultadas': empresas_ids,  # ✅ Lista completa de empresas
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except Exception as e:
            print(f"❌ ERROR en _consultar_articulos_mas_vendidos: {str(e)}")
            return {'error': f'Error en la consulta: {str(e)}'}
    
    def _consultar_articulos_menos_vendidos(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta los artículos menos vendidos - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # ✅ DETECTAR LÍMITE INTELIGENTE
            limite = self._extraer_limite_consulta(consulta)

            # Consulta base - ADAPTADA PARA MÚLTIPLES EMPRESAS
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                cantidad__gt=0,
                tipo_documento='FACTURA_VENTA'
            )

            resultados_query = query.values('articulo_codigo', 'articulo_nombre').annotate(
                total_vendido=Sum('cantidad'),
                total_valor=Sum('valor_total'),
                transacciones=Count('id')
            ).order_by('total_vendido')  # Orden ascendente para menos vendidos

            # ✅ CALCULAR TOTAL REAL
            total_articulos = resultados_query.count()

            # ✅ APLICAR LÍMITE SI ES NECESARIO
            if limite is not None:
                resultados_query = resultados_query[:limite]

            resultados_lista = []
            for item in resultados_query:
                resultados_lista.append({
                    'articulo_codigo': item['articulo_codigo'],
                    'articulo_nombre': item['articulo_nombre'],
                    'total_vendido': float(item['total_vendido'] or 0),
                    'total_valor': float(item['total_valor'] or 0),
                    'transacciones': item['transacciones']
                })

            # ✅ MENSAJE INTELIGENTE SEGÚN CONTEXTO
            if es_consolidado:
                mensaje = f'Top {len(resultados_lista)} artículos menos vendidos (consolidado {len(empresas_ids)} empresas)'
                if limite is None:
                    mensaje = f'Todos los artículos vendidos - menos vendidos primero ({total_articulos} total) - consolidado {len(empresas_ids)} empresas'
            else:
                mensaje = f'Top {len(resultados_lista)} artículos menos vendidos'
                if limite is None:
                    mensaje = f'Todos los artículos vendidos - menos vendidos primero ({total_articulos} total)'

            return {
                'tipo_consulta': 'historico_articulos_menos_vendidos',
                'resultados': resultados_lista,
                'total_articulos': total_articulos,
                'limite_aplicado': limite,
                'mostrando': len(resultados_lista),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error consultando artículos menos vendidos: {str(e)}'}

    def _consultar_articulos_mas_caros(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta los artículos con mayor precio unitario - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # ✅ DETECTAR LÍMITE INTELIGENTE
            limite = self._extraer_limite_consulta(consulta)

            # Consulta base - ADAPTADA PARA MÚLTIPLES EMPRESAS
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                precio_unitario__isnull=False
            )

            resultados_query = query.values('articulo_codigo', 'articulo_nombre').annotate(
                precio_maximo=Max('precio_unitario'),
                precio_minimo=Min('precio_unitario'),
                precio_promedio=Avg('precio_unitario'),
                transacciones=Count('id')
            ).order_by('-precio_maximo')

            # ✅ CALCULAR TOTAL REAL
            total_articulos = resultados_query.count()

            # ✅ APLICAR LÍMITE SI ES NECESARIO
            if limite is not None:
                resultados_query = resultados_query[:limite]

            resultados_lista = []
            for item in resultados_query:
                resultados_lista.append({
                    'articulo_codigo': item['articulo_codigo'],
                    'articulo_nombre': item['articulo_nombre'],
                    'precio_maximo': float(item['precio_maximo'] or 0),
                    'precio_minimo': float(item['precio_minimo'] or 0),
                    'precio_promedio': float(item['precio_promedio'] or 0),
                    'transacciones': item['transacciones']
                })

            # ✅ MENSAJE INTELIGENTE SEGÚN CONTEXTO
            if es_consolidado:
                mensaje = f'Top {len(resultados_lista)} artículos con mayor precio (consolidado {len(empresas_ids)} empresas)'
                if limite is None:
                    mensaje = f'Todos los artículos ordenados por precio ({total_articulos} total) - consolidado {len(empresas_ids)} empresas'
            else:
                mensaje = f'Top {len(resultados_lista)} artículos con mayor precio'
                if limite is None:
                    mensaje = f'Todos los artículos ordenados por precio ({total_articulos} total)'

            return {
                'tipo_consulta': 'historico_articulos_mas_caros',
                'resultados': resultados_lista,
                'total_articulos': total_articulos,
                'limite_aplicado': limite,
                'mostrando': len(resultados_lista),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error consultando artículos más caros: {str(e)}'}

    def _buscar_articulo(self, consulta, empresa_servidor_id=None, request=None):
        """Busca un artículo específico por nombre o código - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Extraer términos de búsqueda
            terminos = consulta.lower().replace('buscar artículo', '').replace('buscar articulo', '').strip()

            if not terminos:
                return {'error': 'Por favor especifica qué artículo buscas'}

            # ✅ DETECTAR LÍMITE INTELIGENTE
            limite = self._extraer_limite_consulta(consulta)

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids
            ).filter(
                Q(articulo_nombre__icontains=terminos) | 
                Q(articulo_codigo__icontains=terminos)
            )

            resultados_query = query.values('articulo_codigo', 'articulo_nombre').annotate(
                total_vendido=Sum('cantidad', filter=Q(tipo_documento='FACTURA_VENTA')),
                total_comprado=Sum('cantidad', filter=Q(tipo_documento='FACTURA_COMPRA')),
                precio_promedio=Avg('precio_unitario'),
                primera_venta=Min('fecha', filter=Q(tipo_documento='FACTURA_VENTA')),
                ultima_venta=Max('fecha', filter=Q(tipo_documento='FACTURA_VENTA'))
            ).order_by('-total_vendido')

            # ✅ CALCULAR TOTAL REAL
            total_encontrados = resultados_query.count()

            # ✅ APLICAR LÍMITE SI ES NECESARIO
            if limite is not None:
                resultados_query = resultados_query[:limite]

            resultados_lista = list(resultados_query)

            # ✅ MENSAJE INTELIGENTE SEGÚN CONTEXTO
            mensaje = f'Se encontraron {total_encontrados} artículos para "{terminos}"'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'
            if limite is not None and total_encontrados > limite:
                mensaje = f'Se encontraron {total_encontrados} artículos para "{terminos}", mostrando {limite}'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'buscar_articulo',
                'termino_busqueda': terminos,
                'resultados': resultados_lista,
                'total_encontrados': total_encontrados,
                'limite_aplicado': limite,
                'mostrando': len(resultados_lista),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error buscando artículo: {str(e)}'}

    def _consultar_articulos_por_categoria(self, empresa_servidor_id=None, request=None):
        """Consulta artículos por categorías (implantes, instrumental, equipo poder) - ADAPTADO"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids
            )

            categorias = {
                'implantes': query.filter(es_implante=True),
                'instrumental': query.filter(es_instrumental=True),
                'equipo_poder': query.filter(es_equipo_poder=True)
            }

            resultados = {}
            for categoria, queryset in categorias.items():
                stats = queryset.aggregate(
                    total_articulos=Sum('cantidad'),
                    total_valor=Sum('valor_total'),
                    total_transacciones=Count('id'),
                    precio_promedio=Avg('precio_unitario')
                )

                resultados[categoria] = {
                    'total_articulos': stats['total_articulos'] or 0,
                    'total_valor': float(stats['total_valor'] or 0),
                    'total_transacciones': stats['total_transacciones'] or 0,
                    'precio_promedio': float(stats['precio_promedio'] or 0)
                }

            # ✅ MENSAJE SEGÚN CONTEXTO
            mensaje = 'Estadísticas por categorías de artículos'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'articulos_por_categoria',
                'resultados': resultados,
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error consultando artículos por categoría: {str(e)}'}
    # ========== MÉTODOS DE CONSULTA POR PERSONAS/ENTIDADES ==========
    def _consultar_por_nit(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta por NIT de pagador - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Extraer NIT de la consulta
            nit_match = re.search(r'[0-9]{6,15}', consulta)
            if not nit_match:
                return {'error': 'No se pudo identificar el NIT en la consulta'}

            nit = nit_match.group()

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                nit_pagador=nit
            )

            resultados = query.values('nit_pagador', 'pagador').annotate(
                total_compras=Count('id'),
                monto_total=Sum('valor_total'),
                primera_compra=Min('fecha'),
                ultima_compra=Max('fecha')
            ).order_by('-monto_total')

            if not resultados:
                return {'error': f'No se encontraron transacciones para el NIT {nit}'}

            # ✅ MENSAJE SEGÚN CONTEXTO
            mensaje = f'Transacciones encontradas para NIT {nit}'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'consulta_por_nit',
                'nit': nit,
                'resultados': list(resultados),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error consultando por NIT: {str(e)}'}

    def _consultar_por_cedula(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta por cédula de paciente o médico - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Extraer cédula de la consulta
            cedula_match = re.search(r'[0-9]{6,12}', consulta)
            if not cedula_match:
                return {'error': 'No se pudo identificar la cédula en la consulta'}

            cedula = cedula_match.group()

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids
            )

            # Buscar como paciente
            como_paciente = query.filter(
                cedula_paciente=cedula
            ).aggregate(
                total_transacciones=Count('id'),
                monto_total=Sum('valor_total')
            )

            # Buscar como médico
            como_medico = query.filter(
                Q(cedula_medico=cedula) | Q(cedula_medico2=cedula)
            ).aggregate(
                total_procedimientos=Count('id'),
                monto_total=Sum('valor_total')
            )

            # ✅ MENSAJE SEGÚN CONTEXTO
            mensaje = f'Resultados para cédula {cedula}'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'consulta_por_cedula',
                'cedula': cedula,
                'como_paciente': {
                    'total_transacciones': como_paciente['total_transacciones'] or 0,
                    'monto_total': float(como_paciente['monto_total'] or 0)
                },
                'como_medico': {
                    'total_procedimientos': como_medico['total_procedimientos'] or 0,
                    'monto_total': float(como_medico['monto_total'] or 0)
                },
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error consultando por cédula: {str(e)}'}

    def _consultar_por_medico(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta por médico - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Extraer nombre del médico
            nombre_medico = consulta.lower().replace('doctor', '').replace('médico', '').replace('medico', '').replace('dr.', '').replace('dra.', '').strip()

            if not nombre_medico:
                # ✅ SI NO SE ESPECIFICA NOMBRE, MOSTRAR TOP MÉDICOS CON LÍMITES INTELIGENTES
                limite = self._extraer_limite_consulta(consulta)

                # Consulta base - ADAPTADA
                query = MovimientoInventario.objects.filter(
                    empresa_servidor_id__in=empresas_ids
                ).exclude(Q(medico='') | Q(medico__isnull=True))

                resultados_query = query.values(
                    'medico', 'cedula_medico'
                ).annotate(
                    total_procedimientos=Count('id'),
                    monto_total=Sum('valor_total')
                ).order_by('-total_procedimientos')

                # ✅ CALCULAR TOTAL REAL
                total_medicos = resultados_query.count()

                # ✅ APLICAR LÍMITE SI ES NECESARIO
                if limite is not None:
                    resultados_query = resultados_query[:limite]

                resultados_lista = list(resultados_query)

                # ✅ MENSAJE INTELIGENTE SEGÚN CONTEXTO
                mensaje = f'Top {len(resultados_lista)} médicos con más procedimientos'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'
                if limite is None:
                    mensaje = f'Todos los médicos ({total_medicos} total)'
                    if es_consolidado:
                        mensaje += f' (consolidado {len(empresas_ids)} empresas)'
                elif limite == 1:
                    mensaje = 'Médico con más procedimientos'
                    if es_consolidado:
                        mensaje += f' (consolidado {len(empresas_ids)} empresas)'

                return {
                    'tipo_consulta': 'top_medicos',
                    'resultados': resultados_lista,
                    'total_medicos': total_medicos,
                    'limite_aplicado': limite,
                    'mostrando': len(resultados_lista),
                    'empresas_consultadas': len(empresas_ids),
                    'consolidado': es_consolidado,
                    'mensaje': mensaje
                }
            else:
                # ✅ BUSCAR MÉDICO ESPECÍFICO (ADAPTADO)
                query = MovimientoInventario.objects.filter(
                    empresa_servidor_id__in=empresas_ids,
                    medico__icontains=nombre_medico
                )

                resultados = query.values('medico', 'cedula_medico').annotate(
                    total_procedimientos=Count('id'),
                    monto_total=Sum('valor_total'),
                    primer_procedimiento=Min('fecha'),
                    ultimo_procedimiento=Max('fecha')
                )

                total_encontrados = resultados.count()

                # ✅ MENSAJE SEGÚN CONTEXTO
                mensaje = f'Resultados para médico {nombre_medico} ({total_encontrados} encontrados)'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'

                return {
                    'tipo_consulta': 'consulta_por_medico',
                    'medico': nombre_medico,
                    'resultados': list(resultados),
                    'total_encontrados': total_encontrados,
                    'empresas_consultadas': len(empresas_ids),
                    'consolidado': es_consolidado,
                    'mensaje': mensaje
                }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error consultando por médico: {str(e)}'}

    def _consultar_por_paciente(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta por paciente - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Extraer nombre del paciente
            nombre_paciente = consulta.lower().replace('paciente', '').strip()

            if not nombre_paciente:
                # ✅ SI NO SE ESPECIFICA NOMBRE, MOSTRAR TOP PACIENTES CON LÍMITES INTELIGENTES
                limite = self._extraer_limite_consulta(consulta)

                # Consulta base - ADAPTADA
                query = MovimientoInventario.objects.filter(
                    empresa_servidor_id__in=empresas_ids
                ).exclude(Q(paciente='') | Q(paciente__isnull=True))

                resultados_query = query.values(
                    'paciente', 'cedula_paciente'
                ).annotate(
                    total_transacciones=Count('id'),
                    monto_total=Sum('valor_total')
                ).order_by('-monto_total')

                # ✅ CALCULAR TOTAL REAL
                total_pacientes = resultados_query.count()

                # ✅ APLICAR LÍMITE SI ES NECESARIO
                if limite is not None:
                    resultados_query = resultados_query[:limite]

                resultados_lista = list(resultados_query)

                # ✅ MENSAJE INTELIGENTE SEGÚN CONTEXTO
                mensaje = f'Top {len(resultados_lista)} pacientes por monto total'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'
                if limite is None:
                    mensaje = f'Todos los pacientes ({total_pacientes} total)'
                    if es_consolidado:
                        mensaje += f' (consolidado {len(empresas_ids)} empresas)'
                elif limite == 1:
                    mensaje = 'Paciente con mayor monto total'
                    if es_consolidado:
                        mensaje += f' (consolidado {len(empresas_ids)} empresas)'

                return {
                    'tipo_consulta': 'top_pacientes',
                    'resultados': resultados_lista,
                    'total_pacientes': total_pacientes,
                    'limite_aplicado': limite,
                    'mostrando': len(resultados_lista),
                    'empresas_consultadas': len(empresas_ids),
                    'consolidado': es_consolidado,
                    'mensaje': mensaje
                }
            else:
                # ✅ BUSCAR PACIENTE ESPECÍFICO (ADAPTADO)
                query = MovimientoInventario.objects.filter(
                    empresa_servidor_id__in=empresas_ids,
                    paciente__icontains=nombre_paciente
                )

                resultados = query.values('paciente', 'cedula_paciente').annotate(
                    total_transacciones=Count('id'),
                    monto_total=Sum('valor_total'),
                    primera_visita=Min('fecha'),
                    ultima_visita=Max('fecha')
                )

                total_encontrados = resultados.count()

                # ✅ MENSAJE SEGÚN CONTEXTO
                mensaje = f'Resultados para paciente {nombre_paciente} ({total_encontrados} encontrados)'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'

                return {
                    'tipo_consulta': 'consulta_por_paciente',
                    'paciente': nombre_paciente,
                    'resultados': list(resultados),
                    'total_encontrados': total_encontrados,
                    'empresas_consultadas': len(empresas_ids),
                    'consolidado': es_consolidado,
                    'mensaje': mensaje
                }

        except Exception as e:
            return {'error': f'Error consultando por paciente: {str(e)}'}

    def _consultar_por_clinica(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta por clínica - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Extraer nombre de la clínica
            nombre_clinica = consulta.lower().replace('clínica', '').replace('clinica', '').replace('hospital', '').strip()

            if not nombre_clinica:
                # ✅ SI NO SE ESPECIFICA NOMBRE, MOSTRAR TOP CLÍNICAS CON LÍMITES INTELIGENTES
                limite = self._extraer_limite_consulta(consulta)

                # Consulta base - ADAPTADA
                query = MovimientoInventario.objects.filter(
                    empresa_servidor_id__in=empresas_ids
                ).exclude(Q(clinica='') | Q(clinica__isnull=True))

                resultados_query = query.values(
                    'clinica', 'nit_clinica'
                ).annotate(
                    total_transacciones=Count('id'),
                    monto_total=Sum('valor_total')
                ).order_by('-monto_total')

                # ✅ CALCULAR TOTAL REAL
                total_clinicas = resultados_query.count()

                # ✅ APLICAR LÍMITE SI ES NECESARIO
                if limite is not None:
                    resultados_query = resultados_query[:limite]

                resultados_lista = list(resultados_query)

                # ✅ MENSAJE INTELIGENTE SEGÚN CONTEXTO
                mensaje = f'Top {len(resultados_lista)} clínicas por monto total'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'
                if limite is None:
                    mensaje = f'Todas las clínicas ({total_clinicas} total)'
                    if es_consolidado:
                        mensaje += f' (consolidado {len(empresas_ids)} empresas)'
                elif limite == 1:
                    mensaje = 'Clínica con mayor monto total'
                    if es_consolidado:
                        mensaje += f' (consolidado {len(empresas_ids)} empresas)'

                return {
                    'tipo_consulta': 'top_clinicas',
                    'resultados': resultados_lista,
                    'total_clinicas': total_clinicas,
                    'limite_aplicado': limite,
                    'mostrando': len(resultados_lista),
                    'empresas_consultadas': len(empresas_ids),
                    'consolidado': es_consolidado,
                    'mensaje': mensaje
                }
            else:
                # ✅ BUSCAR CLÍNICA ESPECÍFICA (ADAPTADO)
                query = MovimientoInventario.objects.filter(
                    empresa_servidor_id__in=empresas_ids,
                    clinica__icontains=nombre_clinica
                )

                resultados = query.values('clinica', 'nit_clinica').annotate(
                    total_transacciones=Count('id'),
                    monto_total=Sum('valor_total'),
                    primera_transaccion=Min('fecha'),
                    ultima_transaccion=Max('fecha')
                )

                total_encontrados = resultados.count()

                # ✅ MENSAJE SEGÚN CONTEXTO
                mensaje = f'Resultados para clínica {nombre_clinica} ({total_encontrados} encontrados)'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'

                return {
                    'tipo_consulta': 'consulta_por_clinica',
                    'clinica': nombre_clinica,
                    'resultados': list(resultados),
                    'total_encontrados': total_encontrados,
                    'empresas_consultadas': len(empresas_ids),
                    'consolidado': es_consolidado,
                    'mensaje': mensaje
                }

        except Exception as e:
            return {'error': f'Error consultando por clínica: {str(e)}'}

    def _consultar_por_pagador(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta por pagador (EPS, ARS, aseguradora) - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Extraer nombre del pagador
            nombre_pagador = consulta.lower().replace('pagador', '').replace('eps', '').replace('ars', '').replace('aseguradora', '').strip()

            if not nombre_pagador:
                # ✅ SI NO SE ESPECIFICA NOMBRE, MOSTRAR TOP PAGADORES CON LÍMITES INTELIGENTES
                limite = self._extraer_limite_consulta(consulta)

                # Consulta base - ADAPTADA
                query = MovimientoInventario.objects.filter(
                    empresa_servidor_id__in=empresas_ids
                ).exclude(Q(pagador='') | Q(pagador__isnull=True))

                resultados_query = query.values(
                    'pagador', 'nit_pagador'
                ).annotate(
                    total_transacciones=Count('id'),
                    monto_total=Sum('valor_total')
                ).order_by('-monto_total')

                # ✅ CALCULAR TOTAL REAL
                total_pagadores = resultados_query.count()

                # ✅ APLICAR LÍMITE SI ES NECESARIO
                if limite is not None:
                    resultados_query = resultados_query[:limite]

                resultados_lista = list(resultados_query)

                # ✅ MENSAJE INTELIGENTE SEGÚN CONTEXTO
                mensaje = f'Top {len(resultados_lista)} pagadores por monto total'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'
                if limite is None:
                    mensaje = f'Todos los pagadores ({total_pagadores} total)'
                    if es_consolidado:
                        mensaje += f' (consolidado {len(empresas_ids)} empresas)'
                elif limite == 1:
                    mensaje = 'Pagador con mayor monto total'
                    if es_consolidado:
                        mensaje += f' (consolidado {len(empresas_ids)} empresas)'

                return {
                    'tipo_consulta': 'top_pagadores',
                    'resultados': resultados_lista,
                    'total_pagadores': total_pagadores,
                    'limite_aplicado': limite,
                    'mostrando': len(resultados_lista),
                    'empresas_consultadas': len(empresas_ids),
                    'consolidado': es_consolidado,
                    'mensaje': mensaje
                }
            else:
                # ✅ BUSCAR PAGADOR ESPECÍFICO (ADAPTADO)
                query = MovimientoInventario.objects.filter(
                    empresa_servidor_id__in=empresas_ids,
                    pagador__icontains=nombre_pagador
                )

                resultados = query.values('pagador', 'nit_pagador').annotate(
                    total_transacciones=Count('id'),
                    monto_total=Sum('valor_total'),
                    primera_transaccion=Min('fecha'),
                    ultima_transaccion=Max('fecha')
                )

                total_encontrados = resultados.count()

                # ✅ MENSAJE SEGÚN CONTEXTO
                mensaje = f'Resultados para pagador {nombre_pagador} ({total_encontrados} encontrados)'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'

                return {
                    'tipo_consulta': 'consulta_por_pagador',
                    'pagador': nombre_pagador,
                    'resultados': list(resultados),
                    'total_encontrados': total_encontrados,
                    'empresas_consultadas': len(empresas_ids),
                    'consolidado': es_consolidado,
                    'mensaje': mensaje
                }

        except Exception as e:
            return {'error': f'Error consultando por pagador: {str(e)}'}
    # ========== MÉTODOS DE CONSULTA POR UBICACIONES ==========
    def _consultar_ventas_por_ciudad(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta ventas por ciudad - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # ✅ DETECTAR LÍMITE INTELIGENTE
            limite = self._extraer_limite_consulta(consulta)

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                tipo_documento='FACTURA_VENTA'
            ).exclude(Q(ciudad='') | Q(ciudad__isnull=True))

            resultados_query = query.values(
                'ciudad', 'codigo_ciudad'
            ).annotate(
                total_ventas=Count('id'),
                total_articulos=Sum('cantidad'),
                valor_total=Sum('valor_total')
            ).order_by('-valor_total')

            # ✅ CALCULAR TOTAL REAL
            total_ciudades = resultados_query.count()

            # ✅ APLICAR LÍMITE SI ES NECESARIO
            if limite is not None:
                resultados_query = resultados_query[:limite]

            resultados_lista = list(resultados_query)

            # ✅ MENSAJE INTELIGENTE SEGÚN CONTEXTO
            mensaje = f'Ventas por ciudad ({len(resultados_lista)} de {total_ciudades} ciudades)'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'
            if limite is None:
                mensaje = f'Ventas por todas las ciudades ({total_ciudades} total)'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'ventas_por_ciudad',
                'resultados': resultados_lista,
                'total_ciudades': total_ciudades,
                'limite_aplicado': limite,
                'mostrando': len(resultados_lista),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except Exception as e:
            return {'error': f'Error consultando ventas por ciudad: {str(e)}'}

    def _consultar_ventas_por_bodega(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta ventas por bodega - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # ✅ DETECTAR LÍMITE INTELIGENTE
            limite = self._extraer_limite_consulta(consulta)

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                tipo_documento='FACTURA_VENTA'
            ).exclude(Q(tipo_bodega='') | Q(tipo_bodega__isnull=True))

            resultados_query = query.values(
                'tipo_bodega', 'codigo_bodega', 'sistema_bodega'
            ).annotate(
                total_ventas=Count('id'),
                total_articulos=Sum('cantidad'),
                valor_total=Sum('valor_total')
            ).order_by('-valor_total')

            # ✅ CALCULAR TOTAL REAL
            total_bodegas = resultados_query.count()

            # ✅ APLICAR LÍMITE SI ES NECESARIO
            if limite is not None:
                resultados_query = resultados_query[:limite]

            resultados_lista = list(resultados_query)

            # ✅ MENSAJE INTELIGENTE SEGÚN CONTEXTO
            mensaje = f'Ventas por bodega ({len(resultados_lista)} de {total_bodegas} bodegas)'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'
            if limite is None:
                mensaje = f'Ventas por todas las bodegas ({total_bodegas} total)'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'ventas_por_bodega',
                'resultados': resultados_lista,
                'total_bodegas': total_bodegas,
                'limite_aplicado': limite,
                'mostrando': len(resultados_lista),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except Exception as e:
            return {'error': f'Error consultando ventas por bodega: {str(e)}'}
    # ========== MÉTODOS DE CONSULTA ESPECÍFICAS DE VENTAS ==========
    
    def _consultar_venta_mas_grande(self, empresa_servidor_id=None, request=None):
        """Consulta la venta individual más grande - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                valor_total__isnull=False,
                tipo_documento='FACTURA_VENTA'
            )

            venta_mas_grande = query.order_by('-valor_total').first()

            if venta_mas_grande:
                # ✅ MENSAJE SEGÚN CONTEXTO
                mensaje = 'Venta individual con mayor valor encontrada'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'

                return {
                    'tipo_consulta': 'historico_venta_mas_grande',
                    'venta_mas_grande': {
                        'articulo': venta_mas_grande.articulo_nombre,
                        'codigo': venta_mas_grande.articulo_codigo,
                        'cantidad': float(venta_mas_grande.cantidad),
                        'valor_total': float(venta_mas_grande.valor_total),
                        'fecha': venta_mas_grande.fecha.strftime('%Y-%m-%d'),
                        'paciente': venta_mas_grande.paciente,
                        'clinica': venta_mas_grande.clinica,
                        'tipo_documento': venta_mas_grande.tipo_documento,
                        'medico': venta_mas_grande.medico
                    },
                    'empresas_consultadas': len(empresas_ids),
                    'consolidado': es_consolidado,
                    'mensaje': mensaje
                }
            else:
                return {'error': 'No se encontraron ventas con valores registrados'}

        except Exception as e:
            return {'error': f'Error consultando venta más grande: {str(e)}'}

    def _consultar_venta_menor(self, empresa_servidor_id=None, request=None):
        """Consulta la venta individual más pequeña - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                valor_total__isnull=False,
                valor_total__gt=0,
                tipo_documento='FACTURA_VENTA'
            )

            venta_menor = query.order_by('valor_total').first()

            if venta_menor:
                # ✅ MENSAJE SEGÚN CONTEXTO
                mensaje = 'Venta individual con menor valor encontrada'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'

                return {
                    'tipo_consulta': 'historico_venta_menor',
                    'venta_menor': {
                        'articulo': venta_menor.articulo_nombre,
                        'codigo': venta_menor.articulo_codigo,
                        'cantidad': float(venta_menor.cantidad),
                        'valor_total': float(venta_menor.valor_total),
                        'fecha': venta_menor.fecha.strftime('%Y-%m-%d'),
                        'paciente': venta_menor.paciente,
                        'clinica': venta_menor.clinica
                    },
                    'empresas_consultadas': len(empresas_ids),
                    'consolidado': es_consolidado,
                    'mensaje': mensaje
                }
            else:
                return {'error': 'No se encontraron ventas con valores registrados'}

        except Exception as e:
            return {'error': f'Error consultando venta menor: {str(e)}'}

    def _consultar_estadisticas_ventas_promedio(self, empresa_servidor_id=None, request=None):
        """Consulta estadísticas de ventas promedio - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                tipo_documento='FACTURA_VENTA',
                valor_total__isnull=False
            )

            # Obtener el valor promedio por transacción individual
            stats = query.aggregate(
                venta_promedio=Avg('valor_total'),  # ✅ Esto es correcto porque es por transacción individual
                venta_maxima=Max('valor_total'),
                venta_minima=Min('valor_total')
            )

            # Calcular estadísticas adicionales
            ventas_totales = query

            total_ventas = ventas_totales.count()
            valor_total_ventas = ventas_totales.aggregate(total=Sum('valor_total'))['total'] or 0

            # Calcular percentiles aproximados usando una consulta ordenada
            if total_ventas > 0:
                ventas_ordenadas = list(ventas_totales.order_by('valor_total').values_list('valor_total', flat=True))
                percentil_25 = ventas_ordenadas[int(total_ventas * 0.25)] if total_ventas >= 4 else 0
                percentil_75 = ventas_ordenadas[int(total_ventas * 0.75)] if total_ventas >= 4 else 0
            else:
                percentil_25 = percentil_75 = 0

            # ✅ MENSAJE SEGÚN CONTEXTO
            mensaje = 'Estadísticas de ventas promedio'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'estadisticas_ventas_promedio',
                'estadisticas': {
                    'venta_promedio_por_transaccion': float(stats['venta_promedio'] or 0),
                    'venta_maxima': float(stats['venta_maxima'] or 0),
                    'venta_minima': float(stats['venta_minima'] or 0),
                    'valor_total_ventas': float(valor_total_ventas),
                    'total_transacciones': total_ventas,
                    'valor_promedio_por_articulo': float(valor_total_ventas / total_ventas) if total_ventas > 0 else 0,
                    'percentil_25': float(percentil_25),
                    'percentil_75': float(percentil_75)
                },
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except Exception as e:
            return {'error': f'Error consultando estadísticas de ventas promedio: {str(e)}'}

    # ========== MÉTODOS DE CONSULTA DE COMPARACIÓN ==========
    def _comparar_periodos(self, consulta, empresa_servidor_id=None, request=None):
        """Compara ventas entre dos periodos - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Para comparaciones, si es consolidado, usar solo la primera empresa
            if es_consolidado and len(empresas_ids) > 1:
                logger.warning("⚠️ Comparación de periodos con múltiples empresas, usando solo la primera")
                empresas_ids = [empresas_ids[0]]
                es_consolidado = False

            # Comparar último mes vs mes anterior
            hoy = timezone.now()
            ultimo_mes = hoy.replace(day=1) - timedelta(days=1)
            mes_anterior = ultimo_mes.replace(day=1) - timedelta(days=1)

            # Consultas base - ADAPTADAS
            query_ultimo_mes = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                fecha__year=ultimo_mes.year,
                fecha__month=ultimo_mes.month,
                tipo_documento='FACTURA_VENTA'
            )

            query_mes_anterior = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                fecha__year=mes_anterior.year,
                fecha__month=mes_anterior.month,
                tipo_documento='FACTURA_VENTA'
            )

            ventas_ultimo_mes = query_ultimo_mes.aggregate(
                total_ventas=Count('id'),
                valor_total=Sum('valor_total')
            )

            ventas_mes_anterior = query_mes_anterior.aggregate(
                total_ventas=Count('id'),
                valor_total=Sum('valor_total')
            )

            valor_ultimo_mes = ventas_ultimo_mes['valor_total'] or 0
            valor_mes_anterior = ventas_mes_anterior['valor_total'] or 0

            if valor_mes_anterior > 0:
                variacion = ((valor_ultimo_mes - valor_mes_anterior) / valor_mes_anterior) * 100
            else:
                variacion = 100 if valor_ultimo_mes > 0 else 0

            # ✅ MENSAJE SEGÚN CONTEXTO
            mensaje = f'Comparación {ultimo_mes.strftime("%B %Y")} vs {mes_anterior.strftime("%B %Y")}'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'comparar_periodos',
                'periodo_actual': f"{ultimo_mes.strftime('%B %Y')}",
                'periodo_anterior': f"{mes_anterior.strftime('%B %Y')}",
                'ventas_actual': {
                    'total_ventas': ventas_ultimo_mes['total_ventas'] or 0,
                    'valor_total': float(valor_ultimo_mes)
                },
                'ventas_anterior': {
                    'total_ventas': ventas_mes_anterior['total_ventas'] or 0,
                    'valor_total': float(valor_mes_anterior)
                },
                'variacion': round(variacion, 2),
                'tendencia': 'positiva' if variacion > 0 else 'negativa',
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except Exception as e:
            return {'error': f'Error comparando periodos: {str(e)}'}

    def _analizar_crecimiento(self, consulta, empresa_servidor_id=None, request=None):
        """Analiza crecimiento de ventas - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Para análisis de crecimiento, si es consolidado, usar solo la primera empresa
            if es_consolidado and len(empresas_ids) > 1:
                logger.warning("⚠️ Análisis de crecimiento con múltiples empresas, usando solo la primera")
                empresas_ids = [empresas_ids[0]]
                es_consolidado = False

            # Analizar últimos 6 meses vs anteriores 6 meses
            hoy = timezone.now()
            seis_meses_atras = hoy - timedelta(days=180)
            doce_meses_atras = hoy - timedelta(days=360)

            # Consultas base - ADAPTADAS
            query_recientes = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                fecha__range=[seis_meses_atras, hoy],
                tipo_documento='FACTURA_VENTA'
            )

            query_anteriores = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                fecha__range=[doce_meses_atras, seis_meses_atras],
                tipo_documento='FACTURA_VENTA'
            )

            ventas_recientes = query_recientes.aggregate(
                valor_total=Sum('valor_total')
            )

            ventas_anteriores = query_anteriores.aggregate(
                valor_total=Sum('valor_total')
            )

            valor_reciente = ventas_recientes['valor_total'] or 0
            valor_anterior = ventas_anteriores['valor_total'] or 0

            if valor_anterior > 0:
                crecimiento = ((valor_reciente - valor_anterior) / valor_anterior) * 100
            else:
                crecimiento = 100 if valor_reciente > 0 else 0

            # Tendencias mensuales - ADAPTADA
            tendencias = query_recientes.annotate(
                mes=TruncMonth('fecha')
            ).values('mes').annotate(
                valor_mensual=Sum('valor_total')
            ).order_by('mes')

            # ✅ MENSAJE SEGÚN CONTEXTO
            mensaje = f'Análisis de crecimiento: {round(crecimiento, 2)}%'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'analisis_crecimiento',
                'periodo_analizado': 'últimos 6 meses vs anteriores 6 meses',
                'ventas_recientes': float(valor_reciente),
                'ventas_anteriores': float(valor_anterior),
                'crecimiento_porcentual': round(crecimiento, 2),
                'tendencia': 'crecimiento' if crecimiento > 0 else 'decrecimiento',
                'tendencias_mensuales': list(tendencias),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except Exception as e:
            return {'error': f'Error analizando crecimiento: {str(e)}'}
    # ========== MÉTODOS DE CONSULTA ESTADÍSTICAS GENERALES ==========
    # ========== MÉTODOS ESTADÍSTICOS GENERALES (ADAPTADOS) ==========

    def _consultar_estadisticas_generales(self, empresa_servidor_id=None, request=None):
        """Consulta estadísticas generales completas - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids
            )

            # Estadísticas básicas
            total_registros = query.count()
            articulos_unicos = query.values('articulo_codigo').distinct().count()

            # Estadísticas de ventas - ADAPTADA
            ventas = query.filter(tipo_documento='FACTURA_VENTA')
            compras = query.filter(tipo_documento='FACTURA_COMPRA')

            stats_ventas = ventas.aggregate(
                total_ventas=Count('id'),
                articulos_vendidos=Sum('cantidad'),
                valor_total_ventas=Sum('valor_total')
            )

            # ✅ CORRECCIÓN: Calcular promedio de venta manualmente
            total_ventas_count = stats_ventas['total_ventas'] or 0
            valor_total_ventas = stats_ventas['valor_total_ventas'] or 0

            if total_ventas_count > 0:
                venta_promedio = valor_total_ventas / total_ventas_count
            else:
                venta_promedio = 0

            stats_compras = compras.aggregate(
                total_compras=Count('id'),
                articulos_comprados=Sum('cantidad'),
                valor_total_compras=Sum('valor_total')
            )

            # Rango de fechas - ADAPTADO (considerando todas las empresas)
            rango_fechas = query.aggregate(
                fecha_minima=Min('fecha'),
                fecha_maxima=Max('fecha')
            )

            # Top categorías - ADAPTADO
            top_articulos = ventas.values('articulo_codigo', 'articulo_nombre').annotate(
                total_vendido=Sum('cantidad')
            ).order_by('-total_vendido')[:5]

            # ✅ MENSAJE SEGÚN CONTEXTO
            mensaje = 'Estadísticas históricas generales completas'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'historico_general',
                'estadisticas': {
                    'totales': {
                        'total_registros': total_registros,
                        'articulos_unicos': articulos_unicos,
                        'total_ventas': total_ventas_count,
                        'total_compras': stats_compras['total_compras'] or 0
                    },
                    'ventas': {
                        'articulos_vendidos': stats_ventas['articulos_vendidos'] or 0,
                        'valor_total_ventas': float(valor_total_ventas),
                        'venta_promedio': float(venta_promedio)
                    },
                    'compras': {
                        'articulos_comprados': stats_compras['articulos_comprados'] or 0,
                        'valor_total_compras': float(stats_compras['valor_total_compras'] or 0)
                    },
                    'rango_fechas': {
                        'desde': rango_fechas['fecha_minima'].strftime('%Y-%m-%d') if rango_fechas['fecha_minima'] else 'N/A',
                        'hasta': rango_fechas['fecha_maxima'].strftime('%Y-%m-%d') if rango_fechas['fecha_maxima'] else 'N/A'
                    }
                },
                'top_articulos': list(top_articulos),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except PermissionError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error consultando estadísticas generales: {str(e)}'}
    
    def _consultar_conteo_general(self, empresa_servidor_id=None, request=None):
        """Consulta conteos generales de diferentes entidades - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # Consulta base - ADAPTADA
            query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids
            )

            conteos = {
                'total_registros': query.count(),
                'articulos_unicos': query.values('articulo_codigo').distinct().count(),
                'pacientes_unicos': query.exclude(Q(paciente='') | Q(paciente__isnull=True)).values('paciente').distinct().count(),
                'medicos_unicos': query.exclude(Q(medico='') | Q(medico__isnull=True)).values('medico').distinct().count(),
                'clinicas_unicas': query.exclude(Q(clinica='') | Q(clinica__isnull=True)).values('clinica').distinct().count(),
                'pagadores_unicos': query.exclude(Q(pagador='') | Q(pagador__isnull=True)).values('pagador').distinct().count(),
                'ciudades_unicas': query.exclude(Q(ciudad='') | Q(ciudad__isnull=True)).values('ciudad').distinct().count(),
                'bodegas_unicas': query.exclude(Q(tipo_bodega='') | Q(tipo_bodega__isnull=True)).values('tipo_bodega').distinct().count()
            }

            # ✅ MENSAJE SEGÚN CONTEXTO
            mensaje = 'Conteos generales del sistema'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'conteo_general',
                'conteos': conteos,
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except Exception as e:
            return {'error': f'Error consultando conteos generales: {str(e)}'}

    def _consultar_estado_inventario(self, consulta, empresa_servidor_id=None, request=None):
        """Consulta estado actual del inventario - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # ✅ DETECTAR LÍMITE INTELIGENTE
            limite = self._extraer_limite_consulta(consulta)

            # Analizar movimientos recientes para inferir stock
            movimientos_recientes = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                fecha__gte=timezone.now() - timedelta(days=90)
            )

            # Consulta base - ADAPTADA
            articulos_activos_query = movimientos_recientes.values('articulo_codigo', 'articulo_nombre').annotate(
                total_ventas=Sum('cantidad', filter=Q(tipo_documento='FACTURA_VENTA')),
                total_compras=Sum('cantidad', filter=Q(tipo_documento='FACTURA_COMPRA')),
                ultimo_movimiento=Max('fecha')
            ).order_by('-ultimo_movimiento')

            # ✅ CALCULAR TOTAL REAL
            total_articulos = articulos_activos_query.count()

            # ✅ APLICAR LÍMITE SI ES NECESARIO
            if limite is not None:
                articulos_activos_query = articulos_activos_query[:limite]

            articulos_activos = []
            for articulo in articulos_activos_query:
                stock_estimado = (articulo['total_compras'] or 0) - (articulo['total_ventas'] or 0)
                articulos_activos.append({
                    'articulo_codigo': articulo['articulo_codigo'],
                    'articulo_nombre': articulo['articulo_nombre'],
                    'stock_estimado': max(stock_estimado, 0),
                    'necesita_reposicion': stock_estimado < 10,
                    'total_ventas': articulo['total_ventas'] or 0,
                    'total_compras': articulo['total_compras'] or 0,
                    'ultimo_movimiento': articulo['ultimo_movimiento'].strftime('%Y-%m-%d') if articulo['ultimo_movimiento'] else 'N/A'
                })

            # ✅ MENSAJE INTELIGENTE SEGÚN CONTEXTO
            mensaje = f'Estado de inventario para {len(articulos_activos)} artículos activos'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'
            if limite is None:
                mensaje = f'Estado de inventario para todos los artículos activos ({total_articulos} total)'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'estado_inventario',
                'articulos_activos': articulos_activos,
                'total_articulos_activos': total_articulos,
                'limite_aplicado': limite,
                'mostrando': len(articulos_activos),
                'necesitan_reposicion': sum(1 for a in articulos_activos if a['necesita_reposicion']),
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except Exception as e:
            return {'error': f'Error consultando estado de inventario: {str(e)}'}

    def _analizar_rotacion_inventario(self, consulta, empresa_servidor_id=None, request=None):
        """Analiza rotación de inventario - ADAPTADO PARA MÚLTIPLES EMPRESAS"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # ✅ OBTENER EMPRESAS SEGÚN CONTEXTO
            empresas_ids, es_consolidado = self._obtener_empresas_para_consulta(request, empresa_servidor_id)

            # ✅ DETECTAR LÍMITE INTELIGENTE
            limite = self._extraer_limite_consulta(consulta)

            # Analizar últimos 6 meses
            fecha_limite = timezone.now() - timedelta(days=180)

            # Consulta base - ADAPTADA
            rotacion_articulos_query = MovimientoInventario.objects.filter(
                empresa_servidor_id__in=empresas_ids,
                fecha__gte=fecha_limite,
                tipo_documento='FACTURA_VENTA'
            ).values('articulo_codigo', 'articulo_nombre').annotate(
                total_vendido=Sum('cantidad'),
                valor_total=Sum('valor_total'),
                transacciones=Count('id'),
                ultima_venta=Max('fecha')
            ).order_by('-total_vendido')

            # ✅ CALCULAR TOTAL REAL
            total_articulos = rotacion_articulos_query.count()

            # ✅ APLICAR LÍMITE SI ES NECESARIO
            if limite is not None:
                rotacion_articulos_query = rotacion_articulos_query[:limite]

            rotacion_articulos = []
            for articulo in rotacion_articulos_query:
                dias_desde_ultima_venta = (timezone.now() - articulo['ultima_venta']).days
                if dias_desde_ultima_venta < 30:
                    rotacion = 'ALTA'
                elif dias_desde_ultima_venta < 90:
                    rotacion = 'MEDIA'
                else:
                    rotacion = 'BAJA'

                rotacion_articulos.append({
                    'articulo_codigo': articulo['articulo_codigo'],
                    'articulo_nombre': articulo['articulo_nombre'],
                    'total_vendido': articulo['total_vendido'],
                    'valor_total': float(articulo['valor_total'] or 0),
                    'transacciones': articulo['transacciones'],
                    'rotacion': rotacion,
                    'dias_desde_ultima_venta': dias_desde_ultima_venta,
                    'ultima_venta': articulo['ultima_venta'].strftime('%Y-%m-%d') if articulo['ultima_venta'] else 'N/A'
                })

            # ✅ MENSAJE INTELIGENTE SEGÚN CONTEXTO
            mensaje = f'Análisis de rotación para {len(rotacion_articulos)} artículos'
            if es_consolidado:
                mensaje += f' (consolidado {len(empresas_ids)} empresas)'
            if limite is None:
                mensaje = f'Análisis de rotación para todos los artículos ({total_articulos} total)'
                if es_consolidado:
                    mensaje += f' (consolidado {len(empresas_ids)} empresas)'

            return {
                'tipo_consulta': 'analisis_rotacion',
                'periodo_analizado': 'últimos 6 meses',
                'articulos_analizados': total_articulos,
                'rotacion_articulos': rotacion_articulos,
                'limite_aplicado': limite,
                'mostrando': len(rotacion_articulos),
                'resumen_rotacion': {
                    'alta': sum(1 for a in rotacion_articulos if a['rotacion'] == 'ALTA'),
                    'media': sum(1 for a in rotacion_articulos if a['rotacion'] == 'MEDIA'),
                    'baja': sum(1 for a in rotacion_articulos if a['rotacion'] == 'BAJA')
                },
                'empresas_consultadas': len(empresas_ids),
                'consolidado': es_consolidado,
                'mensaje': mensaje
            }

        except Exception as e:
            return {'error': f'Error analizando rotación de inventario: {str(e)}'}
    # ========== MÉTODOS DE FALLBACK PREDICTIVO ==========
    
    def _generar_recomendaciones_historicas_mejoradas(self, consulta, empresa_servidor_id, meses=6):
        """Genera recomendaciones basadas en análisis histórico - CON LÍMITES INTELIGENTES"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario
            from django.db.models import Sum, Count, Avg, Max, Q

            logger.info(f"📊 Generando recomendaciones históricas para empresa {empresa_servidor_id}")

            # ✅ DETECTAR LÍMITE INTELIGENTE
            limite = self._extraer_limite_consulta(consulta)

            # Obtener datos históricos de los últimos 12 meses
            fecha_limite = timezone.now() - timedelta(days=365)

            # ✅ ANÁLISIS DE ARTÍCULOS MÁS VENDIDOS - SIN LÍMITE INICIAL
            articulos_ventas_query = MovimientoInventario.objects.filter(
                empresa_servidor_id=empresa_servidor_id,
                fecha__gte=fecha_limite,
                tipo_documento='FACTURA_VENTA'
            ).values('articulo_codigo', 'articulo_nombre').annotate(
                total_vendido=Sum('cantidad'),
                total_valor=Sum('valor_total'),
                transacciones=Count('id'),
                ultima_venta=Max('fecha'),
                precio_promedio=Avg('precio_unitario')
            ).order_by('-total_vendido')

            # ✅ APLICAR LÍMITE SI ES NECESARIO
            if limite is not None:
                articulos_ventas_query = articulos_ventas_query[:limite]

            articulos_ventas = list(articulos_ventas_query)

            if not articulos_ventas:
                return {'error': 'No hay datos históricos suficientes para generar recomendaciones'}

            # Calcular tendencias (ventas de los últimos 3 meses vs anteriores)
            fecha_reciente = timezone.now() - timedelta(days=90)

            recomendaciones = []
            for articulo in articulos_ventas:
                # Ventas recientes (últimos 3 meses)
                ventas_recientes = MovimientoInventario.objects.filter(
                    empresa_servidor_id=empresa_servidor_id,
                    articulo_codigo=articulo['articulo_codigo'],
                    tipo_documento='FACTURA_VENTA',
                    fecha__gte=fecha_reciente
                ).aggregate(total=Sum('cantidad'))['total'] or 0

                # Ventas anteriores (3-6 meses)
                fecha_anterior = timezone.now() - timedelta(days=180)
                ventas_anteriores = MovimientoInventario.objects.filter(
                    empresa_servidor_id=empresa_servidor_id,
                    articulo_codigo=articulo['articulo_codigo'],
                    tipo_documento='FACTURA_VENTA',
                    fecha__range=[fecha_anterior, fecha_reciente]
                ).aggregate(total=Sum('cantidad'))['total'] or 0

                # Calcular tendencia
                if ventas_anteriores > 0:
                    tendencia = (ventas_recientes - ventas_anteriores) / ventas_anteriores
                else:
                    tendencia = 1.0  # Si no hay ventas anteriores, considerar crecimiento

                # Calcular demanda mensual promedio
                demanda_mensual = articulo['total_vendido'] / 12
                demanda_proyectada = demanda_mensual * meses

                # Ajustar por tendencia
                if tendencia > 0.1:  # Crecimiento > 10%
                    factor_ajuste = 1.3
                    urgencia = "ALTA"
                elif tendencia < -0.1:  # Decrecimiento > 10%
                    factor_ajuste = 0.7
                    urgencia = "BAJA"
                else:
                    factor_ajuste = 1.0
                    urgencia = "MEDIA"

                cantidad_recomendada = max(int(demanda_proyectada * factor_ajuste * 1.2), 1)

                # Clasificación ABC basada en valor total
                valor_total = articulo['total_valor'] or 0
                if valor_total > 5000000:
                    clasificacion = "A"
                elif valor_total > 1000000:
                    clasificacion = "B"
                else:
                    clasificacion = "C"

                precio_promedio = float(articulo['precio_promedio'] or 0)
                inversion_estimada = cantidad_recomendada * precio_promedio

                # Determinar si es de alta rotación
                dias_desde_ultima_venta = (timezone.now() - articulo['ultima_venta']).days
                if dias_desde_ultima_venta < 30:
                    rotacion = "ALTA"
                elif dias_desde_ultima_venta < 90:
                    rotacion = "MEDIA"
                else:
                    rotacion = "BAJA"
                    urgencia = "BAJA"  # Si no se vende hace mucho, baja urgencia

                recomendaciones.append({
                    'articulo_codigo': articulo['articulo_codigo'],
                    'articulo_nombre': articulo['articulo_nombre'],
                    'clasificacion_abc': clasificacion,
                    'demanda_predicha': round(demanda_proyectada),
                    'cantidad_recomendada': cantidad_recomendada,
                    'ventas_historicas': articulo['total_vendido'],
                    'transacciones_historicas': articulo['transacciones'],
                    'urgencia': urgencia,
                    'rotacion': rotacion,
                    'tendencia': f"{tendencia:.2%}",
                    'precio_promedio': round(precio_promedio, 2),
                    'inversion_estimada': round(inversion_estimada, 2),
                    'ultima_venta': articulo['ultima_venta'].strftime('%Y-%m-%d'),
                    'dias_desde_ultima_venta': dias_desde_ultima_venta
                })

            # Ordenar por urgencia y demanda
            orden_urgencia = {"ALTA": 3, "MEDIA": 2, "BAJA": 1}
            recomendaciones.sort(key=lambda x: (orden_urgencia[x['urgencia']], x['demanda_predicha']), reverse=True)

            # ✅ NO APLICAR LÍMITE ADICIONAL - ya se aplicó al inicio
            inversion_total = sum(r['inversion_estimada'] for r in recomendaciones)

            # ✅ MENSAJE INTELIGENTE
            mensaje = f'Recomendaciones basadas en análisis histórico ({len(recomendaciones)} artículos)'
            if limite is not None:
                mensaje = f'Top {limite} recomendaciones basadas en análisis histórico'

            logger.info(f"✅ Recomendaciones generadas: {len(recomendaciones)} artículos")

            return {
                'tipo_consulta': 'recomendaciones_compras',
                'recomendaciones': recomendaciones,
                'total_articulos': len(recomendaciones),
                'inversion_estimada': round(inversion_total, 2),
                'nivel_servicio': 0.95,
                'meses_proyeccion': meses,
                'modelo_utilizado': 'analisis_historico_avanzado',
                'empresa_servidor_id': empresa_servidor_id,
                'limite_aplicado': limite,
                'mensaje': mensaje
            }

        except Exception as e:
            logger.error(f"❌ Error en recomendaciones históricas: {e}")
            return {'error': f'Error generando recomendaciones: {str(e)}'}  
        
    def _obtener_empresa_por_nit_y_anio(self, nit, anio_fiscal):
        """Obtiene una empresa por NIT y año fiscal"""
        try:
            from apps.sistema_analitico.models import EmpresaServidor
            return EmpresaServidor.objects.get(nit=nit, anio_fiscal=anio_fiscal)
        except EmpresaServidor.DoesNotExist:
            return None

    def _obtener_empresas_mismo_nit(self, empresa_servidor_id):
        """Obtiene todas las empresas con el mismo NIT (diferentes años)"""
        try:
            from apps.sistema_analitico.models import EmpresaServidor

            empresa_actual = EmpresaServidor.objects.get(id=empresa_servidor_id)
            empresas_relacionadas = EmpresaServidor.objects.filter(
                nit=empresa_actual.nit
            ).exclude(id=empresa_servidor_id).order_by('-anio_fiscal')

            return {
                'empresa_actual': empresa_actual,
                'empresas_relacionadas': list(empresas_relacionadas),
                'total_empresas': empresas_relacionadas.count() + 1
            }
        except Exception as e:
            logger.error(f"Error obteniendo empresas mismo NIT: {e}")
            return None

    def _obtener_empresa_anio_anterior(self, empresa_servidor_id):
        """Obtiene la empresa del año anterior automáticamente"""
        try:
            from apps.sistema_analitico.models import EmpresaServidor

            empresa_actual = EmpresaServidor.objects.get(id=empresa_servidor_id)
            anio_anterior = empresa_actual.anio_fiscal - 1

            return self._obtener_empresa_por_nit_y_anio(empresa_actual.nit, anio_anterior)
        except Exception as e:
            logger.error(f"Error obteniendo empresa año anterior: {e}")
            return None

    def _detectar_comparacion_anios(self, consulta):
        """Detecta si la consulta implica comparación entre años"""
        consulta_lower = consulta.lower()

        palabras_comparacion = [
            'vs', 'versus', 'comparar', 'comparación', 'comparativo',
            'vs.', 'frente a', 'respecto a', 'en comparación'
        ]

        patrones_anios = [
            r'202[0-9].*202[0-9]',  # 2024 vs 2025
            r'20\d{2}.*20\d{2}',     # cualquier año vs cualquier año
            r'año.*año',             # año vs año
            r'anterior',              # año anterior
            r'pasado',                # año pasado
            r'previo'                 # año previo
        ]

        # Verificar palabras de comparación
        if any(palabra in consulta_lower for palabra in palabras_comparacion):
            return True

        # Verificar patrones de años
        for patron in patrones_anios:
            if re.search(patron, consulta_lower):
                return True

        return False
    
    def _comparar_anios_especificos(self, consulta, empresa_servidor_id, anio_actual, anio_comparar):
        """Compara años fiscales específicos"""
        try:
            from apps.sistema_analitico.models import EmpresaServidor, MovimientoInventario

            # Obtener empresa actual
            empresa_actual = EmpresaServidor.objects.get(id=empresa_servidor_id)

            # Buscar empresas para los años especificados
            empresa_anio_actual = self._obtener_empresa_por_nit_y_anio(empresa_actual.nit, anio_actual)
            empresa_anio_comparar = self._obtener_empresa_por_nit_y_anio(empresa_actual.nit, anio_comparar)

            if not empresa_anio_actual or not empresa_anio_comparar:
                return {'error': f'No se encontraron datos para los años {anio_actual} y {anio_comparar}'}

            # Comparar trimestre si se especifica
            trimestre = self._extraer_trimestre(consulta)

            if trimestre:
                return self._comparar_trimestres_entre_anios(
                    empresa_anio_actual.id, empresa_anio_comparar.id, trimestre, anio_actual, anio_comparar
                )
            else:
                return self._comparar_anios_completos(
                    empresa_anio_actual.id, empresa_anio_comparar.id, anio_actual, anio_comparar
                )

        except Exception as e:
            return {'error': f'Error comparando años específicos: {str(e)}'}

    def _comparar_anio_anterior(self, consulta, empresa_servidor_id):
        """Compara automáticamente con el año anterior"""
        try:
            from apps.sistema_analitico.models import EmpresaServidor

            empresa_actual = EmpresaServidor.objects.get(id=empresa_servidor_id)
            empresa_anio_anterior = self._obtener_empresa_anio_anterior(empresa_servidor_id)

            if not empresa_anio_anterior:
                return {'error': 'No se encontraron datos del año anterior para comparar'}

            # Extraer trimestre si se menciona
            trimestre = self._extraer_trimestre(consulta)

            if trimestre:
                return self._comparar_trimestres_entre_anios(
                    empresa_servidor_id, empresa_anio_anterior.id, trimestre,
                    empresa_actual.anio_fiscal, empresa_anio_anterior.anio_fiscal
                )
            else:
                return self._comparar_anios_completos(
                    empresa_servidor_id, empresa_anio_anterior.id,
                    empresa_actual.anio_fiscal, empresa_anio_anterior.anio_fiscal
                )

        except Exception as e:
            return {'error': f'Error comparando con año anterior: {str(e)}'}

    def _extraer_trimestre(self, consulta):
        """Extrae el trimestre de la consulta"""
        consulta_lower = consulta.lower()

        if 'trimestre 1' in consulta_lower or 'trimestre1' in consulta_lower or 'q1' in consulta_lower:
            return 1
        elif 'trimestre 2' in consulta_lower or 'trimestre2' in consulta_lower or 'q2' in consulta_lower:
            return 2
        elif 'trimestre 3' in consulta_lower or 'trimestre3' in consulta_lower or 'q3' in consulta_lower:
            return 3
        elif 'trimestre 4' in consulta_lower or 'trimestre4' in consulta_lower or 'q4' in consulta_lower:
            return 4

        return None

    def _comparar_trimestres_entre_anios(self, empresa_id_actual, empresa_id_anterior, trimestre, anio_actual, anio_anterior):
        """Compara trimestres específicos entre años"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # Definir meses del trimestre
            meses_trimestre = {
                1: [1, 2, 3],   # Enero-Marzo
                2: [4, 5, 6],   # Abril-Junio
                3: [7, 8, 9],   # Julio-Septiembre
                4: [10, 11, 12] # Octubre-Diciembre
            }

            meses = meses_trimestre.get(trimestre, [1, 2, 3])

            # Ventas trimestre actual
            ventas_actual = MovimientoInventario.objects.filter(
                empresa_servidor_id=empresa_id_actual,
                fecha__year=anio_actual,
                fecha__month__in=meses,
                tipo_documento='FACTURA_VENTA'
            ).aggregate(
                total_ventas=Count('id'),
                articulos_vendidos=Sum('cantidad'),
                valor_total=Sum('valor_total')
            )

            # Ventas trimestre anterior
            ventas_anterior = MovimientoInventario.objects.filter(
                empresa_servidor_id=empresa_id_anterior,
                fecha__year=anio_anterior,
                fecha__month__in=meses,
                tipo_documento='FACTURA_VENTA'
            ).aggregate(
                total_ventas=Count('id'),
                articulos_vendidos=Sum('cantidad'),
                valor_total=Sum('valor_total')
            )

            valor_actual = ventas_actual['valor_total'] or 0
            valor_anterior = ventas_anterior['valor_total'] or 0

            # Calcular variaciones
            if valor_anterior > 0:
                variacion_valor = ((valor_actual - valor_anterior) / valor_anterior) * 100
            else:
                variacion_valor = 100 if valor_actual > 0 else 0

            articulos_actual = ventas_actual['articulos_vendidos'] or 0
            articulos_anterior = ventas_anterior['articulos_vendidos'] or 0

            if articulos_anterior > 0:
                variacion_articulos = ((articulos_actual - articulos_anterior) / articulos_anterior) * 100
            else:
                variacion_articulos = 100 if articulos_actual > 0 else 0

            return {
                'tipo_consulta': 'comparar_trimestres_anios',
                'trimestre': trimestre,
                'empresa_actual': {
                    'id': empresa_id_actual,
                    'anio_fiscal': anio_actual
                },
                'empresa_anterior': {
                    'id': empresa_id_anterior,
                    'anio_fiscal': anio_anterior
                },
                'ventas_actual': {
                    'total_ventas': ventas_actual['total_ventas'] or 0,
                    'articulos_vendidos': articulos_actual,
                    'valor_total': float(valor_actual)
                },
                'ventas_anterior': {
                    'total_ventas': ventas_anterior['total_ventas'] or 0,
                    'articulos_vendidos': articulos_anterior,
                    'valor_total': float(valor_anterior)
                },
                'variaciones': {
                    'valor': round(variacion_valor, 2),
                    'articulos': round(variacion_articulos, 2)
                },
                'tendencias': {
                    'valor': 'crecimiento' if variacion_valor > 0 else 'decrecimiento',
                    'articulos': 'crecimiento' if variacion_articulos > 0 else 'decrecimiento'
                },
                'mensaje': f'Comparación Trimestre {trimestre} {anio_actual} vs {anio_anterior}'
            }

        except Exception as e:
            return {'error': f'Error comparando trimestres: {str(e)}'}

    def _comparar_anios_completos(self, empresa_id_actual, empresa_id_anterior, anio_actual, anio_anterior):
        """Compara años fiscales completos"""
        try:
            from apps.sistema_analitico.models import MovimientoInventario

            # Ventas año actual
            ventas_actual = MovimientoInventario.objects.filter(
                empresa_servidor_id=empresa_id_actual,
                tipo_documento='FACTURA_VENTA'
            ).aggregate(
                total_ventas=Count('id'),
                articulos_vendidos=Sum('cantidad'),
                valor_total=Sum('valor_total')
            )

            # Ventas año anterior
            ventas_anterior = MovimientoInventario.objects.filter(
                empresa_servidor_id=empresa_id_anterior,
                tipo_documento='FACTURA_VENTA'
            ).aggregate(
                total_ventas=Count('id'),
                articulos_vendidos=Sum('cantidad'),
                valor_total=Sum('valor_total')
            )

            valor_actual = ventas_actual['valor_total'] or 0
            valor_anterior = ventas_anterior['valor_total'] or 0

            # Calcular variaciones
            if valor_anterior > 0:
                variacion_valor = ((valor_actual - valor_anterior) / valor_anterior) * 100
            else:
                variacion_valor = 100 if valor_actual > 0 else 0

            articulos_actual = ventas_actual['articulos_vendidos'] or 0
            articulos_anterior = ventas_anterior['articulos_vendidos'] or 0

            if articulos_anterior > 0:
                variacion_articulos = ((articulos_actual - articulos_anterior) / articulos_anterior) * 100
            else:
                variacion_articulos = 100 if articulos_actual > 0 else 0

            ventas_actual_count = ventas_actual['total_ventas'] or 0
            ventas_anterior_count = ventas_anterior['total_ventas'] or 0

            if ventas_anterior_count > 0:
                variacion_ventas = ((ventas_actual_count - ventas_anterior_count) / ventas_anterior_count) * 100
            else:
                variacion_ventas = 100 if ventas_actual_count > 0 else 0

            return {
                'tipo_consulta': 'comparar_anios_completos',
                'empresa_actual': {
                    'id': empresa_id_actual,
                    'anio_fiscal': anio_actual
                },
                'empresa_anterior': {
                    'id': empresa_id_anterior,
                    'anio_fiscal': anio_anterior
                },
                'ventas_actual': {
                    'total_ventas': ventas_actual_count,
                    'articulos_vendidos': articulos_actual,
                    'valor_total': float(valor_actual)
                },
                'ventas_anterior': {
                    'total_ventas': ventas_anterior_count,
                    'articulos_vendidos': articulos_anterior,
                    'valor_total': float(valor_anterior)
                },
                'variaciones': {
                    'valor': round(variacion_valor, 2),
                    'articulos': round(variacion_articulos, 2),
                    'transacciones': round(variacion_ventas, 2)
                },
                'tendencias': {
                    'valor': 'crecimiento' if variacion_valor > 0 else 'decrecimiento',
                    'articulos': 'crecimiento' if variacion_articulos > 0 else 'decrecimiento',
                    'transacciones': 'crecimiento' if variacion_ventas > 0 else 'decrecimiento'
                },
                'mensaje': f'Comparación año fiscal {anio_actual} vs {anio_anterior}'
            }

        except Exception as e:
            return {'error': f'Error comparando años completos: {str(e)}'}

    # ========== MÉTODOS ADICIONALES ==========
    
    @action(detail=False, methods=['post'])
    def consulta_tecnica(self, request):
        """Endpoint adicional para consultas técnicas detalladas"""
        try:
            consulta = request.data.get('consulta', '')
            empresa_servidor_id = request.data.get('empresa_servidor_id')
            
            resultados = self._procesar_consulta_tecnica(consulta, empresa_servidor_id)
            return Response(resultados)
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    def _procesar_consulta_tecnica(self, consulta, empresa_servidor_id):
        """Procesa consultas técnicas específicas"""
        return {
            'tipo': 'tecnica',
            'consulta': consulta,
            'resultados': 'Procesamiento técnico completado',
            'detalles': {
                'empresa_servidor_id': empresa_servidor_id,
                'timestamp': timezone.now().isoformat()
            }
        }

    @action(detail=False, methods=['get'])
    def estados_sistema(self, request):
        """Endpoint para verificar el estado del sistema"""
        try:
            from apps.sistema_analitico.models import EmpresaServidor, MovimientoInventario
            
            estados = {
                'ml_engine_activo': hasattr(self, 'ml_engine') and self.ml_engine is not None,
                'response_orchestrator_activo': hasattr(self, 'response_orchestrator') and self.response_orchestrator is not None,
                'empresas_activas': EmpresaServidor.objects.filter(estado='ACTIVO').count(),
                'total_movimientos': MovimientoInventario.objects.count(),
                'total_empresas': EmpresaServidor.objects.count(),
                'ultima_actualizacion': timezone.now().isoformat(),
                'modelos_entrenados': len(self.ml_engine.modelos_entrenados) if hasattr(self.ml_engine, 'modelos_entrenados') else 0
            }
            return Response(estados)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        
    def _extraer_limite_consulta(self, consulta):
        """Detecta si la consulta pide un límite específico (top X) o todos"""
        consulta_lower = consulta.lower()

        # Detectar "top X" o "primeros X"
        top_match = re.search(r'top\s+(\d+)|primeros?\s+(\d+)|primeras?\s+(\d+)', consulta_lower)
        if top_match:
            # Extraer el número del match
            for group in top_match.groups():
                if group:
                    return int(group)

        # Detectar "todos" o "todas"
        if any(palabra in consulta_lower for palabra in ['todos', 'todas', 'completo', 'completa', 'sin límite', 'todos los']):
            return None  # None significa sin límite

        # Por defecto, límite razonable para no sobrecargar
        return 50
    
    @action(detail=False, methods=['get'])
    def tipos_consulta_soportados(self, request):
        """Endpoint para listar todos los tipos de consulta soportados"""
        tipos_consulta = [
            # Predictivas
            'recomendaciones_compras',
            'prediccion_demanda',
            
            # Por Fechas/Periodos
            'ventas_por_mes',
            'compras_por_mes', 
            'ventas_por_anio',
            'ventas_por_rango_fechas',
            'ventas_recientes',
            
            # Por Artículos
            'historico_articulos_mas_vendidos',
            'historico_articulos_menos_vendidos',
            'historico_articulos_mas_caros',
            'buscar_articulo',
            'articulos_por_categoria',
            
            # Por Personas/Entidades
            'consulta_por_nit',
            'consulta_por_cedula',
            'consulta_por_medico',
            'consulta_por_paciente',
            'consulta_por_clinica',
            'consulta_por_pagador',
            
            # Por Ubicaciones
            'ventas_por_ciudad',
            'ventas_por_bodega',
            
            # Específicas de Ventas
            'historico_venta_mas_grande',
            'historico_venta_menor',
            'estadisticas_ventas_promedio',
            
            # Comparación
            'comparar_periodos',
            'analisis_crecimiento',
            
            # Estadísticas
            'historico_general',
            'conteo_general',
            
            # Inventario
            'estado_inventario',
            'analisis_rotacion'
        ]
        
        return Response({
            'total_tipos_consulta': len(tipos_consulta),
            'tipos_consulta_soportados': tipos_consulta,
            'mensaje': 'Tipos de consulta soportados por el sistema'
        }) 

# ========== AUTH VIEWS ==========
class CustomTokenObtainPairView(TokenObtainPairView):
    """Login personalizado que incluye user info"""
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            from django.contrib.auth.models import User
            user = User.objects.get(username=request.data['username'])
            response.data['user'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_superuser': user.is_superuser,
                'puede_gestionar_api_keys': user.puede_gestionar_api_keys()
            }
        return response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout - blacklist refresh token"""
    try:
        refresh_token = request.data.get('refresh_token')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message": "Logout exitoso"}, status=200)
    except Exception as e:
        return Response({"error": "Token inválido"}, status=400)

# ========== API KEY MANAGEMENT VIEWS ==========
class APIKeyManagementViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return APIKeyCliente.objects.all()
        return APIKeyCliente.objects.filter(usuario_creador=self.request.user)
    
    @action(detail=False, methods=['post'])
    def generar_api_key(self, request):
        """Genera API Key para un NIT específico"""
        from .serializers import GenerarAPIKeySerializer
        serializer = GenerarAPIKeySerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
            
        data = serializer.validated_data
        nit = data['nit']
        nombre_cliente = data['nombre_cliente']
        dias_validez = data['dias_validez']
        
        # Verificar que el usuario tiene permisos para gestionar API Keys
        if not request.user.puede_gestionar_api_keys():
            return Response(
                {"error": "No tienes permisos para generar API Keys"}, 
                status=403
            )
        
        # Verificar que existe al menos una empresa con este NIT
        empresas_nit = EmpresaServidor.objects.filter(nit=nit)
        if not empresas_nit.exists():
            return Response(
                {"error": "No existen empresas con este NIT"}, 
                status=404
            )
        
        # Verificar permisos del usuario sobre al menos una empresa del NIT
        tiene_permiso = any(
            request.user.has_empresa_permission(empresa, 'ver') 
            for empresa in empresas_nit
        )
        
        if not tiene_permiso and not request.user.is_superuser:
            return Response(
                {"error": "No tienes permisos para generar API Key para este NIT"}, 
                status=403
            )
        
        # Crear o actualizar API Key
        api_key = f"sk_{secrets.token_urlsafe(32)}"
        fecha_caducidad = timezone.now() + timedelta(days=dias_validez)
        
        api_key_obj, created = APIKeyCliente.objects.update_or_create(
            nit=nit,
            defaults={
                'nombre_cliente': nombre_cliente,
                'api_key': api_key,
                'fecha_caducidad': fecha_caducidad,
                'activa': True,
                'usuario_creador': request.user
            }
        )
        
        # Actualizar empresas asociadas automáticamente
        cantidad_empresas = api_key_obj.actualizar_empresas_asociadas()
        
        return Response({
            "nit": nit,
            "nombre_cliente": nombre_cliente,
            "api_key": api_key,  # ⚠️ Mostrar solo esta vez
            "fecha_creacion": api_key_obj.fecha_creacion,
            "fecha_caducidad": api_key_obj.fecha_caducidad,
            "empresas_asociadas": cantidad_empresas,
            "accion": "Creada" if created else "Actualizada",
            "mensaje": "API Key generada exitosamente - GUARDA ESTA KEY"
        })
    
    @action(detail=False, methods=['get'])
    def listar_api_keys(self, request):
        """Lista todas las API Keys del usuario"""
        from .serializers import APIKeyClienteSerializer
        
        api_keys = self.get_queryset()
        serializer = APIKeyClienteSerializer(api_keys, many=True)
        
        return Response({
            "total_api_keys": api_keys.count(),
            "api_keys": serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def revocar_api_key(self, request):
        """Revoca una API Key"""
        api_key_id = request.data.get('api_key_id')
        
        try:
            api_key = self.get_queryset().get(id=api_key_id)
            api_key.activa = False
            api_key.save()
            
            return Response({"mensaje": "API Key revocada exitosamente"})
            
        except APIKeyCliente.DoesNotExist:
            return Response({"error": "API Key no encontrada"}, status=404)
    
    @action(detail=False, methods=['post'])
    def renovar_api_key(self, request):
        """Renueva una API Key"""
        api_key_id = request.data.get('api_key_id')
        dias = request.data.get('dias', 365)
        
        try:
            api_key = self.get_queryset().get(id=api_key_id)
            api_key.renovar(dias)
            
            return Response({
                "mensaje": f"API Key renovada por {dias} días",
                "nueva_fecha_caducidad": api_key.fecha_caducidad
            })
            
        except APIKeyCliente.DoesNotExist:
            return Response({"error": "API Key no encontrada"}, status=404)
    
    @action(detail=False, methods=['get'])
    def estadisticas_api_keys(self, request):
        """Estadísticas de uso de API Keys"""
        api_keys = self.get_queryset()
        
        stats = {
            "total_api_keys": api_keys.count(),
            "api_keys_activas": api_keys.filter(activa=True).count(),
            "api_keys_expiradas": sum(1 for key in api_keys if key.esta_expirada()),
            "total_peticiones": sum(key.contador_peticiones for key in api_keys),
            "api_key_mas_usada": api_keys.order_by('-contador_peticiones').first().nombre_cliente if api_keys.exists() else None,
        }
        
        return Response(stats)
        
    

class TestingViewSet(viewsets.ViewSet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tester = SystemTester()
    
    @action(detail=False, methods=['post'])
    def ejecutar_pruebas_completas(self, request):
        try:
            resultados = self.tester.ejecutar_pruebas_integracion()
            return Response(resultados)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        
        