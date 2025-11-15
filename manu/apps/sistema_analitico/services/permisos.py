# sistema_analitico/services/permisos.py 
from rest_framework import permissions
from apps.sistema_analitico.models import APIKeyCliente

class HasValidAPIKey(permissions.BasePermission):
    def has_permission(self, request, view):
        if not hasattr(view, 'action') or view.action != 'pregunta_inteligente':
            return True
            
        api_key = request.META.get('HTTP_API_KEY') or request.META.get('HTTP_AUTHORIZATION', '').replace('Api-Key ', '')
        
        print(f"🔑 API Key recibida: {api_key}")
        
        if not api_key:
            print("⚠️ No hay API Key, usando autenticación normal")
            return permissions.IsAuthenticated().has_permission(request, view)
            
        try:
            api_key_obj = APIKeyCliente.objects.get(
                api_key__iexact=api_key.strip(),
                activa=True
            )
            
            print(f"✅ API Key encontrada: {api_key_obj.nombre_cliente}")
            
            if api_key_obj.esta_expirada():
                print("❌ API Key expirada")
                return False
            
            empresas = api_key_obj.empresas_asociadas.all()
            if not empresas.exists():
                api_key_obj.actualizar_empresas_asociadas()
                empresas = api_key_obj.empresas_asociadas.all()
            
            api_key_obj.incrementar_contador()
            
            # ✅ SOLO ASIGNAR ESTOS DOS - NO request.user
            request.cliente_api = api_key_obj
            request.empresas_autorizadas = empresas
            
            print(f"✅ Empresas autorizadas: {empresas.count()}")
            return True
            
        except APIKeyCliente.DoesNotExist:
            print(f"❌ API Key no existe: {api_key}")
            return False
        except Exception as e:
            print(f"❌ Error con API Key: {e}")
            return False
       
class TienePermisoEmpresa(permissions.BasePermission):
    """
    Verifica que el usuario tenga acceso a empresas - COMPATIBLE CON API KEYS
    """
    def has_permission(self, request, view):
        # ✅ SI ES API KEY, PERMITIR ACCESO (ya se validó en HasValidAPIKey)
        if hasattr(request, 'cliente_api') and request.cliente_api:
            return True
            
        if request.user.is_superuser:
            return True
            
        # ✅ EVITAR AnonymousUser en consultas de base de datos
        if request.user.is_anonymous:
            return False
            
        if request.method in permissions.SAFE_METHODS:
            return request.user.empresas_permitidas().exists()
            
        # Para métodos de escritura, necesita permiso de edición
        from apps.sistema_analitico.models import UsuarioEmpresa
        return UsuarioEmpresa.objects.filter(
            usuario=request.user, 
            puede_editar=True
        ).exists()