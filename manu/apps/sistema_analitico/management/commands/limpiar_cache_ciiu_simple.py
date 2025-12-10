"""
Versión simplificada del comando para limpiar cache CIIU.
Usa redis directamente sin pasar por Django cache para evitar problemas de conexión.
"""
from django.core.management.base import BaseCommand
import redis
from django.conf import settings


class Command(BaseCommand):
    help = '🗑️ Limpia el cache de códigos CIIU usando Redis directamente'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--codigo',
            type=str,
            help='Código CIIU específico a limpiar (ej: 5611)',
        )
        parser.add_argument(
            '--todos',
            action='store_true',
            help='Limpiar TODOS los caches de CIUU',
        )

    def handle(self, *args, **options):
        codigo = options['codigo']
        todos = options['todos']
        
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS('🗑️ LIMPIEZA DE CACHE CIIU (Directo)'))
        self.stdout.write('=' * 60)
        self.stdout.write('')
        
        # Obtener URL de Redis desde settings
        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6380/0')
        
        # Parsear URL de Redis
        # Formato: redis://localhost:6380/0
        if redis_url.startswith('redis://'):
            redis_url = redis_url.replace('redis://', '')
            parts = redis_url.split('/')
            host_port = parts[0]
            if ':' in host_port:
                host, port = host_port.split(':')
                port = int(port)
            else:
                host = host_port
                port = 6379
        else:
            host = 'localhost'
            port = 6380
        
        self.stdout.write(f"📋 Conectando a Redis: {host}:{port}")
        self.stdout.write('')
        
        try:
            # Conectar a Redis directamente
            r = redis.Redis(host=host, port=port, db=0, decode_responses=True)
            
            # Verificar conexión
            r.ping()
            self.stdout.write(self.style.SUCCESS("✅ Conectado a Redis"))
            self.stdout.write('')
            
            if todos:
                # Limpiar todos los caches de CIUU
                self.stdout.write("🔍 Buscando todas las claves de cache CIIU...")
                keys = r.keys("ciiu_*")
                
                if not keys:
                    self.stdout.write(self.style.WARNING("   ⚠️  No se encontraron caches de CIUU"))
                    return
                
                self.stdout.write(f"   📋 Encontradas {len(keys)} claves")
                self.stdout.write('')
                
                deleted_count = 0
                for key in keys:
                    r.delete(key)
                    deleted_count += 1
                    if deleted_count <= 10:  # Mostrar solo las primeras 10
                        self.stdout.write(self.style.SUCCESS(f"   ✅ Eliminado: {key}"))
                    elif deleted_count == 11:
                        self.stdout.write(f"   ... y {len(keys) - 10} más")
                
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Eliminadas {deleted_count} claves de cache"
                ))
            else:
                if not codigo:
                    self.stdout.write(self.style.ERROR(
                        '❌ Error: Debes especificar --codigo o --todos'
                    ))
                    return
                
                # Limpiar código específico
                cache_keys = [
                    f"ciiu_info_{codigo}",
                    f"ciiu_modelo_{codigo}",
                ]
                
                self.stdout.write(f"🔍 Limpiando cache para código CIIU: {codigo}")
                self.stdout.write('')
                
                deleted_count = 0
                for key in cache_keys:
                    if r.exists(key):
                        r.delete(key)
                        self.stdout.write(self.style.SUCCESS(f"   ✅ Eliminado: {key}"))
                        deleted_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(f"   ⚠️  No existe: {key}"))
                
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Limpieza completada: {deleted_count} claves eliminadas"
                ))
            
        except redis.ConnectionError as e:
            self.stdout.write(self.style.ERROR(
                f"❌ Error de conexión a Redis: {str(e)}"
            ))
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                f"💡 Verifica que Redis esté corriendo en {host}:{port}"
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"❌ Error: {str(e)}"
            ))
        
        self.stdout.write('')
        self.stdout.write('=' * 60)

