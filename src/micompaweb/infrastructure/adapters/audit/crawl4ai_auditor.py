"""Crawl4AI web auditor - scraping con Chrome + anti-bot + magic bypass."""

from typing import Optional, Any, TYPE_CHECKING
from datetime import datetime

from micompaweb.application.ports.web_auditor import (
    WebAuditor,
    WebAuditError,
    TechnicalAudit,
    SSLResult,
    TrackingResult,
    TechStackResult,
    ContactResult,
)
from micompaweb.infrastructure.browser.anti_bot import (
    BrowserEmulator,
    BrowserProfile,
    WAFDetector,
    SmartRetry,
)
from micompaweb.infrastructure.deps_manager import is_available

if TYPE_CHECKING:
    from crawl4ai import AsyncWebCrawler


class Crawl4Auditor:
    """Auditor completo usando Crawl4AI + anti-bot system.

    Arquitectura:
    1. Usa el HeavyExecutor (Crawl4AI + stealth + magic=True) para obtener HTML
    2. Usa el orquestador FetchOrchestrator para auto-escalación
    3. Reutiliza SimpleAuditor para análisis estático (SSL, tracking, contacts)
    4. Cuando Crawl4AI obtiene el HTML, aprovecha features extras (screenshots, JS-exec)

    Ventajas vs SimpleAuditor:
    - Ejecuta JavaScript (SPA frameworks, lazy-loaded content)
    - Detecta tracking dinámico (injected by JS)
    - Screenshots disponibles vía Crawl4AI
    - Auto-bypass de WAFs (magic=True)
    - Tech stack más preciso (detecta frameworks JS que cargan vía XHR)

    Requiere Crawl4AI >= 0.4.0:
        pip install crawl4ai>=0.4.0
    """

    def __init__(self, headless: bool = True, auto_escalate: bool = True):
        self.headless = headless
        self.auto_escalate = auto_escalate
        self._crawler: Optional["AsyncWebCrawler"] = None
        self._waf_detector = WAFDetector()
        self._browser_emulator = BrowserEmulator()
        self._check_crawl4ai_available()

    def _check_crawl4ai_available(self) -> None:
        try:
            import crawl4ai
        except ImportError:
            raise ImportError(
                "crawl4ai is required for Crawl4Auditor. "
                "Install with: pip install crawl4ai>=0.4.0"
            )

    async def audit(self, url: str) -> TechnicalAudit:
        """Audita sitio completo con Crawl4AI + anti-bot."""
        if not url or not url.startswith(("http://", "https://")):
            raise WebAuditError(f"Invalid URL: {url}")

        # 1. SSL check (independiente del crawler)
        ssl_result = await self.check_ssl(url)

        # 2. Fetch HTML via Crawl4AI con anti-bot
        fetch_result = await self._fetch_html(url)
        html = fetch_result.text

        if not html:
            # Si Crawl4AI falló, retornar solo SSL
            return TechnicalAudit(
                ssl=ssl_result,
                tracking=TrackingResult(False, False, False),
                tech_stack=TechStackResult([]),
                contacts=ContactResult([], [], {}),
            )

        # 3. Parse con BeautifulSoup para análisis estático
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
        except ImportError:
            soup = None  # type: ignore

        # 4. Análisis paralelos
        tracking = await self.check_tracking(html)
        tech_stack = await self.detect_tech_stack(html, soup) if soup else TechStackResult([])
        contacts = await self.extract_contacts(html, soup, url) if soup else ContactResult([], [], {})

        # 5. Extra info que solo Crawl4AI puede obtener
        copyright_year = self._extract_copyright_year(soup) if soup else None
        page_title = self._extract_title(soup) if soup else None
        meta_description = self._extract_meta_description(soup) if soup else None
        mobile_friendly = self._check_mobile_friendly(soup) if soup else False
        load_time_ms = fetch_result.response_time_ms

        return TechnicalAudit(
            ssl=ssl_result,
            tracking=tracking,
            tech_stack=tech_stack,
            contacts=contacts,
            mobile_friendly=mobile_friendly,
            load_time_ms=load_time_ms,
            copyright_year=copyright_year,
            page_title=page_title,
            meta_description=meta_description,
        )

    async def _fetch_html(self, url: str) -> "FetchResult":
        """Obtiene HTML via Crawl4AI con estrategia anti-bot."""
        from micompaweb.infrastructure.browser.executors import HeavyExecutor
        from micompaweb.infrastructure.browser.anti_bot import FetchResult as BotFetchResult

        executor = HeavyExecutor(
            emulator=self._browser_emulator,
            headless=self.headless,
        )

        # Usar perfil determinístico según URL
        profile = self._browser_emulator.get_profile_by_hash(urlparse(url).netloc)

        result = await executor.fetch(url, profile=profile)

        return BotFetchResult(
            status_code=result.status_code,
            headers=result.headers,
            text=result.html,
            url=result.url,
            strategy=result.strategy,
            error=result.error,
            is_bot_detected=result.waf_detected,
            response_time_ms=result.response_time_ms,
        )

    async def check_ssl(self, url: str) -> SSLResult:
        """Delega a SimpleAuditor para SSL (mismo código, testeado)."""
        from .simple_auditor import SimpleAuditor
        simple = SimpleAuditor()
        return await simple.check_ssl(url)

    async def check_tracking(self, html: str) -> TrackingResult:
        """Detecta tracking (más completo con JS ejecutado)."""
        html_lower = html.lower()

        has_meta_pixel = any(
            pattern in html_lower
            for pattern in [
                "fbq(", "facebook.com/tr", "pixel.facebook.com",
                "connect.facebook.net/en_us/fbevents.js",
            ]
        )
        has_gtm = "googletagmanager.com" in html_lower
        has_analytics = any(
            pattern in html_lower
            for pattern in [
                "google-analytics.com/analytics.js", "googleanalytics",
                "gtag(", "ga('create'", "ga('send'",
            ]
        )
        has_linkedin = "linkedin.com/insight" in html_lower or "_linkedin_partner_id" in html_lower
        has_tiktok = "tiktok.com/tr" in html_lower or "ttq.track" in html_lower

        return TrackingResult(
            has_meta_pixel=has_meta_pixel,
            has_gtm=has_gtm,
            has_analytics=has_analytics,
            has_linkedin_pixel=has_linkedin,
            has_tiktok_pixel=has_tiktok,
        )

    async def detect_tech_stack(self, html: str, soup: Optional[Any] = None) -> TechStackResult:
        """Detecta tech stack con precisión mejorada (JS ejecutado detecta más cosas)."""
        html_lower = html.lower()
        detected = []
        cms = None
        framework = None

        # CMS Detection
        if "wp-content" in html_lower or "wordpress" in html_lower:
            detected.append("WordPress")
            cms = "WordPress"
        if "wix.com" in html_lower or "wix-locale" in html_lower:
            detected.append("Wix")
            cms = "Wix"
        if "shopify.com" in html_lower or "cdn.shopify.com" in html_lower:
            detected.append("Shopify")
            cms = "Shopify"
        if "squarespace.com" in html_lower or "squarespace-cdn" in html_lower:
            detected.append("Squarespace")
            cms = "Squarespace"
        if "webflow" in html_lower:
            detected.append("Webflow")
            cms = "Webflow"
        if "elementor" in html_lower:
            detected.append("Elementor")

        # Frameworks JS (Crawl4AI detecta más por JS ejecutado)
        if "react" in html_lower or "reactroot" in html_lower or "data-reactroot" in html_lower:
            detected.append("React")
            framework = "React"
        if "vue.js" in html_lower or "vue-" in html_lower or "__v_" in html_lower:
            detected.append("Vue.js")
            framework = "Vue.js"
        if "angular" in html_lower or "ng-app" in html_lower:
            detected.append("Angular")
            framework = "Angular"
        if "next.js" in html_lower or "__next" in html_lower:
            detected.append("Next.js")
            framework = "Next.js"
        if "nuxt" in html_lower:
            detected.append("Nuxt.js")
            framework = "Nuxt.js"
        if "svelte" in html_lower:
            detected.append("Svelte")
        if "astro" in html_lower:
            detected.append("Astro")

        # CDN / Hosting
        if "cloudflare" in html_lower:
            detected.append("Cloudflare")
        if "amazonaws.com" in html_lower or "aws" in html_lower:
            detected.append("AWS")
        if "googleapis.com" in html_lower:
            detected.append("Google Cloud")

        # Generator meta
        if soup:
            generator = soup.find("meta", attrs={"name": "generator"})
            if generator and generator.get("content"):
                detected.append(generator["content"])

        return TechStackResult(
            detected_platforms=list(set(detected)),
            cms=cms,
            framework=framework,
        )

    async def extract_contacts(self, html: str, soup: Optional[Any], base_url: str) -> ContactResult:
        """Delega a SimpleAuditor para contacts (mismo código testeado)."""
        from .simple_auditor import SimpleAuditor
        simple = SimpleAuditor()
        if soup:
            return await simple.extract_contacts(html, soup, base_url)
        return ContactResult([], [], {})

    def _extract_copyright_year(self, soup) -> Optional[int]:
        """Extrae año de copyright del footer."""
        if not soup or not hasattr(soup, "get_text"):
            return None
        text = soup.get_text()
        current_year = datetime.now().year
        for year in range(current_year + 1, 1989, -1):
            if f"©{year}" in text or f"copyright {year}" in text.lower():
                return year
        return None

    def _extract_title(self, soup) -> Optional[str]:
        if not soup or not hasattr(soup, "find"):
            return None
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)
        return None

    def _extract_meta_description(self, soup) -> Optional[str]:
        if not soup or not hasattr(soup, "find"):
            return None
        desc = soup.find("meta", attrs={"name": "description"})
        if desc:
            return desc.get("content", "")
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc:
            return og_desc.get("content", "")
        return None

    def _check_mobile_friendly(self, soup) -> bool:
        if not soup or not hasattr(soup, "find"):
            return False
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if viewport and viewport.get("content"):
            return "width=device-width" in viewport["content"].lower()
        return False

    @property
    def auditor_name(self) -> str:
        return "crawl4ai_chrome_antibot"

    @property
    def requires_browser(self) -> bool:
        return True

    async def close(self) -> None:
        """Limpia recursos del crawler."""
        if self._crawler:
            await self._crawler.close()
            self._crawler = None
