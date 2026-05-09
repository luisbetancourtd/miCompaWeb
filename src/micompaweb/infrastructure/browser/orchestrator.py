"""Fetch orchestrator - decisión automática de ruta según dominio con ejecutores reales."""

import hashlib
import urllib.parse
from typing import Optional
from enum import Enum
from dataclasses import dataclass

from micompaweb.infrastructure.browser.anti_bot import (
    BrowserEmulator,
    RateLimiter,
    FetchResult,
    SmartRetry,
    WAFDetector,
)
from micompaweb.infrastructure.browser.executors import (
    FastExecutor,
    StrongExecutor,
    HeavyExecutor,
    ExecutorResult,
)


class Strategy(Enum):
    """Las 3 estrategias de fetching anti-bot."""
    FAST = "fast"     # curl_cffi + JA3 (básico, rápido)
    STRONG = "strong" # Playwright stealth (JS + human-like)
    HEAVY = "heavy"   # Crawl4AI (motor completo + deep extraction)


@dataclass
class DomainSignal:
    """Señales de dureza del dominio."""
    requires_js: bool = False
    known_bot_defense: bool = False
    uses_cdn: bool = False
    rate_limited: bool = False


class FetchOrchestrator:
    """Orquesta las 3 rutas según el tipo de dominio con ejecutores reales.

    Usage (low-level):
        orch = FetchOrchestrator()
        result = await orch.fetch("https://example.com")

    Usage (with auto-escalation):
        result = await orch.fetch_smart("https://example.com")
    """

    # Dominios conocidos como difíciles (requieren STRONG/HEAVY)
    HARD_DOMAINS = {
        "instagram.com", "facebook.com", "linkedin.com", "twitter.com",
        "x.com", "reddit.com", "amazon.com", "shopify.com",
        "woocommerce.com", "bigcommerce.com",
    }

    # CDN/Proxy detectables
    CDN_INDICATORS = ["cloudflare", "akamai", "fastly", "incapsula"]

    # WAFs que habitualmente requieren STRONG
    STRONG_WAF_DOMAINS = ["cloudflare", "akamai", "fastly"]

    def __init__(self, emulator: Optional[BrowserEmulator] = None, auto_retry: bool = True):
        self.emulator = emulator or BrowserEmulator()
        self.rate_limiter = RateLimiter(base_delay=1.0)
        self.smart_retry = SmartRetry(max_attempts=3)
        self.waf_detector = WAFDetector()
        self.auto_retry = auto_retry

        # Inicializar ejecutores (lazy)
        self._fast: Optional[FastExecutor] = None
        self._strong: Optional[StrongExecutor] = None
        self._heavy: Optional[HeavyExecutor] = None

    @property
    def fast_executor(self) -> FastExecutor:
        if self._fast is None:
            self._fast = FastExecutor(self.emulator)
        return self._fast

    @property
    def strong_executor(self) -> StrongExecutor:
        if self._strong is None:
            self._strong = StrongExecutor(self.emulator)
        return self._strong

    @property
    def heavy_executor(self) -> HeavyExecutor:
        if self._heavy is None:
            self._heavy = HeavyExecutor(self.emulator)
        return self._heavy

    def classify_domain(self, url: str) -> Strategy:
        """Clasifica la URL en una de las 3 estrategias."""
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        # HEAVY para known hard domains
        if any(hd in domain for hd in self.HARD_DOMAINS):
            return Strategy.HEAVY

        # STRONG para subdominios con CDN conocido o paths protegidos
        path = parsed.path.lower()
        if any(ind in domain for ind in self.CDN_INDICATORS):
            return Strategy.STRONG
        if "/login" in path or "/auth" in path or "/checkout" in path:
            return Strategy.STRONG

        # Todo lo demás = FAST
        return Strategy.FAST

    def analyze_response(self, status: int, headers: dict, body_prefix: str = "") -> DomainSignal:
        """Analiza respuesta HTTP para detectar defensas."""
        sig = DomainSignal()

        if status in (403, 429, 503):
            sig.rate_limited = True
        if status == 403 and "cloudflare" in body_prefix.lower():
            sig.known_bot_defense = True

        header_server = headers.get("Server", "").lower()
        if any(ind in header_server for ind in self.CDN_INDICATORS):
            sig.uses_cdn = True

        # Detect body hints
        body_hints = ["enable javascript", "captcha", "cf-browser-verification", "challenge"]
        if any(h in body_prefix.lower() for h in body_hints):
            sig.requires_js = True
            sig.known_bot_defense = True

        return sig

    def adapt_strategy(self, url: str, signal: DomainSignal) -> Strategy:
        """Adapta estrategia basada en señales post-request."""
        strategy = self.classify_domain(url)

        if signal.known_bot_defense or signal.requires_js:
            if strategy == Strategy.FAST:
                return Strategy.STRONG
            elif strategy == Strategy.STRONG:
                return Strategy.HEAVY

        if signal.rate_limited:
            # Rate limit = aumentar delay, pero mantener estrategía
            self.rate_limiter.wait()

        return strategy

    def get_request_config(self, strategy: Strategy, profile_seed: Optional[str] = None) -> dict:
        """Genera config para la ruta seleccionada."""
        if strategy == Strategy.HEAVY:
            # Semilla determinística para el mismo URL
            seed = profile_seed or "default"
            idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(self.emulator.PROFILES)
            profile = self.emulator.PROFILES[idx]
        else:
            profile = self.emulator.get_random_profile()

        return {
            "headers": self.emulator.get_headers(profile),
            "viewport": profile.viewport,
            "delay": self.rate_limiter.current_delay,
            "strategy": strategy.value,
            "profile": profile,
        }

    # ----------------------------------------------------------------- #
    # FETCH principal - con rutas reales
    # ----------------------------------------------------------------- #

    async def fetch(self, url: str, strategy: Optional[Strategy] = None) -> FetchResult:
        """Fetch con una estrategia específicos o la determinada por clasificación."""
        chosen = strategy or self.classify_domain(url)

        config = self.get_request_config(chosen)
        profile = config["profile"]

        if chosen == Strategy.FAST:
            result = await self.fast_executor.fetch(url, profile=profile)
        elif chosen == Strategy.STRONG:
            result = await self.strong_executor.fetch(url, profile=profile)
        else:
            result = await self.heavy_executor.fetch(url, profile=profile)

        # Actualizar rate limiter con delay
        if self.rate_limiter.current_delay > 0:
            import time
            time.sleep(config.get("delay", 0.5))

        return self._build_fetch_result(result)

    async def fetch_smart(self, url: str, max_attempts: int = 3) -> FetchResult:
        """Fetch con auto-escalación de estrategia si se detecta bot blocking.

        Intenta FAST → STRONG → HEAVY automáticamente.
        """
        current_strategy = self.classify_domain(url)
        last_result: Optional[FetchResult] = None

        for attempt in range(max_attempts):
            config = self.get_request_config(current_strategy)
            profile = config["profile"]

            if current_strategy == Strategy.FAST:
                exec_result = await self.fast_executor.fetch(url, profile=profile)
            elif current_strategy == Strategy.STRONG:
                exec_result = await self.strong_executor.fetch(url, profile=profile)
            else:
                exec_result = await self.heavy_executor.fetch(url, profile=profile)

            fetch_result = self._build_fetch_result(exec_result)
            last_result = fetch_result

            # Si tuvo éxito, retornar
            if not exec_result.error and not exec_result.waf_detected and exec_result.status_code in range(200, 400):
                return fetch_result

            # Detectar si necesitamos escalar
            sig = self.analyze_response(
                exec_result.status_code,
                exec_result.headers,
                exec_result.html[:1500],
            )

            should_retry, action = self.smart_retry.should_retry(
                exec_result.status_code,
                exec_result.html,
                exec_result.waf_detected,
            )

            if not should_retry or attempt == max_attempts - 1:
                break

            if action == "escalate":
                if current_strategy == Strategy.FAST:
                    current_strategy = Strategy.STRONG
                elif current_strategy == Strategy.STRONG:
                    current_strategy = Strategy.HEAVY
            elif action == "slow_down":
                self.rate_limiter.wait()

        return last_result or FetchResult(
            status_code=0,
            headers={},
            text="",
            url=url,
            strategy="failed",
            error="All strategies failed",
            is_bot_detected=True,
        )

    # ----------------------------------------------------------------- #
    # Helpers
    # ----------------------------------------------------------------- #

    def _build_fetch_result(self, executor_result: ExecutorResult) -> FetchResult:
        return FetchResult(
            status_code=executor_result.status_code,
            headers=executor_result.headers,
            text=executor_result.html,
            url=executor_result.url,
            strategy=executor_result.strategy,
            error=executor_result.error,
            is_bot_detected=executor_result.waf_detected,
            response_time_ms=executor_result.response_time_ms,
        )