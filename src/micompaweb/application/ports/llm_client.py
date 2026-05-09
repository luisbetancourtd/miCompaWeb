"""LLM client protocol - contrato para proveedores de LLM."""

from typing import Protocol, Optional
from dataclasses import dataclass
from enum import Enum


class LLMError(Exception):
    """Error al interactuar con LLM."""
    pass


class LLMProvider(str, Enum):
    """Proveedores de LLM soportados."""
    GROQ = "groq"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    HEURISTIC = "heuristic"


@dataclass
class VigencyResult:
    """Resultado de análisis de vigencia de contenido."""
    is_outdated: Optional[bool]
    confidence: float  # 0.0 - 1.0
    reason: str
    snippet: str
    evidence: list[str]
    provider_used: LLMProvider
    cost_usd: Optional[float] = None


@dataclass
class LLMConfig:
    """Configuración para LLM."""
    provider: LLMProvider
    model: str
    temperature: float = 0.1
    max_tokens: int = 500
    timeout_seconds: int = 30


class LLMClient(Protocol):
    """Contrato para clientes LLM.

    Permite chain de fallback:
    1. Groq (rápido, económico)
    2. Ollama (local, gratuito)
    3. Heurístico (siempre disponible)
    """

    async def analyze_vigency(
        self,
        content: str,
        website_url: str,
        copyright_year: Optional[int] = None,
    ) -> VigencyResult:
        """Analiza si el contenido está desactualizado.

        Args:
            content: Texto extraído del website
            website_url: URL del sitio
            copyright_year: Año de copyright si se detectó

        Returns:
            Análisis de vigencia con confianza
        """
        ...

    async def generate_opening_angle(
        self,
        lead_name: str,
        niche: str,
        pain_points: list[str],
    ) -> str:
        """Genera ángulo de apertura para outreach.

        Args:
            lead_name: Nombre del negocio
            niche: Nicho del negocio
            pain_points: Lista de pain points detectados

        Returns:
            Texto de apertura personalizado
        """
        ...

    def is_available(self) -> bool:
        """Verifica si el proveedor está disponible."""
        ...

    @property
    def provider_name(self) -> str:
        """Nombre del proveedor."""
        ...

    @property
    def is_local(self) -> bool:
        """Si es un modelo local (sin costo API)."""
        ...

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estima costo en USD."""
        ...