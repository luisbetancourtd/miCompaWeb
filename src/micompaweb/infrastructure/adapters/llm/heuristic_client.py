"""Heuristic LLM client - siempre disponible, sin costo.

Este cliente usa reglas simples basadas en heurísticas cuando
no hay LLM disponible. Último recurso en la cadena de fallback.
"""

from datetime import datetime
from typing import Optional

from micompaweb.application.ports.llm_client import (
    LLMClient,
    VigencyResult,
    LLMProvider,
)


class HeuristicClient:
    """Cliente heurístico - siempre funciona, sin costo.

    Analiza contenido usando reglas simples:
    - Copyright year > 2 años → outdated
    - Fechas explícitas pasadas → outdated
    - Keywords específicas → outdated
    """

    def __init__(self):
        self.current_year = datetime.now().year

    async def analyze_vigency(
        self,
        content: str,
        website_url: str,
        copyright_year: Optional[int] = None,
    ) -> VigencyResult:
        """Analiza usando heurísticas."""
        content_lower = content.lower()
        evidence = []
        is_outdated = None
        confidence = 0.0
        reason = "No clear signals detected"

        # Heurística 1: Copyright year
        if copyright_year:
            years_old = self.current_year - copyright_year
            if years_old > 2:
                is_outdated = True
                confidence = min(0.9, 0.5 + (years_old * 0.1))
                reason = f"Copyright {copyright_year} is {years_old} years old"
                evidence.append(f"Copyright year: {copyright_year}")
            else:
                is_outdated = False
                confidence = 0.6
                reason = f"Copyright from {copyright_year} (recent)"
                evidence.append(f"Recent copyright: {copyright_year}")

        # Heurística 2: Fechas explícitas en el pasado
        past_years = [str(y) for y in range(self.current_year - 1, self.current_year - 5, -1)]
        found_years = [y for y in past_years if y in content]
        if found_years:
            if is_outdated is None:
                is_outdated = True
                confidence = 0.5
                reason = "References to past years found"
            evidence.extend([f"Mention of year {y}" for y in found_years])

        # Heurística 3: Palabras clave de desactualización
        outdated_keywords = [
            "coming soon", "próximamente", "opening soon",
            "under construction", "en construcción",
            "new location", "nueva ubicación",
        ]
        found_keywords = [kw for kw in outdated_keywords if kw in content_lower]
        if found_keywords:
            evidence.extend([f"Keyword: {kw}" for kw in found_keywords])

        # Heurística 4: Promociones con fechas pasadas
        if any(word in content_lower for word in ["expired", "finalizado", "terminó"]):
            is_outdated = True
            confidence = max(confidence, 0.7)
            evidence.append("Expired content mentioned")

        return VigencyResult(
            is_outdated=is_outdated,
            confidence=confidence,
            reason=reason,
            snippet=content[:200] if content else "",
            evidence=evidence,
            provider_used=LLMProvider.HEURISTIC,
            cost_usd=0.0,
        )

    async def generate_opening_angle(
        self,
        lead_name: str,
        niche: str,
        pain_points: list[str],
    ) -> str:
        """Genera ángulo simple basado en templates."""
        templates = [
            f"Hola {lead_name}, vi que tienen excelentes reviews pero su sitio web no refleja la calidad de su servicio. Me encantaría ayudarles a convertir esas visitas en clientes.",
            f"Buenos días, soy desarrollador web y trabajo con {niche} en la zona. Noté que su presencia online podría estar perdiéndoles clientes potenciales. ¿Tienen 5 minutos para conversar?",
        ]

        # Elegir template basado en pain points
        if "no_website" in pain_points:
            return templates[0]
        elif "outdated_website" in pain_points:
            return templates[1]

        return templates[0]

    def is_available(self) -> bool:
        """Siempre disponible."""
        return True

    @property
    def provider_name(self) -> str:
        return "heuristic"

    @property
    def is_local(self) -> bool:
        return True

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Siempre gratuito."""
        return 0.0
