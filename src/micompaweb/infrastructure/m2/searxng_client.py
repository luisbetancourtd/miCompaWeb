"""M2 search aggregation - SearXNG client para SERP."""

import urllib.parse
from typing import List, Optional, Dict
from dataclasses import dataclass


@dataclass
class SERPResult:
    title: str
    url: str
    snippet: str
    engine: str
    position: int


class SearXNGClient:
    """Cliente SearXNG para búsquedas SERP locales."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")
        self._available = self._check_available()

    def _check_available(self) -> bool:
        try:
            import httpx
            r = httpx.get(f"{self.base_url}/", timeout=5)
            return r.status_code < 400
        except Exception:
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    def search(
        self,
        query: str,
        language: str = "es",
        limit: int = 10,
        categories: Optional[List[str]] = None,
    ) -> List[SERPResult]:
        """Búsqueda SERP vía SearXNG."""
        if not self._available:
            return []

        try:
            import httpx
            params = {
                "q": query,
                "language": language,
                "format": "json",
            }
            if categories:
                params["categories"] = ",".join(categories)

            r = httpx.get(f"{self.base_url}/search", params=params, timeout=30)
            data = r.json()

            results = []
            for i, item in enumerate(data.get("results", [])[:limit]):
                results.append(SERPResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    engine=item.get("engine", "searxng"),
                    position=i + 1,
                ))
            return results
        except Exception:
            return []

    def search_local_businesses(
        self,
        niche: str,
        location: str,
        limit: int = 20,
    ) -> List[SERPResult]:
        """Búsqueda especializada de negocios locales."""
        query = f"{niche} en {location}"
        return self.search(query, language="es", limit=limit, categories=["general"])
