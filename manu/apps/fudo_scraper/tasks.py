from celery import shared_task
from django.utils import timezone
from .models import FudoScrapingSession, FudoDocumentProcessed
from .services.fudo_scraper import FudoScraperService


@shared_task
def run_fudo_scraping_task(session_id):
    """
    Tarea Celery para ejecutar el scraping de FUDO de forma asíncrona
    """
    try:
        session = FudoScrapingSession.objects.get(id=session_id)
        session.status = 'running'
        session.started_at = timezone.now()
        session.save()

        # Crear servicio de scraping
        scraper = FudoScraperService(
            session_id=session.id,
            empresa_servidor=session.empresa_servidor,
            usuario=session.usuario_fudo,
            password=session.password_fudo
        )

        # Callback para actualizar progreso
        def update_progress(actual, total, exitosas, fallidas):
            session.facturas_procesadas = actual
            session.facturas_exitosas = exitosas
            session.facturas_fallidas = fallidas
            session.total_facturas = total
            session.save(update_fields=[
                'facturas_procesadas',
                'facturas_exitosas',
                'facturas_fallidas',
                'total_facturas'
            ])

        # Ejecutar scraping
        result = scraper.ejecutar_scraping(
            fecha_desde=session.fecha_desde,
            fecha_hasta=session.fecha_hasta,
            callback=update_progress
        )

        if result['success']:
            session.status = 'completed'
            session.completed_at = timezone.now()
            session.facturas_procesadas = result.get('total', 0)
            session.facturas_exitosas = result.get('exitosas', 0)
            session.facturas_fallidas = result.get('fallidas', 0)
            session.total_facturas = result.get('total', 0)
            session.save()
            
            # Los documentos procesados se crean en el servicio durante el procesamiento
        else:
            session.status = 'failed'
            session.error_message = result.get('error', 'Error desconocido')
            session.save()

    except FudoScrapingSession.DoesNotExist:
        print(f"❌ Sesión {session_id} no encontrada")
    except Exception as e:
        print(f"❌ Error en tarea de scraping: {str(e)}")
        try:
            session = FudoScrapingSession.objects.get(id=session_id)
            session.status = 'failed'
            session.error_message = str(e)
            session.save()
        except:
            pass

