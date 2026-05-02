"""Market Health Index - salud del mercado por múltiples factores."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MarketHealthIndex:
    """Índice compuesto de salud del mercado."""
    overall_score: float    # 0.0 - 1.0
    digital_penetration: float
    avg_ssl_adoption: float
    avg_tracking_adoption: float
    avg_content_freshness: float
    avg_competitor_density: float
    avg_review_count: float
    sentiment_compound: float
    opportunity_score: float
    risks: List[str]


class MarketHealthAnalyzer:
    """Analiza la salud del mercado desde múltiples factores."""

    def calculate(
        self,
        leads: List[dict],
        ssl_failure_rate: Optional[float] = None,
        tracking_adoption_rate: Optional[float] = None,
        content_outdated_pct: Optional[float] = None,
        avg_competitor_count: Optional[float] = None,
        sentiment_compound: Optional[float] = None,
    ) -> MarketHealthIndex:
        """Calcula índice compuesto desde leads y métricas agregadas."""
        if not leads:
            return MarketHealthIndex(
                overall_score=0.5,
                digital_penetration=0.0,
                avg_ssl_adoption=0.0,
                avg_tracking_adoption=0.0,
                avg_content_freshness=0.0,
                avg_competitor_density=0.0,
                avg_review_count=0.0,
                sentiment_compound=0.0,
                opportunity_score=0.5,
                risks=["Sin datos suficientes"],
            )

        total = len(leads)

        # Métricas derivadas de leads
        has_ssl = sum(1 for l in leads if l.get("has_ssl", True)) / total
        has_tracking = sum(1 for l in leads if l.get("has_tracking", False)) / total
        has_fresh_content = sum(1 for l in leads if l.get("content_fresh", 0) == 0.5) / total
        avg_reviews = sum(l.get("review_count", 0) for l in leads) / total
        avg_competitors = avg_competitor_count or sum(l.get("competitor_count", 0) for l in leads) / total

        # Digital penetration: % con web funcional
        has_website = sum(1 for l in leads if l.get("website")) / total

        # Calcular overall: ponderado
        # - Baja adopción SSL = malo
        # - Bajo tracking = oportunidad
        # - Bajo fresh content = oportunidad
        # - Competencia baja = oportunidad
        # - Sentimiento alto = bueno

        ssl_score = has_ssl  # 0-1
        tracking_score = 1.0 - has_tracking  # Invertido: bajo tracking = oportunidad
        freshness_score = 1.0 - has_fresh_content  # Invertido: contenido viejo = oportunidad
        competition_score = min(1.0, avg_competitors / 20.0)  # Normalizado a 20
        sentiment_score = (sentiment_compound or 0.0 + 1) / 2  # -1..1 → 0..1

        # Overall: promedio ponderado
        overall = (
            ssl_score * 0.2 +
            tracking_score * 0.25 +
            freshness_score * 0.25 +
            (1 - competition_score) * 0.15 +  # Baja competencia = bueno
            sentiment_score * 0.15
        )

        # Opportunity: baja digital + baja competencia
        opportunity = (1 - has_website) * 0.3 + tracking_score * 0.3 + freshness_score * 0.2 + (1 - competition_score) * 0.2

        # Riesgos
        risks = []
        if ssl_failure_rate and ssl_failure_rate > 0.5:
            risks.append("Alta tasa de errores SSL")
        if has_tracking > 0.7:
            risks.append("Alta competencia digital")
        if avg_reviews < 5:
            risks.append("Bajo volumen de reviews en el mercado")
        if not risks:
            risks.append("Mercado estable")

        return MarketHealthIndex(
            overall_score=round(overall, 2),
            digital_penetration=round(has_website, 2),
            avg_ssl_adoption=round(has_ssl, 2),
            avg_tracking_adoption=round(has_tracking, 2),
            avg_content_freshness=round(has_fresh_content, 2),
            avg_competitor_density=round(avg_competitors, 1),
            avg_review_count=round(avg_reviews, 0),
            sentiment_compound=round(sentiment_compound or 0.0, 2),
            opportunity_score=round(opportunity, 2),
            risks=risks,
        )
