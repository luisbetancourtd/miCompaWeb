"""LLM Chain - orquesta múltiples proveedores con fallback."""

from typing import List, Optional, Type

from micompaweb.application.ports.llm_client import (
    LLMClient,
    LLMError,
    VigencyResult,
)
from micompaweb.infrastructure.config.settings import Settings


class LLMChain:
    """Cadena de fallback para LLM.

    Intenta proveedores en orden hasta que uno funcione:
    1. Groq (rápido, económico)
    2. Ollama (local, gratuito)
    3. Heuristic (siempre disponible)

    Usage:
        chain = LLMChain.from_settings(settings)
        result = await chain.analyze_vigency(content, url, copyright_year)
    """

    def __init__(self, providers: List[LLMClient]):
        """Inicializa chain con lista de proveedores."""
        self.providers = providers

    @classmethod
    def from_settings(cls, settings: Settings) -> "LLMChain":
        """Crea chain desde configuración."""
        providers: List[LLMClient] = []

        # 1. Groq (si está configurado)
        if settings.groq_api_key:
            from .groq_client import GroqClient
            providers.append(GroqClient(settings.groq_api_key))

        # 2. Ollama (si está disponible)
        from .ollama_client import OllamaClient
        ollama = OllamaClient(settings.ollama_base_url)
        providers.append(ollama)

        # 3. Heuristic (siempre al final)
        from .heuristic_client import HeuristicClient
        providers.append(HeuristicClient())

        return cls(providers)

    async def analyze_vigency(
        self,
        content: str,
        website_url: str,
        copyright_year: Optional[int] = None,
    ) -> VigencyResult:
        """Analiza vigencia intentando proveedores en orden."""
        last_error: Optional[Exception] = None

        for provider in self.providers:
            try:
                # Verificar disponibilidad
                if hasattr(provider, 'is_available'):
                    if not await provider.is_available():
                        continue

                # Intentar análisis
                result = await provider.analyze_vigency(
                    content=content,
                    website_url=website_url,
                    copyright_year=copyright_year,
                )

                # Si obtuvimos resultado válido, retornar
                if result.is_outdated is not None or result.confidence > 0:
                    return result

            except Exception as e:
                last_error = e
                # Continuar con el siguiente proveedor
                continue

        # Si ninguno funcionó, usar heurístico
        from .heuristic_client import HeuristicClient
        return await HeuristicClient().analyze_vigency(
            content, website_url, copyright_year
        )

    async def generate_opening_angle(
        self,
        lead_name: str,
        niche: str,
        pain_points: list[str],
    ) -> str:
        """Genera ángulo de apertura."""
        for provider in self.providers:
            try:
                if hasattr(provider, 'is_available'):
                    if not await provider.is_available():
                        continue

                return await provider.generate_opening_angle(
                    lead_name=lead_name,
                    niche=niche,
                    pain_points=pain_points,
                )
            except Exception:
                continue

        # Fallback heurístico
        from .heuristic_client import HeuristicClient
        return await HeuristicClient().generate_opening_angle(
            lead_name, niche, pain_points
        )

    def test_connectivity(self) -> bool:
        """Testea conectividad de al menos un proveedor activo (sync-safe)."""
        import asyncio
        for provider in self.providers:
            try:
                if hasattr(provider, "is_available"):
                    if asyncio.iscoroutinefunction(provider.is_available):
                        loop = asyncio.new_event_loop()
                        try:
                            available = loop.run_until_complete(provider.is_available())
                        finally:
                            loop.close()
                    else:
                        available = provider.is_available()
                    if available:
                        return True
            except Exception:
                continue
        return False

    def get_available_providers(self) -> List[str]:
        """Lista proveedores disponibles."""
        return [p.provider_name for p in self.providers]
