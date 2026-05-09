"""Anti-bot infrastructure - Browser emulation + TLS spoofing + WAF evasion."""

import random
import time
import re
import ssl
import socket
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse


class WAFType(Enum):
    """Tipos de WAF detectados."""
    CLOUDFLARE = "cloudflare"
    INCAPSULA = "incapsula"
    AKAMAI = "akamai"
    AWS_WAF = "aws_waf"
    SUCURI = "sucuri"
    DATA_DOME = "data_dome"
    PERIMETER_X = "perimeter_x"
    UNKNOWN = "unknown"
    NONE = "none"


@dataclass
class BrowserProfile:
    """Perfil de navegador para anti-honeypot."""
    user_agent: str
    viewport: tuple[int, int]
    accept_language: str
    platform: str
    sec_ch_ua: Optional[str] = None
    timezone: Optional[str] = None
    screen: tuple[int, int] = (1920, 1080)
    color_depth: int = 24
    device_memory: float = 8.0


@dataclass
class FetchResult:
    """Resultado de fetch anti-bot."""
    status_code: int
    headers: Dict[str, str]
    text: str
    url: str
    strategy: str
    error: Optional[str] = None
    is_bot_detected: bool = False
    waf_type: WAFType = WAFType.NONE
    response_time_ms: Optional[float] = None
    ja3_fingerprint: Optional[str] = None


@dataclass
class AntiBotConfig:
    """Configuración para el sistema anti-bot."""
    user_agents: List[str] = field(default_factory=list)
    proxies: List[str] = field(default_factory=list)
    enable_ja3: bool = True
    enable_random_delay: bool = True
    min_delay: float = 0.5
    max_delay: float = 3.0
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    enable_cookies: bool = True


class JA3Spoofer:
    """TLS fingerprint spoofing via curl_cffi.

    curl_cffi soporta JA3 fingerprints predefinidos que imitan navegadores reales,
    evitando detección por fingerprinting TLS.
    """

    PRESETS = {
        "chrome_120": "chrome120",
        "chrome_119": "chrome119",
        "chrome_118": "chrome118",
        "firefox_120": "firefox120",
        "safari_17": "safari17_0",
        "edge_120": "edge99",
    }

    def __init__(self):
        self._impersonate = self._init_curl_cffi()

    def _init_curl_cffi(self):
        """Inicializa curl_cffi si está disponible."""
        try:
            from curl_cffi import requests as curl_requests
            return curl_requests
        except ImportError:
            return None

    @property
    def is_available(self) -> bool:
        return self._impersonate is not None

    def get_session(self, ja3_preset: str = "chrome120") -> Any:
        """Obtiene una sesión curl_cffi con JA3 spoofing."""
        if not self.is_available:
            raise ImportError("curl_cffi not installed. Install with: pip install curl-cffi")

        session = self._impersonate.Session(impersonate=ja3_preset)
        return session

    def get_random_preset(self) -> str:
        return random.choice(list(self.PRESETS.values()))


@dataclass
class WAFDetection:
    """Resultado de detección de WAF."""
    detected: bool = False
    waf_type: WAFType = WAFType.NONE
    signals: List[str] = field(default_factory=list)
    suggested_strategy: str = "fast"


class WAFDetector:
    """Detector de WAFs basado en headers, body y comportamiento."""

    SIGNATURES: Dict[WAFType, List[str]] = {
        WAFType.CLOUDFLARE: [
            "cloudflare",
            "cf-ray",
            "cf-request-id",
            "__cfduid",
            "cf_bm",
            "challenge-platform",
            "turnstile",
            "cf-browser-verification",
        ],
        WAFType.INCAPSULA: [
            "incap_ses",
            "visid_incap",
            "incapsula",
            "x-iinfo",
        ],
        WAFType.AKAMAI: [
            "akamai",
            "akamai-edge",
            "x-akamai-request-id",
        ],
        WAFType.DATA_DOME: [
            "datadome",
            "dd-request-id",
        ],
        WAFType.PERIMETER_X: [
            "perimeterx",
            "_px",
        ],
        WAFType.SUCURI: [
            "sucuri",
            "x-sucuri-id",
        ],
        WAFType.AWS_WAF: [
            "awselb",
            "awselb-",
            "x-amzn-requestid",
        ],
    }

    def detect(self, status_code: int, headers: Dict[str, str], body: str = "") -> WAFDetection:
        """Detecta presencia de WAF en la respuesta."""
        result = WAFDetection()

        headers_lower = {k.lower(): str(v).lower() for k, v in headers.items()}
        body_lower = body.lower()

        # Check each WAF signature
        for waf_type, signatures in self.SIGNATURES.items():
            signals_found = []
            for sig in signatures:
                if sig in headers_lower or sig in body_lower:
                    signals_found.append(sig)

            if signals_found:
                result.detected = True
                result.waf_type = waf_type
                result.signals.extend(signals_found)

        # Determine suggested strategy based on WAF type
        if result.detected:
            if result.waf_type in (WAFType.CLOUDFLARE, WAFType.INCAPSULA, WAFType.AKAMAI):
                result.suggested_strategy = "strong"
            else:
                result.suggested_strategy = "heavy"

        return result

    def is_blocking_response(self, status_code: int, body: str = "") -> bool:
        """Determina si la respuesta indica bloqueo por bot detection."""
        if status_code in (403, 429, 503, 520, 521, 522, 523):
            return True

        blocking_indicators = [
            "access denied",
            "blocked",
            "captcha",
            "challenge",
            "please enable javascript",
            "enable javascript",
            "automated requests",
            "bot detected",
            "suspicious activity",
            "verification required",
        ]

        body_lower = body.lower()
        return any(ind in body_lower for ind in blocking_indicators)


