"""Pantalla de bienvenida con branding personal de Luis E. Betancourt.

Recrea el banner visual en terminal usando Rich con los colores exactos
de la imagen de marca: amarillo mostaza, rojo, gris oscuro, blanco.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich import box

console = Console()

# Colores exactos de la imagen de marca
COLOR_MUSTARD = "#D4AF37"
COLOR_RED = "#FF0000"
COLOR_WHITE = "#FFFFFF"


class WelcomeBanner:
    """Banner de bienvenida estilo Luis E. Betancourt — PARA LOS COMPAS."""

    VERSION = "v1.2.0 — M1 RECARGADO"

    def __init__(self):
        self.console = Console()

    def show(self) -> None:
        """Renderiza el banner completo con branding personal."""
        inner = self._build_inner()
        panel = Panel(
            Align.center(inner),
            border_style=f"bold {COLOR_RED}",
            box=box.HEAVY,
            padding=(1, 2),
            title=f"[bold {COLOR_MUSTARD}]miCompaWeb[/bold {COLOR_MUSTARD}]",
            subtitle=f"[dim]{self.VERSION}[/dim]",
        )
        self.console.print(panel)
        self.console.print()

    def _build_inner(self) -> Text:
        """Construye el contenido interior del banner."""
        result = Text("")

        # Línea superior decorativa — rojo
        result.append("━" * 56 + "\n", style=f"bold {COLOR_RED}")
        result.append("\n")

        # Caja del nombre — amarillo borde, blanco texto
        result.append("  ╭────────────────────────────────────────────────────╮\n", style=COLOR_MUSTARD)
        result.append("  │                                                    │\n", style=COLOR_MUSTARD)
        result.append("  │    ", style=COLOR_MUSTARD)
        result.append("L U I S   E .   B E T A N C O U R T", style=f"bold {COLOR_WHITE}")
        result.append("    │\n", style=COLOR_MUSTARD)
        result.append("  │                                                    │\n", style=COLOR_MUSTARD)
        result.append("  ╰────────────────────────────────────────────────────╯\n", style=COLOR_MUSTARD)

        result.append("\n")

        # Tagline — amarillo mostaza
        result.append("     ───  P A R A   L O S   C O M P A S  ───\n", style=f"bold {COLOR_MUSTARD}")

        result.append("\n")

        # Contacto — rojo
        result.append("      🔗  luisebetancourt.com\n", style=COLOR_RED)
        result.append("      📧  contacto@luisebetancourt.com\n", style=COLOR_RED)
        result.append("      🐦  @luisebetancourt\n", style=COLOR_RED)

        result.append("\n")

        # Línea inferior — rojo
        result.append("━" * 56 + "\n", style=f"bold {COLOR_RED}")

        result.append("\n")

        # Tagline miCompaWeb
        result.append("    🦊  Encuentra, analiza y convierte negocios con web obsoleta\n", style="dim bright_white")

        return result


def show_welcome() -> None:
    """Función helper para mostrar el banner desde cualquier lugar."""
    banner = WelcomeBanner()
    banner.show()


if __name__ == "__main__":
    show_welcome()
