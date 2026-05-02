"""Tests for InputGuardian and InputAgent."""

import pytest

from micompaweb.domain.rules.guardian import InputGuardian, ValidationLevel
from micompaweb.application.ui.input_agent import InputAgent
from micompaweb.domain.models import ProjectConfig


class TestInputGuardian:
    """Test suite para InputGuardian."""

    def test_normalize_niche_exact_match(self):
        guardian = InputGuardian()
        available = ["plomeros", "dentistas", "abogados"]
        assert guardian.normalize_niche("plomeros", available) == "plomeros"

    def test_normalize_niche_fuzzy_match(self):
        guardian = InputGuardian()
        available = ["plomeros", "dentistas", "abogados"]
        assert guardian.normalize_niche("plomero", available) == "plomeros"

    def test_normalize_niche_no_match_returns_cleaned(self):
        guardian = InputGuardian()
        available = ["plomeros", "dentistas"]
        assert guardian.normalize_niche("carpinteros", available) == "carpinteros"

    def test_normalize_location_basic(self):
        assert InputGuardian.normalize_location("  ciudad de méxico  ") == "Ciudad De México"

    def test_disqualify_chain_detects_walmart(self):
        assert InputGuardian.disqualify_chain("Walmart Supercenter") is True

    def test_disqualify_chain_passes_local(self):
        assert InputGuardian.disqualify_chain("El Rincón de María") is False

    def test_validate_coherence_valid(self):
        result = InputGuardian.validate_coherence("plomeros", "madrid", "es")
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_coherence_empty_niche(self):
        result = InputGuardian.validate_coherence("", "madrid", "es")
        assert result.is_valid is False
        assert any("Nicho vacío" in e for e in result.errors)

    def test_validate_coherence_invalid_language(self):
        result = InputGuardian.validate_coherence("plomeros", "madrid", "de")
        assert result.is_valid is False
        assert any("no soportado" in e for e in result.errors)

    def test_classify_location_metropoli(self):
        assert InputGuardian.classify_location_type("ciudad de mexico") == "metropoli"

    def test_classify_location_ciudad_mediana(self):
        assert InputGuardian.classify_location_type("queretaro") == "ciudad_mediana"

    def test_classify_location_localidad(self):
        assert InputGuardian.classify_location_type("cuautla") == "localidad"


class TestInputAgent:
    """Test suite para InputAgent."""

    def test_normalize_city_known_city(self):
        agent = InputAgent()
        city, warnings = agent.normalize_city("madrid")
        assert city == "madrid"
        assert len(warnings) == 0

    def test_normalize_city_accent_correction(self):
        agent = InputAgent()
        city, warnings = agent.normalize_city("málaga")
        assert city == "málaga"

    def test_normalize_city_empty(self):
        agent = InputAgent()
        city, warnings = agent.normalize_city("  ")
        assert city == ""
        assert "Ciudad vacía" in warnings

    def test_sanitize_niche_removes_stopwords(self):
        agent = InputAgent()
        assert agent.sanitize_niche("plomeros de la") == "plomeros"

    def test_sanitize_niche_no_stopwords(self):
        agent = InputAgent()
        assert agent.sanitize_niche("abogados") == "abogados"

    def test_validate_config_valid(self):
        agent = InputAgent()
        config = ProjectConfig(niche="plomeros", location="madrid", target_language="es")
        is_valid, errors = agent.validate_config(config)
        assert is_valid is True

    def test_validate_config_invalid(self):
        agent = InputAgent()
        config = ProjectConfig(niche="", location="", target_language="es")
        is_valid, errors = agent.validate_config(config)
        assert is_valid is False

    def test_sanitize_completo(self):
        agent = InputAgent()
        config = ProjectConfig(niche="  Plomeros De La  ", location="MALAGA", target_language="es")
        sanitized = agent.sanitize(config)
        assert sanitized.niche == "plomeros"
        assert sanitized.location == "málaga"
