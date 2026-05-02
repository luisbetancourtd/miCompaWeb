"""Pantalla de cierre con resumen y tips SEO."""

import random
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

class ClosingScreen:
    """Pantalla final de sesión."""

    TIPS = [
        "💡 Publicar testimonios aumenta conversiones hasta 34%",
        "💡 La velocidad de carga < 3s reduce abandono en 32%",
        "💡 GBP optimizado = +70% probabilidad de contacto",
        "💡 Fotos de equipo humano aumentan confianza 2x",
        "💡 FAQ page reduce llamadas repetitivas un 40%",
        "💡 Schema.org LocalBusiness mejora CTR en SERP",
        "💡 Reviews con keywords ayudan al ranking local",
        "💡 SSL + HTTPS = señal de confianza para Google y clientes",
        "💡 El 46% de búsquedas Google son locales",
        "💡 78% de búsquedas locales móviles terminan en compra offline",
    ]

    def show(
        self,
        total_leads: int,
        ultra_hot: int,
        hot: int,
        warm: int,
        revenue_total: str = "",
        tips_count: int = 3,
    ) -> None:
        """Renderiza la pantalla de cierre."""

        # Métricas
        metrics = Table.grid(padding=(0, 4))
        metrics.add_column(style="bold bright_white")
        metrics.add_column(style="bright_cyan")
        metrics.add_row("📦 Total analizados:", str(total_leads))
        metrics.add_row("🔥🔥 Ultra HOT:", str(ultra_hot))
        metrics.add_row("🔥 HOT:", str(hot))
        metrics.add_row("🌡️ WARM:", str(warm))
        if revenue_total:
            metrics.add_row("💰 Revenue estimado:", revenue_total)

        # Tips aleatorios
        tips = random.sample(self.TIPS, min(tips_count, len(self.TIPS)))
        tips_text = "\n".join(tips)

        panel = Panel(
            f"[bold bright_green]✅ Sesión completada[/bold bright_green]\n\n"
            f"{metrics}\n\n"
            f"[bold bright_yellow]🦊 Tips SEO:[/bold bright_yellow]\n{tips_text}",
            title="[bold]Resumen miCompaWeb[/bold]",
            subtitle="[dim]Exporta tus resultados con --output[/dim]",
            border_style="green",
            padding=(1, 2),
        )

        console.print()
        console.print(panel)
        console.print()
