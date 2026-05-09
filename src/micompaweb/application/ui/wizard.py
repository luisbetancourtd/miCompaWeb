"""Wizard interactivo con Questionary."""

import questionary
from typing import Optional

from micompaweb.domain.models import ProjectConfig
from micompaweb.domain.models.niche import NicheRepository

class Wizard:
    """Wizard de 4 pasos para configurar prospección."""

    NICHE_HINTS = {
        "plomeros":       "Ej: plomería, fontanería",
        "electricistas":  "Ej: electricidad industrial",
        "carpinteros":    "Ej: ebanistería, muebles a medida",
        "dentistas":      "Ej: odontología, ortodoncia",
        "abogados":       "Ej: derecho penal, laboral",
        "restaurantes":   "Ej: cocina fusión, cafetería",
    }

    def __init__(self):
        self.niches = NicheRepository.list_available()

    def run(self) -> ProjectConfig:
        """Ejecuta el wizard completo con validación."""
        from micompaweb.application.ui.input_agent import InputAgent
        agent = InputAgent()

        niche_raw = self._ask_niche()
        niche = agent.sanitize_niche(niche_raw)
        niche = agent.guardian.normalize_niche(niche, self.niches)

        location = self._ask_location_with_agent(agent, niche)
        language = self._ask_language()
        depth = self._ask_depth()
        max_leads = self._ask_max_leads()

        config = ProjectConfig(
            niche=niche,
            location=location,
            target_language=language,
            depth=depth,
            max_leads=max_leads,
        )

        config = agent.sanitize(config)
        is_valid, errors = agent.validate_config(config)
        if not is_valid:
            for e in errors:
                questionary.print(f"❌ {e}", style="bold fg:red")
            raise ValueError("Configuracion invalida")

        return config

    def _ask_niche(self) -> str:
        """Pregunta nicho con búsqueda fuzzy."""
        return questionary.autocomplete(
            "Elige tu nicho de negocio:",
            choices=self.niches,
            style=questionary.Style([
                ("qmark", "bold fg:cyan"),
                ("question", "bold"),
                ("answer", "bold fg:green"),
            ]),
        ).ask()

    def _ask_location_with_agent(self, agent, niche: str) -> str:
        """Pregunta ciudad con normalización y confirmación de autocorrección."""
        hint = self.NICHE_HINTS.get(niche, "Ej: Ciudad de México")
        while True:
            raw = questionary.text(
                f"Ciudad o área para buscar {niche}:",
                instruction=hint,
                validate=lambda t: len(t.strip()) >= 2 or "Mínimo 2 caracteres",
            ).ask()
            city, warnings = agent.normalize_city(raw)
            if warnings:
                for w in warnings:
                    questionary.print(f"  {w}", style="italic fg:yellow")
                if questionary.confirm(f"Usar '{city}'?", default=True).ask():
                    return city
            else:
                return city

    def _ask_language(self) -> str:
        """Pregunta idioma de comunicación."""
        return questionary.select(
            "Idioma de comunicación:",
            choices=[
                questionary.Choice("Español", value="es"),
                questionary.Choice("English", value="en"),
                questionary.Choice("Français", value="fr"),
            ],
            default="es",
        ).ask()

    def _ask_depth(self) -> str:
        """Pregunta profundidad de análisis."""
        return questionary.select(
            "Profundidad de análisis:",
            choices=[
                questionary.Choice(
                    "⚡ Rápida (~2 min)  - Solo GBP + scoring básico",
                    value="rapida",
                ),
                questionary.Choice(
                    "🔧 Estándar (~5 min) - Competidores + auditoría web",
                    value="estandar",
                ),
                questionary.Choice(
                    "🔬 Exhaustiva (~12 min) - Full pipeline + sentiment",
                    value="exhaustiva",
                ),
            ],
            default="estandar",
        ).ask()

    def _ask_max_leads(self) -> int:
        """Pregunta cantidad de leads."""
        result = questionary.select(
            "Máximo de leads a prospectar:",
            choices=[5, 10, 20, 50, 100],
            default=20,
        ).ask()
        return result if isinstance(result, int) else int(result)

    def welcome(self) -> None:
        """Muestra mensaje de bienvenida del wizard."""
        questionary.print("")
        questionary.print(
            "🦊 miCompaWeb - Configuración de prospección",
            style="bold fg:cyan",
        )
        questionary.print(
            "Responde 5 preguntas para encontrar tus mejores oportunidades.\n",
            style="italic",
        )