class BrowserEmulator:
    """Emulador de navegador con rotación de perfiles y evasión avanzada."""

    PROFILES = [
        BrowserProfile(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport=(1920, 1080),
            accept_language="es-ES,es;q=0.9,en;q=0.8",
            platform="Windows",
            sec_ch_ua='"Chromium";v="124", "Google Chrome";v="124"',
            timezone="Europe/Madrid",
        ),
        BrowserProfile(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport=(1680, 1050),
            accept_language="es-MX,es;q=0.9,en;q=0.8",
            platform="macOS",
            sec_ch_ua='"Chromium";v="124", "Google Chrome";v="124"',
            timezone="America/Mexico_City",
            screen=(1680, 1050),
        ),
        BrowserProfile(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            viewport=(1366, 768),
            accept_language="en-US,en;q=0.9,es;q=0.8",
            platform="Linux",
            sec_ch_ua='"Chromium";v="123", "Google Chrome";v="123"',
            timezone="UTC",
            device_memory=4.0,
        ),
        BrowserProfile(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
                "Gecko/20100101 Firefox/125.0"
            ),
            viewport=(1920, 1080),
            accept_language="es-ES,es;q=0.9",
            platform="Windows",
            timezone="Europe/Madrid",
        ),
        BrowserProfile(
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.4 Mobile/15E148 Safari/604.1"
            ),
            viewport=(390, 844),
            accept_language="es-MX,es;q=0.9,en;q=0.8",
            platform="iOS",
            sec_ch_ua='"Safari";v="17.4"',
            timezone="America/Mexico_City",
            screen=(390, 844),
            device_memory=6.0,
        ),
        BrowserProfile(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
            ),
            viewport=(1920, 1080),
            accept_language="en-US,en;q=0.9,es;q=0.8",
            platform="Windows",
            sec_ch_ua='"Chromium";v="125", "Microsoft Edge";v="125"',
            timezone="America/New_York",
            screen=(1920, 1080),
            device_memory=16.0,
        ),
    ]

    def __init__(self, config: Optional[AntiBotConfig] = None):
        self.config = config or AntiBotConfig()
        self._waf_detector = WAFDetector()
        self._ja3 = JA3Spoofer()
        self._cookie_jar: Dict[str, Dict[str, str]] = {}

    def get_random_profile(self) -> BrowserProfile:
        return random.choice(self.PROFILES)

    def get_profile_by_hash(self, seed: str) -> BrowserProfile:
        """Obtiene perfil determinístico basado en semilla."""
        idx = hash(seed) % len(self.PROFILES)
        return self.PROFILES[idx]

    def get_headers(self, profile: Optional[BrowserProfile] = None) -> Dict[str, str]:
        headers = {
            "User-Agent": profile.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": profile.accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        if profile.sec_ch_ua:
            headers["sec-ch-ua"] = profile.sec_ch_ua
            headers["sec-ch-ua-mobile"] = "?1" if "Mobile" in profile.user_agent else "?0"
            headers["sec-ch-ua-platform"] = f'"{profile.platform}"'
        return headers

    def get_viewports(self) -> List[tuple[int, int]]:
        return [p.viewport for p in self.PROFILES]

    def get_ja3_preset(self, profile: Optional[BrowserProfile] = None) -> str:
        """Mapea perfil a JA3 preset apropiado."""
        p = profile or self.get_random_profile()
        ua_lower = p.user_agent.lower()
        if "edg" in ua_lower:
            return "edge99"
        elif "firefox" in ua_lower:
            return "firefox120"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            return "safari17_0"
        return random.choice(["chrome120", "chrome119", "chrome118"])


class RateLimiter:
    """Rate limiter con jitter exponencial."""

    def __init__(self, base_delay: float = 1.5, max_delay: float = 30.0, jitter: float = 0.5):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.attempt = 0

    def wait(self) -> None:
        delay = min(self.base_delay * (2 ** self.attempt), self.max_delay)
        delay += random.uniform(0, self.jitter)
        time.sleep(delay)
        self.attempt += 1

    def reset(self) -> None:
        self.attempt = 0

    @property
    def current_delay(self) -> float:
        return min(self.base_delay * (2 ** self.attempt), self.max_delay)


class SmartRetry:
    """Retry inteligente que decide estrategia según tipo de error."""

    RETRYABLE_STATUS_CODES = {429, 502, 503, 504, 520, 521, 522, 523}
    BOT_DETECTION_CODES = {403}

    def __init__(self, max_attempts: int = 3, base_delay: float = 2.0, max_delay: float = 30.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._rate_limiter = RateLimiter(base_delay=base_delay, max_delay=max_delay)

    def should_retry(self, status_code: int, body: str = "", waf_detected: bool = False) -> tuple[bool, str]:
        """Determina si debe reintentar y con qué estrategia.

        Returns:
            (should_retry, recommended_strategy_change)
        """
        if waf_detected:
            return True, "escalate"

        if status_code in self.RETRYABLE_STATUS_CODES:
            if status_code == 429:
                return True, "slow_down"
            return True, "same"

        if status_code in self.BOT_DETECTION_CODES:
            body_lower = body.lower()[:500]
            if any(kw in body_lower for kw in ["captcha", "challenge", "bot", "automated", "cloudflare"]):
                return True, "escalate"

        return False, "none"

    def wait(self, attempt: int) -> None:
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        delay += random.uniform(0, 1.0)
        time.sleep(delay)