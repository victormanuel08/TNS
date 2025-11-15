import asyncio
import os
from pathlib import Path
from typing import Optional
from django.conf import settings
from playwright.async_api import async_playwright, Browser, Page

class DianScraperService:
    def __init__(self, session_id: int):
        self.session_id = session_id
        self.download_dir = Path(settings.MEDIA_ROOT) / 'dian_downloads' / f"session_{session_id}"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def start_scraping(self, url: str, tipo: str, fecha_desde: str, fecha_hasta: str) -> dict:
        """Inicia el proceso de scraping"""
        try:
            await self._initialize_browser()
            await self._navigate_to_dian(url, tipo)
            await self._apply_date_filters(fecha_desde, fecha_hasta)
            documents_count = await self._download_documents()
            return {"success": True, "documents_downloaded": documents_count}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            await self._close_browser()

    async def _initialize_browser(self):
        """Inicializa el navegador con Playwright"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,  # Cambiar a False para debugging
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        )
        
        self.page = await self.browser.new_page()
        
        # Configurar descargas
        await self.page._client.send(
            "Page.setDownloadBehavior",
            {
                "behavior": "allow",
                "downloadPath": str(self.download_dir),
            },
        )

    async def _navigate_to_dian(self, url: str, tipo: str):
        """Navega al portal DIAN"""
        print(f"🟡 Ingresando a DIAN: {url}")
        await self.page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Navegar a la sección de documentos
        domain = "/".join(url.split("/")[:3])  # Extraer dominio
        documents_url = f"{domain}/Document/{tipo}"
        print(f"🟢 Redirigiendo a documentos: {documents_url}")
        await self.page.goto(documents_url, wait_until="networkidle", timeout=60000)

    async def _apply_date_filters(self, fecha_desde: str, fecha_hasta: str):
        """Aplica filtros de fecha en la interfaz DIAN"""
        # Esperar a que el selector de fechas esté disponible
        await self.page.wait_for_selector('#dashboard-report-range', timeout=10000)
        
        # Formatear fechas (YYYY/MM/DD)
        fecha_desde_formatted = fecha_desde.replace('-', '/')
        fecha_hasta_formatted = fecha_hasta.replace('-', '/')
        date_range = f"{fecha_desde_formatted} - {fecha_hasta_formatted}"
        
        # Limpiar e ingresar nuevo rango
        input_range = await self.page.query_selector('#dashboard-report-range')
        await input_range.click(click_count=3)  # Seleccionar todo el texto
        await input_range.press('Backspace')
        await input_range.type(date_range)
        
        print(f"📅 Filtro de fechas ingresado: {date_range}")
        
        # Click en botón Buscar
        search_button = await self.page.query_selector('.btn.btn-success.btn-radian-success')
        if search_button:
            await search_button.click()
            
            # Esperar a que el loader desaparezca
            await self.page.wait_for_function(
                """() => {
                    const el = document.querySelector('#tableDocuments_processing');
                    return el && el.style.display === 'none';
                }""",
                timeout=120000
            )
            
            # Esperar a que se carguen las filas
            await self.page.wait_for_selector('#tableDocuments tbody tr', timeout=120000)
            
            tipo_text = "Enviados" if "Sent" in self.page.url else "Recibidos"
            print(f"🔍 Buscando documentos '{tipo_text}' entre {date_range}")

    async def _download_documents(self) -> int:
        """Descarga todos los documentos paginados"""
        total_documents = 0
        has_next_page = True
        current_page = 1

        while has_next_page:
            print(f"📄 Procesando página {current_page}")
            
            # Esperar a que la tabla se estabilice
            await self.page.wait_for_selector('#tableDocuments_wrapper')
            await asyncio.sleep(3)
            
            # Contar filas y botones de descarga
            rows = await self.page.query_selector_all('table#tableDocuments tbody tr')
            download_buttons = await self.page.query_selector_all('table#tableDocuments tbody tr button')
            
            print(f"🔍 {len(rows)} filas encontradas, {len(download_buttons)} botones de descarga")
            
            # Descargar cada documento
            for i, button in enumerate(download_buttons):
                try:
                    total_documents += 1
                    print(f"⬇️ Descargando archivo {total_documents}...")
                    await button.click()
                    await asyncio.sleep(2)  # Esperar entre descargas
                except Exception as e:
                    print(f"⚠️ Error descargando archivo {i+1}: {e}")
            
            # Verificar paginación
            next_button = await self.page.query_selector('#tableDocuments_next')
            if next_button:
                is_disabled = await next_button.evaluate('el => el.classList.contains("disabled")')
                
                if is_disabled:
                    has_next_page = False
                    print("✅ Fin del paginado")
                else:
                    current_page += 1
                    print("➡️ Navegando a siguiente página...")
                    await next_button.click()
                    await asyncio.sleep(2)
            else:
                has_next_page = False
        
        print(f"✅ Descargas completadas: {total_documents} archivos")
        return total_documents

    async def _close_browser(self):
        """Cierra el navegador"""
        if self.browser:
            await self.browser.close()
            
    async def test_dian_connection(self, url: str) -> bool:
        """Prueba si podemos conectar a DIAN"""
        try:
            await self._initialize_browser()
            await self.page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Verificar si estamos logueados (si la URL nos lleva a la página de documentos)
            if "Document" in self.page.url:
                return True
            else:
                # Podría ser que necesitemos redirigir manualmente
                documents_url = f"{url.split('/User')[0]}/Document/Sent"
                await self.page.goto(documents_url, wait_until="networkidle", timeout=30000)
                return "Document" in self.page.url
                
        except Exception as e:
            print(f"Error en test_connection: {e}")
            return False
        finally:
            await self._close_browser()