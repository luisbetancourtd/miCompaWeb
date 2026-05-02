"""Anti-bot infrastructure - Browser emulation with rotation."""

import random
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class BrowserProfile:
    """Perfil de navegador para anti-honeypot."""
    user_agent: str
    viewport: tuple[int, int]
    accept_language: str
    platform: str
    sec_ch_ua: str
    timezone: Optional[str] = None

class BrowserEmulator:
    """Emulador de navegador con rotación de perfiles."""

    PROFILES = [
        BrowserProfile(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport=(1920, 1080),
            accept_language="es-ES,es;q=0.9",
            platform="Windows",
            sec_ch_ua='"Chromium";v="124", "Google Chrome";v="124"',
        ),
        BrowserProfile(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport=(1680, 1050),
            accept_language="es-MX,es;q=0.9,en;q=0.8",
            platform="macOS",
            sec_ch_ua='"Chromium";v="124", "Google Chrome";v="124"',
        ),
        BrowserProfile(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport=(1366, 768),
            accept_language="en-US,en;q=0.9",
            platform="Linux",
            sec_ch_ua='"Chromium";v="123", "Google Chrome";v="123"',
        ),
        BrowserProfile(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            viewport=(1920, 1080),
            accept_language="es-ES,es;q=0.9",
            platform="Windows",
            sec_ch_ua=None,
        ),
        BrowserProfile(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            viewport=(390, 844),
            accept_language="es-MX,es;q=0.9",
            platform="iOS",
            sec_ch_ua='"Safari";v="17.4"',
        ),
    ]

    def get_random_profile(self) -> BrowserProfile:
        return random.choice(self.PROFILES)

    def get_headers(self, profile: Optional[BrowserProfile] = None) -> Dict[str, str]:
        """Headers HTTP que matchean el perfil seleccionado."""
        p = profile or self.get_random_profile()
        headers = {
            "User-Agent": p.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": p.accept_language,
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
        if p.sec_ch_ua:
            headers["sec-ch-ua"] = p.sec_ch_ua
            headers["sec-ch-ua-mobile"] = "?1" if "Mobile" in p.user_agent else "?0"
            headers["sec-ch-ua-platform"] = f'"{p.platform}"'
        return headers

class RateLimiter:
    """Rate limiter con jitter exponencial."""

    def __init__(self, base_delay: float = 1.5, max_delay: float = 30.0, jitter: float = 0.5):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.attempt = 0

    def wait(self) -> None:
        """Espera con backoff exponencial + jitter."""
        delay = min(self.base_delay * (2 ** self.attempt), self.max_delay)
        delay += random.uniform(0, self.jitter)
        time.sleep(delay)
        self.attempt += 1

    def reset(self) -> None:
        self.attempt = 0

    @property
    def current_delay(self) -> float:
        return min(self.base_delay * (2 ** self.attempt), self.max_delay)

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
