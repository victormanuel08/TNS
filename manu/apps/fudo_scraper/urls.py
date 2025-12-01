from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sessions', views.FudoScrapingSessionViewSet, basename='fudo-scraping-session')
router.register(r'documents', views.FudoDocumentProcessedViewSet, basename='fudo-document-processed')

urlpatterns = [
    path('api/', include(router.urls)),
]

