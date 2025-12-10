"""
Servicio para clasificación contable de facturas usando Deepseek.
Basado en el sistema de BCE pero adaptado para MANU con mejoras.
"""
import json
import time
import logging
import requests
import re
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.utils import timezone
from ..models import RUT, ClasificacionContable, Proveedor, AIAnalyticsAPIKey, normalize_nit_and_extract_dv

logger = logging.getLogger(__name__)

# ==================== MAPEO DE CÓDIGOS DE PAGO ====================
# Mapeo estándar de códigos de pago UBL a nombres normalizados
# TODO: Completar con la lista completa de códigos que proporcione el usuario
MAPEO_CODIGOS_PAGO = {
    '10': 'efectivo',
    '20': 'transferencia',
    '30': 'cheque',
    '40': 'tarjeta',
    '41': 'tarjeta_debito',
    '42': 'tarjeta_credito',
    # Agregar más códigos según la lista del usuario
}

def obtener_forma_pago_completa(
    codigo: Optional[str],
    descripcion_xml: Optional[str] = None,
    nombre_firebird: Optional[str] = None
) -> Dict[str, str]:
    """
    Obtiene forma de pago completa con prioridad:
    1. Descripción XML (si es válida y no es solo el código)
    2. Nombre Firebird (si existe)
    3. Mapeo estándar (código → nombre)
    4. "efectivo" por defecto
    
    Retorna: {
        'codigo': '10',
        'nombre': 'efectivo',
        'descripcion': 'Pago en efectivo' (si está disponible)
    }
    """
    codigo_str = str(codigo).strip() if codigo else ''
    
    # Prioridad 1: Descripción del XML (si es válida y no es solo el código)
    nombre_final = None
    if descripcion_xml and len(descripcion_xml.strip()) > 0:
        desc_clean = descripcion_xml.strip()
        # Si la descripción no es solo el código, usarla
        if desc_clean.lower() != codigo_str.lower():
            nombre_final = desc_clean
    
    # Prioridad 2: Nombre de Firebird
    if not nombre_final and nombre_firebird:
        nombre_final = nombre_firebird.strip()
    
    # Prioridad 3: Mapeo estándar
    if not nombre_final and codigo_str in MAPEO_CODIGOS_PAGO:
        nombre_final = MAPEO_CODIGOS_PAGO[codigo_str]
    
    # Prioridad 4: Por defecto
    if not nombre_final:
        nombre_final = 'efectivo'
    
    return {
        'codigo': codigo_str or '',
        'nombre': nombre_final,
        'descripcion': descripcion_xml.strip() if descripcion_xml else ''
    }

# ==================== PROMPTS (Adaptado completo de BCE) ====================cls

PROMPTS = {
    "clasificacion_masiva": {
        "system": """Eres contador público colombiano experto en NIIF, PUC y normatividad tributaria. Analiza los artículos y devuelve EXCLUSIVAMENTE JSON con:

## INSTRUCCIONES ESTRICTAS:
1. **AGRUPAR POR FACTURA** → Usa el campo 'ref' para agrupar artículos por factura
2. **GENERAR 1 ASIENTO POR FACTURA** → Cada factura debe tener su propio asiento contable
3. **RETENCIÓN POR PROVEEDOR** → Usa 'aplica_retencion' y 'porcentaje_retencion' a nivel de proveedor
4. **PRIMERO** analiza el GIRO REAL de la empresa: {mi_ciuu} ({mi_ciuu_desc})
5. **LUEGO** analiza el GIRO del proveedor: {ciuu_proveedor} ({ciuu_proveedor_desc})  
6. **USA LOS IMPUESTOS PROPORCIONADOS** en cada artículo (NO los recalcules)
7. **CLASIFICA** cada artículo con LÓGICA CONTABLE REAL
8. **INCLUYE AUXILIARES CONTABLES** por cada cuenta usada en artículos y asientos. Si no existe, sugiere uno genérico basado en el nombre del artículo.
9. **EVALÚA CONFIANZA** por artículo según coincidencia con giros de empresa/proveedor
10. **MODALIDAD POR FACTURA** → Usar 'modalidad_pago' en cada factura ('credito'/'contado')
11. **CUENTAS SEGÚN MODALIDAD**:
    - CRÉDITO: 110505 (Proveedores varios) → Naturaleza: Crédito (C)
    - CONTADO: 110101 (Caja) o 111005 (Bancos) → Naturaleza: Crédito (C)
12. **FORMA DE PAGO** → Si es contado, usar 'forma_pago_codigo', 'forma_pago_nombre' y 'forma_pago_descripcion' para determinar la cuenta exacta:
    - efectivo (código 10): 110101 (Caja general) → nomauxiliar: "Caja general"
    - transferencia (código 20): 111005 (Bancos) → nomauxiliar: "[Nombre del banco] cuenta corriente" (si se conoce en descripción) o "Cuenta bancaria" (genérico si no se especifica)
    - tarjeta (código 40): 110510 (Anticipos) o 111005 (Bancos) → nomauxiliar: "Tarjeta crédito [Nombre del banco]" (si se conoce) o "Medios electrónicos" (genérico)
    - cheque (código 30): 110515 (Cheques por cobrar) → nomauxiliar: "Cheques por cobrar"
    - Por defecto: 110101 (Caja general) → nomauxiliar: "Caja general"

    **IMPORTANTE**: 
    - Si 'forma_pago_descripcion' contiene nombre de banco, úsalo en el nomauxiliar
    - Si no se proporciona el nombre específico del banco o tarjeta, usar un nomauxiliar genérico como "Cuenta bancaria" o "Medios electrónicos"
    - NUNCA inventar nombres de bancos si no están en los datos proporcionados

## REGLAS DE ORO CONTABLES:
1. **INVENTARIO** → SÓLO si el artículo está en el GIRO NORMAL de la empresa para REVENTA
2. **GASTO/COSTO** → Si es para CONSUMO INTERNO, operación o administración
3. **ACTIVO** → Si es durable y se usa en la operación (maquinaria, equipos, software)
4. Si el artículo NO COINCIDE con el giro de la empresa → Probablemente es GASTO
5. **RETENCIONES** → Reducen el valor a pagar al proveedor (Neto = Total + IVA - Retención)
6. **MODALIDAD Y FORMA DE PAGO** determinan la cuenta de contrapartida:
   - Crédito: 110505 (Proveedores varios)
   - Contado efectivo: 110101 (Caja general)
   - Contado transferencia: 111005 (Bancos)
   - Contado tarjeta: 110510 (Anticipos) o 111005 (Bancos)
   - Contado cheque: 110515 (Cheques por cobrar)

## REGLA DE CONFIANZA (OBLIGATORIA):
Evalúa el campo 'confianza' según coincidencia entre el artículo y los giros de empresa/proveedor:
- **ALTA**: Coincidencia clara con giro principal/secundario de la empresa Y el artículo es típico del giro del proveedor.
- **MEDIA**: Justificable pero requiere validación (ej: artículo atípico pero plausible para el proveedor o la empresa).
- **BAJA**: Ambigüedad o artículo claramente atípico para el giro del proveedor o de la empresa. Ejemplo: un proveedor de computadores que vende alimentos.
- **PENDIENTE**: No se puede determinar sin información adicional.

**Validación adicional**: Si el artículo no es típico del giro del proveedor (ej: proveedor de computadores vendiendo alimentos), la confianza debe ser "BAJA" y se debe agregar una observación indicando la inconsistencia.

## GRUPOS CONTABLES (INFERIR DEL ARTÍCULO):
Grupo contable debe ser inferido del nombre, uso o naturaleza del artículo. Ejemplos:
- SOFTWARE, HERRAMIENTAS, SERVICIOS, PUBLICIDAD, MATERIALES, EQUIPOS, MANTENIMIENTO
- Puede ser compartido por varios ítems de la misma factura

## DESTINOS POSIBLES (ESPECTRO COMPLETO):
### DESTINOS PRINCIPALES (95% de casos):
- INVENTARIO (activos para revender o transformar)
- GASTO (consumo inmediato, operación, administración)
- COSTO (producción, servicios, operación directa)
- ACTIVO FIJO (inmuebles, maquinaria, equipos duraderos)
- ACTIVO INTANGIBLE (software, licencias, patentes)
- DIFERIDO (gastos pagados por anticipado)
- OTROS ACTIVOS (inversiones, propiedades de inversión)

## EJEMPLOS ESPECÍFICOS POR GIRO:
### RESTAURANTES (CIUU 5611, 5619, 5620):
- **Alimentos/Insumos que se TRANSFORMAN** (materias primas para preparar platos) → INVENTARIO (1410) NO COSTO (6135/6175)
  - **Razón**: En restaurantes, estos son INSUMOS/MATERIAS PRIMAS que se almacenan y luego se usan para elaborar platos. NO son gastos directos, son INVENTARIO hasta que se usen en la preparación.
  - **Ejemplos**: Salsa rosada, chicharrón, carnes, verduras, condimentos, insumos de cocina para preparar hamburguesas, sachipapas, etc.
  - **Cuenta**: 1410 (Inventario de materias primas) - Son insumos almacenados para elaboración de platos bajo demanda
  - **NOTA**: Solo cuando se VENDEN los platos preparados, se traslada de inventario (1410) a costo de ventas (6135/6175)
  
- **Bebidas y productos que se REVENDEN DIRECTAMENTE** (sin transformar) → INVENTARIO (1435) NO COSTO (6135)
  - **Razón**: Estos productos se venden directamente al cliente sin transformación
  - **Ejemplos**: Gaseosas, cervezas, aguas, jugos envasados, snacks, paquetes, cigarrillos
  - **Cuenta**: 1435 (Inventario productos terminados para reventa)
  
- **Equipos de cocina** → ACTIVO FIJO (1520) si son duraderos

### SUPERMERCADOS/TIENDAS (CIUU 4711, 4719):
- **Alimentos comprados** → INVENTARIO (1435) para REVENTA
- **Razón**: Los supermercados revenden productos directamente sin transformarlos
- **Ejemplo**: Supermercado compra "Salsa rosada" → 1435 (Inventario alimentos envasados)

### FERRETERÍAS (CIUU 4651):
- **Herramientas compradas** → INVENTARIO (1435) para REVENTA
- **Ejemplo**: Ferretería compra "Martillo" → 1435 (Inventario herramientas)

### DESTINOS ESPECIALIZADOS (5% restante):
- PASIVO DIFERIDO (anticipos recibidos, ingresos no causados)
- INGRESO NO OPERACIONAL (venta de activos, ingresos financieros)
- GASTO NO DEDUCIBLE (partidas sin beneficio fiscal)
- PROVISIONES (para riesgos y contingencias)
- AJUSTES POR INFLACIÓN (cuando aplicable)

## CUENTAS SEGÚN TIPO DE IMPUESTO:
- **iva 19%** → 240801 (débito)
- **iva 5%** → 240801 (débito) 
- **iva 0%** → No registra IVA
- **impoconsumo** → 240802 (débito)
- **retencion_fuente** → 240805 (crédito)
- **ica** → 240806 (débito/crédito según caso)

## VALIDACIONES CRÍTICAS:
1. **AGRUPAR POR FACTURA** → Artículos con misma 'ref' van en el mismo asiento
2. **SUMA DEBE = SUMA HABER** en cada asiento por factura
3. **RETENCIÓN APLICABLE** → Si 'aplica_retencion'=true, aplicar retención a servicios/honorarios
4. **RETENCIONES REDUCEN EL VALOR A PAGAR** → Neto = Total + IVA - Retención
5. **USA LOS VALORES** de impuestos proporcionados (NO recalcules)
6. **CONSIDERA INCLUYE/EXCLUYE** de los CIUU para clasificación
7. **PRIORIZA GIRO EMPRESA** sobre giro proveedor
8. **MARCA COMO PENDIENTE** si hay ambigüedad
9. **AUXILIARES CONSISTENTES** → La misma cuenta debe usar EL MISMO auxiliar en todo el asiento
10. **TOTALIZAR POR CUENTA-AUXILIAR** → En asientos contables, SUMAR todos los valores por cuenta y auxiliar
11. **NO REPETIR CUENTAS** → Cada combinación cuenta-auxiliar debe aparecer UNA vez con el total
12. **NOMAUXILIAR ESPECÍFICO** → El campo 'nomauxiliar' debe ser específico, no genérico:
    - Ejemplo BUENO: 'Herramientas de ferretería', 'Bancolombia Cta. Corriente'
    - Ejemplo MALO: 'Herramientas', 'Bancos'
13. **NO INVENTAR BANCOS** → Si no se proporciona el nombre del banco en los datos de entrada, usar un nomauxiliar genérico como "Cuenta bancaria" para transferencias o "Medios electrónicos" para tarjetas. Nunca usar nombres de bancos específicos si no se mencionan en los datos.
14. **COHERENCIA PROVEEDOR-ARTÍCULO** → Verificar que los artículos sean coherentes con el giro del proveedor. Si no lo son, marcar con confianza "BAJA" y agregar observación.

## FORMATO DE RESPUESTA:
Devuelve SOLO JSON válido. Estructura:
{{
  "proveedores": {{
    "900111222": {{
      "aplica_retencion": true,
      "porcentaje_retencion": 11,
      "clasificaciones": {{
        "F001-12345": [
          {{
            "nombre": "Artículo",
            "ref": "F001-12345",
            "cantidad": 5,
            "valor_unitario": 25000,
            "valor_total": 125000,
            "modalidad_pago": "credito",
            "grupo_contable": "HERRAMIENTAS",
            "destino": "INVENTARIO",
            "cuentas": {{
              "1435": {{ "valor": 125000, "naturaleza": "D", "auxiliar": "01", "nomauxiliar": "Herramientas de ferretería" }},
              "240801": {{ "valor": 23750, "naturaleza": "D", "auxiliar": "02", "nomauxiliar": "IVA compras herramientas" }},
              "110505": {{ "valor": 148750, "naturaleza": "C", "auxiliar": "01", "nomauxiliar": "Proveedores nacionales" }}
            }},
            "impuestos_aplicados": [],
            "confianza": "ALTA"
          }},
          {{
            "nombre": "Salsa rosada 2000g",
            "ref": "F002-67890",
            "cantidad": 1,
            "valor_unitario": 46273.11,
            "valor_total": 46273.11,
            "modalidad_pago": "credito",
            "grupo_contable": "ALIMENTOS",
            "destino": "COSTO",
            "cuentas": {{
              "6135": {{ "valor": 46273.11, "naturaleza": "D", "auxiliar": "01", "nomauxiliar": "Compras de alimentos para preparación" }},
              "240801": {{ "valor": 8791.89, "naturaleza": "D", "auxiliar": "02", "nomauxiliar": "IVA compras alimentos" }},
              "240802": {{ "valor": 7485, "naturaleza": "D", "auxiliar": "03", "nomauxiliar": "Impoconsumo alimentos" }},
              "110505": {{ "valor": 62550, "naturaleza": "C", "auxiliar": "01", "nomauxiliar": "Proveedores nacionales" }}
            }},
            "impuestos_aplicados": [
              {{ "tipo": "iva", "tasa": 19, "valor": 8791.89 }},
              {{ "tipo": "impoconsumo", "tasa": 0, "valor": 7485 }}
            ],
            "observaciones": "Restaurante (CIUU 5611) compra alimentos para transformar en comidas preparadas. Clasificado como COSTO (6135), no INVENTARIO (1435).",
            "confianza": "ALTA"
          }}
        ]
      }}
    }}
  }},
            "impuestos_aplicados": [],
            "confianza": "ALTA"
          }}
        ]
      }},
      "asientos_contables": [
        {{
          "factura": "F001-12345",
          "proveedor": "900111222",
          "fecha": "2024-03-15",
          "descripcion": "Compra de herramientas para inventario - Factura F001-12345",
          "debitos": [
            {{
              "cuenta": "1435",
              "descripcion": "Inventario herramientas",
              "valor": 125000,
              "auxiliar": "01",
              "nomauxiliar": "Herramientas de ferretería"
            }},
            {{
              "cuenta": "240801",
              "descripcion": "IVA compras",
              "valor": 23750,
              "auxiliar": "02",
              "nomauxiliar": "IVA compras herramientas"
            }}
          ],
          "creditos": [
            {{
              "cuenta": "110505",
              "descripcion": "Compras nacionales",
              "valor": 148750,
              "auxiliar": "01",
              "nomauxiliar": "Proveedores nacionales"
            }}
          ],
          "total_debitos": 148750,
          "total_creditos": 148750,
          "balanceado": true,
          "observaciones": "Asiento balanceado. IVA 19% aplicado según datos proporcionados."
        }}
      ]
    }}
  }},
  "recomendaciones": []
}}

¡CUBRE TODO EL ESPECTRO CONTABLE colombiano!""",
        
        "user": """## CONTEXTO EMPRESA COMPRADORA:
- Razón Social: {empresa_id}
- GIRO PRINCIPAL: {mi_ciuu} - {mi_ciuu_desc}
- GIROS SECUNDARIOS: {mi_ciuu_sec}

## CONTEXTO PROVEEDOR:
- NIT: {proveedor_id}
- GIRO: {ciuu_proveedor} - {ciuu_proveedor_desc}
- Tipo Operación: {tipo_operacion}
- Aplica Retención: {aplica_retencion}
- % Retención: {porcentaje_retencion}
- Modalidad Pago: {modalidad_pago}
- Forma Pago Código: {forma_pago_codigo}
- Forma Pago Nombre: {forma_pago_nombre}
- Forma Pago Descripción: {forma_pago_descripcion}

## FACTURAS Y ARTÍCULOS:
{facturas}

## REQUERIMIENTO:
1. **ANALIZA** el giro de la empresa vs giro del proveedor
2. **CLASIFICA** usando los IMPUESTOS YA CALCULADOS proporcionados
3. **APLICA RETENCIONES** como CRÉDITO contable (cuenta 240805)
4. **CALCULA NETO A PAGAR** = Total artículo + IVA - Retención
5. **RESPETA MODALIDAD Y FORMA DE PAGO** → Crédito (110505) vs Contado (110101/111005/110510/110515)
6. **USA LA DESCRIPCIÓN DE FORMA DE PAGO** para determinar nombre de banco si está disponible
7. **GENERA** asiento contable completo
8. **DEVUELVE** SOLO JSON válido sin explicaciones adicionales"""
    }
}


