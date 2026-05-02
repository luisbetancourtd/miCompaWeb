"""Graceful dependency checking for optional features."""
import importlib
from typing import Optional


class DependencyError(Exception):
    """Raised when a required optional dependency is missing."""

    def __init__(self, name: str, install_hint: str = ""):
        self.name = name
        msg = f"Dependencia opcional no instalada: {name}"
        if install_hint:
            msg += f". Instalar con: {install_hint}"
        super().__init__(msg)


# Hints de instalacion para dependencias opcionales conocidas
_INSTALL_HINTS = {
    "googlemaps": "pip install googlemaps",
    "crawl4ai": "pip install crawl4ai>=0.4.0",
    "ollama": "pip install ollama",
    "groq": "pip install groq",
    "openrouter": "pip install openrouter",
    "qdrant_client": "pip install qdrant-client",
    "fastembed": "pip install fastembed",
    "trafilatura": "pip install trafilatura",
    "curl_cffi": "pip install curl-cffi",
}


def is_available(name: str) -> bool:
    """Check if an optional dependency is installed."""
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


def require(name: str, feature_description: Optional[str] = None) -> None:
    """Raise DependencyError if a dependency is missing.

    Args:
        name: Nombre del modulo (e.g. 'googlemaps').
        feature_description: Para mensajes de error (e.g. 'Auditoria web con Chrome').
    """
    if is_available(name):
        return
    hint = _INSTALL_HINTS.get(name, f"pip install {name}")
    desc = f" para {feature_description}" if feature_description else ""
    raise DependencyError(
        name="Feature Disabled: " + name + desc,
        install_hint=hint,
    )


def check_all(deps: list[str]) -> dict[str, bool]:
    """Check multiple dependencies at once.

    Returns:
        dict {nombre: bool}.
    """
    return {d: is_available(d) for d in deps}
