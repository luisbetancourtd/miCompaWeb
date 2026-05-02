"""Tests para application/ui/setup_wizard.py."""
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import httpx

from micompaweb.application.ui.setup_wizard import SetupWizard


class TestSetupWizardWelcome:
    def test_show_welcome_calls_console(self, capsys):
        with patch("micompaweb.application.ui.setup_wizard.console") as mock_console:
            sw = SetupWizard()
            sw._show_welcome()
            assert mock_console.print.called


class TestLoadCurrentEnv:
    def test_no_env_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sw = SetupWizard()
        assert sw._load_current_env() == {}

    def test_loads_existing_env(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        Path(".env").write_text("GOOGLE_PLACES_API_KEY=test123\nGROQ_API_KEY=gsk_abc\n")
        sw = SetupWizard()
        env = sw._load_current_env()
        assert env["GOOGLE_PLACES_API_KEY"] == "test123"
        assert env["GROQ_API_KEY"] == "gsk_abc"

    def test_ignores_comments(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        Path(".env").write_text("# This is a comment\nGOOGLE_PLACES_API_KEY=real\n")
        sw = SetupWizard()
        env = sw._load_current_env()
        assert "# This is a comment" not in env
        assert env["GOOGLE_PLACES_API_KEY"] == "real"


class TestAskKey:
    def test_empty_returns_current(self):
        sw = SetupWizard()
        mock_questionary = Mock()
        mock_questionary.text.return_value.ask.return_value = ""
        with patch("micompaweb.application.ui.setup_wizard.questionary", mock_questionary):
            result = sw._ask_key("google_places_api_key", sw.KEYS["google_places_api_key"], "existing_key")
            assert result == "existing_key"

    def test_same_value_returns_current(self):
        sw = SetupWizard()
        mock_questionary = Mock()
        mock_questionary.text.return_value.ask.return_value = "same_key"
        with patch("micompaweb.application.ui.setup_wizard.questionary", mock_questionary):
            result = sw._ask_key("google_places_api_key", sw.KEYS["google_places_api_key"], "same_key")
            assert result == "same_key"

    def test_valid_format_accepted(self):
        sw = SetupWizard()
        mock_questionary = Mock()
        mock_questionary.text.return_value.ask.return_value = "AIzaSyBtest123456789012345678901234567890"
        with patch("micompaweb.application.ui.setup_wizard.questionary", mock_questionary):
            result = sw._ask_key("google_places_api_key", sw.KEYS["google_places_api_key"], None)
            assert result is not None

    def test_invalid_format_shows_error_and_retries(self):
        sw = SetupWizard()
        # Primero invalido, luego valido
        mock_questionary = Mock()
        mock_questionary.text.return_value.ask.side_effect = [
            "bad_key",
            "AIzaSyBtest123456789012345678901234567890",
        ]
        with patch("micompaweb.application.ui.setup_wizard.questionary", mock_questionary):
            with patch("micompaweb.application.ui.setup_wizard.console") as mock_console:
                result = sw._ask_key("google_places_api_key", sw.KEYS["google_places_api_key"], None)
                assert result is not None
                assert mock_console.print.called  # Muestra error de formato


class TestAskOllama:
    def test_default_localhost(self):
        sw = SetupWizard()
        mock_questionary = Mock()
        mock_questionary.text.return_value.ask.return_value = "http://localhost:11434"
        with patch("micompaweb.application.ui.setup_wizard.questionary", mock_questionary):
            result = sw._ask_ollama(None)
            assert result == "http://localhost:11434"

    def test_custom_url(self):
        sw = SetupWizard()
        mock_questionary = Mock()
        mock_questionary.text.return_value.ask.return_value = "http://192.168.1.100:11434"
        with patch("micompaweb.application.ui.setup_wizard.questionary", mock_questionary):
            result = sw._ask_ollama("http://localhost:11434")
            assert result == "http://192.168.1.100:11434"


class TestSaveToEnv:
    def test_creates_new_env(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sw = SetupWizard()
        sw._save_to_env({"google_places_api_key": "AIzaSyBtest123"})
        assert Path(".env").exists()
        content = Path(".env").read_text()
        assert "GOOGLE_PLACES_API_KEY=AIzaSyBtest123" in content

    def test_updates_existing_key(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        Path(".env").write_text("GOOGLE_PLACES_API_KEY=old_key\n")
        sw = SetupWizard()
        sw._save_to_env({"google_places_api_key": "new_key"})
        content = Path(".env").read_text()
        assert "GOOGLE_PLACES_API_KEY=new_key" in content
        assert "old_key" not in content

    def test_preserves_other_keys(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        Path(".env").write_text("OTHER_KEY=keep_me\nGOOGLE_PLACES_API_KEY=old\n")
        sw = SetupWizard()
        sw._save_to_env({"google_places_api_key": "new"})
        content = Path(".env").read_text()
        assert "OTHER_KEY=keep_me" in content
        assert "GOOGLE_PLACES_API_KEY=new" in content


class TestKeyValidation:
    def test_google_places_format_valid(self):
        meta = SetupWizard.KEYS["google_places_api_key"]
        assert meta["validate_format"]("AIzaSyBtest123456789012345678901234567890")

    def test_google_places_format_invalid_too_short(self):
        meta = SetupWizard.KEYS["google_places_api_key"]
        assert not meta["validate_format"]("AIzaSyB")

    def test_groq_format_valid(self):
        meta = SetupWizard.KEYS["groq_api_key"]
        assert meta["validate_format"]("gsk_test123456789012345678901234567890abc")

    def test_groq_format_invalid(self):
        meta = SetupWizard.KEYS["groq_api_key"]
        assert not meta["validate_format"]("wrong_prefix")


class TestRun:
    def test_run_with_no_changes(self):
        with patch.object(SetupWizard, "_show_welcome"):
            with patch.object(SetupWizard, "_load_current_env", return_value={}):
                with patch.object(SetupWizard, "_ask_key", return_value=None):
                    with patch.object(SetupWizard, "_ask_ollama", return_value=None):
                        with patch("micompaweb.application.ui.setup_wizard.console") as mock_console:
                            sw = SetupWizard()
                            sw.run()
                            # Deberia mostrar mensaje de sin cambios
                            calls = [str(c) for c in mock_console.print.call_args_list]
                            assert any("Sin cambios" in c for c in calls)

    def test_run_saves_keys(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch.object(SetupWizard, "_show_welcome"):
            with patch.object(SetupWizard, "_load_current_env", return_value={}):
                with patch.object(SetupWizard, "_ask_key", side_effect=["AIzaSyBtest123", None, None]):
                    with patch.object(SetupWizard, "_ask_ollama", return_value=None):
                        with patch("micompaweb.application.ui.setup_wizard.console"):
                            sw = SetupWizard()
                            sw.run()
                            assert Path(".env").exists()
                            content = Path(".env").read_text()
                            assert "GOOGLE_PLACES_API_KEY=AIzaSyBtest123" in content