def obtener_contexto_ciuu_inteligente(ciuu_code: str) -> Dict[str, Any]:
    """
    Obtener información completa del CIUU con fallback inteligente.
    Basado en BCE pero adaptado para MANU.
    
    Flujo:
    1. Buscar en BD (ActividadEconomica)
    2. Si no está, consultar API externa de CIUU
    3. Guardar en BD y cache para uso futuro
    4. Si falla todo, usar fallback genérico
    """
    if not ciuu_code or ciuu_code == 'None':
        logger.warning(f"CIUU code es None o vacío")
        return {
            "codigo": ciuu_code or "N/A",
            "descripcion": "Actividad económica no especificada",
            "incluye": "",
            "excluye": "",
            "contexto_completo": "Actividad económica no especificada",
            "fuente": "desconocido"
        }
    
    try:
        from ..models import ActividadEconomica
        actividad = ActividadEconomica.objects.get(codigo=ciuu_code)
        
        # Obtener incluye/excluye del JSONField
        incluye_list = actividad.incluye if actividad.incluye else []
        excluye_list = actividad.excluye if actividad.excluye else []
        
        # Formatear incluye/excluye (pueden ser listas de diccionarios o strings)
        def formatear_actividades(lista):
            if not lista:
                return ""
            textos = []
            for item in lista:
                if isinstance(item, dict):
                    # Si es diccionario, extraer la descripción
                    desc = item.get('actDescripcion', item.get('descripcion', str(item)))
                    textos.append(desc)
                else:
                    textos.append(str(item))
            return "\n• ".join(textos) if textos else ""
        
        incluye_texto = formatear_actividades(incluye_list)
        excluye_texto = formatear_actividades(excluye_list)
        
        descripcion = actividad.descripcion or actividad.titulo or f"CIUU {ciuu_code}"
        
        return {
            "codigo": ciuu_code,
            "descripcion": descripcion,
            "incluye": incluye_texto,
            "excluye": excluye_texto,
            "incluye_raw": incluye_list,  # Guardar raw para análisis
            "excluye_raw": excluye_list,  # Guardar raw para análisis
            "contexto_completo": f"{descripcion}. INCLUYE: {incluye_texto}. EXCLUYE: {excluye_texto}",
            "fuente": "base_datos"
        }
    except ActividadEconomica.DoesNotExist:
        logger.warning(f"No se encontró CIUU {ciuu_code} en BD, consultando API externa...")
        
        # Intentar obtener desde API externa
        try:
            from .ciiu_service import obtener_o_crear_actividad_economica
            
            # Consultar API y guardar en BD
            actividad = obtener_o_crear_actividad_economica(
                codigo_ciiu=ciuu_code,
                forzar_actualizacion=False
            )
            
            if actividad:
                # Obtener incluye/excluye del JSONField
                incluye_list = actividad.incluye if actividad.incluye else []
                excluye_list = actividad.excluye if actividad.excluye else []
                
                # Formatear incluye/excluye (pueden ser listas de diccionarios o strings)
                def formatear_actividades(lista):
                    if not lista:
                        return ""
                    textos = []
                    for item in lista:
                        if isinstance(item, dict):
                            # Si es diccionario, extraer la descripción
                            desc = item.get('actDescripcion', item.get('descripcion', str(item)))
                            textos.append(desc)
                        else:
                            textos.append(str(item))
                    return "\n• ".join(textos) if textos else ""
                
                incluye_texto = formatear_actividades(incluye_list)
                excluye_texto = formatear_actividades(excluye_list)
                
                descripcion = actividad.descripcion or actividad.titulo or f"CIUU {ciuu_code}"
                
                logger.info(f"✅ CIUU {ciuu_code} obtenido desde API y guardado en BD")
                return {
                    "codigo": ciuu_code,
                    "descripcion": descripcion,
                    "incluye": incluye_texto,
                    "excluye": excluye_texto,
                    "contexto_completo": f"{descripcion}. INCLUYE: {incluye_texto}. EXCLUYE: {excluye_texto}",
                    "fuente": "api_externa"
                }
        except Exception as api_error:
            logger.warning(f"Error consultando API de CIUU para {ciuu_code}: {api_error}")
        
        # Fallback genérico si todo falla
        logger.warning(f"Usando fallback genérico para CIUU {ciuu_code}")
        return {
            "codigo": ciuu_code,
            "descripcion": f"Actividad económica CIUU {ciuu_code}",
            "incluye": "actividades comerciales y servicios generales",
            "excluye": "funciones no especificadas",
            "contexto_completo": f"CIUU {ciuu_code} - Actividad económica",
            "fuente": "inferencia"
        }
    except Exception as e:
        logger.warning(f"Error obteniendo CIUU {ciuu_code}: {e}")
        # Fallback genérico
        return {
            "codigo": ciuu_code,
            "descripcion": f"Actividad económica CIUU {ciuu_code}",
            "incluye": "actividades comerciales y servicios generales",
            "excluye": "funciones no especificadas",
            "contexto_completo": f"CIUU {ciuu_code} - Actividad económica",
            "fuente": "inferencia"
        }


