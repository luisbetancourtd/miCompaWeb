"""InputGuardian - validación y normalización de inputs."""

import difflib
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ValidationLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationMessage:
    level: ValidationLevel
    message: str
    suggestion: str = ""


@dataclass
class CoherenceResult:
    """Resultado de validación de coherencia."""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class InputGuardian:
    """Validación y normalización de inputs del usuario."""

    CHAIN_KEYWORDS = [
        "walmart", "costco", "soriana", "chedraui", "oxxo",
        "sanborns", "farmacias", "7-eleven", "burger king",
        "mcdonalds", "starbucks", "subway", "kfc",
        "home depot", "lowes", "ikea", "seven eleven",
        "la comer", "woolworth", "fresko",
    ]

    def __init__(self, suggestions: Optional[List[str]] = None):
        self.suggestions = suggestions or []

    @staticmethod
    def normalize_niche(input_str: str, available: List[str]) -> str:
        """Fuzzy match del input a nichos disponibles (difflib)."""
        cleaned = input_str.lower().strip()
        matches = difflib.get_close_matches(cleaned, available, n=1, cutoff=0.6)
        return matches[0] if matches else cleaned

    @staticmethod
    def normalize_location(input_str: str) -> str:
        """Normaliza ubicación: strip, title case."""
        return input_str.strip().title()

    @staticmethod
    def validate_coherence(niche: str, city: str, language: str) -> CoherenceResult:
        """Valida coherencia de la búsqueda completa."""
        result = CoherenceResult()

        if not niche or len(niche.strip()) < 3:
            result.is_valid = False
            result.errors.append("Nicho vacío o muy corto")
            result.suggestions.append("Ejemplos: plomeros, dentistas, abogados")

        if not city or len(city.strip()) < 2:
            result.is_valid = False
            result.errors.append("Ubicación vacía o muy corta")
            result.suggestions.append("Ejemplos: Ciudad de México, Guadalajara")

        if language not in {"es", "en", "fr"}:
            result.is_valid = False
            result.errors.append(f"Idioma '{language}' no soportado")
            result.suggestions.append("Usa: es (Español), en (English), fr (Français)")

        return result

    def validate(self, niche: str, city: str, language: str) -> CoherenceResult:
        """Validación completa (alias)."""
        return self.validate_coherence(niche, city, language)

    @classmethod
    def disqualify_chain(cls, business_name: str) -> bool:
        """True si el nombre contiene keyword de cadena."""
        name_lower = business_name.lower()
        return any(kw in name_lower for kw in cls.CHAIN_KEYWORDS)

    @classmethod
    def classify_location_type(cls, location: str) -> str:
        """Clasifica tipo de ubicación para estrategia anti-bot."""
        loc = location.lower()
        if any(x in loc for x in ["ciudad de", "cdmx", "mexico", "madrid", "barcelona"]):
            return "metropoli"
        elif any(x in loc for x in ["guadalajara", "monterrey", "valencia"]):
            return "metropoli_secundaria"
        elif any(x in loc for x in ["puebla", "tijuana", "ciudad juarez"]):
            return "ciudad_grande"
        elif any(x in loc for x in ["queretaro", "merida", "aguascalientes"]):
            return "ciudad_mediana"
        else:
            return "localidad"
