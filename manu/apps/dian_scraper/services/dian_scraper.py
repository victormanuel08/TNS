import asyncio
import time
from pathlib import Path
from typing import Optional

from django.conf import settings
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)


class DianScraperService:
    """
    Servicio que replica el flujo implementado originalmente en Node/Puppeteer.
    Se encarga de abrir el portal de la DIAN, aplicar filtros de fecha,
    descargar los XML comprimidos y dejar los archivos en media/dian_downloads.
    """

    def __init__(self, session_id: int):
        self.session_id = session_id
        self.download_dir = Path(settings.MEDIA_ROOT) / "dian_downloads" / f"session_{session_id}"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        # Permite desactivar headless desde .env si se requiere depurar visualmente
        self.headless = getattr(settings, "DIAN_SCRAPER_HEADLESS", True)

    async def start_scraping(self, url: str, tipo: str, fecha_desde: str, fecha_hasta: str) -> dict:
        """
        Ejecuta todo el flujo de scraping: login/redirect, filtros, descargas y paginación.
        """
        try:
            print(f"🟡 [SCRAPER] Iniciando sesión {self.session_id} | url={url} tipo={tipo} rango={fecha_desde} -> {fecha_hasta}")
            await self._initialize_browser()
            await self._navigate_to_dian(url, tipo)
            await self._apply_date_filters(fecha_desde, fecha_hasta)
            documents_count = await self._download_documents()
            return {"success": True, "documents_downloaded": documents_count}
        except Exception as exc:
            print(f"🔴 [SCRAPER] Error durante start_scraping: {exc}")
            return {"success": False, "error": str(exc)}
        finally:
            await self._close_browser()

    async def _initialize_browser(self):
        """
        Levanta Chromium con banderas similares al proyecto Puppeteer y configura la carpeta de descargas.
        """
        self.playwright = await async_playwright().start()
        launch_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
            "--window-size=1920,1080",
        ]

        self.browser = await self.playwright.chromium.launch(headless=self.headless, args=launch_args)
        print(f"🖥️ [SCRAPER] Navegador lanzado (headless={self.headless})")
        self.context = await self.browser.new_context(
            accept_downloads=True,
            viewport={"width": 1920, "height": 1080},
        )
        self.page = await self.context.new_page()

        # Playwright maneja las descargas vía evento; aseguramos crear el directorio
        self.context.set_default_timeout(100_000)

    async def _navigate_to_dian(self, url: str, tipo: str):
        """
        Abre la URL con token y redirige a Document/<tipo> como en el flujo Puppeteer.
        """
        if not self.page:
            raise RuntimeError("Playwright page not initialized")

        print(f"🟡 Ingresando a DIAN: {url}")
        await self.page.goto(url, wait_until="networkidle", timeout=100_000)

        domain = "/".join(url.split("/")[:3])
        documents_url = f"{domain}/Document/{tipo}"
        print(f"🟢 Redirigiendo a documentos: {documents_url}")
        await self.page.goto(documents_url, wait_until="networkidle", timeout=100_000)
        print(f"✅ URL actual: {self.page.url}")

    async def _apply_date_filters(self, fecha_desde: str, fecha_hasta: str):
        """
        Replica el comportamiento de Puppeteer: escribir el rango, click en buscar y esperar el loader.
        """
        if not self.page:
            raise RuntimeError("Playwright page not initialized")

        await self.page.wait_for_selector("#dashboard-report-range", timeout=10_000)
        date_range = f"{fecha_desde.replace('-', '/')} - {fecha_hasta.replace('-', '/')}"

        input_range = await self.page.query_selector("#dashboard-report-range")
        if not input_range:
            raise RuntimeError("No se encontró el selector de rango de fechas")

        await input_range.click(click_count=3)
        await input_range.press("Backspace")
        await input_range.type(date_range)
        print(f"📅 Filtro de fechas ingresado: {date_range}")

        search_button = await self.page.query_selector(".btn.btn-success.btn-radian-success")
        if search_button:
            await search_button.click()

        # Esperar a que desaparezca el loader como en Puppeteer
            await self.page.wait_for_function(
            """
                () => {
                    const el = document.querySelector('#tableDocuments_processing');
                    return el && el.style.display === 'none';
                }
            """,
            timeout=120_000,
        )
        await self.page.wait_for_selector("#tableDocuments tbody tr", timeout=120_000)

        tipo_text = "Enviados" if "Sent" in (self.page.url or "") else "Recibidos"
        print(f"🔍 Buscando documentos '{tipo_text}' entre {date_range}")

    async def _download_documents(self) -> int:
        """
        Recorre la paginación y descarga cada archivo, emulando el while del script Node.
        """
        if not self.page:
            raise RuntimeError("Playwright page not initialized")

        total_documents = 0
        has_next_page = True
        current_page = 1
        # Contador global para nombres únicos (persiste a través de todas las páginas)
        download_counter = [0]  # Usar lista para poder modificar desde función anidada

        while has_next_page:
            print(f"📄 Página {current_page}")

            await self.page.wait_for_selector("#tableDocuments_wrapper")
            await asyncio.sleep(4)

            rows = await self.page.query_selector_all("table#tableDocuments tbody tr")
            download_buttons = await self.page.query_selector_all("table#tableDocuments tbody tr button")
            print(f"🔍 {len(rows)} filas encontradas, {len(download_buttons)} botones de descarga")

            # Descargar en paralelo (máximo 5 simultáneas para no saturar)
            
            async def download_single_file(button, index):
                """Descarga un archivo individual"""
                try:
                    async with self.page.expect_download(timeout=30_000) as download_info:
                        await button.click()
                    download = await download_info.value
                    
                    # Generar nombre único para evitar sobrescritura
                    original_filename = download.suggested_filename
                    download_counter[0] += 1
                    unique_id = download_counter[0]
                    
                    # Usar timestamp en microsegundos + contador para garantizar unicidad
                    # incluso con descargas paralelas
                    timestamp_ms = int(time.time() * 1000000)  # Microsegundos
                    base_name = original_filename.replace('.zip', '')
                    # Formato: p{page}_i{index}_{timestamp}_{counter}_{original}.zip
                    unique_filename = f"p{current_page:02d}_i{index:03d}_{timestamp_ms}_{unique_id:04d}_{base_name}.zip"
                    file_path = self.download_dir / unique_filename
                    
                    # Verificar si ya existe (muy improbable pero por seguridad)
                    counter = 1
                    while file_path.exists():
                        unique_filename = f"p{current_page:02d}_i{index:03d}_{timestamp_ms}_{unique_id:04d}_{counter}_{base_name}.zip"
                        file_path = self.download_dir / unique_filename
                        counter += 1
                    
                    await download.save_as(file_path)
                    
                    # Verificar que el archivo se guardó correctamente
                    if file_path.exists():
                        file_size = file_path.stat().st_size
                        print(f"⬇️ [{index+1}/{len(download_buttons)}] Archivo descargado: {original_filename} -> {unique_filename} ({file_size} bytes)")
                    else:
                        print(f"⚠️ [{index+1}/{len(download_buttons)}] ERROR: Archivo no se guardó: {unique_filename}")
                    
                    return True
                except Exception as exc:
                    print(f"⚠️ [{index+1}/{len(download_buttons)}] Error descargando archivo: {exc}")
                    return False
            
            # Descargar en lotes configurables en paralelo
            # Nota: Aumentar este número consume más memoria y ancho de banda
            # Por defecto: 10 (configurable vía DIAN_SCRAPER_DOWNLOAD_BATCH_SIZE)
            batch_size = getattr(settings, 'DIAN_SCRAPER_DOWNLOAD_BATCH_SIZE', 10)
            for i in range(0, len(download_buttons), batch_size):
                batch = download_buttons[i:i+batch_size]
                batch_indices = list(range(i, min(i+batch_size, len(download_buttons))))
                
                print(f"📦 Descargando lote {i//batch_size + 1} ({len(batch)} archivos en paralelo)...")
                
                # Crear tareas para descargar en paralelo
                tasks = [download_single_file(btn, idx) for btn, idx in zip(batch, batch_indices)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Contar descargas exitosas
                successful = sum(1 for r in results if r is True)
                total_documents += successful
                
                print(f"✅ Lote completado: {successful}/{len(batch)} descargas exitosas")
                
                # Pequeña pausa entre lotes para no saturar
                if i + batch_size < len(download_buttons):
                    await asyncio.sleep(1)

            next_button = await self.page.query_selector("#tableDocuments_next")
            if not next_button:
                break

            is_disabled = await next_button.evaluate("el => el.classList.contains('disabled')")
            if is_disabled:
                print("✅ Fin del paginado")
                has_next_page = False
            else:
                print("➡️ Siguiente página...")
                await next_button.click()
                current_page += 1
                await asyncio.sleep(3)

        print(f"✅ Descargas completadas: {total_documents} archivos")
        return total_documents

    async def _close_browser(self):
        print("🧹 [SCRAPER] Cerrando navegador/contexto")
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def test_dian_connection(self, url: str) -> bool:
        """
        Reutiliza el mismo flujo que start_scraping pero sin filtros ni descargas:
        simplemente verifica si podemos acceder a Document/Sent.
        """
        try:
            await self._initialize_browser()
            await self.page.goto(url, wait_until="networkidle", timeout=60_000)
            if "Document" in (self.page.url or ""):
                return True

            documents_url = f"{url.split('/User')[0]}/Document/Sent"
            await self.page.goto(documents_url, wait_until="networkidle", timeout=60_000)
            success = "Document" in (self.page.url or "")
            print(f"🧪 [SCRAPER] Resultado test_connection -> {success}")
            return success
        except Exception as exc:
            print(f"Error en test_connection: {exc}")
            return False
        finally:
            await self._close_browser()
