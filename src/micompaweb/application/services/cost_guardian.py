"""CostGuardian - control de costos de ejecución."""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class CostBreakdown:
    """Desglose de costos de la sesión."""
    google_places: float = 0.0
    google_search: float = 0.0
    serp_api: float = 0.0
    llm_api: float = 0.0
    crawl_ai: float = 0.0
    manual: float = 0.0
    total: float = 0.0


class CostGuardian:
    """Guardián de presupuesto: máximo $2.00 USD por sesión."""

    MAX_BUDGET_USD = 2.00

    # Costos unitarios estimados
    COSTS = {
        "google_places": 0.017,   # $17/1000 requests
        "google_search": 0.005,   # $5/1000 queries
        "serp_api": 0.0015,       # ~$1.5/1000
        "llm_api": 0.003,         # ~$3/1000 tokens (GPT-3.5)
        "crawl_ai": 0.001,        # Crawl4AI local ≈ gratis, reserva
        "manual": 0.0,            # Síncronas = $0
    }

    def __init__(self):
        self.spent: float = 0.0
        self.breakdown = CostBreakdown()
        self.counters: Dict[str, int] = {}

    def charge(self, service: str, count: int = 1) -> bool:
        """Registra uso de servicio. True si queda presupuesto."""
        unit_cost = self.COSTS.get(service, 0.0)
        cost = unit_cost * count

        if self.spent + cost > self.MAX_BUDGET_USD:
            return False  # No se puede gastar más

        self.spent += cost
        self.breakdown.__dict__[service] = self.breakdown.__dict__.get(service, 0.0) + cost
        self.breakdown.total = self.spent
        self.counters[service] = self.counters.get(service, 0) + count
        return True

    def can_afford(self, service: str, count: int = 1) -> bool:
        """True si hay presupuesto para N llamadas al servicio."""
        cost = self.COSTS.get(service, 0.0) * count
        return self.spent + cost <= self.MAX_BUDGET_USD

    def remaining(self) -> float:
        return round(self.MAX_BUDGET_USD - self.spent, 4)

    def summary(self) -> dict:
        return {
            "total_spent": round(self.spent, 4),
            "remaining": self.remaining(),
            "budget": self.MAX_BUDGET_USD,
            "breakdown": {
                k: round(v, 6)
                for k, v in self.breakdown.__dict__.items()
                if v > 0 or k == "total"
            },
            "usage_counts": self.counters,
        }
