"""Crawl4AI web auditor - scraping con Chrome (completo pero pesado)."""

from typing import Optional, TYPE_CHECKING

from micompaweb.application.ports.web_auditor import (
    WebAuditor,
    WebAuditError,
    TechnicalAudit,
    SSLResult,
    TrackingResult,
    TechStackResult,
    ContactResult,
)

# Crawl4AI es opcional
if TYPE_CHECKING:
    from crawl4ai import AsyncWebCrawler


class Crawl4Auditor:
    """Auditor usando Crawl4AI (requiere Chrome/Chromium).

    Ventajas:
    - Ejecuta JavaScript (SPA frameworks completamente)
    - Detecta tracking cargado dinámicamente
    - Screenshots disponibles
    - Más preciso en tech stack

    Desventajas:
    - Requiere Chrome (~150MB+)
    - Más lento (tiempo de inicialización del browser)
    - Puede ser bloqueado por bot detection
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._crawler: Optional["AsyncWebCrawler"] = None
        self._check_crawl4ai_available()

    def _check_crawl4ai_available(self) -> None:
        """Verifica que crawl4ai esté instalado."""
        try:
            import crawl4ai
        except ImportError:
            raise ImportError(
                "crawl4ai is required for Crawl4Auditor. "
                "Install with: pip install micompaweb[audit-heavy]"
            )

    async def _get_crawler(self):
        """Obtiene o crea crawler de Crawl4AI."""
        if self._crawler is None:
            from crawl4ai import AsyncWebCrawler

            self._crawler = AsyncWebCrawler(headless=self.headless)
            await self._crawler.start()

        return self._crawler

    async def audit(self, url: str) -> TechnicalAudit:
        """Audita sitio usando Crawl4AI."""
        crawler = await self._get_crawler()

        try:
            result = await crawler.arun(url)
            html = result.html
            soup = result.soup

            # SSL check
            ssl_result = await self.check_ssl(url)

            # Tracking detection
            tracking = await self.check_tracking(html)

            # Tech stack
            tech_stack = await self.detect_tech_stack(html, soup)

            # Contacts
            contacts = await self.extract_contacts(html, soup, url)

            return TechnicalAudit(
                ssl=ssl_result,
                tracking=tracking,
                tech_stack=tech_stack,
                contacts=contacts,
                mobile_friendly=result.responsive,
                load_time_ms=int(result.load_time * 1000) if result.load_time else None,
                copyright_year=self._extract_copyright_year(soup),
                page_title=result.title if hasattr(result, "title") else None,
                meta_description=result.description if hasattr(result, "description") else None,
            )

        except Exception as e:
            raise WebAuditError(f"Crawl4AI audit failed: {e}") from e

    async def check_ssl(self, url: str) -> SSLResult:
        """Delega a SimpleAuditor para SSL."""
        # Importar SimpleAuditor para reutilizar lógica SSL
        from .simple_auditor import SimpleAuditor
        simple = SimpleAuditor()
        return await simple.check_ssl(url)

    async def check_tracking(self, html: str) -> TrackingResult:
        """Detecta tracking (más completo con JS ejecutado)."""
        html_lower = html.lower()

        has_meta_pixel = "fbq(" in html_lower or "facebook.com/tr" in html_lower
        has_gtm = "googletagmanager.com" in html_lower
        has_analytics = "google-analytics" in html_lower or "gtag(" in html_lower
        has_linkedin = "linkedin.com/insight" in html_lower
        has_tiktok = "tiktok.com/tr" in html_lower

        return TrackingResult(
            has_meta_pixel=has_meta_pixel,
            has_gtm=has_gtm,
            has_analytics=has_analytics,
            has_linkedin_pixel=has_linkedin,
            has_tiktok_pixel=has_tiktok,
        )

    async def detect_tech_stack(self, html: str, soup) -> TechStackResult:
        """Detecta tech stack con más precisión."""
        html_lower = html.lower()
        detected = []
        cms = None
        framework = None

        # CMS
        if "wp-content" in html_lower:
            detected.append("WordPress")
            cms = "WordPress"
        elif "shopify" in html_lower:
            detected.append("Shopify")
            cms = "Shopify"
        elif "wix" in html_lower:
            detected.append("Wix")
            cms = "Wix"
        elif "squarespace" in html_lower:
            detected.append("Squarespace")
            cms = "Squarespace"

        # Frameworks JS
        if "react" in html_lower:
            detected.append("React")
        if "vue" in html_lower:
            detected.append("Vue.js")
        if "angular" in html_lower:
            detected.append("Angular")
        if "next.js" in html_lower or "__next" in html_lower:
            detected.append("Next.js")

        return TechStackResult(
            detected_platforms=list(set(detected)),
            cms=cms,
            framework=framework,
        )

    async def extract_contacts(self, html: str, soup, base_url: str) -> ContactResult:
        """Extrae contactos."""
        from .simple_auditor import SimpleAuditor
        simple = SimpleAuditor()
        return await simple.extract_contacts(html, soup, base_url)

    def _extract_copyright_year(self, soup) -> Optional[int]:
        """Extrae año de copyright."""
        from datetime import datetime

        text = soup.get_text() if hasattr(soup, "get_text") else str(soup)
        current_year = datetime.now().year

        for year in range(current_year + 1, 1989, -1):
            if str(year) in text:
                return year
        return None

    @property
    def auditor_name(self) -> str:
        return "crawl4ai_chrome"

    @property
    def requires_browser(self) -> bool:
        return True

    async def close(self) -> None:
        """Limpia recursos del crawler."""
        if self._crawler:
            await self._crawler.close()
            self._crawler = None
