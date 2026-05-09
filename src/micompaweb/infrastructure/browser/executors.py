"""Fetch executors - 3 estrategias reales contra anti-bot."""

import asyncio
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from urllib.parse import urlparse

from micompaweb.infrastructure.browser.anti_bot import (
    BrowserEmulator,
    BrowserProfile,
    FetchResult,
    WAFDetector,
    SmartRetry,
    AntiBotConfig,
)
from micompaweb.infrastructure.deps_manager import check_all


@dataclass
class ExecutorResult:
    """Resultado unificado de cualquier ejecutor."""
    html: str
    url: str
    status_code: int
    strategy: str
    headers: Dict[str, str] = None  # type: ignore
    error: Optional[str] = None
    waf_detected: bool = False
    response_time_ms: Optional[float] = None
    cookies: Optional[Dict[str, str]] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


class BaseFetchExecutor:
    """Clase base para todos los ejecutores."""

    def __init__(self, emulator: Optional[BrowserEmulator] = None):
        self.emulator = emulator or BrowserEmulator()
        self.waf_detector = WAFDetector()
        self.smart_retry = SmartRetry(max_attempts=3)

    @property
    def name(self) -> str:
        raise NotImplementedError

    async def fetch(self, url: str, **kwargs: Any) -> ExecutorResult:
        raise NotImplementedError

    def _build_fetch_result(self, executor_result: ExecutorResult) -> FetchResult:
        """Convierte resultado del executor al formato FetchResult."""
        return FetchResult(
            status_code=executor_result.status_code,
            headers=executor_result.headers,
            text=executor_result.html,
            url=executor_result.url,
            strategy=self.name,
            error=executor_result.error,
            is_bot_detected=executor_result.waf_detected,
            response_time_ms=executor_result.response_time_ms,
        )


class FastExecutor(BaseFetchExecutor):
    """Ejecutor FAST: curl_cffi + JA3 spoofing + headers rotados.

    Ideal para:
    - Sitios sin WAF o con protección ligera
    - Sitios que requieren headers reales pero no ejecución JS
    - Bajo consumo de recursos (~5-50MB RAM)

    Tiene fallback a httpx si curl_cffi no está disponible.
    """

    def __init__(self, emulator: Optional[BrowserEmulator] = None, timeout: int = 30):
        super().__init__(emulator)
        self.timeout = timeout
        self._check_deps()

    def _check_deps(self):
        """Verifica dependencias disponibles."""
        self.has_curl_cffi = check_all(["curl_cffi"]).get("curl_cffi", False)
        self.has_httpx = check_all(["httpx"]).get("httpx", False)

    @property
    def name(self) -> str:
        return "fast"

    @property
    def supports_ja3(self) -> bool:
        return self.has_curl_cffi

    async def fetch(self, url: str, **kwargs: Any) -> ExecutorResult:
        """Fetch via curl_cffi con JA3 spoofing o fallback a httpx."""
        start = time.time()
        profile = kwargs.get("profile") or self.emulator.get_random_profile()
        ja3_preset = kwargs.get("ja3_preset") or self.emulator.get_ja3_preset(profile)

        if self.has_curl_cffi:
            result = await self._fetch_curl_cffi(url, profile, ja3_preset)
        else:
            result = await self._fetch_httpx(url, profile)

        result.response_time_ms = (time.time() - start) * 1000
        return result

    async def _fetch_curl_cffi(self, url: str, profile: BrowserProfile, ja3_preset: str) -> ExecutorResult:
        try:
            from curl_cffi import requests as curl_requests
        except ImportError:
            return await self._fetch_httpx(url, profile)

        headers = self.emulator.get_headers(profile)

        # Referer realista
        parsed = urlparse(url)
        headers.setdefault("Referer", f"{parsed.scheme}://{parsed.netloc}/")

        try:
            response = curl_requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
                impersonate=ja3_preset,
                allow_redirects=True,
            )

            text = getattr(response, "text", "")
            status = getattr(response, "status_code", 0)
            resp_headers = dict(getattr(response, "headers", {}))

            # Detect WAF
            waf_detection = self.waf_detector.detect(status, resp_headers, text[:1000])

            return ExecutorResult(
                html=text,
                url=str(getattr(response, "url", url)),
                status_code=status,
                strategy="fast",
                headers=resp_headers,
                waf_detected=waf_detection.detected,
                cookies=dict(getattr(response, "cookies", {})) if hasattr(response, "cookies") else None,
            )

        except Exception as e:
            return ExecutorResult(
                html="",
                url=url,
                status_code=0,
                strategy="fast",
                error=f"curl_cffi error: {e}",
                waf_detected=False,
            )

    async def _fetch_httpx(self, url: str, profile: BrowserProfile) -> ExecutorResult:
        import httpx

        headers = self.emulator.get_headers(profile)

        async with httpx.AsyncClient(
            headers=headers,
            follow_redirects=True,
            timeout=httpx.Timeout(self.timeout),
        ) as client:
            try:
                response = await client.get(url)

                text = response.text
                resp_headers = dict(response.headers)
                status = response.status_code

                waf_detection = self.waf_detector.detect(status, resp_headers, text[:1000])

                return ExecutorResult(
                    html=text,
                    url=str(response.url),
                    status_code=status,
                    strategy="fast_fallback_httpx",
                    headers=resp_headers,
                    waf_detected=waf_detection.detected,
                )

            except Exception as e:
                return ExecutorResult(
                    html="",
                    url=url,
                    status_code=0,
                    strategy="fast",
                    error=f"httpx error: {e}",
                    waf_detected=False,
                )


