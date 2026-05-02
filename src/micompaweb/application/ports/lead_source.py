"""Lead source protocol - contrato para cualquier fuente de leads."""

from typing import Protocol, List, Optional, Tuple
from dataclasses import dataclass

from micompaweb.domain.models import Lead


class LeadSourceError(Exception):
    """Error al obtener leads de la fuente."""
    pass


class NoSourceAvailable(Exception):
    """Ninguna fuente de leads está disponible."""
    pass


@dataclass
class SourceHealth:
    """Estado de salud de una fuente."""
    is_healthy: bool
    message: str
    latency_ms: Optional[float] = None


@dataclass
class CostEstimate:
    """Estimación de costo para una operación."""
    usd_amount: float
    requests_count: int
    source_name: str


class LeadSource(Protocol):
    """Contrato para cualquier fuente de leads (Google Places, Outscraper, Local, etc.).

    Este protocolo permite:
    - Swap de proveedores sin cambiar código de negocio
    - Testing con mocks
    - Caché transparente
    - Fallback entre múltiples fuentes
    """

    async def search(
        self,
        niche: str,
        location: str,
        radius_meters: int = 10000,
        max_results: int = 100,
        language: str = "es",
    ) -> List[Lead]:
        """Busca negocios y retorna leads normalizados.

        Args:
            niche: Tipo de negocio (ej: "plomeros")
            location: Ubicación (ej: "Ciudad de México")
            radius_meters: Radio de búsqueda en metros
            max_results: Máximo de resultados
            language: Código de idioma (es/en/fr)

        Returns:
            Lista de leads normalizados

        Raises:
            LeadSourceError: Si la búsqueda falla
        """
        ...

    async def get_details(self, external_id: str, language: str = "es") -> Optional[Lead]:
        """Obtiene detalles completos de un negocio por su ID externo.

        Args:
            external_id: ID en la fuente externa (ej: place_id de Google)
            language: Código de idioma

        Returns:
            Lead completo o None si no existe
        """
        ...

    def health_check(self) -> SourceHealth:
        """Verifica si la fuente está disponible.

        Returns:
            Estado de salud de la fuente
        """
        ...

    def estimate_cost(self, num_results: int) -> CostEstimate:
        """Estima el costo de una operación.

        Args:
            num_results: Número esperado de resultados

        Returns:
            Estimación de costo
        """
        ...

    @property
    def source_name(self) -> str:
        """Nombre identificador de la fuente."""
        ...

    @property
    def supports_caching(self) -> bool:
        """Si la fuente soporta caché (persistencia local)."""
        ...