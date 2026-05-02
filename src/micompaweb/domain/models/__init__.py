"""Domain models - core business entities."""

from .lead import Lead, WebsiteStatus, PriorityTier, TechnicalAudit, VigencyResult, GBPHealth, RevenueLoss, CompetitorComparison, ReviewSentiment
from .scoring import ScoreBreakdown, ScoringResult, ScoreCategory
from .project import Project, ProjectStatus, ProjectConfig
from .niche import NicheMetrics, NicheRepository
from .revenue import RevenueEstimate, RevenueMethodology

__all__ = [
    "Lead",
    "WebsiteStatus",
    "PriorityTier",
    "TechnicalAudit",
    "VigencyResult",
    "GBPHealth",
    "ScoreBreakdown",
    "ScoringResult",
    "ScoreCategory",
    "Project",
    "ProjectStatus",
    "ProjectConfig",
    "NicheMetrics",
    "NicheRepository",
    "RevenueEstimate",
    "RevenueMethodology",
    "RevenueLoss",
]