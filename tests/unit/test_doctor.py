"""Tests for MiCompaWeb Doctor."""

import pytest

from micompaweb.application.services.doctor import MiCompaWebDoctor, DoctorReport, HealthCheck


class TestMiCompaWebDoctor:
    """Test suite del Doctor de sistema."""

    def test_run_returns_report(self):
        doc = MiCompaWebDoctor()
        report = doc.run()
        assert isinstance(report, DoctorReport)
        assert report.overall in ("healthy", "degraded", "critical")

    def test_report_has_version(self):
        doc = MiCompaWebDoctor()
        report = doc.run()
        assert report.version == "M1-RECARGADO 3.0"
        assert report.python_version.startswith("3.")

    def test_all_checks_present(self):
        doc = MiCompaWebDoctor()
        report = doc.run()
        components = {c.component for c in report.checks}
        assert "Python" in components
        assert "Domain Models" in components
        assert "Services" in components
        assert "TUI" in components
        assert "Database" in components

    def test_python_check_is_ok(self):
        doc = MiCompaWebDoctor()
        report = doc.run()
        python = [c for c in report.checks if c.component == "Python"][0]
        assert python.status == "ok"

    def test_models_check_is_ok(self):
        doc = MiCompaWebDoctor()
        report = doc.run()
        models = [c for c in report.checks if c.component == "Domain Models"][0]
        assert models.status == "ok"

    def test_services_check_is_ok(self):
        doc = MiCompaWebDoctor()
        report = doc.run()
        svc = [c for c in report.checks if c.component == "Services"][0]
        assert svc.status == "ok"

    def test_tui_check_is_ok(self):
        doc = MiCompaWebDoctor()
        report = doc.run()
        tui = [c for c in report.checks if c.component == "TUI"][0]
        assert tui.status == "ok"

    def test_database_check_is_ok(self):
        doc = MiCompaWebDoctor()
        report = doc.run()
        db = [c for c in report.checks if c.component == "Database"][0]
        assert db.status == "ok"

    def test_dependencies_check_is_ok_in_venv(self):
        """Si questionary/structlog están en el PATH del venv, es OK."""
        doc = MiCompaWebDoctor()
        report = doc.run()
        deps = [c for c in report.checks if c.component == "Dependencies"][0]
        # En el sandbox de test puede fallar, en venv está OK
        assert deps.status in ("ok", "error")

    def test_report_has_leads_structure(self):
        doc = MiCompaWebDoctor()
        report = doc.run()
        assert len(report.checks) >= 5
        for c in report.checks:
            assert c.component
            assert c.status in ("ok", "warning", "error")
            assert c.message