class StrongExecutor(BaseFetchExecutor):
    """Ejecutor STRONG: Playwright + stealth + comportamiento humano.

    Ideal para:
    - Cloudflare light (Managed Challenge)
    - Sitios SPA que requieren JS básico
    - WAFs que detectan headers pero no comportamiento del browser
    - Consumo medio (~150-300MB RAM)
    """

    def __init__(self, emulator: Optional[BrowserEmulator] = None, headless: bool = True):
        super().__init__(emulator)
        self.headless = headless
        self._check_deps()

    def _check_deps(self):
        self.has_playwright = check_all(["playwright.async_api"]).get("playwright.async_api", False)
        self.has_stealth = check_all(["playwright_stealth"]).get("playwright_stealth", False)

    @property
    def name(self) -> str:
        return "strong"

    async def fetch(self, url: str, **kwargs: Any) -> ExecutorResult:
        """Fetch via Playwright con stealth."""
        if not self.has_playwright:
            return ExecutorResult(
                html="",
                url=url,
                status_code=0,
                strategy="strong",
                error="playwright not installed. Install with: pip install playwright playwright-stealth",
                waf_detected=False,
            )

        start = time.time()
        profile = kwargs.get("profile") or self.emulator.get_random_profile()

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser_type = p.chromium

            launch_args = {
                "headless": self.headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    f"--window-size={profile.viewport[0]},{profile.viewport[1]}",
                ],
            }

            browser = await browser_type.launch(**launch_args)

            try:
                context = await browser.new_context(
                    viewport={"width": profile.viewport[0], "height": profile.viewport[1]},
                    user_agent=profile.user_agent,
                    locale=profile.accept_language.split(";")[0].split(",")[0] if profile.accept_language else "es-ES",
                    timezone_id=profile.timezone or "Europe/Madrid",
                    extra_http_headers=self.emulator.get_headers(profile),
                )

                page = await context.new_page()
                if self.has_stealth:
                    try:
                        from playwright_stealth import stealth_async
                        await stealth_async(page)
                    except (ImportError, AttributeError):
                        pass

                response = await page.goto(url, wait_until="domcontentloaded")

                # Comportamiento humano ligero
                await asyncio.sleep(0.5)
                await page.evaluate("window.scrollBy(0, 200)")
                await asyncio.sleep(0.3)

                html = await page.content()
                title = await page.title()
                current_url = page.url

                status = response.status if response else 0
                headers = {}
                if response:
                    raw_headers = await response.all_headers()
                    headers = {k: v for k, v in raw_headers.items()}

                # Detectar bot detection en el DOM
                bot_detected = await self._detect_bot_in_page(page)

                resp_time = (time.time() - start) * 1000

                return ExecutorResult(
                    html=html,
                    url=current_url,
                    status_code=status,
                    strategy="strong",
                    headers=headers,
                    waf_detected=bot_detected,
                    response_time_ms=resp_time,
                )

            except Exception as e:
                return ExecutorResult(
                    html="",
                    url=url,
                    status_code=0,
                    strategy="strong",
                    error=f"Playwright error: {e}",
                    waf_detected=False,
                )

            finally:
                await browser.close()

    async def _detect_bot_in_page(self, page: Any) -> bool:
        """Detecta si la página muestra señales de bot detection."""
        try:
            body_text = await page.inner_text("body")
            indicators = [
                "verify you are human",
                "access denied",
                "blocked",
                "automated requests",
                "captcha",
                "challenge",
                "please enable javascript",
            ]
            lower = body_text.lower()[:1000]
            return any(ind in lower for ind in indicators)
        except Exception:
            return False


