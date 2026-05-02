"""InputAgent - validación y procesamiento de inputs."""

from typing import List, Tuple

from micompaweb.domain.rules.guardian import InputGuardian
from micompaweb.domain.models import ProjectConfig


class InputAgent:
    """Agente de validación y normalización de inputs del wizard."""

    KNOWN_CITIES = [
        "madrid", "barcelona", "valencia", "sevilla", "málaga", "murcia", "bilbao",
        "ciudad de México", "guadalajara", "monterrey", "puebla", "tijuana", "león",
        "bogotá", "medellín", "cali", "cartagena", "barranquilla",
        "lima", "arequipa", "trujillo", "cusco",
        "santiago", "valparaíso", "concepción",
        "buenos aires", "córdoba", "rosario",
        "miami", "houston", "los angeles", "new york", "dallas", "chicago",
        "parís", "lyon", "marseille", "toulouse", "niza", "nantes", "estrasburgo",
        "bordeaux", "lille", "rennes", "reims", "le havre", "saint-étienne",
        "toulon", "grenoble", "dijon", "angers", "nîmes", "villeurbanne",
        "saint-denis", "la rochelle", "avignon", "poitiers", "amiens",
    ]

    STOP_WORDS = {"el", "la", "los", "las", "de", "del", "y", "a", "en", "con"}

    def __init__(self):
        self.guardian = InputGuardian(suggestions=[])

    def normalize_city(self, raw: str) -> Tuple[str, List[str]]:
        """Normaliza nombre de ciudad: minúsculas, remove extra spaces, tíldes."""
        normalized = raw.lower().strip()
        normalized = normalized.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        warnings: List[str] = []
        if not normalized:
            return "", ["Ciudad vacía"]
        for city in self.KNOWN_CITIES:
            city_norm = city.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
            if normalized == city_norm or normalized in city_norm:
                if raw.lower().strip() != city:
                    warnings.append(f"Autocorregido: '{raw.strip()}' → '{city}'")
                return city, warnings
        return raw.lower().strip(), warnings

    def sanitize_niche(self, raw: str) -> str:
        """Sanitiza y normaliza nicho."""
        s = raw.lower().strip()
        words = s.split()
        while words and words[-1] in self.STOP_WORDS:
            words.pop()
        return " ".join(words) if words else s

    def validate_config(self, config: ProjectConfig) -> Tuple[bool, List[str]]:
        """Validación completa de configuración."""
        result = self.guardian.validate(
            niche=config.niche,
            city=config.location,
            language=config.target_language,
        )
        return result.is_valid, result.errors + [w for w in result.warnings]

    def sanitize(self, config: ProjectConfig) -> ProjectConfig:
        """Sanitiza completo: ciudad + nicho."""
        city, _ = self.normalize_city(config.location)
        niche = self.sanitize_niche(config.niche)
        return ProjectConfig(
            niche=niche,
            location=city,
            target_language=config.target_language,
            depth=config.depth,
            max_leads=config.max_leads,
        )
