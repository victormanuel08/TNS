"""
Comando de Django para insertar API keys de prueba (MANU1 a MANU5)
Crea 5 registros con api_key temporal que debe actualizarse manualmente después.
"""
from django.core.management.base import BaseCommand
from apps.sistema_analitico.models import AIAnalyticsAPIKey
import uuid


class Command(BaseCommand):
    help = 'Crea 5 registros MANU1 a MANU5 con api_key temporal (debe actualizarse manualmente)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("CREANDO API KEYS MANU1 - MANU5"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        
        creados = 0
        ya_existian = 0
        
        for i in range(1, 6):
            nombre = f"MANU{i}"
            
            try:
                # Verificar si ya existe
                AIAnalyticsAPIKey.objects.get(nombre=nombre)
                ya_existian += 1
                self.stdout.write(self.style.WARNING(f"   ⚠️  {nombre}: Ya existe, omitido"))
                    
            except AIAnalyticsAPIKey.DoesNotExist:
                # Crear nuevo con api_key temporal (UUID aleatorio)
                api_key_temporal = f"temp-{uuid.uuid4().hex[:20]}"
                AIAnalyticsAPIKey.objects.create(
                    nombre=nombre,
                    api_key=api_key_temporal,
                    activa=True
                )
                creados += 1
                self.stdout.write(self.style.SUCCESS(f"   ✅ {nombre}: Creado (api_key temporal: {api_key_temporal})"))
        
        # Resumen
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("RESUMEN:"))
        self.stdout.write(f"   - Creados: {creados}")
        self.stdout.write(f"   - Ya existían: {ya_existian}")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        
        if creados > 0:
            self.stdout.write(self.style.WARNING("\n⚠️  IMPORTANTE: Los api_key son temporales."))
            self.stdout.write(self.style.WARNING("   Debes actualizarlos manualmente con los valores reales."))
        
        # Mostrar todas las API keys MANU activas
        self.stdout.write(self.style.SUCCESS("\n📋 API Keys MANU en BD:"))
        api_keys = AIAnalyticsAPIKey.objects.filter(nombre__startswith='MANU').order_by('nombre')
        for ak in api_keys:
            api_key_display = ak.api_key[:30] + "..." if len(ak.api_key) > 30 else ak.api_key
            self.stdout.write(f"   - {ak.nombre}: {api_key_display} (Activa: {ak.activa}, Peticiones: {ak.total_peticiones})")

