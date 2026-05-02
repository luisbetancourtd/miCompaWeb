"""Tests para infrastructure/deps_manager.py."""
import pytest

from micompaweb.infrastructure.deps_manager import (
    is_available,
    require,
    check_all,
    DependencyError,
)


class TestIsAvailable:
    def test_builtin_module_available(self):
        assert is_available("json") is True

    def test_fake_module_not_available(self):
        assert is_available("fake_module_xyz_123") is False

    def test_stdlib_available(self):
        assert is_available("pathlib") is True


class TestRequire:
    def test_builtin_does_not_raise(self):
        require("json")  # No raise

    def test_missing_raises_dependency_error(self):
        with pytest.raises(DependencyError) as exc:
            require("fake_module_xyz_123")
        assert "fake_module_xyz_123" in str(exc.value)

    def test_missing_with_feature_description(self):
        with pytest.raises(DependencyError) as exc:
            require("fake_module_xyz_123", feature_description="Test feature")
        assert "Test feature" in str(exc.value)

    def test_custom_hint_in_message(self):
        # Usar modulo falso para forzar raise (googlemaps podria estar instalado)
        with pytest.raises(DependencyError) as exc:
            require("crawl4ai_fake_xyz")
        assert "pip install" in str(exc.value)


class TestCheckAll:
    def test_mixed_results(self):
        results = check_all(["json", "fake_module_xyz_123", "pathlib"])
        assert results["json"] is True
        assert results["fake_module_xyz_123"] is False


class TestDependencyError:
    def test_message_format(self):
        err = DependencyError("groq")
        assert "Dependencia opcional no instalada" in str(err)

    def test_message_with_hint(self):
        err = DependencyError("ollama", "pip install ollama")
        assert "pip install ollama" in str(err)

    def test_instance_attributes(self):
        err = DependencyError("my_module")
        assert err.name == "my_module"
