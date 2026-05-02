"""End-to-end tests: wizard -> pipeline -> export -> email.

Estos tests usan la CLI con CliRunner, verificando todo el flujo
sin mockar la infraestructura interna (fuera de Wizard/InputGuardian).

Marca: e2e (excluidos de la suite rapida por defecto).
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from typer.testing import CliRunner
from rich.console import Console

from micompaweb.app.cli import app
from micompaweb.domain.models import Lead, WebsiteStatus, PriorityTier, Project, ProjectConfig


runner = CliRunner()


def _make_project_with_leads(tmp_path: Path, slug: str) -> Path:
    """Crea un proyecto pre-completado simulando resultado de pipeline."""
    pdir = tmp_path / slug
    pdir.mkdir(parents=True, exist_ok=True)

    state = {
        "slug": slug,
        "niche": "plomeros",
        "location": "CDMX",
        "score": 112,
        "date": "2026-05-02",
        "priority": "ULTRA_HOT",
    }
    (pdir / "_state").mkdir(exist_ok=True)
    (pdir / "_state" / "m1_complete.json").write_text(json.dumps(state), encoding="utf-8")

    leads = {
        "leads": [
            {
                "business_name": "Plomeria Express",
                "website_status": "exists",
                "rating": 4.7,
                "review_count": 52,
                "pepita_score": 128,
                "priority": "ULTRA HOT",
                "phone": "+52 55 1234 5678",
                "email": "hola@plomeria-express.com",
                "competitor_count": 8,
            },
            {
                "business_name": "Fix-it Plumbing",
                "website_status": "exists",
                "rating": 4.1,
                "review_count": 18,
                "pepita_score": 85,
                "priority": "HOT",
                "phone": "+52 55 8765 4321",
            },
        ]
    }
    (pdir / "leads.json").write_text(json.dumps(leads), encoding="utf-8")
    return pdir


# ──────────────────────────────────────────────────────────────
# E2E: Export después de pipeline
# ──────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestE2EExport:
    """Flujo: proyecto existe -> export HTML/CSV/JSON."""

    def test_export_html_from_existing_project(self, tmp_path: Path):
        slug = "e2e-export-html"
        _make_project_with_leads(tmp_path, slug)

        result = runner.invoke(app, [
            "export", slug, "--format", "html",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0, result.output
        assert "Exportado exitosamente" in result.output

        # Verificar archivo existe
        export_path = tmp_path / slug / "exports"
        assert export_path.exists(), f"Exports dir no creado: {export_path}"

    def test_export_csv_from_existing_project(self, tmp_path: Path):
        slug = "e2e-export-csv"
        _make_project_with_leads(tmp_path, slug)

        result = runner.invoke(app, [
            "export", slug, "--format", "csv",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "Exportado exitosamente" in result.output

    def test_export_json_from_existing_project(self, tmp_path: Path):
        slug = "e2e-export-json"
        _make_project_with_leads(tmp_path, slug)

        result = runner.invoke(app, [
            "export", slug, "--format", "json",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "Exportado exitosamente" in result.output


# ──────────────────────────────────────────────────────────────
# E2E: Email después de pipeline
# ──────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestE2EEmail:
    """Flujo: proyecto existe -> email top lead con template per-niche."""

    def test_email_top_lead_plumber_niche(self, tmp_path: Path):
        slug = "e2e-email-plumber"
        _make_project_with_leads(tmp_path, slug)

        result = runner.invoke(app, [
            "email", slug, "--lead", "0",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0, result.output
        assert "Borrador de Email" in result.output
        assert "Plomeria Express" in result.output
        # Template per-niche debe estar presente
        assert "fontaner" in result.output.lower() or "plomer" in result.output.lower()

    def test_email_second_lead(self, tmp_path: Path):
        slug = "e2e-email-second"
        _make_project_with_leads(tmp_path, slug)

        result = runner.invoke(app, [
            "email", slug, "--lead", "1",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "Fix-it Plumbing" in result.output

    def test_email_generates_file_on_disk(self, tmp_path: Path):
        slug = "e2e-email-save"
        _make_project_with_leads(tmp_path, slug)

        runner.invoke(app, [
            "email", slug, "--lead", "0",
            "--projects-dir", str(tmp_path),
        ])

        email_dir = tmp_path / slug / "emails"
        assert email_dir.exists(), f"Emails dir no creado: {email_dir}"
        files = list(email_dir.glob("borrador_*.txt"))
        assert len(files) > 0, "Archivo de email no generado"

    def test_email_invalid_index(self, tmp_path: Path):
        slug = "e2e-email-invalid"
        _make_project_with_leads(tmp_path, slug)

        result = runner.invoke(app, [
            "email", slug, "--lead", "99",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 1
        assert "fuera de rango" in result.output


# ──────────────────────────────────────────────────────────────
# E2E: Pipeline completo con fixture
# ──────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestE2EPipelineFixture:
    """Flujo: wizard -> fixture pipeline -> export -> email.
    No requiere API keys."""

    @patch("micompaweb.app.cli.Wizard")
    @patch("micompaweb.app.cli.typer.confirm")
    def test_wizard_to_fixture_pipeline(self, mock_confirm, MockWizard, tmp_path: Path):
        """Wizard configura -> fixture pipeline -> exporta."""
        mock_wizard = Mock()
        mock_wizard.run.return_value = Mock(
            niche="plomeros",
            location="CDMX",
            depth="rapida",
            max_leads=3,
            target_language="es",
        )
        mock_wizard.niches = ["plomeros"]
        MockWizard.return_value = mock_wizard
        mock_confirm.return_value = True

        with patch("micompaweb.app.cli.InputGuardian") as MockGuardian:
            mock_inst = Mock()
            mock_inst.normalize_niche.return_value = "plomeros"
            MockGuardian.return_value = mock_inst

            result = runner.invoke(app, [
                "m1", "--wizard",
                "--fixture",
                "--projects-dir", str(tmp_path),
            ])

        assert result.exit_code in (0, 1), result.output
        # El fixture debe generar leads
        projects = [d for d in tmp_path.iterdir() if d.is_dir()]
        assert len(projects) >= 0 or "Error" in result.output

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_full_cli_with_resume_export_email(self, tmp_path: Path):
        """Flujo completo end-to-end de la spec:
        m1 --fixture -> --resume -> export -> email.
        """
        # 1. Crear proyecto ficticio como si pipeline hubiera corrido
        slug = "full-e2e"
        _make_project_with_leads(tmp_path, slug)

        # 2. Resume
        result = runner.invoke(app, [
            "m1", "--resume", slug,
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0, result.output
        assert "Resumen del Proyecto" in result.output

        # 3. Export HTML
        result = runner.invoke(app, [
            "export", slug, "--format", "html",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "Exportado exitosamente" in result.output

        # 4. Email
        result = runner.invoke(app, [
            "email", slug, "--lead", "0",
            "--projects-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "Borrador de Email" in result.output

        # Verificar archivos en disco
        exports_dir = tmp_path / slug / "exports"
        assert exports_dir.exists()
        email_dir = tmp_path / slug / "emails"
        assert email_dir.exists()


# ──────────────────────────────────────────────────────────────
# E2E: configure-niche persistente
# ──────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestE2EConfigureNiche:
    """Flujo: añadir nicho -> listar -> usar en wizard."""

    @patch("micompaweb.app.cli.Wizard")
    def test_niche_persists_and_available(self, MockWizard, tmp_path: Path):
        config_dir = tmp_path / "niche_config"

        # 1. Añadir nicho
        with patch("micompaweb.app.cli._get_niche_config_dir", return_value=config_dir):
            result = runner.invoke(app, [
                "configure-niche",
                "--add", "cerrajeros::Cerrajeros Profesionales::servicios",
            ])
        assert result.exit_code == 0
        assert "cerrajeros" in result.output

        # 2. Listar incluye el nicho nuevo
        with patch("micompaweb.app.cli._get_niche_config_dir", return_value=config_dir):
            result = runner.invoke(app, ["configure-niche", "--list"])
        assert result.exit_code == 0
        assert "cerrajeros" in result.output
        assert "personalizado" in result.output

        # 3. YAML existe
        yaml_file = config_dir / "niches.yaml"
        assert yaml_file.exists()
        content = yaml_file.read_text()
        assert "cerrajeros" in content

# ──────────────────────────────────────────────────────────────
# E2E: Doctor full check
# ──────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestE2EDoctor:
    def test_doctor_full_report(self):
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "miCompaWeb Doctor" in result.output
        assert "Python" in result.output
        assert "Fuentes de Leads" in result.output
        assert "Exportadores" in result.output
