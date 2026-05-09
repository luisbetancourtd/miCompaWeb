"""Scoring service - matriz 3D explicable (M1 RECARGADO).

Authority (30%, 0-100) + Digital Neglect (45%, 0-145) + Sales Readiness (25%, 0-100)
max weighted ~150 points.
"""

from datetime import datetime
from typing import List, Optional

from micompaweb.domain.models import (
    Lead,
    ScoreBreakdown,
    ScoringResult,
    PriorityTier,
    ScoreCategory,
)


class ScoringService:
    """Servicio de scoring con matriz 3D trazable."""

    # Pesos por categoría (suman 1.0)
    CATEGORY_WEIGHTS = {
        ScoreCategory.AUTHORITY: 0.30,
        ScoreCategory.DIGITAL_NEGLECT: 0.45,
        ScoreCategory.SALES_READINESS: 0.25,
        ScoreCategory.MARKET: 0.0,
    }

    # Máximos por categoría
    CATEGORY_MAX = {
        ScoreCategory.AUTHORITY: 100,
        ScoreCategory.DIGITAL_NEGLECT: 145,
        ScoreCategory.SALES_READINESS: 100,
        ScoreCategory.MARKET: 0,
    }

    # Umbral HIGH_TICKET para sales_readiness category_value
    HIGH_TICKET_THRESHOLD = {
        "high": 200,
        "medium": 100,
    }

    # CMS obsoletos
    OBSOLETE_CMS = {"wix", "godaddy", "weebly", "sitebuilder", "squarespace", "webflow"}

    # Umbrales de prioridad (calibrados a 0-150)
    PRIORITY_THRESHOLDS = {
        PriorityTier.ULTRA_HOT: 120,
        PriorityTier.HOT: 80,
        PriorityTier.WARM: 50,
        PriorityTier.COLD: 25,
        PriorityTier.DISCARD: 0,
    }

    def calculate(
        self,
        lead: Lead,
        depth: Optional[str] = None,
        niche_avg_ticket: Optional[float] = None,
    ) -> ScoringResult:
        """Calcula score 3D con trazabilidad completa."""
        breakdowns: List[ScoreBreakdown] = []

        breakdowns.extend(self._score_authority(lead))
        breakdowns.extend(self._score_digital_neglect(lead))
        breakdowns.extend(self._score_sales_readiness(lead, niche_avg_ticket))

        # Acumulados por categoría
        category_points = {cat: 0 for cat in ScoreCategory}
        for b in breakdowns:
            category_points[b.category] += b.points

        # Aplicar caps por categoría
        for cat in ScoreCategory:
            if cat != ScoreCategory.MARKET:
                category_points[cat] = min(
                    category_points[cat], self.CATEGORY_MAX[cat]
                )

        # Formula ponderada (raw max ~120)
        weighted_score = sum(
            category_points[cat] * self.CATEGORY_WEIGHTS[cat]
            for cat in ScoreCategory
        )

        # Escala a 150 para que el máximo absoluto sea ~150
        max_raw = sum(self.CATEGORY_MAX[cat] * self.CATEGORY_WEIGHTS[cat] for cat in ScoreCategory if cat != ScoreCategory.MARKET)
        scale = 150.0 / max_raw if max_raw > 0 else 1.0
        weighted_score = weighted_score * scale

        depth_mult = {"exhaustiva": 1.0, "estandar": 0.95, "rapida": 0.90}
        mult = depth_mult.get(depth, 1.0) if depth else 1.0
        weighted_score = weighted_score * mult

        total_score = min(int(round(weighted_score)), 150)
        priority = self._get_priority_tier(total_score)

        return ScoringResult(
            total_score=total_score,
            max_possible_score=150,
            priority_tier=priority.value,
            breakdowns=breakdowns,
            authority_points=category_points[ScoreCategory.AUTHORITY],
            authority_max=self.CATEGORY_MAX[ScoreCategory.AUTHORITY],
            digital_neglect_points=category_points[ScoreCategory.DIGITAL_NEGLECT],
            digital_neglect_max=self.CATEGORY_MAX[ScoreCategory.DIGITAL_NEGLECT],
            sales_readiness_points=category_points[ScoreCategory.SALES_READINESS],
            sales_readiness_max=self.CATEGORY_MAX[ScoreCategory.SALES_READINESS],
        )

    # ------------------------------------------------------------------
    # A. AUTHORITY (30%)
    # ------------------------------------------------------------------
    def _score_authority(self, lead: Lead) -> List[ScoreBreakdown]:
        """Puntuación de reputación offline (0-100)."""
        breakdowns = []

        # A1. Review Volume (0-40)
        rc = lead.review_count
        if rc >= 50:
            breakdowns.append(ScoreBreakdown(
                criterion="review_volume", category=ScoreCategory.AUTHORITY,
                points=40, max_points=40, evidence=f"{rc} reviews", confidence=1.0,
                raw_data={"review_count": rc},
            ))
        elif rc >= 30:
            breakdowns.append(ScoreBreakdown(
                criterion="review_volume", category=ScoreCategory.AUTHORITY,
                points=30, max_points=40, evidence=f"{rc} reviews", confidence=1.0,
                raw_data={"review_count": rc},
            ))
        elif rc >= 10:
            breakdowns.append(ScoreBreakdown(
                criterion="review_volume", category=ScoreCategory.AUTHORITY,
                points=15, max_points=40, evidence=f"{rc} reviews", confidence=1.0,
                raw_data={"review_count": rc},
            ))

        # A2. Review Rating (0-30)
        rating = lead.rating
        if rating >= 4.5:
            breakdowns.append(ScoreBreakdown(
                criterion="review_rating", category=ScoreCategory.AUTHORITY,
                points=30, max_points=30, evidence=f"{rating}★ rating", confidence=1.0,
                raw_data={"rating": rating},
            ))
        elif rating >= 4.0:
            breakdowns.append(ScoreBreakdown(
                criterion="review_rating", category=ScoreCategory.AUTHORITY,
                points=20, max_points=30, evidence=f"{rating}★ rating", confidence=1.0,
                raw_data={"rating": rating},
            ))
        elif rating >= 3.5:
            breakdowns.append(ScoreBreakdown(
                criterion="review_rating", category=ScoreCategory.AUTHORITY,
                points=10, max_points=30, evidence=f"{rating}★ rating", confidence=1.0,
                raw_data={"rating": rating},
            ))

        # A3. Local Signals (0-30)
        gbp = lead.gbp_health
        if gbp:
            local_signals = 0
            signals = []
            if gbp.photos_count > 20:
                local_signals += 10
                signals.append("photos>20")
            if gbp.has_categories and gbp.has_phone:
                local_signals += 10
                signals.append("atributos_completos")
            if gbp.has_hours:
                local_signals += 10
                signals.append("horarios_presentes")
            if local_signals > 0:
                breakdowns.append(ScoreBreakdown(
                    criterion="local_signals", category=ScoreCategory.AUTHORITY,
                    points=local_signals, max_points=30,
                    evidence=f"Local signals: {', '.join(signals)}", confidence=0.9,
                    raw_data={"gbp": gbp.model_dump() if hasattr(gbp, "model_dump") else {}},
                ))

        return breakdowns

    # ------------------------------------------------------------------
    # B. DIGITAL NEGLECT (45%, cap 145)
    # ------------------------------------------------------------------
    def _score_digital_neglect(self, lead: Lead) -> List[ScoreBreakdown]:
        """Puntuación de abandono digital (0-145)."""
        breakdowns = []
        current_year = datetime.now().year

        # B1. No Website (+50)
        if lead.website_status.value == "none":
            breakdowns.append(ScoreBreakdown(
                criterion="no_website", category=ScoreCategory.DIGITAL_NEGLECT,
                points=50, max_points=50, evidence="Sin presencia web", confidence=1.0,
                raw_data={"website_status": lead.website_status.value},
            ))
        # B1b. HTTP only / insecure
        elif lead.website_status.value == "http_only":
            breakdowns.append(ScoreBreakdown(
                criterion="insecure_http", category=ScoreCategory.DIGITAL_NEGLECT,
                points=20, max_points=50, evidence="HTTP sin HTTPS", confidence=1.0,
                raw_data={"website_status": lead.website_status.value},
            ))

        # B2. SSL inválido (+20)
        if lead.website_url and not lead.audit.ssl_valid:
            breakdowns.append(ScoreBreakdown(
                criterion="invalid_ssl", category=ScoreCategory.DIGITAL_NEGLECT,
                points=20, max_points=20, evidence="Certificado SSL inválido", confidence=0.9,
                raw_data={"ssl_valid": lead.audit.ssl_valid},
            ))

        # B3. Tech Obsolete (+15)
        cms = (lead.audit.cms or "").lower()
        copyright_year = lead.audit.copyright_year
        if cms in self.OBSOLETE_CMS:
            is_old = copyright_year is not None and (current_year - copyright_year) > 2
            if is_old or not lead.audit.has_meta_pixel and not lead.audit.has_gtm and not lead.audit.has_analytics:
                breakdowns.append(ScoreBreakdown(
                    criterion="tech_obsolete", category=ScoreCategory.DIGITAL_NEGLECT,
                    points=15, max_points=15,
                    evidence=f"CMS {cms} obsoleto/copyright {copyright_year}", confidence=0.85,
                    raw_data={"cms": cms, "copyright_year": copyright_year},
                ))

        # B4. No Tracking (+10)
        has_tracking = (
            lead.audit.has_meta_pixel or lead.audit.has_gtm or lead.audit.has_analytics
        )
        if not has_tracking:
            breakdowns.append(ScoreBreakdown(
                criterion="no_tracking", category=ScoreCategory.DIGITAL_NEGLECT,
                points=10, max_points=10,
                evidence="Sin tracking (Meta Pixel, GTM, Analytics)", confidence=0.95,
                raw_data={"has_meta_pixel": lead.audit.has_meta_pixel,
                          "has_gtm": lead.audit.has_gtm,
                          "has_analytics": lead.audit.has_analytics},
            ))

        # B5. Mobile Broken (+15)
        if not lead.audit.mobile_friendly:
            breakdowns.append(ScoreBreakdown(
                criterion="mobile_broken", category=ScoreCategory.DIGITAL_NEGLECT,
                points=15, max_points=15,
                evidence="Sin viewport responsive", confidence=0.9,
                raw_data={"mobile_friendly": lead.audit.mobile_friendly},
            ))

        # B6. Contact Missing (+10)
        no_emails = len(lead.audit.emails_found) == 0
        no_phones = len(lead.audit.phones_found) == 0
        if no_emails and no_phones:
            breakdowns.append(ScoreBreakdown(
                criterion="contact_missing", category=ScoreCategory.DIGITAL_NEGLECT,
                points=10, max_points=10,
                evidence="Sin email ni teléfono en web", confidence=0.9,
                raw_data={"emails": len(lead.audit.emails_found),
                          "phones": len(lead.audit.phones_found)},
            ))

        # B7. Content Outdated (+25)
        if lead.vigency and lead.vigency.is_outdated:
            points = int(lead.vigency.outdated_confidence * 25)
            breakdowns.append(ScoreBreakdown(
                criterion="content_outdated", category=ScoreCategory.DIGITAL_NEGLECT,
                points=points, max_points=25,
                evidence=lead.vigency.outdated_reason or "Contenido desactualizado",
                confidence=lead.vigency.outdated_confidence,
                raw_data={"is_outdated": lead.vigency.is_outdated,
                          "snippet": lead.vigency.outdated_snippet},
            ))

        return breakdowns

    # ------------------------------------------------------------------
    # C. SALES READINESS (25%, 0-100)
    # ------------------------------------------------------------------
    def _score_sales_readiness(
        self, lead: Lead, niche_avg_ticket: Optional[float] = None
    ) -> List[ScoreBreakdown]:
        """Propensión a comprar servicios digitales (0-100)."""
        breakdowns = []

        # C1. Active GBP (+30)
        if lead.owner_response_rate is not None and lead.owner_response_rate > 0.25:
            breakdowns.append(ScoreBreakdown(
                criterion="active_gbp", category=ScoreCategory.SALES_READINESS,
                points=30, max_points=30,
                evidence=f"Responde reviews ({lead.owner_response_rate:.0%})", confidence=0.9,
                raw_data={"owner_response_rate": lead.owner_response_rate},
            ))

        # C2. Competitor Density (+20)
        if lead.competitor_count > 5:
            breakdowns.append(ScoreBreakdown(
                criterion="competitor_density", category=ScoreCategory.SALES_READINESS,
                points=20, max_points=20,
                evidence=f"{lead.competitor_count} competidores", confidence=0.85,
                raw_data={"competitor_count": lead.competitor_count},
            ))

        # C3. Recent Activity (+25)
        if lead.has_recent_reviews:
            breakdowns.append(ScoreBreakdown(
                criterion="recent_activity", category=ScoreCategory.SALES_READINESS,
                points=25, max_points=25,
                evidence="Reviews recientes (últimos 30 días)", confidence=0.85,
                raw_data={"has_recent_reviews": lead.has_recent_reviews},
            ))

        # C4. Category Value (+25)
        avg = niche_avg_ticket if niche_avg_ticket else 0.0
        if avg >= self.HIGH_TICKET_THRESHOLD["high"]:
            breakdowns.append(ScoreBreakdown(
                criterion="category_value", category=ScoreCategory.SALES_READINESS,
                points=25, max_points=25,
                evidence=f"Nicho alto ticket (${avg})", confidence=0.8,
                raw_data={"avg_ticket": avg},
            ))
        elif avg >= self.HIGH_TICKET_THRESHOLD["medium"]:
            breakdowns.append(ScoreBreakdown(
                criterion="category_value", category=ScoreCategory.SALES_READINESS,
                points=15, max_points=25,
                evidence=f"Nicho medio ticket (${avg})", confidence=0.8,
                raw_data={"avg_ticket": avg},
            ))

        return breakdowns

    def _get_priority_tier(self, score: int) -> PriorityTier:
        """Asigna tier basado en score calibrado 0-150."""
        if score >= self.PRIORITY_THRESHOLDS[PriorityTier.ULTRA_HOT]:
            return PriorityTier.ULTRA_HOT
        elif score >= self.PRIORITY_THRESHOLDS[PriorityTier.HOT]:
            return PriorityTier.HOT
        elif score >= self.PRIORITY_THRESHOLDS[PriorityTier.WARM]:
            return PriorityTier.WARM
        elif score >= self.PRIORITY_THRESHOLDS[PriorityTier.COLD]:
            return PriorityTier.COLD
        return PriorityTier.DISCARD
