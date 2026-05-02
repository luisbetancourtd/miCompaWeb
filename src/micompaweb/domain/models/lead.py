"""Lead model - core domain entity."""

from datetime import datetime
from typing import Optional, List, Dict, Literal
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ConfigDict


class WebsiteStatus(str, Enum):
    """Estado del sitio web."""
    EXISTS = "exists"
    HTTP_ONLY = "http_only"
    NONE = "none"


class PriorityTier(str, Enum):
    """Tier de prioridad del lead."""
    ULTRA_HOT = "ULTRA HOT"
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"
    DISCARD = "DISCARD"


class TechnicalAudit(BaseModel):
    """Resultado de auditoría técnica."""
    ssl_valid: bool = False
    ssl_expiry: Optional[datetime] = None
    ssl_issuer: Optional[str] = None

    has_meta_pixel: bool = False
    has_gtm: bool = False
    has_analytics: bool = False
    has_linkedin_pixel: bool = False
    has_tiktok_pixel: bool = False

    mobile_friendly: bool = False
    load_time_ms: Optional[int] = None

    technology_stack: List[str] = Field(default_factory=list)
    cms: Optional[str] = None
    hosting: Optional[str] = None

    emails_found: List[str] = Field(default_factory=list)
    phones_found: List[str] = Field(default_factory=list)
    social_links: Dict[str, Optional[str]] = Field(default_factory=dict)
    whatsapp_found: bool = False
    contact_forms_count: int = 0

    copyright_year: Optional[int] = None
    page_title: Optional[str] = None
    meta_description: Optional[str] = None

    @field_validator("emails_found", "phones_found")
    @classmethod
    def deduplicate_list(cls, v: List[str]) -> List[str]:
        """Elimina duplicados preservando orden."""
        seen = set()
        result = []
        for item in v:
            lower = item.lower()
            if lower not in seen:
                seen.add(lower)
                result.append(item)
        return result


class VigencyResult(BaseModel):
    """Análisis de vigencia de contenido."""
    is_outdated: Optional[bool] = None
    outdated_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    outdated_reason: str = ""
    outdated_snippet: str = ""
    evidence: List[str] = Field(default_factory=list)
    provider_used: str = "unknown"
    cost_usd: Optional[float] = None


class GBPHealth(BaseModel):
    """Salud del Google Business Profile."""
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    has_photos: bool = False
    has_hours: bool = False
    has_description: bool = False
    has_categories: bool = False
    has_phone: bool = False
    has_website: bool = False
    has_attributes: bool = False
    is_claimed: bool = False
    photos_count: int = 0


class ReviewSentiment(BaseModel):
    """Análisis de sentimiento de reviews."""
    common_themes: List[str] = Field(default_factory=list)
    digital_mentions: List[str] = Field(default_factory=list)
    digital_opportunities: List[str] = Field(default_factory=list)
    quotable_testimonials: List[str] = Field(default_factory=list)
    average_sentiment: float = Field(default=0.0, ge=-1.0, le=1.0)


class CompetitorComparison(BaseModel):
    """Comparación con competidores."""
    competitor_name: str
    competitor_rating: float
    competitor_reviews: int
    has_website: bool
    advantage: str


class RevenueLoss(BaseModel):
    """Pérdida de ingresos estimada."""
    monthly_low: float = 0.0
    monthly_mid: float = 0.0
    monthly_high: float = 0.0
    annual_projection: float = 0.0
    methodology: str = ""
    assumptions: List[str] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    confidence_level: Literal["high", "medium", "low"] = "low"
    sensitivity_analysis: Dict[str, float] = Field(default_factory=dict)


class Lead(BaseModel):
    """Lead completo - entidad principal del dominio."""

    # Identificación
    id: str = Field(default_factory=lambda: str(int(datetime.now().timestamp() * 1000)))
    external_id: str = ""  # ID de la fuente (ej: place_id de Google)
    source: str = ""  # Fuente original (google_places, fixture, etc.)

    # Información básica
    business_name: str
    category: str = ""
    niche: str = ""
    description: Optional[str] = None

    # Contacto
    phone: Optional[str] = None
    email: Optional[str] = None
    website_url: Optional[str] = None
    website_status: WebsiteStatus = WebsiteStatus.NONE

    # Ubicación
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    plus_code: Optional[str] = None

    # Google Maps
    maps_url: str = ""
    rating: float = Field(default=0.0, ge=0.0, le=5.0)
    review_count: int = Field(default=0, ge=0)
    owner_response_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # Estado del negocio
    business_status: Optional[str] = None  # ej: OPERATIONAL, CLOSED_TEMPORARILY, CLOSED_PERMANENTLY

    # Fotos
    photo_references: List[str] = Field(default_factory=list)  # place_photo references de Google

    # Reviews
    has_recent_reviews: bool = False
    review_velocity: float = 0.0  # reviews/mes
    review_sentiment: Optional[ReviewSentiment] = None

    # Redes sociales
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    youtube_url: Optional[str] = None
    whatsapp_url: Optional[str] = None

    # Auditoría y análisis
    audit: TechnicalAudit = Field(default_factory=TechnicalAudit)
    vigency: VigencyResult = Field(default_factory=VigencyResult)
    gbp_health: GBPHealth = Field(default_factory=GBPHealth)

    # Competitividad
    competitor_count: int = 0
    estimated_business_age_years: Optional[float] = None
    competitor_comparison: List[CompetitorComparison] = Field(default_factory=list)

    # Revenue y scoring
    revenue_loss: RevenueLoss = Field(default_factory=RevenueLoss)
    pepita_score: int = Field(default=0, ge=0, le=150)
    priority: PriorityTier = PriorityTier.DISCARD
    score_breakdown: List["ScoreBreakdown"] = Field(default_factory=list)  # type: ignore

    # Estado
    disqualified: bool = False
    disqualification_reason: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(populate_by_name=True)


# Forward reference para evitar circular import
from .scoring import ScoreBreakdown  # noqa: E402