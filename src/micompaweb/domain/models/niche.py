"""Niche data repository - datos validados por nicho."""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass(frozen=True)
class NicheMetrics:
    """Métricas validadas para un nicho específico.

    Este dataclass es inmutable (frozen=True) para garantizar
    que los datos no cambien durante el runtime.
    """

    # Identificación
    niche_slug: str
    display_name: str

    # Datos de ticket promedio
    avg_ticket_usd: float
    ticket_data_source: str
    ticket_confidence: str  # "high", "medium", "low"

    # Datos de búsqueda
    monthly_local_searches_range: tuple[int, int]  # (min, max)
    searches_data_source: str
    searches_confidence: str

    # Tasas de conversión
    conversion_rate_offline: float  # Ej: 0.12 (12%)
    conversion_rate_online_optimized: float  # Ej: 0.22 (22%)
    conversion_data_source: str
    conversion_confidence: str

    # Estacionalidad (multiplicadores por mes)
    seasonality: List[float]  # [1.0, 1.2, 0.8, ...] 12 meses

    # Metadata
    confidence_level: str  # "high", "medium", "low"
    last_updated: str
    notes: str = ""


class NicheRepository:
    """Repositorio de datos por nicho con fuentes citables.

    Toda estimación de revenue debe venir de aquí o de
    datos configurados por el usuario.
    """

    # Base de datos de nichos validados
    DATABASE: dict[str, NicheMetrics] = {
        "plomeros": NicheMetrics(
            niche_slug="plomeros",
            display_name="Servicios de Plomería",
            avg_ticket_usd=150.0,
            ticket_data_source="HomeAdvisor Industry Report 2024",
            ticket_confidence="high",
            monthly_local_searches_range=(150, 800),
            searches_data_source="Google Ads Keyword Planner (promedio 3 ciudades)",
            searches_confidence="high",
            conversion_rate_offline=0.12,
            conversion_rate_online_optimized=0.22,
            conversion_data_source="Local Service Ads Benchmarks 2024",
            conversion_confidence="medium",
            seasonality=[1.0, 1.0, 1.1, 1.0, 0.9, 1.2, 1.3, 1.2, 1.0, 1.0, 1.1, 0.9],
            confidence_level="high",
            last_updated="2024-04-01",
            notes="Nicho estacional: picos en verano (climatización) y diciembre (calefacción)",
        ),

        "plumber": NicheMetrics(
            niche_slug="plumber",
            display_name="Plumbing Services",
            avg_ticket_usd=150.0,
            ticket_data_source="HomeAdvisor Industry Report 2024",
            ticket_confidence="high",
            monthly_local_searches_range=(150, 800),
            searches_data_source="Google Ads Keyword Planner (average 3 cities)",
            searches_confidence="high",
            conversion_rate_offline=0.12,
            conversion_rate_online_optimized=0.22,
            conversion_data_source="Local Service Ads Benchmarks 2024",
            conversion_confidence="medium",
            seasonality=[1.0, 1.0, 1.1, 1.0, 0.9, 1.2, 1.3, 1.2, 1.0, 1.0, 1.1, 0.9],
            confidence_level="high",
            last_updated="2024-04-01",
            notes="English version of plomeros",
        ),

        "dentistas": NicheMetrics(
            niche_slug="dentistas",
            display_name="Consultorios Dentales",
            avg_ticket_usd=450.0,
            ticket_data_source="ADA Survey 2023 - Valor promedio procedimiento",
            ticket_confidence="high",
            monthly_local_searches_range=(300, 1500),
            searches_data_source="Semrush Local SEO Report",
            searches_confidence="high",
            conversion_rate_offline=0.08,
            conversion_rate_online_optimized=0.18,
            conversion_data_source="Dental Marketing Institute Study",
            conversion_confidence="high",
            seasonality=[0.9, 0.9, 1.0, 1.0, 1.0, 0.8, 0.8, 1.0, 1.1, 1.0, 1.0, 0.7],
            confidence_level="high",
            last_updated="2024-03-15",
            notes="Alto valor de ticket, alta competencia",
        ),

        "dentist": NicheMetrics(
            niche_slug="dentist",
            display_name="Dental Services",
            avg_ticket_usd=450.0,
            ticket_data_source="ADA Survey 2023 - Average procedure value",
            ticket_confidence="high",
            monthly_local_searches_range=(300, 1500),
            searches_data_source="Semrush Local SEO Report",
            searches_confidence="high",
            conversion_rate_offline=0.08,
            conversion_rate_online_optimized=0.18,
            conversion_data_source="Dental Marketing Institute Study",
            conversion_confidence="high",
            seasonality=[0.9, 0.9, 1.0, 1.0, 1.0, 0.8, 0.8, 1.0, 1.1, 1.0, 1.0, 0.7],
            confidence_level="high",
            last_updated="2024-03-15",
            notes="English version of dentistas",
        ),

        "electricistas": NicheMetrics(
            niche_slug="electricistas",
            display_name="Servicios Eléctricos",
            avg_ticket_usd=120.0,
            ticket_data_source="HomeAdvisor Industry Report 2024",
            ticket_confidence="medium",
            monthly_local_searches_range=(200, 600),
            searches_data_source="Google Ads Keyword Planner",
            searches_confidence="medium",
            conversion_rate_offline=0.15,
            conversion_rate_online_optimized=0.25,
            conversion_data_source="Local Service Ads Benchmarks 2024",
            conversion_confidence="medium",
            seasonality=[1.0] * 12,
            confidence_level="medium",
            last_updated="2024-04-01",
        ),

        "carpinteros": NicheMetrics(
            niche_slug="carpinteros",
            display_name="Servicios de Carpintería",
            avg_ticket_usd=300.0,
            ticket_data_source="HomeAdvisor Industry Report 2024",
            ticket_confidence="medium",
            monthly_local_searches_range=(100, 400),
            searches_data_source="Google Ads Keyword Planner",
            searches_confidence="medium",
            conversion_rate_offline=0.10,
            conversion_rate_online_optimized=0.20,
            conversion_data_source="Estimado estándar industria",
            conversion_confidence="low",
            seasonality=[1.0] * 12,
            confidence_level="medium",
            last_updated="2024-04-01",
        ),

        "abogados": NicheMetrics(
            niche_slug="abogados",
            display_name="Servicios Legales",
            avg_ticket_usd=500.0,
            ticket_data_source="Clio Legal Industry Report 2024",
            ticket_confidence="high",
            monthly_local_searches_range=(200, 1000),
            searches_data_source="Google Ads Keyword Planner",
            searches_confidence="high",
            conversion_rate_offline=0.08,
            conversion_rate_online_optimized=0.15,
            conversion_data_source="Legal Marketing Association Study",
            conversion_confidence="medium",
            seasonality=[1.0] * 12,
            confidence_level="high",
            last_updated="2024-03-01",
            notes="Ticket muy alto, ciclo de venta largo",
        ),

        "restaurantes": NicheMetrics(
            niche_slug="restaurantes",
            display_name="Restaurantes y Comida",
            avg_ticket_usd=35.0,
            ticket_data_source="National Restaurant Association 2024",
            ticket_confidence="high",
            monthly_local_searches_range=(500, 3000),
            searches_data_source="Google Ads Keyword Planner",
            searches_confidence="high",
            conversion_rate_offline=0.05,
            conversion_rate_online_optimized=0.12,
            conversion_data_source="Restaurant Marketing Benchmarks",
            conversion_confidence="medium",
            seasonality=[1.0, 1.0, 1.1, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.2, 1.3],
            confidence_level="high",
            last_updated="2024-04-01",
            notes="Alto volumen, bajo ticket, alta competencia",
        ),

        # Fallback para nichos no catalogados
        "_default": NicheMetrics(
            niche_slug="default",
            display_name="Servicios Locales",
            avg_ticket_usd=120.0,
            ticket_data_source="Industry average - conservative estimate",
            ticket_confidence="low",
            monthly_local_searches_range=(100, 500),
            searches_data_source="Estimated based on population density",
            searches_confidence="low",
            conversion_rate_offline=0.10,
            conversion_rate_online_optimized=0.18,
            conversion_data_source="General small business benchmarks",
            conversion_confidence="low",
            seasonality=[1.0] * 12,
            confidence_level="low",
            last_updated="2024-01-01",
            notes="Fallback metrics - user should configure specific niche",
        ),
    }

    @classmethod
    def get(cls, niche: str) -> NicheMetrics:
        """Obtiene métricas para un nicho.

        Args:
            niche: Slug del nicho (ej: "plomeros")

        Returns:
            NicheMetrics o default si no existe
        """
        niche_lower = niche.lower().strip()
        # Remover plurales simples para matching
        if niche_lower.endswith("s") and niche_lower[:-1] in cls.DATABASE:
            return cls.DATABASE[niche_lower[:-1]]
        return cls.DATABASE.get(niche_lower, cls.DATABASE["_default"])

    @classmethod
    def get_available(cls) -> List[str]:
        """Lista nichos disponibles (excluyendo default)."""
        return [k for k in cls.DATABASE.keys() if not k.startswith("_")]

    @classmethod
    def list_available(cls) -> List[str]:
        """Lista de nichos disponibles (excluye default)."""
        return sorted([k for k in cls.DATABASE.keys() if not k.startswith("_")])

    @classmethod
    def is_configured(cls, niche: str) -> bool:
        """Verifica si un nicho tiene datos configurados."""
        return niche.lower().strip() in cls.DATABASE

    @classmethod
    def add_custom(cls, niche: str, metrics: NicheMetrics) -> None:
        """Agrega nicho personalizado (para extensión futura)."""
        cls.DATABASE[niche.lower().strip()] = metrics

    @classmethod
    def get_confidence_color(cls, level: str) -> str:
        """Color para nivel de confianza (para UI)."""
        colors = {
            "high": "green",
            "medium": "yellow",
            "low": "red",
        }
        return colors.get(level, "gray")