# sistema_analitico/views.py
# 🔹 Librerías estándar
import logging
import os
import pandas as pd
import re
import secrets
import time
import requests
import base64
from calendar import monthrange
from datetime import datetime, timedelta, date
from decimal import Decimal
import firebirdsql

# 🔹 Django y DRF
from django.conf import settings
from django.db.models import Count, Sum, Avg, Max, Min, Q, F, Value
from django.db.models.functions import TruncMonth, TruncYear, TruncQuarter, Coalesce
from django.utils import timezone
from django.http import HttpRequest

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import BaseAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

# 🔹 Modelos, serializadores y servicios internos
from .models import (
    VpnConfig,
    Servidor,
    EmpresaServidor,
    MovimientoInventario,
    UsuarioEmpresa,
    UserTenantProfile,
    APIKeyCliente,
    EmpresaPersonalizacion,
    GrupoMaterialImagen,
    MaterialImagen,
    CajaAutopago,
    NotaRapida,
    EmpresaDominio,
    EmpresaEcommerceConfig,
    PasarelaPago,
    TransaccionPago,
    RUT,
    EstablecimientoRUT,
    normalize_nit_and_extract_dv,
    ConfiguracionS3,
    BackupS3,
    AIAnalyticsAPIKey,
)
from .serializers import *
from .services.data_manager import DataManager
from .services.ml_engine import MLEngine
from .services.natural_response_orchestrator import NaturalResponseOrchestrator
from .services.system_tester import SystemTester
from .services.permisos import TienePermisoEmpresa, HasValidAPIKey
from .services.tns_bridge import TNSBridge

# 🔹 Logger
logger = logging.getLogger(__name__)
FIREBIRD_CHARSET = 'WIN1252'

def _normalize_nit(value: str) -> str:
    """
    Normaliza NIT eliminando puntos, guiones y cualquier carácter no numérico.
    Ejemplos:
    - "13.279.115-7" -> "132791157"
    - "13279115-7" -> "132791157"
    - "132791157" -> "132791157"
    """
    if not value:
        return ""
    # Eliminar todos los caracteres no numéricos (puntos, guiones, espacios, etc.)
    return re.sub(r"\D", "", str(value))


def _extract_subdomain_from_request(request):
    header = request.META.get('HTTP_X_SUBDOMAIN')
    if header:
        return str(header).strip().lower()

    query_param = None
    if hasattr(request, 'query_params'):
        query_param = request.query_params.get('subdomain')
    if not query_param and isinstance(getattr(request, 'data', None), dict):
        query_param = request.data.get('subdomain')
    if query_param:
        return str(query_param).strip().lower()

    host = request.get_host() or ''
    host = host.split(':')[0]
    if not host:
        return None
    parts = [part for part in host.split('.') if part]
    if len(parts) > 2:
        return parts[0].lower()
    if len(parts) == 2 and parts[0].lower() not in ('www', 'localhost'):
        return parts[0].lower()
    return None


def _clean_nit(value: str) -> str:
    """Normaliza un NIT eliminando DV y separadores."""
    if not value:
        return ""
    nit_str = str(value).replace('.', '').replace(' ', '')
    base = nit_str.split('-')[0]
    return re.sub(r"\D", "", base)


def _decode_firebird_value(value):
    """Decodifica valores de Firebird a string UTF-8 seguro para JSON (retrocompatible)"""
    # Si es None o no es bytes/string, retornar tal cual (retrocompatible)
    if value is None:
        return None
    if not isinstance(value, (bytes, str)):
        return value
    
    if isinstance(value, bytes):
        try:
            # Decodificar desde WIN1252 (charset de Firebird)
            decoded = value.decode(FIREBIRD_CHARSET, errors='replace')
        except (UnicodeDecodeError, LookupError):
            try:
                # Fallback a latin-1
                decoded = value.decode('latin-1', errors='replace')
            except Exception:
                # Último recurso
                decoded = value.decode('utf-8', errors='replace')
        
        # Solo normalizar si hay caracteres problemáticos (evitar doble encoding innecesario)
        try:
            # Intentar codificar a UTF-8 - si falla, hay caracteres problemáticos
            decoded.encode('utf-8')
            return decoded  # Ya es UTF-8 válido, retornar tal cual
        except UnicodeEncodeError:
            # Hay caracteres problemáticos, normalizar
            return decoded.encode('utf-8', errors='replace').decode('utf-8')
    else:
        # Ya es string - solo normalizar si es necesario (retrocompatible)
        try:
            # Verificar si ya es UTF-8 válido
            value.encode('utf-8')
            return value  # Ya es UTF-8 válido, retornar tal cual (retrocompatible)
        except UnicodeEncodeError:
            # Tiene caracteres problemáticos, normalizar
            return value.encode('utf-8', errors='replace').decode('utf-8')


def _rows_to_dicts(cursor, rows):
    # Decodificar nombres de columnas si vienen como bytes (retrocompatible)
    # Si ya son strings, mantener comportamiento original
    columns = []
    for col in cursor.description or []:
        col_name = col[0]
        # Solo decodificar si es bytes (retrocompatible)
        if isinstance(col_name, bytes):
            try:
                col_name = col_name.decode(FIREBIRD_CHARSET, errors='replace')
            except (UnicodeDecodeError, LookupError):
                try:
                    col_name = col_name.decode('latin-1', errors='replace')
                except Exception:
                    col_name = str(col_name, errors='replace')
        # Si ya es string, mantener tal cual (retrocompatible)
        columns.append(col_name.strip() if isinstance(col_name, str) else str(col_name).strip())
    
    results = []
    for row in rows:
        entry = {}
        for idx, column in enumerate(columns):
            entry[column] = _decode_firebird_value(row[idx])
        results.append(entry)
    return results


def _resolve_admin_db_path(empresa):
    config = empresa.configuracion if isinstance(empresa.configuracion, dict) else {}
    config_path = config.get('admin_db_path') or config.get('admin_db')
    return config_path or empresa.servidor.ruta_maestra


def _connect_admin_db(empresa):
    database_path = _resolve_admin_db_path(empresa)
    if not database_path:
        raise serializers.ValidationError('El servidor no tiene ruta configurada para ADMIN.gdb')
    os.environ['ISC_CP'] = FIREBIRD_CHARSET
    servidor = empresa.servidor
    return firebirdsql.connect(
        host=servidor.host,
        database=database_path,
        user=servidor.usuario,
        password=servidor.password,
        port=servidor.puerto or 3050,
        charset=FIREBIRD_CHARSET
    )


def _query_admin_empresas(empresa, target_nit):
    nit_clean = _clean_nit(target_nit)
    conn = _connect_admin_db(empresa)
    try:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT 1 FROM RDB$RELATIONS
                WHERE RDB$RELATION_NAME = 'EMPRESAS'
                AND RDB$SYSTEM_FLAG = 0
            """)
            if not cursor.fetchone():
                raise serializers.ValidationError('La tabla EMPRESAS no existe en la base ADMIN')
            cursor.execute("""
                SELECT CODIGO, NOMBRE, NIT, ANOFIS, REPRES, ARCHIVO
                FROM EMPRESAS
                WHERE 
                    REPLACE(REPLACE(SUBSTRING(NIT FROM 1 FOR POSITION('-' IN NIT || '-') - 1), '.', ''), ' ', '') = ?
                    OR REPLACE(REPLACE(NIT, '.', ''), ' ', '') = ?
                ORDER BY ANOFIS DESC
            """, (nit_clean, nit_clean))
            empresas = _rows_to_dicts(cursor, cursor.fetchall())
        finally:
            cursor.close()
    finally:
        conn.close()
    return {
        'count': len(empresas),
        'nit_buscado': nit_clean,
        'empresas': empresas
    }


def _run_validation_procedure(cursor, username, password):
    cursor.execute("SELECT * FROM TNS_WS_VERIFICAR_USUARIO(?, ?)", (password, username))
    row = cursor.fetchone()
    if not row:
        raise serializers.ValidationError('TNS_WS_VERIFICAR_USUARIO no retorn? datos')
    # Decodificar nombres de columnas si vienen como bytes (retrocompatible)
    # Si ya son strings, mantener comportamiento original
    columns = []
    for col in cursor.description or []:
        col_name = col[0]
        # Solo decodificar si es bytes (retrocompatible)
        if isinstance(col_name, bytes):
            try:
                col_name = col_name.decode(FIREBIRD_CHARSET, errors='replace')
            except (UnicodeDecodeError, LookupError):
                try:
                    col_name = col_name.decode('latin-1', errors='replace')
                except Exception:
                    col_name = str(col_name, errors='replace')
        # Si ya es string, mantener tal cual (retrocompatible)
        columns.append(col_name.strip() if isinstance(col_name, str) else str(col_name).strip())
    return {columns[idx]: _decode_firebird_value(row[idx]) for idx in range(len(columns))}


def _build_validate_payload(row):
    fields = [
        'OVERSIONDB', 'ODESCRIPUSER', 'OIMPOBSERVFACT', 'OMANEJAREDESPACHO',
        'OASENTARSINCUPO', 'OOCULTARVENCIMIENTOPEDIDO', 'OBLOQUEARFACTURACION',
        'OBLOQUEARRECIBOCAJA', 'OIGNORARSALDOCARTERA', 'OAPARTADO',
        'OUSERNAME', 'OSUCCESS', 'OMENSAJE'
    ]
    payload = {}
    for field in fields:
        value = row.get(field)
        if value is None:
            payload[field] = 'VACIO'
        else:
            text_value = str(value).strip()
            payload[field] = text_value if text_value else 'VACIO'
    return payload


def _build_modulos_payload(rows):
    modulos_prohibidos = set()
    for row in rows:
        descripcion = str(row.get('DESCRIPCION') or '').strip()
        modulo = str(row.get('MODULO') or '').strip()
        if descripcion.startswith('No Permitir Ingreso al Modulo de'):
            modulos_prohibidos.add(modulo)
    modulos = {}
    for row in rows:
        modulo = str(row.get('MODULO') or '').strip()
        tabla = str(row.get('TABLA') or '').strip()
        if not modulo or not tabla or modulo in modulos_prohibidos:
            continue
        if modulo not in modulos:
            modulos[modulo] = {'TABLA': {}}
        if tabla not in modulos[modulo]['TABLA']:
            modulos[modulo]['TABLA'][tabla] = []
        permiso = {
            'CODIGO': row.get('CODIGO'),
            'DESCRIPCION': str(row.get('DESCRIPCION') or '').strip(),
            'TIPO': (str(row.get('TIPO') or '').strip() or 'VACIO')
        }
        modulos[modulo]['TABLA'][tabla].append(permiso)
    return modulos


def _fetch_user_permissions(cursor, username):
    cursor.execute("""
        SELECT DU.CODIGO, O.DESCRIPCION, O.MODULO, O.TABLA, O.TIPO
        FROM DEUSUARIOS DU
        INNER JOIN OPERACION O ON O.CODIGO = DU.CODIGO
        INNER JOIN USUARIOS U ON U.USUID = DU.USUID
        WHERE U.NOMBRE = ?
        ORDER BY O.MODULO, O.TABLA, O.DESCRIPCION
    """, (username,))
    rows = _rows_to_dicts(cursor, cursor.fetchall())
    return _build_modulos_payload(rows)



def _attach_api_key(request):
    # Intentar obtener API Key de diferentes headers
    api_key = request.META.get('HTTP_API_KEY')
    if not api_key:
        # Intentar desde Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Api-Key '):
            api_key = auth_header.replace('Api-Key ', '')
        elif auth_header.startswith('Bearer '):
            # Verificar que sea una API Key (formato sk_...) y no un JWT (formato eyJ...)
            bearer_token = auth_header.replace('Bearer ', '').strip()
            # Las API Keys empiezan con 'sk_', los JWT empiezan con 'eyJ'
            if bearer_token.startswith('sk_'):
                api_key = bearer_token
            # Si es JWT (eyJ...), ignorarlo - no es una API Key
    
    # Debug: mostrar todos los headers relacionados
    if not api_key:
        print(f"🔍 [API_KEY] No se encontró API Key en headers estándar")
        print(f"🔍 [API_KEY] HTTP_API_KEY: {request.META.get('HTTP_API_KEY')}")
        print(f"🔍 [API_KEY] HTTP_AUTHORIZATION: {request.META.get('HTTP_AUTHORIZATION')}")
        print(f"🔍 [API_KEY] Headers disponibles (HTTP_*):")
        for key in sorted(request.META.keys()):
            if key.startswith('HTTP_'):
                print(f"   {key}: {request.META[key][:50] if len(str(request.META[key])) > 50 else request.META[key]}")
    
    if not api_key:
        return False
    
    try:
        from apps.sistema_analitico.models import APIKeyCliente
        key = APIKeyCliente.objects.get(api_key__iexact=api_key.strip(), activa=True)
        
        if key.esta_expirada():
            print(f"❌ [API_KEY] API Key expirada: {key.fecha_caducidad}")
            return False
        
        # Si permite_scraping_total está activo, no validar empresas
        if key.permite_scraping_total:
            print(f"✅ [API_KEY] API Key permite_scraping_total=True, omitiendo validación de empresas")
            key.incrementar_contador()
            request.cliente_api = key
            request.empresas_autorizadas = []  # Lista vacía = sin restricciones
            request.scraping_sin_restricciones = True
            return True
        
        # Validación normal: verificar empresas asociadas
        empresas = key.empresas_asociadas.all()
        if not empresas.exists():
            key.actualizar_empresas_asociadas()
            empresas = key.empresas_asociadas.all()
        
        key.incrementar_contador()
        request.cliente_api = key
        request.empresas_autorizadas = empresas
        request.scraping_sin_restricciones = False
        print(f"✅ [API_KEY] API Key autenticada: ID={key.id}, NIT={key.nit}, Empresas={empresas.count()}")
        return True
    except APIKeyCliente.DoesNotExist:
        print(f"❌ [API_KEY] API Key no encontrada en BD: {api_key[:20]}...")
        return False
    except Exception as e:
        print(f"❌ [API_KEY] Error autenticando API Key: {e}")
        import traceback
        traceback.print_exc()
        return False


def _empresa_queryset_for_request(request):
    qs = EmpresaServidor.objects.select_related('servidor')
    if hasattr(request, 'cliente_api') and request.cliente_api:
        # Con API Key: usar empresas_asociadas directamente (ya están filtradas por NIT normalizado)
        empresas_ids = request.empresas_autorizadas.values_list('id', flat=True)
        qs = qs.filter(id__in=empresas_ids)
    else:
        user = getattr(request, 'user', None)
        if not user or user.is_anonymous:
            raise serializers.ValidationError('Autenticacion requerida o API key valida.')
        if not user.is_superuser:
            qs = qs.filter(
                usuarios_permitidos__usuario=user,
                usuarios_permitidos__puede_ver=True,
            )
    return qs


def _get_empresa_for_request(request, data):
    empresa_id = data.get('empresa_servidor_id')
    nit = data.get('nit')
    anio = data.get('anio_fiscal')
    qs = _empresa_queryset_for_request(request)
    
    try:
        if empresa_id:
            # Buscar por ID (ya está filtrado por empresas_asociadas si hay API Key, o por permisos si es JWT)
            empresa = qs.get(id=empresa_id)
            return empresa
        if nit:
            # Buscar por NIT: normalizar y comparar
            nit_normalizado = _normalize_nit(nit)
            
            # Buscar directamente por nit_normalizado (siempre normalizado ahora)
            try:
                empresa = qs.get(nit_normalizado=nit_normalizado)
                if anio and empresa.anio_fiscal != anio:
                    raise EmpresaServidor.DoesNotExist()
                return empresa
            except EmpresaServidor.DoesNotExist:
                raise EmpresaServidor.DoesNotExist()
    except EmpresaServidor.DoesNotExist:
        raise serializers.ValidationError('Empresa no encontrada o sin permisos.')
    raise serializers.ValidationError('Debes indicar empresa_servidor_id o nit.')


class JWTOrAPIKeyAuthentication(BaseAuthentication):
    """
    Autenticación que permite JWT o API Key.
    Si el JWT está expirado, no lanza excepción, permite que la API Key se procese.
    """
    def authenticate(self, request):
        # Intentar autenticar con JWT primero
        jwt_auth = JWTAuthentication()
        try:
            user, token = jwt_auth.authenticate(request)
            if user and token:
                return (user, token)
        except (InvalidToken, TokenError):
            # Token inválido o expirado, no lanzar excepción
            # Permitir que se procese la API Key
            pass
        except Exception:
            # Cualquier otro error, también ignorar
            pass
        
        # Si JWT no funcionó, retornar None (sin autenticar)
        # La API Key se procesará en APIKeyAwareViewSet.initial()
        return None


class APIKeyAwareViewSet:
    def initial(self, request, *args, **kwargs):
        _attach_api_key(request)
        return super().initial(request, *args, **kwargs)


class ServidorViewSet(viewsets.ModelViewSet):
    queryset = Servidor.objects.all()
    serializer_class = ServidorSerializer

class EmpresaServidorViewSet(viewsets.ModelViewSet):
    queryset = EmpresaServidor.objects.all()
    serializer_class = EmpresaServidorSerializer
    
    def get_queryset(self):
        queryset = EmpresaServidor.objects.select_related('servidor').all()
        # Filtrar por servidor si se proporciona el parámetro
        servidor_id = self.request.query_params.get('servidor', None)
        if servidor_id:
            queryset = queryset.filter(servidor_id=servidor_id)
        return queryset
    
    @action(detail=True, methods=['patch'])
    def actualizar_campos(self, request, pk=None):
        """
        Actualiza campos específicos de una empresa: NIT, razón social, representante legal, año fiscal.
        """
        try:
            empresa = self.get_object()
            data = request.data
            
            # Campos permitidos para actualizar
            campos_permitidos = ['nit', 'nombre', 'anio_fiscal']
            campos_actualizados = []
            
            # Actualizar NIT (normaliza automáticamente en save())
            if 'nit' in data:
                empresa.nit = data['nit']
                campos_actualizados.append('nit')
            
            # Actualizar nombre (razón social)
            if 'nombre' in data:
                empresa.nombre = data['nombre']
                campos_actualizados.append('nombre')
            
            # Actualizar año fiscal
            if 'anio_fiscal' in data:
                empresa.anio_fiscal = data['anio_fiscal']
                campos_actualizados.append('anio_fiscal')
            
            # Actualizar representante legal (si existe en RUT)
            if 'representante_legal' in data:
                # Buscar RUT asociado
                from .models import RUT
                rut = RUT.objects.filter(nit_normalizado=empresa.nit_normalizado).first()
                if rut:
                    representante = data['representante_legal']
                    # Actualizar campos de representante legal
                    if 'primer_nombre' in representante:
                        rut.representante_legal_primer_nombre = representante.get('primer_nombre', '')[:100]
                    if 'primer_apellido' in representante:
                        rut.representante_legal_primer_apellido = representante.get('primer_apellido', '')[:100]
                    if 'otros_nombres' in representante:
                        rut.representante_legal_otros_nombres = representante.get('otros_nombres', '')[:100]
                    rut.save()
                    campos_actualizados.append('representante_legal')
            
            if not campos_actualizados:
                return Response(
                    {'error': 'No se proporcionaron campos válidos para actualizar'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            empresa.save()
            
            serializer = self.get_serializer(empresa)
            return Response({
                'mensaje': f'Campos actualizados: {", ".join(campos_actualizados)}',
                'empresa': serializer.data
            }, status=status.HTTP_200_OK)
            
        except EmpresaServidor.DoesNotExist:
            return Response(
                {'error': 'Empresa no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error actualizando empresa: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def ultimo_backup(self, request, pk=None):
        """
        Obtiene el último backup de una empresa.
        """
        try:
            empresa = self.get_object()
            from .models import BackupS3
            
            ultimo_backup = BackupS3.objects.filter(
                empresa_servidor=empresa,
                estado='completado'
            ).order_by('-fecha_backup').first()
            
            if not ultimo_backup:
                return Response(
                    {'mensaje': 'No hay backups para esta empresa'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            from .serializers import BackupS3Serializer
            serializer = BackupS3Serializer(ultimo_backup)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except EmpresaServidor.DoesNotExist:
            return Response(
                {'error': 'Empresa no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error obteniendo último backup: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def ultimos_backups_masivo(self, request):
        """
        Obtiene los últimos backups de múltiples empresas en una sola petición.
        Optimizado para evitar N+1 queries.
        
        Query params:
        - empresa_ids: Lista de IDs de empresas separados por comas (ej: "1,2,3")
        - servidor_id: ID del servidor (alternativa a empresa_ids)
        """
        try:
            from .models import BackupS3
            from .serializers import BackupS3Serializer
            from django.db.models import Max
            
            empresa_ids_param = request.query_params.get('empresa_ids')
            servidor_id = request.query_params.get('servidor_id')
            
            # Obtener lista de empresas
            if empresa_ids_param:
                empresa_ids = [int(id.strip()) for id in empresa_ids_param.split(',') if id.strip().isdigit()]
                empresas = EmpresaServidor.objects.filter(id__in=empresa_ids)
            elif servidor_id:
                empresas = EmpresaServidor.objects.filter(servidor_id=servidor_id)
            else:
                return Response(
                    {'error': 'Se requiere empresa_ids o servidor_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not empresas.exists():
                return Response(
                    {'backups': {}},
                    status=status.HTTP_200_OK
                )
            
            empresa_ids_list = list(empresas.values_list('id', flat=True))
            
            # Obtener el último backup de cada empresa en una sola query optimizada
            # Usar subquery para obtener el ID del último backup por empresa
            ultimos_backups_ids = BackupS3.objects.filter(
                empresa_servidor_id__in=empresa_ids_list,
                estado='completado'
            ).values('empresa_servidor_id').annotate(
                ultimo_id=Max('id')
            ).values_list('ultimo_id', flat=True)
            
            # Obtener los backups completos
            ultimos_backups = BackupS3.objects.filter(id__in=ultimos_backups_ids)
            
            # Serializar y organizar por empresa_id
            serializer = BackupS3Serializer(ultimos_backups, many=True)
            backups_dict = {
                backup['empresa_servidor']: backup
                for backup in serializer.data
            }
            
            return Response(
                {'backups': backups_dict},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo últimos backups masivo: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
class UsuarioEmpresaViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar permisos de usuarios a empresas.
    Permite crear, listar, editar y eliminar relaciones usuario-empresa.
    """
    queryset = UsuarioEmpresa.objects.all().select_related('usuario', 'empresa_servidor', 'empresa_servidor__servidor')
    serializer_class = UsuarioEmpresaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo superusuarios pueden ver todos los permisos
        if not self.request.user.is_superuser:
            return UsuarioEmpresa.objects.none()
        return UsuarioEmpresa.objects.all().select_related('usuario', 'empresa_servidor', 'empresa_servidor__servidor')
    
    def create(self, request, *args, **kwargs):
        """Crear nuevo permiso usuario-empresa"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden crear permisos'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Actualizar permiso"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden editar permisos'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminar permiso"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden eliminar permisos'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

class RUTViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar RUTs de empresas.
    Identifica por NIT normalizado (sin puntos ni guiones).
    Un RUT aplica para todas las empresas con el mismo NIT.
    """
    from .serializers import RUTSerializer, SubirRUTSerializer
    
    # Usar la función de normalización existente
    def normalize_nit(self, nit: str) -> str:
        """Normaliza NIT usando la función global"""
        return _normalize_nit(nit)
    
    def extract_rut_data_from_pdf(self, pdf_file):
        """Extrae datos del PDF usando el servicio"""
        from .services.rut_extractor import extract_rut_data_from_pdf
        return extract_rut_data_from_pdf(pdf_file)
    
    queryset = RUT.objects.all().prefetch_related('establecimientos')
    serializer_class = RUTSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'nit_normalizado'
    
    def get_queryset(self):
        # Solo superusuarios pueden ver todos los RUTs
        if not self.request.user.is_superuser:
            return RUT.objects.none()
        
        queryset = RUT.objects.all().prefetch_related('establecimientos')
        
        # Soporte para búsqueda
        search = self.request.query_params.get('search', '').strip()
        if search:
            from django.db.models import Q
            # Buscar por NIT normalizado o razón social
            queryset = queryset.filter(
                Q(nit_normalizado__icontains=search) |
                Q(nit__icontains=search) |
                Q(razon_social__icontains=search) |
                Q(nombre_comercial__icontains=search)
            )
        
        # Límite opcional
        limit = self.request.query_params.get('limit')
        if limit:
            try:
                limit_int = int(limit)
                queryset = queryset[:limit_int]
            except ValueError:
                pass
        
        return queryset.order_by('-fecha_actualizacion')
    
    @action(detail=False, methods=['post'], url_path='subir-pdf', parser_classes=[MultiPartParser, FormParser, JSONParser])
    def subir_pdf(self, request):
        """
        Sube un PDF de RUT o un ZIP con múltiples PDFs y extrae la información automáticamente.
        Detecta el NIT del PDF y lo asocia a todas las empresas con ese NIT.
        Si ya existe un RUT para ese NIT, lo actualiza.
        
        Si se sube un ZIP:
        - Procesa todos los PDFs del ZIP
        - Omite RUTs que no tienen empresas asociadas
        - Retorna un reporte TXT con los RUTs fallidos y la razón
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden subir RUTs'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SubirRUTSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar si es ZIP o PDF individual
        archivo_zip = serializer.validated_data.get('archivo_zip')
        if archivo_zip:
            # Procesar ZIP
            return self._procesar_zip_ruts(archivo_zip)
        
        # Procesar PDF individual
        archivo_pdf = serializer.validated_data['archivo_pdf']
        nit_proporcionado = serializer.validated_data.get('nit', '').strip()
        
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Extraer datos del PDF
            pdf_data = self.extract_rut_data_from_pdf(archivo_pdf)
            
            # 🔍 LOG DETALLADO: Mostrar qué se extrajo del PDF
            tipo_contribuyente = pdf_data.get('tipo_contribuyente', 'NO_DETECTADO')
            razon_social_raw = pdf_data.get('razon_social', '').strip()
            
            logger.info(f"[RUT PDF DIRECTO] 🔍 EXTRACCIÓN DEL PDF:")
            logger.info(f"  • Tipo Contribuyente: {tipo_contribuyente}")
            logger.info(f"  • Razón Social (campo 35): '{razon_social_raw}'")
            
            if tipo_contribuyente == 'persona_natural':
                pn_apellido1 = pdf_data.get('persona_natural_primer_apellido', '').strip()
                pn_apellido2 = pdf_data.get('persona_natural_segundo_apellido', '').strip()
                pn_nombre = pdf_data.get('persona_natural_primer_nombre', '').strip()
                pn_otros = pdf_data.get('persona_natural_otros_nombres', '').strip()
                logger.info(f"  • Campo 31 (Primer Apellido): '{pn_apellido1}'")
                logger.info(f"  • Campo 32 (Segundo Apellido): '{pn_apellido2}'")
                logger.info(f"  • Campo 33 (Primer Nombre): '{pn_nombre}'")
                logger.info(f"  • Campo 34 (Otros Nombres): '{pn_otros}'")
            
            # Usar NIT proporcionado o el detectado del PDF
            nit_normalizado = self.normalize_nit(nit_proporcionado) if nit_proporcionado else pdf_data.get('nit_normalizado')
            
            if not nit_normalizado:
                return Response(
                    {'error': 'No se pudo detectar el NIT del PDF. Por favor, proporciona el NIT manualmente.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # ✅ CORRECCIÓN: Usar obtener_razon_social_mejorada para construir razón social correctamente
            from .services.rut_batch_processor import obtener_razon_social_mejorada
            razon_social_mejorada = obtener_razon_social_mejorada(pdf_data)
            logger.info(f"[RUT PDF DIRECTO] ✅ Razón Social Final: '{razon_social_mejorada}'")
            
            # Buscar o crear RUT
            rut, created = RUT.objects.get_or_create(
                nit_normalizado=nit_normalizado,
                defaults={
                    'nit': pdf_data.get('nit', nit_normalizado),
                    'dv': pdf_data.get('dv', ''),
                    'razon_social': razon_social_mejorada,  # ✅ Usar razón social mejorada
                }
            )
            
            # Actualizar campos desde PDF (incluyendo valores vacíos para limpiar campos)
            for key, value in pdf_data.items():
                if key != '_texto_completo' and key != '_codigos_ciiu_encontrados' and hasattr(rut, key):
                    # Si el valor existe, actualizarlo; si es None o vacío, también actualizar para limpiar
                    if value is not None:
                        setattr(rut, key, value)
            
            # ✅ IMPORTANTE: Actualizar razón social con la versión mejorada
            rut.razon_social = razon_social_mejorada
            
            # Reemplazar archivo PDF si existe uno anterior
            if rut.archivo_pdf:
                # Eliminar archivo anterior
                rut.archivo_pdf.delete(save=False)
            
            # Guardar nuevo archivo
            rut.archivo_pdf = archivo_pdf
            rut.save()
            
            # Procesar códigos CIIU encontrados en el PDF
            codigos_ciiu = pdf_data.get('_codigos_ciiu_encontrados', [])
            
            # Si no están en _codigos_ciiu_encontrados, buscarlos en los campos individuales
            if not codigos_ciiu:
                if pdf_data.get('actividad_principal_ciiu'):
                    codigos_ciiu.append(pdf_data['actividad_principal_ciiu'])
                if pdf_data.get('actividad_secundaria_ciiu'):
                    codigos_ciiu.append(pdf_data['actividad_secundaria_ciiu'])
                if pdf_data.get('otras_actividades_ciiu'):
                    codigos_ciiu.append(pdf_data['otras_actividades_ciiu'])
            
            # Filtrar códigos válidos y únicos
            codigos_ciiu = list(set([c for c in codigos_ciiu if c and c.strip()]))
            
            if codigos_ciiu:
                # Procesar códigos CIIU de forma asíncrona
                from .tasks import procesar_codigos_ciiu_masivo_task
                task = procesar_codigos_ciiu_masivo_task.delay(codigos_ciiu)
                logger.info(f"Tarea Celery iniciada para procesar {len(codigos_ciiu)} códigos CIIU: {task.id}")
            
            # Procesar códigos de responsabilidades
            codigos_responsabilidades = pdf_data.get('responsabilidades_codigos', [])
            descripciones_responsabilidades = pdf_data.get('responsabilidades_descripcion', [])
            
            if codigos_responsabilidades:
                from .models import ResponsabilidadTributaria
                from django.db import IntegrityError
                
                # Mapeo de códigos a descripciones (basado en el PDF real)
                descripciones_map = {
                    '7': 'Retención en la fuente a título de renta',
                    '9': 'Retención en la fuente en el impuesto',
                    '14': 'Informante de exogena',
                    '42': 'Obligado a llevar contabilidad',
                    '47': 'Régimen Simple de Tributación - SIM',
                    '48': 'Impuesto sobre las ventas - IVA',
                    '52': 'Facturador electrónico',
                    '55': 'Informante de Beneficiarios Finales',
                }
                
                # Si no vienen descripciones del extractor, generarlas desde el mapa
                if not descripciones_responsabilidades:
                    descripciones_responsabilidades = [
                        descripciones_map.get(str(codigo), f'Responsabilidad tributaria código {codigo}')
                        for codigo in codigos_responsabilidades
                    ]
                
                # Guardar/actualizar responsabilidades en la BD
                for codigo in codigos_responsabilidades:
                    codigo_str = str(codigo).strip()
                    if codigo_str:
                        descripcion = descripciones_map.get(
                            codigo_str,
                            f'Responsabilidad tributaria código {codigo_str}'
                        )
                        try:
                            ResponsabilidadTributaria.objects.get_or_create(
                                codigo=codigo_str,
                                defaults={'descripcion': descripcion}
                            )
                        except IntegrityError:
                            # Ya existe, actualizar descripción si es necesario
                            try:
                                resp = ResponsabilidadTributaria.objects.get(codigo=codigo_str)
                                if resp.descripcion != descripcion:
                                    resp.descripcion = descripcion
                                    resp.save()
                            except ResponsabilidadTributaria.DoesNotExist:
                                pass
            
            # Buscar empresas asociadas
            empresas = EmpresaServidor.objects.filter(nit_normalizado=nit_normalizado)
            empresas_info = [
                {
                    'id': emp.id,
                    'nombre': emp.nombre,
                    'anio_fiscal': emp.anio_fiscal,
                    'servidor': emp.servidor.nombre if emp.servidor else None
                }
                for emp in empresas
            ]
            
            response_serializer = RUTSerializer(rut, context={'request': request})
            
            return Response({
                'rut': response_serializer.data,
                'empresas_asociadas': empresas_info,
                'mensaje': 'RUT actualizado exitosamente' if not created else 'RUT creado exitosamente',
                'empresas_encontradas': len(empresas_info)
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error procesando PDF de RUT: {e}", exc_info=True)
            return Response(
                {'error': f'Error al procesar el PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _procesar_zip_ruts(self, zip_file):
        """Procesa un ZIP con múltiples PDFs de RUT. Si tiene más de 50 archivos, usa Celery."""
        import os
        import tempfile
        from .services.rut_batch_processor import procesar_zip_ruts
        from .tasks import procesar_zip_ruts_task
        
        try:
            # Contar archivos PDF en el ZIP para decidir si usar Celery
            import zipfile
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                pdf_files = [f for f in zip_ref.namelist() if f.lower().endswith('.pdf') and not f.endswith('/')]
                total_pdfs = len(pdf_files)
            
            # Si hay más de 50 archivos, usar Celery para procesamiento asíncrono
            if total_pdfs > 50:
                # Guardar archivo temporalmente
                temp_dir = tempfile.gettempdir()
                temp_file_path = os.path.join(temp_dir, f'rut_zip_{self.request.user.id}_{int(timezone.now().timestamp())}.zip')
                
                # Leer contenido del archivo
                if hasattr(zip_file, 'read'):
                    zip_file.seek(0)
                    with open(temp_file_path, 'wb') as f:
                        f.write(zip_file.read())
                else:
                    # Si es un archivo subido, guardarlo directamente
                    with open(temp_file_path, 'wb') as f:
                        for chunk in zip_file.chunks():
                            f.write(chunk)
                
                # Iniciar tarea Celery
                task = procesar_zip_ruts_task.delay(temp_file_path)
                
                return Response({
                    'mensaje': 'Procesamiento de ZIP iniciado (procesamiento asíncrono)',
                    'task_id': task.id,
                    'total': total_pdfs,
                    'procesamiento_asincrono': True,
                    'status': 'PROCESSING'
                }, status=status.HTTP_202_ACCEPTED)
            
            # Si son menos de 50, procesar directamente
            resultados = procesar_zip_ruts(zip_file)
            
            return Response({
                'mensaje': 'Procesamiento de ZIP completado',
                'total': resultados['total'],
                'exitosos': len(resultados['exitosos']),
                'fallidos': len(resultados['fallidos']),
                'reporte_txt': resultados['reporte_txt'],
                'detalles_exitosos': resultados['exitosos'],
                'detalles_fallidos': resultados['fallidos'],
                'procesamiento_asincrono': False
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error procesando ZIP de RUTs: {e}", exc_info=True)
            return Response(
                {'error': f'Error al procesar el ZIP: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='empresas')
    def empresas_asociadas(self, request, nit_normalizado=None):
        """Obtiene todas las empresas asociadas a este RUT"""
        try:
            rut = RUT.objects.get(nit_normalizado=nit_normalizado)
            empresas = EmpresaServidor.objects.filter(nit_normalizado=nit_normalizado).select_related('servidor')
            
            empresas_data = [
                {
                    'id': emp.id,
                    'nombre': emp.nombre,
                    'nit': emp.nit,
                    'anio_fiscal': emp.anio_fiscal,
                    'codigo': emp.codigo,
                    'servidor': emp.servidor.nombre if emp.servidor else None,
                    'estado': emp.estado
                }
                for emp in empresas
            ]
            
            return Response({
                'rut': RUTSerializer(rut, context={'request': request}).data,
                'empresas': empresas_data,
                'total': len(empresas_data)
            })
        except RUT.DoesNotExist:
            return Response(
                {'error': 'RUT no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def create(self, request, *args, **kwargs):
        """Crear RUT manualmente"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden crear RUTs'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Normalizar NIT antes de crear
        if 'nit' in request.data:
            nit = request.data['nit']
            nit_normalizado = self.normalize_nit(nit)
            request.data['nit_normalizado'] = nit_normalizado
        
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Actualizar RUT"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden editar RUTs'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminar RUT"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden eliminar RUTs'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class CalendarioTributarioViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar el calendario tributario.
    Permite subir un Excel con todas las vigencias tributarias.
    """
    from .serializers import (
        TipoTerceroSerializer, TipoRegimenSerializer, 
        ImpuestoSerializer, VigenciaTributariaSerializer,
        SubirCalendarioTributarioSerializer
    )
    from .models import TipoTercero, TipoRegimen, Impuesto, VigenciaTributaria
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Permite ver el calendario a:
        - Superusuarios: pueden ver todo
        - Usuarios con API Key: pueden ver eventos de sus empresas (filtrado en acciones específicas)
        """
        # Para list/retrieve, solo superusuarios
        if self.action in ['list', 'retrieve']:
            if not self.request.user.is_superuser:
                return VigenciaTributaria.objects.none()
        
        return VigenciaTributaria.objects.select_related(
            'impuesto', 'tipo_tercero', 'tipo_regimen'
        ).order_by('impuesto__codigo', 'fecha_limite')
    
    def get_serializer_class(self):
        """Retornar serializer según la acción"""
        if self.action == 'subir_excel':
            return SubirCalendarioTributarioSerializer
        return VigenciaTributariaSerializer
    
    @action(detail=False, methods=['post'], url_path='subir-excel')
    def subir_excel(self, request):
        """
        Sube un Excel con el calendario tributario completo.
        Formato esperado:
        - tax_code: Código del impuesto (RGC, RPJ, IVB, etc.)
        - expirations_digits: Últimos dígitos del NIT ("1", "2", "01", "99", "" para todos)
        - third_type_code: Tipo de tercero ("PN", "PJ", o "" para todos)
        - regiment_type_code: Régimen ("GC", "SIM", "ORD", o "" para todos)
        - date: Fecha límite (DD/MM/YYYY o YYYY-MM-DD)
        - description: Descripción de la obligación
        
        Retorna información de empresas asociadas por NIT.
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden subir el calendario tributario'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SubirCalendarioTributarioSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        archivo_excel = serializer.validated_data['archivo_excel']
        
        try:
            from .services.calendario_importer import importar_calendario_desde_excel
            
            # Importar usando el servicio
            resultados = importar_calendario_desde_excel(archivo_excel)
            
            if not resultados['success']:
                return Response(
                    {
                        'error': 'Error al procesar el Excel',
                        'errores': resultados['errores']
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                'mensaje': 'Calendario tributario procesado exitosamente',
                'total': resultados['total'],
                'creados': resultados['creados'],
                'actualizados': resultados['actualizados'],
                'total_procesadas': resultados['creados'] + resultados['actualizados'],
                'errores': resultados['errores'][:50],  # Limitar a 50 errores
                'total_errores': len(resultados['errores']),
                'empresas_asociadas': resultados['empresas_asociadas'],
                'total_empresas_asociadas': len(resultados['empresas_asociadas'])
            }, status=status.HTTP_200_OK)
            
        except ImportError:
            return Response(
                {'error': 'pandas no está instalado. Instala con: pip install pandas openpyxl'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Error procesando Excel del calendario tributario: {e}", exc_info=True)
            return Response(
                {'error': f'Error al procesar el Excel: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='eventos')
    def obtener_eventos(self, request):
        """
        Obtiene eventos del calendario tributario para un NIT o empresa.
        Usa el RUT para determinar si es Persona Natural o Jurídica.
        
        AUTENTICACIÓN:
        - Requiere API Key válida (puede consultar eventos de sus empresas asociadas)
        - O ser superusuario (puede consultar cualquier empresa)
        
        Parámetros:
        - nit: NIT de la empresa (requerido si no se proporciona empresa_id)
        - empresa_id: ID de la empresa (requerido si no se proporciona nit)
        - fecha_desde: Fecha desde (opcional, formato YYYY-MM-DD)
        - fecha_hasta: Fecha hasta (opcional, formato YYYY-MM-DD)
        - tipo_regimen: Código del régimen (opcional)
        """
        from .services.calendario_tributario_service import (
            obtener_eventos_calendario_tributario,
            obtener_eventos_para_empresa
        )
        from datetime import datetime
        
        # Verificar autenticación: API Key o superusuario
        tiene_api_key = hasattr(request, 'cliente_api') and request.cliente_api
        es_superusuario = request.user.is_authenticated and request.user.is_superuser
        
        if not tiene_api_key and not es_superusuario:
            return Response(
                {
                    'error': 'Se requiere API Key válida o autenticación de superusuario para consultar eventos del calendario tributario',
                    'info': 'Si tienes una API Key, envíala en el header: Api-Key: <tu_api_key>'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        nit = request.query_params.get('nit')
        empresa_id = request.query_params.get('empresa_id')
        fecha_desde_str = request.query_params.get('fecha_desde')
        fecha_hasta_str = request.query_params.get('fecha_hasta')
        tipo_regimen = request.query_params.get('tipo_regimen')
        
        # Soporte para year y month (compatibilidad con plugin Chrome)
        # Si se proporcionan year y month, convertir a fecha_desde y fecha_hasta
        year_str = request.query_params.get('year')
        month_str = request.query_params.get('month')
        if year_str and month_str and not fecha_desde_str and not fecha_hasta_str:
            try:
                year = int(year_str)
                month = int(month_str)
                # Validar rango de mes
                if month < 1 or month > 12:
                    raise ValueError("Mes inválido")
                # Primer día del mes
                fecha_desde_str = f"{year}-{month:02d}-01"
                # Último día del mes
                _, last_day = monthrange(year, month)
                fecha_hasta_str = f"{year}-{month:02d}-{last_day:02d}"
            except (ValueError, TypeError):
                # Si hay error en la conversión, ignorar y usar fecha_desde/fecha_hasta si existen
                pass
        
        # Si tiene API Key y no especificó empresa/nit, retornar eventos de TODAS sus empresas + NITs de RUTs
        if tiene_api_key and not es_superusuario:
            empresas_autorizadas = request.empresas_autorizadas
            cliente_api = request.cliente_api
            
            # Si no especificó nit ni empresa_id, retornar eventos de:
            # 1. Empresas asociadas (EmpresaServidor)
            # 2. NITs de RUTs asociados (APIKeyNITCalendario)
            # DISTINCT para evitar duplicados
            if not nit and not empresa_id:
                todos_eventos = []
                nits_consultados = set()
                
                # 1. Eventos de empresas asociadas
                for empresa in empresas_autorizadas:
                    if empresa.nit_normalizado not in nits_consultados:
                        eventos_empresa = obtener_eventos_para_empresa(
                            empresa.id,
                            fecha_desde=fecha_desde if fecha_desde else None,
                            fecha_hasta=fecha_hasta if fecha_hasta else None
                        )
                        todos_eventos.extend(eventos_empresa)
                        nits_consultados.add(empresa.nit_normalizado)
                
                # 2. Eventos de NITs de RUTs asociados (solo si no están ya en empresas)
                from .models import APIKeyNITCalendario
                nits_ruts = APIKeyNITCalendario.objects.filter(
                    api_key=cliente_api,
                    activo=True
                ).exclude(
                    nit_normalizado__in=nits_consultados
                ).values_list('nit_normalizado', flat=True).distinct()
                
                for nit_rut in nits_ruts:
                    eventos_rut = obtener_eventos_calendario_tributario(
                        nit=nit_rut,
                        tipo_regimen=tipo_regimen,
                        fecha_desde=fecha_desde,
                        fecha_hasta=fecha_hasta
                    )
                    todos_eventos.extend(eventos_rut)
                    nits_consultados.add(nit_rut)
                
                return Response({
                    'eventos': todos_eventos,
                    'total': len(todos_eventos),
                    'nits_consultados': len(nits_consultados),
                    'empresas_consultadas': empresas_autorizadas.count(),
                    'nits_ruts_consultados': len(nits_ruts),
                    'filtros': {
                        'nit': None,
                        'empresa_id': None,
                        'fecha_desde': fecha_desde_str,
                        'fecha_hasta': fecha_hasta_str,
                        'tipo_regimen': tipo_regimen,
                        'modo': 'todas_las_empresas_y_ruts'
                    }
                }, status=status.HTTP_200_OK)
            
            # Si especificó empresa_id, validar que esté autorizada
            if empresa_id:
                try:
                    empresa_id_int = int(empresa_id)
                    if not empresas_autorizadas.filter(id=empresa_id_int).exists():
                        return Response(
                            {'error': 'No tienes permiso para consultar eventos de esta empresa'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                except ValueError:
                    return Response(
                        {'error': 'empresa_id debe ser un número'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            # Si especificó nit, validar que esté autorizada (empresa o RUT asociado)
            elif nit:
                nit_normalizado = ''.join(c for c in str(nit) if c.isdigit())
                cliente_api = request.cliente_api
                
                # Verificar si está en empresas asociadas
                tiene_empresa = empresas_autorizadas.filter(nit_normalizado=nit_normalizado).exists()
                
                # Verificar si está en NITs de RUTs asociados
                from .models import APIKeyNITCalendario
                tiene_rut = APIKeyNITCalendario.objects.filter(
                    api_key=cliente_api,
                    nit_normalizado=nit_normalizado,
                    activo=True
                ).exists()
                
                if not tiene_empresa and not tiene_rut:
                    return Response(
                        {'error': 'No tienes permiso para consultar eventos de este NIT. Debe estar asociado como empresa o RUT.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
        # Si es superusuario sin API Key, puede consultar cualquier empresa pero debe especificarla
        if es_superusuario and not tiene_api_key:
            if not nit and not empresa_id:
                return Response(
                    {'error': 'Debe proporcionar nit o empresa_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Parsear fechas
        fecha_desde = None
        fecha_hasta = None
        if fecha_desde_str:
            try:
                fecha_desde = datetime.strptime(fecha_desde_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Formato de fecha_desde inválido. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        if fecha_hasta_str:
            try:
                fecha_hasta = datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Formato de fecha_hasta inválido. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Obtener eventos
        if empresa_id:
            try:
                eventos = obtener_eventos_para_empresa(
                    int(empresa_id),
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta
                )
            except ValueError:
                return Response(
                    {'error': 'empresa_id debe ser un número'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif nit:
            eventos = obtener_eventos_calendario_tributario(
                nit=nit,
                tipo_regimen=tipo_regimen,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta
            )
        else:
            return Response(
                {'error': 'Debe proporcionar nit o empresa_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'eventos': eventos,
            'total': len(eventos),
            'filtros': {
                'nit': nit,
                'empresa_id': empresa_id,
                'fecha_desde': fecha_desde_str,
                'fecha_hasta': fecha_hasta_str,
                'tipo_regimen': tipo_regimen
            }
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='eventos-multiples')
    def obtener_eventos_multiples(self, request):
        """
        Obtiene eventos del calendario tributario para múltiples NITs.
        
        AUTENTICACIÓN:
        - Requiere API Key válida (puede consultar eventos de sus empresas asociadas)
        - O ser superusuario (puede consultar cualquier empresa)
        
        Body (JSON):
        {
            "nits": ["900869750", "132791157", "800123456"],  // Lista de NITs (sin dígito de verificación)
            "fecha_desde": "2024-01-01",  // Opcional (formato YYYY-MM-DD)
            "fecha_hasta": "2024-12-31",  // Opcional (formato YYYY-MM-DD)
            "tipo_regimen": "GC"  // Opcional (código del régimen)
        }
        
        Retorna:
        {
            "resultados": {
                "900869750": {
                    "nit_original": "900869750",
                    "nit_normalizado": "900869750",
                    "total_eventos": 5,
                    "eventos": [...]
                },
                ...
            },
            "total_nits": 3,
            "total_eventos": 15
        }
        """
        from .services.calendario_tributario_service import obtener_eventos_para_lista_nits
        from datetime import datetime
        
        # Verificar autenticación: API Key o superusuario
        tiene_api_key = hasattr(request, 'cliente_api') and request.cliente_api
        es_superusuario = request.user.is_authenticated and request.user.is_superuser
        
        if not tiene_api_key and not es_superusuario:
            return Response(
                {
                    'error': 'Se requiere API Key válida o autenticación de superusuario para consultar eventos del calendario tributario',
                    'info': 'Si tienes una API Key, envíala en el header: Api-Key: <tu_api_key>'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        nits = request.data.get('nits', [])
        
        # Si tiene API Key y no especificó NITs, usar TODAS sus empresas + NITs de RUTs automáticamente
        if tiene_api_key and not es_superusuario:
            empresas_autorizadas = request.empresas_autorizadas
            cliente_api = request.cliente_api
            
            # Si no especificó nits, usar todas las empresas autorizadas + NITs de RUTs
            if not nits or len(nits) == 0:
                # NITs de empresas asociadas
                nits_empresas = set(empresas_autorizadas.values_list('nit_normalizado', flat=True))
                
                # NITs de RUTs asociados
                from .models import APIKeyNITCalendario
                nits_ruts = set(APIKeyNITCalendario.objects.filter(
                    api_key=cliente_api,
                    activo=True
                ).values_list('nit_normalizado', flat=True))
                
                # Combinar y obtener únicos
                nits = list(nits_empresas | nits_ruts)
                
                if len(nits) == 0:
                    return Response(
                        {'error': 'Tu API Key no tiene empresas ni NITs de RUTs asociados'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Si especificó NITs, filtrar solo los autorizados (empresas o RUTs)
                if not isinstance(nits, list):
                    return Response(
                        {'error': 'El campo "nits" debe ser una lista'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # NITs autorizados: empresas + RUTs
                nits_empresas = set(empresas_autorizadas.values_list('nit_normalizado', flat=True))
                from .models import APIKeyNITCalendario
                nits_ruts = set(APIKeyNITCalendario.objects.filter(
                    api_key=cliente_api,
                    activo=True
                ).values_list('nit_normalizado', flat=True))
                nits_autorizados = nits_empresas | nits_ruts
                
                # Normalizar y filtrar NITs proporcionados
                nits_filtrados = []
                for nit in nits:
                    nit_normalizado = ''.join(c for c in str(nit) if c.isdigit())
                    if nit_normalizado in nits_autorizados:
                        nits_filtrados.append(nit_normalizado)
                
                # Eliminar duplicados
                nits_filtrados = list(set(nits_filtrados))
                
                if len(nits_filtrados) == 0:
                    return Response(
                        {'error': 'Ninguno de los NITs proporcionados está asociado a tu API Key (como empresa o RUT)'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                nits = nits_filtrados
        else:
            # Superusuario debe especificar NITs
            if not isinstance(nits, list) or len(nits) == 0:
                return Response(
                    {'error': 'Debe proporcionar una lista de NITs en el campo "nits"'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Parsear fechas
        fecha_desde = None
        fecha_hasta = None
        fecha_desde_str = request.data.get('fecha_desde')
        fecha_hasta_str = request.data.get('fecha_hasta')
        
        if fecha_desde_str:
            try:
                fecha_desde = datetime.strptime(fecha_desde_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Formato de fecha_desde inválido. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        if fecha_hasta_str:
            try:
                fecha_hasta = datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Formato de fecha_hasta inválido. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        tipo_regimen = request.data.get('tipo_regimen')
        
        # Obtener eventos para todos los NITs
        resultados = obtener_eventos_para_lista_nits(
            nits=nits,
            tipo_regimen=tipo_regimen,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
        
        # Calcular totales
        total_eventos = sum(r.get('total_eventos', 0) for r in resultados.values())
        
        return Response({
            'resultados': resultados,
            'total_nits': len(nits),
            'total_eventos': total_eventos,
            'filtros': {
                'fecha_desde': fecha_desde_str,
                'fecha_hasta': fecha_hasta_str,
                'tipo_regimen': tipo_regimen
            }
        }, status=status.HTTP_200_OK)


class EntidadViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar Entidades (homólogo de Entities en BCE)
    """
    from .serializers import EntidadSerializer
    from .models import Entidad
    
    queryset = Entidad.objects.all()
    serializer_class = EntidadSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if not self.request.user.is_superuser:
            return Entidad.objects.none()
        return Entidad.objects.all().order_by('nombre')


class ContrasenaEntidadViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar Contraseñas de Entidades (homólogo de PasswordsEntities en BCE)
    
    AUTENTICACIÓN:
    - Requiere API Key válida (retorna passwords de sus empresas asociadas automáticamente)
    - O ser superusuario autenticado (puede ver todas)
    
    Si no se especifican filtros, retorna passwords de TODAS las empresas asociadas a la API Key.
    """
    from .serializers import ContrasenaEntidadSerializer
    from .models import ContrasenaEntidad
    
    queryset = ContrasenaEntidad.objects.all()
    serializer_class = ContrasenaEntidadSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        """
        Lista contraseñas de entidades.
        
        AUTENTICACIÓN:
        - Requiere API Key válida (retorna passwords de sus empresas asociadas automáticamente)
        - O ser superusuario autenticado (puede ver todas)
        
        FILTROS OPCIONALES (query params):
        - nit: Filtrar por NIT específico (debe estar en empresas autorizadas)
        - entidad_id: Filtrar por ID de entidad
        - empresa_id: Filtrar por ID de empresa (debe estar en empresas autorizadas)
        
        Si no se especifican filtros, retorna passwords de TODAS las empresas asociadas a la API Key.
        """
        # Verificar autenticación: API Key o superusuario
        tiene_api_key = hasattr(request, 'cliente_api') and request.cliente_api
        es_superusuario = request.user.is_authenticated and request.user.is_superuser
        
        if not tiene_api_key and not es_superusuario:
            return Response(
                {
                    'error': 'Se requiere API Key válida o autenticación de superusuario para consultar passwords de entidades',
                    'info': 'Si tienes una API Key, envíala en el header: Api-Key: <tu_api_key>'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = ContrasenaEntidad.objects.select_related('entidad', 'empresa_servidor').all()
        
        # Si tiene API Key, filtrar solo empresas autorizadas
        if tiene_api_key and not es_superusuario:
            empresas_autorizadas = request.empresas_autorizadas
            nits_autorizados = set(empresas_autorizadas.values_list('nit_normalizado', flat=True))
            
            # Filtrar por NITs autorizados
            queryset = queryset.filter(nit_normalizado__in=nits_autorizados)
            
            # Filtros adicionales opcionales
            nit_filter = request.query_params.get('nit')
            if nit_filter:
                nit_normalizado = ''.join(c for c in str(nit_filter) if c.isdigit())
                if nit_normalizado not in nits_autorizados:
                    return Response(
                        {'error': 'No tienes permiso para consultar passwords de este NIT'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                queryset = queryset.filter(nit_normalizado=nit_normalizado)
            
            empresa_id = request.query_params.get('empresa_id')
            if empresa_id:
                try:
                    empresa_id_int = int(empresa_id)
                    if not empresas_autorizadas.filter(id=empresa_id_int).exists():
                        return Response(
                            {'error': 'No tienes permiso para consultar passwords de esta empresa'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    queryset = queryset.filter(empresa_servidor_id=empresa_id_int)
                except ValueError:
                    return Response(
                        {'error': 'empresa_id debe ser un número'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        else:
            # Superusuario - puede ver todas, pero puede filtrar opcionalmente
            nit_filter = request.query_params.get('nit')
            if nit_filter:
                nit_normalizado = ''.join(c for c in str(nit_filter) if c.isdigit())
                queryset = queryset.filter(nit_normalizado=nit_normalizado)
            
            empresa_id = request.query_params.get('empresa_id')
            if empresa_id:
                queryset = queryset.filter(empresa_servidor_id=empresa_id)
        
        # Filtro por entidad (aplica a ambos casos)
        entidad_id = request.query_params.get('entidad_id')
        if entidad_id:
            queryset = queryset.filter(entidad_id=entidad_id)
        
        queryset = queryset.order_by('entidad__nombre', 'usuario')
        
        # Paginación estándar de DRF
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def get_queryset(self):
        """
        Para otras acciones (retrieve, create, update, delete).
        Filtra por empresas autorizadas si tiene API Key.
        """
        queryset = ContrasenaEntidad.objects.select_related('entidad', 'empresa_servidor').all()
        
        # Si tiene API Key, filtrar solo empresas autorizadas
        tiene_api_key = hasattr(self.request, 'cliente_api') and self.request.cliente_api
        es_superusuario = self.request.user.is_authenticated and self.request.user.is_superuser
        
        if tiene_api_key and not es_superusuario:
            empresas_autorizadas = self.request.empresas_autorizadas
            nits_autorizados = set(empresas_autorizadas.values_list('nit_normalizado', flat=True))
            queryset = queryset.filter(nit_normalizado__in=nits_autorizados)
        elif not es_superusuario:
            # Sin API Key ni superusuario, no puede ver nada
            return ContrasenaEntidad.objects.none()
        
        # Filtros opcionales
        nit = self.request.query_params.get('nit')
        if nit:
            nit_normalizado = ''.join(c for c in str(nit) if c.isdigit())
            queryset = queryset.filter(nit_normalizado=nit_normalizado)
        
        entidad_id = self.request.query_params.get('entidad_id')
        if entidad_id:
            queryset = queryset.filter(entidad_id=entidad_id)
        
        empresa_id = self.request.query_params.get('empresa_id')
        if empresa_id:
            queryset = queryset.filter(empresa_servidor_id=empresa_id)
        
        return queryset.order_by('entidad__nombre', 'usuario')
    
    @action(detail=False, methods=['get'], url_path='nits-disponibles')
    def nits_disponibles(self, request):
        """
        Lista los NITs disponibles para la API Key con su razón social.
        Retorna NITs de empresas asociadas y sus razones sociales desde RUTs si están disponibles.
        """
        # Verificar autenticación: API Key o superusuario
        tiene_api_key = hasattr(request, 'cliente_api') and request.cliente_api
        es_superusuario = request.user.is_authenticated and request.user.is_superuser
        
        if not tiene_api_key and not es_superusuario:
            return Response(
                {
                    'error': 'Se requiere API Key válida o autenticación de superusuario',
                    'info': 'Si tienes una API Key, envíala en el header: Api-Key: <tu_api_key>'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        nits_list = []
        
        if tiene_api_key and not es_superusuario:
            empresas_autorizadas = request.empresas_autorizadas
            nits_empresas = set(empresas_autorizadas.values_list('nit_normalizado', flat=True).distinct())
            
            # Obtener razones sociales desde RUTs si están disponibles
            from .models import RUT
            ruts = RUT.objects.filter(nit_normalizado__in=nits_empresas).values(
                'nit_normalizado', 'razon_social', 'nit'
            )
            ruts_dict = {rut['nit_normalizado']: rut for rut in ruts}
            
            # Construir lista de NITs con razón social
            for nit_norm in sorted(nits_empresas):
                rut_info = ruts_dict.get(nit_norm, {})
                nits_list.append({
                    'nit_normalizado': nit_norm,
                    'nit': rut_info.get('nit', nit_norm),
                    'razon_social': rut_info.get('razon_social', 'N/A'),
                    'tiene_claves': ContrasenaEntidad.objects.filter(nit_normalizado=nit_norm).exists()
                })
        else:
            # Superusuario: retornar todos los NITs que tienen claves
            from django.db.models import Count
            nits_con_claves = ContrasenaEntidad.objects.values('nit_normalizado').annotate(
                total=Count('id')
            ).distinct()
            
            nits_set = set([item['nit_normalizado'] for item in nits_con_claves])
            
            # Obtener razones sociales desde RUTs
            from .models import RUT
            ruts = RUT.objects.filter(nit_normalizado__in=nits_set).values(
                'nit_normalizado', 'razon_social', 'nit'
            )
            ruts_dict = {rut['nit_normalizado']: rut for rut in ruts}
            
            for nit_norm in sorted(nits_set):
                rut_info = ruts_dict.get(nit_norm, {})
                nits_list.append({
                    'nit_normalizado': nit_norm,
                    'nit': rut_info.get('nit', nit_norm),
                    'razon_social': rut_info.get('razon_social', 'N/A'),
                    'tiene_claves': True
                })
        
        return Response({
            'nits': nits_list,
            'total': len(nits_list)
        }, status=status.HTTP_200_OK)


class UserTenantProfileViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar perfiles de tenant de usuarios.
    Permite crear, listar, editar y eliminar perfiles de tenant.
    """
    from .models import UserTenantProfile
    from .serializers import UserTenantProfileSerializer
    
    queryset = UserTenantProfile.objects.all().select_related('user')
    serializer_class = UserTenantProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo superusuarios pueden ver todos los perfiles
        if not self.request.user.is_superuser:
            return UserTenantProfile.objects.none()
        return UserTenantProfile.objects.all().select_related('user')
    
    def create(self, request, *args, **kwargs):
        """Crear nuevo perfil de tenant"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden crear perfiles de tenant'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Actualizar perfil de tenant"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden editar perfiles de tenant'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminar perfil de tenant"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden eliminar perfiles de tenant'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

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
        """
        Inicia el descubrimiento de empresas en un servidor de forma asíncrona.
        Retorna un task_id para consultar el progreso.
        """
        from .tasks import descubrir_empresas_task
        
        serializer = DescubrirEmpresasSerializer(data=request.data)
        if serializer.is_valid():
            servidor_id = serializer.validated_data['servidor_id']
            
            # Iniciar tarea asíncrona
            task = descubrir_empresas_task.delay(servidor_id)
            
            return Response({
                'estado': 'procesando',
                'task_id': task.id,
                'mensaje': 'El descubrimiento de empresas se está procesando en segundo plano. Usa el task_id para consultar el progreso.',
                'endpoint_progreso': f'/api/sistema/estado-descubrimiento/?task_id={task.id}'
            }, status=status.HTTP_202_ACCEPTED)
        
        return Response(serializer.errors, status=400)
    
    @action(detail=False, methods=['get'], url_path='estado-descubrimiento')
    def estado_descubrimiento(self, request):
        """
        Consulta el estado del descubrimiento de empresas.
        
        Query params:
        - task_id: ID de la tarea Celery
        
        Returns:
        {
            "task_id": "abc-123",
            "status": "SUCCESS|FAILED|PENDING|PROCESSING",
            "result": {...}  # Solo si está completada
        }
        """
        from celery.result import AsyncResult
        
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response(
                {'error': 'Debes indicar task_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task_result = AsyncResult(task_id)
        
        response_data = {
            'task_id': task_id,
            'status': task_result.state
        }
        
        if task_result.ready():
            if task_result.successful():
                result = task_result.result
                response_data['result'] = result
                response_data['status'] = result.get('status', 'SUCCESS') if isinstance(result, dict) else 'SUCCESS'
                if isinstance(result, dict) and result.get('status') == 'SUCCESS':
                    response_data['total_empresas'] = result.get('total_empresas', 0)
                    response_data['empresas'] = result.get('empresas', [])
            else:
                response_data['error'] = str(task_result.info)
                response_data['status'] = 'ERROR'
        elif task_result.state == 'PROCESSING':
            response_data['meta'] = task_result.info if isinstance(task_result.info, dict) else {}
        
        return Response(response_data)
    
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
                # ✅ MÉTODOS PREDICTIVOS - Con integración MLflow
                resultados = self._ejecutar_analisis_predictivo(
                    tipo_consulta, parametros, empresa_servidor_id
                )

                if 'error' in resultados and any(msg in resultados['error'].lower() for msg in ['no encontrado', 'no entrenado']):
                    logger.info("🔄 Fallback a análisis histórico")
                    resultados = self._generar_recomendaciones_historicas_mejoradas(
                        consulta, empresa_servidor_id, parametros.get('meses', 6)
                    )
                
                # Agregar información de MLflow a la respuesta si está disponible
                if 'mlflow_ui_url' in resultados and resultados['mlflow_ui_url']:
                    logger.info(f"📊 Ver predicción en MLflow: {resultados['mlflow_ui_url']}")
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
            # Normalizar NIT antes de buscar
            nit_norm, _, _ = normalize_nit_and_extract_dv(nit)
            return EmpresaServidor.objects.get(nit_normalizado=nit_norm, anio_fiscal=anio_fiscal)
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

            subdomain = _extract_subdomain_from_request(request)
            profile = getattr(user, 'tenant_profile', None)
            
            # Los superusers no requieren validación de subdominio
            if not user.is_superuser:
                if (
                    not profile
                    or not subdomain
                    or profile.subdomain.lower() != subdomain
                ):
                    return Response(
                        {'detail': 'Subdominio no autorizado'},
                        status=status.HTTP_403_FORBIDDEN
                    )

            empresas_payload = []
            if user.is_superuser:
                empresas = EmpresaServidor.objects.select_related('servidor').all()
                for empresa in empresas:
                    empresas_payload.append({
                        'empresa_servidor_id': empresa.id,
                        'nombre': empresa.nombre,
                        'nit': empresa.nit,
                        'anio_fiscal': empresa.anio_fiscal,
                        'codigo': empresa.codigo,
                        'preferred_template': 'pro',
                        'servidor': empresa.servidor.nombre,
                    })
            else:
                relaciones = UsuarioEmpresa.objects.filter(usuario=user).select_related('empresa_servidor', 'empresa_servidor__servidor')
                for relacion in relaciones:
                    empresa = relacion.empresa_servidor
                    empresas_payload.append({
                        'empresa_servidor_id': empresa.id,
                        'nombre': empresa.nombre,
                        'nit': empresa.nit,
                        'anio_fiscal': empresa.anio_fiscal,
                        'codigo': empresa.codigo,
                        'preferred_template': relacion.preferred_template,
                        'servidor': empresa.servidor.nombre,
                    })

            # Para superusers, usar template por defecto 'pro' si no hay profile
            if user.is_superuser:
                default_template = (profile.preferred_template if profile else None) or 'pro'
            else:
                default_template = profile.preferred_template or 'pro'
            
            default_empresa_id = empresas_payload[0]['empresa_servidor_id'] if empresas_payload else None
            print(
                '[LOGIN]',
                {
                    'username': user.username,
                    'is_superuser': user.is_superuser,
                    'subdomain': subdomain,
                    'empresas': len(empresas_payload),
                    'default_empresa_id': default_empresa_id
                }
            )

            response.data['user'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_superuser': user.is_superuser,
                'puede_gestionar_api_keys': user.puede_gestionar_api_keys(),
                'empresas': empresas_payload,
                'default_template': default_template,
                'default_empresa_id': default_empresa_id,
                'subdomain': profile.subdomain if profile else None,
                'preferred_template': profile.preferred_template if profile else default_template,
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
class APIKeyManagementViewSet(APIKeyAwareViewSet, viewsets.ViewSet):
    """
    ViewSet para gestionar API Keys.
    Permite autenticación con JWT o API Key.
    """
    
    def get_queryset(self):
        # Si el usuario está autenticado (JWT)
        if hasattr(self.request, 'user') and self.request.user.is_authenticated:
            if self.request.user.is_superuser:
                return APIKeyCliente.objects.all()
            return APIKeyCliente.objects.filter(usuario_creador=self.request.user)
        
        # Si se autenticó con API Key, retornar todas (o filtrar por alguna lógica)
        # Por ahora, retornar todas para que funcione
        return APIKeyCliente.objects.all()
    
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
        # Solo si está autenticado con JWT
        if hasattr(request, 'user') and request.user.is_authenticated:
            if not request.user.puede_gestionar_api_keys():
                return Response(
                    {"error": "No tienes permisos para generar API Keys"}, 
                    status=403
                )
        # Si se autenticó con API Key, permitir (asumimos que es admin)
        
        # Verificar que existe al menos una empresa con este NIT
        # Normalizar NIT antes de buscar
        nit_norm, _, _ = normalize_nit_and_extract_dv(nit) if nit else ('', None, '')
        empresas_nit = EmpresaServidor.objects.filter(nit_normalizado=nit_norm) if nit_norm else EmpresaServidor.objects.none()
        if not empresas_nit.exists():
            return Response(
                {"error": "No existen empresas con este NIT"}, 
                status=404
            )
        
        # Verificar permisos del usuario sobre al menos una empresa del NIT
        # Solo si está autenticado con JWT
        if hasattr(request, 'user') and request.user.is_authenticated:
            tiene_permiso = any(
                request.user.has_empresa_permission(empresa, 'ver') 
                for empresa in empresas_nit
            )
            
            if not tiene_permiso and not request.user.is_superuser:
                return Response(
                    {"error": "No tienes permisos para generar API Key para este NIT"}, 
                    status=403
                )
        # Si se autenticó con API Key, permitir (asumimos que es admin)
        
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
                'usuario_creador': request.user if hasattr(request, 'user') and request.user.is_authenticated else None
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
        serializer = APIKeyClienteSerializer(api_keys, many=True, context={'request': request})
        
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
    
    @action(detail=True, methods=['get'], url_path='nits-calendario')
    def listar_nits_calendario(self, request, pk=None):
        """Lista los NITs de RUTs asociados a una API Key para calendario tributario"""
        from .models import APIKeyNITCalendario
        from .serializers import APIKeyNITCalendarioSerializer
        
        try:
            api_key = self.get_queryset().get(pk=pk)
            nits_calendario = APIKeyNITCalendario.objects.filter(api_key=api_key).select_related('rut')
            serializer = APIKeyNITCalendarioSerializer(nits_calendario, many=True)
            
            return Response({
                'api_key_id': api_key.id,
                'api_key_nombre': api_key.nombre_cliente,
                'total_nits': nits_calendario.count(),
                'nits': serializer.data
            })
        except APIKeyCliente.DoesNotExist:
            return Response({'error': 'API Key no encontrada'}, status=404)
    
    @action(detail=True, methods=['post'], url_path='nits-calendario/asociar')
    def asociar_nits_calendario(self, request, pk=None):
        """Asocia NITs de RUTs a una API Key para calendario tributario"""
        from .models import APIKeyNITCalendario, RUT
        from .serializers import AsociarNITCalendarioSerializer
        
        try:
            api_key = self.get_queryset().get(pk=pk)
            serializer = AsociarNITCalendarioSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response(serializer.errors, status=400)
            
            nits_normalizados = serializer.validated_data['nits']
            nits_asociados = []
            nits_no_encontrados = []
            
            for nit_normalizado in nits_normalizados:
                # Buscar RUT si existe
                rut = None
                try:
                    rut = RUT.objects.get(nit_normalizado=nit_normalizado)
                except RUT.DoesNotExist:
                    pass
                
                # Crear o actualizar asociación
                nit_calendario, created = APIKeyNITCalendario.objects.update_or_create(
                    api_key=api_key,
                    nit_normalizado=nit_normalizado,
                    defaults={
                        'rut': rut,
                        'activo': True
                    }
                )
                nits_asociados.append({
                    'nit_normalizado': nit_normalizado,
                    'rut_existe': rut is not None,
                    'razon_social': rut.razon_social if rut else None,
                    'creado': created
                })
            
            return Response({
                'mensaje': f'{len(nits_asociados)} NITs asociados exitosamente',
                'nits_asociados': nits_asociados,
                'nits_no_encontrados': nits_no_encontrados
            })
            
        except APIKeyCliente.DoesNotExist:
            return Response({'error': 'API Key no encontrada'}, status=404)
    
    @action(detail=True, methods=['delete'], url_path='nits-calendario/(?P<nit_id>[^/.]+)')
    def eliminar_nit_calendario(self, request, pk=None, nit_id=None):
        """Elimina un NIT de RUT asociado a una API Key"""
        from .models import APIKeyNITCalendario
        
        try:
            api_key = self.get_queryset().get(pk=pk)
            nit_calendario = APIKeyNITCalendario.objects.get(api_key=api_key, id=nit_id)
            nit_normalizado = nit_calendario.nit_normalizado
            nit_calendario.delete()
            
            return Response({
                'mensaje': f'NIT {nit_normalizado} eliminado de la API Key'
            })
        except APIKeyCliente.DoesNotExist:
            return Response({'error': 'API Key no encontrada'}, status=404)
        except APIKeyNITCalendario.DoesNotExist:
            return Response({'error': 'NIT no encontrado en esta API Key'}, status=404)
    
    @action(detail=False, methods=['post'], authentication_classes=[], permission_classes=[AllowAny])
    def validar_api_key(self, request):
        """Valida API Key y devuelve empresas asociadas (para login frontend)"""
        import json
        
        # Obtener api_key del body - DRF parsea automáticamente request.data
        try:
            # Log para debug
            logger.info(f"🔑 Request method: {request.method}")
            logger.info(f"🔑 Request content_type: {request.content_type}")
            logger.info(f"🔑 Request data: {request.data}")
            logger.info(f"🔑 Request data type: {type(request.data)}")
            logger.info(f"🔑 Request data keys: {list(request.data.keys()) if isinstance(request.data, dict) else 'Not a dict'}")
            
            # Obtener api_key
            api_key_raw = request.data.get('api_key') if isinstance(request.data, dict) else None
            
            # Si no está en request.data, intentar parsear body directamente
            if api_key_raw is None:
                try:
                    if hasattr(request, 'body') and request.body:
                        body_str = request.body.decode('utf-8') if isinstance(request.body, bytes) else str(request.body)
                        body_data = json.loads(body_str)
                        api_key_raw = body_data.get('api_key') if isinstance(body_data, dict) else None
                except (json.JSONDecodeError, AttributeError, UnicodeDecodeError) as e:
                    logger.warning(f"⚠️ No se pudo parsear body: {e}")
            
            logger.info(f"🔑 api_key_raw: {api_key_raw}, type: {type(api_key_raw)}")
            
            # Convertir a string de forma segura
            if api_key_raw is None:
                logger.error("❌ api_key_raw es None - no se encontró en request")
                return Response({'error': 'API Key requerida'}, status=400)
            
            # Si es string, usar directamente
            if isinstance(api_key_raw, str):
                api_key = api_key_raw.strip()
            # Si es dict (caso raro), extraer el valor
            elif isinstance(api_key_raw, dict):
                api_key = str(api_key_raw.get('api_key', '')).strip()
            # Si es lista/tupla, tomar el primer elemento
            elif isinstance(api_key_raw, (list, tuple)):
                api_key = str(api_key_raw[0]).strip() if api_key_raw else ''
            # Cualquier otro tipo, convertir a string
            else:
                api_key = str(api_key_raw).strip()
            
            logger.info(f"🔑 api_key procesada: {api_key[:10] if len(api_key) > 10 else api_key}...")
            
            if not api_key or api_key == '' or api_key.lower() == 'none':
                return Response({'error': 'API Key requerida'}, status=400)
                
        except Exception as e:
            logger.error(f"❌ Error procesando api_key del request: {e}", exc_info=True)
            return Response({'error': f'Error al procesar API Key: {str(e)}'}, status=400)
        
        try:
            api_key_obj = APIKeyCliente.objects.get(api_key__iexact=api_key, activa=True)
            
            if api_key_obj.esta_expirada():
                return Response({'error': 'API Key expirada'}, status=403)
            
            # Actualizar empresas asociadas si es necesario
            empresas = api_key_obj.empresas_asociadas.all()
            if not empresas.exists():
                api_key_obj.actualizar_empresas_asociadas()
                empresas = api_key_obj.empresas_asociadas.all()
            
            # Incrementar contador
            api_key_obj.incrementar_contador()
            
            # Preparar respuesta con empresas
            empresas_payload = []
            for empresa in empresas.select_related('servidor'):
                empresas_payload.append({
                    'empresa_servidor_id': empresa.id,
                    'nombre': empresa.nombre,
                    'nit': empresa.nit,
                    'anio_fiscal': empresa.anio_fiscal,
                    'codigo': empresa.codigo,
                    'preferred_template': 'retail',  # Default para autopago
                    'servidor': empresa.servidor.nombre,
                })
            
            return Response({
                'valid': True,
                'nit': api_key_obj.nit,
                'nombre_cliente': api_key_obj.nombre_cliente,
                'empresas': empresas_payload,
                'total_empresas': len(empresas_payload)
            })
            
        except APIKeyCliente.DoesNotExist:
            return Response({'error': 'API Key inválida'}, status=403)
        except Exception as e:
            logger.error(f"Error validando API Key: {e}")
            return Response({'error': 'Error al validar API Key'}, status=500)
    

# ========== USER MANAGEMENT VIEWSET ==========

class UserManagementViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar usuarios del sistema.
    Solo accesible para superusuarios.
    """
    from django.contrib.auth.models import User
    from .serializers import UserSerializer, CreateUserSerializer
    
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo superusuarios pueden ver todos los usuarios
        if not self.request.user.is_superuser:
            return User.objects.none()
        return User.objects.all().order_by('-date_joined')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateUserSerializer
        return UserSerializer
    
    def create(self, request, *args, **kwargs):
        """Crear nuevo usuario"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden crear usuarios'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'message': 'Usuario creado exitosamente'
        }, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Actualizar usuario"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden editar usuarios'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminar usuario"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden eliminar usuarios'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        
        # No permitir eliminar el propio usuario
        if user.id == request.user.id:
            return Response(
                {'error': 'No puedes eliminar tu propio usuario'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.delete()
        return Response({'message': 'Usuario eliminado exitosamente'}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Resetear contraseña de un usuario"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden resetear contraseñas'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response(
                {'error': 'Debes proporcionar new_password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.contrib.auth.password_validation import validate_password
        try:
            validate_password(new_password, user)
        except Exception as e:
            return Response(
                {'error': f'Contraseña inválida: {", ".join(e.messages)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Contraseña actualizada exitosamente'})


class PasarelaPagoViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar pasarelas de pago.
    Permite crear, listar, editar y eliminar pasarelas.
    """
    from .models import PasarelaPago
    from .serializers import PasarelaPagoSerializer
    
    queryset = PasarelaPago.objects.all().order_by('-fecha_creacion')
    serializer_class = PasarelaPagoSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'codigo'
    
    def get_queryset(self):
        # Solo superusuarios pueden ver todas las pasarelas
        if not self.request.user.is_superuser:
            return PasarelaPago.objects.none()
        return PasarelaPago.objects.all().order_by('-fecha_creacion')
    
    def create(self, request, *args, **kwargs):
        """Crear nueva pasarela"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden crear pasarelas'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Actualizar pasarela"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden editar pasarelas'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminar pasarela"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden eliminar pasarelas'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

class EmpresaDominioViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar dominios de empresas.
    Permite crear, listar, editar y eliminar dominios.
    """
    from .models import EmpresaDominio
    from .serializers import EmpresaDominioSerializer
    
    queryset = EmpresaDominio.objects.all().order_by('-fecha_creacion')
    serializer_class = EmpresaDominioSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo superusuarios pueden ver todos los dominios
        if not self.request.user.is_superuser:
            return EmpresaDominio.objects.none()
        return EmpresaDominio.objects.all().select_related('empresa_servidor').order_by('-fecha_creacion')
    
    def create(self, request, *args, **kwargs):
        """Crear nuevo dominio"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden crear dominios'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Actualizar dominio"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden editar dominios'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminar dominio"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Solo los superusuarios pueden eliminar dominios'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

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
        
        



class TNSViewSet(APIKeyAwareViewSet, viewsets.ViewSet):
    permission_classes = [AllowAny]
    authentication_classes = [JWTOrAPIKeyAuthentication]

    def _build_bridge(self, request, validated_data):
        empresa = _get_empresa_for_request(request, validated_data)
        bridge = TNSBridge(empresa)
        return bridge

    @action(detail=False, methods=['post'])
    def query(self, request):
        serializer = TNSQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bridge = self._build_bridge(request, serializer.validated_data)
        try:
            rows = bridge.run_query(
                serializer.validated_data['sql'],
                serializer.validated_data.get('params'),
            )
            return Response({'rows': rows})
        finally:
            bridge.close()

    @action(detail=False, methods=['post'])
    def procedure(self, request):
        """
        Endpoint genérico para ejecutar cualquier stored procedure de TNS.
        
        Body:
        {
            "empresa_servidor_id": 1,
            "procedure": "TNS_INS_FACTURAVTA",
            "params": {
                "param1": "value1",
                "param2": "value2"
            }
        }
        
        Los params pueden ser dict (con nombres) o lista (posicional).
        Si es dict, se convierte a lista en orden alfabético de keys.
        Si es lista, se usa directamente.
        """
        serializer = TNSProcedureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bridge = self._build_bridge(request, serializer.validated_data)
        params = serializer.validated_data.get('params') or {}
        
        try:
            # Si params es dict, convertirlo a lista (orden alfabético de keys)
            # Esto es necesario porque call_procedure espera una lista
            if isinstance(params, dict):
                # Ordenar keys alfabéticamente para mantener consistencia
                sorted_keys = sorted(params.keys())
                params_list = [params[key] for key in sorted_keys]
            elif isinstance(params, list):
                params_list = params
            else:
                params_list = []
            
            result = bridge.call_procedure(serializer.validated_data['procedure'], params_list)
            return Response({'result': result})
        finally:
            bridge.close()

    @action(detail=False, methods=['post'])
    def emit_invoice(self, request):
        serializer = TNSFacturaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bridge = self._build_bridge(request, serializer.validated_data)
        try:
            numero = bridge.emit_invoice(serializer.validated_data)
            return Response({'numero': numero})
        finally:
            bridge.close()

    @action(detail=False, methods=['get'])
    def tables(self, request):
        serializer = TNSBaseSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        bridge = self._build_bridge(request, serializer.validated_data)
        try:
            return Response({'tables': bridge.list_tables()})
        finally:
            bridge.close()

    @action(detail=False, methods=['get'], url_path='admin_empresas')
    def admin_empresas(self, request):
        serializer = TNSAdminEmpresasSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        empresa = _get_empresa_for_request(request, serializer.validated_data)
        data = _query_admin_empresas(
            empresa,
            serializer.validated_data['search_nit']
        )
        return Response(data)


    @action(detail=False, methods=['post'], url_path='records')
    def records(self, request):
        """
        Endpoint para consultas dinámicas de tablas TNS
        Similar a BCE pero adaptado para manu
        POST /api/tns/records/
        Body: {
            "empresa_servidor_id": 1,
            "table_name": "KARDEX",
            "fields": ["CODCOMP", "NUMERO", "FECHA"],
            "foreign_keys": [...],
            "filters": {...},
            "order_by": [...],
            "page": 1,
            "page_size": 50
        }
        """
        import sys
        import traceback
        
        print("=" * 80)
        print("🔍 [RECORDS] INICIO DE REQUEST")
        print(f"   Método: {request.method}")
        print(f"   Content-Type: {request.content_type}")
        print(f"   Encoding: {sys.getdefaultencoding()}")
        print(f"   File system encoding: {sys.getfilesystemencoding()}")
        
        from .serializers import TNSRecordsSerializer
        from .services.tns_query_builder import TNSQueryBuilder
        
        # Logging para debug de codificación
        try:
            print("   [1] Intentando parsear request.data...")
            print(f"      Tipo de request.data: {type(request.data)}")
            # NO acceder a request.body aquí porque DRF ya lo parseó y causa RawPostDataException
            
            serializer = TNSRecordsSerializer(data=request.data)
            print("   [2] Validando serializer...")
            serializer.is_valid(raise_exception=True)
            print("   [3] Serializer válido ✓")
        except Exception as ser_error:
            print(f"   ❌ ERROR en serializer: {ser_error}")
            print(f"      Tipo de error: {type(ser_error)}")
            traceback.print_exc()
            logger.error(f'Error en serializer TNSRecords: {ser_error}', exc_info=True)
            # Si el error es de codificación, retornar error
            if 'charmap' in str(ser_error).lower() or 'decode' in str(ser_error).lower():
                print("   [ERROR] Error de codificación detectado")
                return Response(
                    {'error': f'Error de codificación en request: {str(ser_error)}. Verifique que el request esté en UTF-8.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                raise
        
        print("   [4] Obteniendo empresa...")
        print(f"      empresa_servidor_id: {serializer.validated_data.get('empresa_servidor_id')}")
        print(f"      nit: {serializer.validated_data.get('nit')}")
        print(f"      anio_fiscal: {serializer.validated_data.get('anio_fiscal')}")
        print(f"      ¿Tiene API Key?: {hasattr(request, 'cliente_api') and request.cliente_api is not None}")
        if hasattr(request, 'empresas_autorizadas'):
            print(f"      Empresas autorizadas: {list(request.empresas_autorizadas.values_list('id', flat=True)) if request.empresas_autorizadas else 'None'}")
        
        try:
            empresa = _get_empresa_for_request(request, serializer.validated_data)
            print(f"      ✓ Empresa obtenida: {empresa.nombre if empresa else 'None'} (ID: {empresa.id if empresa else 'None'})")
        except serializers.ValidationError as ve:
            print(f"      ❌ ValidationError: {ve}")
            traceback.print_exc()
            return Response(
                {'error': str(ve)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(f"      ❌ ERROR obteniendo empresa: {e}")
            print(f"         Tipo: {type(e)}")
            traceback.print_exc()
            logger.error(f'Error obteniendo empresa: {e}', exc_info=True)
            return Response(
                {'error': f'Error obteniendo empresa: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not empresa:
            print("      ❌ ERROR: Empresa es None")
            return Response(
                {'error': 'Empresa no encontrada o sin permisos.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print("   [5] Creando bridge...")
        bridge = TNSBridge(empresa)
        print(f"      Bridge charset: {bridge.charset}")
        
        try:
            print("   [5.1] Conectando a Firebird...")
            bridge.connect()
            print("   [5.1] ✓ Conexión exitosa")
            
            # Función para obtener nombre real de tabla (como BCE)
            print("   [5.2] Obteniendo esquema de base de datos...")
            def get_real_table_name(table_name):
                bridge._ensure_schema()
                table_key = table_name.upper()
                if table_key not in bridge.schema_cache:
                    available = ", ".join(bridge.schema_cache.keys())
                    raise ValueError(f"Tabla '{table_name}' no encontrada. Tablas disponibles: {available}")
                return bridge.schema_cache[table_key]
            
            # Construir query de forma segura (EXACTAMENTE como BCE)
            print("   [5.3] Construyendo query builder...")
            print(f"      Tabla: {serializer.validated_data['table_name']}")
            print(f"      Campos: {len(serializer.validated_data.get('fields', []))}")
            print(f"      Foreign keys: {len(serializer.validated_data.get('foreign_keys', []))}")
            
            query_builder = TNSQueryBuilder(
                serializer.validated_data['table_name'],
                get_real_table_name_func=get_real_table_name
            )
            
            print("   [5.4] Agregando campos, foreign keys, filtros y orden...")
            query_builder.add_fields(serializer.validated_data.get('fields', []))
            query_builder.add_foreign_keys(serializer.validated_data.get('foreign_keys', []))
            query_builder.add_filters(serializer.validated_data.get('filters', {}))
            query_builder.add_order_by(serializer.validated_data.get('order_by', []))
            query_builder.set_pagination(
                serializer.validated_data.get('page', 1),
                serializer.validated_data.get('page_size', 50)
            )
            print("   [5.4] ✓ Query builder configurado")
            
            # Ejecutar query de conteo primero (como BCE)
            print("   [5.5] Ejecutando query de conteo...")
            count_query, count_params = query_builder.build_count_query()
            print("=" * 80)
            print("   [SQL COUNT] QUERY DE CONTEO COMPLETA:")
            print("=" * 80)
            print(count_query)
            if count_params:
                print(f"\n   [SQL COUNT] Parámetros: {count_params}")
            print("=" * 80)
            bridge.cursor.execute(count_query, count_params)
            total_records = bridge.cursor.fetchone()[0]
            print(f"   [5.5] ✓ Total de registros: {total_records}")
            
            # Ejecutar query de datos (como BCE)
            print("   [5.6] Ejecutando query de datos...")
            paginated_query, params = query_builder.build_query()
            print("=" * 80)
            print("   [SQL SELECT] QUERY DE DATOS COMPLETA:")
            print("=" * 80)
            print(paginated_query)
            if params:
                print(f"\n   [SQL SELECT] Parámetros: {params}")
            print("=" * 80)
            try:
                bridge.cursor.execute(paginated_query, params)
                print("   [5.6] ✓ Query ejecutada")
            except (UnicodeDecodeError, ValueError) as decode_error:
                # Si hay error de decodificación en firebirdsql, intentar con charset alternativo
                print(f"   [5.6] ⚠ Error de decodificación: {decode_error}")
                print(f"      Tipo: {type(decode_error)}")
                # Cerrar cursor y reconectar con charset alternativo
                try:
                    bridge.cursor.close()
                except:
                    pass
                bridge.close()
                # Cambiar charset a latin-1 y reconectar
                original_charset = bridge.charset
                bridge.charset = 'latin-1'
                print(f"   [5.6-RETRY] Reintentando con charset: {bridge.charset} (original: {original_charset})")
                bridge.connect()
                bridge.cursor.execute(paginated_query, params)
                print("   [5.6-RETRY] ✓ Query ejecutada con charset alternativo")
            
            # Decodificar nombres de columnas correctamente (pueden venir como bytes)
            print("   [6] Decodificando nombres de columnas...")
            columns = []
            for idx, desc in enumerate(bridge.cursor.description or []):
                col_name = desc[0]
                should_log = idx < 5  # Log solo las primeras 5 columnas
                if should_log:
                    print(f"      Columna {idx}: tipo={type(col_name)}, valor={repr(str(col_name)[:50]) if col_name else None}")
                if isinstance(col_name, bytes):
                    try:
                        col_name = col_name.decode(bridge.charset, errors='replace')
                        if should_log:
                            print(f"         ✓ Decodificado con {bridge.charset}")
                    except (UnicodeDecodeError, LookupError) as e:
                        if should_log:
                            print(f"         ⚠ Error con {bridge.charset}: {e}")
                        try:
                            col_name = col_name.decode('latin-1', errors='replace')
                            if should_log:
                                print(f"         ✓ Decodificado con latin-1")
                        except Exception as e2:
                            if should_log:
                                print(f"         ⚠ Error con latin-1: {e2}")
                            try:
                                col_name = col_name.decode('utf-8', errors='replace')
                                if should_log:
                                    print(f"         ✓ Decodificado con utf-8")
                            except Exception as e3:
                                if should_log:
                                    print(f"         ⚠ Error con utf-8: {e3}")
                                col_name = str(col_name, errors='replace')
                                if should_log:
                                    print(f"         ✓ Convertido a string")
                # Asegurar que sea string y UTF-8 válido
                if isinstance(col_name, str):
                    try:
                        col_name.encode('utf-8')
                    except UnicodeEncodeError as e:
                        if should_log:
                            print(f"         ⚠ Error encoding UTF-8: {e}, normalizando...")
                        col_name = col_name.encode('utf-8', errors='replace').decode('utf-8')
                columns.append(col_name.strip() if isinstance(col_name, str) else str(col_name).strip())
            print(f"   [6] ✓ {len(columns)} columnas procesadas")
            
            # Procesar resultados con column_mapping (como BCE)
            from math import ceil
            _, column_mapping = query_builder.build_select_clause()
            print("   [7] Procesando filas...")
            rows = []
            row_count = 0
            try:
                all_rows = bridge.cursor.fetchall()
                print(f"      Total de filas a procesar: {len(all_rows)}")
                for row_idx, row in enumerate(all_rows):
                    if row_idx < 3:  # Log solo las primeras 3 filas
                        print(f"      Procesando fila {row_idx + 1}...")
                    row_dict = {}
                    for idx, col in enumerate(columns):
                        try:
                            value = row[idx]
                            if row_idx < 3 and idx < 3:  # Log solo primeros valores
                                print(f"         [{col}] tipo={type(value)}, valor={repr(str(value)[:30]) if value else None}")
                            # Usar función helper para decodificar correctamente (ya normaliza a UTF-8)
                            value = _decode_firebird_value(value)
                            # Mapear nombre de columna a alias original (como BCE)
                            final_col = next((k for k, v in column_mapping.items() if v == col), col)
                            row_dict[final_col] = value
                        except (UnicodeDecodeError, UnicodeEncodeError) as e:
                            # Si hay error de codificación en un campo específico, usar valor por defecto
                            print(f"         ⚠ Error de codificación en columna {col}: {e}")
                            logger.warning(f'Error de codificación en columna {col}: {e}')
                            final_col = next((k for k, v in column_mapping.items() if v == col), col)
                            row_dict[final_col] = None
                        except Exception as e:
                            # Otro error, usar valor por defecto
                            print(f"         ⚠ Error procesando columna {col}: {e}")
                            logger.warning(f'Error procesando columna {col}: {e}')
                            final_col = next((k for k, v in column_mapping.items() if v == col), col)
                            row_dict[final_col] = None
                    rows.append(row_dict)
                    row_count += 1
                print(f"   [7] ✓ {row_count} filas procesadas")
            except (UnicodeDecodeError, UnicodeEncodeError) as e:
                logger.error(f'Error de codificación al procesar filas: {e}', exc_info=True)
                # Retornar error específico
                return Response(
                    {'error': f'Error de codificación de caracteres: {str(e)}. Verifique la configuración de charset de Firebird.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            page = serializer.validated_data.get('page', 1)
            page_size = serializer.validated_data.get('page_size', 50)
            
            # Limpiar y normalizar todos los valores para JSON (asegurar UTF-8)
            def clean_for_json(obj):
                """Recursivamente limpia valores para asegurar serialización JSON segura"""
                if isinstance(obj, dict):
                    return {str(k): clean_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_for_json(item) for item in obj]
                elif isinstance(obj, bytes):
                    # Decodificar bytes
                    return _decode_firebird_value(obj)
                elif isinstance(obj, str):
                    # Asegurar UTF-8 válido
                    try:
                        # Si ya es UTF-8 válido, retornar tal cual
                        obj.encode('utf-8')
                        return obj
                    except UnicodeEncodeError:
                        # Si no es UTF-8 válido, normalizar
                        return _decode_firebird_value(obj.encode('latin-1', errors='replace'))
                elif obj is None:
                    return None
                elif isinstance(obj, (int, float, bool)):
                    return obj
                elif isinstance(obj, Decimal):
                    # Convertir Decimal a float para JSON
                    return float(obj)
                elif hasattr(obj, 'isoformat'):  # datetime, date
                    return obj.isoformat()
                else:
                    # Para otros tipos, convertir a string
                    try:
                        str_val = str(obj)
                        # Asegurar que el string sea UTF-8 válido
                        return _decode_firebird_value(str_val.encode('latin-1', errors='replace') if isinstance(str_val, str) else str_val)
                    except Exception:
                        return None
            
            # Limpiar rows antes de serializar
            try:
                cleaned_rows = clean_for_json(rows)
            except Exception as clean_error:
                logger.error(f'Error limpiando datos para JSON: {clean_error}', exc_info=True)
                # Si falla la limpieza, intentar limpieza más básica
                try:
                    # Limpieza básica: solo decodificar bytes
                    cleaned_rows = []
                    for row in rows:
                        cleaned_row = {}
                        for k, v in row.items():
                            if isinstance(v, bytes):
                                cleaned_row[k] = _decode_firebird_value(v)
                            else:
                                cleaned_row[k] = v
                        cleaned_rows.append(cleaned_row)
                except Exception as e2:
                    logger.error(f'Error incluso con limpieza básica: {e2}', exc_info=True)
                    cleaned_rows = rows
            
            # Agregar URLs de imágenes si es consulta de MATERIAL
            nit_normalizado = None
            table_name = serializer.validated_data.get('table_name', '')
            if table_name and table_name.upper() == 'MATERIAL' and empresa:
                nit_normalizado = _normalize_nit(empresa.nit)
                # Agregar URLs de imágenes a cada fila
                for row in cleaned_rows:
                    # URL de imagen del material (si existe)
                    codigo_material = row.get('CODIGO') or row.get('codigo')
                    if codigo_material:
                        try:
                            material_img = MaterialImagen.objects.get(
                                nit_normalizado=nit_normalizado,
                                codigo_material=str(codigo_material)
                            )
                            if material_img.imagen:
                                row['imagen_url'] = request.build_absolute_uri(material_img.imagen.url)
                            else:
                                row['imagen_url'] = None
                        except MaterialImagen.DoesNotExist:
                            row['imagen_url'] = None
                    
                    # URL de imagen del grupo (si existe)
                    gm_codigo = row.get('GM_CODIGO') or row.get('gm_codigo')
                    if gm_codigo:
                        try:
                            grupo_img = GrupoMaterialImagen.objects.get(
                                nit_normalizado=nit_normalizado,
                                gm_codigo=str(gm_codigo)
                            )
                            if grupo_img.imagen:
                                row['grupo_imagen_url'] = request.build_absolute_uri(grupo_img.imagen.url)
                            else:
                                row['grupo_imagen_url'] = None
                        except GrupoMaterialImagen.DoesNotExist:
                            row['grupo_imagen_url'] = None
            
            # Retornar formato EXACTAMENTE como BCE
            print("   [9] Creando respuesta...")
            try:
                response_data = {
                    'data': cleaned_rows,  # BCE usa 'data', no 'results'
                    'pagination': {  # BCE usa 'pagination', no campos separados
                        'total': total_records,
                        'page': page,
                        'page_size': page_size,
                        'total_pages': ceil(total_records / page_size),
                        'next': page * page_size < total_records,
                        'previous': page > 1
                    }
                }
                print(f"   [9] ✓ Respuesta creada: {len(cleaned_rows)} filas, total={total_records}")
                print("   [9] Intentando serializar Response...")
                response = Response(response_data)
                print("   [9] ✓ Response serializado exitosamente")
                print("=" * 80)
                return response
            except (UnicodeDecodeError, UnicodeEncodeError) as json_error:
                logger.error(f'Error de codificación al serializar JSON: {json_error}', exc_info=True)
                # Intentar limpiar más agresivamente
                import json as json_lib
                try:
                    # Forzar serialización manual para identificar el problema
                    json_str = json_lib.dumps(cleaned_rows, ensure_ascii=False, default=str)
                    # Si llegamos aquí, el problema está en DRF Response, no en los datos
                    return Response({
                        'data': json_lib.loads(json_str),
                        'pagination': {
                            'total': total_records,
                            'page': page,
                            'page_size': page_size,
                            'total_pages': ceil(total_records / page_size),
                            'next': page * page_size < total_records,
                            'previous': page > 1
                        }
                    })
                except Exception as e2:
                    logger.error(f'Error incluso con serialización manual: {e2}', exc_info=True)
                    return Response(
                        {'error': f'Error de codificación: {str(e2)}. Contacte al administrador.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
        except ValueError as e:
            print(f"   ❌ ValueError: {e}")
            print(f"      Tipo: {type(e)}")
            traceback.print_exc()
            logger.error(f'ValueError en records: {e}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except serializers.ValidationError as e:
            print(f"   ❌ ValidationError: {e}")
            print(f"      Tipo: {type(e)}")
            traceback.print_exc()
            logger.error(f'ValidationError en records: {e}', exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except UnicodeDecodeError as e:
            print(f"   ❌ UnicodeDecodeError: {e}")
            traceback.print_exc()
            logger.error(f'Error de codificación en consulta TNS: {e}', exc_info=True)
            return Response(
                {'error': f'Error de codificación de caracteres: {str(e)}. Verifique que los datos estén en formato correcto.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            print(f"   ❌ EXCEPCIÓN GENERAL: {e}")
            print(f"      Tipo: {type(e)}")
            traceback.print_exc()
            logger.error(f'Error en consulta TNS: {e}', exc_info=True)
            # Asegurar que el mensaje de error también sea UTF-8 válido
            error_msg = str(e)
            try:
                error_msg = error_msg.encode('utf-8', errors='replace').decode('utf-8')
            except Exception:
                error_msg = 'Error al ejecutar consulta (error de codificación)'
            print("=" * 80)
            return Response(
                {'error': error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            try:
                print("   [FINAL] Cerrando bridge...")
                bridge.close()
                print("   [FINAL] ✓ Bridge cerrado")
            except Exception as e:
                print(f"   [FINAL] ⚠ Error cerrando bridge: {e}")
            print("=" * 80)

    @action(detail=False, methods=['post'], url_path='validate_user', authentication_classes=[], permission_classes=[AllowAny])
    def validate_user(self, request):
        """
        Valida usuario TNS. Endpoint público para permitir login desde e-commerce.
        No requiere autenticación previa.
        """
        serializer = TNSUserValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Obtener empresa directamente del validated_data (no requiere autenticación)
        empresa_servidor_id = serializer.validated_data.get('empresa_servidor_id')
        if not empresa_servidor_id:
            # Intentar obtener de nit y anio_fiscal si están disponibles
            nit = serializer.validated_data.get('nit')
            anio_fiscal = serializer.validated_data.get('anio_fiscal')
            if nit and anio_fiscal:
                nit_normalizado = _normalize_nit(nit)
                try:
                    empresa = EmpresaServidor.objects.get(nit_normalizado=nit_normalizado, anio_fiscal=anio_fiscal)
                    empresa_servidor_id = empresa.id
                except EmpresaServidor.DoesNotExist:
                    raise serializers.ValidationError(f'Empresa con NIT {nit} y año {anio_fiscal} no encontrada')
            else:
                raise serializers.ValidationError('empresa_servidor_id es requerido (o nit y anio_fiscal)')
        else:
            try:
                empresa = EmpresaServidor.objects.get(id=empresa_servidor_id)
            except EmpresaServidor.DoesNotExist:
                raise serializers.ValidationError(f'Empresa con ID {empresa_servidor_id} no encontrada')
        
        bridge = TNSBridge(empresa)
        try:
            bridge.connect()
            cursor = bridge.conn.cursor()
            try:
                validation_row = _run_validation_procedure(
                    cursor,
                    serializer.validated_data['username'],
                    serializer.validated_data['password']
                )
                validate_payload = _build_validate_payload(validation_row)
                success_raw = validation_row.get('OSUCCESS')
                success_flag = (
                    str(success_raw).strip().lower()
                    if success_raw is not None
                    else ''
                )
                is_success = success_flag in ('1', 'true', 't', 'si', 'yes')
                if is_success:
                    modules_payload = _fetch_user_permissions(
                        cursor,
                        serializer.validated_data['username']
                    )
                else:
                    modules_payload = {}
                return Response({'VALIDATE': validate_payload, 'MODULOS': modules_payload})
            finally:
                cursor.close()
        except firebirdsql.Error as exc:
            raise serializers.ValidationError(f'Error al consultar Firebird: {exc}')
        finally:
            bridge.close()

    @action(detail=False, methods=['post'], url_path='validar-tercero', authentication_classes=[], permission_classes=[AllowAny])
    def validar_tercero(self, request):
        """
        Valida un tercero por documento (cédula o NIT).
        Endpoint público para e-commerce. Usa usuario_tns de EmpresaEcommerceConfig para seguridad.
        1. Busca en TNS (TERCEROS)
        2. Si no encuentra, consulta API DIAN
        3. Crea/actualiza en TNS
        4. Retorna datos del tercero
        """
        from .serializers import TNSValidarTerceroSerializer
        from .services.tns_bridge import TNSBridge
        from django.conf import settings
        import requests
        import re
        
        serializer = TNSValidarTerceroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        empresa_servidor_id = serializer.validated_data.get('empresa_servidor_id')
        document_type = serializer.validated_data.get('document_type')
        document_number = serializer.validated_data.get('document_number')
        telefono = serializer.validated_data.get('telefono', '').strip()
        
        if not empresa_servidor_id:
            return Response(
                {'error': 'Debes indicar empresa_servidor_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener empresa directamente (sin validar autenticación)
        try:
            empresa = EmpresaServidor.objects.get(id=empresa_servidor_id)
        except EmpresaServidor.DoesNotExist:
            return Response(
                {'error': f'Empresa con ID {empresa_servidor_id} no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Obtener configuración de e-commerce para usar usuario_tns seguro
        try:
            config = EmpresaEcommerceConfig.objects.get(empresa_servidor_id=empresa_servidor_id)
            usuario_tns = config.usuario_tns
            password_tns = config.password_tns
        except EmpresaEcommerceConfig.DoesNotExist:
            # Si no hay configuración de e-commerce, usar credenciales de la empresa (fallback)
            logger.warning(f"No hay configuración de e-commerce para empresa {empresa_servidor_id}, usando credenciales de empresa")
            usuario_tns = empresa.usuario_tns
            password_tns = empresa.password_tns
        except Exception as e:
            logger.error(f"Error obteniendo configuración de e-commerce: {e}")
            return Response(
                {'error': 'Error al obtener configuración de e-commerce'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        if not usuario_tns or not password_tns:
            return Response(
                {'error': 'Credenciales TNS no configuradas para esta empresa'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear bridge - TNSBridge usa credenciales del Servidor para conectar a Firebird
        # Las credenciales usuario_tns/password_tns de e-commerce se usan para validaciones TNS internas
        bridge = TNSBridge(empresa)
        bridge.connect()
        
        try:
            # Normalizar número de documento (solo dígitos)
            nit_normalizado = re.sub(r'[^0-9]', '', document_number)
            
            # 1. Buscar en TNS
            logger.info(f"Buscando tercero en TNS con NIT normalizado: {nit_normalizado}")
            cursor = bridge.conn.cursor()
            cursor.execute("""
                SELECT FIRST 1 
                    NOMBRE, NIT, EMAIL, TELEF1
                FROM TERCEROS
                WHERE REPLACE(REPLACE(REPLACE(NIT, '.', ''), '-', ''), ' ', '') LIKE ?
            """, (f'%{nit_normalizado}%',))
            
            tercero_tns = cursor.fetchone()
            
            if tercero_tns:
                # Encontrado en TNS
                nombre, nit, email, telefono_tns = tercero_tns
                logger.info(f"✅ Tercero encontrado en TNS: {nombre}")
                
                # Si se proporcionó teléfono en la petición, actualizar en TNS
                if telefono:
                    cursor.execute("""
                        UPDATE TERCEROS
                        SET TELEF1 = ?
                        WHERE REPLACE(REPLACE(REPLACE(NIT, '.', ''), '-', ''), ' ', '') = ?
                    """, (telefono, nit_normalizado))
                    bridge.conn.commit()
                    logger.info(f"📞 Teléfono actualizado en TNS: {telefono}")
                    telefono_final = telefono
                else:
                    telefono_final = telefono_tns or ''
                
                return Response({
                    'encontrado_en_tns': True,
                    'nombre': nombre or '',
                    'nit': nit or '',
                    'email': email or '',
                    'telefono': telefono_final,
                    'document_number': nit_normalizado
                })
            
            logger.info(f"❌ Tercero no encontrado en TNS, consultando API DIAN...")
            
            # 2. No encontrado en TNS, consultar API DIAN
            # Determinar tipo de documento para API DIAN (31=NIT, 9=Cédula)
            doc_type_api = 31 if document_type == 'nit' else 13
            
            # Obtener token y URL base
            # Primero intentar desde configuración de empresa (TOKENDIANVM)
            cursor.execute("""
                SELECT CAST(contenido AS VARCHAR(500)) FROM varios WHERE variab = ?
            """, ('TOKENDIANVM',))
            token_row = cursor.fetchone()
            token = token_row[0] if token_row and token_row[0] else None
            base_url = getattr(settings, 'API_DIAN_ROUTE', 'http://45.149.204.184:81')
            
            #cursor.execute("""
            #    SELECT CAST(contenido AS VARCHAR(500)) FROM varios WHERE variab = ?
            #""", ('ENDPOINTDIANVM',))
            #endpoint_row = cursor.fetchone()
            #base_url = endpoint_row[0] if endpoint_row and endpoint_row[0] else None
            #
            ## Si no hay token de empresa, usar del env
            if not token:
                token = getattr(settings, 'TOKEN_API_DIAN_BASIC', None)
          
            # Si no hay base_url, usar del env
            if not base_url:
                base_url = getattr(settings, 'API_DIAN_ROUTE', 'http://45.149.204.184:81')
            
            # Construir URL de API DIAN
            # La base_url puede ser completa o solo la base, ajustar
            if '/api/' in base_url:
                api_url = f"{base_url}/customer/{doc_type_api}/{nit_normalizado}"
            else:
                api_url = f"{base_url}/api/customer/{doc_type_api}/{nit_normalizado}"
            
            # Consultar API DIAN
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {token}' if token else ''
            }
            
            try:
                logger.info(f"Consultando API DIAN: {api_url}")
                dian_response = requests.get(api_url, headers=headers, timeout=10)
                dian_response.raise_for_status()
                dian_data = dian_response.json()
                
                logger.info(f"Respuesta DIAN recibida: {dian_data}")
                
                # Extraer datos de la respuesta DIAN
                receiver_name = ''
                receiver_email = ''
                
                # Manejar diferentes formatos de respuesta
                if dian_data.get('ResponseDian', {}).get('GetAcquirerResponse', {}).get('GetAcquirerResult', {}):
                    result = dian_data['ResponseDian']['GetAcquirerResponse']['GetAcquirerResult']
                    receiver_name = result.get('ReceiverName', '') or ''
                    receiver_email = result.get('ReceiverEmail', '') or ''
                elif dian_data.get('GetAcquirerResult', {}):
                    # Formato alternativo
                    result = dian_data['GetAcquirerResult']
                    receiver_name = result.get('ReceiverName', '') or ''
                    receiver_email = result.get('ReceiverEmail', '') or ''
                
                logger.info(f"Datos extraídos - Nombre: {receiver_name}, Email: {receiver_email}")
                
                # 3. Verificar si existe en TNS (solo verificar, NO crear)
                cursor.execute("""
                    SELECT FIRST 1 TERID
                    FROM TERCEROS
                    WHERE REPLACE(REPLACE(REPLACE(NIT, '.', ''), '-', ''), ' ', '') = ?
                """, (nit_normalizado,))
                
                tercero_existente = cursor.fetchone()
                
                if tercero_existente:
                    # Si existe, actualizar solo si se proporcionó teléfono
                    if telefono:
                        terid = tercero_existente[0]
                        cursor.execute("""
                            UPDATE TERCEROS
                            SET TELEF1 = ?
                            WHERE TERID = ?
                        """, (telefono, terid))
                        bridge.conn.commit()
                        logger.info(f"📞 Teléfono actualizado: {telefono}")
                
                # NO crear el tercero aquí - se creará cuando el usuario complete el formulario
                # Solo retornar los datos encontrados en DIAN para prellenar el formulario
                return Response({
                    'encontrado_en_tns': bool(tercero_existente),
                    'encontrado_en_dian': True,
                    'necesita_completar': not bool(tercero_existente),  # Indicar que necesita completar formulario
                    'nombre': receiver_name,
                    'nit': nit_normalizado,
                    'email': receiver_email,
                    'telefono': telefono or '',
                    'document_number': nit_normalizado
                })
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error consultando API DIAN: {e}")
                return Response({
                    'encontrado_en_tns': False,
                    'encontrado_en_dian': False,
                    'error': f'No se encontró en TNS y error al consultar DIAN: {str(e)}',
                    'document_number': nit_normalizado
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Error validando tercero: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            bridge.close()

    @action(detail=False, methods=['post'], url_path='crear-tercero', authentication_classes=[], permission_classes=[AllowAny])
    def crear_tercero(self, request):
        """
        Crea un tercero en TNS usando el procedimiento almacenado TNS_INS_TERCERO.
        Endpoint público para e-commerce. Usa usuario_tns de EmpresaEcommerceConfig para seguridad.
        Se llama cuando el usuario completa el formulario de datos de facturación.
        
        Body:
        {
            "empresa_servidor_id": 1,
            "document_type": "nit",  // "cedula" o "nit"
            "document_number": "900123456",
            "nombre": "Empresa Ejemplo S.A.S.",
            "email": "correo@ejemplo.com",
            "telefono": "3001234567",
            "nature": "juridica"  // "natural" o "juridica" - determina tipo documento (J o N)
        }
        """
        from .serializers import TNSCrearTerceroSerializer
        from .services.tns_bridge import TNSBridge
        import re
        
        serializer = TNSCrearTerceroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        empresa_servidor_id = serializer.validated_data.get('empresa_servidor_id')
        document_type = serializer.validated_data.get('document_type')
        document_number = serializer.validated_data.get('document_number')
        nombre = serializer.validated_data.get('nombre')
        email = serializer.validated_data.get('email', '').strip() or None
        telefono = serializer.validated_data.get('telefono', '').strip() or None
        nature = serializer.validated_data.get('nature')  # 'natural' o 'juridica'
        
        if not empresa_servidor_id:
            return Response(
                {'error': 'Debes indicar empresa_servidor_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener empresa directamente (sin validar autenticación)
        try:
            empresa = EmpresaServidor.objects.get(id=empresa_servidor_id)
        except EmpresaServidor.DoesNotExist:
            return Response(
                {'error': f'Empresa con ID {empresa_servidor_id} no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Obtener configuración de e-commerce para usar usuario_tns seguro
        try:
            config = EmpresaEcommerceConfig.objects.get(empresa_servidor_id=empresa_servidor_id)
            usuario_tns = config.usuario_tns
            password_tns = config.password_tns
        except EmpresaEcommerceConfig.DoesNotExist:
            # Si no hay configuración de e-commerce, usar credenciales de la empresa (fallback)
            logger.warning(f"No hay configuración de e-commerce para empresa {empresa_servidor_id}, usando credenciales de empresa")
            usuario_tns = empresa.usuario_tns
            password_tns = empresa.password_tns
        except Exception as e:
            logger.error(f"Error obteniendo configuración de e-commerce: {e}")
            return Response(
                {'error': 'Error al obtener configuración de e-commerce'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        if not usuario_tns or not password_tns:
            return Response(
                {'error': 'Credenciales TNS no configuradas para esta empresa'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear bridge - TNSBridge usa credenciales del Servidor para conectar a Firebird
        # Las credenciales usuario_tns/password_tns de e-commerce se usan para validaciones TNS internas
        bridge = TNSBridge(empresa)
        bridge.connect()
        
        try:
            # Normalizar número de documento (solo dígitos)
            nit_normalizado = re.sub(r'[^0-9]', '', document_number)
            
            # Verificar si ya existe
            cursor = bridge.conn.cursor()
            cursor.execute("""
                SELECT FIRST 1 TERID
                FROM TERCEROS
                WHERE REPLACE(REPLACE(REPLACE(NIT, '.', ''), '-', ''), ' ', '') = ?
            """, (nit_normalizado,))
            
            tercero_existente = cursor.fetchone()
            
            if tercero_existente:
                # Si ya existe, actualizar datos
                terid = tercero_existente[0]
                update_params = [nombre]
                update_fields = ['NOMBRE = ?']
                
                if email:
                    update_fields.append('EMAIL = ?')
                    update_params.append(email)
                
                if telefono:
                    update_fields.append('TELEF1 = ?')
                    update_params.append(telefono)
                
                update_params.append(terid)
                update_sql = f"UPDATE TERCEROS SET {', '.join(update_fields)} WHERE TERID = ?"
                cursor.execute(update_sql, update_params)
                bridge.conn.commit()
                
                logger.info(f"✅ Tercero actualizado: TERID={terid}, NIT={nit_normalizado}")
                
                return Response({
                    'creado': False,
                    'actualizado': True,
                    'terid': terid,
                    'nit': nit_normalizado,
                    'nombre': nombre,
                    'email': email,
                    'telefono': telefono
                })
            
            # Determinar tipo de documento según naturaleza
            # 'juridica' -> 'J', 'natural' -> 'N'
            tipo_documento = 'J' if nature == 'juridica' else 'N'
            
            # Parámetros del procedimiento TNS_INS_TERCERO según makos.py:
            # 1. NIT (primer parámetro)
            # 2. Tipo de documento (segundo parámetro: J o N)
            # 3. Documento (tercer parámetro)
            # 4. Nombre (cuarto parámetro)
            # 5. Dirección (quinto parámetro, NULL)
            # 6. Estado (sexto parámetro, siempre 'N')
            # 7. Email (séptimo parámetro)
            params_procedimiento = (
                nit_normalizado,  # NIT - primer parámetro
                tipo_documento,   # Tipo de documento - segundo parámetro (J o N según nature)
                nit_normalizado,  # Documento - tercer parámetro
                nombre or 'Consumidor Final',  # Nombre - cuarto parámetro
                None,             # Dirección (NULL) - quinto parámetro
                'N',              # Estado - sexto parámetro (siempre 'N')
                email             # Email - séptimo parámetro
            )
            
            logger.info(f"Creando nuevo tercero con procedimiento TNS_INS_TERCERO: NIT={nit_normalizado}, Tipo={tipo_documento}, Nature={nature}")
            cursor.execute("SELECT * FROM TNS_INS_TERCERO(?,?,?,?,?,?,?)", params_procedimiento)
            resultado_tercero = cursor.fetchone()
            
            if not resultado_tercero:
                logger.warning(f"El procedimiento TNS_INS_TERCERO no retornó resultado para NIT: {nit_normalizado}")
                bridge.conn.rollback()
                return Response(
                    {'error': 'No se pudo crear el tercero. El procedimiento no retornó resultado.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            logger.info(f"✅ Tercero creado correctamente mediante TNS_INS_TERCERO")
            
            # Si se proporcionó teléfono, actualizarlo después de crear el tercero
            if telefono:
                cursor.execute("""
                    UPDATE TERCEROS
                    SET TELEF1 = ?
                    WHERE REPLACE(REPLACE(REPLACE(NIT, '.', ''), '-', ''), ' ', '') = ?
                """, (telefono, nit_normalizado))
                logger.info(f"📞 Teléfono actualizado: {telefono}")
            
            bridge.conn.commit()
            
            # Obtener el TERID del tercero creado
            cursor.execute("""
                SELECT FIRST 1 TERID
                FROM TERCEROS
                WHERE REPLACE(REPLACE(REPLACE(NIT, '.', ''), '-', ''), ' ', '') = ?
            """, (nit_normalizado,))
            terid_row = cursor.fetchone()
            terid = terid_row[0] if terid_row else None
            
            return Response({
                'creado': True,
                'actualizado': False,
                'terid': terid,
                'nit': nit_normalizado,
                'nombre': nombre,
                'email': email,
                'telefono': telefono,
                'tipo_documento': tipo_documento
            })
            
        except Exception as e:
            logger.error(f"Error creando tercero: {e}", exc_info=True)
            if bridge.conn:
                bridge.conn.rollback()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            bridge.close()


class BrandingViewSet(APIKeyAwareViewSet, viewsets.ViewSet):
    """
    ViewSet para gestionar branding (logo y colores) de empresas.
    Requiere autenticación (JWT o API Key) y verifica que el usuario TNS sea ADMIN.
    """
    permission_classes = [AllowAny]
    authentication_classes = [JWTOrAPIKeyAuthentication]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # Permitir multipart/form-data
    
    def _get_nit_normalizado_from_request(self, request):
        """Obtiene el NIT normalizado desde la empresa seleccionada en el request"""
        # Para GET, usar query_params; para POST/PATCH, usar data
        if request.method == 'GET':
            # Convertir QueryDict a dict normal
            data = dict(request.query_params)
            # QueryDict puede tener listas, tomar el primer valor
            data = {k: v[0] if isinstance(v, list) and len(v) > 0 else v for k, v in data.items()}
        else:
            data = request.data if hasattr(request, 'data') else {}
        
        empresa = _get_empresa_for_request(request, data)
        if not empresa:
            raise serializers.ValidationError('Empresa no encontrada o sin permisos.')
        return _normalize_nit(empresa.nit)
    
    def _check_admin_permission(self, request):
        """Verifica que el usuario TNS validado sea ADMIN"""
        # Obtener username del request (puede venir en data o headers)
        username = None
        if isinstance(request.data, dict):
            username = request.data.get('tns_username', '')
        if not username:
            username = request.headers.get('X-TNS-Username', '')
        # Si no viene en request, intentar obtenerlo de la sesión del usuario autenticado
        # (para casos donde se valida antes)
        if not username and hasattr(request, 'user') and request.user.is_authenticated:
            # Intentar obtener de session storage o de algún lugar donde se guarde
            # Por ahora, requerimos que venga explícitamente
            pass
        
        if not username or username.upper() != 'ADMIN':
            raise serializers.ValidationError('Solo usuarios ADMIN pueden gestionar branding.')
        return True
    
    @action(detail=False, methods=['get', 'put', 'patch'], url_path='empresa')
    def empresa_branding(self, request):
        """Obtiene o actualiza el branding de una empresa"""
        nit_normalizado = self._get_nit_normalizado_from_request(request)
        
        if request.method == 'GET':
            try:
                branding = EmpresaPersonalizacion.objects.get(nit_normalizado=nit_normalizado)
                serializer = EmpresaPersonalizacionSerializer(branding, context={'request': request})
                return Response(serializer.data)
            except EmpresaPersonalizacion.DoesNotExist:
                # Retornar valores por defecto si no existe
                return Response({
                    'nit_normalizado': nit_normalizado,
                    'logo': None,
                    'logo_url': None,
                    'color_primario': '#DC2626',
                    'color_secundario': '#FBBF24',
                    'color_fondo': '#f5f5f5',
                    'modo_teclado': 'auto',
                    'modo_visualizacion': 'vertical',
                    'video_por_defecto': None,
                    'video_por_defecto_url': None,
                    'video_del_dia_url': None
                })
        
        # PUT/PATCH - Actualizar
        self._check_admin_permission(request)
        
        # Normalizar request.data - MultiPartParser puede devolver listas
        normalized_data = {}
        for key, value in request.data.items():
            # Si es una lista con un solo elemento, tomar el primer elemento
            if isinstance(value, list):
                if len(value) > 0:
                    normalized_data[key] = value[0]
                else:
                    normalized_data[key] = None
            else:
                normalized_data[key] = value
        
        # El logo debe venir como archivo, no como string
        # Si viene como lista vacía o None, no incluirlo
        if 'logo' in normalized_data and (normalized_data['logo'] is None or normalized_data['logo'] == ''):
            del normalized_data['logo']
        
        try:
            branding = EmpresaPersonalizacion.objects.get(nit_normalizado=nit_normalizado)
            serializer = EmpresaPersonalizacionSerializer(
                branding, 
                data=normalized_data, 
                partial=request.method == 'PATCH',
                context={'request': request}
            )
        except EmpresaPersonalizacion.DoesNotExist:
            serializer = EmpresaPersonalizacionSerializer(
                data={**normalized_data, 'nit_normalizado': nit_normalizado},
                context={'request': request}
            )
        
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=['get', 'put', 'patch'], url_path='grupo')
    def grupo_imagen(self, request):
        """Obtiene o actualiza la imagen de un grupo de material"""
        # Para GET, usar query_params; para POST/PATCH, usar data
        if request.method == 'GET':
            data = dict(request.query_params)
            data = {k: v[0] if isinstance(v, list) and len(v) > 0 else v for k, v in data.items()}
        else:
            data = request.data if hasattr(request, 'data') else {}
        
        nit_normalizado = self._get_nit_normalizado_from_request(request)
        gm_codigo = data.get('gm_codigo') or request.query_params.get('gm_codigo') or request.data.get('gm_codigo')
        
        if not gm_codigo:
            raise serializers.ValidationError('gm_codigo es requerido')
        
        if request.method == 'GET':
            try:
                imagen = GrupoMaterialImagen.objects.get(
                    nit_normalizado=nit_normalizado,
                    gm_codigo=gm_codigo
                )
                serializer = GrupoMaterialImagenSerializer(imagen, context={'request': request})
                return Response(serializer.data)
            except GrupoMaterialImagen.DoesNotExist:
                return Response({'imagen_url': None})
        
        # PUT/PATCH - Actualizar
        self._check_admin_permission(request)
        
        # Normalizar request.data - MultiPartParser puede devolver listas
        normalized_data = {}
        for key, value in request.data.items():
            # Si es una lista con un solo elemento, tomar el primer elemento
            if isinstance(value, list):
                if len(value) > 0:
                    normalized_data[key] = value[0]
                else:
                    normalized_data[key] = None
            else:
                normalized_data[key] = value
        
        # El campo imagen debe venir como archivo, no como string
        # Si viene como lista vacía o None, no incluirlo
        if 'imagen' in normalized_data and (normalized_data['imagen'] is None or normalized_data['imagen'] == ''):
            del normalized_data['imagen']
        
        try:
            imagen = GrupoMaterialImagen.objects.get(
                nit_normalizado=nit_normalizado,
                gm_codigo=gm_codigo
            )
            serializer = GrupoMaterialImagenSerializer(
                imagen,
                data=normalized_data,
                partial=request.method == 'PATCH',
                context={'request': request}
            )
        except GrupoMaterialImagen.DoesNotExist:
            serializer = GrupoMaterialImagenSerializer(
                data={
                    **normalized_data,
                    'nit_normalizado': nit_normalizado,
                    'gm_codigo': gm_codigo
                },
                context={'request': request}
            )
        
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class EcommerceConfigViewSet(APIKeyAwareViewSet, viewsets.ViewSet):
    """
    ViewSet para gestionar la configuración del e-commerce de una empresa.
    Requiere autenticación admin.
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def _get_empresa_servidor_id_from_request(self, request):
        """Obtiene empresa_servidor_id del request (query params o data)"""
        empresa_servidor_id = request.query_params.get('empresa_servidor_id') or request.data.get('empresa_servidor_id')
        if not empresa_servidor_id:
            raise serializers.ValidationError('empresa_servidor_id es requerido')
        return int(empresa_servidor_id)
    
    def _check_admin_permission(self, request):
        """Verifica que el usuario tenga permisos de admin"""
        if not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError('Autenticación requerida.')
        if not (request.user.is_superuser or request.user.is_staff):
            raise serializers.ValidationError('Solo usuarios ADMIN pueden gestionar configuración de e-commerce.')
        return True
    
    @action(detail=False, methods=['get', 'put', 'patch'], url_path='empresa', authentication_classes=[], permission_classes=[AllowAny])
    def empresa_config(self, request):
        """
        Obtiene o actualiza la configuración del e-commerce de una empresa.
        GET: Público, no requiere autenticación.
        PUT/PATCH: Requiere validación TNS interna (username ADMIN + password).
        """
        empresa_servidor_id = self._get_empresa_servidor_id_from_request(request)
        
        if request.method == 'GET':
            try:
                config = EmpresaEcommerceConfig.objects.get(empresa_servidor_id=empresa_servidor_id)
                serializer = EmpresaEcommerceConfigSerializer(config)
                return Response(serializer.data)
            except EmpresaEcommerceConfig.DoesNotExist:
                # Retornar valores por defecto si no existe
                return Response({
                    'empresa_servidor_id': empresa_servidor_id,
                    'color_primario': '#DC2626',
                    'color_secundario': '#FBBF24',
                    'color_fondo': '#FFFFFF',
                    'usar_degradado': False,
                    'color_degradado_inicio': '#DC2626',
                    'color_degradado_fin': '#FBBF24',
                    'direccion_degradado': 'to right',
                    'hero_titulo': 'Bienvenido a nuestra tienda en línea',
                    'hero_subtitulo': 'Pedidos rápidos, sencillos y sin filas',
                    'hero_descripcion': 'Explora nuestro menú y realiza tu pedido en pocos clics.',
                    'about_titulo': 'Sobre nosotros',
                    'about_texto': 'Somos una marca enfocada en ofrecer la mejor experiencia gastronómica, con ingredientes frescos y recetas únicas.',
                    'contact_titulo': 'Contáctanos',
                    'contact_texto': 'Para más información sobre pedidos corporativos, eventos o alianzas, contáctanos a través de nuestros canales oficiales.',
                    'whatsapp_numero': None,
                                'footer_texto_logo': None,
                                'footer_links': [],
                                'footer_sections': [],
                                'menu_items': [],
                                'payment_provider': None,
                                'payment_public_key': None,
                                'payment_secret_key': None,
                                'payment_access_token': None,
                                'payment_enabled': False,
                                'payment_mode': 'test',
                                'logo_url': None,
                                'mostrar_menu': True,
                                'mostrar_hero': True,
                                'mostrar_about': True,
                                'mostrar_contact': True,
                                'mostrar_footer': True,
                                'mostrar_categorias_footer': True,
                                'estilo_tema': 'balanceado',
                })
        
        # PUT/PATCH - Actualizar (requiere validación TNS interna)
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'detail': 'username y password son requeridos para actualizar la configuración'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar que el username sea ADMIN
        if username.upper() != 'ADMIN':
            return Response(
                {'detail': 'Solo el usuario ADMIN puede actualizar la configuración'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validar credenciales TNS internamente
        try:
            empresa = EmpresaServidor.objects.get(id=empresa_servidor_id)
            bridge = TNSBridge(empresa)
            bridge.connect()
            cursor = bridge.conn.cursor()
            
            try:
                validation_row = _run_validation_procedure(cursor, username, password)
                success_raw = validation_row.get('OSUCCESS')
                success_flag = (
                    str(success_raw).strip().lower()
                    if success_raw is not None
                    else ''
                )
                is_success = success_flag in ('1', 'true', 't', 'si', 'yes')
                
                if not is_success:
                    cursor.close()
                    bridge.close()
                    return Response(
                        {'detail': 'Credenciales TNS inválidas'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            finally:
                cursor.close()
                bridge.close()
        except EmpresaServidor.DoesNotExist:
            return Response(
                {'detail': f'Empresa con ID {empresa_servidor_id} no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        except firebirdsql.Error as exc:
            return Response(
                {'detail': f'Error al validar credenciales TNS: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as exc:
            return Response(
                {'detail': f'Error inesperado: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Si la validación es exitosa, proceder con el update
        # Remover username y password del data antes de serializar
        update_data = {k: v for k, v in request.data.items() if k not in ['username', 'password']}
        
        # Asegurar que empresa_servidor_id esté en update_data
        if 'empresa_servidor_id' not in update_data:
            update_data['empresa_servidor_id'] = empresa_servidor_id
        
        try:
            config = EmpresaEcommerceConfig.objects.get(empresa_servidor_id=empresa_servidor_id)
            serializer = EmpresaEcommerceConfigSerializer(
                config,
                data=update_data,
                partial=request.method == 'PATCH',
            )
        except EmpresaEcommerceConfig.DoesNotExist:
            # Crear nueva configuración
            serializer = EmpresaEcommerceConfigSerializer(
                data=update_data,
            )
        
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=['get', 'put', 'patch'], url_path='material')
    def material_imagen(self, request):
        """Obtiene o actualiza la imagen de un material"""
        nit_normalizado = self._get_nit_normalizado_from_request(request)
        codigo_material = request.query_params.get('codigo_material') or request.query_params.get('codigo') or request.data.get('codigo_material')
        
        if not codigo_material:
            raise serializers.ValidationError('codigo_material es requerido')
        
        if request.method == 'GET':
            try:
                imagen = MaterialImagen.objects.get(
                    nit_normalizado=nit_normalizado,
                    codigo_material=codigo_material
                )
                serializer = MaterialImagenSerializer(imagen, context={'request': request})
                return Response(serializer.data)
            except MaterialImagen.DoesNotExist:
                return Response({
                    'imagen_url': None,
                    'caracteristicas': None,
                    'pdf_url': None
                })
        
        # PUT/PATCH - Actualizar
        self._check_admin_permission(request)
        
        # Normalizar request.data - MultiPartParser puede devolver listas
        normalized_data = {}
        for key, value in request.data.items():
            # Si es una lista con un solo elemento, tomar el primer elemento
            if isinstance(value, list):
                if len(value) > 0:
                    normalized_data[key] = value[0]
                else:
                    normalized_data[key] = None
            else:
                normalized_data[key] = value
        
        # El campo imagen debe venir como archivo, no como string
        # Si viene como lista vacía o None, no incluirlo
        if 'imagen' in normalized_data and (normalized_data['imagen'] is None or normalized_data['imagen'] == ''):
            del normalized_data['imagen']
        
        try:
            imagen = MaterialImagen.objects.get(
                nit_normalizado=nit_normalizado,
                codigo_material=codigo_material
            )
            serializer = MaterialImagenSerializer(
                imagen,
                data=normalized_data,
                partial=request.method == 'PATCH',
                context={'request': request}
            )
        except MaterialImagen.DoesNotExist:
            serializer = MaterialImagenSerializer(
                data={
                    **normalized_data,
                    'nit_normalizado': nit_normalizado,
                    'codigo_material': codigo_material
                },
                context={'request': request}
            )
        
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CajaAutopagoViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar cajas autopago.
    Permite CRUD de cajas, filtrando por empresa según permisos del usuario.
    """
    serializer_class = CajaAutopagoSerializer
    permission_classes = [AllowAny]  # Se valida por empresa en get_queryset
    authentication_classes = [JWTOrAPIKeyAuthentication]
    
    def get_queryset(self):
        """Filtrar cajas por empresas permitidas para el usuario"""
        qs = CajaAutopago.objects.all()
        
        # Si hay API Key, filtrar por empresas autorizadas
        if hasattr(self.request, 'empresas_autorizadas') and self.request.empresas_autorizadas:
            qs = qs.filter(empresa_servidor__in=self.request.empresas_autorizadas)
        
        # Si hay usuario autenticado, filtrar por empresas permitidas
        elif self.request.user.is_authenticated:
            empresas_permitidas = EmpresaServidor.objects.filter(
                usuarios_permitidos__usuario=self.request.user
            ).distinct()
            qs = qs.filter(empresa_servidor__in=empresas_permitidas)
        
        # Si no hay autenticación, retornar vacío
        else:
            qs = qs.none()
        
        # Filtrar por empresa_servidor_id si viene en query params
        empresa_id = self.request.query_params.get('empresa_servidor_id')
        if empresa_id:
            qs = qs.filter(empresa_servidor_id=empresa_id)
        
        return qs.select_related('empresa_servidor', 'usuario_creador')
    
    def create(self, request, *args, **kwargs):
        """
        Crear o actualizar caja autopago.
        Si ya existe una caja con el mismo nombre para la empresa, la actualiza.
        """
        empresa_servidor_id = request.data.get('empresa_servidor')
        nombre = request.data.get('nombre')
        
        if empresa_servidor_id and nombre:
            # Buscar si ya existe una caja con ese nombre para esa empresa
            try:
                caja_existente = CajaAutopago.objects.get(
                    empresa_servidor_id=empresa_servidor_id,
                    nombre=nombre
                )
                # Si existe, actualizar en lugar de crear
                serializer = self.get_serializer(caja_existente, data=request.data, partial=False)
                serializer.is_valid(raise_exception=True)
                
                # Obtener usuario TNS de la validación si existe
                tns_username = None
                if hasattr(request, 'session'):
                    validation = request.session.get('tns_validation')
                    if validation and isinstance(validation, dict):
                        tns_username = validation.get('OUSERNAME') or validation.get('username')
                
                # Si no está en session, intentar desde request data
                if not tns_username:
                    tns_username = request.data.get('usuario_tns')
                
                serializer.save(
                    usuario_creador=request.user if request.user.is_authenticated else None,
                    usuario_tns=tns_username
                )
                
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)
            except CajaAutopago.DoesNotExist:
                # No existe, proceder con creación normal
                pass
        
        # Crear nueva caja
        return super().create(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Al crear, guardar el usuario creador y el usuario TNS si está disponible"""
        # Obtener usuario TNS de la validación si existe
        tns_username = None
        if hasattr(self.request, 'session'):
            validation = self.request.session.get('tns_validation')
            if validation and isinstance(validation, dict):
                tns_username = validation.get('OUSERNAME') or validation.get('username')
        
        # Si no está en session, intentar desde sessionStorage (viene en headers o body)
        if not tns_username:
            tns_username = self.request.data.get('usuario_tns')
        
        serializer.save(
            usuario_creador=self.request.user if self.request.user.is_authenticated else None,
            usuario_tns=tns_username
        )
    
    @action(detail=False, methods=['get'], url_path='por-empresa')
    def por_empresa(self, request):
        """Obtener todas las cajas activas de una empresa específica"""
        empresa_id = request.query_params.get('empresa_servidor_id')
        if not empresa_id:
            return Response(
                {'error': 'Debes indicar empresa_servidor_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener todas las cajas (no solo activas) para que el frontend pueda elegir
        cajas = self.get_queryset().filter(
            empresa_servidor_id=empresa_id
        )
        serializer = self.get_serializer(cajas, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='formas-pago')
    def formas_pago(self, request):
        """
        Obtiene las formas de pago permitidas desde VARIOS (GFPPERMITIDASCAJAGC).
        Retorna lista de formas de pago con CODIGO y DESCRIP.
        """
        empresa_servidor_id = request.query_params.get('empresa_servidor_id')
        if not empresa_servidor_id:
            return Response(
                {'error': 'Debes indicar empresa_servidor_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = _get_empresa_for_request(request, {'empresa_servidor_id': empresa_servidor_id})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from .services.tns_bridge import TNSBridge
        bridge = TNSBridge(empresa)
        bridge.connect()
        
        try:
            cursor = bridge.conn.cursor()
            
            # 1. Obtener usuario TNS de la sesión o del request
            usuario_tns = request.query_params.get('usuario_tns') or 'ADMIN'
            
            # GFPPERMITIDASCAJAGC se compone dinámicamente: GFPPERMITIDAS + usuario_logueado
            variab_formas_pago = f"GFPPERMITIDAS{usuario_tns}"
            logger.info(f"Buscando variable de formas de pago: {variab_formas_pago}")
            
            # Obtener GFPPERMITIDASCAJAGC de VARIOS
            cursor.execute("""
                SELECT CAST(contenido AS VARCHAR(500)) 
                FROM varios 
                WHERE variab = ?
            """, (variab_formas_pago,))
            
            resultado = cursor.fetchone()
            if not resultado or not resultado[0]:
                return Response(
                    {'error': f'No se encontró configuración de formas de pago ({variab_formas_pago})'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            codigos_str = resultado[0].strip()
            # Formato: "codigo1,codigo2," (siempre termina en coma)
            # Remover la coma final si existe
            if codigos_str.endswith(','):
                codigos_str = codigos_str[:-1]
            
            # Separar códigos
            codigos = [c.strip() for c in codigos_str.split(',') if c.strip()]
            
            if not codigos:
                return Response(
                    {'error': 'No hay formas de pago configuradas'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 2. Obtener descripciones de FORMAPAGO
            placeholders = ','.join(['?' for _ in codigos])
            cursor.execute(f"""
                SELECT CODIGO, DESCRIP 
                FROM FORMAPAGO 
                WHERE CODIGO IN ({placeholders})
            """, codigos)
            
            formas_pago = []
            for row in cursor.fetchall():
                formas_pago.append({
                    'codigo': row[0],
                    'descripcion': row[1] or row[0]
                })
            
            return Response({
                'formas_pago': formas_pago
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo formas de pago: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            bridge.close()
    
    @action(detail=True, methods=['post'], url_path='procesar-pago')
    def procesar_pago(self, request, pk=None):
        """
        Procesa un pago usando la configuración de la caja.
        Si modo_mock=True, simula una respuesta según probabilidad_exito.
        Si modo_mock=False, hace una petición real al servidor local del datafono.
        """
        import requests
        import random
        
        caja = self.get_object()
        
        if not caja.activa:
            return Response(
                {'error': 'Esta caja no está activa'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener datos del pago del request
        monto = request.data.get('monto')
        referencia = request.data.get('referencia', '')
        descripcion = request.data.get('descripcion', '')
        cart_items = request.data.get('cart_items', [])  # Items del carrito
        invoice_data = request.data.get('invoice_data')  # Datos de facturación (opcional)
        order_type = request.data.get('order_type', 'takeaway')  # 'takeaway' o 'dinein'
        
        if not monto:
            return Response(
                {'error': 'Debes indicar el monto'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Modo mock: simular respuesta
        if caja.modo_mock:
            # Simular delay de 2-5 segundos
            import time
            delay = random.uniform(2, 5)
            time.sleep(delay)
            
            # Decidir éxito o fallo según probabilidad
            exito = random.random() < caja.probabilidad_exito
            
            if exito:
                # Simular respuesta exitosa
                numero_aprobacion = f"{random.randint(100000, 999999)}"
                return Response({
                    'exito': True,
                    'mensaje': 'Pago aprobado',
                    'numero_aprobacion': numero_aprobacion,
                    'referencia': referencia,
                    'monto': float(monto),
                    'modo_mock': True,
                    'tiempo_simulado': round(delay, 2)
                })
            else:
                # Simular respuesta de error
                mensajes_error = [
                    'Tarjeta rechazada',
                    'Fondos insuficientes',
                    'Tarjeta vencida',
                    'Transacción no permitida',
                    'Error de comunicación'
                ]
                return Response({
                    'exito': False,
                    'mensaje': random.choice(mensajes_error),
                    'referencia': referencia,
                    'monto': float(monto),
                    'modo_mock': True,
                    'tiempo_simulado': round(delay, 2)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Modo real: hacer petición al servidor local del datafono (Flask en puerto 8080)
        try:
            url = f"http://{caja.ip_datafono}:{caja.puerto_datafono}/api/payment"
            
            # Convertir monto a centavos (el servidor Flask espera amount en centavos)
            amount_centavos = int(float(monto) * 100)
            
            # Usar referencia como idpospal (o generar uno único si no hay)
            idpospal = referencia or f"PED-{int(time.time())}"
            
            payload = {
                'idpospal': idpospal,
                'amount': amount_centavos,
                # Si la caja tiene modo_mock pero estamos en modo real, no enviar mock_success
                # El servidor Flask usará su propio MOCK_MODE del .env
            }
            
            logger.info(f"Llamando al servidor local del datafono: {url} con payload: {payload}")
            
            # Timeout de 30 segundos
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            respuesta_flask = response.json()
            
            # Adaptar respuesta del servidor Flask al formato esperado por el frontend
            # El servidor Flask devuelve: {'success': True/False, 'codigo_respuesta': '00', ...}
            exito = respuesta_flask.get('success', False)
            codigo_respuesta = respuesta_flask.get('codigo_respuesta', '')
            
            # Respetar el mock_mode que viene del Flask (puede estar en modo mock aunque la caja diga modo_mock: false)
            # Esto es porque el Flask tiene su propio MOCK_MODE en el .env
            modo_mock_flask = respuesta_flask.get('mock_mode', False)
            
            # Construir mensaje más descriptivo
            if exito and codigo_respuesta == '00':
                mensaje = 'Pago aprobado'
                if modo_mock_flask:
                    mensaje += ' (Modo Mock - Prueba)'
                else:
                    mensaje += f'\nTarjeta: {respuesta_flask.get("franquicia", "")} {respuesta_flask.get("ultimos_digitos", "")}\nTipo: {respuesta_flask.get("tipo_cuenta", "")}'
                
                # ============================================
                # PAGO EXITOSO - El frontend llamará a crear-factura después
                # ============================================
                # El datafono solo procesa el pago. La creación de factura se hace
                # en un endpoint separado que el frontend llamará después del pago exitoso.
                
                return Response({
                    'exito': True,
                    'mensaje': mensaje,
                    'numero_aprobacion': respuesta_flask.get('codigo_autorizacion', ''),
                    'referencia': referencia,
                    'monto': float(monto),
                    'modo_mock': modo_mock_flask,
                    'franquicia': respuesta_flask.get('franquicia', ''),
                    'ultimos_digitos': respuesta_flask.get('ultimos_digitos', ''),
                    'tipo_cuenta': respuesta_flask.get('tipo_cuenta', ''),
                    'numero_recibo': respuesta_flask.get('numero_recibo', ''),
                    'rrn': respuesta_flask.get('rrn', ''),
                    'respuesta_completa': respuesta_flask
                })
            else:
                # Pago rechazado
                mensaje_error = respuesta_flask.get('medio_pago', 'Pago rechazado')
                if modo_mock_flask:
                    mensaje_error += ' (Modo Mock - Prueba)'
                
                return Response({
                    'exito': False,
                    'mensaje': mensaje_error,
                    'referencia': referencia,
                    'monto': float(monto),
                    'modo_mock': modo_mock_flask,  # Usar el mock_mode del Flask
                    'codigo_respuesta': codigo_respuesta,
                    'respuesta_completa': respuesta_flask
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except requests.exceptions.Timeout:
            return Response(
                {
                    'exito': False,
                    'mensaje': 'Timeout: El datafono no respondió a tiempo',
                    'modo_mock': False
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except requests.exceptions.ConnectionError:
            return Response(
                {
                    'exito': False,
                    'mensaje': f'No se pudo conectar al datafono en {caja.ip_datafono}:{caja.puerto_datafono}',
                    'modo_mock': False
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except requests.exceptions.RequestException as e:
            return Response(
                {
                    'exito': False,
                    'mensaje': f'Error al comunicarse con el datafono: {str(e)}',
                    'modo_mock': False
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NotaRapidaViewSet(APIKeyAwareViewSet, viewsets.ViewSet):
    """
    ViewSet para gestionar notas rápidas (opciones predefinidas para notas de productos).
    """
    authentication_classes = [JWTOrAPIKeyAuthentication]
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], url_path='list')
    def list_notas(self, request):
        """
        Lista todas las notas rápidas activas.
        Filtra por empresa_servidor_id si se proporciona.
        """
        empresa_servidor_id = request.query_params.get('empresa_servidor_id')
        activo = request.query_params.get('activo', 'true').lower() == 'true'
        categoria = request.query_params.get('categoria')  # Filtrar por categoría específica
        
        queryset = NotaRapida.objects.filter(activo=activo)
        
        # Si se proporciona categoria, filtrar notas que tengan esa categoría o que no tengan categorías (disponibles para todas)
        if categoria:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(categorias__contains=[categoria]) | Q(categorias__len=0)
            )
        
        notas = queryset.order_by('orden', 'texto').values('id', 'texto', 'categorias', 'orden', 'activo')
        
        return Response({
            'success': True,
            'data': list(notas)
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='crear')
    def crear_nota(self, request):
        """
        Crea una nueva nota rápida.
        """
        texto = request.data.get('texto')
        categorias = request.data.get('categorias', [])
        orden = request.data.get('orden', 0)
        activo = request.data.get('activo', True)
        
        if not texto:
            return Response({
                'success': False,
                'error': 'El texto es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        nota = NotaRapida.objects.create(
            texto=texto,
            categorias=categorias if isinstance(categorias, list) else [],
            orden=orden,
            activo=activo
        )
        
        return Response({
            'success': True,
            'data': {
                'id': nota.id,
                'texto': nota.texto,
                'categorias': nota.categorias,
                'orden': nota.orden,
                'activo': nota.activo
            }
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['put', 'patch'], url_path='actualizar')
    def actualizar_nota(self, request, pk=None):
        """
        Actualiza una nota rápida existente.
        """
        try:
            nota = NotaRapida.objects.get(pk=pk)
        except NotaRapida.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Nota rápida no encontrada'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if 'texto' in request.data:
            nota.texto = request.data['texto']
        if 'categorias' in request.data:
            nota.categorias = request.data['categorias'] if isinstance(request.data['categorias'], list) else []
        if 'orden' in request.data:
            nota.orden = request.data['orden']
        if 'activo' in request.data:
            nota.activo = request.data['activo']
        
        nota.save()
        
        return Response({
            'success': True,
            'data': {
                'id': nota.id,
                'texto': nota.texto,
                'categorias': nota.categorias,
                'orden': nota.orden,
                'activo': nota.activo
            }
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'], url_path='eliminar')
    def eliminar_nota(self, request, pk=None):
        """
        Elimina una nota rápida (marca como inactiva o elimina físicamente).
        """
        try:
            nota = NotaRapida.objects.get(pk=pk)
        except NotaRapida.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Nota rápida no encontrada'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Marcar como inactiva en lugar de eliminar físicamente
        nota.activo = False
        nota.save()
        
        return Response({
            'success': True,
            'message': 'Nota rápida eliminada'
        }, status=status.HTTP_200_OK)

class DianProcessorViewSet(APIKeyAwareViewSet, viewsets.ViewSet):
    """
    ViewSet para procesar facturas electrónicas DIAN de forma asíncrona.
    Usa Celery para procesamiento en background.
    """
    permission_classes = [AllowAny]
    authentication_classes = [JWTOrAPIKeyAuthentication]
    
    @action(detail=False, methods=['post'], url_path='procesar-factura')
    def procesar_factura(self, request):
        """
        Procesa una factura electrónica DIAN de forma asíncrona.
        Si mock=true, simula el envío esperando 4 segundos y retorna exitoso.
        
        Body:
        {
            "nit": "132791157",  # NIT (se normaliza automáticamente)
            "kardex_id": 12345,  # ID del documento a procesar
            "empresa_servidor_id": 192,  # Opcional, si no se proporciona se busca por NIT
            "mock": true  # Si es true, simula el envío sin procesar realmente
        }
        
        Returns (si mock=true):
        {
            "status": "SUCCESS",
            "cufe": "MOCK-12345-...",
            "mensaje": "Documento procesado exitosamente",
            "kardex_id": 12345
        }
        
        Returns (si mock=false):
        {
            "task_id": "abc-123-def-456",  # ID de la tarea Celery
            "status": "PENDING",
            "message": "Procesamiento iniciado"
        }
        """
        import time
        from datetime import datetime
        
        nit = request.data.get('nit')
        kardex_id = request.data.get('kardex_id')
        empresa_servidor_id = request.data.get('empresa_servidor_id')
        mock = request.data.get('mock', False)
        
        if not nit or not kardex_id:
            return Response(
                {'error': 'Debes indicar nit y kardex_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Normalizar NIT
        nit_normalizado = _normalize_nit(nit)
        
        # Si es mock, simular envío
        if mock:
            logger.info(f"🔄 [MOCK DIAN] Simulando envío a DIAN para kardex_id={kardex_id}")
            
            # Esperar 4 segundos
            time.sleep(4)
            
            # Generar CUFE mock
            cufe_mock = f"MOCK-{kardex_id}-{int(time.time())}"
            
            logger.info(f"✅ [MOCK DIAN] Factura {kardex_id} 'enviada' a DIAN (Mock)")
            
            # Retornar formato similar al de tasks.py cuando es exitoso
            return Response({
                'status': 'SUCCESS',
                'cufe': cufe_mock,
                'mensaje': 'Documento procesado exitosamente',
                'kardex_id': kardex_id,
                'fecha_envio': datetime.now().isoformat()
            })
        
        # Si no es mock, ejecutar proceso real con Celery
        from .tasks import procesar_factura_dian_task
        
        task = procesar_factura_dian_task.delay(
            nit_normalizado=nit_normalizado,
            kardex_id=kardex_id,
            empresa_servidor_id=empresa_servidor_id
        )
        
        logger.info(f"Tarea Celery iniciada: {task.id} para NIT={nit_normalizado}, KardexID={kardex_id}")
        
        return Response({
            'task_id': task.id,
            'status': 'PENDING',
            'message': 'Procesamiento de factura iniciado. Usa el task_id para consultar el estado.',
            'nit': nit_normalizado,
            'kardex_id': kardex_id
        })
    
    @action(detail=False, methods=['post'], url_path='crear-factura')
    def crear_factura(self, request):
        """
        Crea una factura en TNS después de un pago exitoso.
        Este endpoint se llama desde el frontend después de que el datafono procesa el pago.
        
        Body:
        {
            "empresa_servidor_id": 192,
            "cart_items": [
                {"id": "CODIGO1", "name": "Producto 1", "price": 1000, "quantity": 2},
                ...
            ],
            "monto_total": 3000,
            "invoice_data": {
                "docType": "cedula" | "nit",
                "document": "1234567890",
                "name": "Nombre Completo",
                "email": "email@example.com",
                "phone": "3001234567"
            },
            "order_type": "takeaway" | "dinein",
            "referencia": "PED-1234567890",
            "forma_pago_codigo": "EF",  # Código de forma de pago
            "mesa_number": "5",  # Opcional, solo si es dinein
            "observacion": "PARA LLEVAR - TEL: 3001234567",  # Observación construida
            "usuario_tns": "CAJAGC",  # Usuario TNS logueado
            "medio_pago_data": {  # Datos del datafono (opcional)
                "codigo_autorizacion": "123456",
                "franquicia": "VISA",
                "ultimos_digitos": "1234",
                "tipo_cuenta": "CREDITO",
                "numero_recibo": "12345",
                "rrn": "123456789"
            }
        }
        
        Returns:
        {
            "success": true,
            "kardex_id": 12345,
            "prefijo": "FV",
            "numero": "12345",
            "nit_normalizado": "1234567890",
            "task_id_dian": "abc-123-def-456"  # ID de tarea Celery para DIAN
        }
        """
        from .services.tns_invoice_helper import insertar_factura_tns
        from .services.tns_bridge import TNSBridge
        from .tasks import procesar_factura_dian_task
        
        empresa_servidor_id = request.data.get('empresa_servidor_id')
        empresa_nombre = request.data.get('empresa_nombre', '')
        empresa_nit = request.data.get('empresa_nit', '')
        cart_items = request.data.get('cart_items', [])
        monto_total = request.data.get('monto_total')
        invoice_data = request.data.get('invoice_data')
        order_type = request.data.get('order_type', 'takeaway')
        referencia = request.data.get('referencia', '')
        forma_pago_codigo = request.data.get('forma_pago_codigo')
        mesa_number = request.data.get('mesa_number')
        observacion = request.data.get('observacion')
        usuario_tns = request.data.get('usuario_tns', 'ADMIN')
        medio_pago_data = request.data.get('medio_pago_data', {})
        
        if not empresa_servidor_id:
            return Response(
                {'error': 'Debes indicar empresa_servidor_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not cart_items or len(cart_items) == 0:
            return Response(
                {'error': 'Debes indicar cart_items'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not monto_total:
            return Response(
                {'error': 'Debes indicar monto_total'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = EmpresaServidor.objects.get(id=empresa_servidor_id)
        except EmpresaServidor.DoesNotExist:
            return Response(
                {'error': f'Empresa con ID {empresa_servidor_id} no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            logger.info("=" * 80)
            logger.info("🔄 CREANDO FACTURA EN TNS DESPUÉS DEL PAGO EXITOSO")
            logger.info(f"   Empresa ID: {empresa.id}")
            logger.info(f"   Usuario TNS: {usuario_tns}")
            logger.info(f"   Monto: {monto_total}")
            logger.info(f"   Items: {len(cart_items)}")
            logger.info(f"   Invoice Data: {invoice_data}")
            logger.info(f"   Forma Pago: {forma_pago_codigo}")
            logger.info(f"   Mesa: {mesa_number}")
            logger.info(f"   Observación: {observacion}")
            logger.info("=" * 80)
            
            # Conectar a TNS
            bridge = TNSBridge(empresa)
            
            # Insertar factura en TNS
            resultado_insercion = insertar_factura_tns(
                bridge=bridge,
                cart_items=cart_items,
                monto_total=float(monto_total),
                empresa_servidor_id=empresa.id,
                invoice_data=invoice_data,
                order_type=order_type,
                referencia=referencia,
                medio_pago_data=medio_pago_data,
                forma_pago_codigo=forma_pago_codigo,
                mesa_number=mesa_number,
                observacion=observacion,
                usuario_tns=usuario_tns
            )
            
            bridge.close()
            
            logger.info("=" * 80)
            logger.info("📊 RESULTADO DE INSERCIÓN EN TNS")
            logger.info(f"   Success: {resultado_insercion.get('success')}")
            logger.info(f"   Resultado completo: {resultado_insercion}")
            logger.info("=" * 80)
            
            if resultado_insercion.get('success'):
                # NO procesar DIAN aquí - el frontend lo hará después
                # Solo retornar el kardex_id para que el frontend continúe
                kardex_id = resultado_insercion['kardex_id']
                nit_normalizado = resultado_insercion['nit_normalizado']
                
                logger.info(f"✅ Factura insertada exitosamente en TNS")
                logger.info(f"   KARDEXID: {kardex_id}")
                logger.info(f"   NIT Normalizado: {nit_normalizado}")
                
                # Iniciar tarea DIAN
                task_id_dian = None
                try:
                    task = procesar_factura_dian_task.delay(
                        nit_normalizado=nit_normalizado,
                        kardex_id=kardex_id,
                        empresa_servidor_id=empresa.id
                    )
                    task_id_dian = task.id
                    logger.info(f"✅ Tarea DIAN iniciada: {task_id_dian}")
                except Exception as e:
                    logger.error(f"❌ Error al iniciar tarea DIAN: {e}", exc_info=True)
                
                return Response({
                    'success': True,
                    'kardex_id': kardex_id,
                    'prefijo': resultado_insercion.get('prefijo'),
                    'numero': resultado_insercion.get('numero'),
                    'nit_normalizado': nit_normalizado,
                    'task_id_dian': task_id_dian,
                    'observacion': resultado_insercion.get('observacion')
                })
            else:
                error_msg = resultado_insercion.get('error', 'Error desconocido')
                logger.error(f"❌ Error al insertar factura en TNS: {error_msg}")
                logger.error(f"   Detalles completos: {resultado_insercion}")
                
                # ⚠️ PAGO EXITOSO PERO FALLO LA INSERCIÓN: Generar ticket de error e imprimir
                try:
                    from .services.pdf_helper import generar_ticket_error_pdf
                    from .models import CajaAutopago
                    import requests
                    from django.core.files.uploadedfile import SimpleUploadedFile
                    
                    logger.warning("⚠️ Generando ticket de error porque el pago fue exitoso pero falló la inserción en TNS")
                    
                    # Obtener datos de la empresa
                    empresa_nit = empresa.nit
                    empresa_nombre = empresa.nombre
                    empresa_direccion = ""  # Se puede obtener de TNS si es necesario
                    empresa_telefono = ""  # Se puede obtener de TNS si es necesario
                    empresa_email = ""  # Se puede obtener de TNS si es necesario
                    
                    # Generar ticket de error
                    pdf_buffer = generar_ticket_error_pdf(
                        empresa_nit=empresa_nit,
                        empresa_nombre=empresa_nombre,
                        empresa_direccion=empresa_direccion,
                        empresa_telefono=empresa_telefono,
                        empresa_email=empresa_email,
                        monto_total=float(monto_total),
                        cart_items=cart_items,
                        error_message=error_msg[:200],  # Limitar longitud
                        referencia_pago=referencia or 'SIN-REF',
                        medio_pago_data=medio_pago_data,
                        invoice_data=invoice_data,  # Datos del cliente
                        observacion=observacion,  # Observaciones del pedido
                        fecha=datetime.now().strftime("%Y-%m-%d"),
                        hora=datetime.now().strftime("%H:%M:%S")
                    )
                    
                    if pdf_buffer:
                        # Obtener IP y puerto del servidor Flask desde CajaAutopago
                        caja = CajaAutopago.objects.filter(empresa_servidor_id=empresa.id).first()
                        if caja and caja.ip_datafono and caja.puerto_datafono:
                            flask_url = f"http://{caja.ip_datafono}:{caja.puerto_datafono}/api/invoice/print-short"
                            
                            # Enviar PDF al servidor Flask para imprimir
                            pdf_buffer.seek(0)
                            files = {
                                'pdf': ('ticket_error.pdf', pdf_buffer.read(), 'application/pdf')
                            }
                            data = {
                                'kardex_id': 'ERROR',
                                'empresa_servidor_id': str(empresa.id)
                            }
                            
                            try:
                                response = requests.post(flask_url, files=files, data=data, timeout=10)
                                if response.status_code == 200:
                                    logger.info("✅ Ticket de error enviado a impresión exitosamente")
                                else:
                                    logger.warning(f"⚠️ Error al enviar ticket de error a impresión: {response.status_code} - {response.text}")
                            except Exception as e:
                                logger.error(f"❌ Error al enviar ticket de error a impresión: {e}", exc_info=True)
                        else:
                            logger.warning("⚠️ No se encontró configuración de servidor Flask para imprimir ticket de error")
                    else:
                        logger.error("❌ No se pudo generar el PDF del ticket de error")
                        
                except Exception as e:
                    logger.error(f"❌ Error al generar/imprimir ticket de error: {e}", exc_info=True)
                    # No fallar la respuesta por esto, solo loguear
                
                return Response(
                    {
                        'success': False,
                        'error': error_msg,
                        'detalles': resultado_insercion,
                        'ticket_error_generado': pdf_buffer is not None if 'pdf_buffer' in locals() else False
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        except Exception as e:
            logger.error(f"❌ Error general al crear factura: {e}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='estado-tarea')
    def estado_tarea(self, request):
        """
        Consulta el estado de una tarea Celery.
        
        Query params:
        - task_id: ID de la tarea Celery
        
        Returns:
        {
            "task_id": "abc-123-def-456",
            "status": "SUCCESS|FAILED|PENDING|PROCESSING|ERROR",
            "result": {...}  # Solo si está completada
        }
        """
        from celery.result import AsyncResult
        
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response(
                {'error': 'Debes indicar task_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task_result = AsyncResult(task_id)
        
        response_data = {
            'task_id': task_id,
            'status': task_result.state
        }
        
        if task_result.ready():
            if task_result.successful():
                response_data['result'] = task_result.result
                response_data['status'] = task_result.result.get('status', 'SUCCESS') if isinstance(task_result.result, dict) else 'SUCCESS'
            else:
                response_data['error'] = str(task_result.info)
                response_data['status'] = 'ERROR'
        elif task_result.state == 'PROCESSING':
            response_data['meta'] = task_result.info if isinstance(task_result.info, dict) else {}
        
        return Response(response_data)
    
    @action(detail=False, methods=['post'], url_path='generar-pdf-completo')
    def generar_pdf_completo(self, request):
        """
        Genera PDF de factura completa consultando TNS directamente.
        Django tiene acceso directo a TNS, así que no necesita llamar al Flask.
        
        Body:
        {
            "kardex_id": 12345,
            "empresa_servidor_id": 192
        }
        
        Returns:
            PDF binario
        """
        from django.http import HttpResponse
        from io import BytesIO
        
        kardex_id = request.data.get('kardex_id')
        empresa_servidor_id = request.data.get('empresa_servidor_id')
        empresa_nombre = request.data.get('empresa_nombre', '')
        empresa_nit = request.data.get('empresa_nit', '')
        
        if not kardex_id or not empresa_servidor_id:
            return Response(
                {'error': 'Debes indicar kardex_id y empresa_servidor_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = EmpresaServidor.objects.get(id=empresa_servidor_id)
        except EmpresaServidor.DoesNotExist:
            return Response(
                {'error': f'Empresa con ID {empresa_servidor_id} no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Obtener configuración de la caja para saber la IP del Flask
        caja = CajaAutopago.objects.filter(
            empresa_servidor_id=empresa_servidor_id,
            activa=True
        ).first()
        
        if not caja:
            return Response(
                {'error': 'No hay caja activa configurada para esta empresa'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Consultar datos de la factura desde TNS y generar PDF directamente
        from .services.pdf_helper import consultar_datos_factura_para_pdf, generar_pdf_factura_completa
        from .services.tns_bridge import TNSBridge
        
        bridge = TNSBridge(empresa)
        bridge.connect()
        
        try:
            factura_data = consultar_datos_factura_para_pdf(bridge, kardex_id)
            
            if not factura_data:
                return Response(
                    {'error': 'No se pudieron obtener los datos de la factura desde TNS'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Usar datos de empresa del frontend si están disponibles
            if empresa_nombre:
                factura_data['empresa_nombre'] = empresa_nombre
            if empresa_nit:
                factura_data['empresa_nit'] = empresa_nit
            
            # Obtener logo de la empresa desde EmpresaPersonalizacion usando NIT normalizado
            logo_base64 = None
            try:
                from .models import EmpresaPersonalizacion
                # Usar la misma función de normalización que se usa al guardar el logo
                nit_normalizado = _normalize_nit(empresa_nit) if empresa_nit else ''
                if nit_normalizado:
                    personalizacion = EmpresaPersonalizacion.objects.filter(nit_normalizado=nit_normalizado).first()
                    if personalizacion and personalizacion.logo:
                        logo_base64 = base64.b64encode(personalizacion.logo.read()).decode('utf-8')
                        logger.info(f"✅ Logo obtenido desde EmpresaPersonalizacion para NIT normalizado: {nit_normalizado}")
                    else:
                        logger.info(f"⚠️ No se encontró logo en EmpresaPersonalizacion para NIT normalizado: {nit_normalizado}")
            except Exception as e:
                logger.warning(f"No se pudo obtener logo: {e}", exc_info=True)
                pass
            
            # Generar PDF directamente en Django
            pdf_buffer = generar_pdf_factura_completa(factura_data, logo_base64)
            
            if not pdf_buffer:
                return Response(
                    {'error': 'Error generando PDF'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Retornar el PDF directamente
            response = HttpResponse(
                pdf_buffer.read(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'inline; filename="factura_{factura_data.get("prefijo", "FV")}-{factura_data.get("numero", kardex_id)}.pdf"'
            return response
            
        except Exception as e:
            logger.error(f"Error generando PDF: {e}", exc_info=True)
            return Response(
                {'error': f'Error generando PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            bridge.close()
    
    @action(detail=False, methods=['post'], url_path='generar-pdf-corto')
    def generar_pdf_corto(self, request):
        """
        Genera PDF de ticket corto consultando TNS directamente.
        
        Body:
        {
            "kardex_id": 12345,
            "empresa_servidor_id": 192
        }
        
        Returns:
            PDF binario
        """
        from django.http import HttpResponse
        import requests
        
        kardex_id = request.data.get('kardex_id')
        empresa_servidor_id = request.data.get('empresa_servidor_id')
        empresa_nombre = request.data.get('empresa_nombre', '')
        empresa_nit = request.data.get('empresa_nit', '')
        
        if not kardex_id or not empresa_servidor_id:
            return Response(
                {'error': 'Debes indicar kardex_id y empresa_servidor_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = EmpresaServidor.objects.get(id=empresa_servidor_id)
        except EmpresaServidor.DoesNotExist:
            return Response(
                {'error': f'Empresa con ID {empresa_servidor_id} no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Obtener configuración de la caja para saber la IP del Flask
        caja = CajaAutopago.objects.filter(
            empresa_servidor_id=empresa_servidor_id,
            activa=True
        ).first()
        
        if not caja:
            return Response(
                {'error': 'No hay caja activa configurada para esta empresa'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Consultar datos de la factura desde TNS y generar PDF directamente
        from .services.pdf_helper import consultar_datos_factura_para_pdf, generar_pdf_ticket_corto
        from .services.tns_bridge import TNSBridge
        
        bridge = TNSBridge(empresa)
        bridge.connect()
        
        try:
            factura_data = consultar_datos_factura_para_pdf(bridge, kardex_id)
            
            if not factura_data:
                return Response(
                    {'error': 'No se pudieron obtener los datos de la factura desde TNS'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Usar datos de empresa del frontend si están disponibles
            if empresa_nombre:
                factura_data['empresa_nombre'] = empresa_nombre
            if empresa_nit:
                factura_data['empresa_nit'] = empresa_nit
            
            # Obtener logo de la empresa desde EmpresaPersonalizacion usando NIT normalizado
            logo_base64 = None
            try:
                from .models import EmpresaPersonalizacion
                # Usar la misma función de normalización que se usa al guardar el logo
                nit_normalizado = _normalize_nit(empresa_nit) if empresa_nit else ''
                if nit_normalizado:
                    personalizacion = EmpresaPersonalizacion.objects.filter(nit_normalizado=nit_normalizado).first()
                    if personalizacion and personalizacion.logo:
                        logo_base64 = base64.b64encode(personalizacion.logo.read()).decode('utf-8')
                        logger.info(f"✅ Logo obtenido desde EmpresaPersonalizacion para NIT normalizado: {nit_normalizado}")
                    else:
                        logger.info(f"⚠️ No se encontró logo en EmpresaPersonalizacion para NIT normalizado: {nit_normalizado}")
            except Exception as e:
                logger.warning(f"No se pudo obtener logo: {e}", exc_info=True)
                pass
            
            # Generar PDF directamente en Django
            pdf_buffer = generar_pdf_ticket_corto(factura_data, logo_base64)
            
            if not pdf_buffer:
                return Response(
                    {'error': 'Error generando PDF'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Retornar el PDF directamente
            response = HttpResponse(
                pdf_buffer.read(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'inline; filename="ticket_{factura_data.get("prefijo", "FV")}-{factura_data.get("numero", kardex_id)}.pdf"'
            return response
            
        except Exception as e:
            logger.error(f"Error generando PDF: {e}", exc_info=True)
            return Response(
                {'error': f'Error generando PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            bridge.close()
# ViewSet para VPN - Agregar al final de views.py

class VpnConfigViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar configuraciones VPN (WireGuard).
    Permite crear, listar, activar/desactivar y descargar configuraciones de túneles VPN.
    """
    queryset = VpnConfig.objects.all()
    serializer_class = VpnConfigSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        """
        Crea una nueva configuración VPN.
        Genera claves, asigna IP y crea el archivo .conf.
        """
        from .services.wireguard_manager import WireGuardManager
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        nombre = serializer.validated_data.get('nombre')
        ip_address = serializer.validated_data.get('ip_address')
        activo = serializer.validated_data.get('activo', True)
        notas = serializer.validated_data.get('notas', '')
        
        try:
            wg_manager = WireGuardManager()
            
            # Crear cliente
            client_data = wg_manager.create_client(
                nombre=nombre,
                ip_address=ip_address
            )
            
            # Crear registro en BD
            vpn_config = VpnConfig.objects.create(
                nombre=nombre,
                ip_address=client_data['ip_address'],
                public_key=client_data['public_key'],
                private_key=client_data['private_key'],
                config_file_path=client_data['config_file_path'],
                activo=activo,
                notas=notas
            )
            
            response_serializer = self.get_serializer(vpn_config)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creando configuración VPN: {e}", exc_info=True)
            return Response(
                {'error': f'Error creando configuración VPN: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='download')
    def download_config(self, request, pk=None):
        """
        Descarga el archivo .conf de una configuración VPN.
        SIEMPRE regenera el config para asegurar que la clave pública del servidor esté actualizada.
        """
        try:
            vpn_config = self.get_object()
            
            from pathlib import Path
            from .services.wireguard_manager import WireGuardManager
            wg_manager = WireGuardManager()
            
            # SIEMPRE regenerar el config para asegurar que la clave pública esté correcta
            config_content = None
            
            # Si no hay private_key (peer sincronizado), generar template
            if not vpn_config.private_key:
                # Obtener clave pública del servidor usando el método mejorado
                server_public_key = wg_manager._get_server_public_key()
                
                # Validar que la clave no sea el placeholder
                if server_public_key == "REEMPLAZAR_CON_CLAVE_PUBLICA_DEL_SERVIDOR":
                    logger.error(f"No se pudo obtener la clave pública del servidor para {vpn_config.nombre}")
                    return Response(
                        {'error': 'No se pudo obtener la clave pública del servidor. Verifica la configuración de WireGuard.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                # Detectar red base y puerto
                base_network = wg_manager.server_ip.rsplit('.', 1)[0] if wg_manager.server_ip else "10.8.3"
                listen_port = 51830 if base_network == "10.8.3" else wg_manager.server_port
                server_ip = wg_manager.server_ip or '10.8.3.1'
                
                config_content = f"""# Configuración WireGuard para {vpn_config.nombre}
# Generado automáticamente por EDDESO
# NOTA: Este peer fue importado desde el servidor. Necesitas agregar tu PrivateKey manualmente.
# La PrivateKey debe ser la misma que usaste para generar la PublicKey: {vpn_config.public_key}

[Interface]
PrivateKey = TU_CLAVE_PRIVADA_AQUI
ListenPort = {listen_port}
Address = {vpn_config.ip_address or '10.8.3.X'}/24
DNS = 1.1.1.1
MTU = 1420

[Peer]
PublicKey = {server_public_key}
AllowedIPs = {server_ip}/32
Endpoint = {wg_manager.server_endpoint or 'TU_SERVIDOR:51820'}
PersistentKeepalive = 25
"""
            else:
                # Generar configuración completa con private_key
                # Obtener clave pública del servidor primero para validar
                server_public_key = wg_manager._get_server_public_key()
                if server_public_key == "REEMPLAZAR_CON_CLAVE_PUBLICA_DEL_SERVIDOR":
                    logger.error(f"No se pudo obtener la clave pública del servidor para {vpn_config.nombre}")
                    return Response(
                        {'error': 'No se pudo obtener la clave pública del servidor. Verifica la configuración de WireGuard.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                # Generar config pasando la clave pública del servidor explícitamente
                config_content = wg_manager.create_client_config(
                    client_name=vpn_config.nombre,
                    client_private_key=vpn_config.private_key,
                    client_public_key=vpn_config.public_key,
                    client_ip=vpn_config.ip_address or '10.8.3.X',
                    server_public_key=server_public_key  # Pasar explícitamente
                )
                
                # Asegurar que la clave pública del servidor en el config sea la correcta
                # Reemplazar si está el placeholder (por si acaso)
                if 'PublicKey = REEMPLAZAR_CON_CLAVE_PUBLICA_DEL_SERVIDOR' in config_content:
                    config_content = config_content.replace(
                        'PublicKey = REEMPLAZAR_CON_CLAVE_PUBLICA_DEL_SERVIDOR',
                        f'PublicKey = {server_public_key}'
                    )
            
            # Guardar archivo generado
            config_path = Path(wg_manager.save_config_file(vpn_config.nombre, config_content))
            vpn_config.config_file_path = str(config_path)
            vpn_config.save()
            
            # Crear ZIP con config + scripts PowerShell
            import zipfile
            import io
            
            zip_buffer = io.BytesIO()
            safe_name = "".join(c for c in vpn_config.nombre if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Agregar config
                zip_file.writestr(f"{safe_name}.conf", config_content)
                
                # Script 1: Abrir puerto 3050
                script_abrir = f"""# Script para abrir puerto 3050 (Firebird) para acceso desde VPS 10.8.3.1
# Ejecutar como Administrador

Write-Host "Abriendo puerto 3050 para acceso desde 10.8.3.1..." -ForegroundColor Green

# Verificar si la regla ya existe
$reglaExistente = Get-NetFirewallRule -DisplayName "Firebird 3050 - VPS 10.8.3.1" -ErrorAction SilentlyContinue

if ($reglaExistente) {{
    Write-Host "La regla ya existe. Eliminando para recrearla..." -ForegroundColor Yellow
    Remove-NetFirewallRule -DisplayName "Firebird 3050 - VPS 10.8.3.1"
}}

# Crear regla de firewall para permitir acceso desde 10.8.3.1
New-NetFirewallRule -DisplayName "Firebird 3050 - VPS 10.8.3.1" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 3050 `
    -RemoteAddress 10.8.3.1 `
    -Action Allow `
    -Profile Any

Write-Host "`nRegla de firewall creada exitosamente!" -ForegroundColor Green
Write-Host "Puerto 3050 ahora acepta conexiones desde 10.8.3.1" -ForegroundColor Green

# Verificar que Firebird está escuchando
Write-Host "`nVerificando que Firebird está escuchando en el puerto 3050..." -ForegroundColor Cyan
$firebirdListening = Get-NetTCPConnection -LocalPort 3050 -State Listen -ErrorAction SilentlyContinue

if ($firebirdListening) {{
    Write-Host "Firebird está escuchando en el puerto 3050" -ForegroundColor Green
    Write-Host "Dirección: $($firebirdListening.LocalAddress)" -ForegroundColor Cyan
}} else {{
    Write-Host "ADVERTENCIA: Firebird NO está escuchando en el puerto 3050" -ForegroundColor Yellow
    Write-Host "Verifica que el servicio Firebird esté ejecutándose" -ForegroundColor Yellow
}}

Write-Host "`nListo! El VPS (10.8.3.1) ahora puede conectarse al puerto 3050" -ForegroundColor Green
"""
                zip_file.writestr("abrir_puerto_3050_para_vps.ps1", script_abrir)
                
                # Script 2: Verificar puerto 3050
                script_verificar = f"""# Script para verificar configuración del puerto 3050
# Ejecutar como Administrador

Write-Host "=== Verificación Puerto 3050 (Firebird) ===" -ForegroundColor Cyan

# Verificar reglas de firewall
Write-Host "`n1. Reglas de Firewall para puerto 3050:" -ForegroundColor Yellow
$reglas = Get-NetFirewallRule | Where-Object {{ $_.DisplayName -like "*3050*" -or $_.DisplayName -like "*Firebird*" }}
if ($reglas) {{
    $reglas | ForEach-Object {{
        Write-Host "  - $($_.DisplayName): $($_.Enabled) - $($_.Direction) - $($_.Action)" -ForegroundColor Green
        $addressFilter = Get-NetFirewallAddressFilter -AssociatedNetFirewallRule $_
        if ($addressFilter.RemoteAddress) {{
            Write-Host "    RemoteAddress: $($addressFilter.RemoteAddress)" -ForegroundColor Cyan
        }}
    }}
}} else {{
    Write-Host "  No se encontraron reglas específicas para 3050" -ForegroundColor Yellow
}}

# Verificar conexiones activas
Write-Host "`n2. Conexiones en puerto 3050:" -ForegroundColor Yellow
$conexiones = Get-NetTCPConnection -LocalPort 3050 -ErrorAction SilentlyContinue
if ($conexiones) {{
    $conexiones | ForEach-Object {{
        Write-Host "  - Estado: $($_.State) | Local: $($_.LocalAddress):$($_.LocalPort) | Remote: $($_.RemoteAddress):$($_.RemotePort)" -ForegroundColor Green
    }}
}} else {{
    Write-Host "  No hay conexiones activas en el puerto 3050" -ForegroundColor Yellow
}}

# Verificar si Firebird está escuchando
Write-Host "`n3. Firebird escuchando:" -ForegroundColor Yellow
$listening = Get-NetTCPConnection -LocalPort 3050 -State Listen -ErrorAction SilentlyContinue
if ($listening) {{
    Write-Host "  Firebird está escuchando en:" -ForegroundColor Green
    $listening | ForEach-Object {{
        Write-Host "    - $($_.LocalAddress):$($_.LocalPort)" -ForegroundColor Cyan
    }}
}} else {{
    Write-Host "  Firebird NO está escuchando en el puerto 3050" -ForegroundColor Red
    Write-Host "  Verifica que el servicio Firebird esté ejecutándose" -ForegroundColor Yellow
}}

# Verificar servicios Firebird
Write-Host "`n4. Servicios Firebird:" -ForegroundColor Yellow
$servicios = Get-Service | Where-Object {{ $_.DisplayName -like "*Firebird*" }}
if ($servicios) {{
    $servicios | ForEach-Object {{
        $status = if ($_.Status -eq "Running") {{ "Running" }} else {{ "Stopped" }}
        $color = if ($_.Status -eq "Running") {{ "Green" }} else {{ "Red" }}
        Write-Host "  - $($_.DisplayName): $status" -ForegroundColor $color
    }}
}} else {{
    Write-Host "  No se encontraron servicios Firebird" -ForegroundColor Yellow
}}

Write-Host "`n=== Fin de verificación ===" -ForegroundColor Cyan
"""
                zip_file.writestr("verificar_puerto_3050.ps1", script_verificar)
            
            zip_buffer.seek(0)
            
            # Retornar ZIP
            from django.http import HttpResponse
            response = HttpResponse(zip_buffer.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="vpn-{safe_name}.zip"'
            return response
            
        except Exception as e:
            logger.error(f"Error descargando configuración VPN: {e}", exc_info=True)
            return Response(
                {'error': f'Error descargando configuración: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='read-config')
    def read_config(self, request, pk=None):
        """
        Lee el contenido del archivo .conf actual sin descargarlo.
        Útil para verificar el contenido antes de descargar.
        """
        try:
            vpn_config = self.get_object()
            
            from pathlib import Path
            
            config_content = None
            
            # Intentar leer archivo existente
            if vpn_config.config_file_path:
                config_path = Path(vpn_config.config_file_path)
                if config_path.exists():
                    config_content = config_path.read_text()
            
            if not config_content:
                # Si no existe, generar uno nuevo (igual que download)
                from .services.wireguard_manager import WireGuardManager
                wg_manager = WireGuardManager()
                
                if not vpn_config.private_key:
                    server_public_key = wg_manager._get_server_public_key()
                    # Detectar red base y puerto
                    base_network = wg_manager.server_ip.rsplit('.', 1)[0] if wg_manager.server_ip else "10.8.3"
                    listen_port = 51830 if base_network == "10.8.3" else wg_manager.server_port
                    server_ip = wg_manager.server_ip or '10.8.3.1'
                    
                    config_content = f"""# Configuración WireGuard para {vpn_config.nombre}
# Generado automáticamente por EDDESO

[Interface]
PrivateKey = TU_CLAVE_PRIVADA_AQUI
ListenPort = {listen_port}
Address = {vpn_config.ip_address or '10.8.3.X'}/24
DNS = 1.1.1.1
MTU = 1420

[Peer]
PublicKey = {server_public_key}
AllowedIPs = {server_ip}/32
Endpoint = {wg_manager.server_endpoint or 'TU_SERVIDOR:51820'}
PersistentKeepalive = 25
"""
                else:
                    config_content = wg_manager.create_client_config(
                        client_name=vpn_config.nombre,
                        client_private_key=vpn_config.private_key,
                        client_public_key=vpn_config.public_key,
                        client_ip=vpn_config.ip_address or '10.8.3.X'
                    )
            
            return Response({
                'config_content': config_content,
                'config_file_path': vpn_config.config_file_path,
                'has_private_key': bool(vpn_config.private_key)
            })
            
        except Exception as e:
            logger.error(f"Error leyendo configuración VPN: {e}", exc_info=True)
            return Response(
                {'error': f'Error leyendo configuración: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='delete-config')
    def delete_config(self, request, pk=None):
        """
        Elimina el archivo .conf de una configuración VPN.
        No elimina el registro, solo el archivo.
        """
        try:
            vpn_config = self.get_object()
            
            from pathlib import Path
            
            deleted = False
            if vpn_config.config_file_path:
                config_path = Path(vpn_config.config_file_path)
                if config_path.exists():
                    config_path.unlink()
                    deleted = True
            
            # Limpiar la ruta del archivo en la BD
            vpn_config.config_file_path = None
            vpn_config.save()
            
            return Response({
                'deleted': deleted,
                'message': 'Archivo de configuración eliminado exitosamente' if deleted else 'No había archivo para eliminar'
            })
            
        except Exception as e:
            logger.error(f"Error eliminando configuración VPN: {e}", exc_info=True)
            return Response(
                {'error': f'Error eliminando configuración: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """
        Actualiza una configuración VPN (principalmente para activar/desactivar).
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Si se está activando/desactivando, actualizar en el servidor WireGuard
        if 'activo' in serializer.validated_data:
            activo = serializer.validated_data['activo']
            from .services.wireguard_manager import WireGuardManager
            wg_manager = WireGuardManager()
            
            if activo and not instance.activo:
                # Activar: agregar peer al servidor
                wg_manager.add_peer_to_server(instance.public_key, instance.ip_address)
            elif not activo and instance.activo:
                # Desactivar: remover peer del servidor
                wg_manager.remove_peer_from_server(instance.public_key)
        
        self.perform_update(serializer)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Elimina una configuración VPN y remueve el peer del servidor.
        """
        instance = self.get_object()
        
        try:
            # Remover peer del servidor
            from .services.wireguard_manager import WireGuardManager
            wg_manager = WireGuardManager()
            wg_manager.remove_peer_from_server(instance.public_key)
        except Exception as e:
            logger.warning(f"No se pudo remover peer del servidor: {e}")
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'], url_path='server-status')
    def server_status(self, request):
        """
        Obtiene el estado del servidor WireGuard.
        """
        from .services.wireguard_manager import WireGuardManager
        wg_manager = WireGuardManager()
        status_data = wg_manager.get_server_status()
        return Response(status_data)
    
    @action(detail=False, methods=['post'], url_path='sync-peers')
    def sync_peers(self, request):
        """
        Sincroniza los peers existentes en el servidor WireGuard con la base de datos.
        Crea registros VpnConfig para peers que existen en el servidor pero no en la BD.
        """
        from .services.wireguard_manager import WireGuardManager
        wg_manager = WireGuardManager()
        sync_result = wg_manager.sync_existing_peers()
        
        if 'error' in sync_result:
            return Response(
                {'error': sync_result['error']},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': f'Sincronización completada',
            'created': sync_result['created'],
            'existing': sync_result['existing'],
            'total_peers': sync_result['total_peers']
        })
    
    @action(detail=False, methods=['get'], url_path='peer-stats')
    def peer_stats(self, request):
        """
        Obtiene estadísticas detalladas de todos los peers (tráfico, conexión, etc.)
        """
        from .services.wireguard_manager import WireGuardManager
        wg_manager = WireGuardManager()
        stats = wg_manager.get_peer_stats()
        
        # Enriquecer con información de la BD (nombres, etc.)
        if stats.get('peers'):
            for peer in stats['peers']:
                try:
                    vpn_config = VpnConfig.objects.get(public_key=peer['public_key'])
                    peer['nombre'] = vpn_config.nombre
                    peer['id'] = vpn_config.id
                    peer['activo'] = vpn_config.activo
                    peer['fecha_creacion'] = vpn_config.fecha_creacion
                except VpnConfig.DoesNotExist:
                    peer['nombre'] = 'Desconocido'
                    peer['id'] = None
                    peer['activo'] = False
        
        return Response(stats)
    
    @action(detail=True, methods=['get'], url_path='stats')
    def peer_detail_stats(self, request, pk=None):
        """
        Obtiene estadísticas detalladas de un peer específico.
        """
        vpn_config = self.get_object()
        
        from .services.wireguard_manager import WireGuardManager
        wg_manager = WireGuardManager()
        stats = wg_manager.get_peer_stats(public_key=vpn_config.public_key)
        
        if stats.get('peers') and len(stats['peers']) > 0:
            peer_stats = stats['peers'][0]
            peer_stats['nombre'] = vpn_config.nombre
            peer_stats['id'] = vpn_config.id
            return Response(peer_stats)
        else:
            return Response({
                'error': 'Peer no encontrado o no conectado',
                'nombre': vpn_config.nombre,
                'id': vpn_config.id,
                'activo': vpn_config.activo
            }, status=status.HTTP_404_NOT_FOUND)


class ServerManagementViewSet(APIKeyAwareViewSet, viewsets.ViewSet):
    """
    ViewSet para gestionar servicios del sistema (systemd) y PM2 vía SSH.
    Permite ver estado, iniciar, detener, reiniciar servicios y ver logs.
    """
    # No requerir autenticación específica, usar la del APIKeyAwareViewSet
    permission_classes = []  # Se maneja en APIKeyAwareViewSet
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            from .services.server_manager import ServerManager
            self.server_manager = ServerManager()
        except Exception as e:
            logger.error(f"Error inicializando ServerManager: {e}")
            self.server_manager = None
    
    @action(detail=False, methods=['get'])
    def systemd_services(self, request):
        """Obtiene lista de servicios systemd"""
        if not self.server_manager:
            return Response({'error': 'ServerManager no está configurado'}, status=500)
        
        try:
            services = self.server_manager.get_systemd_services()
            return Response({'services': services})
        except Exception as e:
            logger.error(f"Error obteniendo servicios systemd: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['get'])
    def pm2_processes(self, request):
        """Obtiene lista de procesos PM2"""
        if not self.server_manager:
            return Response({'error': 'ServerManager no está configurado'}, status=500)
        
        try:
            processes = self.server_manager.get_pm2_processes()
            return Response({'processes': processes})
        except Exception as e:
            logger.error(f"Error obteniendo procesos PM2: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['post'])
    def systemd_action(self, request):
        """Ejecuta una acción sobre un servicio systemd"""
        if not self.server_manager:
            return Response({'error': 'ServerManager no está configurado'}, status=500)
        
        service_name = request.data.get('service_name')
        action = request.data.get('action')
        
        if not service_name or not action:
            return Response({'error': 'service_name y action son requeridos'}, status=400)
        
        try:
            result = self.server_manager.systemd_action(service_name, action)
            return Response(result)
        except Exception as e:
            logger.error(f"Error ejecutando acción systemd: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['post'])
    def pm2_action(self, request):
        """Ejecuta una acción sobre un proceso PM2"""
        if not self.server_manager:
            return Response({'error': 'ServerManager no está configurado'}, status=500)
        
        process_name = request.data.get('process_name')
        action = request.data.get('action')
        
        if not process_name or not action:
            return Response({'error': 'process_name y action son requeridos'}, status=400)
        
        try:
            result = self.server_manager.pm2_action(process_name, action)
            return Response(result)
        except Exception as e:
            logger.error(f"Error ejecutando acción PM2: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['get'])
    def service_logs(self, request):
        """Obtiene logs de un servicio"""
        if not self.server_manager:
            return Response({'error': 'ServerManager no está configurado'}, status=500)
        
        service_name = request.query_params.get('service_name')
        lines = int(request.query_params.get('lines', 100))
        service_type = request.query_params.get('service_type', 'systemd')
        
        if not service_name:
            return Response({'error': 'service_name es requerido'}, status=400)
        
        try:
            logs = self.server_manager.get_service_logs(service_name, lines, service_type)
            return Response({'logs': logs, 'service_name': service_name, 'lines': lines})
        except Exception as e:
            logger.error(f"Error obteniendo logs: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['get'])
    def system_info(self, request):
        """Obtiene información general del sistema"""
        if not self.server_manager:
            return Response({'error': 'ServerManager no está configurado'}, status=500)
        
        try:
            info = self.server_manager.get_system_info()
            return Response(info)
        except Exception as e:
            logger.error(f"Error obteniendo información del sistema: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['post'])
    def execute_command(self, request):
        """Ejecuta un comando arbitrario en el servidor vía SSH"""
        if not self.server_manager:
            return Response({'error': 'ServerManager no está configurado'}, status=500)
        
        command = request.data.get('command')
        use_sudo = request.data.get('use_sudo', False)
        
        if not command:
            return Response({'error': 'command es requerido'}, status=400)
        
        # Validar comandos peligrosos (opcional, por seguridad)
        dangerous_commands = ['rm -rf /', 'dd if=', 'mkfs', 'fdisk']
        if any(danger in command.lower() for danger in dangerous_commands):
            return Response({'error': 'Comando peligroso no permitido'}, status=400)
        
        try:
            result = self.server_manager.execute_command(command, use_sudo=use_sudo)
            return Response(result)
        except Exception as e:
            logger.error(f"Error ejecutando comando: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['get'])
    def celery_logs(self, request):
        """Obtiene logs de Celery worker"""
        if not self.server_manager:
            return Response({'error': 'ServerManager no está configurado'}, status=500)
        
        lines = int(request.query_params.get('lines', 100))
        log_file = request.query_params.get('log_file', None)
        
        try:
            logs = self.server_manager.get_celery_logs(lines=lines, log_file=log_file)
            return Response({'logs': logs, 'lines': lines, 'type': 'celery'})
        except Exception as e:
            logger.error(f"Error obteniendo logs de Celery: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['get'])
    def celery_task_logs(self, request):
        """Obtiene logs de una tarea específica de Celery"""
        if not self.server_manager:
            return Response({'error': 'ServerManager no está configurado'}, status=500)
        
        task_name = request.query_params.get('task_name', None)
        lines = int(request.query_params.get('lines', 100))
        
        if not task_name:
            return Response({'error': 'task_name es requerido'}, status=400)
        
        try:
            logs = self.server_manager.get_celery_task_logs(task_name=task_name, lines=lines)
            return Response({'logs': logs, 'task_name': task_name, 'lines': lines, 'type': 'celery_task'})
        except Exception as e:
            logger.error(f"Error obteniendo logs de tarea Celery: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['get'])
    def pm2_logs(self, request):
        """Obtiene logs de PM2"""
        if not self.server_manager:
            return Response({'error': 'ServerManager no está configurado'}, status=500)
        
        process_name = request.query_params.get('process_name', None)
        lines = int(request.query_params.get('lines', 100))
        log_type = request.query_params.get('log_type', 'out')
        
        try:
            logs = self.server_manager.get_pm2_logs(
                process_name=process_name, 
                lines=lines, 
                log_type=log_type
            )
            return Response({
                'logs': logs, 
                'process_name': process_name or 'all',
                'lines': lines, 
                'type': 'pm2'
            })
        except Exception as e:
            logger.error(f"Error obteniendo logs de PM2: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['get'])
    def celery_tasks_list(self, request):
        """Lista todas las tareas registradas en Celery"""
        try:
            from config.celery import app as celery_app
            
            # Obtener todas las tareas registradas
            registered_tasks = {}
            for task_name, task in celery_app.tasks.items():
                # Filtrar tareas internas de Celery
                if not task_name.startswith('celery.'):
                    registered_tasks[task_name] = {
                        'name': task_name,
                        'routing_key': getattr(task, 'routing_key', None),
                        'queue': getattr(task, 'queue', None),
                    }
            
            return Response({
                'tasks': list(registered_tasks.values()),
                'total': len(registered_tasks)
            })
        except Exception as e:
            logger.error(f"Error listando tareas de Celery: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['get'])
    def celery_active_tasks(self, request):
        """Obtiene tareas activas de Celery en tiempo real"""
        try:
            from config.celery import app as celery_app
            
            # Usar inspect para obtener tareas activas
            inspect = celery_app.control.inspect()
            
            # Obtener información de workers activos (puede retornar None si no hay workers)
            active = inspect.active() or {}
            scheduled = inspect.scheduled() or {}
            reserved = inspect.reserved() or {}
            stats = inspect.stats() or {}
            
            # Formatear tareas activas
            active_tasks = []
            if active:
                for worker_name, tasks in active.items():
                    if tasks:
                        for task in tasks:
                            active_tasks.append({
                                'worker': worker_name,
                                'task_id': task.get('id'),
                                'task_name': task.get('name'),
                                'args': task.get('args', []),
                                'kwargs': task.get('kwargs', {}),
                                'time_start': task.get('time_start'),
                                'status': 'ACTIVE'
                            })
            
            # Formatear tareas programadas
            scheduled_tasks = []
            if scheduled:
                for worker_name, tasks in scheduled.items():
                    if tasks:
                        for task in tasks:
                            request_data = task.get('request', {})
                            scheduled_tasks.append({
                                'worker': worker_name,
                                'task_id': request_data.get('id'),
                                'task_name': request_data.get('task'),
                                'eta': task.get('eta'),
                                'status': 'SCHEDULED'
                            })
            
            # Formatear tareas reservadas
            reserved_tasks = []
            if reserved:
                for worker_name, tasks in reserved.items():
                    if tasks:
                        for task in tasks:
                            reserved_tasks.append({
                                'worker': worker_name,
                                'task_id': task.get('id'),
                                'task_name': task.get('name'),
                                'args': task.get('args', []),
                                'kwargs': task.get('kwargs', {}),
                                'status': 'RESERVED'
                            })
            
            return Response({
                'active': active_tasks,
                'scheduled': scheduled_tasks,
                'reserved': reserved_tasks,
                'workers': list(stats.keys()) if stats else [],
                'stats': stats
            })
        except Exception as e:
            logger.error(f"Error obteniendo tareas activas de Celery: {e}", exc_info=True)
            return Response({
                'active': [],
                'scheduled': [],
                'reserved': [],
                'workers': [],
                'stats': {},
                'error': str(e)
            }, status=200)  # Retornar 200 con estructura vacía en lugar de error


@api_view(['GET'])
@permission_classes([AllowAny])
def public_catalog_view(request):
    """
    Endpoint público y seguro para catálogo de e-commerce.
    Solo acepta dominio como parámetro y retorna empresa, productos, categorías y más vendidos.
    Usa SQL queries predefinidos (quemados) internamente - NO expone el sistema de records.
    GET /api/public-catalog/?dominio=pepito.ecommerce.localhost:3001
    """
    print("=" * 80)
    print("🛒 [PUBLIC-CATALOG] INICIO DE REQUEST")
    print(f"   Método: {request.method}")
    print(f"   Path: {request.path}")
    print(f"   Query params: {request.query_params}")
    
    dominio = request.query_params.get('dominio')
    print(f"   Dominio recibido: {dominio}")
    
    if not dominio:
        print("   ❌ ERROR: Parámetro 'dominio' faltante")
        return Response({'error': 'Parámetro "dominio" requerido'}, status=400)
    
    # Normalizar dominio
    dominio_normalizado = dominio.lower().strip()
    if dominio_normalizado.startswith('www.'):
        dominio_normalizado = dominio_normalizado[4:]
    
    print(f"   Dominio normalizado: {dominio_normalizado}")
    
    try:
        # Buscar dominio (exacto o por subdominio)
        empresa_dominio = None
        try:
            empresa_dominio = EmpresaDominio.objects.select_related('empresa_servidor').get(
                dominio=dominio_normalizado,
                activo=True
            )
        except EmpresaDominio.DoesNotExist:
            subdominio = dominio_normalizado.split('.')[0] if '.' in dominio_normalizado else dominio_normalizado
            empresa_dominio = EmpresaDominio.objects.select_related('empresa_servidor').filter(
                activo=True
            ).filter(
                Q(dominio=subdominio) | Q(dominio__startswith=f"{subdominio}.")
            ).first()
        
        if not empresa_dominio:
            print(f"   ❌ Dominio no encontrado: {dominio_normalizado}")
            return Response({'error': 'Dominio no encontrado o inactivo'}, status=404)
        
        # Obtener empresa (con lógica de año fiscal más reciente)
        empresa = empresa_dominio.empresa_servidor
        if not empresa:
            # Buscar por NIT si no hay empresa asociada
            if empresa_dominio.nit:
                nit_normalizado = _normalize_nit(empresa_dominio.nit)
                empresas_mismo_nit = EmpresaServidor.objects.filter(
                    nit_normalizado=nit_normalizado
                ).order_by('-anio_fiscal')
                if empresas_mismo_nit.exists():
                    empresa = empresas_mismo_nit.first()
                    empresa_dominio.empresa_servidor = empresa
                    empresa_dominio.anio_fiscal = empresa.anio_fiscal
                    empresa_dominio.save(update_fields=['empresa_servidor', 'anio_fiscal'])
        
        if not empresa:
            return Response({'error': 'No se pudo determinar la empresa para este dominio'}, status=404)
        
        print(f"   ✅ Empresa encontrada: {empresa.nombre} (ID: {empresa.id})")
        
        # Obtener logo
        logo_url = None
        try:
            nit_normalizado = _normalize_nit(empresa.nit) if empresa.nit else ''
            if nit_normalizado:
                personalizacion = EmpresaPersonalizacion.objects.filter(
                    nit_normalizado=nit_normalizado
                ).first()
                if personalizacion and personalizacion.logo:
                    logo_url = request.build_absolute_uri(personalizacion.logo.url)
        except Exception as e:
            logger.warning(f"Error obteniendo logo: {e}")
        
        # SQL QUERIES PREDEFINIDOS (QUEMADOS) - NO EXPONER records
        from .services.tns_bridge import TNSBridge
        bridge = TNSBridge(empresa)
        
        try:
            # 1. PRODUCTOS BÁSICOS (con precio > 0)
            productos_sql = """
            SELECT FIRST 500 DISTINCT 
                M.CODIGO, 
                M.DESCRIP, 
                M.MATID,
                G.CODIGO as GM_CODIGO, 
                G.DESCRIP as GM_DESCRIP,
                MS.PRECIO1,
                M.UNIDAD,
                M.PESO,
                M.CODBARRA
            FROM MATERIAL M
            LEFT JOIN GRUPMAT G ON G.GRUPMATID = M.GRUPMATID
            LEFT JOIN MATERIALSUC MS ON MS.MATID = M.MATID
            WHERE MS.PRECIO1 > 0
            ORDER BY M.CODIGO
            """
            productos = bridge.run_query(productos_sql)
            print(f"   ✅ {len(productos)} productos cargados")
            
            # 2. CATEGORÍAS (GRUPMAT)
            categorias_sql = """
            SELECT DISTINCT
                G.CODIGO as GM_CODIGO,
                G.DESCRIP as GM_DESCRIP,
                G.GRUPMATID
            FROM GRUPMAT G
            INNER JOIN MATERIAL M ON M.GRUPMATID = G.GRUPMATID
            INNER JOIN MATERIALSUC MS ON MS.MATID = M.MATID
            WHERE MS.PRECIO1 > 0
            ORDER BY G.CODIGO
            """
            categorias = bridge.run_query(categorias_sql)
            print(f"   ✅ {len(categorias)} categorías cargadas")
            
            # 3. MÁS VENDIDOS (últimos 30 días, PRECIO1 > 1000)
            mas_vendidos_sql = """
            SELECT FIRST 50
                DK.MATID, 
                COUNT(*) as VENTAS,
                M.CODIGO, 
                M.DESCRIP,
                G.CODIGO as GM_CODIGO, 
                G.DESCRIP as GM_DESCRIP,
                MS.PRECIO1,
                M.UNIDAD,
                M.PESO,
                M.CODBARRA
            FROM DEKARDEX DK
            LEFT JOIN KARDEX K ON K.KARDEXID = DK.KARDEXID
            LEFT JOIN MATERIAL M ON M.MATID = DK.MATID
            LEFT JOIN GRUPMAT G ON G.GRUPMATID = M.GRUPMATID
            LEFT JOIN MATERIALSUC MS ON MS.MATID = M.MATID
            WHERE CAST(K.FECHA AS TIMESTAMP) BETWEEN DATEADD(-30 DAY TO CURRENT_TIMESTAMP) AND CURRENT_TIMESTAMP
              AND MS.PRECIO1 > 1000
            GROUP BY DK.MATID, M.CODIGO, M.DESCRIP, G.CODIGO, G.DESCRIP, MS.PRECIO1, M.UNIDAD, M.PESO, M.CODBARRA
            ORDER BY VENTAS DESC, MS.PRECIO1 DESC
            """
            mas_vendidos = bridge.run_query(mas_vendidos_sql)
            print(f"   ✅ {len(mas_vendidos)} más vendidos cargados")
            
            # Seleccionar 5 aleatorios de los más vendidos
            import random
            if len(mas_vendidos) > 5:
                mas_vendidos = random.sample(mas_vendidos, 5)
                print(f"   ✅ Seleccionados 5 aleatorios de más vendidos")
            
            bridge.close()
            
            # Obtener NIT normalizado para buscar imágenes
            nit_normalizado = _normalize_nit(empresa.nit) if empresa.nit else ''
            
            # Agregar URLs de imágenes a productos
            if nit_normalizado:
                materiales_imagenes = {
                    mat.codigo_material: {
                        'imagen_url': request.build_absolute_uri(mat.imagen.url) if mat.imagen else None,
                        'caracteristicas': mat.caracteristicas,
                        'pdf_url': request.build_absolute_uri(mat.pdf.url) if mat.pdf else None
                    }
                    for mat in MaterialImagen.objects.filter(nit_normalizado=nit_normalizado)
                }
                
                # Agregar imágenes a productos
                for producto in productos:
                    codigo = producto.get('CODIGO') or producto.get('codigo')
                    if codigo and codigo in materiales_imagenes:
                        producto['imagen_url'] = materiales_imagenes[codigo]['imagen_url']
                        producto['caracteristicas'] = materiales_imagenes[codigo]['caracteristicas']
                        producto['pdf_url'] = materiales_imagenes[codigo]['pdf_url']
                
                # Agregar imágenes a más vendidos
                for producto in mas_vendidos:
                    codigo = producto.get('CODIGO') or producto.get('codigo')
                    if codigo and codigo in materiales_imagenes:
                        producto['imagen_url'] = materiales_imagenes[codigo]['imagen_url']
                        producto['caracteristicas'] = materiales_imagenes[codigo]['caracteristicas']
                        producto['pdf_url'] = materiales_imagenes[codigo]['pdf_url']
                
                # Agregar URLs de imágenes a categorías
                grupos_imagenes = {
                    grupo.gm_codigo: request.build_absolute_uri(grupo.imagen.url) if grupo.imagen else None
                    for grupo in GrupoMaterialImagen.objects.filter(nit_normalizado=nit_normalizado)
                }
                
                for categoria in categorias:
                    gm_codigo = categoria.get('GM_CODIGO') or categoria.get('gm_codigo')
                    if gm_codigo and gm_codigo in grupos_imagenes:
                        categoria['imagen_url'] = grupos_imagenes[gm_codigo]
            
            # Construir respuesta
            nombre_comercial = empresa.nombre
            if empresa.configuracion:
                nombre_comercial = empresa.configuracion.get('nombre_comercial', empresa.nombre)
            
            response_data = {
                'empresa': {
                    'empresa_servidor_id': empresa.id,
                    'nombre': empresa.nombre,
                    'nombre_comercial': nombre_comercial,
                    'nit': empresa.nit or '',
                    'anio_fiscal': empresa.anio_fiscal,
                    'modo': empresa_dominio.modo,
                    'logo_url': logo_url
                },
                'productos': productos,
                'categorias': categorias,
                'mas_vendidos': mas_vendidos
            }
            
            print(f"   ✅ Respuesta exitosa: empresa={empresa.nombre}, productos={len(productos)}, categorias={len(categorias)}, mas_vendidos={len(mas_vendidos)}")
            print("=" * 80)
            return Response(response_data, status=200)
            
        except Exception as e:
            bridge.close()
            print(f"   ❌ ERROR ejecutando queries: {e}")
            import traceback
            print(traceback.format_exc())
            logger.error(f"Error en public_catalog_view: {e}")
            return Response({'error': 'Error al cargar catálogo'}, status=500)
            
    except Exception as e:
        print(f"   ❌ ERROR EXCEPCIÓN: {str(e)}")
        import traceback
        print(traceback.format_exc())
        logger.error(f"Error en public_catalog_view: {e}")
        return Response({'error': 'Error interno del servidor'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_images_view(request):
    """
    Endpoint público para obtener imágenes y características de productos y categorías.
    Solo lectura, basado en dominio. Seguro para e-commerce.
    
    GET /api/public-catalog/images/?dominio=pepito.ecommerce.localhost:3001&tipo=materiales|grupos|all
    GET /api/public-catalog/images/?dominio=pepito.ecommerce.localhost:3001&tipo=materiales&codigo=VU00006
    GET /api/public-catalog/images/?dominio=pepito.ecommerce.localhost:3001&tipo=grupos&gm_codigo=00.01.01
    """
    from .models import EmpresaDominio
    from django.db.models import Q
    
    dominio = request.query_params.get('dominio')
    if not dominio:
        return Response({'error': 'Parámetro dominio es requerido'}, status=400)
    
    tipo = request.query_params.get('tipo', 'all')  # materiales, grupos, all
    codigo_material = request.query_params.get('codigo')
    gm_codigo = request.query_params.get('gm_codigo')
    
    try:
        # Normalizar dominio
        dominio_normalizado = dominio.lower().strip()
        if dominio_normalizado.startswith('www.'):
            dominio_normalizado = dominio_normalizado[4:]
        
        # Buscar empresa desde dominio (reutilizar lógica de public_catalog_view)
        empresa_dominio = None
        try:
            empresa_dominio = EmpresaDominio.objects.select_related('empresa_servidor').get(
                dominio=dominio_normalizado,
                activo=True
            )
        except EmpresaDominio.DoesNotExist:
            subdominio = dominio_normalizado.split('.')[0] if '.' in dominio_normalizado else dominio_normalizado
            empresa_dominio = EmpresaDominio.objects.select_related('empresa_servidor').filter(
                activo=True
            ).filter(
                Q(dominio=subdominio) | Q(dominio__startswith=f"{subdominio}.")
            ).first()
        
        if not empresa_dominio or not empresa_dominio.empresa_servidor:
            return Response({'error': 'Dominio no encontrado'}, status=404)
        
        empresa = empresa_dominio.empresa_servidor
        nit_normalizado = _normalize_nit(empresa.nit) if empresa.nit else ''
        
        if not nit_normalizado:
            return Response({'error': 'No se pudo determinar el NIT de la empresa'}, status=400)
        
        response_data = {}
        
        # Obtener imágenes de materiales (productos)
        if tipo in ['materiales', 'all']:
            materiales_query = MaterialImagen.objects.filter(nit_normalizado=nit_normalizado)
            
            if codigo_material:
                materiales_query = materiales_query.filter(codigo_material=codigo_material)
            
            materiales = materiales_query.all()
            materiales_data = []
            for mat in materiales:
                mat_data = {
                    'codigo_material': mat.codigo_material,
                    'imagen_url': request.build_absolute_uri(mat.imagen.url) if mat.imagen else None,
                    'caracteristicas': mat.caracteristicas,
                    'pdf_url': request.build_absolute_uri(mat.pdf.url) if mat.pdf else None
                }
                materiales_data.append(mat_data)
            
            if codigo_material:
                # Si se especificó un código, retornar solo ese
                response_data['material'] = materiales_data[0] if materiales_data else None
            else:
                response_data['materiales'] = materiales_data
        
        # Obtener imágenes de grupos (categorías)
        if tipo in ['grupos', 'all']:
            grupos_query = GrupoMaterialImagen.objects.filter(nit_normalizado=nit_normalizado)
            
            if gm_codigo:
                grupos_query = grupos_query.filter(gm_codigo=gm_codigo)
            
            grupos = grupos_query.all()
            grupos_data = []
            for grupo in grupos:
                grupo_data = {
                    'gm_codigo': grupo.gm_codigo,
                    'imagen_url': request.build_absolute_uri(grupo.imagen.url) if grupo.imagen else None
                }
                grupos_data.append(grupo_data)
            
            if gm_codigo:
                # Si se especificó un código, retornar solo ese
                response_data['grupo'] = grupos_data[0] if grupos_data else None
            else:
                response_data['grupos'] = grupos_data
        
        return Response(response_data, status=200)
        
    except Exception as e:
        logger.error(f"Error en public_images_view: {e}")
        import traceback
        print(traceback.format_exc())
        return Response({'error': 'Error al cargar imágenes'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def resolve_domain_view(request):
    """
    Endpoint público para resolver un dominio a una empresa.
    Usado por el frontend e-commerce para cargar la empresa sin autenticación.
    GET /api/resolve-domain/?dominio=pepito.ecommerce.localhost:3001
    """
    print("=" * 80)
    print("🔍 [RESOLVE-DOMAIN] INICIO DE REQUEST")
    print(f"   Método: {request.method}")
    print(f"   Path: {request.path}")
    print(f"   Query params: {request.query_params}")
    
    dominio = request.query_params.get('dominio')
    print(f"   Dominio recibido: {dominio}")
    
    if not dominio:
        print("   ❌ ERROR: Parámetro 'dominio' faltante")
        return Response({'error': 'Parámetro "dominio" requerido'}, status=400)
    
    # Normalizar dominio: minúsculas, sin www., sin espacios
    dominio_normalizado = dominio.lower().strip()
    if dominio_normalizado.startswith('www.'):
        dominio_normalizado = dominio_normalizado[4:]
    
    print(f"   Dominio normalizado: {dominio_normalizado}")
    
    # Debug: listar todos los dominios en BD con información de empresa
    todos_dominios = EmpresaDominio.objects.select_related('empresa_servidor').all()
    print(f"   Dominios en BD:")
    for ed in todos_dominios:
        if ed.empresa_servidor:
            print(f"      - Dominio: '{ed.dominio}' -> Empresa: {ed.empresa_servidor.nombre} (ID: {ed.empresa_servidor.id}, NIT: '{ed.empresa_servidor.nit}')")
        else:
            print(f"      - Dominio: '{ed.dominio}' -> Sin empresa (NIT: '{ed.nit}')")
    
    try:
        # Primero intentar búsqueda exacta
        empresa_dominio = None
        try:
            empresa_dominio = EmpresaDominio.objects.select_related('empresa_servidor').get(
                dominio=dominio_normalizado,
                activo=True
            )
            empresa_nombre = empresa_dominio.empresa_servidor.nombre if empresa_dominio.empresa_servidor else 'Sin empresa'
            print(f"   ✅ Empresa dominio encontrada (exacta): {empresa_dominio.dominio} -> {empresa_nombre}")
        except EmpresaDominio.DoesNotExist:
            # Si no se encuentra exacta, intentar buscar por subdominio (primera parte antes del primer punto)
            subdominio = dominio_normalizado.split('.')[0] if '.' in dominio_normalizado else dominio_normalizado
            print(f"   🔍 Búsqueda exacta falló, intentando por subdominio: '{subdominio}'")
            
            # Buscar dominios que empiecen con el subdominio o que sean exactamente el subdominio
            empresa_dominio = EmpresaDominio.objects.select_related('empresa_servidor').filter(
                activo=True
            ).filter(
                Q(dominio=subdominio) | Q(dominio__startswith=f"{subdominio}.")
            ).first()
            
            if empresa_dominio:
                empresa_nombre = empresa_dominio.empresa_servidor.nombre if empresa_dominio.empresa_servidor else 'Sin empresa'
                print(f"   ✅ Empresa dominio encontrada (por subdominio): {empresa_dominio.dominio} -> {empresa_nombre}")
            else:
                raise EmpresaDominio.DoesNotExist(f"No se encontró dominio para '{dominio_normalizado}' o subdominio '{subdominio}'")
        
        # Debug: mostrar información completa de la empresa encontrada
        print(f"   📋 Información de EmpresaDominio:")
        print(f"      - ID: {empresa_dominio.id}")
        print(f"      - Dominio: {empresa_dominio.dominio}")
        print(f"      - NIT: '{empresa_dominio.nit}'")
        print(f"      - Modo: {empresa_dominio.modo}")
        print(f"      - Activo: {empresa_dominio.activo}")
        print(f"      - Año Fiscal guardado: {empresa_dominio.anio_fiscal}")
        print(f"      - Empresa Servidor ID: {empresa_dominio.empresa_servidor_id}")
        
        # Si no hay empresa_servidor asociada, buscar por NIT
        empresa = empresa_dominio.empresa_servidor
        if not empresa:
            print(f"   🔍 No hay empresa asociada, buscando por NIT...")
            if empresa_dominio.nit:
                nit_normalizado = _normalize_nit(empresa_dominio.nit)
                print(f"   🔍 Buscando empresas con NIT normalizado: '{nit_normalizado}'")
                
                if nit_normalizado:
                    # Buscar empresas con el mismo NIT normalizado
                    empresas_mismo_nit = EmpresaServidor.objects.filter(
                        nit_normalizado=nit_normalizado
                    )
                    
                    # Si el dominio tiene un servidor autorizado, filtrar solo empresas de ese servidor
                    if empresa_dominio.servidor:
                        empresas_mismo_nit = empresas_mismo_nit.filter(servidor=empresa_dominio.servidor)
                    
                    empresas_mismo_nit = empresas_mismo_nit.order_by('-anio_fiscal')
                    
                    print(f"   📊 Búsqueda directa: {empresas_mismo_nit.count()} empresas encontradas")
                    
                    # Si no se encuentra, hacer búsqueda flexible normalizando todos los NITs
                    if not empresas_mismo_nit.exists():
                        print(f"   🔄 Búsqueda directa falló, intentando búsqueda flexible...")
                        todas_empresas = EmpresaServidor.objects.all()
                        print(f"   📊 Total empresas en BD: {todas_empresas.count()}")
                        
                        empresas_encontradas = []
                        for emp in todas_empresas:
                            nit_emp_normalizado = _normalize_nit(emp.nit) if emp.nit else ''
                            if nit_emp_normalizado == nit_normalizado:
                                empresas_encontradas.append(emp)
                                print(f"      - Empresa encontrada: {emp.nombre} (NIT original: '{emp.nit}', NIT normalizado: '{nit_emp_normalizado}')")
                        
                        if empresas_encontradas:
                            # Ordenar por año fiscal descendente
                            empresas_encontradas.sort(key=lambda e: e.anio_fiscal, reverse=True)
                            empresa = empresas_encontradas[0]
                            print(f"   ✅ Empresa encontrada por NIT (búsqueda flexible): {empresa.nombre} (Año: {empresa.anio_fiscal})")
                        else:
                            print(f"   ❌ No se encontraron empresas con NIT normalizado '{nit_normalizado}'")
                            # Mostrar algunos NITs de ejemplo para debug
                            print(f"   📋 Primeros 5 NITs en BD (para referencia):")
                            for emp in todas_empresas[:5]:
                                nit_emp_norm = _normalize_nit(emp.nit) if emp.nit else ''
                                print(f"      - '{emp.nit}' -> normalizado: '{nit_emp_norm}'")
                            return Response({'error': f'No se encontró empresa con NIT {empresa_dominio.nit} (normalizado: {nit_normalizado})'}, status=404)
                    else:
                        empresa = empresas_mismo_nit.first()
                        print(f"   ✅ Empresa encontrada por NIT (búsqueda directa): {empresa.nombre} (Año: {empresa.anio_fiscal})")
                    
                    # Actualizar EmpresaDominio con la empresa encontrada
                    empresa_dominio.empresa_servidor = empresa
                    empresa_dominio.anio_fiscal = empresa.anio_fiscal
                    empresa_dominio.save(update_fields=['empresa_servidor', 'anio_fiscal'])
                    print(f"   💾 EmpresaDominio actualizado con empresa {empresa.id}")
                else:
                    print(f"   ❌ NIT inválido: '{empresa_dominio.nit}'")
                    return Response({'error': f'NIT inválido: {empresa_dominio.nit}'}, status=400)
            else:
                print(f"   ❌ No hay NIT ni empresa asociada al dominio")
                return Response({'error': 'Dominio no tiene NIT ni empresa asociada'}, status=404)
        
        # Verificar si necesitamos buscar la empresa con año fiscal más reciente
        from django.utils import timezone
        anio_actual = timezone.now().year
        necesita_buscar_mas_reciente = (
            empresa_dominio.anio_fiscal is None or 
            empresa_dominio.anio_fiscal < anio_actual
        )
        
        if necesita_buscar_mas_reciente:
            print(f"   🔄 Año fiscal guardado ({empresa_dominio.anio_fiscal}) es menor al actual ({anio_actual}), buscando empresa más reciente...")
            # Usar NIT del dominio o de la empresa actual
            nit_normalizado = None
            if empresa_dominio.nit:
                nit_normalizado = _normalize_nit(empresa_dominio.nit)
            elif empresa.nit:
                nit_normalizado = _normalize_nit(empresa.nit)
            
            if nit_normalizado:
                # Buscar todas las empresas con el mismo NIT normalizado, ordenadas por año fiscal descendente
                empresas_mismo_nit = EmpresaServidor.objects.filter(
                    nit_normalizado=nit_normalizado
                ).order_by('-anio_fiscal')
                
                if empresas_mismo_nit.exists():
                    empresa_mas_reciente = empresas_mismo_nit.first()
                    print(f"   ✅ Empresa más reciente encontrada: {empresa_mas_reciente.nombre} (Año: {empresa_mas_reciente.anio_fiscal})")
                    
                    # Actualizar EmpresaDominio con la empresa más reciente
                    if empresa_mas_reciente.id != empresa_dominio.empresa_servidor_id:
                        empresa_dominio.empresa_servidor = empresa_mas_reciente
                        empresa_dominio.anio_fiscal = empresa_mas_reciente.anio_fiscal
                        empresa_dominio.save(update_fields=['empresa_servidor', 'anio_fiscal'])
                        print(f"   💾 EmpresaDominio actualizado: empresa {empresa.id} -> {empresa_mas_reciente.id}")
                    
                    empresa = empresa_mas_reciente
                else:
                    print(f"   ⚠️  No se encontraron empresas con NIT '{nit_normalizado}'")
            else:
                print(f"   ⚠️  NIT vacío, no se puede buscar empresa más reciente")
        else:
            print(f"   ✅ Año fiscal guardado ({empresa_dominio.anio_fiscal}) es actual, usando empresa asociada directamente")
        
        print(f"   📋 Información de EmpresaServidor (final):")
        print(f"      - ID: {empresa.id}")
        print(f"      - Nombre: {empresa.nombre}")
        print(f"      - NIT: '{empresa.nit}'")
        print(f"      - Año Fiscal: {empresa.anio_fiscal}")
        print(f"      - Código: {empresa.codigo}")
        print(f"      - Configuración: {empresa.configuracion}")
        
        # Obtener logo si existe
        logo_url = None
        try:
            nit_normalizado = _normalize_nit(empresa.nit) if empresa.nit else ''
            print(f"   🖼️  Buscando logo con NIT normalizado: '{nit_normalizado}'")
            if nit_normalizado:
                personalizacion = EmpresaPersonalizacion.objects.filter(
                    nit_normalizado=nit_normalizado
                ).first()
                if personalizacion:
                    print(f"      - Personalización encontrada: {personalizacion.id}")
                    if personalizacion.logo:
                        logo_url = request.build_absolute_uri(personalizacion.logo.url)
                        print(f"      - Logo URL: {logo_url}")
                    else:
                        print(f"      - No hay logo en personalización")
                else:
                    print(f"      - No se encontró personalización para NIT '{nit_normalizado}'")
            else:
                print(f"      - NIT vacío, no se puede buscar logo")
        except Exception as e:
            logger.warning(f"Error obteniendo logo para dominio {dominio}: {e}")
            print(f"      - ❌ Error obteniendo logo: {e}")
        
        nombre_comercial = empresa.nombre
        if empresa.configuracion:
            nombre_comercial = empresa.configuracion.get('nombre_comercial', empresa.nombre)
            print(f"   📝 Nombre comercial desde config: '{nombre_comercial}'")
        
        # Asegurar que empresa no sea None antes de construir la respuesta
        if not empresa:
            print(f"   ❌ ERROR: empresa es None después de toda la lógica")
            print("=" * 80)
            return Response({'error': 'No se pudo determinar la empresa para este dominio'}, status=500)
        
        # Opcional: incluir productos iniciales, categorías y más vendidos si se solicita
        include_products = request.query_params.get('include_products', 'false').lower() == 'true'
        
        response_data = {
            'empresa_servidor_id': empresa.id,
            'nombre': empresa.nombre,
            'nombre_comercial': nombre_comercial,
            'nit': empresa.nit or '',
            'anio_fiscal': empresa.anio_fiscal,
            'modo': empresa_dominio.modo,
            'logo_url': logo_url
        }
        
        if include_products:
            print(f"   📦 Incluyendo productos iniciales en la respuesta...")
            try:
                from .services.tns_bridge import TNSBridge
                bridge = TNSBridge(empresa)
                
                # Productos básicos (materialprecio)
                try:
                    productos_sql = """
                    SELECT FIRST 200 DISTINCT 
                        M.CODIGO, M.DESCRIP, M.MATID,
                        G.CODIGO as GM_CODIGO, G.DESCRIP as GM_DESCRIP,
                        MS.PRECIO1
                    FROM MATERIAL M
                    LEFT JOIN GRUPMAT G ON G.GRUPMATID = M.GRUPMATID
                    LEFT JOIN MATERIALSUC MS ON MS.MATID = M.MATID
                    WHERE MS.PRECIO1 > 0
                    ORDER BY M.CODIGO
                    """
                    productos = bridge.run_query(productos_sql)
                    response_data['productos'] = productos[:200]  # Limitar a 200
                    print(f"      ✅ {len(productos)} productos cargados")
                except Exception as e:
                    print(f"      ⚠️  Error cargando productos: {e}")
                    response_data['productos'] = []
                
                # Más vendidos (últimos 30 días)
                try:
                    mas_vendidos_sql = """
                    SELECT FIRST 50
                        DK.MATID, 
                        COUNT(*) as VENTAS,
                        M.CODIGO, M.DESCRIP,
                        G.CODIGO as GM_CODIGO, G.DESCRIP as GM_DESCRIP,
                        MS.PRECIO1
                    FROM DEKARDEX DK
                    LEFT JOIN KARDEX K ON K.KARDEXID = DK.KARDEXID
                    LEFT JOIN MATERIAL M ON M.MATID = DK.MATID
                    LEFT JOIN GRUPMAT G ON G.GRUPMATID = M.GRUPMATID
                    LEFT JOIN MATERIALSUC MS ON MS.MATID = M.MATID
                    WHERE CAST(K.FECHA AS TIMESTAMP) BETWEEN DATEADD(-30 DAY TO CURRENT_TIMESTAMP) AND CURRENT_TIMESTAMP
                      AND MS.PRECIO1 > 1000
                    GROUP BY DK.MATID, M.CODIGO, M.DESCRIP, G.CODIGO, G.DESCRIP, MS.PRECIO1
                    ORDER BY VENTAS DESC, MS.PRECIO1 DESC
                    """
                    mas_vendidos = bridge.run_query(mas_vendidos_sql)
                    response_data['mas_vendidos'] = mas_vendidos[:50]  # Limitar a 50
                    print(f"      ✅ {len(mas_vendidos)} más vendidos cargados")
                except Exception as e:
                    print(f"      ⚠️  Error cargando más vendidos: {e}")
                    response_data['mas_vendidos'] = []
                
                bridge.close()
            except Exception as e:
                print(f"   ⚠️  Error incluyendo productos: {e}")
                response_data['productos'] = []
                response_data['mas_vendidos'] = []
        
        print(f"   ✅ Respuesta exitosa: {response_data}")
        print("=" * 80)
        return Response(response_data, status=200)
    except EmpresaDominio.DoesNotExist:
        print(f"   ❌ ERROR: Dominio '{dominio_normalizado}' no encontrado o inactivo")
        print("   Intentando búsqueda parcial...")
        # Intentar búsqueda parcial (solo el subdominio)
        subdominio = dominio_normalizado.split('.')[0] if '.' in dominio_normalizado else dominio_normalizado
        print(f"   Subdominio extraído: {subdominio}")
        dominios_similares = EmpresaDominio.objects.filter(dominio__icontains=subdominio).values_list('dominio', 'activo', 'modo')
        print(f"   Dominios similares encontrados: {list(dominios_similares)}")
        print("=" * 80)
        return Response({'error': f'Dominio no encontrado o inactivo. Dominio buscado: {dominio_normalizado}, Subdominio: {subdominio}'}, status=404)
    except Exception as e:
        print(f"   ❌ ERROR EXCEPCIÓN: {str(e)}")
        import traceback
        print(traceback.format_exc())
        print("=" * 80)
        logger.error(f"Error resolviendo dominio {dominio}: {e}")
        return Response({'error': 'Error interno del servidor'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_company_by_subdomain_view(request, subdomain):
    """
    Endpoint público para resolver una empresa a partir de un subdominio.
    Usado por el frontend para cargar la empresa sin autenticación.
    GET /api/companies/by-subdomain/{subdomain}/
    """
    print("=" * 80)
    print(f"🔍 [GET-COMPANY-BY-SUBDOMAIN] INICIO DE REQUEST para subdominio: {subdomain}")
    
    if not subdomain:
        print("   ❌ ERROR: Subdominio faltante")
        return Response({'error': 'Subdominio requerido'}, status=400)
    
    # Normalizar subdominio
    subdominio_normalizado = subdomain.lower().strip()
    print(f"   Subdominio normalizado: {subdominio_normalizado}")
    
    try:
        # Buscar en EmpresaDominio por subdominio (primera parte del dominio)
        empresa_dominio = EmpresaDominio.objects.select_related('empresa_servidor').filter(
            activo=True
        ).filter(
            Q(dominio=subdominio_normalizado) | Q(dominio__startswith=f"{subdominio_normalizado}.")
        ).first()
        
        if not empresa_dominio:
            print(f"   ❌ Dominio no encontrado para subdominio: {subdominio_normalizado}")
            return Response({'error': 'Dominio no encontrado o inactivo'}, status=404)
        
        # Reutilizar lógica de resolve_domain_view para obtener la empresa
        mock_request = HttpRequest()
        mock_request.method = 'GET'
        mock_request.query_params = {'dominio': empresa_dominio.dominio}
        
        response = resolve_domain_view(mock_request)
        
        # Si resolve_domain_view retorna un error, pasarlo
        if response.status_code != 200:
            return response
        
        # Extraer los datos de la empresa del response
        response_data = response.data
        
        # Adaptar al formato CompanyInfo esperado por el frontend
        company_info = {
            'id': response_data.get('empresa_servidor_id'),
            'name': response_data.get('nombre_comercial') or response_data.get('nombre'),
            'subdomain': subdomain,
            'custom_domain': empresa_dominio.dominio if empresa_dominio.dominio != subdomain else None,
            'mode': empresa_dominio.modo,
            'imageUrl': response_data.get('logo_url'),
            'is_active': empresa_dominio.activo,
            'primary_color': None,
            'secondary_color': None,
            'font_family': None,
            'tagline': None,
        }
        
        print(f"   ✅ Empresa encontrada y adaptada: {company_info['name']}")
        print("=" * 80)
        return Response(company_info, status=200)
        
    except Exception as e:
        logger.exception(f"Error en get_company_by_subdomain_view para subdominio {subdomain}")
        print(f"   ❌ ERROR inesperado: {str(e)}")
        print("=" * 80)
        return Response({'error': 'Error interno del servidor'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_company_by_domain_view(request, domain):
    """
    Endpoint público para resolver una empresa a partir de un dominio completo.
    Usado por el frontend para cargar la empresa sin autenticación cuando no hay subdominio.
    GET /api/companies/by-domain/{domain}/
    """
    print("=" * 80)
    print(f"🔍 [GET-COMPANY-BY-DOMAIN] INICIO DE REQUEST para dominio: {domain}")
    
    if not domain:
        print("   ❌ ERROR: Dominio faltante")
        return Response({'error': 'Dominio requerido'}, status=400)
    
    # Normalizar dominio
    dominio_normalizado = domain.lower().strip()
    if dominio_normalizado.startswith('www.'):
        dominio_normalizado = dominio_normalizado[4:]
    print(f"   Dominio normalizado: {dominio_normalizado}")
    
    try:
        # Buscar en EmpresaDominio por dominio exacto
        empresa_dominio = EmpresaDominio.objects.select_related('empresa_servidor').filter(
            dominio=dominio_normalizado,
            activo=True
        ).first()
        
        if not empresa_dominio:
            print(f"   ❌ Dominio no encontrado: {dominio_normalizado}")
            return Response({'error': 'Dominio no encontrado o inactivo'}, status=404)
        
        # Reutilizar lógica de resolve_domain_view para obtener la empresa
        mock_request = HttpRequest()
        mock_request.method = 'GET'
        mock_request.query_params = {'dominio': empresa_dominio.dominio}
        
        response = resolve_domain_view(mock_request)
        
        # Si resolve_domain_view retorna un error, pasarlo
        if response.status_code != 200:
            return response
        
        # Extraer los datos de la empresa del response
        response_data = response.data
        
        # Adaptar al formato CompanyInfo esperado por el frontend
        company_info = {
            'id': response_data.get('empresa_servidor_id'),
            'name': response_data.get('nombre_comercial') or response_data.get('nombre'),
            'subdomain': None,  # No hay subdominio cuando se busca por dominio completo
            'custom_domain': empresa_dominio.dominio,
            'mode': empresa_dominio.modo,
            'imageUrl': response_data.get('logo_url'),
            'is_active': empresa_dominio.activo,
            'primary_color': None,
            'secondary_color': None,
            'font_family': None,
            'tagline': None,
        }
        
        print(f"   ✅ Empresa encontrada y adaptada: {company_info['name']}")
        print("=" * 80)
        return Response(company_info, status=200)
        
    except Exception as e:
        logger.exception(f"Error en get_company_by_domain_view para dominio {domain}")
        print(f"   ❌ ERROR inesperado: {str(e)}")
        print("=" * 80)
        return Response({'error': 'Error interno del servidor'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def formas_pago_ecommerce_view(request):
    """
    Endpoint público para obtener formas de pago desde TNS para e-commerce.
    Usa usuario_tns de EmpresaEcommerceConfig.
    GET /api/formas-pago-ecommerce/?empresa_servidor_id=192
    """
    empresa_servidor_id = request.query_params.get('empresa_servidor_id')
    
    if not empresa_servidor_id:
        return Response(
            {'error': 'empresa_servidor_id es requerido'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        empresa = EmpresaServidor.objects.select_related('servidor').get(id=empresa_servidor_id)
        config = EmpresaEcommerceConfig.objects.get(empresa_servidor_id=empresa_servidor_id)
    except EmpresaServidor.DoesNotExist:
        return Response(
            {'error': f'Empresa con ID {empresa_servidor_id} no encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )
    except EmpresaEcommerceConfig.DoesNotExist:
        return Response(
            {'error': 'Configuración de e-commerce no encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if not config.usuario_tns:
        return Response(
            {'error': 'usuario_tns no configurado en e-commerce'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    bridge = TNSBridge(empresa)
    bridge.connect()
    
    try:
        cursor = bridge.conn.cursor()
        
        # Obtener usuario TNS de la configuración de e-commerce
        usuario_tns = config.usuario_tns
        
        # GFPPERMITIDASCAJAGC se compone dinámicamente: GFPPERMITIDAS + usuario_logueado
        variab_formas_pago = f"GFPPERMITIDAS{usuario_tns}"
        logger.info(f"[ecommerce] Buscando variable de formas de pago: {variab_formas_pago}")
        
        # Obtener GFPPERMITIDAS{usuario_tns} de VARIOS
        cursor.execute("""
            SELECT CAST(contenido AS VARCHAR(500)) 
            FROM varios 
            WHERE variab = ?
        """, (variab_formas_pago,))
        
        resultado = cursor.fetchone()
        if not resultado or not resultado[0]:
            return Response(
                {'error': f'No se encontró configuración de formas de pago ({variab_formas_pago})'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        codigos_str = resultado[0].strip()
        # Formato: "codigo1,codigo2," (siempre termina en coma)
        # Remover la coma final si existe
        if codigos_str.endswith(','):
            codigos_str = codigos_str[:-1]
        
        # Separar códigos
        codigos = [c.strip() for c in codigos_str.split(',') if c.strip()]
        
        if not codigos:
            return Response(
                {'error': 'No hay formas de pago configuradas'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Obtener descripciones de FORMAPAGO
        placeholders = ','.join(['?' for _ in codigos])
        cursor.execute(f"""
            SELECT CODIGO, DESCRIP 
            FROM FORMAPAGO 
            WHERE CODIGO IN ({placeholders})
        """, codigos)
        
        formas_pago = []
        for row in cursor.fetchall():
            codigo, descrip = row
            formas_pago.append({
                'codigo': codigo.strip() if codigo else '',
                'descripcion': descrip.strip() if descrip else codigo.strip() if codigo else ''
            })
        
        logger.info(f"[ecommerce] Formas de pago cargadas: {len(formas_pago)} opciones")
        
        return Response({
            'formas_pago': formas_pago
        })
        
    except Exception as e:
        logger.error(f"[ecommerce] Error cargando formas de pago: {e}", exc_info=True)
        return Response(
            {'error': f'Error al cargar formas de pago: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        bridge.close()

@api_view(['GET'])
@permission_classes([AllowAny])
def pasarelas_disponibles_view(request):
    """
    Endpoint público para listar pasarelas de pago disponibles.
    No requiere autenticación ni credenciales.
    
    Query params:
    - empresa_servidor_id: ID de la empresa (opcional, solo para logging)
    
    Returns:
    {
        "pasarelas": [
            {"id": 1, "codigo": "credibanco", "nombre": "Credibanco", "activa": true}
        ]
    }
    """
    # Retornar pasarelas activas sin validación (es información pública)
    pasarelas = PasarelaPago.objects.filter(activa=True)
    serializer = PasarelaPagoSerializer(pasarelas, many=True)
    
    return Response({
        'pasarelas': serializer.data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def procesar_pago_ecommerce_view(request):
    """
    Endpoint público único para procesar pagos (mock o producción según pasarela).
    
    Si mock=true: procesa en modo simulado y crea factura inmediatamente.
    Si mock=false o no viene: procesa con la pasarela real configurada en admin.
    
    Body:
    {
        "empresa_servidor_id": 192,
        "mock": true,  # Opcional: si es true, simula. Si false o no viene, usa pasarela real
        "forma_pago_codigo": "TC",  # Código de FORMAPAGO (TC, TD, EF, etc.)
        "cart_items": [
            {"id": "CODIGO1", "name": "Producto 1", "price": 1000, "quantity": 2},
            ...
        ],
        "monto_total": 3000,
        "document_number": "1234567890",  # Cédula/NIT del cliente
        "direccion_envio": "Calle 123 #45-67, Bogotá",
        "nombre_cliente": "Juan Pérez",
        "telefono_cliente": "3001234567",
        "email_cliente": "cliente@example.com",
        "tarjeta": {  # Solo si forma_pago_codigo es TC/TD
            "numero": "4111111111111111",
            "nombre_titular": "Juan Pérez",
            "mes_vencimiento": "12",
            "anio_vencimiento": "2025",
            "cvv": "123"
        }
    }
    
    Returns (modo mock):
    {
        "success": true,
        "mock": true,
        "pago": {
            "codigo_autorizacion": "MOCK123456",
            "franquicia": "VISA",
            ...
        },
        "factura": {...}
    }
    
    Returns (modo producción - Credibanco):
    {
        "success": true,
        "mock": false,
        "formUrl": "https://eco.credibanco.com/payment/merchants/...",
        "order_number": "1234567890",
        "transaccion_id": 123
    }
    """
    empresa_servidor_id = request.data.get('empresa_servidor_id')
    mock = request.data.get('mock', None)  # None = usar configuración de la pasarela
    forma_pago_codigo = request.data.get('forma_pago_codigo')  # Código de FORMAPAGO (TC, TD, EF, etc.)
    cart_items = request.data.get('cart_items', [])
    monto_total = request.data.get('monto_total', 0)
    doc_type = request.data.get('doc_type', 'cedula')  # 'cedula' o 'nit'
    document_number = request.data.get('document_number') or request.data.get('cedula')
    nature = request.data.get('nature', 'natural')  # 'natural' o 'juridica'
    direccion_envio = request.data.get('direccion_envio', '')
    nombre_cliente = request.data.get('nombre_cliente', '')
    telefono_cliente = request.data.get('telefono_cliente', '')
    email_cliente = request.data.get('email_cliente', '')
    
    # Validaciones básicas
    if not empresa_servidor_id:
        return Response(
            {'detail': 'empresa_servidor_id es requerido'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not forma_pago_codigo:
        return Response(
            {'detail': 'forma_pago_codigo es requerido'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not cart_items or len(cart_items) == 0:
        return Response(
            {'detail': 'cart_items no puede estar vacío'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not document_number:
        return Response(
            {'detail': 'document_number (o cedula) es requerido'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Obtener empresa y configuración
    try:
        empresa = EmpresaServidor.objects.get(id=empresa_servidor_id)
        config = EmpresaEcommerceConfig.objects.get(empresa_servidor_id=empresa_servidor_id)
    except EmpresaServidor.DoesNotExist:
        return Response(
            {'detail': f'Empresa con ID {empresa_servidor_id} no encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )
    except EmpresaEcommerceConfig.DoesNotExist:
        return Response(
            {'detail': 'Configuración de e-commerce no encontrada. Configure usuario_tns y password_tns en el panel de administración.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Determinar si es tarjeta
    # Los códigos pueden ser: 'TC', 'TD', 'TCGC', 'TDCG', 'TARJETA CREDITO', etc.
    codigo_upper = forma_pago_codigo.upper().strip()
    es_tarjeta = (codigo_upper.startswith('TC') or 
                  codigo_upper.startswith('TD') or 
                  codigo_upper == 'TC' or 
                  codigo_upper == 'TD' or 
                  'TARJETA' in codigo_upper or 
                  'CARD' in codigo_upper or
                  'CREDITO' in codigo_upper or
                  'DEBITO' in codigo_upper)
    logger.info(f"[ecommerce] Forma de pago: {codigo_upper}, es_tarjeta: {es_tarjeta}")
    
    # Si es tarjeta, necesitamos pasarela
    if es_tarjeta:
        # Leer pasarela configurada
        pasarela_codigo = config.payment_provider
        if not pasarela_codigo:
            return Response(
                {'detail': 'No hay pasarela de pago configurada. Configure payment_provider en el panel de administración.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            pasarela = PasarelaPago.objects.get(codigo=pasarela_codigo, activa=True)
        except PasarelaPago.DoesNotExist:
            return Response(
                {'detail': f'Pasarela de pago "{pasarela_codigo}" no encontrada o inactiva.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Determinar modo: 
        # 1. Si mock viene explícitamente en el request, usarlo (para testing)
        # 2. Si no, usar payment_mode de la configuración: 'test' = mock, 'live' = pasarela real
        if mock is None:
            # Usar payment_mode de la configuración
            mock = (config.payment_mode == 'test')
            logger.info(f"[ecommerce] payment_mode={config.payment_mode}, mock={mock}")
            if config.payment_mode == 'test':
                logger.warning("[ecommerce] ⚠️ payment_mode está en 'test'. Para procesar pagos reales, cambia a 'live' en el panel de administración.")
        else:
            logger.info(f"[ecommerce] mock viene explícitamente en request: {mock}")
        
        logger.info(f"[ecommerce] Procesando pago: es_tarjeta={es_tarjeta}, pasarela={pasarela_codigo}, mock={mock}")
        
        # Si es mock, procesar como mock
        if mock:
            logger.info("[ecommerce] Procesando como MOCK (simulado)")
            return _procesar_pago_mock(request, empresa, config, forma_pago_codigo, cart_items, monto_total,
                                      doc_type, document_number, nature, direccion_envio,
                                      nombre_cliente, telefono_cliente, email_cliente)
        
        # Si no es mock, procesar con pasarela real
        logger.info(f"[ecommerce] Procesando con pasarela REAL: {pasarela_codigo}")
        
        # Verificar que las credenciales estén configuradas
        if not config.payment_public_key or not config.payment_secret_key:
            logger.error("[ecommerce] ❌ Credenciales de Credibanco no configuradas")
            return Response(
                {
                    'detail': 'Credenciales de Credibanco no configuradas. Configure payment_public_key y payment_secret_key en el panel de administración.',
                    'error_code': 'CREDENTIALS_MISSING'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return _procesar_pago_pasarela_real(request, empresa, config, pasarela, forma_pago_codigo, cart_items,
                                           monto_total, doc_type, document_number, nature, direccion_envio,
                                           nombre_cliente, telefono_cliente, email_cliente)
    else:
        # Para efectivo, transferencia, etc. - siempre procesar como mock (no requiere pasarela)
        return _procesar_pago_mock(request, empresa, config, forma_pago_codigo, cart_items, monto_total,
                                  doc_type, document_number, nature, direccion_envio,
                                  nombre_cliente, telefono_cliente, email_cliente)


def _procesar_pago_mock(request, empresa, config, forma_pago_codigo, cart_items, monto_total,
                       doc_type, document_number, nature, direccion_envio,
                       nombre_cliente, telefono_cliente, email_cliente):
    """Procesa pago en modo mock (simulado)"""
    import random
    import time
    import re
    
    empresa_servidor_id = empresa.id
    codigo_upper = forma_pago_codigo.upper()
    es_tarjeta = codigo_upper in ['TC', 'TD'] or 'TARJETA' in codigo_upper or 'CARD' in codigo_upper
    
    pago_data = {}
    
    if es_tarjeta:
        # Obtener datos de tarjeta del request
        tarjeta = request.data.get('tarjeta', {})
        numero_tarjeta = tarjeta.get('numero', '')
        nombre_titular = tarjeta.get('nombre_titular', '')
        mes_vencimiento = tarjeta.get('mes_vencimiento', '')
        anio_vencimiento = tarjeta.get('anio_vencimiento', '')
        cvv = tarjeta.get('cvv', '')
        
        # Validar datos de tarjeta
        numero_tarjeta_limpio = re.sub(r'\s', '', numero_tarjeta) if numero_tarjeta else ''
        if not numero_tarjeta or len(numero_tarjeta_limpio) < 13:
            return Response(
                {'detail': 'Número de tarjeta inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not nombre_titular:
            return Response(
                {'detail': 'Nombre del titular es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not mes_vencimiento or not anio_vencimiento:
            return Response(
                {'detail': 'Fecha de vencimiento es requerida'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not cvv or len(cvv) < 3:
            return Response(
                {'detail': 'CVV es requerido (mínimo 3 dígitos)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Simular procesamiento de pago (mock)
        time.sleep(2)  # Simular delay de procesamiento (2 segundos)
        
        # Determinar franquicia basada en el primer dígito
        primer_digito = numero_tarjeta_limpio[0] if numero_tarjeta_limpio else '4'
        franquicia = 'VISA'
        if primer_digito == '5':
            franquicia = 'MASTERCARD'
        elif primer_digito == '3':
            franquicia = 'AMEX'
        
        # Obtener últimos 4 dígitos
        ultimos_digitos = numero_tarjeta_limpio[-4:] if len(numero_tarjeta_limpio) >= 4 else '0000'
        
        # Generar datos mock del pago
        pago_data = {
            'codigo_autorizacion': f'{random.randint(100000, 999999)}',
            'franquicia': franquicia,
            'ultimos_digitos': ultimos_digitos,
            'tipo_cuenta': 'CREDITO',
            'numero_recibo': f'{random.randint(100000, 999999)}',
            'rrn': f'{random.randint(100000, 999999)}',
            'nombre_titular': nombre_titular,
            'fecha_vencimiento': f'{mes_vencimiento}/{anio_vencimiento}'
        }
    else:
        # Para efectivo, transferencia, etc. - no hay datos de tarjeta
        time.sleep(1)  # Simular delay más corto
        pago_data = {
            'codigo_autorizacion': None,
            'franquicia': None,
            'ultimos_digitos': None,
            'tipo_cuenta': None,
            'numero_recibo': f'{random.randint(100000, 999999)}',
            'rrn': None
        }
    
    # Construir observación con dirección de envío
    observacion_parts = []
    if direccion_envio:
        observacion_parts.append(f'DIRECCIÓN DE ENVÍO: {direccion_envio}')
    if telefono_cliente:
        observacion_parts.append(f'TEL: {telefono_cliente}')
    if nombre_cliente:
        observacion_parts.append(f'CLIENTE: {nombre_cliente}')
    observacion = ' - '.join(observacion_parts) if observacion_parts else direccion_envio
    
    # Crear factura en TNS
    try:
        from .services.tns_invoice_helper import insertar_factura_tns
        
        bridge = TNSBridge(empresa)
        bridge.connect()
        
        # Preparar invoice_data según el tipo de documento
        invoice_data = {
            'docType': doc_type,
            'document': document_number,
            'name': nombre_cliente or 'CONSUMIDOR FINAL',
            'email': email_cliente or '',
            'phone': telefono_cliente or '',
            'nature': nature
        }
        
        # Insertar factura
        resultado = insertar_factura_tns(
            bridge=bridge,
            cart_items=cart_items,
            monto_total=float(monto_total),
            empresa_servidor_id=empresa_servidor_id,
            invoice_data=invoice_data,
            order_type='takeaway',
            referencia=f'ECOMM-MOCK-{random.randint(100000, 999999)}',
            medio_pago_data=pago_data,
            forma_pago_codigo=forma_pago_codigo,
            mesa_number=None,
            observacion=observacion,
            usuario_tns=config.usuario_tns
        )
        
        bridge.close()
        
        if resultado.get('success'):
            return Response({
                'success': True,
                'mock': True,
                'pago': pago_data,
                'factura': {
                    'kardex_id': resultado.get('kardex_id'),
                    'prefijo': resultado.get('prefijo'),
                    'numero': resultado.get('numero'),
                    'nit_normalizado': resultado.get('nit_normalizado')
                }
            })
        else:
            return Response(
                {'detail': f'Error al crear factura: {resultado.get("error", "Error desconocido")}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    except Exception as exc:
        logger.error(f"Error procesando pago mock: {str(exc)}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(
            {'detail': f'Error al procesar pago: {str(exc)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _procesar_pago_pasarela_real(request, empresa, config, pasarela, forma_pago_codigo, cart_items,
                                 monto_total, doc_type, document_number, nature, direccion_envio,
                                 nombre_cliente, telefono_cliente, email_cliente):
    """Procesa pago con pasarela real (Credibanco, etc.)"""
    
    # Determinar qué pasarela es y llamar a su función específica
    if pasarela.codigo.lower() == 'credibanco':
        return _procesar_pago_credibanco(request, empresa, config, pasarela, forma_pago_codigo, cart_items,
                                        monto_total, doc_type, document_number, nature, direccion_envio,
                                        nombre_cliente, telefono_cliente, email_cliente)
    else:
        # Otras pasarelas futuras (Wompi, PayU, etc.)
        return Response(
            {'detail': f'Pasarela "{pasarela.codigo}" aún no implementada'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


def _procesar_pago_credibanco(request, empresa, config, pasarela, forma_pago_codigo, cart_items,
                              monto_total, doc_type, document_number, nature, direccion_envio,
                              nombre_cliente, telefono_cliente, email_cliente):
    """Procesa pago con Credibanco (API real)"""
    import time
    from urllib.parse import urlencode, quote
    import json
    
    # Obtener configuración de Credibanco
    pasarela_config = pasarela.configuracion or {}
    
    # URLs y endpoints
    api_url = pasarela_config.get('api_url', 'https://eco.credibanco.com/payment/rest/')
    register_endpoint = pasarela_config.get('register_endpoint', 'register.do')
    status_endpoint = pasarela_config.get('status_endpoint', 'getOrderStatusExtended.do')
    
    # Credenciales (prioridad: EmpresaEcommerceConfig > PasarelaPago.configuracion)
    user_name = config.payment_public_key or pasarela_config.get('user_name', '')
    password = config.payment_secret_key or pasarela_config.get('password', '')
    
    # Valores de configuración con defaults según PASARELADEPAGO
    currency_code = pasarela_config.get('currency_code', '170')  # Pesos colombianos
    plan_id = pasarela_config.get('plan_id', '01')  # Plan de cobranza
    quota_id = pasarela_config.get('quota_id', '012')  # Cuotas TDC
    language = pasarela_config.get('language', 'es')
    default_country = pasarela_config.get('default_country', 'CO')
    default_state = pasarela_config.get('default_state', 'NDS')  # Norte de Santander
    default_postal_code = pasarela_config.get('default_postal_code', '54001')
    default_gender = pasarela_config.get('default_gender', 'M')
    shipping_reception_method = pasarela_config.get('shipping_reception_method', 'ba')
    
    if not user_name or not password:
        return Response(
            {'detail': 'Credenciales de Credibanco no configuradas. Configure payment_public_key y payment_secret_key en el panel de administración.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Generar order_number único (timestamp)
    order_number = str(int(time.time() * 1000))  # Milisegundos
    
    # Obtener IP del cliente
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
    
    # Construir URLs de retorno
    dominio = request.get_host()
    protocolo = 'https' if request.is_secure() else 'http'
    return_url = f"{protocolo}://{dominio}/api/pasarela-response/"
    fail_url = f"{protocolo}://{dominio}/api/pasarela-response/"
    
    # Preparar datos del cliente
    nombres_parts = (nombre_cliente or '').split(' ', 1)
    billing_first_name = nombres_parts[0][:30] if nombres_parts else 'CLIENTE'
    billing_last_name = nombres_parts[1][:30] if len(nombres_parts) > 1 else 'ECOMMERCE'
    
    # Normalizar dirección (sin espacios para jsonParams)
    direccion_normalizada = direccion_envio.replace(' ', '')[:50] if direccion_envio else 'SIN_DIRECCION'
    
    # Construir jsonParams (similar a envio.php)
    # Nota: payerCity, payerPostalCode, payerState deberían venir del cliente si están disponibles
    # Por ahora usamos valores por defecto de la configuración
    json_params = {
        'IVA.amount': '000',
        'email': email_cliente or 'noreply@ecommerce.com',
        'postAddress': direccion_normalizada,
        'payerCity': 'BOGOTA',  # TODO: Obtener del cliente si está disponible
        'payerPostalCode': default_postal_code,
        'payerCountry': default_country,
        'payerState': default_state,  # TODO: Obtener del cliente si está disponible
        'docType': 'CC',  # Cédula de ciudadanía
        'docValue': document_number or '',
        'phone': f'+57{telefono_cliente}' if telefono_cliente else '+571234567890',
        'shippingAddress': direccion_envio[:50] if direccion_envio else ''
    }
    
    # Convertir jsonParams a string URL-encoded
    json_params_str = quote(json.dumps(json_params))
    
    # Monto en centavos (Credibanco espera en centavos)
    amount_centavos = int(float(monto_total) * 100)
    
    # Construir URL de register.do
    register_url = f"{api_url}{register_endpoint}"
    params = {
        'userName': user_name,
        'password': password,
        'orderNumber': order_number,
        'returnUrl': return_url,
        'failUrl': fail_url,
        'language': 'es',
        'amount': amount_centavos,
        'jsonParams': json_params_str
    }
    
    url_completa = f"{register_url}?{urlencode(params)}"
    
    # Crear TransaccionPago con estado PENDIENTE
    datos_cliente = {
        'nombre': nombre_cliente,
        'email': email_cliente,
        'telefono': telefono_cliente,
        'document_number': document_number,
        'doc_type': doc_type,
        'nature': nature,
        'direccion_envio': direccion_envio,
        'cart_items': cart_items,  # Guardar items del carrito para crear factura después
        'forma_pago_codigo': forma_pago_codigo
    }
    
    transaccion = TransaccionPago.objects.create(
        empresa_servidor=empresa,
        pasarela_pago=pasarela,
        order_number=order_number,
        monto=Decimal(str(monto_total)),
        estado='PENDIENTE',
        datos_cliente=datos_cliente
    )
    
    # Llamar a API de Credibanco
    try:
        import requests
        logger.info(f"[ecommerce] Llamando a Credibanco: {register_url}")
        logger.info(f"[ecommerce] Parámetros: userName={user_name}, orderNumber={order_number}, amount={amount_centavos}")
        
        # IMPORTANTE: Credibanco espera un POST, pero los parámetros van en la URL (query string)
        # No enviar datos en el body, solo en la URL
        response = requests.post(url_completa, timeout=30)
        response.raise_for_status()
        
        logger.info(f"[ecommerce] Respuesta de Credibanco recibida, status={response.status_code}")
        credibanco_response = response.json()
        logger.info(f"[ecommerce] Respuesta JSON de Credibanco: {credibanco_response}")
        
        # Verificar si hay error
        if 'errorCode' in credibanco_response:
            transaccion.estado = 'FALLIDA'
            transaccion.error_message = credibanco_response.get('errorMessage', 'Error desconocido')
            transaccion.datos_respuesta = credibanco_response
            transaccion.save()
            
            return Response(
                {
                    'detail': f'Error en Credibanco: {credibanco_response.get("errorMessage", "Error desconocido")}',
                    'error_code': credibanco_response.get('errorCode')
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Si hay formUrl, la transacción está en proceso
        form_url = credibanco_response.get('formUrl')
        if not form_url:
            transaccion.estado = 'FALLIDA'
            transaccion.error_message = 'Credibanco no retornó formUrl'
            transaccion.datos_respuesta = credibanco_response
            transaccion.save()
            
            return Response(
                {'detail': 'Credibanco no retornó formUrl'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Actualizar transacción con order_id si viene
        if 'orderId' in credibanco_response:
            transaccion.order_id = credibanco_response['orderId']
        
        transaccion.estado = 'PROCESANDO'
        transaccion.datos_respuesta = credibanco_response
        transaccion.save()
        
        return Response({
            'success': True,
            'mock': False,
            'formUrl': form_url,
            'order_number': order_number,
            'transaccion_id': transaccion.id,
            'pasarela': pasarela.codigo
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error llamando a Credibanco: {str(e)}")
        transaccion.estado = 'FALLIDA'
        transaccion.error_message = f'Error de conexión: {str(e)}'
        transaccion.save()
        
        return Response(
            {'detail': f'Error de conexión con Credibanco: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        logger.error(f"Error procesando pago Credibanco: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        transaccion.estado = 'FALLIDA'
        transaccion.error_message = str(e)
        transaccion.save()
        
        return Response(
            {'detail': f'Error al procesar pago: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def pasarela_response_view(request):
    """
    Endpoint de callback para Credibanco (y otras pasarelas futuras).
    Credibanco redirige aquí después de que el usuario completa el pago.
    
    Query params:
    - orderId: ID de orden de Credibanco (viene en la URL de retorno)
    
    Returns:
    - HTML con redirección al frontend con resultado del pago
    """
    order_id = request.query_params.get('orderId')
    
    if not order_id:
        return Response(
            {'detail': 'orderId es requerido'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Buscar transacción por order_id
        transaccion = TransaccionPago.objects.get(order_id=order_id)
    except TransaccionPago.DoesNotExist:
        logger.error(f"[pasarela-response] Transacción no encontrada para orderId: {order_id}")
        # Retornar HTML de error
        html_error = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error en el pago</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>Error</h1>
            <p>No se encontró la transacción de pago.</p>
            <script>
                setTimeout(function() {{
                    window.location.href = '/subdomain/ecommerce?payment_error=transaccion_no_encontrada';
                }}, 3000);
            </script>
        </body>
        </html>
        """
        return Response(html_error, content_type='text/html')
    
    # Obtener configuración de la empresa
    empresa = transaccion.empresa_servidor
    config = EmpresaEcommerceConfig.objects.get(empresa_servidor_id=empresa.id)
    pasarela = transaccion.pasarela_pago
    
    if not pasarela:
        logger.error(f"[pasarela-response] Pasarela no encontrada para transacción {transaccion.id}")
        html_error = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error en el pago</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>Error</h1>
            <p>Configuración de pasarela no encontrada.</p>
            <script>
                setTimeout(function() {{
                    window.location.href = '/subdomain/ecommerce?payment_error=configuracion_no_encontrada';
                }}, 3000);
            </script>
        </body>
        </html>
        """
        return Response(html_error, content_type='text/html')
    
    # Consultar estado del pago en Credibanco
    if pasarela.codigo.lower() == 'credibanco':
        try:
            pasarela_config = pasarela.configuracion or {}
            api_url = pasarela_config.get('api_url', 'https://eco.credibanco.com/payment/rest/')
            user_name = config.payment_public_key or pasarela_config.get('user_name', '')
            password = config.payment_secret_key or pasarela_config.get('password', '')
            
            if not user_name or not password:
                raise Exception('Credenciales de Credibanco no configuradas')
            
            import requests
            # Obtener configuración de la pasarela para el endpoint de status
            pasarela_config = transaccion.pasarela_pago.configuracion or {}
            api_url = pasarela_config.get('api_url', 'https://eco.credibanco.com/payment/rest/')
            status_endpoint = pasarela_config.get('status_endpoint', 'getOrderStatusExtended.do')
            
            # Obtener credenciales (prioridad: EmpresaEcommerceConfig > PasarelaPago.configuracion)
            ecommerce_config = EmpresaEcommerceConfig.objects.filter(
                empresa_servidor=transaccion.empresa_servidor
            ).first()
            user_name = (ecommerce_config.payment_public_key if ecommerce_config else None) or pasarela_config.get('user_name', '')
            password = (ecommerce_config.payment_secret_key if ecommerce_config else None) or pasarela_config.get('password', '')
            
            status_url = f"{api_url}{status_endpoint}"
            params = {
                'userName': user_name,
                'password': password,
                'orderId': order_id
            }
            
            response = requests.get(status_url, params=params, timeout=30)
            response.raise_for_status()
            
            credibanco_status = response.json()
            
            # Actualizar transacción con respuesta
            transaccion.datos_respuesta = credibanco_status
            
            # Extraer información importante
            error_code = credibanco_status.get('errorCode')
            error_message = credibanco_status.get('errorMessage')
            order_status = credibanco_status.get('orderStatus')
            action_code = credibanco_status.get('actionCode')
            action_code_description = credibanco_status.get('actionCodeDescription')
            
            # Obtener paymentState
            payment_state = None
            payment_amount_info = credibanco_status.get('paymentAmountInfo', {})
            if isinstance(payment_amount_info, dict):
                payment_state = payment_amount_info.get('paymentState')
            
            # Obtener approvalCode
            approval_code = None
            card_auth_info = credibanco_status.get('cardAuthInfo', {})
            if isinstance(card_auth_info, dict):
                approval_code = card_auth_info.get('approvalCode')
            
            if error_code:
                # Error en Credibanco
                transaccion.estado = 'FALLIDA'
                transaccion.error_message = error_message or 'Error desconocido'
                transaccion.save()
                
                html_error = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Error en el pago</title>
                    <meta charset="utf-8">
                </head>
                <body>
                    <h1>Error en el pago</h1>
                    <p>{error_message or 'Error desconocido'}</p>
                    <script>
                        setTimeout(function() {{
                            window.location.href = '/subdomain/ecommerce?payment_error={error_code}&order_number={transaccion.order_number}';
                        }}, 3000);
                    </script>
                </body>
                </html>
                """
                return Response(html_error, content_type='text/html')
            
            # Verificar si el pago fue exitoso
            if payment_state == 'DEPOSITED':
                # Pago exitoso
                transaccion.estado = 'EXITOSA'
                transaccion.approval_code = approval_code
                transaccion.save()
                
                # Crear factura en TNS
                try:
                    from .services.tns_invoice_helper import insertar_factura_tns
                    import random
                    
                    bridge = TNSBridge(empresa)
                    bridge.connect()
                    
                    datos_cliente = transaccion.datos_cliente
                    invoice_data = {
                        'docType': datos_cliente.get('doc_type', 'cedula'),
                        'document': datos_cliente.get('document_number', ''),
                        'name': datos_cliente.get('nombre', 'CONSUMIDOR FINAL'),
                        'email': datos_cliente.get('email', ''),
                        'phone': datos_cliente.get('telefono', ''),
                        'nature': datos_cliente.get('nature', 'natural')
                    }
                    
                    # Preparar datos del pago para TNS
                    medio_pago_data = {
                        'codigo_autorizacion': approval_code or 'N/A',
                        'franquicia': 'TARJETA',
                        'ultimos_digitos': '****',
                        'tipo_cuenta': 'CREDITO',
                        'numero_recibo': order_id[:20],
                        'rrn': order_id
                    }
                    
                    # Obtener cart_items de la transacción (se guardaron en datos_cliente o se pueden reconstruir)
                    # Por ahora, necesitamos guardar cart_items en TransaccionPago también
                    # Por simplicidad, asumimos que están en datos_cliente
                    cart_items = datos_cliente.get('cart_items', [])
                    
                    observacion = f'DIRECCIÓN DE ENVÍO: {datos_cliente.get("direccion_envio", "")}'
                    if datos_cliente.get('telefono'):
                        observacion += f' - TEL: {datos_cliente.get("telefono")}'
                    
                    forma_pago_codigo = datos_cliente.get('forma_pago_codigo', 'TC')  # Default a TC si no está
                    
                    resultado = insertar_factura_tns(
                        bridge=bridge,
                        cart_items=cart_items,
                        monto_total=float(transaccion.monto),
                        empresa_servidor_id=empresa.id,
                        invoice_data=invoice_data,
                        order_type='takeaway',
                        referencia=f'ECOMM-{transaccion.order_number}',
                        medio_pago_data=medio_pago_data,
                        forma_pago_codigo=forma_pago_codigo,
                        mesa_number=None,
                        observacion=observacion,
                        usuario_tns=config.usuario_tns
                    )
                    
                    bridge.close()
                    
                    if resultado.get('success'):
                        transaccion.factura_tns_id = resultado.get('kardex_id')
                        transaccion.save()
                        
                        html_success = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Pago exitoso</title>
                            <meta charset="utf-8">
                        </head>
                        <body>
                            <h1>¡Pago exitoso!</h1>
                            <p>Tu pedido ha sido procesado correctamente.</p>
                            <p>Número de factura: {resultado.get('prefijo')} {resultado.get('numero')}</p>
                            <script>
                                setTimeout(function() {{
                                    window.location.href = '/subdomain/ecommerce?payment_success=true&order_number={transaccion.order_number}&factura={resultado.get("prefijo")}-{resultado.get("numero")}';
                                }}, 3000);
                            </script>
                        </body>
                        </html>
                        """
                        return Response(html_success, content_type='text/html')
                    else:
                        logger.error(f"[pasarela-response] Error creando factura TNS: {resultado.get('error')}")
                        transaccion.error_message = f"Error creando factura: {resultado.get('error')}"
                        transaccion.save()
                        
                        html_error = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Error al crear factura</title>
                            <meta charset="utf-8">
                        </head>
                        <body>
                            <h1>Pago exitoso pero error al crear factura</h1>
                            <p>El pago fue procesado pero hubo un error al crear la factura. Por favor contacta al soporte.</p>
                            <script>
                                setTimeout(function() {{
                                    window.location.href = '/subdomain/ecommerce?payment_error=factura_error&order_number={transaccion.order_number}';
                                }}, 3000);
                            </script>
                        </body>
                        </html>
                        """
                        return Response(html_error, content_type='text/html')
                        
                except Exception as e:
                    logger.error(f"[pasarela-response] Error creando factura TNS: {str(e)}", exc_info=True)
                    transaccion.error_message = f"Error creando factura: {str(e)}"
                    transaccion.save()
                    
                    html_error = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Error al crear factura</title>
                        <meta charset="utf-8">
                    </head>
                    <body>
                        <h1>Pago exitoso pero error al crear factura</h1>
                        <p>El pago fue procesado pero hubo un error al crear la factura. Por favor contacta al soporte.</p>
                        <script>
                            setTimeout(function() {{
                                window.location.href = '/subdomain/ecommerce?payment_error=factura_error&order_number={transaccion.order_number}';
                            }}, 3000);
                        </script>
                    </body>
                    </html>
                    """
                    return Response(html_error, content_type='text/html')
            else:
                # Pago no exitoso
                transaccion.estado = 'FALLIDA'
                transaccion.error_message = action_code_description or 'Pago rechazado'
                transaccion.save()
                
                html_error = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Pago rechazado</title>
                    <meta charset="utf-8">
                </head>
                <body>
                    <h1>Pago rechazado</h1>
                    <p>{action_code_description or 'El pago fue rechazado'}</p>
                    <script>
                        setTimeout(function() {{
                            window.location.href = '/subdomain/ecommerce?payment_error=rechazado&order_number={transaccion.order_number}';
                        }}, 3000);
                    </script>
                </body>
                </html>
                """
                return Response(html_error, content_type='text/html')
                
        except Exception as e:
            logger.error(f"[pasarela-response] Error consultando estado Credibanco: {str(e)}", exc_info=True)
            transaccion.estado = 'FALLIDA'
            transaccion.error_message = f'Error consultando estado: {str(e)}'
            transaccion.save()
            
            html_error = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error</title>
                <meta charset="utf-8">
            </head>
            <body>
                <h1>Error al consultar estado del pago</h1>
                <p>Por favor contacta al soporte.</p>
                <script>
                    setTimeout(function() {{
                        window.location.href = '/subdomain/ecommerce?payment_error=consulta_error&order_number={transaccion.order_number}';
                    }}, 3000);
                </script>
            </body>
            </html>
            """
            return Response(html_error, content_type='text/html')
    else:
        # Otras pasarelas futuras
        return Response(
            {'detail': f'Pasarela "{pasarela.codigo}" aún no implementada para callback'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


@api_view(['GET'])
@permission_classes([AllowAny])  # Permitir API Key o JWT
def celery_task_status_view(request, task_id):
    """
    Consulta el estado de una tarea Celery por su ID.
    GET /api/celery/task-status/{task_id}/
    Permite autenticación con API Key o JWT.
    """
    # Intentar autenticar con API Key primero
    api_key_authenticated = _attach_api_key(request)
    
    # Si no hay API Key, intentar autenticar con JWT
    if not api_key_authenticated:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        jwt_auth = JWTAuthentication()
        try:
            user, token = jwt_auth.authenticate(request)
            if user and token:
                request.user = user
        except Exception:
            # JWT inválido o expirado, continuar sin autenticación
            pass
        
        # Verificar si hay usuario autenticado (JWT o API Key)
        if not (hasattr(request, 'user') and request.user.is_authenticated):
            return Response(
                {'error': 'Se requiere API Key o autenticación de usuario'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    
    from celery.result import AsyncResult
    from config.celery import app as celery_app
    
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        response_data = {
            'task_id': task_id,
            'state': task_result.state,
            'ready': task_result.ready(),
            'successful': task_result.successful() if task_result.ready() else None,
            'failed': task_result.failed() if task_result.ready() else None,
        }
        
        # Si la tarea está lista, incluir resultado
        if task_result.ready():
            if task_result.successful():
                response_data['result'] = task_result.result
            else:
                response_data['error'] = str(task_result.result) if task_result.result else 'Error desconocido'
        else:
            # Si está en progreso, incluir meta información
            if hasattr(task_result, 'info') and task_result.info:
                if isinstance(task_result.info, dict):
                    response_data['meta'] = task_result.info
                else:
                    response_data['meta'] = {'status': str(task_result.info)}
            # También verificar si hay información en el estado de la tarea
            if task_result.state == 'PROCESSING' and hasattr(task_result, 'info'):
                meta_info = task_result.info if isinstance(task_result.info, dict) else {}
                if meta_info:
                    response_data['meta'] = meta_info
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error consultando estado de tarea Celery {task_id}: {e}", exc_info=True)
        return Response(
            {'error': f'Error al consultar estado de tarea: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ConfiguracionS3ViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar configuraciones S3.
    """
    queryset = ConfiguracionS3.objects.all()
    serializer_class = ConfiguracionS3Serializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(activo=True)
        return queryset.order_by('-activo', 'nombre')
    
    def perform_create(self, serializer):
        serializer.save()
    
    def perform_update(self, serializer):
        serializer.save()


class BackupS3ViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar backups S3.
    """
    queryset = BackupS3.objects.all()
    serializer_class = BackupS3Serializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        empresa_id = self.request.query_params.get('empresa_id')
        if empresa_id:
            queryset = queryset.filter(empresa_servidor_id=empresa_id)
        return queryset.order_by('-fecha_backup')
    
    @action(detail=False, methods=['post'])
    def realizar_backup(self, request):
        """
        Realiza un backup manual de una empresa.
        """
        empresa_id = request.data.get('empresa_id')
        configuracion_s3_id = request.data.get('configuracion_s3_id')
        
        if not empresa_id or not configuracion_s3_id:
            return Response(
                {'error': 'Se requiere empresa_id y configuracion_s3_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .tasks import realizar_backup_empresa_task
            task = realizar_backup_empresa_task.delay(empresa_id, configuracion_s3_id)
            
            return Response({
                'status': 'started',
                'task_id': task.id,
                'mensaje': 'Backup iniciado. Consulta el estado con el task_id.'
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Error iniciando backup: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='servidores-disponibles')
    def servidores_disponibles(self, request):
        """
        Lista los servidores disponibles para la API Key.
        Solo retorna servidores que tienen empresas asociadas a la API Key.
        """
        # Verificar autenticación: API Key o superusuario
        tiene_api_key = hasattr(request, 'cliente_api') and request.cliente_api
        es_superusuario = request.user.is_authenticated and request.user.is_superuser
        
        if not tiene_api_key and not es_superusuario:
            return Response(
                {
                    'error': 'Se requiere API Key válida o autenticación de superusuario',
                    'info': 'Si tienes una API Key, envíala en el header: Api-Key: <tu_api_key>'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        if tiene_api_key and not es_superusuario:
            empresas_autorizadas = request.empresas_autorizadas
            # Obtener servidores únicos de las empresas autorizadas
            servidores = Servidor.objects.filter(
                empresas_servidor__in=empresas_autorizadas
            ).distinct().values('id', 'nombre')
            
            servidores_list = [
                {
                    'id': s['id'],
                    'nombre': s['nombre'],
                    'nombre_normalizado': s['nombre'].replace(' ', '_').replace('/', '_').replace('\\', '_')
                }
                for s in servidores
            ]
        else:
            # Superusuario: todos los servidores
            servidores = Servidor.objects.all().values('id', 'nombre')
            servidores_list = [
                {
                    'id': s['id'],
                    'nombre': s['nombre'],
                    'nombre_normalizado': s['nombre'].replace(' ', '_').replace('/', '_').replace('\\', '_')
                }
                for s in servidores
            ]
        
        return Response({
            'servidores': servidores_list,
            'total': len(servidores_list)
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='listar-archivos')
    def listar_archivos_s3(self, request):
        """
        Lista archivos y carpetas en S3 para un servidor específico.
        Solo muestra NITs autorizados para la API Key.
        
        Parámetros:
        - servidor_id: ID del servidor (requerido)
        - prefix: Prefijo de ruta en S3 (opcional, para navegar carpetas)
        """
        # Verificar autenticación
        tiene_api_key = hasattr(request, 'cliente_api') and request.cliente_api
        es_superusuario = request.user.is_authenticated and request.user.is_superuser
        
        if not tiene_api_key and not es_superusuario:
            return Response(
                {
                    'error': 'Se requiere API Key válida o autenticación de superusuario',
                    'info': 'Si tienes una API Key, envíala en el header: Api-Key: <tu_api_key>'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        servidor_id = request.query_params.get('servidor_id')
        prefix = request.query_params.get('prefix', '').strip()
        
        if not servidor_id:
            return Response(
                {'error': 'Se requiere servidor_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            servidor = Servidor.objects.get(id=servidor_id)
        except Servidor.DoesNotExist:
            return Response(
                {'error': 'Servidor no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validar que el servidor esté autorizado
        if tiene_api_key and not es_superusuario:
            empresas_autorizadas = request.empresas_autorizadas
            if not empresas_autorizadas.filter(servidor_id=servidor_id).exists():
                return Response(
                    {'error': 'No tienes permiso para acceder a este servidor'},
                    status=status.HTTP_403_FORBIDDEN
                )
            nits_autorizados = set(empresas_autorizadas.values_list('nit_normalizado', flat=True))
        else:
            nits_autorizados = None  # Superusuario: todos los NITs
        
        # Obtener configuración S3 activa
        try:
            config_s3 = ConfiguracionS3.objects.filter(activo=True).first()
            if not config_s3:
                return Response(
                    {'error': 'No hay configuración S3 activa'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            logger.error(f"Error obteniendo configuración S3: {e}", exc_info=True)
            return Response(
                {'error': 'Error obteniendo configuración S3'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        try:
            from .services.backup_s3_service import BackupS3Service
            servicio = BackupS3Service(config_s3)
            
            # Normalizar nombre del servidor
            server_name = servidor.nombre.replace(' ', '_').replace('/', '_').replace('\\', '_')
            
            # Construir prefijo base
            if prefix:
                base_prefix = prefix
            else:
                base_prefix = f"{server_name}/"
            
            # Listar objetos en S3
            paginator = servicio.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=servicio.bucket_name, Prefix=base_prefix, Delimiter='/')
            
            carpetas = []
            archivos = []
            
            for page in pages:
                # Carpetas (CommonPrefixes)
                if 'CommonPrefixes' in page:
                    for prefix_obj in page['CommonPrefixes']:
                        folder_path = prefix_obj['Prefix']
                        folder_name = folder_path.replace(base_prefix, '').rstrip('/')
                        
                        # Validar que la carpeta pertenezca a un NIT autorizado
                        if nits_autorizados is not None:
                            # Extraer NIT del path: server_name/nit_normalizado/...
                            parts = folder_path.split('/')
                            if len(parts) >= 2:
                                nit_en_path = parts[1]  # Segundo elemento es el NIT
                                if nit_en_path not in nits_autorizados:
                                    continue
                        
                        carpetas.append({
                            'nombre': folder_name,
                            'ruta': folder_path,
                            'tipo': 'carpeta'
                        })
                
                # Archivos
                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Omitir "carpetas" (objetos que terminan en /)
                        if obj['Key'].endswith('/'):
                            continue
                        
                        file_path = obj['Key']
                        file_name = file_path.replace(base_prefix, '')
                        
                        # Validar que el archivo pertenezca a un NIT autorizado
                        if nits_autorizados is not None:
                            parts = file_path.split('/')
                            if len(parts) >= 2:
                                nit_en_path = parts[1]
                                if nit_en_path not in nits_autorizados:
                                    continue
                        
                        archivos.append({
                            'nombre': file_name,
                            'ruta': file_path,
                            'tipo': 'archivo',
                            'tamano': obj['Size'],
                            'fecha_modificacion': obj['LastModified'].isoformat() if 'LastModified' in obj else None
                        })
            
            return Response({
                'carpetas': sorted(carpetas, key=lambda x: x['nombre']),
                'archivos': sorted(archivos, key=lambda x: x['nombre']),
                'prefijo_actual': base_prefix,
                'servidor': {
                    'id': servidor.id,
                    'nombre': servidor.nombre
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error listando archivos S3: {e}", exc_info=True)
            return Response(
                {'error': f'Error listando archivos: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='descargar-archivo')
    def descargar_archivo_s3(self, request):
        """
        Genera una URL temporal para descargar un archivo de S3.
        
        Parámetros:
        - ruta: Ruta completa del archivo en S3 (requerido)
        """
        # Verificar autenticación
        tiene_api_key = hasattr(request, 'cliente_api') and request.cliente_api
        es_superusuario = request.user.is_authenticated and request.user.is_superuser
        
        if not tiene_api_key and not es_superusuario:
            return Response(
                {
                    'error': 'Se requiere API Key válida o autenticación de superusuario',
                    'info': 'Si tienes una API Key, envíala en el header: Api-Key: <tu_api_key>'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        ruta = request.query_params.get('ruta')
        if not ruta:
            return Response(
                {'error': 'Se requiere el parámetro ruta'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar que la ruta pertenezca a un NIT autorizado
        if tiene_api_key and not es_superusuario:
            empresas_autorizadas = request.empresas_autorizadas
            nits_autorizados = set(empresas_autorizadas.values_list('nit_normalizado', flat=True))
            
            # Extraer NIT del path
            parts = ruta.split('/')
            if len(parts) >= 2:
                nit_en_path = parts[1]
                if nit_en_path not in nits_autorizados:
                    return Response(
                        {'error': 'No tienes permiso para acceder a este archivo'},
                        status=status.HTTP_403_FORBIDDEN
                    )
        
        # Obtener configuración S3
        try:
            config_s3 = ConfiguracionS3.objects.filter(activo=True).first()
            if not config_s3:
                return Response(
                    {'error': 'No hay configuración S3 activa'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            logger.error(f"Error obteniendo configuración S3: {e}", exc_info=True)
            return Response(
                {'error': 'Error obteniendo configuración S3'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        try:
            from .services.backup_s3_service import BackupS3Service
            servicio = BackupS3Service(config_s3)
            
            # Generar URL presignada (válida por 1 hora)
            url = servicio.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': servicio.bucket_name, 'Key': ruta},
                ExpiresIn=3600
            )
            
            return Response({
                'url': url,
                'ruta': ruta,
                'expira_en': 3600
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error generando URL de descarga: {e}", exc_info=True)
            return Response(
                {'error': f'Error generando URL de descarga: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['delete'])
    def eliminar_backup(self, request, pk=None):
        """
        Elimina un backup de S3 y de la BD.
        """
        try:
            backup = self.get_object()
            from .models import ConfiguracionS3
            from .services.backup_s3_service import BackupS3Service
            
            config_s3 = backup.configuracion_s3
            if not config_s3:
                return Response(
                    {'error': 'Backup no tiene configuración S3 asociada'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            servicio = BackupS3Service(config_s3)
            if servicio.eliminar_backup(backup.id):
                return Response(
                    {'mensaje': 'Backup eliminado exitosamente'},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': 'Error al eliminar backup'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except BackupS3.DoesNotExist:
            return Response(
                {'error': 'Backup no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error eliminando backup: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def estadisticas_empresa(self, request):
        """
        Obtiene estadísticas de backups para una empresa.
        """
        empresa_id = request.query_params.get('empresa_id')
        if not empresa_id:
            return Response(
                {'error': 'Se requiere empresa_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .models import EmpresaServidor, ConfiguracionS3
            from .services.backup_s3_service import BackupS3Service
            
            empresa = EmpresaServidor.objects.get(id=empresa_id)
            config_s3 = ConfiguracionS3.objects.filter(activo=True).first()
            
            if not config_s3:
                return Response(
                    {'error': 'No hay configuración S3 activa'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            servicio = BackupS3Service(config_s3)
            excede, tamano_actual, limite = servicio.verificar_limite_espacio(empresa)
            
            backups = BackupS3.objects.filter(empresa_servidor=empresa, estado='completado')
            
            return Response({
                'empresa_id': empresa_id,
                'empresa_nombre': empresa.nombre,
                'tamano_actual_gb': tamano_actual,
                'limite_gb': limite,
                'excede_limite': tamano_actual >= limite,
                'total_backups': backups.count(),
                'backups_por_anio': {
                    str(anio): backups.filter(anio_fiscal=anio).count()
                    for anio in backups.values_list('anio_fiscal', flat=True).distinct()
                }
            }, status=status.HTTP_200_OK)
            
        except EmpresaServidor.DoesNotExist:
            return Response(
                {'error': 'Empresa no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def solicitar_descarga_gdb(self, request, pk=None):
        """
        Solicita la conversión de un backup a GDB y envío por correo.
        Para GDB, se requiere email y se envía un link seguro de descarga.
        
        Body:
            email: Email del destinatario
        """
        try:
            backup = self.get_object()
            email = request.data.get('email')
            
            if not email:
                return Response(
                    {'error': 'Se requiere un email para descargar en formato GDB'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar formato de email
            import re
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return Response(
                    {'error': 'Email inválido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from .models import DescargaTemporalBackup, ConfiguracionS3
            from .tasks import convertir_backup_a_gdb_task
            import secrets
            from datetime import timedelta
            
            # Generar token único y seguro
            token = secrets.token_urlsafe(48)
            
            # Crear registro de descarga temporal
            descarga_temporal = DescargaTemporalBackup.objects.create(
                backup=backup,
                token=token,
                email=email,
                estado='pendiente',
                fecha_expiracion=timezone.now() + timedelta(days=1)
            )
            
            # Iniciar tarea Celery para convertir y enviar correo
            convertir_backup_a_gdb_task.delay(descarga_temporal.id)
            
            logger.info(f"Descarga GDB solicitada para backup {backup.id}, email: {email}, token: {token[:8]}...")
            
            return Response({
                'mensaje': 'Solicitud recibida. Se está procesando la conversión a GDB. Recibirás un correo con el link de descarga en breve.',
                'token': token,  # Solo para debugging, no se debe exponer en producción
                'fecha_expiracion': descarga_temporal.fecha_expiracion
            }, status=status.HTTP_202_ACCEPTED)
            
        except BackupS3.DoesNotExist:
            return Response(
                {'error': 'Backup no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error solicitando descarga GDB: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='solicitar_descarga_fbk')
    def solicitar_descarga_fbk(self, request, pk=None):
        """
        Solicita el envío de un backup FBK por correo.
        Similar a solicitar_descarga_gdb pero para FBK (no requiere conversión).
        
        Body:
            email: Email del destinatario
        """
        try:
            backup = self.get_object()
            email = request.data.get('email')
            
            if not email:
                return Response(
                    {'error': 'Se requiere un email para descargar en formato FBK'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar formato de email
            import re
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return Response(
                    {'error': 'Email inválido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from .models import DescargaTemporalBackup
            from .tasks import enviar_backup_fbk_por_email_task
            import secrets
            from datetime import timedelta
            
            # Generar token único y seguro
            token = secrets.token_urlsafe(48)
            
            # Crear registro de descarga temporal
            descarga_temporal = DescargaTemporalBackup.objects.create(
                backup=backup,
                token=token,
                email=email,
                estado='pendiente',
                fecha_expiracion=timezone.now() + timedelta(days=1)
            )
            
            # Iniciar tarea Celery para enviar correo con link de descarga
            enviar_backup_fbk_por_email_task.delay(descarga_temporal.id)
            
            logger.info(f"Descarga FBK solicitada para backup {backup.id}, email: {email}, token: {token[:8]}...")
            
            return Response({
                'mensaje': 'Solicitud recibida. Recibirás un correo con el link de descarga en breve.',
                'token': token,  # Solo para debugging
                'fecha_expiracion': descarga_temporal.fecha_expiracion
            }, status=status.HTTP_202_ACCEPTED)
            
        except BackupS3.DoesNotExist:
            return Response(
                {'error': 'Backup no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error solicitando descarga FBK: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def descargar_backup(self, request, pk=None):
        """
        Descarga un backup desde S3 en formato FBK (descarga directa).
        Para GDB, usar el endpoint solicitar_descarga_gdb.
        
        Query params:
            formato: 'fbk' (default: 'fbk')
        """
        from django.http import HttpResponse, FileResponse
        import tempfile
        import os
        
        try:
            backup = self.get_object()
            formato = request.query_params.get('formato', 'fbk').lower()
            
            if formato not in ['fbk']:
                return Response(
                    {'error': 'Para descargar en formato GDB, usa el endpoint solicitar_descarga_gdb con tu email'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from .models import ConfiguracionS3
            from .services.backup_s3_service import BackupS3Service
            
            config_s3 = backup.configuracion_s3
            if not config_s3:
                return Response(
                    {'error': 'Backup no tiene configuración S3 asociada'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            servicio = BackupS3Service(config_s3)
            
            # Descargar FBK desde S3 a archivo temporal
            temp_dir = tempfile.gettempdir()
            temp_fbk = os.path.join(temp_dir, f"backup_{backup.id}_{backup.nombre_archivo}")
            
            try:
                servicio.s3_client.download_file(
                    servicio.bucket_name,
                    backup.ruta_s3,
                    temp_fbk
                )
                
                # Devolver FBK directamente
                nombre_descarga = backup.nombre_archivo
                response = FileResponse(
                    open(temp_fbk, 'rb'),
                    content_type='application/octet-stream'
                )
                response['Content-Disposition'] = f'attachment; filename="{nombre_descarga}"'
                return response
                
            except Exception as e:
                logger.error(f"Error descargando backup: {e}", exc_info=True)
                # Limpiar archivos temporales
                if os.path.exists(temp_fbk):
                    os.remove(temp_fbk)
                return Response(
                    {'error': f'Error al descargar backup: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except BackupS3.DoesNotExist:
            return Response(
                {'error': 'Backup no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error en descargar_backup: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([AllowAny])
def descargar_backup_por_token(request, token):
    """
    Endpoint público para descargar un backup (FBK o GDB) usando un token seguro.
    No requiere autenticación, solo el token válido.
    
    GET /api/backups-s3/descargar_backup_token/{token}/?formato=fbk|gdb
    """
    from django.http import FileResponse, Http404
    from .models import DescargaTemporalBackup, ConfiguracionS3
    from .services.backup_s3_service import BackupS3Service
    import os
    import tempfile
    
    try:
        descarga = DescargaTemporalBackup.objects.get(token=token)
        formato = request.query_params.get('formato', 'gdb').lower()
        
        # Verificar que no esté expirado
        if descarga.esta_expirado():
            descarga.estado = 'expirado'
            descarga.save()
            return Response(
                {'error': 'El link de descarga ha expirado. Solicita uno nuevo.'},
                status=status.HTTP_410_GONE
            )
        
        backup = descarga.backup
        
        if formato == 'gdb':
            # Para GDB, usar ruta temporal (ya convertido)
            if descarga.estado != 'listo':
                return Response(
                    {'error': f'El archivo aún no está listo. Estado: {descarga.estado}'},
                    status=status.HTTP_202_ACCEPTED
                )
            
            if not descarga.ruta_gdb_temporal or not os.path.exists(descarga.ruta_gdb_temporal):
                return Response(
                    {'error': 'El archivo no está disponible. Contacta al administrador.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            nombre_archivo = os.path.basename(descarga.ruta_gdb_temporal)
            archivo_path = descarga.ruta_gdb_temporal
        else:
            # Para FBK, descargar desde S3
            config_s3 = backup.configuracion_s3
            if not config_s3:
                return Response(
                    {'error': 'Backup no tiene configuración S3 asociada'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            servicio = BackupS3Service(config_s3)
            temp_dir = tempfile.gettempdir()
            temp_fbk = os.path.join(temp_dir, f"backup_{backup.id}_{backup.nombre_archivo}")
            
            try:
                servicio.s3_client.download_file(
                    servicio.bucket_name,
                    backup.ruta_s3,
                    temp_fbk
                )
                nombre_archivo = backup.nombre_archivo
                archivo_path = temp_fbk
            except Exception as e:
                logger.error(f"Error descargando FBK desde S3: {e}", exc_info=True)
                return Response(
                    {'error': f'Error al descargar backup desde S3: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # Actualizar estadísticas
        descarga.intentos_descarga += 1
        if descarga.intentos_descarga == 1:
            descarga.fecha_descarga = timezone.now()
        descarga.save()
        
        # Devolver archivo
        response = FileResponse(
            open(archivo_path, 'rb'),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        
        logger.info(f"Descarga exitosa de backup {formato.upper()} con token {token[:8]}... (intento {descarga.intentos_descarga})")
        
        return response
        
    except DescargaTemporalBackup.DoesNotExist:
        return Response(
            {'error': 'Token inválido o link no encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error descargando backup por token: {e}", exc_info=True)
        return Response(
            {'error': 'Error al descargar el archivo'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== ViewSet para Comunicación (SMS y Llamadas) ====================

class ComunicacionViewSet(APIKeyAwareViewSet, viewsets.ViewSet):
    """
    ViewSet organizado para gestión de comunicación telefónica.
    Proporciona endpoints para SMS, llamadas y comunicación mixta.
    
    Endpoints disponibles:
    - POST /api/comunicacion/enviar-sms/ - Enviar SMS
    - POST /api/comunicacion/enviar-llamada/ - Enviar llamada TTS
    - POST /api/comunicacion/enviar-mixto/ - Enviar llamada + SMS de respaldo
    - GET /api/comunicacion/verificar-sms/<sms_id>/ - Verificar estado de SMS
    - GET /api/comunicacion/verificar-llamada/<call_id>/ - Verificar estado de llamada
    """
    
    def get_queryset(self):
        """ViewSet no usa modelos, retorna queryset vacío"""
        from django.contrib.auth.models import User
        return User.objects.none()
    
    @action(detail=False, methods=['post'], url_path='enviar-sms')
    def enviar_sms(self, request):
        """
        Envía un SMS a través de la API de Hablame.
        
        Body:
            telefono: Número de teléfono (10 dígitos, sin indicativo)
            mensaje: Mensaje a enviar (máximo 160 caracteres)
            flash: (opcional) Si es True, el SMS aparece directamente en pantalla
            prioridad: (opcional) Si es True, envía con prioridad alta (default: True)
        
        Returns:
            {
                "success": bool,
                "sms_id": str,
                "costo": int,
                "estado": str,
                "telefono": str,
                "mensaje": str
            }
        """
        from .serializers import EnviarSMSSerializer
        from .services.hablame_service import hablame_service
        
        serializer = EnviarSMSSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        datos = serializer.validated_data
        telefono = datos['telefono']
        mensaje = datos['mensaje']
        flash = datos.get('flash', False)
        prioridad = datos.get('prioridad', True)
        
        logger.info(f"📱 [SMS] Solicitud de envío a {telefono}")
        
        resultado = hablame_service.enviar_sms(
            telefono=telefono,
            mensaje=mensaje,
            flash=flash,
            prioridad=prioridad
        )
        
        if resultado.get('success'):
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(
                resultado,
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], url_path='enviar-llamada')
    def enviar_llamada(self, request):
        """
        Envía una llamada TTS (Text-to-Speech) a través de la API de Hablame.
        
        Body:
            telefono: Número de teléfono (10 dígitos, sin indicativo)
            mensaje: Mensaje a convertir a voz (máximo 500 caracteres)
            duplicar_mensaje: (opcional) Si es True, duplica el mensaje para mejor comprensión (default: True)
        
        Returns:
            {
                "success": bool,
                "call_id": str,
                "costo": int,
                "estado": str ("contestada" | "no_contestada"),
                "duracion": str,
                "telefono": str,
                "mensaje": str
            }
        """
        from .serializers import EnviarLlamadaSerializer
        from .services.hablame_service import hablame_service
        
        serializer = EnviarLlamadaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        datos = serializer.validated_data
        telefono = datos['telefono']
        mensaje = datos['mensaje']
        duplicar_mensaje = datos.get('duplicar_mensaje', True)
        
        logger.info(f"📞 [LLAMADA] Solicitud de envío a {telefono}")
        
        resultado = hablame_service.enviar_llamada(
            telefono=telefono,
            mensaje=mensaje,
            duplicar_mensaje=duplicar_mensaje
        )
        
        if resultado.get('success'):
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(
                resultado,
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], url_path='enviar-mixto')
    def enviar_mixto(self, request):
        """
        Envía primero una llamada y si no contesta, envía un SMS de respaldo.
        Estrategia de comunicación mixta para mayor efectividad.
        
        Body:
            telefono: Número de teléfono (10 dígitos, sin indicativo)
            mensaje: Mensaje a enviar (máximo 160 caracteres para SMS)
        
        Returns:
            {
                "success": bool,
                "tipo": "mixto",
                "metodo_efectivo": str ("llamada" | "sms"),
                "llamada": dict,
                "sms": dict,
                "costo_total": int
            }
        """
        from .serializers import EnviarMixtoSerializer
        from .services.hablame_service import hablame_service
        
        serializer = EnviarMixtoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        datos = serializer.validated_data
        telefono = datos['telefono']
        mensaje = datos['mensaje']
        
        logger.info(f"📞📱 [MIXTO] Solicitud de envío mixto a {telefono}")
        
        resultado = hablame_service.enviar_mixto(
            telefono=telefono,
            mensaje=mensaje
        )
        
        if resultado.get('success'):
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(
                resultado,
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], url_path='verificar-sms/(?P<sms_id>[^/.]+)')
    def verificar_sms(self, request, sms_id=None):
        """
        Verifica el estado de un SMS enviado.
        
        URL: /api/comunicacion/verificar-sms/<sms_id>/
        
        Returns:
            {
                "sms_id": str,
                "estado": dict,
                "precio": int,
                "data": dict
            }
        """
        from .services.hablame_service import hablame_service
        
        if not sms_id:
            return Response(
                {'error': 'sms_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"🔍 [SMS] Verificando estado de SMS: {sms_id}")
        
        estado = hablame_service.verificar_estado_sms(sms_id)
        
        return Response({
            'sms_id': sms_id,
            'estado': estado
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='verificar-llamada/(?P<call_id>[^/.]+)')
    def verificar_llamada(self, request, call_id=None):
        """
        Verifica el estado de una llamada TTS.
        
        URL: /api/comunicacion/verificar-llamada/<call_id>/
        
        Returns:
            {
                "call_id": str,
                "estado": dict,
                "data": dict
            }
        """
        from .services.hablame_service import hablame_service
        
        if not call_id:
            return Response(
                {'error': 'call_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"🔍 [LLAMADA] Verificando estado de llamada: {call_id}")
        
        estado = hablame_service.verificar_estado_llamada(call_id)
        
        if estado:
            return Response({
                'call_id': call_id,
                'estado': estado
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'No se pudo obtener el estado de la llamada'},
                status=status.HTTP_404_NOT_FOUND
            )


# ==================== ViewSet para Clasificación Contable ====================

class ClasificacionContableViewSet(APIKeyAwareViewSet, viewsets.ViewSet):
    """
    ViewSet para clasificación contable de facturas usando servicios de IA/Analytics.
    Acepta factura directa o session_id para cargar desde sesión DIAN.
    """
    permission_classes = [AllowAny]  # Permitir acceso con API Key o usuario autenticado
    
    def get_queryset(self):
        """ViewSet no usa modelos directamente"""
        from django.contrib.auth.models import User
        return User.objects.none()
    
    def initial(self, request, *args, **kwargs):
        """Sobrescribir initial para autenticar con API Key antes de procesar"""
        # Intentar autenticar con API Key
        if not _attach_api_key(request):
            # Si no hay API Key, verificar si hay usuario autenticado
            if not (hasattr(request, 'user') and request.user.is_authenticated):
                return Response(
                    {'error': 'Se requiere API Key o autenticación de usuario'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        return super().initial(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'], url_path='clasificar-factura')
    def clasificar_factura(self, request):
        """
        Clasificar factura(s) contable usando servicios de IA/Analytics.
        
        Acepta 4 modos:
        1. Factura directa: Enviar 'factura' en el body
        2. Sesión DIAN: Enviar 'session_id' para cargar todas las facturas
        3. Documento individual: Enviar 'document_id' para clasificar un documento específico
        4. Documentos masivos: Enviar 'document_ids' para clasificar múltiples documentos
        
        IMPORTANTE:
        - Si session_id: Se determina empresa/proveedor según tipo de sesión (Received/Sent)
        - Si document_id/document_ids: Se determina empresa/proveedor desde el documento
        - CIUU se busca automáticamente desde RUT (cacheado)
        
        Body:
            factura: (opcional) Dict con factura individual
            session_id: (opcional) ID de sesión DIAN
            document_id: (opcional) ID de documento específico
            document_ids: (opcional) Lista de IDs de documentos
            empresa_nit: (opcional) Se obtiene de sesión/documento si no se proporciona
            empresa_ciuu_principal: (opcional) Se busca en RUT si no se proporciona
            proveedor_nit: (opcional) Se obtiene de documento si no se proporciona
            aplica_retencion: (opcional) Si aplica retención
            porcentaje_retencion: (opcional) Porcentaje de retención
            tipo_operacion: (opcional) compra/venta
            procesar_asincrono: (opcional) Si True, usa Celery
        
        Returns:
            Resultado de clasificación o task_id si es asíncrono
        """
        import traceback
        
        try:
            print(f"🔍 [CLASIFICACION] ========== INICIO ==========")
            print(f"🔍 [CLASIFICACION] Payload recibido: {request.data}")
            print(f"🔍 [CLASIFICACION] Headers: {dict(request.headers)}")
            
            from .serializers import ClasificarFacturaSerializer
            from .services.clasificador_contable_service import ClasificadorContableService
            from .tasks import clasificar_factura_contable_task
            from celery import group
            import time
            
            print(f"🔍 [CLASIFICACION] Imports completados")
            serializer = ClasificarFacturaSerializer(data=request.data)
            if not serializer.is_valid():
                print(f"❌ [CLASIFICACION] Errores de validación: {serializer.errors}")
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )
            print(f"✅ [CLASIFICACION] Serializer válido")
            
            datos = serializer.validated_data
            servicio = ClasificadorContableService()
            
            # Determinar facturas a procesar según modo
            facturas = []
            session_dian_id = None
            empresa_nit = None
            empresa_ciuu_principal = None
            empresa_ciuu_secundarios = []
            
            if datos.get('session_id'):
            # Modo sesión DIAN: cargar todas las facturas
                session_dian_id = datos['session_id']
                facturas_list, empresa_nit, empresa_ciuu_info = servicio.leer_facturas_desde_excel_sesion(session_dian_id)
                
                if not facturas_list:
                    return Response(
                        {'error': f'No se encontraron facturas en la sesión {session_dian_id}'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                facturas = facturas_list
                empresa_ciuu_principal = empresa_ciuu_info.get('ciuu_principal')
                empresa_ciuu_secundarios = empresa_ciuu_info.get('ciuu_secundarios', [])
                
                logger.info(f"📂 {len(facturas)} facturas cargadas desde sesión DIAN {session_dian_id}")
                
            elif datos.get('document_id'):
                # Modo documento individual
                print(f"🔍 [CLASIFICACION] Leyendo documento ID: {datos['document_id']}")
                doc_info = servicio.leer_documento_por_id(datos['document_id'])
                print(f"🔍 [CLASIFICACION] doc_info obtenido: {doc_info is not None}")
                
                if not doc_info:
                    print(f"❌ [CLASIFICACION] Documento {datos['document_id']} no encontrado")
                    return Response(
                        {'error': f'Documento {datos["document_id"]} no encontrado'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                facturas = [doc_info['factura']]
                empresa_nit = doc_info['empresa_nit']
                empresa_ciuu_principal = doc_info['empresa_ciuu_info'].get('ciuu_principal')
                empresa_ciuu_secundarios = doc_info['empresa_ciuu_info'].get('ciuu_secundarios', [])
                session_dian_id = doc_info['session_id']
                
                print(f"✅ [CLASIFICACION] Documento {datos['document_id']} cargado - empresa_nit: {empresa_nit}")
                logger.info(f"📄 Documento {datos['document_id']} cargado")
                
            elif datos.get('document_ids'):
                # Modo documentos masivos
                facturas = []
                empresa_nit = None
                empresa_ciuu_principal = None
                empresa_ciuu_secundarios = []
                
                for doc_id in datos['document_ids']:
                    doc_info = servicio.leer_documento_por_id(doc_id)
                    if doc_info:
                        facturas.append(doc_info['factura'])
                        # Usar datos del primer documento para empresa (deben ser iguales)
                        if not empresa_nit:
                            empresa_nit = doc_info['empresa_nit']
                            empresa_ciuu_principal = doc_info['empresa_ciuu_info'].get('ciuu_principal')
                            empresa_ciuu_secundarios = doc_info['empresa_ciuu_info'].get('ciuu_secundarios', [])
                            session_dian_id = doc_info['session_id']
                
                if not facturas:
                    return Response(
                        {'error': 'No se encontraron documentos válidos'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                logger.info(f"📄 {len(facturas)} documentos cargados")
                
            else:
                # Modo factura directa
                facturas = [datos['factura']]
                empresa_nit = datos.get('empresa_nit')
            
            # Usar valores proporcionados o buscar desde RUT
            empresa_nit = datos.get('empresa_nit') or empresa_nit
            if not empresa_nit:
                return Response(
                    {'error': 'empresa_nit es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Buscar CIUU de empresa si no se tiene
            if not empresa_ciuu_principal:
                empresa_ciuu_principal = datos.get('empresa_ciuu_principal')
                empresa_ciuu_secundarios = datos.get('empresa_ciuu_secundarios', [])
                
                if not empresa_ciuu_principal:
                    rut_empresa = servicio.buscar_rut_por_nit(empresa_nit)
                    if rut_empresa:
                        empresa_ciuu_principal = rut_empresa.get('ciuu_principal')
                        empresa_ciuu_secundarios = rut_empresa.get('ciuu_secundarios', [])
            
            # Validar límites
            es_valido, mensaje_error = servicio.validar_limites(facturas)
            if not es_valido:
                return Response(
                    {'error': mensaje_error},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Procesar facturas (cada una puede tener proveedor diferente)
            resultados = []
            
            # Configuración de procesamiento paralelo con rate limiting
            # Servicio de IA: límite de 60 llamadas por minuto (RPM)
            # Estrategia segura: lotes de 10, máximo 50 por minuto, pausa de 60 segundos
            from celery import group
            from celery.result import allow_join_result
            import time
            
            # Tamaño de lote configurable (recomendado: 10 según el servicio)
            lote_size = getattr(settings, 'CLASIFICACION_LOTE_PARALELO', 10)
            
            # Preparar todas las facturas para procesamiento
            # PROTECCIÓN CONTRA DUPLICADOS: Filtrar facturas que ya están clasificadas
            # PERO: Si forzar_reclasificacion=True, procesar todas (incluso las ya clasificadas)
            tareas_preparadas = []
            facturas_para_procesar = []
            facturas_ya_clasificadas = []
            
            # Verificar si se debe forzar reclasificación (omite la protección de duplicados)
            forzar_reclasificacion = datos.get('forzar_reclasificacion', False)
            
            # Si hay session_dian_id y NO se fuerza reclasificación, verificar qué facturas ya están clasificadas
            if session_dian_id and not forzar_reclasificacion:
                from .models import ClasificacionContable
                facturas_clasificadas = ClasificacionContable.objects.filter(
                    session_dian_id=session_dian_id
                ).values_list('factura_numero', flat=True)
                facturas_clasificadas_set = set(facturas_clasificadas)
                logger.info(f"🔍 [CLASIFICACION] Verificando duplicados: {len(facturas_clasificadas_set)} facturas ya clasificadas en sesión {session_dian_id}")
            else:
                facturas_clasificadas_set = set()
                if forzar_reclasificacion:
                    logger.info(f"🔄 [CLASIFICACION] Modo FORZAR RECLASIFICACIÓN activo: se procesarán todas las facturas (incluso las ya clasificadas)")
            
            for factura in facturas:
                factura_numero = factura.get('numero_factura')
                
                # PROTECCIÓN: Si ya está clasificada Y NO se fuerza reclasificación, omitir
                # (evita duplicados y llamadas innecesarias en clasificación normal)
                if session_dian_id and factura_numero and not forzar_reclasificacion:
                    if factura_numero in facturas_clasificadas_set:
                        facturas_ya_clasificadas.append(factura_numero)
                        resultados.append({
                            'factura_numero': factura_numero,
                            'proveedor_nit': datos.get('proveedor_nit') or factura.get('proveedor_nit'),
                            'procesamiento_asincrono': datos.get('procesar_asincrono', False),
                            'estado': 'YA_CLASIFICADA',
                            'mensaje': 'Esta factura ya fue clasificada previamente. Use "Reclasificar" para forzar una nueva clasificación.'
                        })
                        logger.info(f"⏭️ [CLASIFICACION] Factura {factura_numero} ya clasificada, omitiendo...")
                        continue
                
                proveedor_nit = datos.get('proveedor_nit') or factura.get('proveedor_nit')
                
                if not proveedor_nit:
                    resultados.append({
                        'factura_numero': factura_numero,
                        'error': 'proveedor_nit no encontrado en factura',
                        'estado': 'FALLIDO'
                    })
                    continue
                
                # Buscar CIUU del proveedor (cacheado)
                proveedor_ciuu = datos.get('proveedor_ciuu')
                if not proveedor_ciuu:
                    rut_proveedor = servicio.buscar_rut_por_nit(proveedor_nit)
                    if rut_proveedor:
                        proveedor_ciuu = rut_proveedor.get('ciuu_principal')
                
                facturas_para_procesar.append({
                    'factura': factura,
                    'proveedor_nit': proveedor_nit,
                    'proveedor_ciuu': proveedor_ciuu
                })
            
            if facturas_ya_clasificadas:
                logger.info(f"⏭️ [CLASIFICACION] {len(facturas_ya_clasificadas)} facturas ya clasificadas, omitidas: {facturas_ya_clasificadas[:5]}{'...' if len(facturas_ya_clasificadas) > 5 else ''}")
            
            if datos.get('procesar_asincrono'):
                # Procesar en lotes paralelos con rate limiting seguro
                # Estrategia basada en recomendaciones del servicio:
                # - El servicio acepta hasta 60 llamadas por minuto (RPM)
                # - Cada factura toma ~20 segundos en procesarse
                # - Estrategia: Enviar 50 facturas primero (en lotes de 10), esperar 60s, enviar las restantes
                max_facturas_por_minuto = getattr(settings, 'CLASIFICACION_MAX_FACTURAS_POR_MINUTO', 50)
                pausa_entre_grupos = getattr(settings, 'CLASIFICACION_PAUSA_ENTRE_GRUPOS', 60)
                
                logger.info(f"🔄 [CLASIFICACION] Procesando {len(facturas_para_procesar)} facturas con rate limiting seguro")
                logger.info(f"   - Tamaño de lote: {lote_size} facturas (recomendado: 10)")
                logger.info(f"   - Máximo por minuto: {max_facturas_por_minuto} facturas (límite del servicio: 60 RPM)")
                logger.info(f"   - Pausa entre grupos: {pausa_entre_grupos} segundos (para resetear contador)")
                
                # Dividir en lotes de tamaño configurado
                lotes = [facturas_para_procesar[i:i + lote_size] for i in range(0, len(facturas_para_procesar), lote_size)]
                
                facturas_enviadas_en_grupo = 0
                grupo_actual = 1
                total_lotes_enviados = 0
                
                    # Procesar lotes respetando rate limit del servicio
                for idx_lote, lote in enumerate(lotes):
                    # Verificar si necesitamos pausar (hemos enviado el máximo por minuto)
                    if facturas_enviadas_en_grupo >= max_facturas_por_minuto:
                        logger.info(f"⏸️ [CLASIFICACION] Límite de {max_facturas_por_minuto} facturas/min alcanzado")
                        logger.info(f"⏳ [CLASIFICACION] Esperando {pausa_entre_grupos} segundos antes del siguiente grupo...")
                        logger.info(f"   - Grupo {grupo_actual} completado: {facturas_enviadas_en_grupo} facturas enviadas")
                        time.sleep(pausa_entre_grupos)
                        facturas_enviadas_en_grupo = 0
                        grupo_actual += 1
                        logger.info(f"✅ [CLASIFICACION] Iniciando Grupo {grupo_actual}")
                    
                    logger.info(f"📦 [CLASIFICACION] Grupo {grupo_actual} - Lote {idx_lote + 1}/{len(lotes)} ({len(lote)} facturas)")
                    logger.info(f"   - Facturas enviadas en este grupo: {facturas_enviadas_en_grupo}/{max_facturas_por_minuto}")
                    logger.info(f"   - Total lotes enviados: {total_lotes_enviados}")
                    
                    # Crear grupo de tareas Celery para este lote
                    tareas_lote = []
                    for item in lote:
                        task = clasificar_factura_contable_task.s(
                            factura_data=item['factura'],
                            empresa_nit=empresa_nit,
                            empresa_ciuu_principal=empresa_ciuu_principal,
                            empresa_ciuu_secundarios=empresa_ciuu_secundarios,
                            proveedor_nit=item['proveedor_nit'],
                            proveedor_ciuu=item['proveedor_ciuu'],
                            aplica_retencion=datos.get('aplica_retencion', False),
                            porcentaje_retencion=datos.get('porcentaje_retencion', 0),
                            tipo_operacion=datos.get('tipo_operacion', 'compra'),
                            session_dian_id=session_dian_id
                        )
                        tareas_lote.append(task)
                    
                    # Ejecutar lote en paralelo (Celery group)
                    job = group(tareas_lote)
                    result = job.apply_async()
                    
                    # Actualizar contadores
                    facturas_enviadas_en_grupo += len(lote)
                    total_lotes_enviados += 1
                    
                    # Agregar resultados inmediatamente (las tareas se ejecutan en background)
                    for i, item in enumerate(lote):
                        resultados.append({
                            'factura_numero': item['factura'].get('numero_factura'),
                            'proveedor_nit': item['proveedor_nit'],
                            'procesamiento_asincrono': True,
                            'task_id': result.results[i].id if i < len(result.results) else None,
                            'lote': idx_lote + 1,
                            'grupo': grupo_actual,
                            'estado': 'PENDIENTE'
                        })
                    
                    # Pausa entre lotes del mismo grupo para distribuir las peticiones
                    # Esto ayuda a evitar saturar el servicio y distribuir las 50 facturas a lo largo del minuto
                    # Pausa fija de 2 segundos entre lotes (seguro y predecible)
                    if idx_lote < len(lotes) - 1 and facturas_enviadas_en_grupo < max_facturas_por_minuto:
                        time.sleep(2)  # 2 segundos entre lotes del mismo grupo
                
                logger.info(f"✅ [CLASIFICACION] Todas las tareas lanzadas:")
                logger.info(f"   - Total facturas: {len(facturas_para_procesar)}")
                logger.info(f"   - Total lotes: {len(lotes)} (tamaño: {lote_size} facturas/lote)")
                logger.info(f"   - Total grupos: {grupo_actual}")
                logger.info(f"   - Tiempo estimado: ~{grupo_actual * pausa_entre_grupos + len(facturas_para_procesar) * 20 / 60} minutos")
            else:
                # Procesar sincrónicamente (una por una)
                for item in facturas_para_procesar:
                    resultado = servicio.clasificar_factura(
                        factura=item['factura'],
                        empresa_nit=empresa_nit,
                        empresa_ciuu_principal=empresa_ciuu_principal,
                        empresa_ciuu_secundarios=empresa_ciuu_secundarios,
                        proveedor_nit=item['proveedor_nit'],
                        proveedor_ciuu=item['proveedor_ciuu'],
                        aplica_retencion=datos.get('aplica_retencion', False),
                        porcentaje_retencion=datos.get('porcentaje_retencion', 0),
                        tipo_operacion=datos.get('tipo_operacion', 'compra')
                    )
                    
                    if resultado.get('success'):
                        # Guardar en BD
                        clasificacion = servicio.guardar_clasificacion(
                            factura_numero=item['factura'].get('numero_factura'),
                            proveedor_nit=item['proveedor_nit'],
                            empresa_nit=empresa_nit,
                            empresa_ciuu_principal=empresa_ciuu_principal,
                            proveedor_ciuu=item['proveedor_ciuu'],
                            resultado=resultado,
                            session_dian_id=session_dian_id
                        )
                        
                        resultados.append({
                            'factura_numero': item['factura'].get('numero_factura'),
                            'proveedor_nit': item['proveedor_nit'],
                            'clasificacion_id': clasificacion.id,
                            'procesamiento_asincrono': False,
                            'costo_usd': float(resultado.get('costo', {}).get('costo_usd', 0)),
                            'tiempo_segundos': resultado.get('tiempo_procesamiento', 0),
                            'estado': 'COMPLETADO'
                        })
                    else:
                        resultados.append({
                            'factura_numero': item['factura'].get('numero_factura'),
                            'proveedor_nit': item['proveedor_nit'],
                            'procesamiento_asincrono': False,
                            'error': resultado.get('error'),
                            'estado': 'FALLIDO'
                        })
        
            return Response({
                'success': True,
                'total_facturas': len(facturas),
                'resultados': resultados
            }, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"❌ [CLASIFICACION] ========== ERROR ==========")
            print(f"❌ [CLASIFICACION] Error: {type(e).__name__}: {e}")
            traceback.print_exc()
            logger.error(f"Error en clasificar_factura: {e}", exc_info=True)
            return Response(
                {
                    'error': f'Error al clasificar factura: {str(e)}',
                    'error_type': type(e).__name__,
                    'traceback': traceback.format_exc() if settings.DEBUG else None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='documentos-sesion/(?P<session_id>[^/.]+)')
    def listar_documentos_sesion(self, request, session_id=None):
        """
        Listar documentos de una sesión DIAN para selección en frontend.
        
        URL: /api/clasificacion-contable/documentos-sesion/<session_id>/
        
        Returns:
            Lista de documentos con información básica para mostrar en modal
        """
        # Verificar autenticación (API Key o usuario)
        if not hasattr(request, 'cliente_api') and not (hasattr(request, 'user') and request.user.is_authenticated):
            print(f"❌ [CLASIFICACION] No hay API Key ni usuario autenticado")
            return Response(
                {'error': 'Se requiere API Key o autenticación de usuario'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        print(f"✅ [CLASIFICACION] Autenticado: API Key={hasattr(request, 'cliente_api')}, User={hasattr(request, 'user') and request.user.is_authenticated}")
        if hasattr(request, 'cliente_api'):
            print(f"✅ [CLASIFICACION] API Key: ID={request.cliente_api.id}, permite_scraping_total={getattr(request.cliente_api, 'permite_scraping_total', False)}")
        
        try:
            from apps.dian_scraper.models import ScrapingSession, DocumentProcessed
            
            session = ScrapingSession.objects.get(id=session_id)
            
            # Paginación
            page_size = int(request.query_params.get('page_size', 5))
            page = int(request.query_params.get('page', 1))
            
            print(f"📄 [BACKEND PAGINACION] Parámetros recibidos: page={page}, page_size={page_size}")
            print(f"📄 [BACKEND PAGINACION] Query params completos: {dict(request.query_params)}")
            
            # Obtener total de documentos
            total_documentos = DocumentProcessed.objects.filter(session=session).count()
            
            # Calcular offset y limit
            offset = (page - 1) * page_size
            print(f"📄 [BACKEND PAGINACION] Offset: {offset}, Limit: {page_size}, Total docs: {total_documentos}")
            # Ordenar por ID para garantizar orden consistente (no por fecha que puede ser igual)
            documentos = DocumentProcessed.objects.filter(session=session).order_by('-id')[offset:offset + page_size]
            
            # Obtener NIT y nombre del receptor desde el primer documento
            receptor_nit = None
            receptor_nombre = None
            primer_doc = DocumentProcessed.objects.filter(session=session).first()
            if primer_doc:
                if session.tipo == 'Received':
                    # Para recibidos, el receptor es el customer
                    receptor_nit = primer_doc.customer_nit or ''
                    receptor_nombre = primer_doc.customer_name or ''
                else:  # Sent
                    # Para enviados, el receptor es el supplier
                    receptor_nit = primer_doc.supplier_nit or ''
                    receptor_nombre = primer_doc.supplier_name or ''
            
            documentos_data = []
            for doc in documentos:
                # Determinar proveedor según tipo de sesión
                if session.tipo == 'Received':
                    proveedor_nit = doc.supplier_nit or ''
                    proveedor_nombre = doc.supplier_name or ''
                else:  # Sent
                    proveedor_nit = doc.customer_nit or ''
                    proveedor_nombre = doc.customer_name or ''
                
                # Obtener clasificación si existe para obtener el precio
                clasificacion = ClasificacionContable.objects.filter(
                    factura_numero=doc.document_number,
                    session_dian_id=session_id
                ).first()
                
                tiene_clasificacion = clasificacion is not None
                
                # Obtener costo: si existe y es > 0, usarlo; si no, intentar recalcular desde tokens
                costo_usd = None
                costo_cop = None
                
                if clasificacion:
                    if clasificacion.costo_total_factura and float(clasificacion.costo_total_factura) > 0:
                        # Ya tiene costo guardado
                        costo_usd = float(clasificacion.costo_total_factura)
                        costo_cop = float(clasificacion.costo_total_cop) if clasificacion.costo_total_cop else None
                    elif clasificacion.tokens_input > 0 or clasificacion.tokens_output > 0:
                        # Recalcular desde tokens guardados
                        from .services.clasificador_contable_service import calcular_costo_tokens
                        
                        # Intentar extraer cache hit/miss desde respuesta_json_completa
                        cache_hit_tokens = None
                        cache_miss_tokens = None
                        if clasificacion.respuesta_json_completa:
                            usage = clasificacion.respuesta_json_completa.get('usage', {})
                            cache_hit_tokens = usage.get('prompt_cache_hit_tokens')
                            cache_miss_tokens = usage.get('prompt_cache_miss_tokens')
                        
                        costo_info = calcular_costo_tokens(
                            input_tokens=clasificacion.tokens_input,
                            output_tokens=clasificacion.tokens_output,
                            cache_hit_tokens=cache_hit_tokens,
                            cache_miss_tokens=cache_miss_tokens
                        )
                        costo_usd = costo_info['costo_usd']
                        costo_cop = costo_info['costo_cop']
                
                documentos_data.append({
                    'id': doc.id,
                    'document_number': doc.document_number,
                    'cufe': doc.cufe,
                    'issue_date': str(doc.issue_date) if doc.issue_date else None,
                    'proveedor_nit': proveedor_nit,
                    'proveedor_nombre': proveedor_nombre,
                    'total_amount': float(doc.total_amount or 0),
                    'tiene_clasificacion': tiene_clasificacion,
                    'costo_usd': costo_usd,
                    'costo_cop': costo_cop
                })
            
            return Response({
                'session_id': session_id,
                'session_tipo': session.tipo,
                'receptor_nit': receptor_nit or '',
                'receptor_nombre': receptor_nombre or '',
                'total_documentos': total_documentos,
                'documentos': documentos_data,
                'paginacion': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total_documentos + page_size - 1) // page_size if total_documentos > 0 else 1,
                    'has_next': offset + page_size < total_documentos,
                    'has_previous': page > 1
                }
            })
            
        except ScrapingSession.DoesNotExist:
            return Response(
                {'error': f'Sesión {session_id} no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error listando documentos: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='clasificaciones')
    def listar_clasificaciones(self, request):
        """
        Listar clasificaciones contables guardadas.
        
        Query params:
            session_id: Filtrar por sesión DIAN
            factura_numero: Filtrar por número de factura
            proveedor_nit: Filtrar por NIT proveedor
            empresa_nit: Filtrar por NIT empresa
            estado: Filtrar por estado
        """
        from .serializers import ClasificacionContableSerializer
        from .models import ClasificacionContable
        from django.db.models import Q
        
        print(f"\n{'='*80}")
        print(f"🔍 [LISTAR_CLASIFICACIONES] Iniciando búsqueda de clasificaciones")
        print(f"{'='*80}")
        
        queryset = ClasificacionContable.objects.all()
        
        # Filtros
        session_id = request.query_params.get('session_id')
        if session_id:
            print(f"📋 [LISTAR_CLASIFICACIONES] Filtro session_id: {session_id}")
            queryset = queryset.filter(session_dian_id=session_id)
        
        factura_numero = request.query_params.get('factura_numero')
        if factura_numero:
            print(f"📋 [LISTAR_CLASIFICACIONES] Filtro factura_numero: {factura_numero}")
            queryset = queryset.filter(factura_numero=factura_numero)
        
        proveedor_nit = request.query_params.get('proveedor_nit')
        if proveedor_nit:
            nit_normalizado, _, _ = normalize_nit_and_extract_dv(proveedor_nit)
            print(f"📋 [LISTAR_CLASIFICACIONES] Filtro proveedor_nit: {proveedor_nit} (normalizado: {nit_normalizado})")
            queryset = queryset.filter(proveedor_nit_normalizado=nit_normalizado)
        
        empresa_nit = request.query_params.get('empresa_nit')
        if empresa_nit:
            print(f"📋 [LISTAR_CLASIFICACIONES] Filtro empresa_nit: {empresa_nit}")
            queryset = queryset.filter(empresa_nit=empresa_nit)
        
        estado = request.query_params.get('estado')
        if estado:
            print(f"📋 [LISTAR_CLASIFICACIONES] Filtro estado: {estado}")
            queryset = queryset.filter(estado=estado)
        
        # Ordenar por fecha de creación descendente
        queryset = queryset.order_by('-created_at')
        
        count = queryset.count()
        print(f"📊 [LISTAR_CLASIFICACIONES] Total clasificaciones encontradas: {count}")
        
        serializer = ClasificacionContableSerializer(queryset, many=True)
        
        # Debug: Verificar qué se está retornando
        if count > 0:
            primera = queryset.first()
            print(f"📄 [LISTAR_CLASIFICACIONES] Primera clasificación:")
            print(f"   - ID: {primera.id}")
            print(f"   - Factura: {primera.factura_numero}")
            print(f"   - factura_json_enviada existe: {bool(primera.factura_json_enviada)}")
            if primera.factura_json_enviada:
                articulos = primera.factura_json_enviada.get('articulos', [])
                print(f"   - Artículos en factura_json_enviada: {len(articulos)}")
                if len(articulos) > 0:
                    print(f"   - Primer artículo: {articulos[0]}")
                else:
                    print(f"   - ⚠️ factura_json_enviada.articulos está VACÍO")
                    print(f"   - factura_json_enviada completo: {primera.factura_json_enviada}")
            else:
                print(f"   - ⚠️ factura_json_enviada es None o vacío")
        
        print(f"{'='*80}\n")
        
        return Response({
            'count': count,
            'results': serializer.data
        })
    
    @action(detail=False, methods=['post'], url_path='reclasificar-factura')
    def reclasificar_factura(self, request):
        """
        Reclasificar una factura existente, releyendo los artículos del Excel.
        
        Body:
            clasificacion_id: ID de la clasificación a reclasificar (opcional)
            factura_numero: Número de factura (opcional, si no se proporciona clasificacion_id)
            session_id: ID de sesión DIAN (opcional, si no se proporciona clasificacion_id)
            document_id: ID de documento específico (opcional, preferido)
        
        Returns:
            Resultado de la nueva clasificación
        """
        from .models import ClasificacionContable
        from .services.clasificador_contable_service import ClasificadorContableService
        from apps.dian_scraper.models import DocumentProcessed
        
        print(f"\n{'='*80}")
        print(f"🔄 [RECLASIFICAR_FACTURA] Iniciando reclasificación")
        print(f"{'='*80}")
        
        clasificacion_id = request.data.get('clasificacion_id')
        factura_numero = request.data.get('factura_numero')
        session_id = request.data.get('session_id')
        document_id = request.data.get('document_id')
        
        # Buscar clasificación existente
        clasificacion_existente = None
        if clasificacion_id:
            try:
                clasificacion_existente = ClasificacionContable.objects.get(id=clasificacion_id)
                print(f"📋 [RECLASIFICAR_FACTURA] Clasificación encontrada: ID={clasificacion_id}, Factura={clasificacion_existente.factura_numero}")
            except ClasificacionContable.DoesNotExist:
                return Response(
                    {'error': f'Clasificación {clasificacion_id} no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif factura_numero and session_id:
            clasificacion_existente = ClasificacionContable.objects.filter(
                factura_numero=factura_numero,
                session_dian_id=session_id
            ).order_by('-created_at').first()
            
            if clasificacion_existente:
                print(f"📋 [RECLASIFICAR_FACTURA] Clasificación encontrada por factura_numero: {factura_numero}, session_id: {session_id}")
            else:
                return Response(
                    {'error': f'No se encontró clasificación para factura {factura_numero} en sesión {session_id}'},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif document_id:
            # Buscar clasificación por document_id
            try:
                doc = DocumentProcessed.objects.get(id=document_id)
                clasificacion_existente = ClasificacionContable.objects.filter(
                    factura_numero=doc.document_number,
                    session_dian_id=doc.session_id
                ).order_by('-created_at').first()
                
                if clasificacion_existente:
                    print(f"📋 [RECLASIFICAR_FACTURA] Clasificación encontrada por document_id: {document_id}")
                else:
                    # Si no hay clasificación, usar document_id directamente
                    print(f"📋 [RECLASIFICAR_FACTURA] No hay clasificación previa, usando document_id: {document_id}")
            except DocumentProcessed.DoesNotExist:
                return Response(
                    {'error': f'Documento {document_id} no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                {'error': 'Se requiere clasificacion_id, o (factura_numero + session_id), o document_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener información de la clasificación existente
        if clasificacion_existente:
            factura_numero = clasificacion_existente.factura_numero
            session_id = clasificacion_existente.session_dian_id
            empresa_nit = clasificacion_existente.empresa_nit
            proveedor_nit = clasificacion_existente.proveedor_nit
            
            print(f"📄 [RECLASIFICAR_FACTURA] Datos de clasificación existente:")
            print(f"   - Factura: {factura_numero}")
            print(f"   - Sesión: {session_id}")
            print(f"   - Empresa NIT: {empresa_nit}")
            print(f"   - Proveedor NIT: {proveedor_nit}")
        
        # Buscar document_id si no se proporcionó
        if not document_id and session_id and factura_numero:
            try:
                doc = DocumentProcessed.objects.filter(
                    session_id=session_id,
                    document_number=factura_numero
                ).first()
                if doc:
                    document_id = doc.id
                    print(f"📄 [RECLASIFICAR_FACTURA] Documento encontrado: ID={document_id}")
            except Exception as e:
                print(f"⚠️ [RECLASIFICAR_FACTURA] Error buscando documento: {e}")
        
        if not document_id:
            return Response(
                {'error': 'No se pudo determinar document_id para reclasificar'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Leer documento desde raw_data (BD) - debería ser idéntico al Excel
        servicio = ClasificadorContableService()
        print(f"🔄 [RECLASIFICAR_FACTURA] Leyendo documento desde raw_data (BD)...")
        doc_info = servicio.leer_documento_por_id(document_id)
        
        if not doc_info:
            return Response(
                {'error': f'No se pudo leer documento {document_id}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        print(f"✅ [RECLASIFICAR_FACTURA] Documento leído desde raw_data:")
        print(f"   - Factura: {doc_info['factura'].get('numero_factura')}")
        print(f"   - Artículos REALES: {len(doc_info['factura'].get('articulos', []))}")
        if len(doc_info['factura'].get('articulos', [])) > 0:
            primer_articulo = doc_info['factura']['articulos'][0]
            print(f"   - Primer artículo: {primer_articulo.get('nombre')}")
            print(f"     * Cantidad: {primer_articulo.get('cantidad')}")
            print(f"     * Valor unitario: ${primer_articulo.get('valor_unitario')}")
            print(f"     * Valor total: ${primer_articulo.get('valor_total')}")
            print(f"     * Impuestos: {len(primer_articulo.get('impuestos', []))}")
            if len(primer_articulo.get('impuestos', [])) > 0:
                print(f"       - {primer_articulo['impuestos'][0].get('nombre')} ({primer_articulo['impuestos'][0].get('porcentaje')}%)")
        
        # Obtener información de empresa y proveedor
        empresa_nit = doc_info['empresa_nit']
        empresa_ciuu_info = doc_info['empresa_ciuu_info']
        proveedor_nit = doc_info['factura'].get('proveedor_nit')
        
        # Buscar CIUU del proveedor
        rut_proveedor = servicio.buscar_rut_por_nit(proveedor_nit)
        proveedor_ciuu = rut_proveedor.get('ciuu_principal') if rut_proveedor else None
        
        # Clasificar nuevamente
        print(f"🔄 [RECLASIFICAR_FACTURA] Iniciando clasificación con servicio de IA...")
        resultado = servicio.clasificar_factura(
            factura=doc_info['factura'],
            empresa_nit=empresa_nit,
            empresa_ciuu_principal=empresa_ciuu_info.get('ciuu_principal'),
            empresa_ciuu_secundarios=empresa_ciuu_info.get('ciuu_secundarios', []),
            proveedor_nit=proveedor_nit,
            proveedor_ciuu=proveedor_ciuu,
            aplica_retencion=False,  # Se puede obtener de la clasificación anterior si es necesario
            porcentaje_retencion=0,
            tipo_operacion='compra'
        )
        
        if not resultado.get('success'):
            return Response(
                {'error': resultado.get('error', 'Error al reclasificar factura')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Eliminar clasificación anterior si existe
        if clasificacion_existente:
            print(f"🗑️ [RECLASIFICAR_FACTURA] Eliminando clasificación anterior: ID={clasificacion_existente.id}")
            clasificacion_existente.delete()
        
        # Guardar nueva clasificación
        nueva_clasificacion = servicio.guardar_clasificacion(
            factura_numero=doc_info['factura'].get('numero_factura'),
            proveedor_nit=proveedor_nit,
            empresa_nit=empresa_nit,
            empresa_ciuu_principal=empresa_ciuu_info.get('ciuu_principal'),
            proveedor_ciuu=proveedor_ciuu,
            resultado=resultado,
            session_dian_id=doc_info['session_id']
        )
        
        print(f"✅ [RECLASIFICAR_FACTURA] Nueva clasificación guardada: ID={nueva_clasificacion.id}")
        print(f"{'='*80}\n")
        
        from .serializers import ClasificacionContableSerializer
        serializer = ClasificacionContableSerializer(nueva_clasificacion)
        
        return Response({
            'success': True,
            'mensaje': 'Factura reclasificada exitosamente',
            'clasificacion': serializer.data,
            'costo_usd': float(resultado.get('costo', {}).get('costo_usd', 0)),
            'tiempo_segundos': resultado.get('tiempo_procesamiento', 0)
        })
    
    @action(detail=True, methods=['get'], url_path='analisis-ciuu')
    def obtener_analisis_ciuu(self, request, pk=None):
        """
        Obtiene análisis completo de CIUU para emisor y receptor de una clasificación.
        Incluye información de incluye/excluye para cada CIUU.
        
        Returns:
            {
                'empresa': {
                    'nit': '...',
                    'razon_social': '...',
                    'ciuu_principal': {...},
                    'ciuu_secundarios': [...]
                },
                'proveedor': {
                    'nit': '...',
                    'razon_social': '...',
                    'ciuu_principal': {...},
                    'ciuu_secundarios': [...]
                },
                'perspectiva_auditor': '...'
            }
        """
        from .models import ClasificacionContable
        from .services.clasificador_contable_service import ClasificadorContableService, obtener_contexto_ciuu_inteligente
        from .services.camara_comercio_service import consultar_camara_comercio_por_nit
        
        try:
            clasificacion = ClasificacionContable.objects.select_related('session_dian').get(id=pk)
            servicio = ClasificadorContableService()
            
            empresa_nit = clasificacion.empresa_nit
            proveedor_nit = clasificacion.proveedor_nit
            
            # Obtener información de empresa
            empresa_info = {
                'nit': empresa_nit,
                'razon_social': None,
                'ciuu_principal': None,
                'ciuu_secundarios': []
            }
            
            # Buscar RUT de empresa con el NIT guardado
            rut_empresa = servicio.buscar_rut_por_nit(empresa_nit)
            
            # Si no se encuentra, intentar con el NIT de la sesión original (puede ser más completo)
            if not rut_empresa and clasificacion.session_dian:
                nit_sesion = clasificacion.session_dian.nit
                if nit_sesion and nit_sesion != empresa_nit:
                    logger.info(f"🔍 [ANALISIS_CIUU] NIT guardado ({empresa_nit}) no encontró RUT, intentando con NIT de sesión ({nit_sesion})")
                    rut_empresa = servicio.buscar_rut_por_nit(nit_sesion)
                    if rut_empresa:
                        empresa_nit = nit_sesion  # Actualizar para mostrar el NIT correcto
                        empresa_info['nit'] = nit_sesion
            
            if rut_empresa:
                empresa_info['razon_social'] = rut_empresa.get('razon_social')
                empresa_info['ciuu_principal'] = rut_empresa.get('ciuu_principal')
                empresa_info['ciuu_secundarios'] = rut_empresa.get('ciuu_secundarios', [])
            else:
                # Intentar Cámara de Comercio con el NIT más completo disponible
                nit_para_buscar = empresa_nit
                if clasificacion.session_dian and clasificacion.session_dian.nit:
                    nit_para_buscar = clasificacion.session_dian.nit
                
                camara_info = consultar_camara_comercio_por_nit(nit_para_buscar)
                if camara_info:
                    empresa_info['razon_social'] = camara_info.get('razon_social')
                    empresa_info['ciuu_principal'] = camara_info.get('ciuu_principal')
                    empresa_info['ciuu_secundarios'] = camara_info.get('ciuu_secundarios', [])
                    empresa_info['nit'] = nit_para_buscar  # Actualizar NIT si se encontró con el de sesión
            
            # Obtener detalles de CIUU de empresa
            if empresa_info['ciuu_principal']:
                empresa_info['ciuu_principal'] = obtener_contexto_ciuu_inteligente(empresa_info['ciuu_principal'])
            
            empresa_info['ciuu_secundarios'] = [
                obtener_contexto_ciuu_inteligente(ciuu) 
                for ciuu in empresa_info['ciuu_secundarios'] 
                if ciuu
            ]
            
            # Obtener información de proveedor
            proveedor_info = {
                'nit': proveedor_nit,
                'razon_social': None,
                'ciuu_principal': None,
                'ciuu_secundarios': []
            }
            
            # Buscar RUT de proveedor
            rut_proveedor = servicio.buscar_rut_por_nit(proveedor_nit)
            if rut_proveedor:
                proveedor_info['razon_social'] = rut_proveedor.get('razon_social')
                proveedor_info['ciuu_principal'] = rut_proveedor.get('ciuu_principal')
                proveedor_info['ciuu_secundarios'] = rut_proveedor.get('ciuu_secundarios', [])
            else:
                # Intentar Cámara de Comercio
                camara_info = consultar_camara_comercio_por_nit(proveedor_nit)
                if camara_info:
                    proveedor_info['razon_social'] = camara_info.get('razon_social')
                    proveedor_info['ciuu_principal'] = camara_info.get('ciuu_principal')
                    proveedor_info['ciuu_secundarios'] = camara_info.get('ciuu_secundarios', [])
            
            # Obtener detalles de CIUU de proveedor
            if proveedor_info['ciuu_principal']:
                proveedor_info['ciuu_principal'] = obtener_contexto_ciuu_inteligente(proveedor_info['ciuu_principal'])
            
            proveedor_info['ciuu_secundarios'] = [
                obtener_contexto_ciuu_inteligente(ciuu) 
                for ciuu in proveedor_info['ciuu_secundarios'] 
                if ciuu
            ]
            
            # Generar perspectiva para auditor
            perspectiva = []
            if not empresa_info['ciuu_principal']:
                perspectiva.append("⚠️ La empresa no tiene CIUU principal registrado. Se recomienda verificar el RUT.")
            if not proveedor_info['ciuu_principal']:
                perspectiva.append("⚠️ El proveedor no tiene CIUU principal registrado. Se recomienda verificar el RUT del proveedor.")
            
            if empresa_info['ciuu_principal'] and proveedor_info['ciuu_principal']:
                perspectiva.append(f"✅ Empresa (CIUU {empresa_info['ciuu_principal'].get('codigo', 'N/A')}) y Proveedor (CIUU {proveedor_info['ciuu_principal'].get('codigo', 'N/A')}) tienen actividades económicas definidas.")
            
            # Verificar si la clasificación es coherente con los CIUU
            factura_json = clasificacion.factura_json_enviada or {}
            articulos = factura_json.get('articulos', [])
            
            if articulos:
                perspectiva.append(f"📊 La factura contiene {len(articulos)} artículo(s).")
                
                # Detectar inconsistencias: verificar si los artículos son consistentes con el CIUU del proveedor
                if proveedor_info.get('ciuu_principal'):
                    proveedor_ciuu = proveedor_info['ciuu_principal']
                    proveedor_incluye = proveedor_ciuu.get('incluye_raw', [])
                    proveedor_excluye = proveedor_ciuu.get('excluye_raw', [])
                    
                    articulos_inconsistentes = []
                    for articulo in articulos:
                        nombre_articulo = articulo.get('nombre', '').lower()
                        ref_articulo = articulo.get('ref', '').lower()
                        
                        # Verificar si el artículo está en las actividades excluidas del proveedor
                        es_inconsistente = False
                        motivo = []
                        
                        # Buscar en excluye
                        for excluido in proveedor_excluye:
                            if isinstance(excluido, dict):
                                desc_excluido = excluido.get('actDescripcion', '').lower()
                                if desc_excluido and (nombre_articulo in desc_excluido or desc_excluido in nombre_articulo):
                                    es_inconsistente = True
                                    motivo.append(f"El artículo '{articulo.get('nombre', 'N/A')}' está en las actividades EXCLUIDAS del CIUU del proveedor")
                                    break
                        
                        # Verificar si el artículo NO está en las actividades incluidas
                        if not es_inconsistente and proveedor_incluye:
                            encontrado_en_incluye = False
                            for incluido in proveedor_incluye:
                                if isinstance(incluido, dict):
                                    desc_incluido = incluido.get('actDescripcion', '').lower()
                                    if desc_incluido and (nombre_articulo in desc_incluido or desc_incluido in nombre_articulo):
                                        encontrado_en_incluye = True
                                        break
                            
                            # Si no se encontró en incluye y hay artículos específicos, puede ser inconsistente
                            if not encontrado_en_incluye and len(proveedor_incluye) > 0:
                                # Solo marcar como inconsistente si el nombre del artículo es muy específico
                                palabras_clave = ['computador', 'telefono', 'celular', 'equipo', 'software', 'servicio']
                                if any(palabra in nombre_articulo for palabra in palabras_clave):
                                    es_inconsistente = True
                                    motivo.append(f"El artículo '{articulo.get('nombre', 'N/A')}' no parece estar relacionado con el CIUU principal del proveedor ({proveedor_ciuu.get('codigo', 'N/A')})")
                        
                        if es_inconsistente:
                            articulos_inconsistentes.append({
                                'nombre': articulo.get('nombre', 'N/A'),
                                'motivo': '; '.join(motivo)
                            })
                    
                    if articulos_inconsistentes:
                        perspectiva.append(f"⚠️ INCONSISTENCIA DETECTADA: {len(articulos_inconsistentes)} artículo(s) no son consistentes con la actividad comercial del proveedor:")
                        for art_inc in articulos_inconsistentes:
                            perspectiva.append(f"  • {art_inc['nombre']}: {art_inc['motivo']}")
                    else:
                        perspectiva.append(f"✅ Los artículos son consistentes con el CIUU del proveedor ({proveedor_ciuu.get('codigo', 'N/A')}).")
            
            return Response({
                'empresa': empresa_info,
                'proveedor': proveedor_info,
                'perspectiva_auditor': '\n'.join(perspectiva) if perspectiva else 'No hay observaciones adicionales.'
            })
            
        except ClasificacionContable.DoesNotExist:
            return Response(
                {'error': 'Clasificación no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error obteniendo análisis CIUU: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AIAnalyticsAPIKeyViewSet(APIKeyAwareViewSet, viewsets.ModelViewSet):
    """
    ViewSet para gestionar API keys de servicios de IA/Analytics.
    Permite crear, listar, actualizar y ver estadísticas de uso y costos.
    """
    queryset = AIAnalyticsAPIKey.objects.all()
    serializer_class = AIAnalyticsAPIKeySerializer
    permission_classes = [IsAuthenticated]  # Solo usuarios autenticados
    
    def get_queryset(self):
        """Ordenar por última vez usada y total de peticiones"""
        return AIAnalyticsAPIKey.objects.all().order_by('-ultima_vez_usada', '-total_peticiones')
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """
        Obtener estadísticas agregadas de todas las API keys.
        """
        from django.db.models import Sum, Count
        
        stats = AIAnalyticsAPIKey.objects.aggregate(
            total_api_keys=Count('id'),
            api_keys_activas=Count('id', filter=Q(activa=True)),
            total_peticiones=Sum('total_peticiones'),
            total_peticiones_exitosas=Sum('total_peticiones_exitosas'),
            total_peticiones_fallidas=Sum('total_peticiones_fallidas'),
            total_errores_rate_limit=Sum('total_errores_rate_limit'),
            costo_total_usd=Sum('costo_total_usd'),
            tokens_input_total=Sum('tokens_input_total'),
            tokens_output_total=Sum('tokens_output_total'),
            tokens_cache_hit_total=Sum('tokens_cache_hit_total'),
            tokens_cache_miss_total=Sum('tokens_cache_miss_total'),
        )
        
        # Calcular tasas
        if stats['total_peticiones'] and stats['total_peticiones'] > 0:
            stats['tasa_exito_global'] = round(
                (stats['total_peticiones_exitosas'] / stats['total_peticiones']) * 100, 2
            )
            stats['tasa_error_rate_limit_global'] = round(
                (stats['total_errores_rate_limit'] / stats['total_peticiones']) * 100, 2
            )
        else:
            stats['tasa_exito_global'] = 0.0
            stats['tasa_error_rate_limit_global'] = 0.0
        
        return Response(stats)

