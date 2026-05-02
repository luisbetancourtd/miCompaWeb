"""Tests para los nuevos comandos CLI de miCompaWeb."""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from micompaweb.app.cli import app
from micompaweb.application.ports.exporter import ExportResult


runner = CliRunner()


# ──────────────────────────────────────────────────────────────
# Mock data helpers
# ──────────────────────────────────────────────────────────────

def _make_project_dir(tmp_path: Path, slug: str, **overrides) -> Path:
    """Crea un directorio de proyecto M1 simulado."""
    pdir = tmp_path / slug
    pdir.mkdir(parents=True, exist_ok=True)

    state = {
        "slug": slug,
        "business_name": overrides.get("business_name", "Test Business"),
        "niche": overrides.get("niche", "plomeros"),
        "location": overrides.get("location", "CDMX"),
        "score": overrides.get("score", 87),
        "date": "2026-05-01",
        "priority": "ULTRA_HOT",
    }
    (pdir / "_state").mkdir(exist_ok=True)
    (pdir / "_state" / "m1_complete.json").write_text(json.dumps(state), encoding="utf-8")

    leads = {
        "leads": [
            {
                "business_name": "Business One",
                "website_status": "none",
                "rating": 4.5,
                "review_count": 45,
                "pepita_score": 120,
                "priority": "ULTRA HOT",
            },
            {
                "business_name": "Business Two",
                "website_status": "exists",
                "rating": 3.8,
                "review_count": 12,
                "pepita_score": 85,
                "priority": "HOT",
            },
            {
                "business_name": "Business Three",
                "website_status": "http_only",
                "rating": 4.0,
                "review_count": 22,
                "pepita_score": 62,
                "priority": "WARM",
            },
            {
                "business_name": "Business Four",
                "website_status": "none",
                "rating": 4.9,
                "review_count": 78,
                "pepita_score": 135,
                "priority": "ULTRA HOT",
            },
        ]
    }
    (pdir / "leads.json").write_text(json.dumps(leads), encoding="utf-8")
    return pdir


# ──────────────────────────────────────────────────────────────
# Welcome / Banner
# ──────────────────────────────────────────────────────────────

