"""Cached lead source wrapper - añade persistencia a cualquier fuente."""

from typing import List, Optional

from micompaweb.domain.models import Lead
from micompaweb.application.ports import LeadSource, Cache
from micompaweb.application.ports.lead_source import SourceHealth, CostEstimate


class CachedSource:
    """Wrapper que añade caché a una fuente de leads.

    Decorator pattern: envuelve cualquier LeadSource y agrega
    persistencia transparente vía el protocolo Cache.

    Usage:
        source = CachedSource(
            underlying=GooglePlacesSource(api_key),
            cache=SQLiteCache(db_path)
        )
    """

    def __init__(
        self,
        underlying: LeadSource,
        cache: Cache,
        ttl_seconds: int = 86400 * 30,  # 30 días por defecto
    ):
        self.underlying = underlying
        self.cache = cache
        self.ttl_seconds = ttl_seconds

    async def search(
        self,
        niche: str,
        location: str,
        radius_meters: int = 10000,
        max_results: int = 100,
        language: str = "es",
    ) -> List[Lead]:
        """Busca con caché transparente.

        1. Verifica caché primero
        2. Si no existe, delega a underlying
        3. Guarda resultado en caché
        """
        cache_key = self.cache.make_key(
            "search",
            self.underlying.source_name,
            niche,
            location,
            str(radius_meters),
            str(max_results),
            language,
        )

        # 1. Intentar caché
        cached = await self.cache.get(cache_key)
        if cached is not None:
            # Marcar como provenientes de caché
            for lead in cached:
                lead.source = f"{lead.source}(cached)"
            return cached

        # 2. Delegar a fuente subyacente
        leads = await self.underlying.search(
            niche=niche,
            location=location,
            radius_meters=radius_meters,
            max_results=max_results,
            language=language,
        )

        # 3. Guardar en caché
        if leads:
            await self.cache.set(cache_key, leads, ttl_seconds=self.ttl_seconds)

        return leads

    async def get_details(self, external_id: str, language: str = "es") -> Optional[Lead]:
        """Obtiene detalles con caché."""
        cache_key = self.cache.make_key(
            "details",
            self.underlying.source_name,
            external_id,
            language,
        )

        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        lead = await self.underlying.get_details(external_id, language)
        if lead:
            await self.cache.set(cache_key, lead, ttl_seconds=self.ttl_seconds)

        return lead

    def health_check(self) -> SourceHealth:
        """Estado combina underlying + caché."""
        underlying_health = self.underlying.health_check()

        if underlying_health.is_healthy:
            return SourceHealth(
                is_healthy=True,
                message=f"{self.underlying.source_name} healthy, cache enabled",
            )

        # Si underlying está caído pero caché funciona, podemos operar offline
        return SourceHealth(
            is_healthy=True,  # Aún funcional vía caché
            message=f"{self.underlying.source_name} unhealthy, using cache",
        )

    def estimate_cost(self, num_results: int) -> CostEstimate:
        """Costo de underlying (caché es gratuito)."""
        return self.underlying.estimate_cost(num_results)

    @property
    def source_name(self) -> str:
        return f"cached_{self.underlying.source_name}"

    @property
    def supports_caching(self) -> bool:
        return True