def calcular_costo_tokens(
    input_tokens: int, 
    output_tokens: int,
    cache_hit_tokens: int = None,
    cache_miss_tokens: int = None
) -> Dict[str, Any]:
    """
    Calcular costo real en USD y COP basado en tokens.
    Usa precios reales del servicio de IA/Analytics con diferenciación de cache hit/miss.
    
    Args:
        input_tokens: Total de tokens de entrada (prompt_tokens)
        output_tokens: Total de tokens de salida (completion_tokens)
        cache_hit_tokens: Tokens que usaron cache (prompt_cache_hit_tokens). Si es None, se estima.
        cache_miss_tokens: Tokens que NO usaron cache (prompt_cache_miss_tokens). Si es None, se estima.
    
    Returns:
        Dict con costos, tokens y detalles
    """
    from django.conf import settings
    
    # Precios desde settings (cargados desde ENV)
    # Usar nuevos nombres, con fallback a nombres antiguos para compatibilidad
    precio_output = getattr(settings, 'AIANALYTICS_PRICE_OUTPUT_TOKEN', None) or getattr(settings, 'DEEPSEEK_PRICE_OUTPUT_TOKEN', 0.00000042)
    precio_cache_hit = getattr(settings, 'AIANALYTICS_PRICE_INPUT_CACHE_HIT', None) or getattr(settings, 'DEEPSEEK_PRICE_INPUT_CACHE_HIT', 0.000000028)
    precio_cache_miss = getattr(settings, 'AIANALYTICS_PRICE_INPUT_CACHE_MISS', None) or getattr(settings, 'DEEPSEEK_PRICE_INPUT_CACHE_MISS', 0.00000056)
    tasa_cambio = getattr(settings, 'TASA_CAMBIO_COP_USD', 4000)
    
    # Si no se proporcionan valores de cache, usar estimación conservadora (70% hit, 30% miss)
    if cache_hit_tokens is None or cache_miss_tokens is None:
        if cache_hit_tokens is None:
            cache_hit_tokens = int(input_tokens * 0.7)  # Estimación: 70% cache hit
        if cache_miss_tokens is None:
            cache_miss_tokens = input_tokens - cache_hit_tokens
    
    # Calcular costo real con cache diferenciado
    costo_input = (cache_hit_tokens * precio_cache_hit) + (cache_miss_tokens * precio_cache_miss)
    costo_output = output_tokens * precio_output
    costo_usd = costo_input + costo_output
    costo_cop = costo_usd * tasa_cambio
    
    return {
        "costo_usd": round(costo_usd, 6),
        "costo_cop": round(costo_cop, 2),
        "tokens_input": input_tokens,
        "tokens_output": output_tokens,
        "tokens_cache_hit": cache_hit_tokens,
        "tokens_cache_miss": cache_miss_tokens,
        "costo_input_usd": round(costo_input, 6),
        "costo_output_usd": round(costo_output, 6),
        "detalle": {
            "precio_cache_hit": precio_cache_hit,
            "precio_cache_miss": precio_cache_miss,
            "precio_output": precio_output
        }
    }


