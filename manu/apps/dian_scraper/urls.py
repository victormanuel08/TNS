from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sessions', views.ScrapingSessionViewSet, basename='scraping-session')
router.register(r'documents', views.DocumentProcessedViewSet, basename='document-processed')

urlpatterns = [
    path('api/', include(router.urls)),
]