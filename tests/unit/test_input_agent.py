"""Tests para InputAgent - validacion de ciudad, nicho y config."""

import pytest
from unittest.mock import Mock

from micompaweb.application.ui.input_agent import InputAgent
from micompaweb.domain.models import ProjectConfig


class TestInputAgent:
    """Unit tests para normalize_city, sanitize_niche, validate_config."""

    def setup_method(self):
        self.agent = InputAgent()

    # ──────────────────────────────────────────────────────────────
    # normalize_city
    # ──────────────────────────────────────────────────────────────

    def test_normalize_city_known_exact(self):
        city, warnings = self.agent.normalize_city("madrid")
        assert city == "madrid"
        assert not warnings

    def test_normalize_city_known_tilde(self):
        city, warnings = self.agent.normalize_city("bogotá")
        assert city == "bogotá"
        assert not warnings

    def test_normalize_city_ciudad_mexico(self):
        city, warnings = self.agent.normalize_city("ciudad de México")
        assert city == "ciudad de méxico"
        assert not warnings

    def test_normalize_city_unknown(self):
        city, warnings = self.agent.normalize_city("Springfield")
        assert city == "springfield"
        assert not warnings

    def test_normalize_city_empty(self):
        city, warnings = self.agent.normalize_city("  ")
        assert city == ""
        assert any("vacía" in w.lower() for w in warnings)

    def test_normalize_city_extra_spaces(self):
        city, warnings = self.agent.normalize_city("  madrid  ")
        assert city == "madrid"
        assert not warnings

    # ──────────────────────────────────────────────────────────────
    # sanitize_niche
    # ──────────────────────────────────────────────────────────────

    def test_sanitize_niche_no_trailing_stop(self):
        # "plomeros de la ciudad": última palabra "ciudad" no es stop word => se mantiene
        assert self.agent.sanitize_niche("plomeros de la ciudad") == "plomeros de la ciudad"

    def test_sanitize_niche_no_stop_at_end(self):
        assert self.agent.sanitize_niche("electricistas") == "electricistas"

    def test_sanitize_niche_empty(self):
        assert self.agent.sanitize_niche("") == ""

    def test_sanitize_niche_strips_trailing_stop_words(self):
        # "plomeros de la " -> strip -> "plomeros de la" -> pop "la", pop "de" -> "plomeros"
        assert self.agent.sanitize_niche("plomeros de la ") == "plomeros"

    # ──────────────────────────────────────────────────────────────
    # validate_config
    # ──────────────────────────────────────────────────────────────

    def test_validate_config_ok(self):
        config = ProjectConfig(
            niche="plomeros",
            location="CDMX",
            depth="estandar",
            max_leads=50,
            target_language="es",
        )
        is_valid, errors = self.agent.validate_config(config)
        assert is_valid
        assert not errors

    def test_validate_config_empty_niche(self):
        config = ProjectConfig(
            niche="",
            location="CDMX",
            depth="estandar",
            max_leads=50,
            target_language="es",
        )
        is_valid, errors = self.agent.validate_config(config)
        assert not is_valid
        assert len(errors) > 0

    def test_sanitize_combined(self):
        original = ProjectConfig(
            niche="plomeros de la ",
            location="  madrid  ",
            depth="estandar",
            max_leads=50,
            target_language="es",
        )
        sanitized = self.agent.sanitize(original)
        assert sanitized.niche == "plomeros"
        assert sanitized.location == "madrid"

    def test_sanitize_city_unknown(self):
        original = ProjectConfig(
            niche="electricistas",
            location="Springfield",
            depth="estandar",
            max_leads=50,
            target_language="es",
        )
        sanitized = self.agent.sanitize(original)
        assert sanitized.location == "springfield"