class HeavyExecutor(BaseFetchExecutor):
    """Ejecutor HEAVY: Crawl4AI con motor headless completo + magic anti-bot.

    Ideal para:
    - Cloudflare heavy (Interactive Challenge)
    - JavaScript-heavy pages
    - Detección de tech stack dinámico
    - Screenshots y extracción profunda
    - Consumo alto (~300-600MB RAM)
    """

    def __init__(self, emulator: Optional[BrowserEmulator] = None, headless: bool = True):
        super().__init__(emulator)
        self.headless = headless
        self._check_deps()

    def _check_deps(self):
        self.has_crawl4ai = check_all(["crawl4ai"]).get("crawl4ai", False)
        self.has_playwright = check_all(["playwright.async_api"]).get("playwright.async_api", False)

    @property
    def name(self) -> str:
        return "heavy"

    async def fetch(self, url: str, **kwargs: Any) -> ExecutorResult:
        """Fetch via Crawl4AI con anti-bot integrado (magic=True)."""
        if not self.has_crawl4ai:
            # Fallback: usar StrongExecutor si disponible
            if getattr(self, "has_playwright", False):
                strong = StrongExecutor(self.emulator, headless=self.headless)
                return await strong.fetch(url, **kwargs)

            return ExecutorResult(
                html="",
                url=url,
                status_code=0,
                strategy="heavy",
                error="crawl4ai not installed. Install with: pip install crawl4ai>=0.4.0",
                waf_detected=False,
            )

        start = time.time()
        profile = kwargs.get("profile") or self.emulator.get_random_profile()

        try:
            from crawl4ai import AsyncWebCrawler
            from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

            browser_config = BrowserConfig(
                headless=self.headless,
                user_agent=profile.user_agent,
                headers=self.emulator.get_headers(profile),
                viewport={"width": profile.viewport[0], "height": profile.viewport[1]},
                text_mode=False,
                enable_stealth=True,
                extra_args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    f"--window-size={profile.viewport[0]},{profile.viewport[1]}",
                ],
            )

            # magic=True habilita bypass automático de challenges anti-bot
            run_config = CrawlerRunConfig(
                scan_full_page=True,
                page_timeout=30000,
                wait_until="domcontentloaded",
                simulate_user=True,
                magic=True,
                remove_consent_popups=True,
                ignore_body_visibility=True,
            )

            crawler = AsyncWebCrawler(config=browser_config)
            await crawler.start()

            try:
                crawl_result = await crawler.arun(
                    url=url,
                    config=run_config,
                )

                # Crawl4AI 0.8.6 retorna CrawlResult con .html
                html = getattr(crawl_result, "html", "") or ""
                status = getattr(crawl_result, "status_code", 200) or 200

                if html:
                    lower = html.lower()[:3000]
                    bot_indicators = [
                        "cloudflare",
                        "captcha",
                        "challenge",
                        "please enable javascript",
                        "automated requests",
                        "access denied",
                        "blocked",
                        "verify you are human",
                        "turnstile",
                    ]
                    bot_detected = any(ind in lower for ind in bot_indicators)
                else:
                    bot_detected = True

                resp_time = (time.time() - start) * 1000

                return ExecutorResult(
                    html=html,
                    url=getattr(crawl_result, "url", url),
                    status_code=status,
                    strategy="heavy",
                    headers=dict(getattr(crawl_result, "headers", {})) or {},
                    waf_detected=bot_detected,
                    response_time_ms=resp_time,
                )

            finally:
                await crawler.close()

        except Exception as e:
            return ExecutorResult(
                html="",
                url=url,
                status_code=0,
                strategy="heavy",
                error=f"Crawl4AI error: {e}",
                waf_detected=False,
            )