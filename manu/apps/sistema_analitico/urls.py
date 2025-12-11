# sistema_analitico/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views_firebird_admin import FirebirdAdminViewSet

router = DefaultRouter()
router.register('servidores', views.ServidorViewSet)
router.register('empresas-servidor', views.EmpresaServidorViewSet)
router.register('movimientos', views.MovimientoInventarioViewSet)
router.register('permisos-usuarios', views.UsuarioEmpresaViewSet, basename='permisos-usuarios')
router.register('tenant-profiles', views.UserTenantProfileViewSet, basename='tenant-profiles')
router.register('sistema', views.SistemaViewSet, basename='sistema')
router.register('ml', views.MLViewSet, basename='ml')
router.register('consulta-natural', views.ConsultaNaturalViewSet, basename='consulta-natural')
router.register('testing', views.TestingViewSet, basename='testing')
router.register('api-keys', views.APIKeyManagementViewSet, basename='api-keys')
router.register('tns', views.TNSViewSet, basename='tns')
router.register('branding', views.BrandingViewSet, basename='branding')
router.register('ecommerce-config', views.EcommerceConfigViewSet, basename='ecommerce-config')
router.register('cajas-autopago', views.CajaAutopagoViewSet, basename='cajas-autopago')
router.register('dian-processor', views.DianProcessorViewSet, basename='dian-processor')
router.register('vpn/configs', views.VpnConfigViewSet, basename='vpn-configs')
router.register('server', views.ServerManagementViewSet, basename='server-management')
router.register('notas-rapidas', views.NotaRapidaViewSet, basename='notas-rapidas')
router.register('usuarios', views.UserManagementViewSet, basename='usuarios')
router.register('empresa-dominios', views.EmpresaDominioViewSet, basename='empresa-dominios')
router.register('pasarelas-pago', views.PasarelaPagoViewSet, basename='pasarelas-pago')
router.register('ruts', views.RUTViewSet, basename='ruts')
router.register('calendario-tributario', views.CalendarioTributarioViewSet, basename='calendario-tributario')
router.register('entidades', views.EntidadViewSet, basename='entidades')
router.register('contrasenas-entidades', views.ContrasenaEntidadViewSet, basename='contrasenas-entidades')
router.register('configuraciones-s3', views.ConfiguracionS3ViewSet, basename='configuraciones-s3')
router.register('backups-s3', views.BackupS3ViewSet, basename='backups-s3')
router.register('comunicacion', views.ComunicacionViewSet, basename='comunicacion')
router.register('clasificacion-contable', views.ClasificacionContableViewSet, basename='clasificacion-contable')
router.register('ai-analytics-api-keys', views.AIAnalyticsAPIKeyViewSet, basename='ai-analytics-api-keys')
router.register('firebird-admin', FirebirdAdminViewSet, basename='firebird-admin')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/resolve-domain/', views.resolve_domain_view, name='resolve-domain'),
    path('api/companies/by-subdomain/<str:subdomain>/', views.get_company_by_subdomain_view, name='get-company-by-subdomain'),
    path('api/companies/by-domain/<str:domain>/', views.get_company_by_domain_view, name='get-company-by-domain'),
    path('api/public-catalog/', views.public_catalog_view, name='public-catalog'),
    path('api/public-catalog/images/', views.public_images_view, name='public-images'),
    path('api/formas-pago-ecommerce/', views.formas_pago_ecommerce_view, name='formas-pago-ecommerce'),
    path('api/pasarelas-disponibles/', views.pasarelas_disponibles_view, name='pasarelas-disponibles'),
    path('api/procesar-pago-ecommerce/', views.procesar_pago_ecommerce_view, name='procesar-pago-ecommerce'),
    path('api/pasarela-response/', views.pasarela_response_view, name='pasarela-response'),
    path('api/celery/task-status/<str:task_id>/', views.celery_task_status_view, name='celery-task-status'),
    path('api/celery/cancel-task/<str:task_id>/', views.celery_cancel_task_view, name='celery-cancel-task'),
    path('api/backups/descargar/<str:token>/', views.descargar_backup_por_token, name='descargar-backup-token'),
]
