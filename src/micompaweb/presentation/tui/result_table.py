"""Tabla de resultados con colores por tier."""

from dataclasses import dataclass
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()

@dataclass
class LeadRow:
    """Fila de lead para la tabla."""
    rank: int
    name: str
    priority_tier: str
    score: int
    signals: List[str]
    phone: Optional[str] = None
    email: Optional[str] = None
    revenue_estimate: str = ""
    status: str = ""

class ResultTable:
    """Tabla Rich de leads con formato SEO-tiempo-real."""

    TIER_STYLES = {
        "ULTRA HOT":   "bold bright_red on_black",
        "HOT":         "bold bright_yellow on_black",
        "WARM":        "bold bright_green",
        "COLD":        "dim white",
        "DISCARDED":   "dim strikethrough",
    }

    TIER_ICONS = {
        "ULTRA HOT": "🔥🔥",
        "HOT":       "🔥",
        "WARM":      "🌡️",
        "COLD":      "❄️",
        "DISCARDED": "🗑️",
    }

    def render(self, leads: List[LeadRow], title: str = "Top Leads") -> Table:
        """Construye la tabla de leads."""
        table = Table(
            title=f"[bold bright_cyan]{title}[/bold bright_cyan]",
            show_header=True,
            header_style="bold bright_white",
            border_style="bright_blue",
            row_styles=["", "dim"],
        )

        table.add_column("#", style="bright_white", width=3)
        table.add_column("Tier", width=10)
        table.add_column("Negocio", style="bright_white", width=30)
        table.add_column("Score", justify="right", width=6)
        table.add_column("Señales", width=40)
        table.add_column("Estimado", justify="right", width=12)
        table.add_column("Tel/Email", width=25)

        for lead in leads:
            style = self.TIER_STYLES.get(lead.priority_tier, "")
            icon = self.TIER_ICONS.get(lead.priority_tier, "")
            tier_text = Text(f"{icon} {lead.priority_tier}", style=style)

            signals = ", ".join(lead.signals[:3])  # max 3 signals
            contact = lead.phone or lead.email or "N/D"

            table.add_row(
                str(lead.rank),
                tier_text,
                lead.name,
                f"{lead.score}",
                signals,
                lead.revenue_estimate,
                contact,
            )

        return table

    def show(self, leads: List[LeadRow], title: str = "Top Leads") -> None:
        """Muestra la tabla en consola."""
        console.print()
        console.print(self.render(leads, title))
        console.print()
