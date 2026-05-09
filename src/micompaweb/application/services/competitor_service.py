"""Competitor analysis service - Market intelligence."""

import asyncio
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CompetitorProfile:
    """Perfil de un competidor encontrado."""
    name: str
    has_website: bool = False
    has_tracking: bool = False  # Meta Pixel / GTM detectado
    has_gbp_optimized: bool = False  # Fotos, categorías, respuestas
    review_count: int = 0
    rating: float = 0.0
    estimated_age_months: int = 0
    digital_maturity_score: float = 0.0  # 0-100 (SSL + tracking + mobile + CMS)
    signals: List[str] = field(default_factory=list)


@dataclass
class CompetitorMatrix:
    """Matriz de inteligencia de competidores."""
    total_competitors: int = 0
    with_website: int = 0
    with_tracking: int = 0
    with_gbp_optimized: int = 0
    avg_rating: float = 0.0
    avg_reviews: float = 0.0
    market_maturity: str = "unknown"  # emergente, creciente, madura, saturada
    opportunity_score: float = 0.0  # 0-100
    profiles: List[CompetitorProfile] = field(default_factory=list)


class CompetitorService:
    """Servicio de análisis de competidores locales."""

    def __init__(self, web_auditor=None):
        self.web_auditor = web_auditor

    def analyze(self, raw_competitors: List[dict]) -> CompetitorMatrix:
        """Analiza lista de competidores crudos y genera matriz."""
        if not raw_competitors:
            return CompetitorMatrix()

        profiles: List[CompetitorProfile] = []
        for data in raw_competitors:
            profile = self._build_profile(data)
            profiles.append(profile)

        total = len(profiles)
        with_web = sum(1 for p in profiles if p.has_website)
        with_track = sum(1 for p in profiles if p.has_tracking)
        with_gbp = sum(1 for p in profiles if p.has_gbp_optimized)
        ratings = [p.rating for p in profiles if p.rating > 0]
        reviews = [p.review_count for p in profiles if p.review_count > 0]

        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
        avg_reviews = sum(reviews) / len(reviews) if reviews else 0.0

        # Clasificar madurez del mercado
        maturity = self._classify_maturity(total, with_web, with_track)

        # Escoring oportunidad: baja competencia digital = más oportunidad
        digital_penetration = (with_web / total * 0.5 + with_track / total * 0.3 + with_gbp / total * 0.2) if total else 0
        opportunity = max(0, 100 - int(digital_penetration * 100))

        return CompetitorMatrix(
            total_competitors=total,
            with_website=with_web,
            with_tracking=with_track,
            with_gbp_optimized=with_gbp,
            avg_rating=round(avg_rating, 1),
            avg_reviews=round(avg_reviews, 0),
            market_maturity=maturity,
            opportunity_score=opportunity,
            profiles=profiles,
        )

    def _build_profile(self, data: dict) -> CompetitorProfile:
        """Construye perfil desde datos crudos."""
        signals = []
        has_web = bool(data.get("website"))
        has_track = bool(data.get("has_tracking"))
        has_gbp = bool(data.get("has_photos", False)) and bool(data.get("has_reviews", False))

        if has_web:
            signals.append("Tiene web")
        else:
            signals.append("Sin web")
        if has_track:
            signals.append("Usa tracking")
        if has_gbp:
            signals.append("GBP activo")

        digital_maturity = self._calculate_digital_maturity(data)

        return CompetitorProfile(
            name=data.get("name", "Unknown"),
            has_website=has_web,
            has_tracking=has_track,
            has_gbp_optimized=has_gbp,
            review_count=data.get("review_count", 0),
            rating=data.get("rating", 0.0),
            estimated_age_months=data.get("age_months", 0),
            digital_maturity_score=round(digital_maturity, 1),
            signals=signals,
        )

    @staticmethod
    def _calculate_digital_maturity(data: dict) -> float:
        """Calcula score de madurez digital 0-100 desde datos crudos."""
        score = 0.0
        if data.get("ssl_valid", False):
            score += 25.0
        if data.get("has_tracking", False):
            score += 25.0
        if data.get("mobile_friendly", False):
            score += 25.0
        if data.get("cms") or data.get("technology_stack"):
            score += 25.0
        return score

    async def fetch_competitor_details(self, competitor_urls: List[str]) -> List[CompetitorProfile]:
        """Audita URLs de competidores y genera perfiles enriquecidos con datos reales.

        Args:
            competitor_urls: Lista de URLs de sitios web de competidores.

        Returns:
            Lista de CompetitorProfile con digital_maturity_score calculado.
        """
        if not self.web_auditor or not competitor_urls:
            return []

        profiles: List[CompetitorProfile] = []
        for url in competitor_urls:
            try:
                audit = await self.web_auditor.audit(url)
                data = {
                    "name": url,
                    "website": bool(url),
                    "has_tracking": any([
                        getattr(audit, "has_meta_pixel", False),
                        getattr(audit, "has_gtm", False),
                        getattr(audit, "has_analytics", False),
                    ]),
                    "ssl_valid": getattr(audit, "ssl_valid", False),
                    "mobile_friendly": getattr(audit, "mobile_friendly", False),
                    "cms": getattr(audit, "cms", None),
                    "technology_stack": getattr(audit, "technology_stack", []),
                }
                profiles.append(self._build_profile(data))
            except Exception:
                continue
        return profiles

    def _classify_maturity(self, total: int, with_web: int, with_track: int) -> str:
        """Clasifica madurez del mercado."""
        if total < 10:
            return "emergente"
        elif with_web / total < 0.3:
            return "emergente"
        elif with_track / total < 0.2:
            return "creciente"
        elif with_web / total > 0.7 and with_track / total > 0.5:
            return "madura"
        return "creciente"
