"""
Comando para limpiar el cache de códigos CIIU de Redis.
Útil cuando se borra un CIUU de la base de datos y se quiere forzar la consulta a la API.
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
import redis


class Command(BaseCommand):
    help = '🗑️ Limpia el cache de códigos CIIU de Redis'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--codigo',
            type=str,
            help='Código CIIU específico a limpiar (ej: 5611)',
        )
        parser.add_argument(
            '--todos',
            action='store_true',
            help='Limpiar TODOS los caches de CIUU (peligroso)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se eliminaría SIN hacer cambios reales',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la eliminación sin confirmación',
        )

    def handle(self, *args, **options):
        codigo = options['codigo']
        todos = options['todos']
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS('🗑️ LIMPIEZA DE CACHE CIIU'))
        self.stdout.write('=' * 60)
        self.stdout.write('')
        
        # Mostrar configuración
        self.stdout.write(f"📋 CONFIGURACIÓN:")
        self.stdout.write(f"   • Dry-run: {dry_run}")
        self.stdout.write(f"   • Todos los caches: {todos}")
        if codigo:
            self.stdout.write(f"   • Código CIIU: {codigo}")
        self.stdout.write('-' * 60)
        self.stdout.write('')
        
        # Validar entrada
        if not codigo and not todos:
            self.stdout.write(self.style.ERROR(
                '❌ Error: Debes especificar --codigo o --todos'
            ))
            return
        
        # Confirmación (a menos que sea dry-run o force)
        if not dry_run and not force and todos:
            self.stdout.write(self.style.WARNING(
                '⚠️  ADVERTENCIA: Esto eliminará TODOS los caches de CIUU'
            ))
            respuesta = input('¿Estás seguro? (escribe "si" para confirmar): ')
            if respuesta.lower() != 'si':
                self.stdout.write(self.style.WARNING('❌ Operación cancelada'))
                return
        
        # Ejecutar limpieza
        if todos:
            deleted_count = self._limpiar_todos_los_caches(dry_run)
        else:
            deleted_count = self._limpiar_codigo_especifico(codigo, dry_run)
        
        # Mostrar resultados
        self.stdout.write('')
        self.stdout.write('=' * 60)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'✅ SIMULACIÓN COMPLETADA: {deleted_count} caches serían eliminados'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'✅ LIMPIEZA COMPLETADA: {deleted_count} caches eliminados'
            ))
        self.stdout.write('=' * 60)
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(
            '💡 TIP: La próxima vez que se consulte un CIUU, se buscará en BD y luego en la API'
        ))

    def _limpiar_codigo_especifico(self, codigo: str, dry_run: bool) -> int:
        """Limpia el cache de un código CIIU específico"""
        deleted_count = 0
        
        # Claves de cache que se usan para CIUU
        cache_keys = [
            f"ciiu_info_{codigo}",      # Cache de información de API
            f"ciiu_modelo_{codigo}",    # Cache del modelo ActividadEconomica
        ]
        
        self.stdout.write(f"🔍 Limpiando cache para código CIIU: {codigo}")
        self.stdout.write('')
        
        # Verificar conexión a Redis primero
        try:
            cache.get('test_connection')  # Intento de conexión
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"❌ Error de conexión a Redis: {str(e)}"
            ))
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                "💡 SOLUCIÓN: Asegúrate de que Redis esté corriendo en el puerto 6380"
            ))
            self.stdout.write("   O usa redis-cli directamente:")
            self.stdout.write(f"   redis-cli -p 6380 DEL ciiu_info_{codigo}")
            self.stdout.write(f"   redis-cli -p 6380 DEL ciiu_modelo_{codigo}")
            return 0
        
        for key in cache_keys:
            try:
                if dry_run:
                    if cache.get(key):
                        self.stdout.write(f"   📋 [DRY-RUN] Eliminaría: {key}")
                        deleted_count += 1
                    else:
                        self.stdout.write(f"   ℹ️  [DRY-RUN] No existe: {key}")
                else:
                    if cache.delete(key):
                        self.stdout.write(self.style.SUCCESS(f"   ✅ Eliminado: {key}"))
                        deleted_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(f"   ⚠️  No existe: {key}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Error con {key}: {str(e)}"))
        
        return deleted_count

    def _limpiar_todos_los_caches(self, dry_run: bool) -> int:
        """Limpia todos los caches de CIUU usando Redis directamente"""
        deleted_count = 0
        
        try:
            # Obtener conexión Redis desde cache
            # Django cache puede usar diferentes backends, intentar obtener Redis directamente
            from django.conf import settings
            from django.core.cache import caches
            
            # Intentar obtener el backend de cache
            cache_backend = caches['default']
            
            # Si es Redis, obtener la conexión
            if hasattr(cache_backend, '_cache') and hasattr(cache_backend._cache, 'client'):
                redis_client = cache_backend._cache.client
                
                self.stdout.write("🔍 Buscando todas las claves de cache CIIU...")
                self.stdout.write('')
                
                # Buscar todas las claves que empiezan con ciiu_
                pattern = "ciiu_*"
                keys = redis_client.keys(pattern)
                
                if not keys:
                    self.stdout.write(self.style.WARNING("   ⚠️  No se encontraron caches de CIUU"))
                    return 0
                
                self.stdout.write(f"   📋 Encontradas {len(keys)} claves de cache")
                self.stdout.write('')
                
                if dry_run:
                    for key in keys[:20]:  # Mostrar solo las primeras 20
                        key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                        self.stdout.write(f"   📋 [DRY-RUN] Eliminaría: {key_str}")
                    if len(keys) > 20:
                        self.stdout.write(f"   ... y {len(keys) - 20} más")
                    deleted_count = len(keys)
                else:
                    # Eliminar todas las claves
                    for key in keys:
                        key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                        if cache.delete(key_str):
                            deleted_count += 1
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"   ✅ Eliminadas {deleted_count} claves de cache"
                    ))
                
            else:
                # Si no es Redis o no podemos acceder directamente, usar método alternativo
                self.stdout.write(self.style.WARNING(
                    "⚠️  No se puede acceder directamente a Redis. "
                    "Usando método alternativo (menos eficiente)..."
                ))
                self.stdout.write('')
                
                # Método alternativo: intentar eliminar códigos comunes
                # Esto es menos eficiente pero funciona con cualquier backend
                codigos_comunes = [
                    '0010', '0141', '4123', '4290', '4291', '4530', '4520',
                    '4661', '4741', '4752', '4923', '0510', '5611', '5619',
                    '7010', '7490', '8299', '8560', '8621', '9512', '5530'
                ]
                
                for codigo in codigos_comunes:
                    deleted = self._limpiar_codigo_especifico(codigo, dry_run)
                    deleted_count += deleted
                
                self.stdout.write('')
                self.stdout.write(self.style.WARNING(
                    "💡 TIP: Para limpiar TODOS los caches, cierra y reinicia Redis"
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"❌ Error al limpiar caches: {str(e)}"
            ))
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                "💡 SOLUCIÓN ALTERNATIVA: Cierra y reinicia Redis para limpiar todo el cache"
            ))
        
        return deleted_count

