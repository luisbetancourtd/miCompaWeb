"""Simple web auditor - httpx + BeautifulSoup (ligero, sin Chrome)."""

import re
import ssl
import time
import socket
from typing import Optional, List, Dict
from urllib.parse import urljoin, urlparse
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from micompaweb.application.ports.web_auditor import (
    WebAuditor,
    WebAuditError,
    TechnicalAudit,
    SSLResult,
    TrackingResult,
    TechStackResult,
    ContactResult,
)


class SimpleAuditor:
    """Auditor web ligero usando httpx + BeautifulSoup.

    Ventajas:
    - No requiere Chrome/Chromium (~150MB menos)
    - Más rápido (sin overhead de browser)
    - Funciona en cualquier entorno Docker

    Limitaciones:
    - No ejecuta JavaScript (SPA frameworks parcialmente)
    - No detecta tracking cargado dinámicamente
    """

    def __init__(self, timeout_seconds: int = 30):
        self.timeout = timeout_seconds
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene cliente HTTP."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
        return self._client

    async def audit(self, url: str) -> TechnicalAudit:
        """Audita completo un sitio web."""
        if not url or not url.startswith(("http://", "https://")):
            raise WebAuditError(f"Invalid URL: {url}")

        # Ejecutar todas las auditorías
        ssl_result = await self.check_ssl(url)

        fetch_start = time.monotonic()
        try:
            html = await self._fetch_html(url)
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            return TechnicalAudit(
                ssl=ssl_result,
                tracking=TrackingResult(False, False, False),
                tech_stack=TechStackResult([]),
                contacts=ContactResult([], [], {}),
            )
        load_time_ms = int((time.monotonic() - fetch_start) * 1000)

        tracking = await self.check_tracking(html)
        tech_stack = await self.detect_tech_stack(html, soup)
        contacts = await self.extract_contacts(html, soup, url)

        return TechnicalAudit(
            ssl=ssl_result,
            tracking=tracking,
            tech_stack=tech_stack,
            contacts=contacts,
            mobile_friendly=self._check_mobile_friendly(soup),
            load_time_ms=load_time_ms,
            copyright_year=self._extract_copyright_year(soup),
            page_title=self._extract_title(soup),
            meta_description=self._extract_meta_description(soup),
        )

    async def check_ssl(self, url: str) -> SSLResult:
        """Verifica certificado SSL."""
        if not url.startswith("https://"):
            return SSLResult(
                is_valid=False,
                error_message="HTTP only (no SSL)",
            )

        hostname = urlparse(url).hostname
        if not hostname:
            return SSLResult(is_valid=False, error_message="Invalid hostname")

        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()

                    # Verificar expiración
                    not_after = cert.get("notAfter")
                    expiry_date = None
                    if not_after:
                        expiry_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")

                    # Verificar emisor
                    issuer = cert.get("issuer")
                    issuer_str = ""
                    if issuer:
                        issuer_parts = [f"{k}={v}" for k, v in issuer]
                        issuer_str = ", ".join(issuer_parts)

                    return SSLResult(
                        is_valid=True,
                        expiry_date=expiry_date,
                        issuer=issuer_str,
                    )

        except ssl.SSLError as e:
            return SSLResult(is_valid=False, error_message=str(e))
        except socket.error as e:
            return SSLResult(is_valid=False, error_message=f"Connection error: {e}")
        except Exception as e:
            return SSLResult(is_valid=False, error_message=str(e))

    async def check_tracking(self, html: str) -> TrackingResult:
        """Detecta scripts de tracking."""
        html_lower = html.lower()

        # Meta Pixel (Facebook)
        has_meta_pixel = any(
            pattern in html_lower
            for pattern in [
                "fbq(",
                "facebook.com/tr",
                "pixel.facebook.com",
                "connect.facebook.net/en_US/fbevents.js",
            ]
        )

        # Google Tag Manager
        has_gtm = any(
            pattern in html_lower
            for pattern in [
                "googletagmanager.com/gtm.js",
                "gtm-",
                "gtm.",
            ]
        )

        # Google Analytics (Universal or GA4)
        has_analytics = any(
            pattern in html_lower
            for pattern in [
                "google-analytics.com/analytics.js",
                "googleanalytics",
                "gtag(",
                "ga('create'",
                "ga('send'",
            ]
        )

        # LinkedIn Pixel
        has_linkedin = "linkedin.com/insight" in html_lower or "_linkedin_partner_id" in html_lower

        # TikTok Pixel
        has_tiktok = "tiktok.com/tr" in html_lower or "ttq.track" in html_lower

        return TrackingResult(
            has_meta_pixel=has_meta_pixel,
            has_gtm=has_gtm,
            has_analytics=has_analytics,
            has_linkedin_pixel=has_linkedin,
            has_tiktok_pixel=has_tiktok,
        )

    async def detect_tech_stack(self, html: str, soup: BeautifulSoup) -> TechStackResult:
        """Detecta tecnologías utilizadas."""
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
        if "elementor" in html_lower or "elementor-pro" in html_lower:
            detected.append("Elementor")

        # Framework Detection
        if "react" in html_lower or "reactroot" in html_lower:
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

        # Generators
        generator = soup.find("meta", attrs={"name": "generator"})
        if generator and generator.get("content"):
            detected.append(generator["content"])

        # CDN Detection
        if "cloudflare" in html_lower:
            detected.append("Cloudflare")
        if "amazonaws.com" in html_lower or "aws" in html_lower:
            detected.append("AWS")

        return TechStackResult(
            detected_platforms=list(set(detected)),
            cms=cms,
            framework=framework,
        )

    async def extract_contacts(self, html: str, soup: BeautifulSoup, base_url: str) -> ContactResult:
        """Extrae información de contacto."""
        # Emails
        emails = self._extract_emails(html)

        # Phones
        phones = self._extract_phones(html)

        # Social links
        social_links = self._extract_social_links(soup, base_url)

        # Contact form detection
        has_contact_form = self._detect_contact_form(soup)

        # WhatsApp
        has_whatsapp = "wa.me" in html or "whatsapp.com" in html

        return ContactResult(
            emails=list(set(emails)),
            phones=list(set(phones)),
            social_links=social_links,
            has_contact_form=has_contact_form,
            has_whatsapp=has_whatsapp,
        )

    def _extract_emails(self, html: str) -> List[str]:
        """Extrae emails del HTML."""
        # Patrón regex para emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, html)

        # Filtrar falsos positivos comunes
        filtered = [
            e for e in emails
            if not any(x in e.lower() for x in [
                "example.com", "test.com", "domain.com", "email.com",
                "yourname", "username", "info@company", "email@domain"
            ])
        ]

        return list(set(filtered))[:10]  # Máximo 10 emails

    def _extract_phones(self, html: str) -> List[str]:
        """Extrae teléfonos del HTML."""
        # Patrones comunes de teléfono mexicano/USA
        patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # +1 (555) 555-5555
            r'\+52[-.\s]?\d{2}[-.\s]?\d{4}[-.\s]?\d{4}',  # +52 55 5555 5555
            r'\(\d{3}\)\s?\d{3}-\d{4}',  # (555) 555-5555
        ]

        phones = []
        for pattern in patterns:
            matches = re.findall(pattern, html)
            phones.extend(matches)

        return list(set(phones))[:5]

    def _extract_social_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Extrae links a redes sociales."""
        socials = {}

        all_links = soup.find_all("a", href=True)

        for link in all_links:
            href = link["href"].lower()

            if "facebook.com" in href:
                socials["facebook"] = urljoin(base_url, link["href"])
            elif "instagram.com" in href:
                socials["instagram"] = urljoin(base_url, link["href"])
            elif "twitter.com" in href or "x.com" in href:
                socials["twitter"] = urljoin(base_url, link["href"])
            elif "linkedin.com" in href:
                socials["linkedin"] = urljoin(base_url, link["href"])
            elif "youtube.com" in href or "youtu.be" in href:
                socials["youtube"] = urljoin(base_url, link["href"])
            elif "tiktok.com" in href:
                socials["tiktok"] = urljoin(base_url, link["href"])
            elif "wa.me" in href or "whatsapp.com" in href:
                socials["whatsapp"] = urljoin(base_url, link["href"])

        return socials

    def _detect_contact_form(self, soup: BeautifulSoup) -> bool:
        """Detecta si hay formulario de contacto."""
        forms = soup.find_all("form")
        for form in forms:
            # Buscar indicadores de formulario de contacto
            form_text = str(form).lower()
            if any(word in form_text for word in [
                "contact", "message", "email", "name", "phone",
                "enviar", "contacto", "mensaje", "nombre", "teléfono"
            ]):
                return True
        return False

    def _check_mobile_friendly(self, soup: BeautifulSoup) -> bool:
        """Verifica si tiene viewport responsive."""
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if viewport and viewport.get("content"):
            content = viewport["content"].lower()
            return "width=device-width" in content
        return False

    def _extract_copyright_year(self, soup: BeautifulSoup) -> Optional[int]:
        """Extrae año de copyright del footer."""
        footer = soup.find("footer")
        if footer:
            text = footer.get_text()
            # Buscar año entre 1990 y año actual + 1
            current_year = datetime.now().year
            for year in range(current_year + 1, 1989, -1):
                if str(year) in text:
                    return year

        # Buscar en todo el documento
        text = soup.get_text()
        for year in range(datetime.now().year + 1, 1989, -1):
            if f"©{year}" in text or f"copyright {year}" in text.lower():
                return year

        return None

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrae título de la página."""
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)
        return None

    def _extract_meta_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrae meta description."""
        desc = soup.find("meta", attrs={"name": "description"})
        if desc:
            return desc.get("content", "")

        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc:
            return og_desc.get("content", "")

        return None

    async def _fetch_html(self, url: str) -> str:
        """Obtiene HTML de la URL."""
        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()
        return response.text

    @property
    def auditor_name(self) -> str:
        return "simple_httpx_bs4"

    @property
    def requires_browser(self) -> bool:
        return False
