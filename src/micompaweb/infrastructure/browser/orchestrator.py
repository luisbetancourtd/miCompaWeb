"""Fetch orchestrator - decisión automática de ruta según dominio."""

import hashlib
import urllib.parse
from typing import Optional
from enum import Enum
from dataclasses import dataclass

from micompaweb.infrastructure.browser.anti_bot import (
    BrowserEmulator,
    RateLimiter,
    FetchResult,
)


class Strategy(Enum):
    FAST = "fast"     # requests + headers rotados
    STRONG = "strong" # playwright stealth (JS, cloudflare light)
    HEAVY = "heavy"   # crawler con motor headless pesado


@dataclass
class DomainSignal:
    """Señales de dureza del dominio."""
    requires_js: bool = False
    known_bot_defense: bool = False
    uses_cdn: bool = False
    rate_limited: bool = False


class FetchOrchestrator:
    """Orquesta las 3 rutas según el tipo de dominio."""

    # Dominios conocidos como difíciles (requieren STRONG/HEAVY)
    HARD_DOMAINS = {
        "instagram.com", "facebook.com", "linkedin.com", "twitter.com",
        "x.com", "reddit.com", "amazon.com",
    }

    # CDN/Proxy detectables
    CDN_INDICATORS = ["cloudflare", "akamai", "fastly", "incapsula"]

    def __init__(self, emulator: Optional[BrowserEmulator] = None):
        self.emulator = emulator or BrowserEmulator()
        self.rate_limiter = RateLimiter(base_delay=1.0)

    def classify_domain(self, url: str) -> Strategy:
        """Clasifica la URL en una de las 3 estrategias."""
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        # Estrategia HEAVY para known hard
        if any(hd in domain for hd in self.HARD_DOMAINS):
            return Strategy.HEAVY

        # Estrategía STRONG para subdominios con CDN conocido o path con login
        path = parsed.path.lower()
        if any(ind in domain for ind in self.CDN_INDICATORS) or "/login" in path or "/auth" in path:
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
        }
