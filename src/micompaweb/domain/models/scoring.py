"""Scoring models - sistema de puntuación explicable."""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field


class ScoreCategory(str, Enum):
    """Categorías de señales de scoring (3 Dimensiones)."""
    AUTHORITY = "authority"
    DIGITAL_NEGLECT = "digital_neglect"
    SALES_READINESS = "sales_readiness"
    MARKET = "market"


class ScoreBreakdown(BaseModel):
    """Desglose de scoring individual - trazabilidad completa.

    Cada criterio que suma al score tiene:
    - criterion: ID único del criterio
    - category: Categoría de negocio
    - points: Puntos asignados
    - max_points: Puntos máximos posibles
    - evidence: Evidencia observable
    - confidence: Confianza en la medición (0-1)
    - raw_data: Datos crudos que respaldan
    """

    criterion: str
    category: ScoreCategory
    points: int = Field(ge=0)
    max_points: int = Field(ge=0)
    evidence: str
    confidence: float = Field(ge=0.0, le=1.0)
    raw_data: dict = Field(default_factory=dict)

    @property
    def percentage(self) -> float:
        """Porcentaje de puntos obtenidos vs máximo."""
        if self.max_points == 0:
            return 0.0
        return (self.points / self.max_points) * 100


class ScoringResult(BaseModel):
    """Resultado completo de scoring con trazabilidad."""

    total_score: int = Field(ge=0, le=150)
    max_possible_score: int = 150
    priority_tier: str = "DISCARD"

    # Desglose por categoría
    breakdowns: List[ScoreBreakdown] = Field(default_factory=list)

    # Resumen por categoría (3D Matrix)
    authority_points: int = 0
    authority_max: int = 100
    digital_neglect_points: int = 0
    digital_neglect_max: int = 145
    sales_readiness_points: int = 0
    sales_readiness_max: int = 100

    # Pesos aplicados
    weights: dict = Field(default_factory=lambda: {
        "authority": 0.30,
        "digital_neglect": 0.45,
        "sales_readiness": 0.25,
    })

    # Metadata
    calculated_at: datetime = Field(default_factory=datetime.now)
    scorer_version: str = "2.0.0"

    @property
    def confidence_score(self) -> float:
        """Confianza promedio del scoring."""
        if not self.breakdowns:
            return 0.0
        return sum(b.confidence for b in self.breakdowns) / len(self.breakdowns)

    @property
    def percentage(self) -> float:
        """Porcentaje del score máximo."""
        return (self.total_score / self.max_possible_score) * 100

    def get_breakdown_by_category(self, category: ScoreCategory) -> List[ScoreBreakdown]:
        """Obtiene desglose por categoría."""
        return [b for b in self.breakdowns if b.category == category]

    def get_top_signals(self, n: int = 5) -> List[ScoreBreakdown]:
        """Obtiene las top señales por puntos."""
        sorted_breakdowns = sorted(self.breakdowns, key=lambda x: x.points, reverse=True)
        return sorted_breakdowns[:n]

    def to_dict_for_report(self) -> dict:
        """Convierte a dict para el reporte HTML."""
        return {
            "total_score": self.total_score,
            "max_possible": self.max_possible_score,
            "percentage": round(self.percentage, 1),
            "priority_tier": self.priority_tier,
            "confidence": round(self.confidence_score, 2),
            "by_category": {
                "authority": {
                    "points": self.authority_points,
                    "max": self.authority_max,
                    "percentage": round((self.authority_points / self.authority_max) * 100, 1) if self.authority_max else 0,
                },
                "digital_neglect": {
                    "points": self.digital_neglect_points,
                    "max": self.digital_neglect_max,
                    "percentage": round((self.digital_neglect_points / self.digital_neglect_max) * 100, 1) if self.digital_neglect_max else 0,
                },
                "sales_readiness": {
                    "points": self.sales_readiness_points,
                    "max": self.sales_readiness_max,
                    "percentage": round((self.sales_readiness_points / self.sales_readiness_max) * 100, 1) if self.sales_readiness_max else 0,
                },
            },
            "breakdowns": [
                {
                    "criterion": b.criterion,
                    "category": b.category.value,
                    "points": b.points,
                    "max_points": b.max_points,
                    "evidence": b.evidence,
                    "confidence": round(b.confidence, 2),
                }
                for b in self.breakdowns
            ],
        }