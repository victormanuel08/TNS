"""
Django management command para configurar una API Key con scraping total sin restricciones.

Uso:
    python manage.py configurar_api_key_scraping_total <api_key_id>
    python manage.py configurar_api_key_scraping_total --api-key <api_key_string>
    python manage.py configurar_api_key_scraping_total --nit <nit>
"""

from django.core.management.base import BaseCommand
from apps.sistema_analitico.models import APIKeyCliente


class Command(BaseCommand):
    help = 'Configura una API Key para permitir scraping total sin validar empresas'

    def add_arguments(self, parser):
        parser.add_argument(
            'api_key_id',
            nargs='?',
            type=int,
            help='ID de la API Key a configurar'
        )
        parser.add_argument(
            '--api-key',
            type=str,
            help='API Key (string) a configurar'
        )
        parser.add_argument(
            '--nit',
            type=str,
            help='NIT de la API Key a configurar'
        )
        parser.add_argument(
            '--desactivar',
            action='store_true',
            help='Desactivar scraping total (poner en False)'
        )

    def handle(self, *args, **options):
        api_key_obj = None
        
        # Buscar por ID
        if options['api_key_id']:
            try:
                api_key_obj = APIKeyCliente.objects.get(id=options['api_key_id'])
            except APIKeyCliente.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ API Key con ID {options["api_key_id"]} no encontrada')
                )
                return
        
        # Buscar por API Key string
        elif options['api_key']:
            try:
                api_key_obj = APIKeyCliente.objects.get(api_key=options['api_key'])
            except APIKeyCliente.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ API Key "{options["api_key"]}" no encontrada')
                )
                return
        
        # Buscar por NIT
        elif options['nit']:
            try:
                api_key_obj = APIKeyCliente.objects.get(nit=options['nit'])
            except APIKeyCliente.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ API Key con NIT {options["nit"]} no encontrada')
                )
                return
        else:
            self.stdout.write(
                self.style.ERROR('❌ Debes proporcionar: ID, --api-key, o --nit')
            )
            return
        
        # Configurar el flag
        valor_anterior = api_key_obj.permite_scraping_total
        nuevo_valor = not options['desactivar']
        
        api_key_obj.permite_scraping_total = nuevo_valor
        api_key_obj.save()
        
        if nuevo_valor:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ API Key configurada para scraping TOTAL sin restricciones\n'
                    f'   ID: {api_key_obj.id}\n'
                    f'   NIT: {api_key_obj.nit}\n'
                    f'   Nombre: {api_key_obj.nombre_cliente}\n'
                    f'   API Key: {api_key_obj.api_key[:20]}...\n'
                    f'   Estado anterior: {valor_anterior}\n'
                    f'   Estado nuevo: {nuevo_valor}'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Scraping total DESACTIVADO para esta API Key\n'
                    f'   ID: {api_key_obj.id}\n'
                    f'   NIT: {api_key_obj.nit}\n'
                    f'   Nombre: {api_key_obj.nombre_cliente}\n'
                    f'   Ahora requiere empresas asociadas para scraping'
                )
            )

