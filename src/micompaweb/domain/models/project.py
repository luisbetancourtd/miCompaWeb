"""Project model - metadata de sesión de prospección."""

from datetime import datetime
from typing import Optional, Literal, List
from enum import Enum

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """Estado del proyecto."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProjectConfig(BaseModel):
    """Configuración del wizard."""
    niche: str
    location: str
    target_language: Literal["es", "en", "fr"] = "es"
    depth: Literal["rapida", "estandar", "exhaustiva"] = "estandar"
    max_leads: int = Field(default=20, ge=1, le=500)


class ProjectStats(BaseModel):
    """Estadísticas del proyecto."""
    total_scanned: int = 0
    total_leads: int = 0
    ultra_hot_leads: int = 0
    hot_leads: int = 0
    warm_leads: int = 0
    cold_leads: int = 0
    discarded_leads: int = 0
    # Nuevos campos Market Health
    ssl_failure_rate: float = 0.0
    tracking_adoption_rate: float = 0.0
    content_outdated_pct: float = 0.0
    avg_competitor_count: float = 0.0


class PipelineStage(str, Enum):
    """Etapas del pipeline M1 completo."""
    WIZARD = "wizard"
    VALIDATION = "validation"
    DISCOVERY = "discovery"
    COMPETITORS = "competitors"
    AUDIT = "audit"
    SENTIMENT = "sentiment"
    VIGENCY = "vigency"
    SCORING = "scoring"
    REVENUE = "revenue"
    EXPORT = "export"


class ProcessingState(BaseModel):
    """Estado de procesamiento actual."""
    current_stage: str = ""
    current_step: int = 0
    total_steps: int = 0
    progress_percentage: float = 0.0
    message: str = ""


class Project(BaseModel):
    """Proyecto de prospección - contenedor de sesión."""

    # Identificación
    slug: str  # formato: "plomeros-cdmx-20260419"
    id: str = Field(default_factory=lambda: str(int(datetime.now().timestamp() * 1000)))

    # Configuración
    config: ProjectConfig

    # Estado
    status: ProjectStatus = ProjectStatus.PENDING
    processing_state: ProcessingState = Field(default_factory=ProcessingState)

    # Resultados
    stats: ProjectStats = Field(default_factory=ProjectStats)
    market_health_score: float = Field(default=0.0, ge=0.0, le=100.0)
    total_estimated_revenue_loss_low: float = 0.0
    total_estimated_revenue_loss_high: float = 0.0

    # Cost tracking
    estimated_api_cost_usd: float = 0.0
    actual_api_cost_usd: float = 0.0

    # Rutas
    project_path: Optional[str] = None
    cache_path: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    # Notas
    notes: List[str] = Field(default_factory=list)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duración del procesamiento en segundos."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_complete(self) -> bool:
        """Si el proyecto está completado."""
        return self.status == ProjectStatus.COMPLETED

    @property
    def has_hot_leads(self) -> bool:
        """Si hay leads HOT o ULTRA HOT."""
        return self.stats.hot_leads > 0 or self.stats.ultra_hot_leads > 0

    def to_summary_dict(self) -> dict:
        """Resumen para UI."""
        return {
            "slug": self.slug,
            "niche": self.config.niche,
            "location": self.config.location,
            "status": self.status.value,
            "total_leads": self.stats.total_leads,
            "hot_leads": self.stats.hot_leads,
            "ultra_hot_leads": self.stats.ultra_hot_leads,
            "market_health_score": round(self.market_health_score, 1),
            "duration": self.duration_seconds,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }