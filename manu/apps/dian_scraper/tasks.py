import asyncio
import re
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import (
    ScrapingSession,
    DocumentProcessed,
    ScrapingRange,
)
from .services.dian_scraper import DianScraperService
from .services.file_processor import FileProcessor

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
        fecha_desde = session.ejecutado_desde or session.fecha_desde
        fecha_hasta = session.ejecutado_hasta or session.fecha_hasta
        
        # Ejecutar async en event loop
        async def run_async():
            return await scraper.start_scraping(
                url=session.url,
                tipo=session.tipo,
                fecha_desde=fecha_desde.strftime('%Y-%m-%d'),
                fecha_hasta=fecha_hasta.strftime('%Y-%m-%d')
            )
        
        result = asyncio.run(run_async())
        
        if result['success']:
            # Procesar archivos descargados
            processor = FileProcessor()
            processing_result = processor.process_downloaded_files(session_id, session.tipo)
            
            if 'error' not in processing_result:
                # documents_downloaded = archivos ZIP descargados
                # documents_processed = documentos XML válidos procesados
                zip_files_downloaded = result['documents_downloaded']
                documents_processed = processing_result.get('documents_count', len(processing_result.get('documents', [])))
                zip_stats = processing_result.get('zip_stats', {})
                
                print(f"📊 [TASK] Resumen final:")
                print(f"   - Archivos ZIP descargados: {zip_files_downloaded}")
                print(f"   - Documentos XML procesados: {documents_processed}")
                if zip_stats:
                    print(f"   - ZIPs procesados exitosamente: {zip_stats.get('zips_procesados', 0)}")
                    print(f"   - ZIPs vacíos: {zip_stats.get('zips_vacios', 0)}")
                    print(f"   - ZIPs con error: {zip_stats.get('zips_con_error', 0)}")
                
                session.documents_downloaded = zip_files_downloaded  # Mantener compatibilidad
                session.excel_file = processing_result['excel_file']
                session.json_file = processing_result['json_file']
                session.status = 'completed'
                session.completed_at = timezone.now()
                session.ejecutado_desde = fecha_desde
                session.ejecutado_hasta = fecha_hasta
                
                # Guardar estadísticas en error_message si hay discrepancia
                if zip_files_downloaded > documents_processed:
                    diferencia = zip_files_downloaded - documents_processed
                    session.error_message = f"Advertencia: Se descargaron {zip_files_downloaded} archivos ZIP, pero solo se procesaron {documents_processed} documentos XML válidos. {diferencia} ZIPs pueden estar vacíos o tener errores."
                
                # Crear registros de documentos procesados
                actual_nit = _extract_actual_nit(
                    processing_result['documents'],
                    session.tipo,
                    session.nit,
                )
                if actual_nit:
                    session.nit = actual_nit

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
                _merge_coverage(session.nit, session.tipo, fecha_desde, fecha_hasta)
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


def _extract_actual_nit(documents, tipo, fallback):
    target_field = 'NIT del Emisor'
    if tipo and str(tipo).lower().startswith('rece'):
        target_field = 'NIT del Receptor'

    for doc in documents or []:
        candidate = _normalize_nit(doc.get(target_field, ''))
        if candidate:
            return candidate
    return _normalize_nit(fallback)


def _normalize_nit(value):
    if not value:
        return ''
    return re.sub(r'\D', '', str(value))


def _merge_coverage(nit: str, tipo: str, start, end):
    ranges = ScrapingRange.objects.filter(nit=nit, tipo=tipo).order_by('start_date')
    merged_start = start
    merged_end = end
    overlapping_ids = []
    one_day = timedelta(days=1)

    for r in ranges:
        if r.end_date < merged_start - one_day:
            continue
        if r.start_date > merged_end + one_day:
            break
        overlapping_ids.append(r.id)
        merged_start = min(merged_start, r.start_date)
        merged_end = max(merged_end, r.end_date)

    if overlapping_ids:
        ScrapingRange.objects.filter(id__in=overlapping_ids).delete()

    ScrapingRange.objects.create(
        nit=nit,
        tipo=tipo,
        start_date=merged_start,
        end_date=merged_end,
    )
