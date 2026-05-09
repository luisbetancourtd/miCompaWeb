"""Lead source manager - orquesta múltiples fuentes con fallback."""

from typing import List, Optional
from dataclasses import dataclass

from micompaweb.domain.models import Lead
from micompaweb.application.ports import LeadSource, Cache, LeadSourceError, NoSourceAvailable
from micompaweb.application.ports.lead_source import CostEstimate
from micompaweb.infrastructure.cost_guardian import CostGuardian


@dataclass
class SourceWithPriority:
    """Fuente con prioridad para fallback chain."""
    source: LeadSource
    priority: int
    max_cost_usd: float = float("inf")


class LeadSourceManager:
    """Gestiona múltiples fuentes de leads con fallback automático.

    Implementa el patrón Chain of Responsibility:
    1. Intenta fuente 1, si falla o supera costo → fuente 2
    2. Continúa hasta encontrar una fuente disponible
    3. Si ninguna funciona, lanza NoSourceAvailable

    Usage:
        manager = LeadSourceManager()
        manager.add_source(CachedSource(GooglePlacesSource(api_key), cache), priority=1)
        manager.add_source(FixtureSource(), priority=99)  # Fallback último

        leads = await manager.search(niche="plomeros", location="CDMX")
    """

    def __init__(
        self,
        max_cost_per_operation: float = 2.00,
        cost_guardian: Optional[CostGuardian] = None,
    ):
        """Inicializa manager.

        Args:
            max_cost_per_operation: Costo máximo permitido por búsqueda
            cost_guardian: Guardian de costos diario con persistencia SQLite
        """
        self._sources: List[SourceWithPriority] = []
        self.max_cost_per_operation = max_cost_per_operation
        self._cost_tracker: dict[str, float] = {}
        self.cost_guardian = cost_guardian

    def add_source(
        self,
        source: LeadSource,
        priority: int = 50,
        max_cost_usd: Optional[float] = None,
    ) -> None:
        """Agrega una fuente al chain.

        Args:
            source: Implementación de LeadSource
            priority: Menor número = mayor prioridad (1 = primero)
            max_cost_usd: Costo máximo para usar esta fuente
        """
        self._sources.append(SourceWithPriority(
            source=source,
            priority=priority,
            max_cost_usd=max_cost_usd or float("inf"),
        ))
        # Reordenar por prioridad
        self._sources.sort(key=lambda x: x.priority)

    async def search(
        self,
        niche: str,
        location: str,
        radius_meters: int = 10000,
        max_results: int = 100,
        language: str = "es",
        max_cost: Optional[float] = None,
    ) -> List[Lead]:
        """Busca leads intentando fuentes en orden.

        Args:
            niche: Tipo de negocio
            location: Ubicación
            radius_meters: Radio de búsqueda
            max_results: Máximo de resultados
            language: Idioma
            max_cost: Costo máximo (sobrescribe default)

        Returns:
            Lista de leads

        Raises:
            NoSourceAvailable: Si ninguna fuente funciona
        """
        cost_limit = max_cost or self.max_cost_per_operation
        errors: List[str] = []

        for source_with_priority in self._sources:
            source = source_with_priority.source

            # Verificar health
            health = source.health_check()
            if not health.is_healthy:
                errors.append(f"{source.source_name}: {health.message}")
                continue

            # Verificar costo
            cost_estimate = source.estimate_cost(max_results)
            if cost_estimate.usd_amount > min(cost_limit, source_with_priority.max_cost_usd):
                errors.append(
                    f"{source.source_name}: Cost ${cost_estimate.usd_amount} > limit"
                )
                continue

            # Verificar presupuesto diario si hay CostGuardian
            if self.cost_guardian and not self.cost_guardian.can_proceed(
                source.source_name, cost_estimate.requests_count
            ):
                errors.append(
                    f"{source.source_name}: Daily budget exceeded"
                )
                continue

            try:
                leads = await source.search(
                    niche=niche,
                    location=location,
                    radius_meters=radius_meters,
                    max_results=max_results,
                    language=language,
                )

                if leads:
                    # Registrar costo usado
                    self._track_cost(source.source_name, cost_estimate.usd_amount)
                    if self.cost_guardian:
                        self.cost_guardian.charge(
                            source.source_name, cost_estimate.requests_count
                        )
                    return leads

            except LeadSourceError as e:
                errors.append(f"{source.source_name}: {e}")
                continue

        # Ninguna fuente funcionó
        raise NoSourceAvailable(
            f"No source available for {niche} in {location}. "
            f"Errors: {'; '.join(errors)}"
        )

    def get_available_sources(self) -> List[dict]:
        """Lista fuentes disponibles con su estado."""
        result = []
        for sp in self._sources:
            health = sp.source.health_check()
            cost = sp.source.estimate_cost(100)
            result.append({
                "name": sp.source.source_name,
                "priority": sp.priority,
                "healthy": health.is_healthy,
                "message": health.message,
                "cost_per_100": cost.usd_amount,
            })
        return result

    def get_cost_summary(self) -> dict:
        """Resumen de costos acumulados."""
        total = sum(self._cost_tracker.values())
        return {
            "total_usd": total,
            "by_source": self._cost_tracker.copy(),
        }

    def _track_cost(self, source_name: str, amount: float) -> None:
        """Registra costo usado."""
        self._cost_tracker[source_name] = self._cost_tracker.get(source_name, 0) + amount