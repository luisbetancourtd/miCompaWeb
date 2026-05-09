"""CostGuardian - control de costos con persistencia diaria SQLite."""

import sqlite3
from dataclasses import dataclass, field
from typing import Dict
from datetime import date
from pathlib import Path


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
    """Guardián de presupuesto: máximo $2.00 USD por día, con persistencia SQLite."""

    DAILY_LIMIT_USD = 2.00

    # Costos unitarios estimados
    COSTS = {
        "google_places": 0.017,   # $17/1000 requests
        "google_search": 0.005,   # $5/1000 queries
        "serp_api": 0.0015,       # ~$1.5/1000
        "llm_api": 0.003,         # ~$3/1000 tokens
        "crawl_ai": 0.001,        # Crawl4AI local ≈ gratis, reserva
        "manual": 0.0,            # Síncronas = $0
    }

    def __init__(self, db_path: Path = Path("./projects/.cache/cost_log.db")):
        self.db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.spent: float = self._load_daily_spent()
        self.breakdown = CostBreakdown()
        self.counters: Dict[str, int] = {}

    @property
    def _db_path(self) -> Path:
        return self.db_path

    def _init_db(self) -> None:
        """Crea tabla de cost_log si no existe."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cost_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    service TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 1,
                    cost REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _load_daily_spent(self) -> float:
        """Carga gasto acumulado del día actual desde SQLite."""
        today = date.today().isoformat()
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                row = conn.execute(
                    "SELECT SUM(cost) FROM cost_log WHERE date = ?",
                    (today,),
                ).fetchone()
                return row[0] or 0.0
        except Exception:
            return 0.0

    def _persist_charge(self, service: str, count: int, cost: float) -> None:
        """Guarda un cargo en SQLite."""
        today = date.today().isoformat()
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute(
                    "INSERT INTO cost_log (date, service, count, cost) VALUES (?, ?, ?, ?)",
                    (today, service, count, cost),
                )
                conn.commit()
        except Exception:
            pass  # Fail silently on DB error; in-memory tracker still works

    def charge(self, service: str, count: int = 1) -> bool:
        """Registra uso de servicio. True si queda presupuesto."""
        unit_cost = self.COSTS.get(service, 0.0)
        cost = unit_cost * count

        if self.spent + cost > self.DAILY_LIMIT_USD:
            return False

        self.spent += cost
        self._persist_charge(service, count, cost)
        self.breakdown.__dict__[service] = self.breakdown.__dict__.get(service, 0.0) + cost
        self.breakdown.total = self.spent
        self.counters[service] = self.counters.get(service, 0) + count
        return True

    def preview_cost(self, service: str, count: int = 1) -> float:
        """Devuelve costo estimado sin registrar el cargo."""
        return self.COSTS.get(service, 0.0) * count

    def can_proceed(self, service: str, count: int = 1) -> bool:
        """True si hay presupuesto diario para N llamadas al servicio."""
        cost = self.preview_cost(service, count)
        return self.spent + cost <= self.DAILY_LIMIT_USD

    def can_afford(self, service: str, count: int = 1) -> bool:
        """Alias de can_proceed para compatibilidad."""
        return self.can_proceed(service, count)

    def remaining(self) -> float:
        return round(self.DAILY_LIMIT_USD - self.spent, 4)

    def summary(self) -> dict:
        return {
            "total_spent": round(self.spent, 4),
            "remaining": self.remaining(),
            "budget": self.DAILY_LIMIT_USD,
            "breakdown": {
                k: round(v, 6)
                for k, v in self.breakdown.__dict__.items()
                if v > 0 or k == "total"
            },
            "usage_counts": self.counters,
        }