class ClasificadorContableService:
    """
    Servicio para clasificación contable de facturas usando Deepseek.
    Basado en BCE pero mejorado para MANU.
    """
    
    def __init__(self):
        # API URL y configuración (usar nuevos nombres con fallback a antiguos)
        self.api_url = getattr(settings, 'AIANALYTICS_API_URL', None) or getattr(settings, 'DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
        self.max_facturas = getattr(settings, 'CLASIFICACION_MAX_FACTURAS', 0)
        self.max_articulos = getattr(settings, 'CLASIFICACION_MAX_ARTICULOS', 0)
        self.max_articulos_por_factura = getattr(settings, 'CLASIFICACION_MAX_ARTICULOS_POR_FACTURA', 0)
        self.timeout = getattr(settings, 'CLASIFICACION_TIMEOUT_SEGUNDOS', 90)
        self.max_tokens = getattr(settings, 'CLASIFICACION_MAX_TOKENS', 8000)
        self.temperature = getattr(settings, 'CLASIFICACION_TEMPERATURE', 0.1)
        self.debug = getattr(settings, 'CLASIFICACION_DEBUG', False)
        
        # API Key: Intentar usar modelo primero, fallback a settings
        self.api_key_obj = None
        self.api_key = None
        self._obtener_api_key()
        
        self.cache_ciuu = {}  # Cache para CIUU
    
    def _obtener_api_key(self):
        """
        Obtener API key usando rotación automática desde el modelo.
        Si no hay API keys en el modelo, usar la de settings como fallback.
        """
        api_key_obj = AIAnalyticsAPIKey.obtener_siguiente_api_key()
        if api_key_obj:
            self.api_key_obj = api_key_obj
            self.api_key = api_key_obj.api_key
            logger.info(f"🔑 [API_KEY] Usando API key: {api_key_obj.nombre} (Total peticiones: {api_key_obj.total_peticiones})")
        else:
            # Fallback a settings si no hay API keys en BD (usar nuevos nombres con fallback a antiguos)
            self.api_key = getattr(settings, 'AIANALYTICS_API_KEY', None) or getattr(settings, 'DEEPSEEK_API_KEY', '')
            if self.api_key:
                logger.warning(f"⚠️ [API_KEY] No hay API keys en BD, usando API key de settings")
            else:
                logger.error(f"❌ [API_KEY] No se encontró API key ni en BD ni en settings")
        
        # Headers se generan dinámicamente en cada petición para usar la API key actual
    
    def _print_debug(self, *args, **kwargs):
        """Print de debug si está habilitado"""
        if self.debug:
            print(f"[CLASIFICACION DEBUG] {' '.join(str(a) for a in args)}")
            if kwargs:
                print(f"[CLASIFICACION DEBUG] {kwargs}")
        logger.debug(f"{' '.join(str(a) for a in args)}")
    
    def obtener_info_ciuu_cached(self, ciuu_code: str) -> Dict[str, Any]:
        """Obtener información de CIUU con cache"""
        if ciuu_code in self.cache_ciuu:
            return self.cache_ciuu[ciuu_code]
        
        info = obtener_contexto_ciuu_inteligente(ciuu_code)
        self.cache_ciuu[ciuu_code] = info
        return info
    
    def buscar_rut_por_nit(self, nit: str) -> Optional[Dict[str, Any]]:
        """
        Buscar CIUU por NIT con fallback inteligente:
        1. Buscar en RUT (si existe) - primero con NIT tal cual, luego normalizado
        2. Buscar en Proveedor (cache de Cámara de Comercio)
        3. Consultar Cámara de Comercio si no está en cache
        4. Guardar en Proveedor para uso futuro
        
        Retorna None si no se encuentra en ninguna fuente.
        """
        try:
            # ✅ CORRECCIÓN: Buscar primero con el NIT tal cual (sin normalizar) para evitar recortar NITs completos
            # Ejemplo: Si viene "1005038638" (10 dígitos), NO debe recortarse a "100503863" (9 dígitos)
            nit_original = str(nit).strip()
            nit_limpio = re.sub(r'\D', '', nit_original)  # Solo dígitos, sin guiones ni puntos
            
            # 1. Intentar buscar en RUT primero con el NIT limpio (sin normalizar)
            rut = None
            nit_normalizado = None
            
            if nit_limpio:
                # Buscar primero con el NIT limpio tal cual (sin normalizar)
                rut = RUT.objects.filter(nit_normalizado=nit_limpio).first()
                
                # Si no encuentra y el NIT tiene guión o formato especial, normalizar
                if not rut and ('-' in nit_original or '.' in nit_original or ' ' in nit_original):
                    nit_normalizado, _, _ = normalize_nit_and_extract_dv(nit)
                    if nit_normalizado and nit_normalizado != nit_limpio:
                        rut = RUT.objects.filter(nit_normalizado=nit_normalizado).first()
                    else:
                        nit_normalizado = nit_limpio
                else:
                    # Si el NIT ya está limpio y no tiene formato especial, usar directamente
                    nit_normalizado = nit_limpio
            else:
                nit_normalizado, _, _ = normalize_nit_and_extract_dv(nit)
                rut = RUT.objects.filter(nit_normalizado=nit_normalizado).first()
            
            if rut:
                self._print_debug(f"✅ RUT encontrado para NIT: {nit} - {rut.razon_social}")
                
                # Extraer CIUU del RUT
                ciuu_principal = rut.actividad_principal_ciiu if hasattr(rut, 'actividad_principal_ciiu') else None
                ciuu_secundarios = []
                
                if hasattr(rut, 'actividad_secundaria_ciiu') and rut.actividad_secundaria_ciiu:
                    ciuu_secundarios.append(rut.actividad_secundaria_ciiu)
                
                if hasattr(rut, 'otras_actividades_ciiu') and rut.otras_actividades_ciiu:
                    otras = rut.otras_actividades_ciiu
                    if isinstance(otras, list):
                        ciuu_secundarios.extend(otras)
                    elif isinstance(otras, str):
                        try:
                            otras_list = json.loads(otras) if otras.startswith('[') else [otras]
                            ciuu_secundarios.extend(otras_list)
                        except:
                            ciuu_secundarios.append(otras)
                
                return {
                    "nit": rut.nit,
                    "nit_normalizado": rut.nit_normalizado,
                    "razon_social": rut.razon_social,
                    "ciuu_principal": ciuu_principal,
                    "ciuu_secundarios": list(set(ciuu_secundarios)),
                    "fuente": "rut"
                }
            
            # 2. Buscar en Proveedor (cache de Cámara de Comercio)
            proveedor = Proveedor.objects.filter(nit_normalizado=nit_normalizado).first()
            
            if proveedor:
                self._print_debug(f"✅ Proveedor encontrado en cache para NIT: {nit} - {proveedor.razon_social}")
                return {
                    "nit": proveedor.nit,
                    "nit_normalizado": proveedor.nit_normalizado,
                    "razon_social": proveedor.razon_social,
                    "ciuu_principal": proveedor.actividad_principal_ciiu,
                    "ciuu_secundarios": proveedor.get_ciuu_secundarios(),
                    "fuente": proveedor.fuente
                }
            
            # 3. Consultar Cámara de Comercio (usar NIT original, no normalizado recortado)
            self._print_debug(f"⚠️ RUT no encontrado para NIT: {nit}, consultando Cámara de Comercio...")
            
            from .camara_comercio_service import consultar_camara_comercio_por_nit
            # ✅ CORRECCIÓN: Usar NIT original completo para la consulta, no el normalizado (que puede estar recortado)
            nit_para_consulta = nit_original if 'nit_original' in locals() else nit
            datos_ccb = consultar_camara_comercio_por_nit(nit_para_consulta)
            
            if datos_ccb and datos_ccb.get('ciuu_principal'):
                self._print_debug(f"✅ Info obtenida de Cámara de Comercio para NIT: {nit}")
                
                # Guardar en modelo Proveedor para uso futuro
                proveedor, created = Proveedor.objects.update_or_create(
                    nit_normalizado=nit_normalizado,
                    defaults={
                        'nit': datos_ccb.get('nit', nit),
                        'razon_social': datos_ccb.get('razon_social', ''),
                        'actividad_principal_ciiu': datos_ccb.get('ciuu_principal'),
                        'actividad_secundaria_ciiu': datos_ccb.get('ciuu_secundarios', [])[0] if datos_ccb.get('ciuu_secundarios') else None,
                        'otras_actividades_ciiu': datos_ccb.get('ciuu_secundarios', [])[1:] if len(datos_ccb.get('ciuu_secundarios', [])) > 1 else [],
                        'fuente': 'camara_comercio',
                        'datos_completos': datos_ccb.get('datos_completos', {})
                    }
                )
                
                if created:
                    self._print_debug(f"💾 Proveedor guardado en BD: {proveedor.razon_social}")
                else:
                    self._print_debug(f"🔄 Proveedor actualizado en BD: {proveedor.razon_social}")
                
                return {
                    "nit": datos_ccb.get('nit', nit),
                    "nit_normalizado": nit_normalizado,
                    "razon_social": datos_ccb.get('razon_social', ''),
                    "ciuu_principal": datos_ccb.get('ciuu_principal'),
                    "ciuu_secundarios": datos_ccb.get('ciuu_secundarios', []),
                    "fuente": "camara_comercio"
                }
            
            # No se encontró en ninguna fuente
            self._print_debug(f"❌ No se encontró información CIUU para NIT: {nit} en ninguna fuente")
            return None
            
        except Exception as e:
            self._print_debug(f"❌ Error buscando RUT para NIT {nit}: {e}")
            logger.error(f"Error buscando RUT para NIT {nit}: {e}", exc_info=True)
            return None
    
    def validar_limites(self, facturas: List[Dict]) -> tuple:
        """
        Validar límites configurables.
        Retorna (es_valido, mensaje_error)
        """
        total_facturas = len(facturas)
        total_articulos = sum(len(f.get('articulos', [])) for f in facturas)
        
        # Validar límite de facturas
        if self.max_facturas > 0 and total_facturas > self.max_facturas:
            return False, f"Límite de facturas excedido: {total_facturas} > {self.max_facturas}"
        
        # Validar límite total de artículos
        if self.max_articulos > 0 and total_articulos > self.max_articulos:
            return False, f"Límite de artículos excedido: {total_articulos} > {self.max_articulos}"
        
        # Validar límite de artículos por factura
        if self.max_articulos_por_factura > 0:
            for factura in facturas:
                articulos_count = len(factura.get('articulos', []))
                if articulos_count > self.max_articulos_por_factura:
                    return False, f"Factura {factura.get('numero_factura', 'SIN_NUMERO')} excede límite: {articulos_count} > {self.max_articulos_por_factura}"
        
        return True, None
    
    def clasificar_factura(
        self,
        factura: Dict[str, Any],
        empresa_nit: str,
        empresa_ciuu_principal: str,
        empresa_ciuu_secundarios: List[str],
        proveedor_nit: str,
        proveedor_ciuu: Optional[str] = None,
        aplica_retencion: bool = False,
        porcentaje_retencion: float = 0,
        tipo_operacion: str = "compra"
    ) -> Dict[str, Any]:
        """
        Clasificar una factura individual usando Deepseek.
        Retorna resultado con clasificación, costos y tiempos.
        """
        inicio_tiempo = time.time()
        
        try:
            # Buscar CIUU del proveedor si no se proporcionó
            if not proveedor_ciuu:
                rut_proveedor = self.buscar_rut_por_nit(proveedor_nit)
                if rut_proveedor:
                    proveedor_ciuu = rut_proveedor.get('ciuu_principal')
            
            # Obtener información de CIUUs
            mi_ciuu_info = self.obtener_info_ciuu_cached(empresa_ciuu_principal)
            mi_ciuu_sec_info = [self.obtener_info_ciuu_cached(ciuu) for ciuu in empresa_ciuu_secundarios]
            
            empresa_desc = f"{mi_ciuu_info['descripcion']} [Fuente: {mi_ciuu_info['fuente']}]"
            if mi_ciuu_info.get('incluye'):
                empresa_desc += f". INCLUYE: {mi_ciuu_info['incluye']}"
            if mi_ciuu_info.get('excluye'):
                empresa_desc += f". EXCLUYE: {mi_ciuu_info['excluye']}"
            
            mi_ciuu_sec_desc = "\n".join([
                f"- {info['descripcion']} [Fuente: {info['fuente']}]. INCLUYE: {info.get('incluye', '')}. EXCLUYE: {info.get('excluye', '')}"
                for info in mi_ciuu_sec_info
            ])
            
            prov_ciuu_info = self.obtener_info_ciuu_cached(proveedor_ciuu) if proveedor_ciuu else {
                "descripcion": "No especificado",
                "incluye": "",
                "excluye": "",
                "fuente": "desconocido"
            }
            prov_desc = f"{prov_ciuu_info['descripcion']} [Fuente: {prov_ciuu_info['fuente']}]"
            if prov_ciuu_info.get('incluye'):
                prov_desc += f". INCLUYE: {prov_ciuu_info['incluye']}"
            if prov_ciuu_info.get('excluye'):
                prov_desc += f". EXCLUYE: {prov_ciuu_info['excluye']}"
            
            # Construir prompt
            user_content = PROMPTS["clasificacion_masiva"]["user"].format(
                empresa_id=empresa_nit,
                mi_ciuu=empresa_ciuu_principal,
                mi_ciuu_desc=empresa_desc,
                mi_ciuu_sec=mi_ciuu_sec_desc,
                proveedor_id=proveedor_nit,
                ciuu_proveedor=proveedor_ciuu or "N/A",
                ciuu_proveedor_desc=prov_desc,
                tipo_operacion=tipo_operacion,
                aplica_retencion=aplica_retencion,
                porcentaje_retencion=porcentaje_retencion,
                modalidad_pago=factura.get('modalidad_pago', 'credito'),
                forma_pago_codigo=factura.get('forma_pago_codigo') or 'N/A',
                forma_pago_nombre=factura.get('forma_pago', 'efectivo'),
                forma_pago_descripcion=factura.get('forma_pago_descripcion') or 'N/A',
                facturas=json.dumps([factura], ensure_ascii=False)
            )
            
            # JSON de factura enviada (sin prompt)
            articulos_factura = factura.get('articulos', [])
            factura_json_enviada = {
                "numero_factura": factura.get('numero_factura'),
                "fecha": factura.get('fecha'),
                "cufe": factura.get('cufe'),
                "modalidad_pago": factura.get('modalidad_pago'),
                "forma_pago": factura.get('forma_pago'),
                "forma_pago_codigo": factura.get('forma_pago_codigo'),
                "forma_pago_descripcion": factura.get('forma_pago_descripcion'),
                "fecha_vencimiento": factura.get('fecha_vencimiento'),
                "proveedor_nit": factura.get('proveedor_nit'),
                "articulos": articulos_factura
            }
            
            self._print_debug(f"📤 Enviando factura {factura.get('numero_factura')} al servicio de IA")
            self._print_debug(f"📊 Total artículos: {len(articulos_factura)}")
            for idx, art in enumerate(articulos_factura, 1):
                self._print_debug(f"  Artículo {idx}: {art.get('nombre', 'N/A')} - Cant: {art.get('cantidad', 0)} - Total: ${art.get('valor_total', 0)} - Impuestos: {len(art.get('impuestos', []))}")
            
            # Llamar al servicio de IA
            provider_messages = [
                {"role": "system", "content": PROMPTS["clasificacion_masiva"]["system"]},
                {"role": "user", "content": user_content}
            ]
            
            data = {
                "model": "deepseek-chat",
                "messages": provider_messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "response_format": {"type": "json_object"}
            }
            
            # Intentar llamada al servicio de IA con retry y backoff exponencial
            # Usar rotación de API keys: obtener una nueva en cada petición
            max_retries = 3
            retry_delay = 1  # Segundos iniciales
            last_error = None
            api_key_usada = None
            es_rate_limit = False
            
            for intento in range(max_retries):
                # Obtener siguiente API key (rotación automática)
                api_key_obj = AIAnalyticsAPIKey.obtener_siguiente_api_key()
                if api_key_obj:
                    api_key_usada = api_key_obj
                    current_api_key = api_key_obj.api_key
                    logger.info(f"🔑 [API_KEY] Intento {intento + 1}: Usando API key '{api_key_obj.nombre}'")
                else:
                    # Fallback a settings (usar nuevos nombres con fallback a antiguos)
                    current_api_key = getattr(settings, 'AIANALYTICS_API_KEY', None) or getattr(settings, 'DEEPSEEK_API_KEY', '')
                    if not current_api_key:
                        raise ValueError("No hay API keys disponibles ni en BD ni en settings")
                
                # Headers dinámicos con la API key actual
                headers = {
                    "Authorization": f"Bearer {current_api_key}",
                    "Content-Type": "application/json"
                }
                
                try:
                    response = requests.post(
                        self.api_url,
                        headers=headers,
                        json=data,
                        timeout=self.timeout
                    )
                    response.raise_for_status()
                    
                    # Éxito: trackear petición exitosa
                    if api_key_usada:
                        api_key_usada.incrementar_peticion(exitosa=True, es_rate_limit=False)
                    
                    last_error = None
                    break  # Éxito, salir del loop
                except requests.exceptions.HTTPError as e:
                    es_rate_limit = (e.response and e.response.status_code == 429)
                    
                    # Trackear petición fallida
                    if api_key_usada:
                        api_key_usada.incrementar_peticion(exitosa=False, es_rate_limit=es_rate_limit)
                    
                    if es_rate_limit:
                        if intento < max_retries - 1:
                            wait_time = retry_delay * (2 ** intento)  # Backoff exponencial
                            logger.warning(f"⏳ [AI_ANALYTICS] Rate limit alcanzado con API key '{api_key_usada.nombre if api_key_usada else 'settings'}'. Esperando {wait_time}s antes de reintentar (intento {intento + 1}/{max_retries})...")
                            time.sleep(wait_time)
                            last_error = e
                            continue
                    # Si no es rate limit o ya agotamos los reintentos, lanzar error
                    last_error = e
                    raise
                except requests.exceptions.RequestException as e:
                    # Trackear petición fallida
                    if api_key_usada:
                        api_key_usada.incrementar_peticion(exitosa=False, es_rate_limit=False)
                    
                    if intento < max_retries - 1:
                        wait_time = retry_delay * (2 ** intento)
                        logger.warning(f"⏳ [AI_ANALYTICS] Error de conexión. Esperando {wait_time}s antes de reintentar (intento {intento + 1}/{max_retries})...")
                        time.sleep(wait_time)
                        last_error = e
                        continue
                    last_error = e
                    raise
            
            if last_error:
                raise last_error
            
            # Optimización de memoria: usar response.content en lugar de response.json()
            # Esto es funcionalmente idéntico pero más eficiente en memoria para respuestas grandes
            # El resultado es exactamente el mismo, solo cambia cómo se carga en memoria
            respuesta_api = json.loads(response.content.decode('utf-8'))
            contenido = respuesta_api['choices'][0]['message']['content']
            
            # Calcular tokens y costos usando valores reales de cache
            usage = respuesta_api.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            
            # Extraer valores reales de cache si están disponibles
            cache_hit_tokens = usage.get('prompt_cache_hit_tokens', None)
            cache_miss_tokens = usage.get('prompt_cache_miss_tokens', None)
            
            # Si no están disponibles, intentar desde prompt_tokens_details
            if cache_hit_tokens is None and 'prompt_tokens_details' in usage:
                cached_tokens = usage['prompt_tokens_details'].get('cached_tokens', 0)
                if cached_tokens > 0:
                    cache_hit_tokens = cached_tokens
                    cache_miss_tokens = input_tokens - cached_tokens
            
            costo_info = calcular_costo_tokens(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_hit_tokens=cache_hit_tokens,
                cache_miss_tokens=cache_miss_tokens
            )
            
            # Trackear costo en la API key usada
            if api_key_usada:
                api_key_usada.agregar_costo(
                    costo_usd=costo_info['costo_usd'],
                    tokens_input=input_tokens,
                    tokens_output=output_tokens,
                    tokens_cache_hit=cache_hit_tokens or 0,
                    tokens_cache_miss=cache_miss_tokens or 0
                )
                logger.info(f"💰 [API_KEY] Costo agregado a '{api_key_usada.nombre}': ${costo_info['costo_usd']:.6f} USD (Total acumulado: ${api_key_usada.costo_total_usd:.6f} USD)")
            
            tiempo_procesamiento = time.time() - inicio_tiempo
            
            self._print_debug(f"✅ Factura procesada en {tiempo_procesamiento:.2f}s")
            
            # Mostrar información de costos (siempre visible, no solo en debug)
            print("=" * 60)
            print("💰 DETALLE COMPLETO DE COSTOS:")
            print("=" * 60)
            print(f"📊 TOKENS UTILIZADOS:")
            print(f"   - Input tokens (total):     {costo_info['tokens_input']}")
            print(f"   - Output tokens:            {costo_info['tokens_output']}")
            print(f"   - Cache HIT tokens:         {costo_info['tokens_cache_hit']}")
            print(f"   - Cache MISS tokens:        {costo_info['tokens_cache_miss']}")
            print("")
            print(f"💵 DESGLOSE DE COSTOS:")
            detalle = costo_info.get('detalle', {})
            if costo_info['tokens_cache_hit'] > 0 or costo_info['tokens_cache_miss'] > 0:
                print(f"   - Input Cache HIT:         {costo_info['tokens_cache_hit']} × ${detalle.get('precio_cache_hit', 0):.10f} = ${(costo_info['tokens_cache_hit'] * detalle.get('precio_cache_hit', 0)):.10f} USD")
                print(f"   - Input Cache MISS:        {costo_info['tokens_cache_miss']} × ${detalle.get('precio_cache_miss', 0):.10f} = ${(costo_info['tokens_cache_miss'] * detalle.get('precio_cache_miss', 0)):.10f} USD")
                print(f"   - Costo Input Total:       ${costo_info['costo_input_usd']:.10f} USD")
            else:
                print(f"   - Costo Input (estimado):  ${costo_info['costo_input_usd']:.10f} USD")
            print(f"   - Costo Output:            {costo_info['tokens_output']} × ${detalle.get('precio_output', 0):.10f} = ${costo_info['costo_output_usd']:.10f} USD")
            print("")
            print(f"💰 COSTO TOTAL:")
            print(f"   - USD: ${costo_info['costo_usd']:.10f}")
            from django.conf import settings as django_settings
            print(f"   - COP: ${costo_info['costo_cop']:,.2f} (tasa: {getattr(django_settings, 'TASA_CAMBIO_COP_USD', 4000)} COP/USD)")
            print("=" * 60)
            
            # Parsear JSON de respuesta
            try:
                respuesta_json = json.loads(contenido)
                
                # Extraer solo la parte de la factura (sin metadata)
                respuesta_factura = respuesta_json.get('proveedores', {}).get(proveedor_nit, {})
                
                # ✅ CORRECCIÓN: Incluir asientos_contables del nivel superior si existen
                # Los asientos_contables están en el nivel raíz del JSON, no dentro de proveedores
                if 'asientos_contables' in respuesta_json:
                    respuesta_factura['asientos_contables'] = respuesta_json['asientos_contables']
                
                # También incluir recomendaciones si existen
                if 'recomendaciones' in respuesta_json:
                    respuesta_factura['recomendaciones'] = respuesta_json['recomendaciones']
                
                return {
                    "success": True,
                    "factura_numero": factura.get('numero_factura'),
                    "clasificacion": respuesta_json,
                    "respuesta_factura": respuesta_factura,
                    "factura_json_enviada": factura_json_enviada,
                    "respuesta_json_completa": respuesta_api,
                    "costo": costo_info,
                    "tiempo_procesamiento": tiempo_procesamiento,
                    "tokens": {
                        "input": input_tokens,
                        "output": output_tokens
                    }
                }
            except json.JSONDecodeError as e:
                self._print_debug(f"❌ Error parseando JSON: {e}")
                return {
                    "success": False,
                    "error": f"Error parseando JSON: {str(e)}",
                    "respuesta_cruda": contenido,
                    "tiempo_procesamiento": tiempo_procesamiento
                }
                
        except requests.exceptions.RequestException as e:
            tiempo_procesamiento = time.time() - inicio_tiempo
            self._print_debug(f"❌ Error de conexión: {e}")
            return {
                "success": False,
                "error": f"Error de conexión: {str(e)}",
                "tiempo_procesamiento": tiempo_procesamiento
            }
        except Exception as e:
            tiempo_procesamiento = time.time() - inicio_tiempo
            self._print_debug(f"❌ Error inesperado: {e}")
            logger.error(f"Error clasificando factura: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Error inesperado: {str(e)}",
                "tiempo_procesamiento": tiempo_procesamiento
            }
    
    def _consultar_payment_method(self, empresa_nit: str, codigo_pago: str) -> Optional[Dict[str, str]]:
        """
        Consulta la tabla payment_methods en MariaDB (APIDIAN) para obtener el nombre del método de pago.
        Retorna {'code': codigo, 'name': nombre} o None si no se encuentra.
        """
        if not codigo_pago or not codigo_pago.strip():
            return None
        
        try:
            import pymysql
            from django.conf import settings
            
            # Obtener credenciales de MariaDB desde settings (misma BD de APIDIAN)
            host = getattr(settings, 'APIDIAN_DB_HOST', '45.149.204.184')
            port = getattr(settings, 'APIDIAN_DB_PORT', 3307)
            user = getattr(settings, 'APIDIAN_DB_USER', 'apidian')
            password = getattr(settings, 'APIDIAN_DB_PASSWORD', '')
            database = getattr(settings, 'APIDIAN_DB_NAME', 'apidian')
            
            # Conectar a MariaDB
            connection = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10
            )
            
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT code, name
                        FROM payment_methods
                        WHERE code = %s
                        LIMIT 1
                    """, (codigo_pago.strip(),))
                    
                    row = cursor.fetchone()
                    
                    if row:
                        code = row.get('code', codigo_pago)
                        name = row.get('name', '')
                        
                        self._print_debug(f"✅ Método de pago encontrado en MariaDB: {code} = {name}")
                        return {'code': code, 'name': name}
                    else:
                        self._print_debug(f"⚠️ Método de pago '{codigo_pago}' no encontrado en payment_methods (MariaDB)")
                        return None
                        
            finally:
                connection.close()
                
        except Exception as e:
            self._print_debug(f"⚠️ Error consultando payment_methods en MariaDB: {e}")
            logger.warning(f"Error consultando payment_methods para código '{codigo_pago}': {e}", exc_info=True)
            return None
    
    def _determinar_modalidad_pago(self, due_date: Any) -> str:
        """
        Determina la modalidad de pago basado en la fecha de vencimiento.
        - Si hay fecha de vencimiento → 'credito'
        - Si no hay fecha de vencimiento → 'contado'
        """
        if due_date:
            # Si es string, intentar parsear
            if isinstance(due_date, str):
                due_date = due_date.strip()
                if due_date and due_date.lower() not in ['', 'none', 'null', 'nan']:
                    return 'credito'
            # Si es fecha válida (datetime, date)
            elif hasattr(due_date, 'year'):
                return 'credito'
        
        return 'contado'
    
    def leer_facturas_desde_excel_sesion(self, session_id: int) -> tuple:
        """
        Leer facturas desde el Excel de una sesión de scraping DIAN.
        Retorna (facturas, empresa_nit, empresa_ciuu_info).
        
        IMPORTANTE:
        - Si tipo='Received': nit_receptor es la empresa, nit_emisor es el proveedor
        - Si tipo='Sent': nit_emisor es la empresa, nit_receptor es el cliente
        - Cada factura puede tener un proveedor diferente
        - Modalidad de pago: se determina por fecha de vencimiento (due_date)
        - Forma de pago: se consulta desde payment_methods en MariaDB (APIDIAN)
        """
        try:
            from apps.dian_scraper.models import ScrapingSession, DocumentProcessed
            import pandas as pd
            import os
            from datetime import datetime
            
            session = ScrapingSession.objects.get(id=session_id)
            
            self._print_debug(f"📂 Leyendo facturas de sesión DIAN: {session_id} (tipo: {session.tipo})")
            
            # Determinar NIT de empresa según tipo de sesión
            if session.tipo == 'Received':
                # Facturas recibidas: nit_receptor es la empresa, nit_emisor es el proveedor
                empresa_nit = session.nit  # El NIT de la sesión es el receptor (empresa)
                self._print_debug(f"✅ Tipo Received: Empresa (receptor) = {empresa_nit}")
            else:  # Sent
                # Facturas enviadas: nit_emisor es la empresa, nit_receptor es el cliente
                empresa_nit = session.nit  # El NIT de la sesión es el emisor (empresa)
                self._print_debug(f"✅ Tipo Sent: Empresa (emisor) = {empresa_nit}")
            
            # Buscar CIUU de la empresa (cacheado)
            rut_empresa = self.buscar_rut_por_nit(empresa_nit)
            empresa_ciuu_info = {
                "ciuu_principal": rut_empresa.get('ciuu_principal') if rut_empresa else None,
                "ciuu_secundarios": rut_empresa.get('ciuu_secundarios', []) if rut_empresa else []
            }
            
            facturas = []
            
            # PRIORIDAD 1: Leer directamente desde DocumentProcessed (más rápido y confiable)
            documentos = DocumentProcessed.objects.filter(session=session).select_related('session')
            if documentos.exists():
                self._print_debug(f"📄 Leyendo {documentos.count()} documentos desde BD (raw_data.LineItems)")
                
                for doc in documentos:
                    # Determinar proveedor según tipo de sesión
                    if session.tipo == 'Received':
                        proveedor_nit = doc.supplier_nit or ''
                    else:  # Sent
                        proveedor_nit = doc.customer_nit or ''
                    
                    # Obtener datos del raw_data
                    raw_data = doc.raw_data or {}
                    due_date = raw_data.get('Fecha de Vencimiento') or raw_data.get('due_date')
                    payment_method_code = str(raw_data.get('Metodo de Pago', '') or raw_data.get('payment_method', '')).strip()
                    payment_method_description = raw_data.get('Metodo de Pago Descripcion') or raw_data.get('payment_method_description') or None
                    cufe = doc.cufe or raw_data.get('CUFE', '')
                    numero_factura = doc.document_number
                    
                    # Determinar modalidad de pago
                    modalidad_pago = self._determinar_modalidad_pago(due_date)
                    
                    # Consultar payment_methods en MariaDB para obtener nombre
                    nombre_firebird = None
                    if payment_method_code:
                        forma_pago_info = self._consultar_payment_method(empresa_nit, payment_method_code)
                        if forma_pago_info:
                            nombre_firebird = forma_pago_info.get('name')
                    
                    # Obtener forma de pago completa usando la nueva función
                    forma_pago_completa = obtener_forma_pago_completa(
                        codigo=payment_method_code,
                        descripcion_xml=payment_method_description,
                        nombre_firebird=nombre_firebird
                    )
                    
                    # Extraer artículos REALES desde raw_data.LineItems
                    articulos = []
                    line_items = raw_data.get('LineItems', [])
                    
                    if line_items and len(line_items) > 0:
                        self._print_debug(f"✅ Factura {numero_factura}: {len(line_items)} artículos REALES desde raw_data.LineItems")
                        for idx, line_item in enumerate(line_items):
                            nombre = line_item.get('Nombre del Producto', '') or line_item.get('product_name', '') or f'Artículo {idx + 1}'
                            referencia = line_item.get('Referencia', '') or line_item.get('reference', '')
                            cantidad = float(line_item.get('Cantidad', 0) or line_item.get('quantity', 0))
                            precio_unitario = float(line_item.get('Precio Unitario', 0) or line_item.get('unit_price', 0))
                            valor_total = float(line_item.get('Total', 0) or line_item.get('total', 0))
                            unidad_medida = line_item.get('Unidad de Medida', '') or line_item.get('unit_measure', '')
                            
                            # Extraer impuestos del artículo
                            impuestos = []
                            taxes = line_item.get('taxes', [])
                            if taxes:
                                for tax in taxes:
                                    impuestos.append({
                                        "code": tax.get('code', ''),
                                        "nombre": tax.get('name', ''),
                                        "porcentaje": float(tax.get('percent', 0) or tax.get('percentage', 0)),
                                        "base": float(tax.get('taxable_amount', 0) or tax.get('base', 0)),
                                        "valor": float(tax.get('amount', 0) or tax.get('value', 0))
                                    })
                            
                            articulos.append({
                                "nombre": nombre,
                                "ref": referencia or numero_factura,
                                "cantidad": cantidad,
                                "valor_unitario": precio_unitario,
                                "valor_total": valor_total,
                                "unidad_medida": unidad_medida,
                                "impuestos": impuestos
                            })
                    else:
                        # Fallback: Si no hay LineItems, crear artículo genérico
                        self._print_debug(f"⚠️ Factura {numero_factura}: Sin LineItems, usando fallback genérico")
                        articulos = [{
                            "nombre": f"Documento {numero_factura}",
                            "cantidad": 1,
                            "valor_unitario": float(doc.total_amount or 0),
                            "valor_total": float(doc.total_amount or 0),
                            "ref": numero_factura,
                            "impuestos": []
                        }]
                    
                    factura = {
                        "numero_factura": numero_factura,
                        "fecha": str(doc.issue_date) if doc.issue_date else '',
                        "cufe": cufe,
                        "modalidad_pago": modalidad_pago,
                        "forma_pago": forma_pago_completa['nombre'],
                        "forma_pago_codigo": forma_pago_completa['codigo'] if forma_pago_completa['codigo'] else None,
                        "forma_pago_descripcion": forma_pago_completa['descripcion'] if forma_pago_completa['descripcion'] else None,
                        "fecha_vencimiento": str(due_date) if due_date else None,
                        "proveedor_nit": proveedor_nit,
                        "articulos": articulos
                    }
                    facturas.append(factura)
                    self._print_debug(f"✅ Factura {numero_factura} preparada con {len(articulos)} artículos REALES")
                
                self._print_debug(f"✅ {len(facturas)} facturas leídas desde DocumentProcessed (raw_data.LineItems)")
                return facturas, empresa_nit, empresa_ciuu_info
            
            # PRIORIDAD 2: Fallback a Excel si no hay DocumentProcessed
            if session.excel_file and os.path.exists(session.excel_file.path):
                self._print_debug(f"📊 Leyendo desde Excel: {session.excel_file.path}")
                
                # Leer hoja 1: Documentos (resumen)
                df_documentos = pd.read_excel(session.excel_file.path, sheet_name='Documentos')
                
                # Leer hoja 2: Lineas (artículos detallados)
                df_lineas = None
                try:
                    df_lineas = pd.read_excel(session.excel_file.path, sheet_name='Lineas')
                    self._print_debug(f"✅ Hoja 'Lineas' encontrada con {len(df_lineas)} registros")
                    if len(df_lineas) > 0:
                        self._print_debug(f"📋 Columnas en hoja 'Lineas': {list(df_lineas.columns)}")
                except Exception as e:
                    self._print_debug(f"⚠️ No se pudo leer hoja 'Lineas': {e}")
                    # Intentar leer como segunda hoja por índice
                    try:
                        df_lineas = pd.read_excel(session.excel_file.path, sheet_name=1)
                        self._print_debug(f"✅ Segunda hoja encontrada con {len(df_lineas)} registros")
                        if len(df_lineas) > 0:
                            self._print_debug(f"📋 Columnas en segunda hoja: {list(df_lineas.columns)}")
                    except Exception as e2:
                        self._print_debug(f"⚠️ No se pudo leer segunda hoja: {e2}")
                
                print(f"\n{'='*80}")
                print(f"📊 [LEER_EXCEL] Procesando {len(df_documentos)} documentos de la hoja 'Documentos'")
                print(f"{'='*80}")
                
                for idx, (_, row) in enumerate(df_documentos.iterrows(), 1):
                    print(f"\n📄 [LEER_EXCEL] Procesando documento {idx}/{len(df_documentos)}")
                    
                    # Determinar proveedor según tipo de sesión
                    if session.tipo == 'Received':
                        # Received: supplier_nit es el emisor (proveedor)
                        proveedor_nit = str(row.get('NIT del Emisor', '')) or str(row.get('supplier_nit', '')) or str(row.get('nit_emisor', ''))
                    else:  # Sent
                        # Sent: customer_nit es el receptor (cliente, pero para clasificación es el "proveedor" de servicios)
                        proveedor_nit = str(row.get('NIT del Receptor', '')) or str(row.get('customer_nit', '')) or str(row.get('nit_receptor', ''))
                    
                    # Obtener identificadores de la factura
                    numero_factura = str(row.get('Numero de Factura', '')) or str(row.get('document_number', 'SIN_NUMERO'))
                    cufe = str(row.get('CUFE', '')) or ''
                    
                    print(f"   📋 Factura: {numero_factura}")
                    print(f"   🔑 CUFE: {cufe if cufe else 'NO DISPONIBLE'}")
                    print(f"   👤 Proveedor NIT: {proveedor_nit}")
                    
                    # Obtener fecha de vencimiento y método de pago del Excel
                    due_date = row.get('Fecha de Vencimiento') or row.get('due_date')
                    payment_method_code = str(row.get('Metodo de Pago', '') or row.get('payment_method', '')).strip()
                    
                    # Determinar modalidad de pago
                    modalidad_pago = self._determinar_modalidad_pago(due_date)
                    
                    # Consultar payment_methods para obtener nombre
                    forma_pago_info = None
                    forma_pago_nombre = "efectivo"  # Por defecto
                    if payment_method_code:
                        forma_pago_info = self._consultar_payment_method(empresa_nit, payment_method_code)
                        if forma_pago_info:
                            forma_pago_nombre = forma_pago_info.get('name', payment_method_code)
                    
                    # Buscar artículos en la hoja "Lineas" por CUFE o número de factura
                    articulos = []
                    print(f"   🔍 Buscando artículos en hoja 'Lineas'...")
                    
                    if df_lineas is not None and len(df_lineas) > 0:
                        print(f"   ✅ Hoja 'Lineas' disponible con {len(df_lineas)} registros totales")
                        
                        # Verificar que las columnas necesarias existan
                        columnas_necesarias = ['CUFE', 'Numero', 'Linea', 'Nombre_Producto', 'Cantidad', 'PrecioUnitario', 'TotalLinea']
                        columnas_faltantes = [col for col in columnas_necesarias if col not in df_lineas.columns]
                        if columnas_faltantes:
                            print(f"   ⚠️ Columnas faltantes en hoja 'Lineas': {columnas_faltantes}")
                            print(f"   📋 Columnas disponibles: {list(df_lineas.columns)}")
                        else:
                            print(f"   ✅ Todas las columnas necesarias están presentes")
                        
                        # Filtrar líneas por CUFE o número de factura
                        if cufe and 'CUFE' in df_lineas.columns:
                            print(f"   🔍 Buscando por CUFE='{cufe}' o Numero='{numero_factura}'")
                            lineas_factura = df_lineas[
                                (df_lineas['CUFE'].astype(str) == cufe) | 
                                (df_lineas['Numero'].astype(str) == numero_factura)
                            ]
                        elif 'Numero' in df_lineas.columns:
                            print(f"   🔍 Buscando solo por Numero='{numero_factura}' (sin CUFE)")
                            lineas_factura = df_lineas[df_lineas['Numero'].astype(str) == numero_factura]
                        else:
                            print(f"   ⚠️ No se encontraron columnas 'CUFE' ni 'Numero' en hoja 'Lineas'")
                            lineas_factura = pd.DataFrame()
                        
                        print(f"   📦 Líneas encontradas: {len(lineas_factura)}")
                        
                        if len(lineas_factura) == 0:
                            print(f"   ⚠️ No se encontraron líneas para esta factura")
                            # Mostrar algunos ejemplos de lo que hay en el Excel
                            if len(df_lineas) > 0:
                                print(f"   📋 Ejemplos de CUFE en Excel (primeros 5):")
                                if 'CUFE' in df_lineas.columns:
                                    print(f"      {df_lineas['CUFE'].head().tolist()}")
                                print(f"   📋 Ejemplos de Numero en Excel (primeros 5):")
                                if 'Numero' in df_lineas.columns:
                                    print(f"      {df_lineas['Numero'].head().tolist()}")
                        
                        # Agrupar líneas por número de línea (cada línea puede tener múltiples impuestos)
                        lineas_agrupadas = {}
                        for _, linea_row in lineas_factura.iterrows():
                            linea_num = int(linea_row.get('Linea', 0))
                            if linea_num not in lineas_agrupadas:
                                lineas_agrupadas[linea_num] = {
                                    'nombre': str(linea_row.get('Nombre_Producto', '')),
                                    'referencia': str(linea_row.get('Referencia', '')),
                                    'cantidad': float(linea_row.get('Cantidad', 0)),
                                    'precio_unitario': float(linea_row.get('PrecioUnitario', 0)),
                                    'total': float(linea_row.get('TotalLinea', 0)),
                                    'unidad_medida': str(linea_row.get('Medida', '')),
                                    'impuestos': []
                                }
                            
                            # Agregar impuesto si existe
                            imp_code = str(linea_row.get('ImpCode', '')).strip()
                            if imp_code and imp_code not in ['', 'nan', 'None']:
                                impuesto = {
                                    'code': imp_code,
                                    'nombre': str(linea_row.get('ImpName', '')),
                                    'porcentaje': float(linea_row.get('ImpPercent', 0)),
                                    'base': float(linea_row.get('ImpBase', 0)),
                                    'valor': float(linea_row.get('ImpValor', 0))
                                }
                                lineas_agrupadas[linea_num]['impuestos'].append(impuesto)
                        
                        # Convertir a lista de artículos
                        for linea_num in sorted(lineas_agrupadas.keys()):
                            linea = lineas_agrupadas[linea_num]
                            articulo = {
                                "nombre": linea['nombre'] or f"Artículo {linea_num}",
                                "ref": linea['referencia'] or numero_factura,
                                "cantidad": linea['cantidad'],
                                "valor_unitario": linea['precio_unitario'],
                                "valor_total": linea['total'],
                                "unidad_medida": linea['unidad_medida'],
                                "impuestos": linea['impuestos']
                            }
                            articulos.append(articulo)
                            self._print_debug(f"  ✅ Artículo {linea_num}: {articulo['nombre']} - Cant: {articulo['cantidad']} - Total: ${articulo['valor_total']} - Impuestos: {len(articulo['impuestos'])}")
                    
                    # Si no se encontraron artículos en la hoja "Lineas", crear uno genérico
                    if not articulos:
                        print(f"   ⚠️ No se encontraron artículos para factura {numero_factura}, usando total de factura")
                        total_factura = float(row.get('Total a Pagar', 0)) or float(row.get('total_amount', 0))
                        articulos = [{
                            "nombre": f"Documento {numero_factura}",
                            "cantidad": 1,
                            "valor_unitario": total_factura,
                            "valor_total": total_factura,
                            "ref": numero_factura,
                            "impuestos": []
                        }]
                        print(f"   📦 Artículo genérico creado: Total=${total_factura}")
                    
                    factura = {
                        "numero_factura": numero_factura,
                        "fecha": str(row.get('Fecha de Creación', '')) or str(row.get('issue_date', '')),
                        "cufe": cufe,
                        "modalidad_pago": modalidad_pago,
                        "forma_pago": forma_pago_nombre,
                        "forma_pago_codigo": payment_method_code if payment_method_code else None,
                        "fecha_vencimiento": str(due_date) if due_date else None,
                        "proveedor_nit": proveedor_nit,  # Cada factura puede tener proveedor diferente
                        "articulos": articulos
                    }
                    print(f"   ✅ Factura {numero_factura} preparada con {len(articulos)} artículos")
                    if len(articulos) > 0:
                        print(f"      - Primer artículo: {articulos[0].get('nombre', 'N/A')} (Cant: {articulos[0].get('cantidad', 0)}, Total: ${articulos[0].get('valor_total', 0)})")
                    facturas.append(factura)
                
                self._print_debug(f"✅ {len(facturas)} facturas leídas desde Excel")
                return facturas, empresa_nit, empresa_ciuu_info
            
            # Si no hay DocumentProcessed ni Excel, retornar vacío
            self._print_debug(f"⚠️ No se encontraron documentos ni Excel para sesión {session_id}")
            return [], empresa_nit, empresa_ciuu_info
            
        except ScrapingSession.DoesNotExist:
            if session.excel_file and os.path.exists(session.excel_file.path):
                try:
                    df_lineas = pd.read_excel(session.excel_file.path, sheet_name='Lineas')
                    self._print_debug(f"✅ Hoja 'Lineas' encontrada para DocumentProcessed con {len(df_lineas)} registros")
                except Exception as e:
                    try:
                        df_lineas = pd.read_excel(session.excel_file.path, sheet_name=1)
                        self._print_debug(f"✅ Segunda hoja encontrada para DocumentProcessed con {len(df_lineas)} registros")
                    except Exception as e2:
                        self._print_debug(f"⚠️ No se pudo leer hoja de artículos: {e2}")
            
            for doc in documentos:
                # Determinar proveedor según tipo de sesión
                if session.tipo == 'Received':
                    # Received: supplier_nit es el emisor (proveedor)
                    proveedor_nit = doc.supplier_nit or ''
                else:  # Sent
                    # Sent: customer_nit es el receptor (cliente)
                    proveedor_nit = doc.customer_nit or ''
                
                # Obtener datos del raw_data si está disponible
                raw_data = doc.raw_data or {}
                due_date = raw_data.get('Fecha de Vencimiento') or raw_data.get('due_date')
                payment_method_code = str(raw_data.get('Metodo de Pago', '') or raw_data.get('payment_method', '')).strip()
                payment_method_description = raw_data.get('Metodo de Pago Descripcion') or raw_data.get('payment_method_description') or None
                cufe = doc.cufe or raw_data.get('CUFE', '')
                numero_factura = doc.document_number
                
                # Determinar modalidad de pago
                modalidad_pago = self._determinar_modalidad_pago(due_date)
                
                # Consultar payment_methods en Firebird para obtener nombre
                nombre_firebird = None
                if payment_method_code:
                    forma_pago_info = self._consultar_payment_method(empresa_nit, payment_method_code)
                    if forma_pago_info:
                        nombre_firebird = forma_pago_info.get('name')
                
                # Obtener forma de pago completa usando la nueva función
                forma_pago_completa = obtener_forma_pago_completa(
                    codigo=payment_method_code,
                    descripcion_xml=payment_method_description,
                    nombre_firebird=nombre_firebird
                )
                
                # Buscar artículos en la hoja "Lineas" por CUFE o número de factura
                articulos = []
                if df_lineas is not None and len(df_lineas) > 0:
                    # Filtrar líneas por CUFE o número de factura
                    if cufe:
                        lineas_factura = df_lineas[
                            (df_lineas['CUFE'].astype(str) == cufe) | 
                            (df_lineas['Numero'].astype(str) == numero_factura)
                        ]
                    else:
                        lineas_factura = df_lineas[df_lineas['Numero'].astype(str) == numero_factura]
                    
                    self._print_debug(f"📦 Factura {numero_factura} (CUFE: {cufe}): {len(lineas_factura)} artículos encontrados")
                    
                    # Agrupar líneas por número de línea (cada línea puede tener múltiples impuestos)
                    lineas_agrupadas = {}
                    for _, linea_row in lineas_factura.iterrows():
                        linea_num = int(linea_row.get('Linea', 0))
                        if linea_num not in lineas_agrupadas:
                            lineas_agrupadas[linea_num] = {
                                'nombre': str(linea_row.get('Nombre_Producto', '')),
                                'referencia': str(linea_row.get('Referencia', '')),
                                'cantidad': float(linea_row.get('Cantidad', 0)),
                                'precio_unitario': float(linea_row.get('PrecioUnitario', 0)),
                                'total': float(linea_row.get('TotalLinea', 0)),
                                'unidad_medida': str(linea_row.get('Medida', '')),
                                'impuestos': []
                            }
                        
                        # Agregar impuesto si existe
                        imp_code = str(linea_row.get('ImpCode', '')).strip()
                        if imp_code and imp_code not in ['', 'nan', 'None']:
                            impuesto = {
                                'code': imp_code,
                                'nombre': str(linea_row.get('ImpName', '')),
                                'porcentaje': float(linea_row.get('ImpPercent', 0)),
                                'base': float(linea_row.get('ImpBase', 0)),
                                'valor': float(linea_row.get('ImpValor', 0))
                            }
                            lineas_agrupadas[linea_num]['impuestos'].append(impuesto)
                    
                    # Convertir a lista de artículos
                    for linea_num in sorted(lineas_agrupadas.keys()):
                        linea = lineas_agrupadas[linea_num]
                        articulos.append({
                            "nombre": linea['nombre'] or f"Artículo {linea_num}",
                            "ref": linea['referencia'] or numero_factura,
                            "cantidad": linea['cantidad'],
                            "valor_unitario": linea['precio_unitario'],
                            "valor_total": linea['total'],
                            "unidad_medida": linea['unidad_medida'],
                            "impuestos": linea['impuestos']
                        })
                
                # Si no se encontraron artículos, intentar desde raw_data (LineItems)
                if not articulos and raw_data.get('LineItems'):
                    self._print_debug(f"📦 Usando LineItems de raw_data para factura {numero_factura}")
                    for line_item in raw_data.get('LineItems', []):
                        impuestos_linea = []
                        for tax in line_item.get('taxes', []):
                            impuestos_linea.append({
                                'code': tax.get('code', ''),
                                'nombre': tax.get('name', ''),
                                'porcentaje': float(tax.get('percent', 0)),
                                'base': float(tax.get('taxable_amount', 0)),
                                'valor': float(tax.get('amount', 0))
                            })
                        
                        articulos.append({
                            "nombre": line_item.get('Nombre del Producto', '') or f"Artículo",
                            "ref": line_item.get('Referencia', '') or numero_factura,
                            "cantidad": float(line_item.get('Cantidad', 0)),
                            "valor_unitario": float(line_item.get('Precio Unitario', 0)),
                            "valor_total": float(line_item.get('Total', 0)),
                            "unidad_medida": line_item.get('Unidad de Medida', ''),
                            "impuestos": impuestos_linea
                        })
                
                # Si aún no hay artículos, crear uno genérico
                if not articulos:
                    self._print_debug(f"⚠️ No se encontraron artículos para factura {numero_factura}, usando total")
                    articulos = [{
                        "nombre": f"Documento {doc.document_number}",
                        "cantidad": 1,
                        "valor_unitario": float(doc.total_amount or 0),
                        "valor_total": float(doc.total_amount or 0),
                        "ref": doc.document_number,
                        "impuestos": []
                    }]
                
                factura = {
                    "numero_factura": numero_factura,
                    "fecha": str(doc.issue_date) if doc.issue_date else '',
                    "cufe": cufe,
                    "modalidad_pago": modalidad_pago,
                    "forma_pago": forma_pago_completa['nombre'],
                    "forma_pago_codigo": forma_pago_completa['codigo'] if forma_pago_completa['codigo'] else None,
                    "forma_pago_descripcion": forma_pago_completa['descripcion'] if forma_pago_completa['descripcion'] else None,
                    "fecha_vencimiento": str(due_date) if due_date else None,
                    "proveedor_nit": proveedor_nit,  # Cada factura puede tener proveedor diferente
                    "articulos": articulos
                }
                facturas.append(factura)
            
            self._print_debug(f"✅ {len(facturas)} facturas leídas desde DocumentProcessed")
            return facturas, empresa_nit, empresa_ciuu_info
            
        except ScrapingSession.DoesNotExist:
            self._print_debug(f"❌ Sesión {session_id} no encontrada")
            return [], None, None
        except Exception as e:
            self._print_debug(f"❌ Error leyendo facturas: {e}")
            logger.error(f"Error leyendo facturas de sesión {session_id}: {e}", exc_info=True)
            return [], None, None
    
    def leer_documento_por_id(self, document_id: int) -> Dict[str, Any]:
        """
        Leer un documento específico por ID y convertirlo a formato de factura.
        Retorna (factura, empresa_nit, empresa_ciuu_info, proveedor_nit).
        Incluye lógica de modalidad de pago y consulta de payment_methods.
        
        IMPORTANTE: Lee desde raw_data (BD), que debería ser idéntico al Excel.
        SIEMPRE extrae TODOS los artículos reales desde raw_data.LineItems,
        nunca un artículo genérico acumulado.
        """
        try:
            from apps.dian_scraper.models import DocumentProcessed
            
            doc = DocumentProcessed.objects.select_related('session').get(id=document_id)
            session = doc.session
            
            self._print_debug(f"📄 [LEER_DOCUMENTO] Leyendo documento ID: {document_id} de sesión {session.id} (tipo: {session.tipo})")
            self._print_debug(f"💾 [LEER_DOCUMENTO] Modo: LECTURA DESDE raw_data (BD)")
            
            # Determinar NIT de empresa según tipo de sesión
            # Preferir NIT del documento si está disponible (puede ser más completo)
            if session.tipo == 'Received':
                # Receptor es la empresa - usar customer_nit del documento si está disponible
                empresa_nit = doc.customer_nit or session.nit
                proveedor_nit = doc.supplier_nit or ''  # Emisor es el proveedor
            else:  # Sent
                # Emisor es la empresa - usar supplier_nit del documento si está disponible
                empresa_nit = doc.supplier_nit or session.nit
                proveedor_nit = doc.customer_nit or ''
            
            self._print_debug(f"🏢 [LEER_DOCUMENTO] Empresa NIT: {empresa_nit} (sesión: {session.nit}, doc: {doc.customer_nit if session.tipo == 'Received' else doc.supplier_nit})")
            
            # ✅ CORRECCIÓN: Buscar primero directamente con el NIT de la sesión (más completo y confiable)
            # El NIT de la sesión viene directamente del modelo DianScrapingSession y no debe recortarse
            rut_empresa = None
            if session.nit:
                self._print_debug(f"🔍 [LEER_DOCUMENTO] Buscando RUT primero con NIT de sesión (directo): {session.nit}")
                rut_empresa = self.buscar_rut_por_nit(session.nit)
                if rut_empresa:
                    empresa_nit = session.nit  # Usar el NIT de la sesión que funcionó
                    self._print_debug(f"✅ [LEER_DOCUMENTO] RUT encontrado con NIT de sesión: {session.nit}")
            
            # Si no se encuentra con el NIT de la sesión, intentar con el NIT del documento
            if not rut_empresa and empresa_nit and empresa_nit != session.nit:
                self._print_debug(f"🔍 [LEER_DOCUMENTO] No se encontró RUT con NIT de sesión, intentando con NIT del documento: {empresa_nit}")
                rut_empresa = self.buscar_rut_por_nit(empresa_nit)
                if rut_empresa:
                    self._print_debug(f"✅ [LEER_DOCUMENTO] RUT encontrado con NIT del documento: {empresa_nit}")
            
            # Si aún no se encuentra, intentar búsqueda con LIKE (más eficiente que variaciones manuales)
            if not rut_empresa and empresa_nit:
                nit_base = re.sub(r'\D', '', empresa_nit)
                if len(nit_base) >= 7 and len(nit_base) <= 10:
                    self._print_debug(f"🔍 [LEER_DOCUMENTO] Buscando RUT con LIKE: {nit_base}%")
                    # Buscar RUTs cuyo nit_normalizado empiece con el NIT base
                    rut_like = RUT.objects.filter(nit_normalizado__startswith=nit_base).first()
                    if rut_like:
                        # Usar el NIT completo del RUT encontrado
                        empresa_nit_completo = rut_like.nit if rut_like.nit else f"{rut_like.nit_normalizado}-{rut_like.dv}" if rut_like.dv else rut_like.nit_normalizado
                        self._print_debug(f"✅ [LEER_DOCUMENTO] RUT encontrado con LIKE: {rut_like.nit_normalizado} (NIT completo: {empresa_nit_completo})")
                        # Construir respuesta en el mismo formato que buscar_rut_por_nit
                        ciuu_principal = rut_like.actividad_principal_ciiu if hasattr(rut_like, 'actividad_principal_ciiu') else None
                        ciuu_secundarios = []
                        if hasattr(rut_like, 'actividad_secundaria_ciiu') and rut_like.actividad_secundaria_ciiu:
                            ciuu_secundarios.append(rut_like.actividad_secundaria_ciiu)
                        if hasattr(rut_like, 'otras_actividades_ciiu') and rut_like.otras_actividades_ciiu:
                            otras = rut_like.otras_actividades_ciiu
                            if isinstance(otras, list):
                                ciuu_secundarios.extend(otras)
                            elif isinstance(otras, str):
                                try:
                                    otras_list = json.loads(otras) if otras.startswith('[') else [otras]
                                    ciuu_secundarios.extend(otras_list)
                                except:
                                    ciuu_secundarios.append(otras)
                        rut_empresa = {
                            "nit": rut_like.nit,
                            "nit_normalizado": rut_like.nit_normalizado,
                            "razon_social": rut_like.razon_social,
                            "ciuu_principal": ciuu_principal,
                            "ciuu_secundarios": list(set(ciuu_secundarios)),
                            "fuente": "rut_like"
                        }
                        empresa_nit = empresa_nit_completo
            
            empresa_ciuu_info = {
                "ciuu_principal": rut_empresa.get('ciuu_principal') if rut_empresa else None,
                "ciuu_secundarios": rut_empresa.get('ciuu_secundarios', []) if rut_empresa else []
            }
            
            # Obtener datos del raw_data (BD)
            raw_data = doc.raw_data or {}
            due_date = raw_data.get('Fecha de Vencimiento') or raw_data.get('due_date')
            payment_method_code = str(raw_data.get('Metodo de Pago', '') or raw_data.get('payment_method', '')).strip()
            
            # Extraer descripción del método de pago si está disponible en raw_data
            payment_method_description = raw_data.get('Metodo de Pago Descripcion') or raw_data.get('payment_method_description') or None
            
            # Determinar modalidad de pago
            modalidad_pago = self._determinar_modalidad_pago(due_date)
            
            # Consultar payment_methods en Firebird para obtener nombre
            nombre_firebird = None
            if payment_method_code:
                forma_pago_info = self._consultar_payment_method(empresa_nit, payment_method_code)
                if forma_pago_info:
                    nombre_firebird = forma_pago_info.get('name')
            
            # Obtener forma de pago completa usando la nueva función
            forma_pago_completa = obtener_forma_pago_completa(
                codigo=payment_method_code,
                descripcion_xml=payment_method_description,
                nombre_firebird=nombre_firebird
            )
            
            # EXTRAER TODOS LOS ARTÍCULOS REALES desde raw_data.LineItems
            articulos = []
            line_items = raw_data.get('LineItems', [])
            
            self._print_debug(f"📦 [LEER_DOCUMENTO] Buscando artículos en raw_data.LineItems...")
            self._print_debug(f"   - LineItems encontrados: {len(line_items)}")
            
            if line_items and len(line_items) > 0:
                self._print_debug(f"✅ [LEER_DOCUMENTO] Usando LineItems REALES de raw_data ({len(line_items)} artículos)")
                for idx, line_item in enumerate(line_items):
                    # Extraer datos del artículo
                    nombre = line_item.get('Nombre del Producto', '') or line_item.get('product_name', '') or f'Artículo {idx + 1}'
                    referencia = line_item.get('Referencia', '') or line_item.get('reference', '')
                    cantidad = float(line_item.get('Cantidad', 0) or line_item.get('quantity', 0))
                    precio_unitario = float(line_item.get('Precio Unitario', 0) or line_item.get('unit_price', 0))
                    valor_total = float(line_item.get('Total', 0) or line_item.get('total', 0))
                    unidad_medida = line_item.get('Unidad de Medida', '') or line_item.get('unit_measure', '')
                    
                    # Extraer impuestos del artículo (cada artículo puede tener múltiples impuestos)
                    impuestos = []
                    taxes = line_item.get('taxes', [])
                    if taxes:
                        for tax in taxes:
                            impuestos.append({
                                "code": tax.get('code', ''),
                                "nombre": tax.get('name', ''),
                                "porcentaje": float(tax.get('percent', 0) or tax.get('percentage', 0)),
                                "base": float(tax.get('taxable_amount', 0) or tax.get('base', 0)),
                                "valor": float(tax.get('amount', 0) or tax.get('value', 0))
                            })
                    
                    articulos.append({
                        "nombre": nombre,
                        "ref": referencia or doc.document_number,
                        "cantidad": cantidad,
                        "valor_unitario": precio_unitario,
                        "valor_total": valor_total,
                        "unidad_medida": unidad_medida,
                        "impuestos": impuestos
                    })
                
                self._print_debug(f"   ✅ Artículos extraídos: {len(articulos)}")
                if len(articulos) > 0:
                    self._print_debug(f"   - Primer artículo: {articulos[0].get('nombre')} - Cant: {articulos[0].get('cantidad')} - Total: ${articulos[0].get('valor_total')} - Impuestos: {len(articulos[0].get('impuestos', []))}")
            else:
                # SOLO como último recurso si NO hay LineItems en raw_data
                self._print_debug(f"⚠️ [LEER_DOCUMENTO] ⚠️ ADVERTENCIA: No se encontraron LineItems en raw_data")
                self._print_debug(f"⚠️ [LEER_DOCUMENTO] Esto NO debería pasar si el documento fue procesado correctamente")
                self._print_debug(f"⚠️ [LEER_DOCUMENTO] Usando artículo genérico como último recurso")
                articulos = [{
                    "nombre": f"Documento {doc.document_number}",
                    "cantidad": 1,
                    "valor_unitario": float(doc.total_amount or 0),
                    "valor_total": float(doc.total_amount or 0),
                    "ref": doc.document_number,
                    "impuestos": []
                }]
            
            factura = {
                "numero_factura": doc.document_number,
                "fecha": str(doc.issue_date) if doc.issue_date else '',
                "modalidad_pago": modalidad_pago,
                "forma_pago": forma_pago_completa['nombre'],
                "forma_pago_codigo": forma_pago_completa['codigo'] if forma_pago_completa['codigo'] else None,
                "forma_pago_descripcion": forma_pago_completa['descripcion'] if forma_pago_completa['descripcion'] else None,
                "fecha_vencimiento": str(due_date) if due_date else None,
                "proveedor_nit": proveedor_nit,
                "articulos": articulos  # TODOS los artículos reales, cada uno con su valor, IVA, tipo de impuesto, etc.
            }
            
            self._print_debug(f"✅ [LEER_DOCUMENTO] Documento convertido a factura: {doc.document_number}")
            self._print_debug(f"   - Total artículos: {len(articulos)}")
            self._print_debug(f"   - Cada artículo tiene: nombre, cantidad, valor_unitario, valor_total, impuestos")
            
            return {
                "factura": factura,
                "empresa_nit": empresa_nit,
                "empresa_ciuu_info": empresa_ciuu_info,
                "proveedor_nit": proveedor_nit,
                "session_id": session.id
            }
            
        except DocumentProcessed.DoesNotExist:
            self._print_debug(f"❌ Documento {document_id} no encontrado")
            return None
        except Exception as e:
            self._print_debug(f"❌ Error leyendo documento: {e}")
            logger.error(f"Error leyendo documento {document_id}: {e}", exc_info=True)
            return None
    
    def guardar_clasificacion(
        self,
        factura_numero: str,
        proveedor_nit: str,
        empresa_nit: str,
        empresa_ciuu_principal: str,
        proveedor_ciuu: Optional[str],
        resultado: Dict[str, Any],
        session_dian_id: Optional[int] = None
    ) -> ClasificacionContable:
        """
        Guardar resultado de clasificación en la base de datos.
        """
        print(f"\n{'='*80}")
        print(f"💾 [GUARDAR_CLASIFICACION] Guardando clasificación para factura: {factura_numero}")
        print(f"{'='*80}")
        
        # Verificar qué se está guardando en factura_json_enviada
        factura_json_enviada = resultado.get('factura_json_enviada', {})
        articulos_a_guardar = factura_json_enviada.get('articulos', [])
        print(f"📦 [GUARDAR_CLASIFICACION] Artículos a guardar: {len(articulos_a_guardar)}")
        if len(articulos_a_guardar) > 0:
            print(f"   ✅ Primer artículo: {articulos_a_guardar[0]}")
        else:
            print(f"   ⚠️ factura_json_enviada.articulos está VACÍO")
            print(f"   📋 factura_json_enviada completo: {factura_json_enviada}")
        
        try:
            nit_normalizado, _, _ = normalize_nit_and_extract_dv(proveedor_nit)
            
            # Calcular confianza promedio
            confianza_promedio = None
            total_articulos = 0
            if resultado.get('success') and resultado.get('respuesta_factura'):
                clasificaciones = resultado['respuesta_factura'].get('clasificaciones', {})
                for factura_id, articulos in clasificaciones.items():
                    total_articulos += len(articulos)
                    confianzas = [a.get('confianza', 'PENDIENTE') for a in articulos if 'confianza' in a]
                    if confianzas:
                        # Contar por nivel
                        alta = confianzas.count('ALTA')
                        media = confianzas.count('MEDIA')
                        baja = confianzas.count('BAJA')
                        if alta > media and alta > baja:
                            confianza_promedio = 'ALTA'
                        elif media > baja:
                            confianza_promedio = 'MEDIA'
                        else:
                            confianza_promedio = 'BAJA'
            
            # Verificar antes de guardar
            print(f"💾 [GUARDAR_CLASIFICACION] Preparando para guardar en BD:")
            print(f"   - factura_numero: {factura_numero}")
            print(f"   - session_dian_id: {session_dian_id}")
            print(f"   - factura_json_enviada tiene articulos: {bool(articulos_a_guardar)}")
            print(f"   - Cantidad de artículos: {len(articulos_a_guardar)}")
            if len(articulos_a_guardar) > 0:
                print(f"   - Primer artículo: {articulos_a_guardar[0]}")
            
            # PROTECCIÓN CONTRA DUPLICADOS: Verificar si ya existe clasificación para esta factura en esta sesión
            # Esto previene duplicados por:
            # - Clicks múltiples en "clasificar toda la sesión"
            # - Retries de Celery
            # - Race conditions con múltiples workers
            clasificacion_existente = None
            if session_dian_id and factura_numero:
                clasificacion_existente = ClasificacionContable.objects.filter(
                    session_dian_id=session_dian_id,
                    factura_numero=factura_numero
                ).order_by('-created_at').first()  # Obtener la más reciente
            
            if clasificacion_existente:
                print(f"⚠️ [GUARDAR_CLASIFICACION] Ya existe clasificación para factura {factura_numero} en sesión {session_dian_id}")
                print(f"   - Clasificación existente ID: {clasificacion_existente.id}")
                print(f"   - Creada: {clasificacion_existente.created_at}")
                print(f"   - Estado: {clasificacion_existente.estado}")
                print(f"   - Actualizando clasificación existente en lugar de crear duplicado...")
                
                # Actualizar la clasificación existente con los nuevos datos
                clasificacion_existente.proveedor_nit = proveedor_nit
                clasificacion_existente.proveedor_nit_normalizado = nit_normalizado
                clasificacion_existente.empresa_nit = empresa_nit
                clasificacion_existente.empresa_ciuu_principal = empresa_ciuu_principal
                clasificacion_existente.proveedor_ciuu = proveedor_ciuu
                clasificacion_existente.costo_total_factura = resultado.get('costo', {}).get('costo_usd', 0)
                clasificacion_existente.costo_total_cop = resultado.get('costo', {}).get('costo_cop', 0)
                clasificacion_existente.costo_por_articulo = resultado.get('costo', {}).get('costo_usd', 0) / total_articulos if total_articulos > 0 else 0
                clasificacion_existente.tiempo_procesamiento_segundos = resultado.get('tiempo_procesamiento', 0)
                clasificacion_existente.tokens_input = resultado.get('tokens', {}).get('input', 0)
                clasificacion_existente.tokens_output = resultado.get('tokens', {}).get('output', 0)
                clasificacion_existente.factura_json_enviada = resultado.get('factura_json_enviada', {})
                clasificacion_existente.respuesta_json_completa = resultado.get('respuesta_json_completa', {})
                clasificacion_existente.respuesta_json_factura = resultado.get('respuesta_factura', {})
                clasificacion_existente.estado = 'completado' if resultado.get('success') else 'fallido'
                clasificacion_existente.error_message = resultado.get('error')
                clasificacion_existente.confianza_promedio = confianza_promedio
                clasificacion_existente.total_articulos = total_articulos
                clasificacion_existente.procesado_at = timezone.now() if resultado.get('success') else None
                clasificacion_existente.save()
                
                clasificacion = clasificacion_existente
                print(f"✅ [GUARDAR_CLASIFICACION] Clasificación actualizada (ID {clasificacion.id})")
            else:
                # No existe, crear nueva
                print(f"✅ [GUARDAR_CLASIFICACION] No existe clasificación previa, creando nueva...")
                clasificacion = ClasificacionContable.objects.create(
                    session_dian_id=session_dian_id,
                    factura_numero=factura_numero,
                    proveedor_nit=proveedor_nit,
                    proveedor_nit_normalizado=nit_normalizado,
                    empresa_nit=empresa_nit,
                    empresa_ciuu_principal=empresa_ciuu_principal,
                    proveedor_ciuu=proveedor_ciuu,
                    costo_total_factura=resultado.get('costo', {}).get('costo_usd', 0),
                    costo_total_cop=resultado.get('costo', {}).get('costo_cop', 0),
                    costo_por_articulo=resultado.get('costo', {}).get('costo_usd', 0) / total_articulos if total_articulos > 0 else 0,
                    tiempo_procesamiento_segundos=resultado.get('tiempo_procesamiento', 0),
                    tokens_input=resultado.get('tokens', {}).get('input', 0),
                    tokens_output=resultado.get('tokens', {}).get('output', 0),
                    factura_json_enviada=resultado.get('factura_json_enviada', {}),
                    respuesta_json_completa=resultado.get('respuesta_json_completa', {}),
                    respuesta_json_factura=resultado.get('respuesta_factura', {}),
                    estado='completado' if resultado.get('success') else 'fallido',
                    error_message=resultado.get('error'),
                    confianza_promedio=confianza_promedio,
                    total_articulos=total_articulos,
                    procesado_at=timezone.now() if resultado.get('success') else None
                )
                print(f"✅ [GUARDAR_CLASIFICACION] Clasificación creada (ID {clasificacion.id})")
            
            # Verificar después de guardar
            print(f"✅ [GUARDAR_CLASIFICACION] Clasificación guardada: ID {clasificacion.id}")
            print(f"   📋 Verificando factura_json_enviada guardado...")
            clasificacion_refreshed = ClasificacionContable.objects.get(id=clasificacion.id)
            factura_guardada = clasificacion_refreshed.factura_json_enviada or {}
            articulos_guardados = factura_guardada.get('articulos', [])
            print(f"   - factura_json_enviada existe: {bool(factura_guardada)}")
            print(f"   - Artículos guardados en BD: {len(articulos_guardados)}")
            if len(articulos_guardados) > 0:
                print(f"   ✅ Primer artículo guardado: {articulos_guardados[0]}")
            else:
                print(f"   ⚠️ factura_json_enviada.articulos está VACÍO en BD")
                print(f"   📋 factura_json_enviada completo guardado: {factura_guardada}")
            print(f"{'='*80}\n")
            
            self._print_debug(f"💾 Clasificación guardada: ID {clasificacion.id}")
            return clasificacion
            
        except Exception as e:
            self._print_debug(f"❌ Error guardando clasificación: {e}")
            logger.error(f"Error guardando clasificación: {e}", exc_info=True)
            raise

