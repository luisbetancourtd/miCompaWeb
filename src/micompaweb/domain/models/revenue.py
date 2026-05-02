"""Revenue calculation models - metodología defendible."""

from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime


@dataclass
class RevenueMethodology:
    """Metodología de cálculo de pérdida de ingresos.

    Contiene toda la información necesaria para defender
    la estimación ante un cliente o auditoría.
    """

    # Fórmula explicada
    formula: str = (
        "Pérdida = Búsquedas_Mensuales × Brecha_Conversión × Ticket_Promedio"
    )

    # Explicación paso a paso
    steps: List[str] = None  # type: ignore

    # Fuentes de datos
    data_sources: List[str] = None  # type: ignore

    # Supuestos clave
    assumptions: List[str] = None  # type: ignore

    # Limitaciones conocidas
    limitations: List[str] = None  # type: ignore

    def __post_init__(self):
        if self.steps is None:
            self.steps = [
                "1. Estimar volumen de búsquedas mensuales para el nicho y ubicación",
                "2. Calcular brecha de conversión (offline vs. online optimizado)",
                "3. Multiplicar por ticket promedio del nicho",
                "4. Aplicar factores de ajuste (conservador/optimista)",
            ]
        if self.data_sources is None:
            self.data_sources = ["Datos de nicho configurados"]
        if self.assumptions is None:
            self.assumptions = [
                "El negocio aparece en Google Maps (verificado)",
                "La brecha de conversión se mantiene constante",
                "No hay estacionalidad extrema fuera de lo normal",
                "El ticket promedio no varía >20% de la media",
            ]
        if self.limitations is None:
            self.limitations = [
                "Estimación basada en promedios de industria",
                "No considera factores específicos del negocio individual",
                "Resultados reales dependen de implementación y ejecución",
            ]


@dataclass
class RevenueEstimate:
    """Estimación de pérdida de ingresos con metodología completa.

    A diferencia de v1.0, incluye:
    - Rangos con justificación
    - Metodología trazable
    - Fuentes citables
    - Análisis de sensibilidad
    """

    # Resultados
    monthly_loss_low: float
    monthly_loss_mid: float
    monthly_loss_high: float
    annual_projection: float

    # Inputs usados
    monthly_searches: int
    conversion_gap: float
    avg_ticket: float
    confidence_level: str  # "high", "medium", "low"

    # Metodología completa
    methodology: RevenueMethodology

    # Análisis de sensibilidad
    sensitivity: Dict[str, float]

    # Metadata
    calculated_at: datetime = None  # type: ignore
    niche_slug: str = ""
    location: str = ""

    def __post_init__(self):
        if self.calculated_at is None:
            self.calculated_at = datetime.now()

    @property
    def monthly_range_str(self) -> str:
        """Rango mensual como string formateado."""
        return f"${self.monthly_loss_low:,.0f} - ${self.monthly_loss_high:,.0f}"

    @property
    def annual_range_str(self) -> str:
        """Rango anual como string formateado."""
        annual_low = self.monthly_loss_low * 12
        annual_high = self.monthly_loss_high * 12
        return f"${annual_low:,.0f} - ${annual_high:,.0f}"

    def to_report_dict(self) -> dict:
        """Convierte a dict para reporte HTML."""
        return {
            "monthly": {
                "low": round(self.monthly_loss_low, 2),
                "mid": round(self.monthly_loss_mid, 2),
                "high": round(self.monthly_loss_high, 2),
                "formatted": self.monthly_range_str,
            },
            "annual": {
                "projection": round(self.annual_projection, 2),
                "formatted": self.annual_range_str,
            },
            "confidence": self.confidence_level,
            "methodology": {
                "formula": self.methodology.formula,
                "steps": self.methodology.steps,
                "sources": self.methodology.data_sources,
                "assumptions": self.methodology.assumptions,
                "limitations": self.methodology.limitations,
            },
            "sensitivity": self.sensitivity,
            "inputs": {
                "monthly_searches": self.monthly_searches,
                "conversion_gap": round(self.conversion_gap * 100, 1),  # %
                "avg_ticket": self.avg_ticket,
            },
        }


class RevenueCalculator:
    """Calculadora de pérdida de ingresos con metodología transparente.

    Esta es la versión mejorada del revenue loss de v1.0.
    """

    @staticmethod
    def calculate(
        niche_slug: str,
        location: str,
        monthly_searches_range: tuple[int, int],
        conversion_offline: float,
        conversion_online: float,
        avg_ticket: float,
        data_sources: List[str],
        confidence: str = "medium",
    ) -> RevenueEstimate:
        """Calcula pérdida de ingresos con metodología completa.

        Args:
            niche_slug: Identificador del nicho
            location: Ubicación geográfica
            monthly_searches_range: Rango (min, max) de búsquedas mensuales
            conversion_offline: Tasa conversión sin web optimizada (0.0-1.0)
            conversion_online: Tasa conversión con web optimizada (0.0-1.0)
            avg_ticket: Ticket promedio en USD
            data_sources: Lista de fuentes de datos
            confidence: Nivel de confianza en los datos

        Returns:
            RevenueEstimate con metodología completa
        """
        # Brecha de conversión
        conversion_gap = conversion_online - conversion_offline

        # Escenarios
        searches_low, searches_high = monthly_searches_range
        searches_mid = (searches_low + searches_high) / 2

        # Factores de ajuste
        conservative_factor = 0.7
        optimistic_factor = 1.3

        # Cálculos
        monthly_low = (
            searches_low *
            (conversion_gap * conservative_factor) *
            avg_ticket
        )

        monthly_mid = searches_mid * conversion_gap * avg_ticket

        monthly_high = (
            searches_high *
            (conversion_gap * optimistic_factor) *
            avg_ticket
        )

        annual = monthly_mid * 12

        # Análisis de sensibilidad
        sensitivity = {
            "if_conversion_10_percent_higher": monthly_mid * 1.10,
            "if_conversion_10_percent_lower": monthly_mid * 0.90,
            "if_ticket_20_percent_higher": monthly_mid * 1.20,
            "if_ticket_20_percent_lower": monthly_mid * 0.80,
            "if_searches_half": monthly_mid * 0.50,
            "if_searches_double": monthly_mid * 2.00,
        }

        methodology = RevenueMethodology(
            formula="Pérdida = Búsquedas × Brecha_Conversión × Ticket",
            steps=[
                f"1. Volumen de búsquedas: {searches_low:,} - {searches_high:,}/mes",
                f"2. Brecha de conversión: {conversion_offline:.0%} → {conversion_online:.0%}",
                f"3. Ticket promedio: ${avg_ticket:,.0f}",
                "4. Factores de ajuste: 70% (conservador) / 130% (optimista)",
            ],
            data_sources=data_sources,
        )

        return RevenueEstimate(
            monthly_loss_low=monthly_low,
            monthly_loss_mid=monthly_mid,
            monthly_loss_high=monthly_high,
            annual_projection=annual,
            monthly_searches=int(searches_mid),
            conversion_gap=conversion_gap,
            avg_ticket=avg_ticket,
            confidence_level=confidence,
            methodology=methodology,
            sensitivity=sensitivity,
            niche_slug=niche_slug,
            location=location,
        )