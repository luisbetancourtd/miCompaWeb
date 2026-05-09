"""Tests for ClosingMenu TUI component."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from micompaweb.domain.models import (
    Lead, WebsiteStatus, PriorityTier, Project, ProjectConfig, RevenueLoss,
)
from micompaweb.presentation.tui.closing_menu import ClosingMenu


def _make_leads():
    """Leads de ejemplo para tests."""
    return [
        Lead(
            id="l1",
            business_name="Top Biz",
            website_status=WebsiteStatus.NONE,
            niche="test",
            rating=4.8,
            review_count=55,
            pepita_score=130,
            priority=PriorityTier.ULTRA_HOT,
            revenue_loss=RevenueLoss(monthly_low=500, monthly_mid=1000, monthly_high=2000),
        ),
        Lead(
            id="l2",
            business_name="Hot Biz",
            website_status=WebsiteStatus.HTTP_ONLY,
            niche="test",
            rating=4.2,
            review_count=20,
            pepita_score=95,
            priority=PriorityTier.HOT,
            revenue_loss=RevenueLoss(monthly_low=300, monthly_mid=600, monthly_high=1200),
        ),
        Lead(
            id="l3",
            business_name="Warm Biz",
            website_status=WebsiteStatus.EXISTS,
            niche="test",
            rating=3.8,
            review_count=8,
            pepita_score=60,
            priority=PriorityTier.WARM,
        ),
    ]


def _make_project(tmp_path: Path):
    """Proyecto de ejemplo."""
    project = Project(
        slug="test-proj",
        config=ProjectConfig(niche="test", location="CDMX", max_leads=10),
    )
    project.total_estimated_revenue_loss_low = 800
    project.total_estimated_revenue_loss_high = 3200
    project.market_health_score = 65.5
    return project


class TestClosingMenu:
    """Tests del menu post-scan."""

    def test_options_list_complete(self):
        """Debe tener las 7 opciones definidas."""
        menu = ClosingMenu(
            project=_make_project(Path("/tmp")),
            leads=[],
            project_dir=Path("/tmp"),
        )
        assert len(menu.OPTIONS) == 7
        labels = [opt[0] for opt in menu.OPTIONS]
        assert any("Top 10" in l for l in labels)
        assert any("HTML" in l for l in labels)
        assert any("CSV" in l for l in labels)
        assert any("email borrador" in l for l in labels)
        assert any("emails batch" in l for l in labels)
        assert any("Revenue" in l for l in labels)
        assert any("Salir" in l for l in labels)

    @patch("micompaweb.presentation.tui.closing_menu.questionary.select")
    def test_show_returns_selected_action(self, mock_select, tmp_path: Path):
        """show() retorna la accion seleccionada."""
        menu = ClosingMenu(
            project=_make_project(tmp_path),
            leads=_make_leads(),
            project_dir=tmp_path,
        )
        mock_select.return_value.ask.return_value = menu.OPTIONS[-1][0]
        result = menu.show()
        assert result == "exit"

    @patch("micompaweb.presentation.tui.closing_menu.console.print")
    def test_view_leads_prints_table(self, mock_print, tmp_path: Path):
        """view_leads debe imprimir tabla con leads."""
        menu = ClosingMenu(
            project=_make_project(tmp_path),
            leads=_make_leads(),
            project_dir=tmp_path,
        )
        menu.view_leads()
        # Debe haber llamado a console.print al menos una vez
        assert mock_print.called

    @patch("micompaweb.presentation.tui.closing_menu.console.print")
    def test_revenue_dashboard_prints_metrics(self, mock_print, tmp_path: Path):
        """revenue_dashboard debe mostrar metricas de revenue."""
        menu = ClosingMenu(
            project=_make_project(tmp_path),
            leads=_make_leads(),
            project_dir=tmp_path,
        )
        menu.revenue_dashboard()
        calls = " ".join(str(c) for c in mock_print.call_args_list)
        assert "Proyeccion" in calls
        assert "100" in calls  # Projected revenue value

    def test_signals_for_lead_with_no_website(self, tmp_path: Path):
        """Debe detectar sin sitio web."""
        menu = ClosingMenu(
            project=_make_project(tmp_path),
            leads=[],
            project_dir=tmp_path,
        )
        lead = Lead(
            business_name="X",
            website_status=WebsiteStatus.NONE,
            niche="test",
        )
        signals = menu._signals_for_lead(lead)
        assert any("Sin sitio web" in s for s in signals)

    def test_email_top_no_leads(self, tmp_path: Path):
        """email_top con leads vacios debe mostrar warning."""
        menu = ClosingMenu(
            project=_make_project(tmp_path),
            leads=[],
            project_dir=tmp_path,
        )
        with patch("micompaweb.presentation.tui.closing_menu.console.print") as mock:
            menu.email_top()
            assert mock.called
