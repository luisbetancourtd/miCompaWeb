"""M2 anti-bot fetcher - TLS fingerprint spoofing via curl_cffi."""

from typing import Optional, Dict
from dataclasses import dataclass


def _has_curl_cffi() -> bool:
    try:
        import curl_cffi
        return True
    except ImportError:
        return False


@dataclass
class TLSFetchResult:
    url: str
    status_code: int
    text: str
    headers: Dict[str, str]
    success: bool
    error: Optional[str] = None
    tls_fingerprint: Optional[str] = None


class TLSFetcher:
    """Fetcher con TLS fingerprint spoofing (curl_cffi)."""

    BROWSER_PROFILES = [
        "chrome110", "chrome116", "chrome119", "chrome120",
        "safari15_5", "safari17_0",
        "firefox110", "firefox120",
    ]

    def __init__(self):
        self._available = _has_curl_cffi()
        self._session = None
        if self._available:
            from curl_cffi import requests as curl_requests
            self._session = curl_requests.Session()

    @property
    def is_available(self) -> bool:
        return self._available

    def fetch(
        self,
        url: str,
        browser: Optional[str] = None,
        timeout: int = 30,
        impersonate: bool = True,
    ) -> TLSFetchResult:
        """Fetch con TLS spoofing."""
        if not self._available:
            return TLSFetchResult(
                url=url, status_code=0, text="", headers={},
                success=False, error="curl_cffi no instalado",
            )

        browser = browser or self.BROWSER_PROFILES[0]

        try:
            import curl_cffi
            if impersonate:
                resp = self._session.get(url, timeout=timeout, impersonate=browser)
            else:
                resp = self._session.get(url, timeout=timeout)

            return TLSFetchResult(
                url=url,
                status_code=resp.status_code,
                text=resp.text,
                headers=dict(resp.headers),
                success=200 <= resp.status_code < 400,
                tls_fingerprint=browser,
            )
        except Exception as e:
            return TLSFetchResult(
                url=url, status_code=0, text="", headers={},
                success=False, error=str(e),
            )

    def fetch_with_fallback(
        self,
        url: str,
        browsers: Optional[list] = None,
        timeout: int = 30,
    ) -> TLSFetchResult:
        """Prueba múltiples perfiles TLS hasta que uno funcione."""
        browsers = browsers or self.BROWSER_PROFILES
        for browser in browsers:
            result = self.fetch(url, browser=browser, timeout=timeout)
            if result.success:
                return result
        # Último intento sin impersonate
        return self.fetch(url, impersonate=False, timeout=timeout)
