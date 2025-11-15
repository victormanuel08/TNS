from celery import shared_task
from django.utils import timezone
from .models import ScrapingSession
from .services.dian_scraper import DianScraperService
from .services.file_processor import FileProcessor
import asyncio

@shared_task
def run_dian_scraping_task(session_id):
    """
    Tarea Celery para ejecutar el scraping de DIAN de forma asíncrona
    """
    try:
        session = ScrapingSession.objects.get(id=session_id)
        session.status = 'running'
        session.save()
        
        # Ejecutar scraping
        scraper = DianScraperService(session_id)
        
        # Ejecutar async en event loop
        async def run_async():
            return await scraper.start_scraping(
                url=session.url,
                tipo=session.tipo,
                fecha_desde=session.fecha_desde.strftime('%Y-%m-%d'),
                fecha_hasta=session.fecha_hasta.strftime('%Y-%m-%d')
            )
        
        result = asyncio.run(run_async())
        
        if result['success']:
            # Procesar archivos descargados
            processor = FileProcessor()
            processing_result = processor.process_downloaded_files(session_id, session.tipo)
            
            if 'error' not in processing_result:
                session.documents_downloaded = result['documents_downloaded']
                session.excel_file = processing_result['excel_file']
                session.json_file = processing_result['json_file']
                session.status = 'completed'
                session.completed_at = timezone.now()
                
                # Crear registros de documentos procesados
                from .models import DocumentProcessed
                for doc_data in processing_result['documents']:
                    DocumentProcessed.objects.create(
                        session=session,
                        document_number=doc_data.get('Numero de Factura', ''),
                        cufe=doc_data.get('CUFE', ''),
                        issue_date=doc_data.get('Fecha de Creación'),
                        supplier_nit=doc_data.get('NIT del Emisor', ''),
                        supplier_name=doc_data.get('Razon Social del Emisor', ''),
                        customer_nit=doc_data.get('NIT del Receptor', ''),
                        customer_name=doc_data.get('Razon Social del Receptor', ''),
                        total_amount=doc_data.get('Total a Pagar', 0),
                        raw_data=doc_data
                    )
            else:
                session.status = 'failed'
                session.error_message = processing_result['error']
        else:
            session.status = 'failed'
            session.error_message = result['error']
        
        session.save()
        
    except Exception as e:
        session = ScrapingSession.objects.get(id=session_id)
        session.status = 'failed'
        session.error_message = str(e)
        session.save()
        raise e

# Tarea síncrona alternativa (sin Celery)
def run_dian_scraping_sync(session_id):
    """Versión síncrona para desarrollo/testing"""
    return run_dian_scraping_task(session_id)