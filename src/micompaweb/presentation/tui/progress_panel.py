"""Panel de progreso en vivo con Rich."""

from typing import Optional
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console

console = Console()

class ProgressPanel:
    """Panel de progreso con estados de pipeline M1."""

    STAGES = [
        "validation", "discovery", "filter_chains",
        "audit", "vigency", "competitors",
        "scoring", "sentiment",
        "revenue", "export",
    ]

    STAGE_NAMES = {
        "validation":    "✅  Validación",
        "discovery":     "🔍  Descubrimiento",
        "filter_chains": "🛡️  Filtro Cadenas",
        "audit":         "🔧  Auditoría Web",
        "vigency":       "🕒  Vigencia",
        "competitors":   "⚔️  Competidores",
        "scoring":       "📊  Scoring 3D",
        "sentiment":     "🎭  Sentimiento",
        "revenue":       "💰  Revenue",
        "export":        "📦  Exportación",
    }

    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            console=console,
        )
        self.task_id: Optional[int] = None
        self.current_stage_idx = 0

    def __enter__(self):
        self.live = Live(self._render(), console=console, refresh_per_second=4)
        self.live.__enter__()
        return self

    def __exit__(self, *args):
        self.live.__exit__(*args)

    def _render(self):
        lines = []
        for i, stage in enumerate(self.STAGES):
            name = self.STAGE_NAMES[stage]
            if i < self.current_stage_idx:
                lines.append(f"[green]✓ {name}[/green]")
            elif i == self.current_stage_idx:
                if self.task_id is not None:
                    lines.append(str(self.progress.tasks[self.task_id]))
                else:
                    lines.append(f"[bold yellow]⏳ {name}...[/bold yellow]")
            else:
                lines.append(f"[dim]○ {name}[/dim]")
        return Panel(
            "\n".join(lines),
            title="[bold]Pipeline M1[/bold]",
            border_style="bright_blue",
        )

    def start_stage(self, stage: str, total_steps: int = 100) -> None:
        """Inicia una nueva etapa."""
        self.current_stage_idx = self.STAGES.index(stage)
        desc = self.STAGE_NAMES.get(stage, stage)
        self.task_id = self.progress.add_task(desc, total=total_steps)
        self._refresh()

    def advance(self, steps: int = 1) -> None:
        """Avanza el progreso."""
        if self.task_id is not None:
            self.progress.advance(self.task_id, steps)
            self._refresh()

    def complete_stage(self, message: str = "") -> None:
        """Marca la etapa actual como completada."""
        if self.task_id is not None:
            self.progress.update(self.task_id, completed=self.progress.tasks[self.task_id].total)
            self.task_id = None
            self.current_stage_idx += 1
        if message:
            console.print(f"[green]{message}[/green]")
        self._refresh()

    def _refresh(self):
        if hasattr(self, "live") and self.live is not None:
            self.live.update(self._render())
