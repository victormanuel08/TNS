# sistema_analitico/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('servidores', views.ServidorViewSet)
router.register('empresas-servidor', views.EmpresaServidorViewSet)
router.register('movimientos', views.MovimientoInventarioViewSet)
router.register('permisos-usuarios', views.UsuarioEmpresaViewSet)
router.register('sistema', views.SistemaViewSet, basename='sistema')
router.register('ml', views.MLViewSet, basename='ml')
router.register('consulta-natural', views.ConsultaNaturalViewSet, basename='consulta-natural')
router.register('testing', views.TestingViewSet, basename='testing')
router.register('api-keys', views.APIKeyManagementViewSet, basename='api-keys')
router.register('tns', views.TNSViewSet, basename='tns')

urlpatterns = [
    path('api/', include(router.urls)),
]
