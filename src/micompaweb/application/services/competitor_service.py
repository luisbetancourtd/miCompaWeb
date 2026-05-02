"""Competitor analysis service - Market intelligence."""

from dataclasses import dataclass, field
from typing import List


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

        return CompetitorProfile(
            name=data.get("name", "Unknown"),
            has_website=has_web,
            has_tracking=has_track,
            has_gbp_optimized=has_gbp,
            review_count=data.get("review_count", 0),
            rating=data.get("rating", 0.0),
            estimated_age_months=data.get("age_months", 0),
            signals=signals,
        )

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
