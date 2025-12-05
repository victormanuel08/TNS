from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from rest_framework_simplejwt.views import TokenRefreshView
from apps.sistema_analitico import views
from django.conf import settings
from django.conf.urls.static import static

def redirect_to_admin(request):
    """Redirige el root al admin estándar"""
    return redirect('/admin/')

urlpatterns = [
    path('admin/', admin.site.urls),  # Admin clásico de Django
    path('', redirect_to_admin),  # Redirige root al admin
    path('', include('apps.sistema_analitico.urls')),
    path('dian/', include('apps.dian_scraper.urls')),
    path('fudo/', include('apps.fudo_scraper.urls')),
    path('', include('apidian.urls')),  # URLs de APIDIAN
    path('api/auth/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', views.logout_view, name='logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)