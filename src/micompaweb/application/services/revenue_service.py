"""Revenue service - cálculo defendible de pérdida de ingresos."""

from micompaweb.domain.models import Lead, RevenueLoss
from micompaweb.domain.models.niche import NicheRepository
from micompaweb.domain.models.revenue import RevenueCalculator


class RevenueService:
    """Servicio de cálculo de pérdida de ingresos.

    Usa NicheRepository para obtener datos validados
    y RevenueCalculator para la metodología transparente.
    """

    def calculate(self, lead: Lead, niche_override: str = "") -> RevenueLoss:
        """Calcula pérdida de ingresos para un lead.

        Args:
            lead: Lead con datos completos
            niche_override: Nicho alternativo (opcional)

        Returns:
            RevenueLoss con metodología completa
        """
        niche = niche_override or lead.niche
        metrics = NicheRepository.get(niche)

        # Calcular usando metodología transparente
        estimate = RevenueCalculator.calculate(
            niche_slug=metrics.niche_slug,
            location=lead.city or "Unknown",
            monthly_searches_range=metrics.monthly_local_searches_range,
            conversion_offline=metrics.conversion_rate_offline,
            conversion_online=metrics.conversion_rate_online_optimized,
            avg_ticket=metrics.avg_ticket_usd,
            data_sources=[
                metrics.ticket_data_source,
                metrics.searches_data_source,
                metrics.conversion_data_source,
            ],
            confidence=metrics.confidence_level,
        )

        return RevenueLoss(
            monthly_low=estimate.monthly_loss_low,
            monthly_mid=estimate.monthly_loss_mid,
            monthly_high=estimate.monthly_loss_high,
            annual_projection=estimate.annual_projection,
            methodology=estimate.methodology.formula,
            assumptions=estimate.methodology.assumptions,
            data_sources=estimate.methodology.data_sources,
            confidence_level=estimate.confidence_level,
            sensitivity_analysis=estimate.sensitivity,
        )