class TestWelcomeBanner:
    def test_no_args_shows_banner_and_help(self):
        result = runner.invoke(app)
        assert result.exit_code == 0
        assert "━" in result.output
        assert "Comandos disponibles" in result.output
        assert "m1" in result.output
        assert "wizard" in result.output
        assert "doctor" in result.output

    def test_version_flag_shows_help(self):
        """--version muestra help como fallback (Typer callback pattern)."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "micompaweb" in result.output.lower() or "━" in result.output


# ──────────────────────────────────────────────────────────────
# Doctor mejorado
# ──────────────────────────────────────────────────────────────

class TestDoctor:
    def test_doctor_shows_system_info(self):
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "miCompaWeb Doctor" in result.output
        assert "Python" in result.output

    def test_doctor_shows_sources(self):
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Fuentes de Leads" in result.output


# ──────────────────────────────────────────────────────────────
# m1 --list
# ──────────────────────────────────────────────────────────────

class TestM1List:
    def test_list_empty_dir(self, tmp_path: Path):
        """Directorio existe pero esta vacio -> mensaje apropiado."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = runner.invoke(app, ["m1", "--list", "--projects-dir", str(empty_dir)])
        assert result.exit_code == 0
        assert "No hay proyectos completados" in result.output

    def test_list_with_projects(self, tmp_path: Path):
        _make_project_dir(tmp_path, "plomeria-cdmx-1", business_name="Plomeria Garcia", score=87)
        _make_project_dir(tmp_path, "dentistas-miami-2", business_name="Dentista Miami", score=72)

        result = runner.invoke(app, ["m1", "--list", "--projects-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Proyectos M1 Completados" in result.output
        assert "Plomeria Garcia" in result.output
        assert "Dentista Miami" in result.output
        assert "87" in result.output
        assert "72" in result.output

    def test_list_shows_tier_counts(self, tmp_path: Path):
        _make_project_dir(tmp_path, "test-1", score=95)

        result = runner.invoke(app, ["m1", "--list", "--projects-dir", str(tmp_path)])
        assert result.exit_code == 0
        # 2 ULTRA HOT en el fixture
        assert "2" in result.output

    def test_list_shows_priority_names(self, tmp_path: Path):
        """Los nombres de negocios aparecen en la tabla de proyectos."""
        _make_project_dir(tmp_path, "biz-1", business_name="Plomeria Garcia", score=87)
        result = runner.invoke(app, ["m1", "--list", "--projects-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Plomeria Garcia" in result.output


# ──────────────────────────────────────────────────────────────
# m1 --resume
# ──────────────────────────────────────────────────────────────

class TestM1Resume:
    def test_resume_not_found(self):
        result = runner.invoke(app, ["m1", "--resume", "nonexistent", "--projects-dir", str(Path("/tmp/nonexistent_x"))])
        assert result.exit_code == 1
        assert "no encontrado" in result.output or "not found" in result.output

    def test_resume_existing(self, tmp_path: Path):
        slug = "plomeros-cdmx-test"
        _make_project_dir(tmp_path, slug, business_name="Test Prospecting")

        result = runner.invoke(app, ["m1", "--resume", slug, "--projects-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Resumen del Proyecto" in result.output

    def test_resume_shows_m2_status(self, tmp_path: Path):
        slug = "m2-ready"
        pdir = _make_project_dir(tmp_path, slug)
        (pdir / "m2").mkdir(exist_ok=True)
        (pdir / "m2" / "_state").mkdir(exist_ok=True)
        (pdir / "m2" / "_state" / "m2_complete.json").write_text(json.dumps({"done": True}))

        result = runner.invoke(app, ["m1", "--resume", slug, "--projects-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "M2 completado" in result.output


# ──────────────────────────────────────────────────────────────
# m1 --wizard
# ──────────────────────────────────────────────────────────────

class TestM1Wizard:
    @patch("micompaweb.app.cli.Wizard")
    @patch("micompaweb.app.cli.typer.confirm")
    def test_wizard_flag_cancels(self, mock_confirm, MockWizard, tmp_path: Path):
        mock_wizard = Mock()
        mock_wizard.run.return_value = Mock(
            niche="plomeros",
            location="CDMX",
            depth="estandar",
            max_leads=10,
            target_language="es",
        )
        mock_wizard.niches = ["plomeros"]
        MockWizard.return_value = mock_wizard
        mock_confirm.return_value = False

        with patch("micompaweb.app.cli.InputGuardian") as MockGuardian:
            mock_inst = Mock()
            mock_inst.normalize_niche.return_value = "plomeros"
            MockGuardian.return_value = mock_inst
            result = runner.invoke(app, ["m1", "--wizard", "--projects-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Cancelado" in result.output


# ──────────────────────────────────────────────────────────────
# wizard command
# ──────────────────────────────────────────────────────────────

class TestWizardCommand:
    @patch("micompaweb.app.cli.Wizard")
    @patch("micompaweb.app.cli.typer.confirm")
    def test_wizard_success_flow(self, mock_confirm, MockWizard, tmp_path: Path):
        mock_wizard = Mock()
        mock_wizard.run.return_value = Mock(
            niche="plomeros",
            location="CDMX",
            depth="rapida",
            max_leads=5,
            target_language="es",
        )
        mock_wizard.niches = ["plomeros"]
        MockWizard.return_value = mock_wizard
        mock_confirm.return_value = False  # cancela despues de wizard

        with patch("micompaweb.app.cli.InputGuardian") as MockGuardian:
            mock_inst = Mock()
            mock_inst.normalize_niche.return_value = "plomeros"
            MockGuardian.return_value = mock_inst
            result = runner.invoke(app, ["wizard", "--projects-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Configuraci" in result.output


# ──────────────────────────────────────────────────────────────
# projects alias
# ──────────────────────────────────────────────────────────────

class TestProjectsAlias:
    def test_projects_shows_list(self, tmp_path: Path):
        _make_project_dir(tmp_path, "alias-test", business_name="Alias Test Biz")
        result = runner.invoke(app, ["projects", "--projects-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Proyectos M1 Completados" in result.output


# ──────────────────────────────────────────────────────────────
# export
# ──────────────────────────────────────────────────────────────

class TestExport:
    def test_export_html_success(self, tmp_path: Path):
        slug = "export-test"
        _make_project_dir(tmp_path, slug, business_name="Export Test Biz", score=90)
        result = runner.invoke(app, [
            "export", slug, "--format", "html",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0, result.output
        assert "Exportado exitosamente" in result.output
        assert "html" in result.output.lower() or ".html" in result.output

    def test_export_csv_success(self, tmp_path: Path):
        slug = "export-csv"
        _make_project_dir(tmp_path, slug, business_name="CSV Test", score=80)
        result = runner.invoke(app, [
            "export", slug, "--format", "csv",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "Exportado exitosamente" in result.output
        assert "csv" in result.output.lower() or ".csv" in result.output

    def test_export_json_success(self, tmp_path: Path):
        slug = "export-json"
        _make_project_dir(tmp_path, slug, business_name="JSON Test", score=75)
        result = runner.invoke(app, [
            "export", slug, "--format", "json",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "Exportado exitosamente" in result.output
        assert "json" in result.output.lower() or ".json" in result.output

    def test_export_invalid_slug(self):
        result = runner.invoke(app, [
            "export", "no-existe", "--format", "html",
            "--projects-dir", str(Path("/tmp/nonexistent_x")),
        ])
        assert result.exit_code == 1

    def test_export_invalid_format(self, tmp_path: Path):
        slug = "export-fmt"
        _make_project_dir(tmp_path, slug)
        result = runner.invoke(app, [
            "export", slug, "--format", "xlsx",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 1
        assert "Formato no soportado" in result.output

    @patch("micompaweb.app.cli.HTMLReportExporter.export")
    def test_export_custom_output(self, mock_exp, tmp_path: Path):
        slug = "out-test"
        _make_project_dir(tmp_path, slug)
        custom_dir = tmp_path / "custom_output"
        mock_exp.return_value = ExportResult(
            file_path=custom_dir / "test.html",
            format="html",
            records_exported=4,
            file_size_bytes=1234,
            duration_ms=0,
            checksum="abc123",
        )
        result = runner.invoke(app, [
            "export", slug, "--format", "html",
            "--output", str(custom_dir),
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0


# ──────────────────────────────────────────────────────────────
# email
# ──────────────────────────────────────────────────────────────

class TestEmail:
    def test_email_success_top_lead(self, tmp_path: Path):
        slug = "email-test"
        _make_project_dir(tmp_path, slug, business_name="Email Biz", niche="plomeros")
        result = runner.invoke(app, [
            "email", slug, "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0, result.output
        assert "Borrador de Email" in result.output
        assert "Business Four" in result.output  # top score 135

    def test_email_with_index(self, tmp_path: Path):
        slug = "email-idx"
        _make_project_dir(tmp_path, slug, niche="electricistas")
        result = runner.invoke(app, [
            "email", slug, "--lead", "1",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "Borrador de Email" in result.output

    def test_email_invalid_slug(self):
        result = runner.invoke(app, [
            "email", "no-existe",
            "--projects-dir", str(Path("/tmp/nonexistent_x")),
        ])
        assert result.exit_code == 1

    def test_email_index_out_of_range(self, tmp_path: Path):
        slug = "email-range"
        _make_project_dir(tmp_path, slug)
        result = runner.invoke(app, [
            "email", slug, "--lead", "99",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 1
        assert "fuera de rango" in result.output


# ──────────────────────────────────────────────────────────────
# configure-niche
# ──────────────────────────────────────────────────────────────

class TestConfigureNiche:
    @patch("micompaweb.app.cli.Wizard")
    def test_niche_list_shows_built_in(self, MockWizard, tmp_path: Path):
        mock_w = Mock()
        mock_w.niches = ["plomeros", "electricistas", "dentistas"]
        MockWizard.return_value = mock_w

        result = runner.invoke(app, ["configure-niche", "--list"])
        assert result.exit_code == 0
        assert "plomeros" in result.output
        assert "Nichos Conocidos" in result.output

    def test_niche_add_and_remove(self, tmp_path: Path):
        # Asegurar un directorio de config limpio
        config_dir = tmp_path / "niche_config"
        with patch("micompaweb.app.cli._get_niche_config_dir", return_value=config_dir):
            result = runner.invoke(app, [
                "configure-niche",
                "--add", "cerrajeros::Cerrajeros Locales::servicios",
            ])
            assert result.exit_code == 0
            assert "Nicho añadido" in result.output
            assert "cerrajeros" in result.output

            result = runner.invoke(app, ["configure-niche", "--list"])
            assert result.exit_code == 0
            assert "cerrajeros" in result.output
            assert "personalizado" in result.output

            result = runner.invoke(app, [
                "configure-niche", "--remove", "cerrajeros",
            ])
            assert result.exit_code == 0
            assert "Nicho eliminado" in result.output

            result = runner.invoke(app, ["configure-niche", "--list"])
            assert result.exit_code == 0

    def test_niche_remove_not_found(self, tmp_path: Path):
        config_dir = tmp_path / "niche_config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "niches.yaml").write_text("custom_niches: {}\n")

        with patch("micompaweb.app.cli._get_niche_config_dir", return_value=config_dir):
            result = runner.invoke(app, [
                "configure-niche", "--remove", "fantasma",
            ])
            assert result.exit_code == 1
            assert "no encontrado" in result.output.lower()
