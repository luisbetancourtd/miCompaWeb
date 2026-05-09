"""MiCompaWeb Doctor - health check del sistema."""

import sys
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class HealthCheck:
    component: str
    status: str   # "ok", "warning", "error"
    message: str
    latency_ms: Optional[float] = None


@dataclass
class DoctorReport:
    overall: str  # "healthy", "degraded", "critical"
    checks: List[HealthCheck] = field(default_factory=list)
    version: str = "M1-RECARGADO 3.0"
    python_version: str = field(default_factory=lambda: f"{sys.version_info.major}.{sys.version_info.minor}")


class MiCompaWebDoctor:
    """Doctor de sistema - verifica salud de todos los componentes."""

    REQUIRED_PACKAGES = [
        "typer", "rich", "pydantic", "questionary", "tenacity", "structlog",
    ]

    def __init__(self):
        self._checks: List[HealthCheck] = []

    def run(self) -> DoctorReport:
        """Ejecuta todos los checks y genera reporte."""
        self._checks = []

        self._check_python_version()
        self._check_dependencies()
        self._check_models()
        self._check_services()
        self._check_tui()
        self._check_database()

        # Calcular overall
        errors = sum(1 for c in self._checks if c.status == "error")
        warnings = sum(1 for c in self._checks if c.status == "warning")

        if errors > 0:
            overall = "critical"
        elif warnings > 0:
            overall = "degraded"
        else:
            overall = "healthy"

        return DoctorReport(
            overall=overall,
            checks=self._checks,
        )

    def _check_python_version(self) -> None:
        v = sys.version_info
        if v.major >= 3 and v.minor >= 10:
            self._checks.append(HealthCheck(
                component="Python",
                status="ok",
                message=f"Python {v.major}.{v.minor}.{v.micro}",
            ))
        else:
            self._checks.append(HealthCheck(
                component="Python",
                status="warning",
                message=f"Python {v.major}.{v.minor}.{v.micro} - se recomienda 3.10+",
            ))

    def _check_dependencies(self) -> None:
        missing = []
        for pkg in self.REQUIRED_PACKAGES:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)

        if missing:
            self._checks.append(HealthCheck(
                component="Dependencies",
                status="error",
                message=f"Faltan: {', '.join(missing)}",
            ))
        else:
            self._checks.append(HealthCheck(
                component="Dependencies",
                status="ok",
                message="Todas las dependencias instaladas",
            ))

    def _check_models(self) -> None:
        try:
            from micompaweb.domain.models import Lead, Project, ScoringResult
            self._checks.append(HealthCheck(
                component="Domain Models",
                status="ok",
                message="Lead, Project, ScoringResult importan correctamente",
            ))
        except Exception as e:
            self._checks.append(HealthCheck(
                component="Domain Models",
                status="error",
                message=f"Error: {e}",
            ))

    def _check_services(self) -> None:
        try:
            from micompaweb.infrastructure.cost_guardian import CostGuardian
            from micompaweb.application.services import (
                ScoringService, CompetitorService, MarketHealthAnalyzer,
                EmailGenerator, SentimentAdapter,
            )
            self._checks.append(HealthCheck(
                component="Services",
                status="ok",
                message="Scoring, Competitors, Market Health, Cost, Email, Sentiment OK",
            ))
        except Exception as e:
            self._checks.append(HealthCheck(
                component="Services",
                status="error",
                message=f"Error: {e}",
            ))

    def _check_tui(self) -> None:
        try:
            from micompaweb.presentation.tui import WelcomeBanner, ProgressPanel, ResultTable, ClosingScreen
            self._checks.append(HealthCheck(
                component="TUI",
                status="ok",
                message="WelcomeBanner, ProgressPanel, ResultTable, ClosingScreen OK",
            ))
        except Exception as e:
            self._checks.append(HealthCheck(
                component="TUI",
                status="error",
                message=f"Error: {e}",
            ))

    def _check_database(self) -> None:
        try:
            import sqlite3
            conn = sqlite3.connect(":memory:")
            conn.execute("SELECT 1")
            conn.close()
            self._checks.append(HealthCheck(
                component="Database",
                status="ok",
                message="SQLite funcional",
            ))
        except Exception as e:
            self._checks.append(HealthCheck(
                component="Database",
                status="warning",
                message=f"SQLite no disponible: {e}",
            ))
