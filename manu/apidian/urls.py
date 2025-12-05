"""
URLs para APIDIAN
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApidianViewSet

router = DefaultRouter()
router.register(r'apidian', ApidianViewSet, basename='apidian')

urlpatterns = [
    path('api/', include(router.urls)),
]

